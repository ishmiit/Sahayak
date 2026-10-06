"""Numbers as words, both ways, in Hindi and English, on the Indian system (lakh, crore).

  words(200, "hi") -> "दो सौ"          words(250000, "en") -> "two lakh fifty thousand"
  parse("मेरी उम्र सड़सठ साल है", "hi") -> 67     parse("sixty seven", "en") -> 67

Amounts are spoken as words because a listener who cannot read hears "do sau rupaye", not
"rupee two zero zero"; ages are heard as words because that is how people say them.
"""
from __future__ import annotations

import re
from functools import lru_cache

from ..fraud.normalize import fold
from ..packs import get_pack


@lru_cache(maxsize=1)
def _data() -> dict:
    return get_pack("voice").data


def _below_100(n: int, lang: str) -> str:
    d = _data()["numbers"]
    if lang == "hi":
        return d["hi"][n]
    if n < 20:
        return d["en"][n]
    tens, ones = divmod(n, 10)
    return d["en_tens"][tens] + (f" {d['en'][ones]}" if ones else "")


def words(n: int, lang: str = "hi") -> str:
    """0 <= n < 1,000,000,000,000 as words."""
    if n < 0:
        raise ValueError("negative numbers are not spoken")
    if n < 100:
        return _below_100(n, lang)
    scale = _data()["scales"][lang]
    parts = []
    for size, name in ((10_000_000, "crore"), (100_000, "lakh"), (1000, "thousand"), (100, "hundred")):
        if n >= size:
            count, n = divmod(n, size)
            parts.append(f"{words(count, lang)} {scale[name]}")
    if n:
        parts.append(_below_100(n, lang))
    return " ".join(parts)


def digits(s: str, lang: str = "hi") -> str:
    """Read a number digit by digit, as people dial it: 1930 -> "एक नौ तीन शून्य"."""
    return " ".join(_below_100(int(c), lang) for c in s if c.isdigit())


@lru_cache(maxsize=2)
def _lexicon(lang: str) -> tuple[dict[str, int], dict[str, int]]:
    d = _data()
    units: dict[str, int] = {}
    if lang == "hi":
        for i, w in enumerate(d["numbers"]["hi"]):
            units[fold(w)] = i
        for w, i in d["number_variants"]["hi"].items():
            units.setdefault(fold(w), i)
    else:
        for i, w in enumerate(d["numbers"]["en"]):
            units[w] = i
        for i, w in enumerate(d["numbers"]["en_tens"]):
            if w:
                units[w] = i * 10
    scales = {fold(w) if lang == "hi" else w: v for w, v in d["scale_words"][lang].items()}
    return units, scales


_DIGITS = re.compile(r"\d[\d,]*")


def parse(text: str, lang: str = "hi") -> int | None:
    """The first number in `text`, written in digits or spoken as words, else None."""
    m = _DIGITS.search(text)
    if m:
        return int(m.group().replace(",", ""))
    units, scales = _lexicon(lang)
    tokens = [fold(t) if lang == "hi" else t for t in re.split(r"[\s\-]+", text.lower()) if t]
    total, current, seen = 0, 0, False
    for tok in tokens:
        if tok in units:
            v = units[tok]
            if not seen:
                current = v
            elif current % 100 == 0 and v < 100:  # "एक सौ बीस", "two hundred thirty", after a scale word
                current += v
            elif lang == "en" and current % 10 == 0 and current % 100 >= 20 and v < 10:  # "sixty seven"
                current += v
            else:
                break  # a second number: keep the first
            seen = True
        elif tok in scales:
            size = scales[tok]
            if not seen:  # "सौ" or "hundred" on its own
                current, seen = size, True
            elif size == 100:
                current = (current or 1) * 100
            else:
                total += (current or 1) * size
                current = 0
        elif seen:
            break
    return total + current if seen else None
