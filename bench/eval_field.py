"""Score a field morning (docs/field/FIELD_TEST_PROTOCOL.md) from its two sheets.

  bench/field/field_participants_v0.csv   one row per person (no names or numbers)
  bench/field/field_tasks_v0.csv          one row per attempt: message cards, a call, their own message,
                                          the benefits interview, the off-node check

What it reports, with 95% Wilson intervals where it is a rate:
  cards       judged right on their own first, then right with Sahayak (paired; McNemar's exact test)
  actions     "what will you do now?" answered right after a Sahayak verdict
  benefits    finished without help, schemes found, schemes new to the person, PM-JAY 70+ shown to seniors
  offline     the check worked on a phone off the node's Wi-Fi
  opinions    share answering 4 or 5 to understood / trust / would use again
and the same card results for people aged 55+ and for people who read little or no Hindi.

Usage: python bench/eval_field.py [--report] [--participants F] [--tasks F] [--out DIR]
       (--report writes field_v0.json and field_v0.md to DIR, default bench/results)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
FIELD = ROOT / "bench" / "field"


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": wilson(k, n)}


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f) if any((v or "").strip() for v in row.values())]


def num(v: str) -> float | None:
    try:
        return float(v)
    except ValueError:
        return None


def median(values: list) -> float | None:
    xs = [x for x in values if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def cards(rows: list[dict]) -> dict:
    """Paired: the person's own judgement first, then Sahayak's verdict. "Unsure" counts as not right."""
    before_ok = [r["before"] == r["truth"] for r in rows]
    after_ok = [(r["verdict"] != "no_signs") == (r["truth"] == "scam") for r in rows]
    gained = sum(1 for b, a in zip(before_ok, after_ok) if a and not b)
    lost = sum(1 for b, a in zip(before_ok, after_ok) if b and not a)
    p = binomtest(min(gained, lost), gained + lost, 0.5).pvalue if gained + lost else 1.0
    return {"attempts": len(rows), "before": rate(sum(before_ok), len(rows)), "with_sahayak": rate(sum(after_ok), len(rows)),
            "right_only_with_sahayak": gained, "right_only_on_their_own": lost, "mcnemar_p": float(p),
            "scams_caught": rate(sum(1 for r, ok in zip(rows, after_ok) if ok and r["truth"] == "scam"),
                                 sum(1 for r in rows if r["truth"] == "scam")),
            "genuine_left_alone": rate(sum(1 for r, ok in zip(rows, after_ok) if ok and r["truth"] == "genuine"),
                                       sum(1 for r in rows if r["truth"] == "genuine")),
            "median_seconds": median([num(r["seconds"]) for r in rows]),
            "needed_help": rate(sum(r["helped"] == "y" for r in rows), len(rows))}


def evaluate(participants: list[dict], tasks: list[dict]) -> dict:
    people = {p["pid"]: p for p in participants}
    unknown = sorted({t["pid"] for t in tasks} - set(people))
    if unknown:
        raise SystemExit(f"tasks for people not on the participants sheet: {unknown}")
    by = lambda kind: [t for t in tasks if t["task"] == kind]  # noqa: E731
    card_rows = by("card")
    checks = [t for t in tasks if t["task"] in ("card", "call", "own") and t["action_right"] in ("y", "n")]
    calls = [t for t in by("call") if t["truth"]]
    benefits, offline = by("benefits"), [t for t in by("offline") if t["worked"] in ("y", "n")]
    seniors = [t for t in benefits if t["pmjay70_shown"] in ("y", "n")]

    def group(pred) -> dict | None:
        rows = [t for t in card_rows if pred(people[t["pid"]])]
        return cards(rows) if rows else None

    def agree(field: str) -> dict:
        xs = [num(p[field]) for p in participants if num(p[field]) is not None]
        return {**rate(sum(x >= 4 for x in xs), len(xs)), "median": median(xs)}

    def count(field: str) -> dict:
        out: dict[str, int] = {}
        for p in participants:
            out[p[field] or "not recorded"] = out.get(p[field] or "not recorded", 0) + 1
        return dict(sorted(out.items()))

    return {
        "people": len(participants),
        "who": {f: count(f) for f in ("age_band", "gender", "reads_hindi", "phone", "lang")},
        "cards": cards(card_rows) if card_rows else None,
        "cards_aged_55_plus": group(lambda p: p["age_band"] in ("55-69", "70+")),
        "cards_reads_little_or_no_hindi": group(lambda p: p["reads_hindi"] in ("some", "no")),
        "calls": {"attempts": len(calls),
                  "right": rate(sum((t["verdict"] != "no_signs") == (t["truth"] == "scam") for t in calls), len(calls))},
        "own_messages": {"checked": len(by("own")), "verdicts": {v: sum(t["verdict"] == v for t in by("own"))
                                                                 for v in ("scam", "suspicious", "no_signs")},
                         "donated": sum(p["donated_message"] == "y" for p in participants)},
        "right_action_after_verdict": rate(sum(t["action_right"] == "y" for t in checks), len(checks)),
        "benefits": {"interviews": len(benefits),
                     "finished_unaided": rate(sum(t["helped"] == "n" for t in benefits), len(benefits)),
                     "median_seconds": median([num(t["seconds"]) for t in benefits]),
                     "median_schemes_found": median([num(t["schemes_found"]) for t in benefits]),
                     "found_something_new": rate(sum((num(t["schemes_new"]) or 0) >= 1 for t in benefits), len(benefits)),
                     "schemes_new_total": int(sum(num(t["schemes_new"]) or 0 for t in benefits)),
                     "seniors_70_shown_pmjay": rate(sum(t["pmjay70_shown"] == "y" for t in seniors), len(seniors))},
        "offline_on_phone": rate(sum(t["worked"] == "y" for t in offline), len(offline)),
        "opinions": {f: agree(f) for f in ("understood", "trust", "use_again")},
    }


def pct(r: dict | None) -> str:
    if not r or not r["n"]:
        return "—"
    lo, hi = r["ci95"]
    return f"{100 * r['rate']:.0f}% ({r['k']}/{r['n']}; 95% CI {100 * lo:.0f}–{100 * hi:.0f}%)"


def render(res: dict, meta: dict) -> str:
    c = res["cards"]
    lines = [
        "# Field morning v0",
        "",
        f"{meta.get('place', 'One CSC')}, {meta.get('date', 'date not recorded')}: {res['people']} people. "
        "Scored by `python bench/eval_field.py --report` from `bench/field/` (no names or numbers kept). "
        "Protocol: `docs/field/FIELD_TEST_PROTOCOL.md`.",
        "",
        "| Measure | Result |",
        "| --- | --- |",
    ]
    if c:
        lines += [
            f"| Message cards judged right on their own | {pct(c['before'])} |",
            f"| Same cards judged right with Sahayak | {pct(c['with_sahayak'])} |",
            f"| Right only with Sahayak / only on their own | {c['right_only_with_sahayak']} / {c['right_only_on_their_own']} "
            f"(McNemar p = {c['mcnemar_p']:.3g}) |",
            f"| Scams flagged / genuine messages left alone | {pct(c['scams_caught'])} / {pct(c['genuine_left_alone'])} |",
        ]
    lines += [
        f"| Right action after a verdict | {pct(res['right_action_after_verdict'])} |",
        f"| Benefits interview finished without help | {pct(res['benefits']['finished_unaided'])} |",
        f"| Found at least one scheme new to them | {pct(res['benefits']['found_something_new'])} |",
        f"| Seniors 70+ without the card shown Ayushman Vay Vandana | {pct(res['benefits']['seniors_70_shown_pmjay'])} |",
        f"| Check worked on a phone away from the node | {pct(res['offline_on_phone'])} |",
        f"| \"I understood\" / \"I would trust it\" / \"I would use it again\" (4–5 of 5) | "
        f"{pct(res['opinions']['understood'])} / {pct(res['opinions']['trust'])} / {pct(res['opinions']['use_again'])} |",
        "",
    ]
    for key, label in (("cards_aged_55_plus", "aged 55+"), ("cards_reads_little_or_no_hindi", "reading little or no Hindi")):
        g = res[key]
        if g:
            lines.append(f"- People {label}: right on their own {pct(g['before'])}, with Sahayak {pct(g['with_sahayak'])}.")
    lines += [
        "",
        "**What this does not show.** One place, one morning, a few dozen people the operator invited, with a "
        "facilitator present and printed cards rather than messages arriving on their own phones. It shows whether "
        "people understand and act on Sahayak, not how often it would stop a real loss. Read the notes column for "
        "what went wrong.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--participants", type=Path, default=FIELD / "field_participants_v0.csv")
    ap.add_argument("--tasks", type=Path, default=FIELD / "field_tasks_v0.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "bench" / "results")
    ap.add_argument("--place", default="One CSC")
    ap.add_argument("--date", default="")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    participants, tasks = read(args.participants), read(args.tasks)
    if not participants:
        raise SystemExit(f"{args.participants} has no rows yet: run the field morning first (docs/field/FIELD_TEST_PROTOCOL.md)")
    res = evaluate(participants, tasks)
    meta = {"place": args.place, "date": args.date}
    print(render(res, meta))
    if args.report:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "field_v0.json").write_text(json.dumps({"meta": meta, **res}, indent=1, ensure_ascii=False), encoding="utf-8")
        (args.out / "field_v0.md").write_text(render(res, meta), encoding="utf-8")
        print(f"wrote {args.out / 'field_v0.json'}")
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
