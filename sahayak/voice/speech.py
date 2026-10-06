"""Turn display text into text a voice can say well.

  "₹2 लाख का बीमा, ₹20 साल"   -> "दो लाख रुपये का बीमा, बीस रुपये साल"
  "1930 पर कॉल करें"            -> "एक नौ तीन शून्य पर कॉल करें"
  "उम्र 18 से 70 साल · OTP"     -> "उम्र अठारह से सत्तर साल, ओ टी पी"

Amounts become words with the currency spoken, helplines are read digit by digit,
acronyms are spelled the way people say them, and symbols that a voice would read out
(·, —, /, brackets) become pauses or words. Everything language-specific is in the voice pack.
"""
from __future__ import annotations

import re
from functools import lru_cache

from ..packs import get_pack
from .numbers import digits, words


@lru_cache(maxsize=1)
def _data() -> dict:
    return get_pack("voice").data


_AMOUNT = re.compile(r"₹\s?(\d[\d,]*)(\s?(?:लाख|lakh|करोड़|crore))?(\+)?")
_RANGE_DASH = re.compile(r"(?<=\d)\s?[–-]\s?(?=₹?\d)")
_PERCENT = re.compile(r"(\d+)\s?%")
_NUMBER = re.compile(r"\d[\d,]*")
_URL = re.compile(r"https?://\S+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?", re.I)
_OFFICIAL = re.compile(r"(?:^|\.)(?:gov\.in|nic\.in|bank\.in)$", re.I)
_LATIN = re.compile(r"[A-Za-z][A-Za-z.\-]*[A-Za-z]|[A-Za-z]")


def _amount(m: re.Match, lang: str) -> str:
    d = _data()
    n = int(m.group(1).replace(",", ""))
    scale = (m.group(2) or "").strip()
    spoken = words(n, lang)
    if scale:
        spoken += " " + (d["scales"][lang]["lakh"] if scale in ("लाख", "lakh") else d["scales"][lang]["crore"])
    spoken += " " + d["currency"][lang]
    if m.group(3):
        spoken += " से ज़्यादा" if lang == "hi" else " or more"
    return spoken


def _number(m: re.Match, lang: str) -> str:
    raw = m.group().replace(",", "")
    if raw in _data()["read_as_digits"] or len(raw) >= 6 or (raw.startswith("0") and len(raw) > 1):
        return digits(raw, lang)  # helplines, phone numbers, codes
    return words(int(raw), lang)


def _url(m: re.Match, lang: str) -> str:
    """Official addresses are spoken (people need to hear where to go); any other link is
    just "a link", so the voice never reads a scam address out as if it were advice."""
    host = re.sub(r"^https?://", "", m.group(), flags=re.I).split("/")[0].lower().rstrip(".")
    if _OFFICIAL.search(host):
        return f" {_data()['dot'][lang]} ".join(host.split("."))
    return "एक लिंक" if lang == "hi" else "a link"


def _latin(m: re.Match, lang: str) -> str:
    """Latin words inside Hindi text: known words by the pack's list, acronyms letter by letter."""
    token = m.group()
    known = _data()["words"][lang]
    key = re.sub(r"[.\-]", "", token).lower()
    if key in known:
        return known[key]
    if lang == "en":
        return " ".join(token) if token.isupper() and 1 < len(token) <= 6 else token
    letters = _data()["letters"]["hi"]
    if token.isupper() or len(key) <= 3:
        return " ".join(letters.get(c.upper(), c) for c in key)
    return token  # an English word we do not know: leave it to the voice


def speakable(text: str, lang: str = "hi") -> str:
    d = _data()
    s = text.replace("…", "")
    s = _RANGE_DASH.sub(f" {d['range'][lang]} ", s)
    s = _AMOUNT.sub(lambda m: _amount(m, lang), s)
    s = _PERCENT.sub(lambda m: f"{words(int(m.group(1)), lang)} {d['percent'][lang]}", s)
    s = _URL.sub(lambda m: _url(m, lang), s)
    s = _NUMBER.sub(lambda m: _number(m, lang), s)
    s = re.sub(r"\s*[·•|]\s*", ", ", s)
    s = re.sub(r"\s*[—–]\s*", ", ", s)
    s = re.sub(r"\s*/\s*", f" {d['or'][lang]} ", s)
    s = re.sub(r"\s*[()]\s*", ", ", s)
    s = re.sub(r"[“”\"'‘’]", "", s)
    s = _LATIN.sub(lambda m: _latin(m, lang), s)
    s = re.sub(r"\s*,\s*(,\s*)+", ", ", s)
    s = re.sub(r"\s+([,।.?!])", r"\1", s)
    return re.sub(r"\s{2,}", " ", s).strip(" ,")


_SENTENCE_END = re.compile(r"(?<=[।.?!])\s+")


def sentences(text: str, max_chars: int = 220) -> list[str]:
    """Split for speaking: the first sentence starts playing while the next is synthesised."""
    out = []
    for part in _SENTENCE_END.split(text.strip()):
        part = part.strip()
        while len(part) > max_chars:  # a long sentence: break at the last comma before the limit
            cut = part.rfind(",", 0, max_chars)
            cut = cut if cut > 40 else max_chars
            out.append(part[:cut + 1].strip())
            part = part[cut + 1:].strip()
        if part:
            out.append(part)
    return out
