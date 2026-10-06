"""One interface over local model runtimes.

- OllamaBackend: Ollama's /api/chat with a JSON schema in `format` (the dev laptop).
- OpenAIBackend: any server speaking the OpenAI chat API: llama.cpp's llama-server,
  or Crucible if it exposes the same endpoint.
- NullBackend: no model; Sahayak uses its template explanations.

Endpoints must be loopback or private-network addresses: the node never sends a
prompt to the internet, and this module refuses to be pointed at a public host.
"""
from __future__ import annotations

import ipaddress
import json
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import httpx

from ..config import get_settings


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class LLMResult:
    data: dict[str, Any]
    raw: str
    completion_tokens: int
    seconds: float

    @property
    def tokens_per_s(self) -> float | None:
        return round(self.completion_tokens / self.seconds, 1) if self.seconds > 0 and self.completion_tokens else None


def assert_local(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host in ("localhost",):
        return
    try:
        ip = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError(f"LLM endpoint must be a loopback or private IP literal, not '{host}'") from exc
    if not (ip.is_loopback or ip.is_private or ip.is_link_local):
        raise ValueError(f"LLM endpoint {host} is a public address; the node must stay offline")


class NullBackend:
    name = "none"

    def __init__(self, model: str = "", url: str = ""):
        self.model, self.url = model, url

    def info(self) -> dict[str, Any]:
        return {"backend": self.name, "model": None, "available": False}

    def chat_json(self, system: str, user: str, schema: dict, max_tokens: int = 300,
                  temperature: float = 0.2, timeout: float = 30.0) -> LLMResult:
        raise LLMUnavailable("No LLM backend configured")


class OllamaBackend:
    name = "ollama"

    def __init__(self, model: str, url: str):
        assert_local(url)
        self.model, self.url = model, url

    def info(self) -> dict[str, Any]:
        try:
            r = httpx.get(f"{self.url}/api/tags", timeout=2.0)
            names = [m.get("name") for m in r.json().get("models", [])]
            return {"backend": self.name, "model": self.model, "available": self.model in names}
        except Exception as exc:  # noqa: BLE001 - report, never crash the health check
            return {"backend": self.name, "model": self.model, "available": False, "error": type(exc).__name__}

    def chat_json(self, system: str, user: str, schema: dict, max_tokens: int = 300,
                  temperature: float = 0.2, timeout: float = 30.0) -> LLMResult:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "format": schema,
            "keep_alive": "30m",
            # repeat_penalty stops small models looping inside a JSON string until the token cap
            "options": {"temperature": temperature, "num_predict": max_tokens, "repeat_penalty": 1.3},
        }
        t0 = time.perf_counter()
        try:
            r = httpx.post(f"{self.url}/api/chat", json=body, timeout=timeout)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"Ollama call failed: {type(exc).__name__}") from exc
        payload = r.json()
        raw = payload.get("message", {}).get("content", "")
        eval_ns = payload.get("eval_duration") or 0
        return LLMResult(
            data=_parse_json(raw),
            raw=raw,
            completion_tokens=int(payload.get("eval_count") or 0),
            seconds=eval_ns / 1e9 if eval_ns else time.perf_counter() - t0,
        )


class OpenAIBackend:
    """llama.cpp's llama-server, or Crucible exposing /v1/chat/completions."""

    name = "openai"

    def __init__(self, model: str, url: str):
        assert_local(url)
        self.model, self.url = model, url

    def info(self) -> dict[str, Any]:
        try:
            r = httpx.get(f"{self.url}/v1/models", timeout=2.0)
            ids = [m.get("id") for m in r.json().get("data", [])]
            return {"backend": self.name, "model": self.model or (ids[0] if ids else None), "available": bool(ids)}
        except Exception as exc:  # noqa: BLE001
            return {"backend": self.name, "model": self.model, "available": False, "error": type(exc).__name__}

    def chat_json(self, system: str, user: str, schema: dict, max_tokens: int = 300,
                  temperature: float = 0.2, timeout: float = 30.0) -> LLMResult:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}},
        }
        t0 = time.perf_counter()
        try:
            r = httpx.post(f"{self.url}/v1/chat/completions", json=body, timeout=timeout)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"OpenAI-style call failed: {type(exc).__name__}") from exc
        payload = r.json()
        raw = payload["choices"][0]["message"]["content"]
        timings = payload.get("timings") or {}
        tokens = int((payload.get("usage") or {}).get("completion_tokens") or timings.get("predicted_n") or 0)
        seconds = (timings.get("predicted_ms") or 0) / 1000 or (time.perf_counter() - t0)
        return LLMResult(data=_parse_json(raw), raw=raw, completion_tokens=tokens, seconds=seconds)


def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise LLMUnavailable("Model did not return JSON")
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMUnavailable("Model returned malformed JSON") from exc


@lru_cache(maxsize=1)
def get_backend():
    s = get_settings()
    if s.llm_backend == "ollama":
        return OllamaBackend(s.llm_model, s.llm_url)
    if s.llm_backend in ("openai", "llamacpp", "crucible"):
        return OpenAIBackend(s.llm_model, s.llm_url)
    return NullBackend()
