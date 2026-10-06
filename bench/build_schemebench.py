"""Build SchemeBench v1: 200 personas with expected answers for all 12 schemes.

  20 hand-written stories (the people the app is for), plus
  180 generated personas, weighted towards the ages where a rule changes
  (15-19, 39-41, 49-51, 58-61, 69-71, 78-81) and towards "don't know" answers.

Expected answers come from bench/schemebench/oracle.py, which never touches the engine or
the pack. Also writes a blank worksheet for the human second derivation the PRD asks for.

Outputs (bench/schemebench/):
  schemebench_v1.jsonl   one persona per line: id, story, answers, expected
  worksheet_v1.csv       same personas, scheme columns left blank for a second person
Usage: python bench/build_schemebench.py
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "bench" / "schemebench"
sys.path.insert(0, str(OUT))

from oracle import SCHEMES, expected  # noqa: E402

SEED = 20261002
N_TOTAL = 200
BOUNDARY_AGES = [15, 16, 17, 18, 19, 39, 40, 41, 49, 50, 51, 58, 59, 60, 61, 69, 70, 71, 78, 79, 80, 81]

# Story, answers. Every persona answers all seven questions (full information); the interview
# replay in eval_schemebench.py asks only what it needs.
STORIES = [
    ("Widow, 67, Antyodaya card, Jan Dhan account, does not work",
     dict(age=67, situation=["widow"], ration="aay", bank="yes", work="not_working", money="le15k", kisan="no")),
    ("Daily-wage worker, 32, priority card, no bank account, earns about Rs 9,000",
     dict(age=32, situation=[], ration="bpl_phh", bank="no", work="unorganised", money="le15k", kisan="no")),
    ("Farmer, 45, owns 2 acres, APL card, bank account, nobody in the family pays tax",
     dict(age=45, situation=[], ration="apl", bank="yes", work="farmer_land", money="le15k", kisan="no")),
    ("Retired labourer, 74, BPL card, bank account",
     dict(age=74, situation=[], ration="bpl_phh", bank="yes", work="not_working", money="le15k", kisan="no")),
    ("Woman, 38, husband (the earner) died last year, BPL card, domestic worker, bank account",
     dict(age=38, situation=["widow", "earner_died"], ration="bpl_phh", bank="yes", work="unorganised", money="le15k", kisan="no")),
    ("Man, 52, 85% disability certificate, Antyodaya card, no bank account, not working",
     dict(age=52, situation=["disability80"], ration="aay", bank="no", work="not_working", money="le15k", kisan="no")),
    ("Government school teacher, 35, APL card, salary account, pays income tax",
     dict(age=35, situation=[], ration="apl", bank="yes", work="government", money="taxpayer", kisan="yes")),
    ("Factory worker with PF, 28, priority card, bank account, earns Rs 18,000",
     dict(age=28, situation=[], ration="bpl_phh", bank="yes", work="salaried_pf", money="gt15k", kisan="no")),
    ("Street vendor, 40, no ration card, bank account, earns Rs 12,000",
     dict(age=40, situation=[], ration="none", bank="yes", work="unorganised", money="le15k", kisan="no")),
    ("Farm labourer, 59, Antyodaya card, no bank account",
     dict(age=59, situation=[], ration="aay", bank="no", work="farm_labour", money="le15k", kisan="no")),
    ("Grandmother, 81, widow, BPL card, bank account",
     dict(age=81, situation=["widow"], ration="bpl_phh", bank="yes", work="not_working", money="le15k", kisan="no")),
    ("Farmer, 62, land in his name, retired Group D peon with an Rs 8,000 pension, BPL card",
     dict(age=62, situation=[], ration="bpl_phh", bank="yes", work="farmer_land", money="le15k", kisan="no")),
    ("Farmer, 48, owns land, wife is a practising doctor",
     dict(age=48, situation=[], ration="apl", bank="yes", work="farmer_land", money="gt15k", kisan="yes")),
    ("Boy, 17, helps in the family shop, no bank account, no ration card",
     dict(age=17, situation=[], ration="none", bank="no", work="unorganised", money="le15k", kisan="no")),
    ("Homemaker, 70, APL card, savings account",
     dict(age=70, situation=[], ration="apl", bank="yes", work="not_working", money="le15k", kisan="no")),
    ("Delivery rider, 24, does not know the ration card type, bank account, earns Rs 16,000",
     dict(age=24, situation=[], ration="dont_know", bank="yes", work="unorganised", money="gt15k", kisan="no")),
    ("Widow, 45, no ration card, no bank account, domestic help",
     dict(age=45, situation=["widow"], ration="none", bank="no", work="unorganised", money="le15k", kisan="no")),
    ("Man, 55, his wife (the main earner) died at 50, Antyodaya card, not sure about a bank account",
     dict(age=55, situation=["earner_died"], ration="aay", bank="dont_know", work="not_working", money="le15k", kisan="no")),
    ("Home-based tailor, 41, 80% disability certificate, priority card, bank account, unsure about tax",
     dict(age=41, situation=["disability80"], ration="bpl_phh", bank="yes", work="unorganised", money="dont_know", kisan="no")),
    ("Unemployed man, 30, APL card, no bank account",
     dict(age=30, situation=[], ration="apl", bank="no", work="not_working", money="le15k", kisan="no")),
]


def generated(rng: random.Random) -> dict:
    age = rng.choice(BOUNDARY_AGES) if rng.random() < 0.5 else rng.randint(14, 95)
    situation = [s for s, p in (("widow", 0.25), ("disability80", 0.12), ("earner_died", 0.12)) if rng.random() < p]
    return dict(
        age=age,
        situation=situation,
        ration=rng.choices(["aay", "bpl_phh", "apl", "none", "dont_know"], [2, 4, 3, 1.5, 1])[0],
        bank=rng.choices(["yes", "no", "dont_know"], [6.5, 2.8, 0.7])[0],
        work=rng.choice(["farmer_land", "farm_labour", "unorganised", "salaried_pf", "government", "not_working"]),
        money=rng.choices(["taxpayer", "le15k", "gt15k", "dont_know"], [1, 5.5, 2.5, 1])[0],
        kisan=rng.choices(["yes", "no", "dont_know"], [2, 7, 1])[0],
    )


def main() -> None:
    rng = random.Random(SEED)
    rows = [{"id": f"sb-s{i:02d}", "story": story, "answers": answers} for i, (story, answers) in enumerate(STORIES, 1)]
    seen = {json.dumps(r["answers"], sort_keys=True) for r in rows}
    while len(rows) < N_TOTAL:
        answers = generated(rng)
        key = json.dumps(answers, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"id": f"sb-g{len(rows) - len(STORIES) + 1:03d}", "story": "", "answers": answers})
    for r in rows:
        r["expected"] = expected(r["answers"])

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "schemebench_v1.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (OUT / "worksheet_v1.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "story", "age", "situation", "ration", "bank", "work", "money", "kisan", *SCHEMES])
        for r in rows:
            a = r["answers"]
            w.writerow([r["id"], r["story"], a["age"], "+".join(a["situation"]) or "none", a["ration"], a["bank"],
                        a["work"], a["money"], a["kisan"], *[""] * len(SCHEMES)])

    counts: dict[str, dict[str, int]] = {}
    for r in rows:
        for sid, status in r["expected"].items():
            counts.setdefault(sid, {}).setdefault(status, 0)
            counts[sid][status] += 1
    print(f"{len(rows)} personas ({len(STORIES)} stories, {len(rows) - len(STORIES)} generated, seed {SEED})")
    for sid, c in counts.items():
        print(f"  {sid:8s} " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))


if __name__ == "__main__":
    main()
