"""Offline text to speech on the node: Piper voices run by sherpa-onnx.

Fixed sentences from the packs (verdicts, reasons, actions, questions, scheme names) are
synthesised ahead of time by scripts/build_speech_cache.py and play instantly from disk.
Anything else is synthesised live, at about half real time on the dev laptop's CPU, and kept
only in memory: text derived from a person's message is never written to disk.
"""
from __future__ import annotations

import hashlib
import io
import threading
import time
import wave
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..config import get_settings
from .speech import speakable

VOICES = {
    "hi": {"female": "vits-piper-hi_IN-priyamvada-medium-int8", "male": "vits-piper-hi_IN-pratham-medium-int8"},
    "en": {"female": "vits-piper-en_US-lessac-medium-int8", "male": "vits-piper-en_US-lessac-medium-int8"},
}


class TTSUnavailable(RuntimeError):
    pass


def to_wav(samples: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes())
    return buf.getvalue()


class Speaker:
    def __init__(self, models_dir: Path, cache_dir: Path, threads: int = 4):
        self.models_dir, self.cache_dir, self.threads = models_dir, cache_dir, threads
        self._engines: dict[str, object] = {}
        self._lock = threading.Lock()
        self._memory: OrderedDict[str, bytes] = OrderedDict()

    def voices(self) -> dict[str, list[str]]:
        return {lang: sorted({v for v, d in by.items() if (self.models_dir / d).is_dir()})
                for lang, by in VOICES.items()}

    def _engine(self, model: str):
        with self._lock:
            if model not in self._engines:
                import sherpa_onnx  # imported late: the node runs without voice models too
                d = self.models_dir / model
                onnx = next(d.glob("*.onnx"), None)
                if onnx is None:
                    raise TTSUnavailable(f"voice model {model} is not installed (python scripts/get_models.py)")
                cfg = sherpa_onnx.OfflineTtsConfig(
                    model=sherpa_onnx.OfflineTtsModelConfig(
                        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                            model=str(onnx), tokens=str(d / "tokens.txt"), data_dir=str(d / "espeak-ng-data")),
                        num_threads=self.threads, provider="cpu"),
                    max_num_sentences=1)
                self._engines[model] = (sherpa_onnx.OfflineTts(cfg), threading.Lock())
            return self._engines[model]

    def clear_memory(self) -> None:
        """Forget live-synthesised sentences (they may echo what a person said)."""
        self._memory.clear()

    @staticmethod
    def key(model: str, speed: float, spoken: str) -> str:
        return hashlib.sha256(f"{model}|{speed:.2f}|{spoken}".encode("utf-8")).hexdigest()[:40]

    def synth(self, text: str, lang: str = "hi", voice: str = "female", speed: float = 0.9,
              store: bool = False) -> tuple[bytes, dict]:
        """WAV bytes for `text`. `store=True` (template sentences only) writes the disk cache."""
        if lang not in VOICES:
            raise TTSUnavailable(f"no voice for language '{lang}'")
        model = VOICES[lang].get(voice) or VOICES[lang]["female"]
        # A final full stop changes nothing audible, so "हाँ" and "हाँ।" share one cached clip.
        spoken = speakable(text, lang).rstrip("।. ")
        if not spoken:
            raise TTSUnavailable("nothing to say")
        key = self.key(model, speed, spoken)
        path = self.cache_dir / f"{key}.wav"
        t0 = time.perf_counter()
        if path.exists():
            return path.read_bytes(), {"cached": "disk", "ms": round((time.perf_counter() - t0) * 1000, 1), "spoken": spoken}
        if key in self._memory:
            self._memory.move_to_end(key)
            return self._memory[key], {"cached": "memory", "ms": 0.0, "spoken": spoken}
        engine, lock = self._engine(model)
        with lock:
            audio = engine.generate(spoken, sid=0, speed=speed)
        wav = to_wav(np.asarray(audio.samples, dtype=np.float32), audio.sample_rate)
        if store:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(wav)
            tmp.replace(path)
        else:
            self._memory[key] = wav
            while len(self._memory) > 64:
                self._memory.popitem(last=False)
        return wav, {"cached": "no", "ms": round((time.perf_counter() - t0) * 1000, 1), "spoken": spoken}


@lru_cache(maxsize=1)
def get_speaker() -> Speaker:
    s = get_settings()
    return Speaker(s.models_dir, s.data_dir / "tts_cache")
