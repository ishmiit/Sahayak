"""Impact counters: a monthly number for the district, with no personal data kept.

Only counts are stored: never names, numbers, message text or anything a person typed. Each
month is a small JSON object in %USERPROFILE%/.sahayak/data/counters.json:

  checks       scam checks completed, by input type (text, call, voice, ocr, qr)
  verdicts     scam / suspicious / no_signs
  categories   scam categories (the export shows the top five)
  rupees_at_risk  sum of amounts named or requested in messages judged Scam ("at risk", never "saved")
  schemes      people found eligible or likely eligible, by scheme
  slips        slips printed: fraud, scheme
  escalations  "Ask the agent" requests
  languages    sessions by language

The monthly export is a CSV in which any count below 5 is shown as "<5", signed with the node's
Ed25519 key so the district can tell it was not edited on the way.
"""
from __future__ import annotations

import base64
import csv
import io
import json
import threading
import time
from collections import OrderedDict
from pathlib import Path

from ..config import get_settings

FIELDS = ("checks", "verdicts", "categories", "schemes", "slips", "languages")
SMALL = 5
_lock = threading.Lock()
_seen: OrderedDict[str, float] = OrderedDict()  # navigator sessions already counted (memory only)


def _path() -> Path:
    return get_settings().data_dir / "counters.json"


def month(ts: float | None = None) -> str:
    return time.strftime("%Y-%m", time.localtime(ts or time.time()))


def _load() -> dict:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def _bump(changes: list[tuple[str, str | None, int]]) -> None:
    with _lock:
        data = _load()
        m = data.setdefault(month(), {})
        for field, key, n in changes:
            if key is None:
                m[field] = m.get(field, 0) + n
            else:
                bucket = m.setdefault(field, {})
                bucket[key] = bucket.get(key, 0) + n
        _save(data)


def record_check(card: dict, lang: str | None = None) -> None:
    """One completed scam check. Takes only the verdict card's coded fields."""
    changes = [("checks", card.get("input_type", "text"), 1), ("verdicts", card["verdict"], 1)]
    if card["verdict"] == "scam":
        if card.get("category"):
            changes.append(("categories", card["category"]["id"], 1))
        changes.append(("rupees_at_risk", None, int(card.get("extracted", {}).get("rupees_at_risk") or 0)))
    if lang in ("hi", "en"):
        changes.append(("languages", lang, 1))
    _bump(changes)


def record_navigator(session: str | None, result: dict, lang: str | None = None) -> None:
    """People found eligible or likely eligible, by scheme: once per interview session."""
    if not session:
        return
    with _lock:
        if session in _seen:
            return
        _seen[session] = time.time()
        while len(_seen) > 2048:
            _seen.popitem(last=False)
    changes = [("schemes", sid, 1) for g in ("eligible", "likely") for sid in result["groups"].get(g, [])]
    if lang in ("hi", "en"):
        changes.append(("languages", lang, 1))
    if changes:
        _bump(changes)


def record_slip(kind: str) -> None:
    if kind in ("fraud", "scheme"):
        _bump([("slips", kind, 1)])


def record_escalation() -> None:
    _bump([("escalations", None, 1)])


def view(which: str | None = None) -> dict:
    """The counters for one month (default: this month), exactly as stored."""
    return _load().get(which or month(), {})


def masked(n: int) -> str:
    return "<5" if 0 < n < SMALL else str(n)


def export_rows(which: str | None = None) -> list[tuple[str, str, str]]:
    m = view(which)
    rows = []
    for field in FIELDS:
        items = sorted(m.get(field, {}).items(), key=lambda kv: -kv[1])
        if field == "categories":
            items = items[:5]  # the top five scam categories
        rows += [(field, key, masked(n)) for key, n in items]
    # a sum over fewer than 5 scam messages could reveal one person's amount: withhold it
    scams = m.get("verdicts", {}).get("scam", 0)
    rows.append(("rupees_at_risk", "", str(m.get("rupees_at_risk", 0)) if scams >= SMALL else "withheld (<5 scams)"))
    rows.append(("escalations", "", masked(m.get("escalations", 0))))
    return rows


def export_csv(which: str | None = None) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["month", "counter", "key", "value"])
    for field, key, value in export_rows(which):
        w.writerow([which or month(), field, key, value])
    return buf.getvalue()


def sign(text: str) -> dict:
    """Sign an export with the node's own Ed25519 key (created on first use)."""
    from ..signing import load_or_create_private_key, public_pem
    key = load_or_create_private_key(get_settings().home / "keys" / "node-export.key")
    return {"signature": base64.b64encode(key.sign(text.encode("utf-8"))).decode("ascii"),
            "public_key": public_pem(key).decode("ascii")}


def reset() -> None:
    with _lock:
        _save({})
