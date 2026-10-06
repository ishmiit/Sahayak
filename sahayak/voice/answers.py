"""Map what was heard to a Benefits Navigator answer.

  ("age", "मेरी उम्र सड़सठ साल है")      -> 67
  ("ration", "अंत्योदय वाला कार्ड है")     -> "aay"
  ("bank", "पता नहीं")                     -> "dont_know"   (the longest keyword wins over "नहीं")
  ("situation", "मैं विधवा हूँ")            -> ["widow"]
  ("money", "दस हज़ार महीना")              -> "le15k"       (a spoken amount is compared with the limit)

Keywords live in the voice pack. Matching is on whole words after the same Hindi folding the
scam checker uses, so spelling variants from the recogniser still match. Nothing here decides
eligibility: the answer goes back through the normal interview, and the phone shows "I heard …,
is that right?" before using it.
"""
from __future__ import annotations

import re
from functools import lru_cache

from ..fraud.normalize import fold
from ..packs import get_pack
from .numbers import parse

INCOME_LIMIT = 15000


@lru_cache(maxsize=1)
def _answers() -> dict:
    return get_pack("voice").data["answers"]


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[\s,।.?!\"'“”‘’()\-]+", fold(text)) if t]


def _found(tokens: list[str], phrase: str) -> int:
    """Length (in characters) of `phrase` if it occurs as whole words in `tokens`, else 0."""
    want = _tokens(phrase)
    n = len(want)
    for i in range(len(tokens) - n + 1):
        if tokens[i:i + n] == want:
            return len(" ".join(want))
    return 0


def keywords(qid: str) -> dict[str, dict[str, list[str]]]:
    spec = _answers().get(qid, {})
    return _answers()[spec] if isinstance(spec, str) else spec


def _best(tokens: list[str], qid: str, lang: str, allowed: set[str]) -> dict[str, int]:
    """Longest keyword match per option."""
    scores: dict[str, int] = {}
    for option, by_lang in keywords(qid).items():
        if option not in allowed:
            continue
        for phrase in by_lang.get(lang, []) + (by_lang.get("en", []) if lang != "en" else []):
            hit = _found(tokens, phrase)
            if hit > scores.get(option, 0):
                scores[option] = hit
    return scores


def grammar(question: dict, lang: str = "hi") -> list[str]:
    """Phrases a short answer to `question` can contain, for grammar-constrained recognition."""
    voice = get_pack("voice").data
    numbers = (voice["numbers"]["hi"] + list(voice["number_variants"]["hi"]) if lang == "hi"
               else voice["numbers"]["en"] + [w for w in voice["numbers"]["en_tens"] if w])
    if question["kind"] == "age":
        return numbers + list(voice["scale_words"][lang])[:1] + voice["age_words"][lang]
    shown = {o["id"] for o in question.get("options", [])} | ({"none"} if question["kind"] == "multi" else set())
    phrases = [p for option, by_lang in keywords(question["id"]).items() if option in shown for p in by_lang.get(lang, [])]
    if question["id"] == "money":
        phrases += numbers + list(voice["scale_words"][lang])
    return sorted(set(phrases))


def match(question: dict, text: str, lang: str = "hi") -> dict | None:
    """`question` is the payload from /api/navigator/next (only its shown options count)."""
    if not text.strip():
        return None
    qid, kind = question["id"], question["kind"]
    if kind == "age":
        n = parse(text, lang)
        return {"answer": n} if n is not None and 0 <= n <= 120 else None

    tokens = _tokens(text)
    shown = {o["id"] for o in question.get("options", [])}
    if kind == "multi":
        scores = _best(tokens, qid, lang, shown | {"none"})
        picked = sorted((o for o in scores if o != "none"), key=[o["id"] for o in question["options"]].index)
        if picked:
            return {"answer": picked}
        return {"answer": []} if "none" in scores else None

    if qid == "money":
        scores = _best(tokens, qid, lang, {"taxpayer", "dont_know"} & shown)
        if scores:
            return {"answer": max(scores, key=scores.get)}
        amount = parse(text, lang)
        if amount is not None and amount >= 100:  # "दस हज़ार", "12000": a monthly income
            return {"answer": "le15k" if amount <= INCOME_LIMIT else "gt15k"}

    scores = _best(tokens, qid, lang, shown)
    if not scores:
        return None
    top = max(scores.values())
    best = [o for o, s in scores.items() if s == top]
    return {"answer": best[0]} if len(best) == 1 else None  # a tie is not an answer
