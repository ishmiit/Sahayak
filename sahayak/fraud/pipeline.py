"""Fraud-Shield entry point: message in, verdict card out.

Stages: fold and extract -> signal layer -> similarity to known scams -> classifier ->
verdict card. Every stage adds named, weighted signals, so the verdict always explains
itself. The LLM explainer runs afterwards (`explain.py`) and never decides the verdict.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from ..packs import get_pack
from .classifier import get_classifier
from .normalize import build_context, rupees_at_risk
from .patterns import get_matcher
from .signals import Fired, get_engine
from .verdict import build_card

INPUT_TYPES = ("text", "voice", "ocr", "qr", "call")


def check_message(text: str, sender: str | None = None, input_type: str = "text") -> dict[str, Any]:
    return check_message_full(text, sender, input_type)[0]


def check_message_full(text: str, sender: str | None = None, input_type: str = "text",
                       use_patterns: bool = True, use_classifier: bool = True) -> tuple[dict[str, Any], list[Fired]]:
    """Return the verdict card and the fired signals (the explainer needs both)."""
    t0 = time.perf_counter()
    if input_type not in INPUT_TYPES:
        input_type = "text"
    pack = get_pack("fraud")
    defs, cats = pack.data["signals"], pack.data["categories"]
    ctx = build_context(text, sender=sender, input_type=input_type)
    fired = get_engine().run(ctx)
    t_signals = time.perf_counter()

    scores: dict[str, float] = {}
    matcher = get_matcher() if use_patterns else None
    if matcher:
        best = matcher.best(ctx.norm)
        scores["pattern_similarity"] = round(best.score, 3)
        if best.score >= matcher.threshold:
            name = cats[best.category]["name"]
            fired.append(Fired("pattern_match", float(defs["pattern_match"]["weight"]), False,
                               {"name": name["en"], "name_hi": name["hi"], "_category": best.category}))
    clf = get_classifier() if use_classifier else None
    if clf:
        p = clf.probability(ctx.norm, {f.id for f in fired})
        scores["classifier_p"] = round(p, 3)
        if p >= clf.threshold:
            fired.append(Fired("classifier_flag", float(defs["classifier_flag"]["weight"]), False, {}))

    card = build_card(fired, pack.data, unread=ctx.unread)
    card.update({
        "id": uuid.uuid4().hex[:12],
        "input_type": input_type,
        "lang_detected": ctx.lang,
        "explainer": "template",
        "model_scores": scores,
        "helplines": pack.data["helplines"] if card["verdict"] in ("scam", "suspicious") else [],
        "extracted": {
            "links": [u.raw for u in ctx.urls],
            "mobiles": ctx.mobiles,
            "upi_ids": ctx.upi_ids,
            "amounts": ctx.amounts,
            "rupees_at_risk": rupees_at_risk(ctx.norm) if card["verdict"] == "scam" else 0.0,
        },
        "pack": {"name": pack.name, "version": pack.version, "sha256": pack.sha256[:12]},
    })
    card["timing_ms"] = {
        "signals": round((t_signals - t0) * 1000, 2),
        "total": round((time.perf_counter() - t0) * 1000, 2),
    }
    return card, fired
