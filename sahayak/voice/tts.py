"""Offline text to speech on the node: Piper voices run by sherpa-onnx.

Fixed sentences from the packs (verdicts, reasons, actions, questions, scheme names) are
synthesised ahead of time by scripts/build_speech_cache.py and play instantly from disk.
Anything else is synthesised live, at about half real time on the dev laptop's CPU, and kept
only in memory: text derived from a person's message is never written to disk.
"""
from __future__ import annotations

import hashlib
import io
import os
import threading
import time
import wave
from collections import OrderedDict
from concurrent.futures import Future
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


class _Engines:
    """Engines for one voice model. It starts with one; while every engine is busy and another
    phone is waiting, it adds one, up to `size`. With many phones at once, several small engines
    beat one large one: on the dev laptop (8 cores), 16 waiting sentences took 3.5 s with four
    1-thread engines and 7.0 s with one 4-thread engine, while a single sentence takes about the
    same either way (0.63 s vs 0.53 s). Each extra engine holds about 110 MB."""

    def __init__(self, make, size: int):
        self.make, self.size = make, size
        self.idle: list = []
        self.count = 0
        self.cond = threading.Condition()

    def acquire(self):
        with self.cond:
            while True:
                if self.idle:
                    return self.idle.pop()
                if self.count < self.size:
                    self.count += 1
                    break
                self.cond.wait()
        try:  # loading takes a second; other phones keep using the engines already there
            return self.make()
        except BaseException:
            with self.cond:
                self.count -= 1
                self.cond.notify()
            raise

    def release(self, engine) -> None:
        with self.cond:
            self.idle.append(engine)
            self.cond.notify()


class Speaker:
    def __init__(self, models_dir: Path, cache_dir: Path, threads: int | None = None, engines: int | None = None):
        cpus = os.cpu_count() or 2
        self.engines = engines or int(os.environ.get("SAHAYAK_TTS_ENGINES", "0") or 0) or max(1, min(4, cpus // 2))
        self.threads = threads or max(1, cpus // (2 * self.engines))
        self.models_dir, self.cache_dir = models_dir, cache_dir
        self._pools: dict[str, _Engines] = {}
        self._lock = threading.Lock()
        self._memory: OrderedDict[str, bytes] = OrderedDict()
        self._inflight: dict[str, Future] = {}

    def voices(self) -> dict[str, list[str]]:
        return {lang: sorted({v for v, d in by.items() if (self.models_dir / d).is_dir()})
                for lang, by in VOICES.items()}

    def _make(self, model: str):
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
        return sherpa_onnx.OfflineTts(cfg)

    def _pool(self, model: str) -> _Engines:
        with self._lock:
            if model not in self._pools:
                self._pools[model] = _Engines(lambda: self._make(model), self.engines)
            return self._pools[model]

    def clear_memory(self) -> None:
        """Forget live-synthesised sentences (they may echo what a person said)."""
        with self._lock:
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
        with self._lock:
            if key in self._memory:
                self._memory.move_to_end(key)
                return self._memory[key], {"cached": "memory", "ms": 0.0, "spoken": spoken}
            # When several phones ask for the same sentence at once (a jury table trying the same
            # card), it is synthesised once and every one of them gets that clip.
            waiting = self._inflight.get(key)
            if waiting is None:
                self._inflight[key] = mine = Future()
        if waiting is not None:
            wav = waiting.result()
            return wav, {"cached": "shared", "ms": round((time.perf_counter() - t0) * 1000, 1), "spoken": spoken}
        try:
            pool = self._pool(model)
            engine = pool.acquire()
            try:
                audio = engine.generate(spoken, sid=0, speed=speed)
            finally:
                pool.release(engine)
            wav = to_wav(np.asarray(audio.samples, dtype=np.float32), audio.sample_rate)
            if store:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(wav)
                tmp.replace(path)
            else:
                with self._lock:
                    self._memory[key] = wav
                    while len(self._memory) > 64:
                        self._memory.popitem(last=False)
            mine.set_result(wav)
        except BaseException as e:
            mine.set_exception(e)
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)
        return wav, {"cached": "no", "ms": round((time.perf_counter() - t0) * 1000, 1), "spoken": spoken}


@lru_cache(maxsize=1)
def get_speaker() -> Speaker:
    s = get_settings()
    return Speaker(s.models_dir, s.data_dir / "tts_cache")
