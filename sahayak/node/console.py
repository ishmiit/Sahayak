"""The operator console's state: PIN sessions, the "Ask the agent" queue, and the case log.

PIN. The console sits behind a PIN (SAHAYAK_CONSOLE_PIN). If none is set, a random six-digit PIN is
made at start-up and printed in the node's terminal, so there is never a default password.
Five wrong tries lock logins for a minute.

Queue. A citizen's "Ask the agent" puts a ticket (A-01, A-02…) in a memory-only queue with the
verdict or the scheme results it refers to. Tickets expire after two hours; nothing is written
to disk.

Case log. Only with the person's consent, and only coded fields: verdict, category, amount at
risk, scheme results, language. No message text, names or numbers. Encrypted at rest (Fernet,
key in %USERPROFILE%/.sahayak/keys), and entries older than 30 days are deleted automatically.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from collections import OrderedDict

from cryptography.fernet import Fernet, InvalidToken

from ..config import get_settings

SESSION_TTL = 12 * 3600
QUEUE_TTL = 2 * 3600
CASE_DAYS = 30
_lock = threading.Lock()


# ---------------------------------------------------------------- PIN and sessions

class Auth:
    def __init__(self, pin: str | None):
        self.pin = pin or f"{secrets.randbelow(10**6):06d}"
        self.generated = pin is None
        self.sessions: dict[str, float] = {}
        self.failures: list[float] = []

    def login(self, pin: str) -> str | None:
        now = time.time()
        self.failures = [t for t in self.failures if now - t < 60]
        if len(self.failures) >= 5:
            raise PermissionError("too many wrong PINs; try again in a minute")
        if not secrets.compare_digest(str(pin), self.pin):
            self.failures.append(now)
            return None
        token = secrets.token_urlsafe(24)
        self.sessions[token] = now
        return token

    def check(self, token: str | None) -> bool:
        started = self.sessions.get(token or "")
        if started is None or time.time() - started > SESSION_TTL:
            self.sessions.pop(token or "", None)
            return False
        return True

    def logout(self, token: str | None) -> None:
        self.sessions.pop(token or "", None)


# ---------------------------------------------------------------- queue

class Queue:
    def __init__(self):
        self.items: OrderedDict[str, dict] = OrderedDict()
        self.counter = 0

    def add(self, kind: str, summary: dict, lang: str) -> dict:
        with _lock:
            self._expire()
            self.counter = self.counter % 99 + 1
            ticket = f"A-{self.counter:02d}"
            item = {"ticket": ticket, "kind": kind, "summary": summary, "lang": lang,
                    "at": time.strftime("%H:%M"), "created": time.time(), "state": "waiting"}
            self.items[ticket] = item
            return item

    def list(self) -> list[dict]:
        with _lock:
            self._expire()
            return [{k: v for k, v in i.items() if k != "created"} for i in self.items.values()]

    def set_state(self, ticket: str, state: str) -> dict | None:
        with _lock:
            item = self.items.get(ticket)
            if item:
                item["state"] = state
                if state == "done":
                    self.items.pop(ticket)
            return item

    def clear(self) -> None:
        with _lock:
            self.items.clear()

    def _expire(self) -> None:
        now = time.time()
        for t in [t for t, i in self.items.items() if now - i["created"] > QUEUE_TTL]:
            self.items.pop(t)


# ---------------------------------------------------------------- case log

CASE_FIELDS = {"kind", "verdict", "category", "rupees_at_risk", "schemes", "lang", "slip_printed"}


class CaseLog:
    def __init__(self):
        s = get_settings()
        self.path = s.data_dir / "caselog.enc"
        key_file = s.home / "keys" / "caselog.key"
        if not key_file.exists():
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(Fernet.generate_key())
        self.fernet = Fernet(key_file.read_bytes())

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_bytes().splitlines():
            try:
                out.append(json.loads(self.fernet.decrypt(line)))
            except (InvalidToken, ValueError):
                continue  # a line from another key or a damaged write: skip it
        return out

    def _write(self, entries: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_bytes(b"\n".join(self.fernet.encrypt(json.dumps(e).encode("utf-8")) for e in entries))
        tmp.replace(self.path)

    def add(self, entry: dict, consent: bool) -> dict:
        if not consent:
            raise PermissionError("the person has not agreed to keep a record")
        record = {k: v for k, v in entry.items() if k in CASE_FIELDS}
        record.update(id=secrets.token_hex(4), at=time.strftime("%Y-%m-%dT%H:%M"), ts=time.time())
        with _lock:
            entries = self._fresh(self._read())
            entries.append(record)
            self._write(entries)
        return record

    def list(self, limit: int = 50) -> list[dict]:
        with _lock:
            entries = self._read()
            fresh = self._fresh(entries)
            if len(fresh) != len(entries):
                self._write(fresh)  # 30-day auto-delete happens on every read
        return list(reversed(fresh))[:limit]

    def clear(self) -> None:
        with _lock:
            if self.path.exists():
                self.path.unlink()

    @staticmethod
    def _fresh(entries: list[dict]) -> list[dict]:
        cutoff = time.time() - CASE_DAYS * 86400
        return [e for e in entries if e.get("ts", 0) >= cutoff]


QUEUE = Queue()
_auth: Auth | None = None
_caselog: CaseLog | None = None


def auth() -> Auth:
    global _auth
    if _auth is None:
        import os
        _auth = Auth(os.environ.get("SAHAYAK_CONSOLE_PIN") or None)
        if _auth.generated:
            print(f"Operator console PIN for this run: {_auth.pin}  (set SAHAYAK_CONSOLE_PIN to choose one)", flush=True)
    return _auth


def caselog() -> CaseLog:
    global _caselog
    if _caselog is None:
        _caselog = CaseLog()
    return _caselog
