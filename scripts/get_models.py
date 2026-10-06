"""Download the offline speech models into %USERPROFILE%/.sahayak/models (outside OneDrive).

Run once with internet; after that the node never needs it. Each file is fetched from its
publisher's release page, its SHA-256 is printed for the README, and the archive is unpacked.

  speech to text  Vosk small Hindi and small Indian English (Apache-2.0, alphacephei.com)
  text to speech  Piper voices converted for sherpa-onnx (k2-fsa/sherpa-onnx tts-models):
                  Hindi priyamvada (female) and pratham (male), English lessac.
                  The Hindi voices are CC BY-NC-SA 4.0: fine for this non-commercial prototype,
                  not for a commercial deployment (see PROGRESS.md decision D12).
  screenshots     EasyOCR text detector + Devanagari and English recognisers (Apache-2.0)

Usage: python scripts/get_models.py [--big]   (--big adds the 1.5 GB Vosk Hindi model)
"""
from __future__ import annotations

import hashlib
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.config import get_settings  # noqa: E402

TTS = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/"
VOSK = "https://alphacephei.com/vosk/models/"
MODELS = [
    ("vosk-model-small-hi-0.22", VOSK + "vosk-model-small-hi-0.22.zip"),
    ("vosk-model-small-en-in-0.4", VOSK + "vosk-model-small-en-in-0.4.zip"),
    ("vits-piper-hi_IN-priyamvada-medium-int8", TTS + "vits-piper-hi_IN-priyamvada-medium-int8.tar.bz2"),
    ("vits-piper-hi_IN-pratham-medium-int8", TTS + "vits-piper-hi_IN-pratham-medium-int8.tar.bz2"),
    ("vits-piper-en_US-lessac-medium-int8", TTS + "vits-piper-en_US-lessac-medium-int8.tar.bz2"),
]
BIG = [("vosk-model-hi-0.22", VOSK + "vosk-model-hi-0.22.zip")]


def fetch(name: str, url: str, dest: Path) -> None:
    if (dest / name).exists():
        print(f"{name}: already here")
        return
    archive = dest / url.rsplit("/", 1)[1]
    print(f"{name}: downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as r, archive.open("wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
    else:
        with tarfile.open(archive, "r:bz2") as t:
            t.extractall(dest)
    archive.unlink()
    print(f"{name}: ok  sha256 {digest}")


def fetch_ocr(dest: Path) -> None:
    """EasyOCR's text detector and its Devanagari and English recognisers (Apache-2.0), fetched by
    EasyOCR itself; at run time the node loads them with downloads switched off."""
    target = dest / "easyocr"
    if all((target / f).exists() for f in ("craft_mlt_25k.pth", "devanagari.pth", "english_g2.pth")):
        print("easyocr: already here")
        return
    try:
        import easyocr
    except ImportError:
        print("easyocr: skipped (screenshot reading is optional: pip install -r requirements-ocr.txt, then run this again)")
        return
    target.mkdir(parents=True, exist_ok=True)
    easyocr.Reader(["hi", "en"], gpu=False, model_storage_directory=str(target), verbose=False)
    easyocr.Reader(["en"], gpu=False, model_storage_directory=str(target), verbose=False)
    for f in sorted(target.glob("*.pth")):
        print(f"easyocr/{f.name}: ok  sha256 {hashlib.sha256(f.read_bytes()).hexdigest()}")


def main() -> None:
    dest = get_settings().home / "models"
    dest.mkdir(parents=True, exist_ok=True)
    for name, url in MODELS + (BIG if "--big" in sys.argv else []):
        fetch(name, url, dest)
    fetch_ocr(dest)


if __name__ == "__main__":
    main()
