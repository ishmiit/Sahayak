"""Runtime settings, read once from environment variables.

Models and runtime data (case log, counters) live under SAHAYAK_HOME, outside the
repository, so multi-GB weights and personal data never land in a synced folder.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    home: Path
    host: str
    port: int
    # "ollama" | "openai" (llama.cpp server, or Crucible exposing the same API) | "none"
    llm_backend: str
    llm_url: str
    llm_model: str
    llm_timeout_s: float
    # Languages the model may write explanations in. A language is added only after the
    # model passes a quality check in it; the others always use the vetted templates.
    llm_langs: tuple[str, ...]
    packs_dir: Path
    web_dir: Path
    console_dir: Path
    models_dir: Path  # speech and language models; SAHAYAK_MODELS, else SAHAYAK_HOME/models
    # VoiceBench recording (consented speech samples for the benchmark) is off unless asked for.
    voicebench: bool = False
    # HTTPS: a real certificate for a team-owned domain (obtained online beforehand). With both
    # set, the node serves HTTPS on `port` and redirects plain HTTP on `http_port` to it, which is
    # also what makes phones' captive-portal checks open the app.
    tls_cert: str = ""
    tls_key: str = ""
    public_host: str = ""
    http_port: int = 80

    @property
    def data_dir(self) -> Path:
        return self.home / "data"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    home = Path(_env("SAHAYAK_HOME", str(Path.home() / ".sahayak")))
    backend = _env("SAHAYAK_LLM", "none").lower()  # off by default: the vetted templates read better (D20)
    default_url = "http://127.0.0.1:11434" if backend == "ollama" else "http://127.0.0.1:8081"
    return Settings(
        home=home,
        host=_env("SAHAYAK_HOST", "0.0.0.0"),
        port=int(_env("SAHAYAK_PORT", "8000")),
        llm_backend=backend,
        llm_url=_env("SAHAYAK_LLM_URL", default_url).rstrip("/"),
        llm_model=_env("SAHAYAK_LLM_MODEL", "qwen2.5:3b"),
        llm_timeout_s=float(_env("SAHAYAK_LLM_TIMEOUT", "60")),
        llm_langs=tuple(x.strip() for x in _env("SAHAYAK_LLM_LANGS", "en").split(",") if x.strip()),
        packs_dir=Path(_env("SAHAYAK_PACKS", str(REPO_ROOT / "packs"))),
        web_dir=REPO_ROOT / "web",
        console_dir=REPO_ROOT / "console",
        models_dir=Path(_env("SAHAYAK_MODELS", str(home / "models"))),
        voicebench=_env("SAHAYAK_VOICEBENCH", "0") == "1",
        tls_cert=_env("SAHAYAK_TLS_CERT", ""),
        tls_key=_env("SAHAYAK_TLS_KEY", ""),
        public_host=_env("SAHAYAK_PUBLIC_HOST", ""),
        http_port=int(_env("SAHAYAK_HTTP_PORT", "80")),
    )
