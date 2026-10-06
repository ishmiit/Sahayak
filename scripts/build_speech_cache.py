"""Synthesise every fixed sentence ahead of time, so the app speaks it instantly.

Collects the sentences the phone will ask the node to say: verdict labels and headlines
(one per scam category), reasons and action steps, the Navigator's questions, answers,
scheme names, benefits, papers and notes, and the app's own screen text. Each is split the
way the phone splits it (web/app.js speak()) and synthesised in every installed voice into
%USERPROFILE%/.sahayak/data/tts_cache. Sentences with a blank to fill ({…}) are left to
live synthesis. Safe to re-run: existing clips are skipped.

Usage: python scripts/build_speech_cache.py [--voices female,male] [--limit N]
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.packs import get_pack  # noqa: E402
from sahayak.voice.tts import TTSUnavailable, get_speaker  # noqa: E402

_SPLIT = re.compile(r"(?<=[।.?!])\s+")


def chunks(text: str) -> list[str]:
    """Mirror of splitSentences() in web/app.js."""
    out = []
    for part in _SPLIT.split(text.strip()):
        part = part.strip()
        if not part:
            continue
        while len(part) > 480:
            cut = part.rfind(" ", 0, 460)
            out.append(part[:cut if cut > 0 else 460].strip())
            part = part[cut if cut > 0 else 460:].strip()
        out.append(part)
    return out


def bilingual(obj, out: dict[str, set[str]]) -> None:
    """Every {"hi": ..., "en": ...} string inside obj."""
    if isinstance(obj, dict):
        if set(obj) >= {"hi", "en"} and all(isinstance(obj[k], str) for k in ("hi", "en")):
            for lang in ("hi", "en"):
                out[lang].add(obj[lang])
        for v in obj.values():
            bilingual(v, out)
    elif isinstance(obj, list):
        for v in obj:
            bilingual(v, out)


def ui_strings(out: dict[str, set[str]]) -> None:
    """The app's own screen text, read from the T table in web/app.js."""
    src = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    start = src.index("const T = {")
    end = src.index("};", start)
    block = src[start:end]
    hi_at, en_at = block.index("hi: {"), block.index("en: {")
    for lang, part in (("hi", block[hi_at:en_at]), ("en", block[en_at:])):
        for m in re.finditer(r'\b\w+: "((?:[^"\\]|\\.)*)"', part):
            out[lang].add(m.group(1))


def collect() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {"hi": set(), "en": set()}
    fraud = get_pack("fraud").data
    bilingual(fraud["verdicts"], out)
    bilingual(fraud.get("no_signs", {}), out)
    for cat in fraud["categories"].values():
        bilingual(cat, out)
        for lang in ("hi", "en"):  # the scam headline is filled with each category name
            out[lang].add(fraud["verdicts"]["scam"]["headline"][lang].replace("{category}", cat["name"][lang]))
    for sig in fraud["signals"].values():
        bilingual(sig.get("reason", {}), out)
    for cat in fraud["categories"].values():
        for lang in ("hi", "en"):
            out[lang].update(cat.get("actions", {}).get(lang, []))
    for lang in ("hi", "en"):
        out[lang].update(fraud.get("no_signs", {}).get("actions", {}).get(lang, []))
    schemes = get_pack("schemes").data
    for key in ("questions", "schemes", "amount_note", "fraud_note", "decision_note"):
        bilingual(schemes[key], out)
    for s in schemes["schemes"]:  # benefit_now variants keep hi/en beside a "when"
        for v in s.get("benefit_now", []):
            out["hi"].add(v["hi"])
            out["en"].add(v["en"])
    ui_strings(out)
    return {lang: {c for text in texts if "{" not in text for c in chunks(text)} for lang, texts in out.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voices", default="female,male")
    ap.add_argument("--limit", type=int, default=0, help="stop after N new clips (for a quick test)")
    args = ap.parse_args()
    speaker = get_speaker()
    installed = speaker.voices()
    sentences = collect()
    made = skipped = failed = 0
    t0 = time.perf_counter()
    for lang, texts in sentences.items():
        for gender in args.voices.split(","):
            if gender not in installed.get(lang, []):
                continue
            if lang == "en" and gender == "male":  # one English voice so far; it serves both
                continue
            for text in sorted(texts):
                try:
                    _, info = speaker.synth(text, lang, gender, 0.9, store=True)
                except TTSUnavailable:
                    failed += 1
                    continue
                if info["cached"] == "disk":
                    skipped += 1
                else:
                    made += 1
                    if args.limit and made >= args.limit:
                        break
                    if made % 50 == 0:
                        print(f"  {made} new clips, {time.perf_counter() - t0:.0f}s", flush=True)
    total = {lang: len(t) for lang, t in sentences.items()}
    print(f"sentences: {total}; new clips {made}, already cached {skipped}, failed {failed}, "
          f"{time.perf_counter() - t0:.0f}s; cache at {speaker.cache_dir}")


if __name__ == "__main__":
    main()
