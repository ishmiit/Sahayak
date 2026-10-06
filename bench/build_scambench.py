"""Build ScamBench from the source files: validate, assign ids and splits, check leakage.

Splits are assigned per *group* (a scam and its translations share a group), using a
stable hash, so the same story never appears in both train and test. Near-duplicate
texts across splits (character 5-gram Jaccard >= 0.8) are reported and dropped from test.

Usage: python bench/build_scambench.py
Writes bench/scambench/scambench_v0.jsonl and bench/scambench/DATA_CARD.md
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "scambench"
SOURCES = {"scam": ROOT / "scam_v0.jsonl", "genuine": ROOT / "genuine_v0.jsonl"}
OUT = ROOT / "scambench_v0.jsonl"
CARD = ROOT / "DATA_CARD.md"
SPLITS = (("train", 0.6), ("dev", 0.2), ("test", 0.2))
LANGS = {"en", "hi", "hinglish"}


def split_for(group: str) -> str:
    bucket = int(hashlib.sha256(group.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    edge = 0.0
    for name, share in SPLITS:
        edge += share
        if bucket <= edge:
            return name
    return SPLITS[-1][0]


def grams(text: str, n: int = 5) -> set[str]:
    t = " ".join(text.lower().split())
    return {t[i : i + n] for i in range(max(1, len(t) - n + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / max(1, len(a | b))


def main() -> None:
    items = []
    for label, path in SOURCES.items():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            assert row.get("text"), f"{path.name}:{line_no} empty text"
            assert row.get("lang") in LANGS, f"{path.name}:{line_no} bad lang {row.get('lang')}"
            assert row.get("group"), f"{path.name}:{line_no} missing group"
            row["label"] = label
            row.setdefault("input_type", "text")
            row["source"] = ("team-written v0; modelled on publicly reported scam patterns" if label == "scam"
                             else "team-written v0; modelled on real message formats")
            items.append(row)

    for i, row in enumerate(items, 1):
        row["id"] = f"sb-{i:04d}"
        row["split"] = split_for(row["group"])

    # leakage: near-duplicates across splits
    leaks = []
    by_split = {s: [r for r in items if r["split"] == s] for s, _ in SPLITS}
    test_grams = {r["id"]: grams(r["text"]) for r in by_split["test"]}
    for other in ("train", "dev"):
        for r in by_split[other]:
            g = grams(r["text"])
            for tid, tg in test_grams.items():
                if jaccard(g, tg) >= 0.8:
                    leaks.append((tid, r["id"]))
    leaked_ids = {tid for tid, _ in leaks}
    kept = [r for r in items if r["id"] not in leaked_ids]

    with OUT.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps({k: r[k] for k in ("id", "split", "label", "category", "lang", "input_type", "sender", "text", "group", "source") if k in r},
                               ensure_ascii=False) + "\n")

    counts = Counter((r["split"], r["label"]) for r in kept)
    langs = Counter((r["label"], r["lang"]) for r in kept)
    cats = Counter(r["category"] for r in kept if r["label"] == "scam")
    lines = [
        "# ScamBench v0 data card",
        "",
        f"{len(kept)} messages: {sum(1 for r in kept if r['label'] == 'scam')} scams and "
        f"{sum(1 for r in kept if r['label'] == 'genuine')} genuine messages, in English, Hindi and Hinglish.",
        "",
        "**Provenance and its limit.** Every v0 message was written by the Sahayak team, modelled on publicly reported",
        "scam patterns and on the format of real bank, government and delivery messages. No real person's message is",
        "included. Phone numbers are dummy patterns and links are invented. Because the same team wrote the detection",
        "rules, v0 scores are optimistic; the honest test is v1, which adds real messages collected with consent.",
        "",
        "## Splits",
        "",
        "| Split | Scam | Genuine |",
        "| --- | --- | --- |",
        *[f"| {s} | {counts[(s, 'scam')]} | {counts[(s, 'genuine')]} |" for s, _ in SPLITS],
        "",
        "Splits are assigned per group (a scam and its translations share a group) with a stable hash.",
        f"Leakage check: {len(leaks)} near-duplicate pair(s) across splits (5-gram Jaccard >= 0.8); "
        f"{len(leaked_ids)} test item(s) dropped.",
        "",
        "## Languages",
        "",
        "| Language | Scam | Genuine |",
        "| --- | --- | --- |",
        *[f"| {lang} | {langs[('scam', lang)]} | {langs[('genuine', lang)]} |" for lang in ("en", "hi", "hinglish")],
        "",
        "## Scam categories",
        "",
        "| Category | Messages |",
        "| --- | --- |",
        *[f"| {c} | {n} |" for c, n in sorted(cats.items(), key=lambda x: -x[1])],
        "",
        "## Adding real messages (v1)",
        "",
        "Put real messages in `bench/scambench/private/` (git-ignored) first. Remove names, numbers, account digits and",
        "links that identify a person, get the owner's consent, then move them to a `*_v1.jsonl` source file with",
        "`source` set to how they were collected.",
        "",
    ]
    CARD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(kept)} items; leaks {len(leaks)}; splits {dict(Counter(r['split'] for r in kept))}")


if __name__ == "__main__":
    main()
