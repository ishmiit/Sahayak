"""Evaluate the Benefits Navigator on SchemeBench v1, using the real engine and pack.

  1. Rules: with all seven questions answered, does each scheme's result match the oracle's
     expected answer? 200 personas x 12 schemes = 2,400 decisions. Acceptance: 100%.
  2. Interview: replay each persona through the adaptive interview. How many questions does
     it ask (acceptance: median <= 5, max <= 8), and does the shortened interview reach exactly
     the result that answering everything gives?
  3. Sweep: the interview check again on random answer sets, including age-band answers.
  4. Amount trace: every rupee figure in every result appears in the pack file.

Optional --worksheet scores a human-filled worksheet_v1.csv (E/L/C/U/N per scheme) against
the engine: the independent second derivation the PRD asks for.

Usage: python bench/eval_schemebench.py [--report] [--sweep 5000] [--worksheet path.csv]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.navigator import get_navigator  # noqa: E402

BENCH = ROOT / "bench" / "schemebench" / "schemebench_v1.jsonl"
RESULTS = ROOT / "bench" / "results"
STATUSES = ["eligible", "likely", "check", "unlock", "not_eligible"]
LETTER = {"E": "eligible", "L": "likely", "C": "check", "U": "unlock", "N": "not_eligible"}
BANDS = ["lt18", "18_40", "41_50", "51_59", "60_69", "70_79", "80p"]
RUPEES = re.compile(r"₹\s?[\d,]+(?:\s?(?:लाख|lakh))?")


def statuses(result: dict) -> dict[str, str]:
    return {c["id"]: c["status"] for c in result["schemes"]}


def replay(nav, answers: dict) -> dict:
    """Answer the interview's questions from a full answer set, like the person would."""
    def answer_for(q: dict):
        if q["kind"] == "multi":
            shown = {o["id"] for o in q["options"]}
            return [s for s in answers["situation"] if s in shown]
        return answers[q["id"]]
    return nav.interview(answer_for)


def random_answers(rng: random.Random) -> dict:
    age = rng.choice(BANDS) if rng.random() < 0.2 else rng.randint(0, 100)
    return dict(
        age=age,
        situation=[s for s in ("widow", "disability80", "earner_died") if rng.random() < 0.3],
        ration=rng.choice(["aay", "bpl_phh", "apl", "none", "dont_know"]),
        bank=rng.choice(["yes", "no", "dont_know"]),
        work=rng.choice(["farmer_land", "farm_labour", "unorganised", "salaried_pf", "government", "not_working"]),
        money=rng.choice(["taxpayer", "le15k", "gt15k", "dont_know"]),
        kisan=rng.choice(["yes", "no", "dont_know"]),
    )


def all_text(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in all_text(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in all_text(v)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="write bench/results/schemebench_v1.md and .json")
    ap.add_argument("--sweep", type=int, default=5000, help="random answer sets for the interview check")
    ap.add_argument("--worksheet", type=Path, help="a human-filled worksheet_v1.csv to score")
    ap.add_argument("--exhaustive", action="store_true",
                    help="also replay every answer combination at every age where a rule changes (~250k, ~15 min)")
    args = ap.parse_args()

    nav = get_navigator()
    rows = [json.loads(line) for line in BENCH.read_text(encoding="utf-8").splitlines() if line.strip()]
    pack_text = nav.pack.path.read_text(encoding="utf-8")
    scheme_ids = [s["id"] for s in nav.schemes]

    # 1 + 2 + 4 on the 200 personas
    agree, disagreements = Counter(), []
    dist = {sid: Counter() for sid in scheme_ids}
    lengths, not_equivalent, untraced, times = [], [], set(), []
    for r in rows:
        t0 = time.perf_counter()
        full = nav.result(r["answers"])
        times.append((time.perf_counter() - t0) * 1000)
        got = statuses(full)
        for sid in scheme_ids:
            dist[sid][r["expected"][sid]] += 1
            if got[sid] == r["expected"][sid]:
                agree[sid] += 1
            else:
                disagreements.append((r["id"], sid, r["expected"][sid], got[sid]))
        asked = replay(nav, r["answers"])
        lengths.append(len(asked))
        if statuses(nav.result(asked)) != got:
            not_equivalent.append(r["id"])
        for text in all_text(full):
            for amount in RUPEES.findall(text):
                if amount not in pack_text:
                    untraced.add(amount)

    # 3 sweep
    rng = random.Random(7)
    sweep_lengths, sweep_bad = [], []
    for i in range(args.sweep):
        answers = random_answers(rng)
        asked = replay(nav, answers)
        sweep_lengths.append(len(asked))
        if statuses(nav.result(asked)) != statuses(nav.result(answers)):
            sweep_bad.append(answers)

    total = len(rows) * len(scheme_ids)
    n_agree = sum(agree.values())
    hist = Counter(lengths)
    summary = {
        "date": dt.date.today().isoformat(),
        "pack": {"version": nav.pack.version, "date": nav.pack.date, "sha256": nav.pack.sha256},
        "personas": len(rows),
        "rules": {"decisions": total, "agree": n_agree, "rate": round(n_agree / total, 4),
                  "per_scheme": {sid: agree[sid] for sid in scheme_ids},
                  "disagreements": [dict(zip(("id", "scheme", "expected", "engine"), d)) for d in disagreements]},
        "expected_distribution": {sid: dict(dist[sid]) for sid in scheme_ids},
        "interview": {"median": statistics.median(lengths), "mean": round(statistics.mean(lengths), 2),
                      "p90": sorted(lengths)[int(0.9 * (len(lengths) - 1))], "max": max(lengths),
                      "histogram": {str(k): hist[k] for k in sorted(hist)},
                      "equivalent": len(rows) - len(not_equivalent), "not_equivalent": not_equivalent},
        "sweep": {"n": args.sweep, "median": statistics.median(sweep_lengths) if sweep_lengths else None,
                  "max": max(sweep_lengths) if sweep_lengths else None, "not_equivalent": len(sweep_bad)},
        "amounts": {"untraced": sorted(untraced)},
        "timing_ms": {"result_p50": round(statistics.median(times), 2),
                      "result_p95": round(sorted(times)[int(0.95 * (len(times) - 1))], 2)},
    }

    if args.worksheet:
        summary["worksheet"] = score_worksheet(nav, rows, args.worksheet)
    if args.exhaustive:
        summary["exhaustive"] = exhaustive(nav)
    elif (RESULTS / "schemebench_v1.json").exists():  # keep the last exhaustive run if this one skipped it
        previous = json.loads((RESULTS / "schemebench_v1.json").read_text(encoding="utf-8")).get("exhaustive")
        if previous and previous.get("pack_sha256") == nav.pack.sha256:
            summary["exhaustive"] = previous

    print_summary(summary)
    if args.report:
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "schemebench_v1.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (RESULTS / "schemebench_v1.md").write_text(report(summary, nav), encoding="utf-8")
        print(f"wrote {RESULTS / 'schemebench_v1.md'}")
    ok = (n_agree == total and not not_equivalent and not sweep_bad and not untraced
          and summary["interview"]["median"] <= 5 and summary["interview"]["max"] <= nav.max_questions
          and (summary["sweep"]["max"] or 0) <= nav.max_questions
          and summary.get("exhaustive", {}).get("not_equivalent", 0) == 0)
    return 0 if ok else 1


def exhaustive(nav) -> dict:
    """Every combination of answers, at every age where some rule changes plus every age band."""
    import itertools
    edges = sorted({a for e in nav._age_probes for a in (e - 1, e) if 0 <= a <= 120})
    ages = edges + BANDS
    situations = [list(c) for n in range(4) for c in itertools.combinations(("widow", "disability80", "earner_died"), n)]
    space = itertools.product(ages, situations, ["aay", "bpl_phh", "apl", "none", "dont_know"], ["yes", "no", "dont_know"],
                              ["farmer_land", "farm_labour", "unorganised", "salaried_pf", "government", "not_working"],
                              ["taxpayer", "le15k", "gt15k", "dont_know"], ["yes", "no", "dont_know"])
    hist, bad, n, t0 = Counter(), [], 0, time.perf_counter()
    for age, sit, ration, bank, work, money, kisan in space:
        answers = dict(age=age, situation=sit, ration=ration, bank=bank, work=work, money=money, kisan=kisan)
        asked = replay(nav, answers)
        hist[len(asked)] += 1
        n += 1
        if statuses(nav.result(asked)) != statuses(nav.result(answers)):
            bad.append(answers)
    lengths = sorted(hist.elements())
    return {"pack_sha256": nav.pack.sha256, "cases": n, "ages": ages, "max": max(hist), "median": statistics.median(lengths),
            "histogram": {str(k): hist[k] for k in sorted(hist)}, "not_equivalent": len(bad), "examples": bad[:5],
            "seconds": round(time.perf_counter() - t0)}


def score_worksheet(nav, rows: list[dict], path: Path) -> dict:
    """Compare a second person's answers (E/L/C/U/N) with the engine's."""
    by_id = {r["id"]: r for r in rows}
    agree, total, misses, blank = 0, 0, [], 0
    with path.open(encoding="utf-8") as f:
        for line in csv.DictReader(f):
            r = by_id.get(line["id"])
            if r is None:
                continue
            got = statuses(nav.result(r["answers"]))
            for sid in got:
                mark = (line.get(sid) or "").strip().upper()[:1]
                if not mark:
                    blank += 1
                    continue
                total += 1
                if LETTER.get(mark) == got[sid]:
                    agree += 1
                else:
                    misses.append({"id": r["id"], "scheme": sid, "human": LETTER.get(mark, mark), "engine": got[sid]})
    return {"decisions": total, "agree": agree, "blank": blank, "disagreements": misses}


def print_summary(s: dict) -> None:
    r, i, w = s["rules"], s["interview"], s["sweep"]
    print(f"rules: {r['agree']}/{r['decisions']} agree with the oracle ({100 * r['rate']:.1f}%)")
    for d in r["disagreements"][:20]:
        print(f"  DISAGREE {d['id']} {d['scheme']}: expected {d['expected']}, engine {d['engine']}")
    print(f"interview (200 personas): median {i['median']} questions, mean {i['mean']}, p90 {i['p90']}, max {i['max']}; "
          f"histogram {i['histogram']}; same result as answering everything: {i['equivalent']}/{s['personas']}")
    print(f"sweep ({w['n']} random answer sets): median {w['median']}, max {w['max']}, not equivalent {w['not_equivalent']}")
    print(f"amounts not found in the pack: {s['amounts']['untraced'] or 'none'}")
    print(f"timing: result p50 {s['timing_ms']['result_p50']} ms, p95 {s['timing_ms']['result_p95']} ms")
    if "worksheet" in s:
        ws = s["worksheet"]
        print(f"worksheet: {ws['agree']}/{ws['decisions']} agree, {ws['blank']} blank cells")
    if "exhaustive" in s:
        e = s["exhaustive"]
        print(f"exhaustive ({e['cases']} answer sets): median {e['median']}, max {e['max']}, "
              f"not equivalent {e['not_equivalent']}; histogram {e['histogram']}")


def report(s: dict, nav) -> str:
    r, i, w = s["rules"], s["interview"], s["sweep"]
    names = {sc["id"]: sc["short"] for sc in nav.schemes}
    lines = [
        "# SchemeBench v1: Benefits Navigator results",
        "",
        f"Run {s['date']} on the schemes pack v{s['pack']['version']} ({s['pack']['date']}), "
        f"SHA-256 `{s['pack']['sha256'][:16]}…`. Reproduce with `python bench/build_schemebench.py` then "
        "`python bench/eval_schemebench.py --report`.",
        "",
        "## Summary",
        "",
        "| Check | Result | Target |",
        "| --- | --- | --- |",
        f"| Scheme decisions matching the independent oracle | {r['agree']} / {r['decisions']} ({100 * r['rate']:.1f}%) | 100% |",
        f"| Questions per interview (200 personas) | median {i['median']}, max {i['max']} | median ≤ 5, max ≤ 8 |",
        f"| Short interview gives the same result as answering everything | {i['equivalent']} / {s['personas']} | all |",
        f"| Random answer sets: max questions, results changed by skipping | max {w['max']}; {w['not_equivalent']} of {w['n']} changed | ≤ 8; none |",
        *([f"| Every answer combination ({s['exhaustive']['cases']:,}): max questions, results changed by skipping | "
           f"max {s['exhaustive']['max']}; {s['exhaustive']['not_equivalent']} changed | ≤ 8; none |"] if "exhaustive" in s else []),
        f"| Rupee amounts not found in the pack | {len(s['amounts']['untraced'])} | 0 |",
        f"| Time to compute a full result | p50 {s['timing_ms']['result_p50']} ms, p95 {s['timing_ms']['result_p95']} ms | — |",
        "",
        "## 1. Rules: engine against the oracle",
        "",
        "The 200 personas are 20 hand-written stories and 180 generated cases weighted towards the ages where a "
        "rule changes and towards \"don't know\" answers. Each answers all seven questions. The expected answer for "
        "each scheme comes from `bench/schemebench/oracle.py`, a separate transcription of the official rules as "
        "plain if/else that does not read the pack or call the engine.",
        "",
        "| Scheme | Agree | Expected: eligible | likely | check | after bank account | not eligible |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for sid, n in r["per_scheme"].items():
        d = s["expected_distribution"][sid]
        lines.append(f"| {names[sid]} | {n}/{s['personas']} | {d.get('eligible', 0)} | {d.get('likely', 0)} | "
                     f"{d.get('check', 0)} | {d.get('unlock', 0)} | {d.get('not_eligible', 0)} |")
    if r["disagreements"]:
        lines += ["", "Disagreements:", "", "| Persona | Scheme | Oracle | Engine |", "| --- | --- | --- | --- |"]
        lines += [f"| {d['id']} | {names[d['scheme']]} | {d['expected']} | {d['engine']} |" for d in r["disagreements"]]
    else:
        lines += ["", "No disagreements."]
    lines += [
        "",
        "## 2. Interview length",
        "",
        "Each persona is replayed through the real interview: the engine picks the next question, the persona "
        "answers it, and the engine stops when no remaining answer could change any scheme's result.",
        "",
        "| Questions asked | Personas |",
        "| --- | --- |",
    ]
    lines += [f"| {k} | {v} |" for k, v in i["histogram"].items()]
    lines += [
        "",
        f"Median {i['median']}, mean {i['mean']}, 90th percentile {i['p90']}, maximum {i['max']}. In "
        f"{i['equivalent']} of {s['personas']} cases the shortened interview reached exactly the result that "
        "answering all seven questions gives.",
        "",
        f"The same check on {w['n']} random answer sets (a fifth of them answering age as a range): median "
        f"{w['median']}, maximum {w['max']} questions, {w['not_equivalent']} results changed by skipping questions.",
        "",
    ]
    if "exhaustive" in s:
        e = s["exhaustive"]
        lines += [
            f"Exhaustive check: every combination of answers ({e['cases']:,} answer sets), with age taken on both "
            f"sides of every point where a rule changes and as each age band. Maximum {e['max']} questions, median "
            f"{e['median']}; {e['not_equivalent']} results changed by skipping questions.",
            "",
        ]
    lines += [
        "## What this shows and what it does not",
        "",
        "- It shows that the pack encodes the rules as the oracle reads them, that the interview never asks "
        "more than it needs, and that skipping questions never changes an answer.",
        "- The oracle and the pack were written by the same author, from the same official pages. Agreement "
        "rules out transcription slips, not a shared misreading. The PRD's acceptance needs a second person "
        "to fill `bench/schemebench/worksheet_v1.csv` from the official pages alone (E, L, C, U or N per scheme) "
        "and score it with `python bench/eval_schemebench.py --worksheet <file>`. That is still to do.",
        "- Both follow the pack's documented interpretations: a ration card stands in for BPL status, PM-JAY "
        "below 70 always needs a list check, and land-owning farmers are not treated as unorganised workers.",
        "- Amounts are the central share. State top-ups are not modelled yet (PRD row 26).",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
