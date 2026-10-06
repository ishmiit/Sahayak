"""Score the red-team set v0: how many disguised scams still get flagged, and how many hard genuine
messages are left alone, for Sahayak and for the keyword blocklist baseline.

A message is flagged when the verdict is Scam or Suspicious. The first run on the frozen set is the
number to quote; fixes made after it are logged under "Post-freeze log" in the report and the set
is re-scored, but the first numbers stay in the report.

Usage: python bench/eval_redteam.py [--report] [--rerun-note "what changed"]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))

from eval_scambench import predict  # noqa: E402

SET = ROOT / "bench" / "redteam" / "redteam_v0.jsonl"
RESULTS = ROOT / "bench" / "results"
FLAG = ("scam", "suspicious")


def score(rows: list[dict]) -> dict:
    out = {"date": dt.date.today().isoformat(), "messages": len(rows), "systems": {}}
    for system in ("blocklist", "full"):
        items, by_tech = [], defaultdict(lambda: [0, 0])
        for r in rows:
            verdict, _ = predict(system, r)
            flagged = verdict in FLAG
            right = flagged == (r["label"] == "scam")
            items.append({"id": r["id"], "label": r["label"], "technique": r["technique"], "verdict": verdict, "right": right})
            by_tech[r["technique"]][0] += right
            by_tech[r["technique"]][1] += 1
        scams = [i for i in items if i["label"] == "scam"]
        genuine = [i for i in items if i["label"] == "genuine"]
        out["systems"][system] = {
            "scams_flagged": sum(i["right"] for i in scams), "scams": len(scams),
            "genuine_left_alone": sum(i["right"] for i in genuine), "genuine": len(genuine),
            "by_technique": {k: {"right": v[0], "n": v[1]} for k, v in sorted(by_tech.items())},
            "misses": [i for i in items if not i["right"]],
        }
    return out


def render(first: dict, latest: dict | None, notes: list[str], rows: dict) -> str:
    def line(name, s):
        return (f"| {name} | {s['scams_flagged']} / {s['scams']} ({100 * s['scams_flagged'] / s['scams']:.0f}%) | "
                f"{s['genuine_left_alone']} / {s['genuine']} ({100 * s['genuine_left_alone'] / s['genuine']:.0f}%) |")
    f, b = first["systems"]["full"], first["systems"]["blocklist"]
    md = [
        "# Red-team set v0",
        "",
        f"{first['messages']} messages written on 6 Oct 2026 to get past Sahayak ({f['scams']} disguised scams, "
        f"{f['genuine']} hard genuine messages), scored once on {first['date']} before any change. Each scam is a known "
        "scam disguised with one technique: hidden characters, spaced or look-alike letters, links written in words, a "
        "warning wrapped around the ask, a spoofed bank sender, short links, no link at all, newer scam types. The genuine "
        "messages share words with scams (OTPs for a delivery agent, bank awareness SMS, a shop offer on a short link). "
        "Reproduce: `python bench/build_redteam.py`, `python bench/eval_redteam.py --report`.",
        "",
        "## First run (the number to quote)",
        "",
        "| System | Disguised scams flagged | Genuine messages left alone |",
        "| --- | --- | --- |",
        line("Keyword blocklist (baseline)", b),
        line("Sahayak", f),
        "",
        "| Technique | Sahayak right | Blocklist right |",
        "| --- | --- | --- |",
    ]
    for tech, v in f["by_technique"].items():
        bv = b["by_technique"][tech]
        md.append(f"| {tech.replace('_', ' ')} | {v['right']} / {v['n']} | {bv['right']} / {bv['n']} |")
    md += ["", "Sahayak's misses on the first run:", ""]
    for m in f["misses"]:
        md.append(f"- {m['id']} ({m['technique']}, {m['label']}, read as {m['verdict']}): {rows[m['id']]['text'][:140]!r}")
    if latest:
        lf = latest["systems"]["full"]
        md += ["", "## Post-freeze log", ""] + [f"- {n}" for n in notes] + [
            "",
            f"Re-scored {latest['date']} after the changes above: {lf['scams_flagged']} / {lf['scams']} disguised scams flagged, "
            f"{lf['genuine_left_alone']} / {lf['genuine']} genuine messages left alone. These messages informed the fixes, so "
            "the re-score is not an unbiased test; the first run above stays the number to quote.",
        ]
        if lf["misses"]:
            md += ["", "Still missed:", ""] + [f"- {m['id']} ({m['technique']}, read as {m['verdict']})" for m in lf["misses"]]
    md += ["", "**What this does not show.** The set is small and written by the same team as the rules, so it finds blind "
           "spots rather than measuring a rate; a red team from outside the team is the next step."]
    return "\n".join(md) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--rerun-note", help="re-score after a fix; the note is added to the post-freeze log")
    args = ap.parse_args()
    rows = [json.loads(line) for line in SET.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {r["id"]: r for r in rows}
    path = RESULTS / "redteam_v0.json"
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    result = score(rows)
    if saved and args.rerun_note:
        first, notes = saved["first"], saved.get("notes", []) + [args.rerun_note]
        data = {"first": first, "latest": result, "notes": notes}
    elif saved and not args.rerun_note:
        print("first run already saved; pass --rerun-note to re-score after a change")
        data = {**saved, "check": result}
        first, notes = saved["first"], saved.get("notes", [])
    else:
        first, notes = result, []
        data = {"first": result, "latest": None, "notes": []}
    for name, s in result["systems"].items():
        print(f"{name}: scams flagged {s['scams_flagged']}/{s['scams']}, genuine left alone {s['genuine_left_alone']}/{s['genuine']}")
        if name == "full":
            for m in s["misses"]:
                print(f"   miss {m['id']} {m['technique']} {m['label']} -> {m['verdict']}")
    if args.report:
        data.pop("check", None)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        (RESULTS / "redteam_v0.md").write_text(render(data["first"], data.get("latest"), data.get("notes", []), by_id), encoding="utf-8")
        print(f"wrote {RESULTS / 'redteam_v0.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
