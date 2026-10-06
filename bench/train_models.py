"""Build the scam pattern pack and train the classifier from ScamBench (train split only).

  packs/scam_patterns.v1.json  known-scam texts from the TRAIN split, with categories
  packs/fraud_model.v1.json    logistic regression weights (JSON, no pickles)

Thresholds are set on the DEV split, never on test:
  pattern similarity: just above the highest similarity any genuine train/dev message reaches
  classifier probability: the lowest value that keeps dev false alarms at zero, floored at 0.5

Usage: python bench/train_models.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.packtool import save  # noqa: E402
from sahayak.fraud import classifier as clf_mod  # noqa: E402
from sahayak.fraud.normalize import build_context  # noqa: E402
from sahayak.fraud.patterns import PatternMatcher  # noqa: E402
from sahayak.fraud.signals import get_engine  # noqa: E402
from sahayak.packs import get_pack  # noqa: E402

BENCH = ROOT / "bench" / "scambench" / "scambench_v0.jsonl"
TODAY = dt.date.today().isoformat()


def rows(split: str) -> list[dict]:
    data = [json.loads(line) for line in BENCH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in data if r["split"] == split]


def featurise(items: list[dict], signal_ids: list[str]):
    engine, vec = get_engine(), clf_mod.make_vectorizer()
    texts, sigs = [], []
    for r in items:
        ctx = build_context(r["text"], sender=r.get("sender"), input_type=r.get("input_type", "text"))
        texts.append(ctx.norm)
        fired = {f.id for f in engine.run(ctx)}
        sigs.append(clf_mod.signal_vector(signal_ids, fired))
    return hstack([vec.transform(texts), csr_matrix(np.array(sigs))]).tocsr(), texts


def main() -> None:
    train, dev = rows("train"), rows("dev")

    # ---- pattern pack: train-split scams only
    patterns = [{"id": r["id"], "category": r["category"], "text": r["text"]} for r in train if r["label"] == "scam"]
    matcher = PatternMatcher(patterns, threshold=1.0)
    genuine_sims = [matcher.best(build_context(r["text"]).norm).score for r in train + dev if r["label"] == "genuine"]
    pattern_threshold = round(min(0.95, max(genuine_sims) + 0.05), 3)
    save(ROOT / "packs" / "scam_patterns.v1.json", {
        "pack": "scam_patterns", "version": "1.0.0", "date": TODAY,
        "notes": "Known-scam texts from the ScamBench v0 TRAIN split only (never dev or test). Threshold sits just "
                 "above the highest similarity any genuine train/dev message reaches.",
        "threshold": pattern_threshold, "patterns": patterns,
    })

    # ---- classifier
    signal_ids = sorted(get_pack("fraud").data["signals"])
    X_train, _ = featurise(train, signal_ids)
    y_train = np.array([1 if r["label"] == "scam" else 0 for r in train])
    X_dev, _ = featurise(dev, signal_ids)
    y_dev = np.array([1 if r["label"] == "scam" else 0 for r in dev])

    best = None
    for C in (0.3, 1.0, 3.0, 10.0):
        model = LogisticRegression(C=C, class_weight="balanced", max_iter=5000).fit(X_train, y_train)
        p_dev = model.predict_proba(X_dev)[:, 1]
        safe = p_dev[y_dev == 0].max() if (y_dev == 0).any() else 0.5
        threshold = float(max(0.5, min(0.95, safe + 0.02)))
        recall = float(((p_dev >= threshold) & (y_dev == 1)).sum() / max(1, y_dev.sum()))
        if best is None or recall > best[0]:
            best = (recall, C, threshold, model)
    recall, C, threshold, model = best
    n_text = clf_mod.N_FEATURES
    coef = model.coef_.ravel()
    text_coef = {str(i): round(float(w), 6) for i, w in enumerate(coef[:n_text]) if abs(w) > 1e-6}
    save(ROOT / "packs" / "fraud_model.v1.json", {
        "pack": "fraud_model", "version": "1.0.0", "date": TODAY,
        "notes": "Logistic regression over hashed char 2-5 grams (2^16) plus fired signals, trained on the ScamBench v0 "
                 f"TRAIN split; C={C}; threshold set on DEV to keep dev false alarms at zero.",
        "threshold": round(threshold, 4), "intercept": round(float(model.intercept_[0]), 6),
        "signal_ids": signal_ids, "signal_coef": [round(float(w), 6) for w in coef[n_text:]],
        "text_coef": text_coef,
    })
    print(f"patterns: {len(patterns)} (threshold {pattern_threshold}; max genuine similarity {max(genuine_sims):.3f})")
    print(f"classifier: C={C} threshold={threshold:.3f} dev recall at zero dev false alarms={recall:.3f} "
          f"text weights kept={len(text_coef)}")


if __name__ == "__main__":
    main()
