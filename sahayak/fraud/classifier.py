"""Calibrated scam classifier: logistic regression over hashed character n-grams plus the
fired signals. Trained by bench/train_classifier.py on the ScamBench train split and
shipped as plain JSON weights (no pickles), so it can live in a signed content pack.

It never decides alone: above its threshold it fires `classifier_flag`, one more
weighted signal in the explainable score.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from ..packs import get_pack

N_FEATURES = 2 ** 16


def make_vectorizer() -> HashingVectorizer:
    return HashingVectorizer(analyzer="char_wb", ngram_range=(2, 5), n_features=N_FEATURES,
                             alternate_sign=False, norm="l2")


def signal_vector(signal_ids: list[str], fired_ids: set[str]) -> np.ndarray:
    return np.array([1.0 if s in fired_ids else 0.0 for s in signal_ids])


class ScamClassifier:
    def __init__(self, model: dict[str, Any]):
        self.signal_ids = model["signal_ids"]
        self.threshold = float(model["threshold"])
        self.intercept = float(model["intercept"])
        self.text_coef = {int(k): float(v) for k, v in model["text_coef"].items()}
        self.signal_coef = np.array(model["signal_coef"], dtype=float)
        self.vectorizer = make_vectorizer()

    def probability(self, norm_text: str, fired_ids: set[str]) -> float:
        x = self.vectorizer.transform([norm_text])
        z = self.intercept
        for idx, val in zip(x.indices, x.data):
            z += self.text_coef.get(int(idx), 0.0) * float(val)
        z += float(self.signal_coef @ signal_vector(self.signal_ids, fired_ids))
        return 1.0 / (1.0 + math.exp(-z))


@lru_cache(maxsize=1)
def get_classifier() -> ScamClassifier | None:
    try:
        return ScamClassifier(get_pack("fraud_model").data)
    except FileNotFoundError:
        return None
