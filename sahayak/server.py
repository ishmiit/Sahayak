"""Sahayak node server: serves the phone app and the API from one offline process.

Zero-egress by construction: FastAPI's interactive docs are disabled (they load
scripts from a CDN), every response carries a Content-Security-Policy that lets
the browser talk only to this node, and the LLM backend refuses public hosts.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import psutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import __version__
from .config import REPO_ROOT, get_settings
from .fraud.explain import explain
from .fraud.pipeline import check_message_full
from .inputs.ocr import OCRUnavailable, get_reader
from .inputs.qr import QRError
from .inputs.qr import analyse as qr_analyse
from .inputs.qr import decode as qr_decode
from .llm import get_backend
from .navigator import AnswerError, get_navigator, slip
from .navigator.slip import qr_data_uri
from .node import console, counters, egress
from .node import status as node_status
from .packs import get_pack, installed_packs
from .voice import (ASRUnavailable, AudioError, TTSUnavailable, get_listener, get_speaker, grammar, match,
                    read_audio, read_wav)

CSP = (
    "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; "
    "font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)
STARTED = time.time()
egress.install()  # count every outbound attempt this process makes (it should never make one)


def _warm_model() -> None:
    """Load the models in the background so the first explanation, the first spoken
    sentence and the first recognised answer are not cold starts."""
    def _warm() -> None:
        try:
            speaker = get_speaker()
            for lang, voices in speaker.voices().items():
                for v in voices:
                    speaker.synth("नमस्ते" if lang == "hi" else "Hello", lang, v)
            for lang in get_listener().languages():
                get_listener()._model(lang)  # noqa: SLF001 - loading is the point
            # The screenshot reader (PyTorch, about 1 GB) is used least; load it at start-up only when
            # asked (SAHAYAK_WARM_OCR=1 on a demo node with RAM to spare), else on the first screenshot.
            if os.environ.get("SAHAYAK_WARM_OCR") == "1" and get_reader().available():
                get_reader()._load()  # noqa: SLF001 - loading is the point
        except Exception:  # noqa: BLE001 - warm-up is best effort
            pass
        try:
            backend = get_backend()
            if backend.info().get("available"):
                backend.chat_json("Reply with JSON.", "Say ok.", {"type": "object", "properties": {"ok": {"type": "string"}}},
                                  max_tokens=8, timeout=180)
        except Exception:  # noqa: BLE001 - warm-up is best effort
            pass
    threading.Thread(target=_warm, daemon=True).start()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _warm_model()
    console.auth()  # makes (and prints) the operator PIN at start-up if none was set
    yield


app = FastAPI(title="Sahayak node", version=__version__, docs_url=None, redoc_url=None, openapi_url=None,
              lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(self), microphone=(self)"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------- recent checks (memory only)

class _Recent:
    """Last few checks, kept in memory for 15 minutes so /api/explain can find them.
    Nothing is written to disk; message text never outlives this window."""

    def __init__(self, max_items: int = 256, ttl_s: float = 900):
        self._items: OrderedDict[str, tuple[float, str, dict, list]] = OrderedDict()
        self._lock = threading.Lock()
        self.max_items, self.ttl_s = max_items, ttl_s

    def put(self, card: dict, text: str, fired: list) -> None:
        with self._lock:
            self._items[card["id"]] = (time.time(), text, card, fired)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def get(self, check_id: str) -> tuple[str, dict, list] | None:
        with self._lock:
            item = self._items.get(check_id)
            if not item or time.time() - item[0] > self.ttl_s:
                self._items.pop(check_id, None)
                return None
            return item[1], item[2], item[3]


RECENT = _Recent()


# ---------------------------------------------------------------- API

class CheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    sender: str | None = Field(default=None, max_length=40)
    input_type: Literal["text", "voice", "ocr", "qr", "call"] = "text"
    lang: Literal["hi", "en"] | None = None  # the app's language, for the language counter only


class ExplainRequest(BaseModel):
    id: str = Field(min_length=4, max_length=32)


@app.post("/api/check")
def api_check(req: CheckRequest) -> dict[str, Any]:
    card, fired = check_message_full(req.text, sender=req.sender, input_type=req.input_type)
    RECENT.put(card, req.text, fired)
    counters.record_check(card, req.lang)  # counts only: no text, numbers or names
    return card


@app.post("/api/explain")
def api_explain(req: ExplainRequest) -> dict[str, Any]:
    found = RECENT.get(req.id)
    if not found:
        raise HTTPException(status_code=404, detail="Check expired or not found; run the check again")
    text, card, fired = found
    return explain(text, card, fired, timeout=get_settings().llm_timeout_s)


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "uptime_s": round(time.time() - STARTED),
        "packs": installed_packs(),
        "llm": get_backend().info(),
        "llm_langs": list(get_settings().llm_langs),
        "voice": {"tts": get_speaker().voices(), "asr": get_listener().languages()},
        "lan_addresses": lan_addresses(),
    }


@app.get("/api/examples")
def api_examples() -> dict[str, Any]:
    return get_pack("demo").data


@app.get("/api/demo/qr/{example_id}")
def api_demo_qr(example_id: str) -> Response:
    """An example QR code from the demo pack, as an image: lets the app (and printed demo cards)
    try the QR check without a real payment code."""
    for ex in get_pack("demo").data.get("qr_examples", []):
        if ex["id"] == example_id:
            import io as _io
            import qrcode as _qrcode
            from qrcode.image.pil import PilImage
            buf = _io.BytesIO()
            _qrcode.make(ex["payload"], image_factory=PilImage, box_size=8, border=3).get_image().save(buf, format="PNG")
            return Response(buf.getvalue(), media_type="image/png")
    raise HTTPException(status_code=404, detail="no such example")


# Benefits Navigator. Stateless: the phone sends all answers so far on every call, and the
# node keeps nothing, so no answer outlives the request.

class NavigatorRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    already: list[str] = Field(default_factory=list, max_length=20)
    session: str | None = Field(default=None, max_length=40)  # counts each interview once
    lang: Literal["hi", "en"] | None = None


@app.get("/api/navigator")
def api_navigator() -> dict[str, Any]:
    return get_navigator().catalog()


@app.post("/api/navigator/next")
def api_navigator_next(req: NavigatorRequest) -> dict[str, Any]:
    nav = get_navigator()
    try:
        question = nav.next_question(req.answers)
    except AnswerError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return {"done": question is None, "question": question, "asked": len(req.answers),
            "max_questions": nav.max_questions}


@app.post("/api/navigator/result")
def api_navigator_result(req: NavigatorRequest) -> dict[str, Any]:
    try:
        result = get_navigator().result(req.answers, already=req.already)
    except AnswerError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    result["slip"] = slip(result)
    counters.record_navigator(req.session, result, req.lang)
    return result


# Voice. Speech out works for every phone; speech in needs the page on a secure origin
# (localhost on the node, or HTTPS from Phase 6) because browsers only open the mic there.

class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    lang: Literal["hi", "en"] = "hi"
    voice: Literal["female", "male"] = "female"
    speed: float = Field(default=0.9, ge=0.6, le=1.3)


@app.post("/api/tts")
def api_tts(req: TTSRequest) -> Response:
    try:
        wav, info = get_speaker().synth(req.text, req.lang, req.voice, req.speed)
    except TTSUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from None
    return Response(wav, media_type="audio/wav",
                    headers={"X-Sahayak-Cached": info["cached"], "X-Sahayak-Ms": str(info["ms"])})


MAX_AUDIO_BYTES = 2 * 1024 * 1024


@app.post("/api/asr")
async def api_asr(request: Request, lang: Literal["hi", "en"] = "hi", question: str | None = None,
                  options: str | None = None) -> dict[str, Any]:
    """Body: a recording (WAV from the app's recorder, or any common audio file from a phone's
    recorder app where the browser will not open the mic). With `question` (a Navigator question id) and `options` (the
    shown option ids, comma-separated) the answer is matched too; nothing is stored."""
    body = await request.body()
    if len(body) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="recording too long")
    try:
        pcm, seconds = read_audio(body)
    except AudioError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    q = None
    if question:
        nav_q = get_navigator().by_id.get(question)
        if nav_q is None:
            raise HTTPException(status_code=422, detail=f"unknown question '{question}'")
        shown = set((options or "").split(",")) if options else None
        q = {"id": nav_q["id"], "kind": nav_q["kind"],
             "options": [o for o in nav_q.get("options", []) if shown is None or o["id"] in shown]}

    def recognise() -> dict[str, Any]:
        listener = get_listener()
        out = listener.transcribe(pcm, lang)
        out["seconds"] = round(seconds, 2)
        if q is not None:
            found = match(q, out["text"], lang)
            if found is None:  # open dictation missed: try again against the answer's own words
                second = listener.transcribe(pcm, lang, grammar=grammar(q, lang))
                found = match(q, second["text"], lang)
                if found is not None:
                    out.update(text=second["text"], confidence=second["confidence"], grammar=True,
                               ms=out["ms"] + second["ms"])
            out["answer"] = found["answer"] if found else None
        return out

    try:
        return await run_in_threadpool(recognise)
    except ASRUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from None


# VoiceBench recording: consented speech samples for the benchmark. Off unless the node is
# started with SAHAYAK_VOICEBENCH=1; no names; files stay on the node; a speaker can withdraw.

VB_PROMPTS = REPO_ROOT / "bench" / "voicebench" / "prompts_v1.jsonl"
_VB_SESSION = re.compile(r"^\d{8}-[0-9a-f]{8}$")


class VoiceBenchSession(BaseModel):
    consent: bool
    age_band: Literal["18-34", "35-54", "55+"]
    gender: Literal["female", "male", "other", "not_said"] = "not_said"
    region: str = Field(default="", max_length=40)
    first_language: str = Field(default="", max_length=30)


def _voicebench_dir(session: str | None = None) -> Path:
    if not get_settings().voicebench:
        raise HTTPException(status_code=404, detail="VoiceBench recording is off (start the node with SAHAYAK_VOICEBENCH=1)")
    base = get_settings().data_dir / "voicebench"
    if session is None:
        return base
    if not _VB_SESSION.match(session) or not (base / session).is_dir():
        raise HTTPException(status_code=404, detail="unknown session")
    return base / session


def _voicebench_prompts() -> dict[str, dict]:
    rows = [json.loads(line) for line in VB_PROMPTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {r["id"]: r for r in rows}


@app.get("/api/voicebench/prompts")
def api_voicebench_prompts() -> dict[str, Any]:
    _voicebench_dir()
    return {"prompts": [{"id": p["id"], "lang": p["lang"], "text": p["text"]} for p in _voicebench_prompts().values()]}


@app.post("/api/voicebench/session")
def api_voicebench_session(req: VoiceBenchSession) -> dict[str, Any]:
    base = _voicebench_dir()
    if not req.consent:
        raise HTTPException(status_code=422, detail="consent is required")
    session = f"{time.strftime('%Y%m%d')}-{secrets.token_hex(4)}"
    (base / session).mkdir(parents=True)
    meta = {"speaker": req.model_dump(exclude={"consent"}), "consent": True, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "prompts": VB_PROMPTS.name}
    (base / session / "session.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"session": session}


@app.post("/api/voicebench/{session}/{prompt_id}")
async def api_voicebench_record(session: str, prompt_id: str, request: Request) -> dict[str, Any]:
    folder = _voicebench_dir(session)
    if prompt_id not in _voicebench_prompts():
        raise HTTPException(status_code=404, detail="unknown prompt")
    body = await request.body()
    if len(body) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="recording too long")
    try:
        _, seconds = read_wav(body)
    except AudioError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    (folder / f"{prompt_id}.wav").write_bytes(body)  # a re-record replaces the earlier take
    return {"saved": prompt_id, "seconds": round(seconds, 2)}


@app.delete("/api/voicebench/{session}")
def api_voicebench_withdraw(session: str) -> dict[str, Any]:
    folder = _voicebench_dir(session)
    shutil.rmtree(folder)
    return {"deleted": session}


# ---------------------------------------------------------------- photographed QR codes and screenshots
MAX_IMAGE_BYTES = 8 * 1024 * 1024


@app.post("/api/qr")
async def api_qr(request: Request, lang: Literal["hi", "en"] | None = None) -> dict[str, Any]:
    """Body: a photo or screenshot of a QR code. Returns the usual verdict card plus what the
    code really does ("scanning sends money; it never brings money in")."""
    body = await request.body()
    if len(body) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image too large")
    try:
        payload = await run_in_threadpool(qr_decode, body)
    except QRError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    info = qr_analyse(payload)
    card, fired = check_message_full(info["check_text"], input_type="qr")
    RECENT.put(card, info["check_text"], fired)
    counters.record_check(card, lang)
    card["qr"] = {k: v for k, v in info.items() if k != "check_text"}
    return card


@app.post("/api/ocr")
async def api_ocr(request: Request) -> dict[str, Any]:
    """Body: a screenshot or photo of a message. Returns the text read offline, for the person to
    look over before it is checked (nothing is kept)."""
    body = await request.body()
    if len(body) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image too large")
    try:
        return await run_in_threadpool(get_reader().read, body)
    except OCRUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


# ---------------------------------------------------------------- "Ask the agent" and the operator console
# The citizen app can hand a case to the agent at the counter; the console (behind a PIN) shows the
# queue, runs assisted checks, keeps a consented and encrypted case log, prints slips, and shows the
# impact counters. Nothing here stores message text, names or numbers.

class QueueRequest(BaseModel):
    kind: Literal["check", "benefits"]
    check_id: str | None = Field(default=None, max_length=32)
    answers: dict[str, Any] = Field(default_factory=dict)
    lang: Literal["hi", "en"] = "hi"


@app.post("/api/queue")
def api_queue(req: QueueRequest) -> dict[str, Any]:
    if req.kind == "check":
        found = RECENT.get(req.check_id or "")
        if not found:
            raise HTTPException(status_code=404, detail="Check expired; run it again")
        card = found[1]
        summary = {"check_id": card["id"], "verdict": card["verdict"], "label": card["label"],
                   "category": card["category"]["name"] if card.get("category") else None,
                   "rupees_at_risk": card["extracted"]["rupees_at_risk"]}
    else:
        try:
            result = get_navigator().result(req.answers)
        except AnswerError as e:
            raise HTTPException(status_code=422, detail=str(e)) from None
        names = {s["id"]: s["short"] for s in result["schemes"]}
        summary = {"answers": req.answers,
                   "groups": {g: [names[i] for i in ids] for g, ids in result["groups"].items() if g != "not_eligible" and ids}}
    item = console.QUEUE.add(req.kind, summary, req.lang)
    counters.record_escalation()
    return {"ticket": item["ticket"]}


class SlipRequest(BaseModel):
    kind: Literal["fraud", "scheme"]


@app.post("/api/counters/slip")
def api_count_slip(req: SlipRequest) -> dict[str, Any]:
    counters.record_slip(req.kind)
    return {"ok": True}


CONSOLE_COOKIE = "sahayak_console"


def require_console(request: Request) -> None:
    if not console.auth().check(request.cookies.get(CONSOLE_COOKIE)):
        raise HTTPException(status_code=401, detail="Console login required")


class LoginRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=12)


@app.post("/api/console/login")
def api_console_login(req: LoginRequest, request: Request) -> JSONResponse:
    try:
        token = console.auth().login(req.pin)
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e)) from None
    if token is None:
        raise HTTPException(status_code=401, detail="Wrong PIN")
    res = JSONResponse({"ok": True})
    res.set_cookie(CONSOLE_COOKIE, token, httponly=True, samesite="strict", secure=request.url.scheme == "https",
                   max_age=console.SESSION_TTL, path="/api/console")
    return res


@app.post("/api/console/logout")
def api_console_logout(request: Request) -> JSONResponse:
    console.auth().logout(request.cookies.get(CONSOLE_COOKIE))
    res = JSONResponse({"ok": True})
    res.delete_cookie(CONSOLE_COOKIE, path="/api/console")
    return res


@app.get("/api/console/queue")
def api_console_queue(request: Request) -> dict[str, Any]:
    require_console(request)
    return {"items": console.QUEUE.list()}


class QueueState(BaseModel):
    state: Literal["serving", "done"]


@app.post("/api/console/queue/{ticket}")
def api_console_queue_state(ticket: str, req: QueueState, request: Request) -> dict[str, Any]:
    require_console(request)
    if console.QUEUE.set_state(ticket, req.state) is None:
        raise HTTPException(status_code=404, detail="No such ticket")
    return {"ok": True}


@app.get("/api/console/case/{check_id}")
def api_console_case(check_id: str, request: Request) -> dict[str, Any]:
    """The full verdict card behind a queued check (memory only; gone after 15 minutes)."""
    require_console(request)
    found = RECENT.get(check_id)
    if not found:
        raise HTTPException(status_code=404, detail="Check expired; run it again with the person")
    return found[1]


class CaseRequest(BaseModel):
    consent: bool
    entry: dict[str, Any]


@app.post("/api/console/caselog")
def api_console_caselog_add(req: CaseRequest, request: Request) -> dict[str, Any]:
    require_console(request)
    try:
        return console.caselog().add(req.entry, req.consent)
    except PermissionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


@app.get("/api/console/caselog")
def api_console_caselog(request: Request) -> dict[str, Any]:
    require_console(request)
    return {"entries": console.caselog().list(), "keep_days": console.CASE_DAYS}


@app.post("/api/console/delete-everything")
def api_console_delete_everything(request: Request) -> dict[str, Any]:
    """One control that removes every trace of the people served: case log, queue, recent checks
    and spoken sentences held in memory. Counters hold no personal data and are kept."""
    require_console(request)
    console.caselog().clear()
    console.QUEUE.clear()
    RECENT.clear()
    get_speaker().clear_memory()
    return {"deleted": ["case log", "queue", "recent checks", "speech memory"]}


@app.get("/api/console/counters")
def api_console_counters(request: Request, month: str | None = None) -> dict[str, Any]:
    require_console(request)
    return {"month": month or counters.month(), "counters": counters.view(month),
            "export_rows": counters.export_rows(month)}


@app.get("/api/console/export")
def api_console_export(request: Request, month: str | None = None) -> dict[str, Any]:
    require_console(request)
    text = counters.export_csv(month)
    return {"month": month or counters.month(), "csv": text, **counters.sign(text)}


@app.post("/api/console/counters/reset")
def api_console_counters_reset(request: Request) -> dict[str, Any]:
    require_console(request)
    counters.reset()
    return {"ok": True}


@app.get("/api/console/reference")
def api_console_reference(request: Request) -> dict[str, Any]:
    """Quick reference: this month's most common scam categories first, each with its plain
    explanation and what to tell the person (from the fraud pack)."""
    require_console(request)
    cats = get_pack("fraud").data["categories"]
    seen = counters.view().get("categories", {})
    order = sorted(cats, key=lambda c: (-seen.get(c, 0), -cats[c].get("priority", 0)))
    return {"categories": [{"id": c, "name": cats[c]["name"], "actions": cats[c]["actions"], "seen": seen.get(c, 0)}
                           for c in order if c != "generic"]}


# Node status: zero-egress evidence, installed packs and models with their hashes, and the
# addresses and QR codes for the sticker on the node.

@app.get("/api/egress")
def api_egress() -> dict[str, Any]:
    return egress.snapshot()


@app.get("/api/status")
def api_status() -> dict[str, Any]:
    s = get_settings()
    addresses = lan_addresses()
    if s.tls_cert and s.public_host:
        app_url = f"https://{s.public_host}" + ("" if s.port == 443 else f":{s.port}") + "/"
    else:
        app_url = f"http://{addresses[0] if addresses else '127.0.0.1'}:{s.port}/"
    wifi_ssid = os.environ.get("SAHAYAK_WIFI_SSID", "")
    wifi = None
    if wifi_ssid:
        password = os.environ.get("SAHAYAK_WIFI_PASSWORD", "")
        auth = "WPA" if password else "nopass"
        esc = lambda v: re.sub(r'([\\;,:"])', r"\\\1", v)  # noqa: E731 - Wi-Fi QR escaping
        wifi = {"ssid": wifi_ssid, "qr": qr_data_uri(f"WIFI:T:{auth};S:{esc(wifi_ssid)};" +
                                                     (f"P:{esc(password)};" if password else "") + ";")}
    return {
        "version": __version__, "uptime_s": round(time.time() - STARTED), **node_status.snapshot(),
        "voice": {"tts": get_speaker().voices(), "asr": get_listener().languages()},
        "require_signed": os.environ.get("SAHAYAK_REQUIRE_SIGNED", "0") == "1",
        "app_url": app_url, "app_qr": qr_data_uri(app_url), "wifi": wifi, "lan_addresses": addresses,
        "https": bool(s.tls_cert),
    }


@app.get("/api/voice")
def api_voice() -> dict[str, Any]:
    cache = get_settings().data_dir / "tts_cache"
    return {"tts": get_speaker().voices(), "asr": get_listener().languages(),
            "cached_sentences": len(list(cache.glob("*.wav"))) if cache.is_dir() else 0}


def lan_addresses() -> list[str]:
    out = []
    for name, addrs in psutil.net_if_addrs().items():
        for a in addrs:
            if getattr(a.family, "name", "") == "AF_INET" and not a.address.startswith(("127.", "169.254.")):
                out.append(a.address)
    return out


# ---------------------------------------------------------------- the phone app

settings = get_settings()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(settings.web_dir / "index.html")


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    # Served from the root so the worker can cache the whole app.
    return FileResponse(settings.web_dir / "sw.js", media_type="text/javascript",
                        headers={"Service-Worker-Allowed": "/"})


app.mount("/app", StaticFiles(directory=settings.web_dir), name="app")


@app.exception_handler(404)
async def not_found(request: Request, exc: Exception) -> JSONResponse:
    if request.url.path.startswith("/api/"):
        detail = getattr(exc, "detail", "Not found")
        return JSONResponse({"detail": detail}, status_code=404)
    # Captive-portal probes and unknown paths land on the app.
    return FileResponse(settings.web_dir / "index.html", status_code=200)  # type: ignore[return-value]

