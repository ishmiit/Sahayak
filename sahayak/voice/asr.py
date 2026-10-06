"""Offline speech to text on the node (Vosk, Kaldi models, Apache-2.0).

The phone records 16 kHz mono PCM itself (web/recorder.js) and posts a WAV, so the node
never needs ffmpeg. A short answer to a known question can be recognised against a small
grammar (the answer's keywords and number words), which is far more reliable than open
dictation for "हाँ", "अंत्योदय" or "सड़सठ". Audio is processed in memory and never stored.
"""
from __future__ import annotations

import io
import json
import threading
import time
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..config import get_settings

MODELS = {"hi": "vosk-model-small-hi-0.22", "en": "vosk-model-small-en-in-0.4"}
RATE = 16000
MAX_SECONDS = 30


class ASRUnavailable(RuntimeError):
    pass


class AudioError(ValueError):
    pass


def read_audio(data: bytes) -> tuple[bytes, float]:
    """16 kHz mono PCM from a recording. WAV (what the app's own recorder sends) is read directly;
    anything else (m4a, aac, amr, ogg, webm from a phone's recorder app, used where the browser
    will not open the mic) is decoded with PyAV."""
    if data[:4] == b"RIFF":
        return read_wav(data)
    try:
        import av
    except ImportError:
        raise AudioError("only WAV is supported on this node (PyAV is not installed)") from None
    try:
        with av.open(io.BytesIO(data)) as container:
            stream = next((s for s in container.streams if s.type == "audio"), None)
            if stream is None:
                raise AudioError("no audio in the file")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=RATE)
            chunks, samples = [], 0
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    chunk = out.to_ndarray().reshape(-1).astype("<i2")
                    chunks.append(chunk)
                    samples += len(chunk)
                    if samples > RATE * MAX_SECONDS:
                        raise AudioError(f"recording longer than {MAX_SECONDS} s")
            for out in resampler.resample(None):  # flush
                chunks.append(out.to_ndarray().reshape(-1).astype("<i2"))
    except AudioError:
        raise
    except Exception as e:  # noqa: BLE001 - any decoder failure is a bad upload
        raise AudioError(f"could not decode the recording: {e}") from None
    pcm = np.concatenate(chunks) if chunks else np.zeros(0, dtype="<i2")
    return pcm.tobytes(), len(pcm) / RATE


def read_wav(data: bytes) -> tuple[bytes, float]:
    """Mono 16-bit PCM at 16 kHz (resampled if it is not), and its duration in seconds."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.readframes(w.getnframes())
    except (wave.Error, EOFError) as e:
        raise AudioError(f"not a WAV file: {e}") from None
    if width != 2:
        raise AudioError("expected 16-bit PCM")
    x = np.frombuffer(frames, dtype="<i2")
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1).astype("<i2")
    if rate != RATE:
        n = int(len(x) * RATE / rate)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype("<i2")
    seconds = len(x) / RATE
    if seconds > MAX_SECONDS:
        raise AudioError(f"recording longer than {MAX_SECONDS} s")
    return x.tobytes(), seconds


class Listener:
    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self._models: dict[str, object] = {}
        self._lock = threading.Lock()

    def languages(self) -> list[str]:
        return [lang for lang, d in MODELS.items() if (self.models_dir / d).is_dir()]

    def _model(self, lang: str):
        with self._lock:
            if lang not in self._models:
                if lang not in MODELS or not (self.models_dir / MODELS[lang]).is_dir():
                    raise ASRUnavailable(f"no speech model for '{lang}' (python scripts/get_models.py)")
                from vosk import Model, SetLogLevel  # imported late: the node runs without it too
                SetLogLevel(-1)
                self._models[lang] = Model(str(self.models_dir / MODELS[lang]))
            return self._models[lang]

    def transcribe(self, pcm: bytes, lang: str = "hi", grammar: list[str] | None = None) -> dict:
        from vosk import KaldiRecognizer
        model = self._model(lang)
        t0 = time.perf_counter()
        rec = KaldiRecognizer(model, RATE, json.dumps(grammar + ["[unk]"], ensure_ascii=False)) if grammar \
            else KaldiRecognizer(model, RATE)
        rec.SetWords(True)
        rec.AcceptWaveform(pcm)
        out = json.loads(rec.FinalResult())
        words = [w for w in out.get("result", []) if w.get("word") != "[unk]"]
        text = " ".join(w["word"] for w in words) if grammar else out.get("text", "")
        conf = float(np.mean([w.get("conf", 0.0) for w in words])) if words else 0.0
        return {"text": text.strip(), "confidence": round(conf, 3), "ms": round((time.perf_counter() - t0) * 1000),
                "grammar": bool(grammar)}


@lru_cache(maxsize=1)
def get_listener() -> Listener:
    return Listener(get_settings().models_dir)
