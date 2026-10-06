"""Similarity to known scams (the scam pattern pack).

TF-IDF over character 3-5 grams of the folded text, so it survives typos, Hinglish
spellings and look-alike letters. A close match fires `pattern_match` with the matched
scam's category, which also helps name the scam on the verdict card.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from ..packs import get_pack
from .normalize import fold


@dataclass
class PatternHit:
    score: float
    category: str
    pattern_id: str


class PatternMatcher:
    def __init__(self, patterns: list[dict], threshold: float):
        self.threshold = threshold
        self.ids = [p["id"] for p in patterns]
        self.categories = [p["category"] for p in patterns]
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform([fold(p["text"]) for p in patterns])

    def best(self, norm_text: str) -> PatternHit | None:
        sims = linear_kernel(self.vectorizer.transform([norm_text]), self.matrix).ravel()
        i = int(sims.argmax())
        return PatternHit(float(sims[i]), self.categories[i], self.ids[i])

    def match(self, norm_text: str) -> PatternHit | None:
        hit = self.best(norm_text)
        return hit if hit and hit.score >= self.threshold else None


@lru_cache(maxsize=1)
def get_matcher() -> PatternMatcher | None:
    try:
        pack = get_pack("scam_patterns").data
    except FileNotFoundError:
        return None
    return PatternMatcher(pack["patterns"], float(pack.get("threshold", 0.5)))
