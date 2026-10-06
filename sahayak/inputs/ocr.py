"""Read the text in a screenshot or photo of a message, offline (EasyOCR).

Text boxes are found once, then each box is read by two recognisers: the Devanagari one (Hindi,
with English letters) and the English one, which keeps the punctuation of links ("-", "//",
":") that the Devanagari one drops. A box is kept in Devanagari only when it really is Hindi.
Links broken by the reader are then repaired where it is safe ("spin-win-\\nbonusxyz" ->
"spin-win-bonus.xyz"). The text comes back for the person to look over before it is checked.

Models live in SAHAYAK_HOME/models/easyocr; downloads are switched off at run time, so reading a
screenshot never touches the internet.
"""
from __future__ import annotations

import importlib.util
import re
import threading
import time
from functools import lru_cache

import numpy as np

from ..config import get_settings

MODEL_FILES = ("craft_mlt_25k.pth", "devanagari.pth", "english_g2.pth")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
# endings scam links use most, glued to the word before by a reader that dropped the dot
_TLDS = ("xyz", "site", "click", "top", "online", "info", "link", "live", "shop", "club", "store", "icu", "buzz", "apk",
         "com", "net", "org", "in")
_GLUED_TLD = re.compile(r"(?<![\w.])((?:https?://)?[a-z0-9]+(?:-[a-z0-9]+)+?)(" + "|".join(_TLDS) + r")(?=$|[\s/])", re.I)


_HYPHEN_TLD = re.compile(r"(?<![\w.-])((?:https?://)?[a-z0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*)-(xyz|click|top|site|online|icu|buzz)(?=$|[\s/])", re.I)


class OCRUnavailable(RuntimeError):
    pass


def repair_links(text: str) -> str:
    """Undo the reader's usual damage to links, only where the token is clearly a link."""
    t = re.sub(r"(?i)\b(https?)\s*[:;]\s*/\s*[/Il|1]\s*", r"\1://", text)  # "http:/I" -> "http://"
    # a link broken across lines at a hyphen: "http://spin-win-\nbonusxyz"
    t = re.sub(r"((?:https?://|www\.)?[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-)\s*\n\s*([A-Za-z0-9])", r"\1\2", t)

    def dot(m: re.Match) -> str:
        head, tld = m.group(1), m.group(2)
        return m.group(0) if head.lower().endswith("." + tld.lower()) else f"{head}.{tld}"
    t = _GLUED_TLD.sub(dot, t)
    # "lpg-subsidy-click": two or more hyphens and a scam-favourite ending read as "-" instead of "."
    return _HYPHEN_TLD.sub(lambda m: f"{m.group(1)}.{m.group(2)}", t)


class Reader:
    def __init__(self):
        self._readers = None
        self._lock = threading.Lock()  # one recognition at a time
        self._load_lock = threading.Lock()  # one model load, however many threads ask (start-up warm-up and a request)

    def available(self) -> bool:
        d = get_settings().models_dir / "easyocr"
        return importlib.util.find_spec("easyocr") is not None and all((d / f).exists() for f in MODEL_FILES)

    def _load(self):
        with self._load_lock:
            if self._readers is None:
                if importlib.util.find_spec("easyocr") is None:
                    raise OCRUnavailable("screenshot reading is not installed (pip install -r requirements-ocr.txt)")
                if not self.available():
                    raise OCRUnavailable("text-reading models are not installed (python scripts/get_models.py)")
                import easyocr  # imported late: heavy, and the node runs without it too
                import torch
                torch.set_num_threads(2)  # leave cores for speech and the model
                d = str(get_settings().models_dir / "easyocr")
                kw = dict(gpu=False, verbose=False, download_enabled=False, model_storage_directory=d)
                self._readers = (easyocr.Reader(["hi", "en"], **kw), easyocr.Reader(["en"], detector=False, **kw))
        return self._readers

    def read(self, image: bytes) -> dict:
        import cv2
        img = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("not an image")
        h, w = img.shape[:2]
        if max(h, w) > 1800:
            scale = 1800 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        t0 = time.perf_counter()
        with self._lock:
            hi, en = self._load()
            horizontal, free = hi.detect(img)
            horizontal, free = horizontal[0], free[0]
            boxes_hi = hi.recognize(img, horizontal_list=horizontal, free_list=free, detail=1, paragraph=False)
            boxes_en = en.recognize(img, horizontal_list=horizontal, free_list=free, detail=1, paragraph=False)
        boxes = []
        for b_hi, b_en in zip(boxes_hi, boxes_en):
            text_hi = b_hi[1]
            letters = [c for c in text_hi if c.isalpha()]
            hindi = letters and sum(bool(_DEVANAGARI.match(c)) for c in letters) / len(letters) >= 0.3
            boxes.append(b_hi if hindi else b_en)
        text = repair_links(repair_capitals(_lines(boxes)))
        return {"text": text, "boxes": len(boxes), "ms": round((time.perf_counter() - t0) * 1000)}


def _lines(boxes: list) -> str:
    """Group recognised words into lines (by vertical position), left to right, and lines into paragraphs.

    A line that starts right under the previous one, at the same left edge, is the same paragraph
    wrapped by the screen, so it is joined with a space: the checks read a line break as the end of
    a sentence, and "Never / share it with anyone" must stay one warning. A bigger gap (the sender
    above the bubble, a blank line, the next message) keeps the break.
    """
    items = []
    for box, text, conf in boxes:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append((min(ys), max(ys), min(xs), text.strip()))
    items.sort(key=lambda i: (i[0], i[2]))
    lines: list[list] = []  # [top, bottom, left, words]
    for top, bottom, left, text in items:
        if lines and top < lines[-1][1] - 0.35 * (lines[-1][1] - lines[-1][0]):  # overlaps the current line
            lines[-1][3].append((left, text))
            lines[-1][1] = max(lines[-1][1], bottom)
            lines[-1][2] = min(lines[-1][2], left)
        else:
            lines.append([top, bottom, left, [(left, text)]])
    out, prev = "", None
    for top, bottom, left, words in lines:
        text = " ".join(t for _, t in sorted(words))
        height = bottom - top if prev is None else min(bottom - top, prev[1] - prev[0])
        if prev is not None and top - prev[1] <= 0.35 * height and abs(left - prev[2]) <= height:
            out += ("" if out.endswith(("-", "/")) else " ") + text  # wrapped by the screen
        else:
            out += ("\n" if out else "") + text
        prev = (top, bottom, left)
    return out.strip()


# Inside capitals OCR reads a capital I as a small l ("SBl", "UPl PlN"); the checks look for SBI, UPI, PIN.
_CAPS_WITH_L = re.compile(r"\b[A-Zl]{3,}\b")


def repair_capitals(text: str) -> str:
    return _CAPS_WITH_L.sub(lambda m: m.group().replace("l", "I") if sum(c.isupper() for c in m.group()) >= 2 else m.group(), text)


@lru_cache(maxsize=1)
def get_reader() -> Reader:
    return Reader()
