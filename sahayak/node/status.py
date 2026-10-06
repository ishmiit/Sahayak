"""What is installed on this node, with hashes a jury member can check against the README:
content packs (version, date, SHA-256, who signed them), speech models (a SHA-256 per model
folder) and the local language model (its digest as reported by the local runtime)."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import httpx

from ..config import get_settings
from ..packs import installed_packs


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def speech_models() -> list[dict]:
    """One SHA-256 per model folder: the hash of its files' relative paths and hashes, in order.
    Cached by file sizes and times, so only a changed model is hashed again."""
    s = get_settings()
    if not s.models_dir.is_dir():
        return []
    cache_file = s.data_dir / "model_hashes.json"
    try:
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    out, changed = [], False
    for d in sorted(p for p in s.models_dir.iterdir() if p.is_dir()):
        files = sorted(f for f in d.rglob("*") if f.is_file())
        stamp = hashlib.sha256("\n".join(f"{f.relative_to(d).as_posix()}:{f.stat().st_size}:{int(f.stat().st_mtime)}"
                                          for f in files).encode()).hexdigest()
        entry = cache.get(d.name)
        if not entry or entry.get("stamp") != stamp:
            h = hashlib.sha256()
            for f in files:
                h.update(f.relative_to(d).as_posix().encode())
                h.update(_file_sha256(f).encode())
            entry = {"stamp": stamp, "sha256": h.hexdigest(), "files": len(files), "bytes": sum(f.stat().st_size for f in files)}
            cache[d.name] = entry
            changed = True
        out.append({"name": d.name, "sha256": entry["sha256"], "files": entry["files"], "mb": round(entry["bytes"] / 1e6, 1)})
    if changed:
        s.data_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return out


_llm_cache: dict = {"at": 0.0, "value": None}


def llm_model() -> dict:
    """The local model's name and digest, from the local runtime (Ollama), cached for a minute."""
    s = get_settings()
    if time.time() - _llm_cache["at"] < 60 and _llm_cache["value"] is not None:
        return _llm_cache["value"]
    value = {"backend": s.llm_backend, "model": s.llm_model, "digest": None}
    if s.llm_backend == "ollama":
        try:
            tags = httpx.get(f"{s.llm_url}/api/tags", timeout=3).json()  # llm_url is checked to be local
            for m in tags.get("models", []):
                if m.get("name") == s.llm_model or m.get("model") == s.llm_model:
                    value.update(digest=m.get("digest"), size_mb=round(m.get("size", 0) / 1e6))
        except (httpx.HTTPError, ValueError):
            value["digest"] = None
    _llm_cache.update(at=time.time(), value=value)
    return value


def snapshot() -> dict:
    return {"packs": installed_packs(), "speech_models": speech_models(), "llm": llm_model()}
