"""Turn fired signals into a verdict card: level, category, reasons, actions.

Rules (fraud pack `thresholds`): any hard signal means Scam; otherwise the summed
weight decides Scam / Suspicious / No scam signs. Negative signals (genuine-looking
OTP or transaction alerts) can lower the score but never below the floor, and the
lowest verdict is "no scam signs found", never "safe".
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .signals import Fired

LANGS = ("en", "hi")


def _fill(template: dict[str, str], evidence: dict[str, str]) -> dict[str, str]:
    out = {}
    for lang in LANGS:
        text = template[lang]
        for key, value in evidence.items():
            text = text.replace("{" + key + "}", str(value))
        out[lang] = text
    return out


def score(fired: list[Fired], pack: dict[str, Any]) -> tuple[float, bool]:
    floor = pack["thresholds"]["negative_floor"]
    positive = sum(f.weight for f in fired if f.weight > 0)
    negative = sum(f.weight for f in fired if f.weight < 0)
    return round(positive + max(negative, floor), 3), any(f.hard for f in fired)


def level_for(risk: float, hard: bool, pack: dict[str, Any]) -> str:
    th = pack["thresholds"]
    if hard or risk >= th["scam"]:
        return "scam"
    if risk >= th["suspicious"]:
        return "suspicious"
    return "no_signs"


def confidence_for(risk: float, hard: bool) -> float:
    p = 1.0 / (1.0 + math.exp(-1.5 * (risk - 2.25)))
    return round(max(p, 0.97) if hard else p, 3)


def pick_category(fired: list[Fired], pack: dict[str, Any]) -> str:
    totals: dict[str, float] = defaultdict(float)
    for f in fired:
        # a signal can carry its own category (pattern_match names the scam it resembles)
        cat = f.evidence.get("_category") or pack["signals"][f.id].get("category")
        if cat and f.weight > 0:
            totals[cat] += f.weight + (10.0 if f.hard else 0.0)
    if not totals:
        return "generic"
    cats = pack["categories"]
    return max(totals, key=lambda c: (totals[c], cats[c]["priority"]))


def build_card(fired: list[Fired], pack: dict[str, Any], level: str | None = None) -> dict[str, Any]:
    risk, hard = score(fired, pack)
    level = level or level_for(risk, hard, pack)
    category = pick_category(fired, pack) if level != "no_signs" else None
    defs, cats = pack["signals"], pack["categories"]

    if level == "no_signs":
        shown = [f for f in fired if f.weight < 0 and defs[f.id].get("show", True)]
        shown.sort(key=lambda f: f.weight)
        reasons = [{"id": f.id, "text": _fill(defs[f.id]["reason"], f.evidence), "weight": f.weight} for f in shown[:2]]
        if not reasons:
            reasons = [{"id": "no_signals", "text": dict(pack["no_signs"]["default_reason"]), "weight": 0.0}]
        actions = pack["no_signs"]["actions"]
    else:
        shown = [f for f in fired if f.weight > 0 and defs[f.id].get("show", True)]
        shown.sort(key=lambda f: (not f.hard, -f.weight))
        reasons = [{"id": f.id, "text": _fill(defs[f.id]["reason"], f.evidence), "weight": f.weight, "hard": f.hard}
                   for f in shown[:3]]
        if not reasons:  # only hidden low-weight signals fired
            hidden = sorted((f for f in fired if f.weight > 0), key=lambda f: -f.weight)[:2]
            reasons = [{"id": f.id, "text": _fill(defs[f.id]["reason"], f.evidence), "weight": f.weight} for f in hidden]
        actions = cats[category]["actions"]

    verdict_text = pack["verdicts"][level]
    cat_name = cats[category]["name"] if category else None
    headline = {
        lang: verdict_text["headline"][lang].replace("{category}", cat_name[lang] if cat_name else "")
        for lang in LANGS
    }
    return {
        "verdict": level,
        "label": dict(verdict_text["label"]),
        "headline": headline,
        "category": {"id": category, "name": dict(cat_name)} if category else None,
        "risk_score": risk,
        "confidence": confidence_for(risk, hard),
        "hard_signal": hard,
        "reasons": reasons,
        "actions": {lang: list(actions[lang]) for lang in LANGS},
        "sensitive": any(defs[f.id].get("sensitive") for f in fired),
        "signals": [{"id": f.id, "weight": f.weight, "hard": f.hard} for f in fired],
    }
