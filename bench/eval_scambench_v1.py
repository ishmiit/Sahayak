"""Score ScamBench v1: real messages people received and shared with consent (bench/scambench/COLLECTING.md).

The messages stay in bench/scambench/private/scambench_v1.jsonl, which git never sees; only counts and message ids go
into bench/results/scambench_v1.json and .md, never message text. Every row must have been through
bench/redact_messages.py and read by a person ("redacted": true); the script refuses the file otherwise.

As with PublicBench: scored once, and that first run is the number to quote. The set is split in two by a fixed hash
of each id before anyone reads an error; fixes may learn from the "dev" half only, and the "test" half's messages stay
unread, so its score after the fixes is a fair estimate of the improvement. Later runs need --rerun-note.

Rows: {"id": "v1-001", "text": ..., "sender": optional, "input_type": "text" | "call" | "qr", "label": "scam" | "genuine",
"category": optional, "lang": "hi" | "en" | "hinglish" | other, "source": "field" | "friends" | ..., "redacted": true}

Usage: python bench/eval_scambench_v1.py [--report] [--rerun-note "what changed"] [--set <path>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))

from eval_public_v0 import half  # noqa: E402
from eval_redteam_v1 import OURS, outcome, predict, tally  # noqa: E402
from sahayak.packs import get_pack  # noqa: E402

SET = ROOT / "bench" / "scambench" / "private" / "scambench_v1.jsonl"
RESULTS = ROOT / "bench" / "results"


def score(rows: list[dict]) -> dict:
    packs = {p: get_pack(p).version for p in ("fraud", "scam_patterns", "fraud_model")}
    out = {"date": dt.date.today().isoformat(), "messages": len(rows), "packs": packs, "systems": {}}
    for system in ("blocklist", "full"):
        items = []
        for r in rows:
            verdict = predict(system, r)
            items.append({"id": r["id"], "label": r["label"], "category": r.get("category", ""), "lang": r.get("lang", ""),
                          "input_type": r.get("input_type", "text"), "source": r.get("source", ""),
                          "half": half(r["id"]), "verdict": verdict, "outcome": outcome(r["label"], verdict)})
        groups = {
            "all": items,
            "hindi_english_hinglish": [i for i in items if i["lang"] in OURS],
            "other_indian_languages": [i for i in items if i["lang"] not in OURS],
            "dev_half": [i for i in items if i["half"] == "dev"],
            "test_half": [i for i in items if i["half"] == "test"],
        }
        out["systems"][system] = {
            "groups": {g: tally(v) for g, v in groups.items()},
            # ids only, and only from the dev half: the test half's errors stay unread
            "wrong_dev": [{k: i[k] for k in ("id", "label", "category", "lang", "input_type", "verdict")}
                          for i in items if i["half"] == "dev" and i["outcome"] in ("missed", "false_alarm")],
        }
    return out


def pct(k: int, n: int) -> str:
    return f"{k} / {n} ({100 * k / n:.0f}%)" if n else "0 / 0"


def ci(v: list[float]) -> str:
    return f"{100 * v[0]:.0f}–{100 * v[1]:.0f}%"


def render(first: dict, latest: dict | None, notes: list[str]) -> str:
    f, b = first["systems"]["full"]["groups"], first["systems"]["blocklist"]["groups"]
    o, bo, x = f["hindi_english_hinglish"], b["hindi_english_hinglish"], f["other_indian_languages"]
    md = [
        "# ScamBench v1: real messages shared with consent",
        "",
        f"{first['messages']} messages ({f['all']['scams']} scams, {f['all']['genuine']} genuine) that people received and "
        "chose to share, collected and redacted as `bench/scambench/COLLECTING.md` describes. The messages themselves are "
        f"not in the repository. Scored once on {first['date']}, on fraud pack {first['packs']['fraud']}.",
        "",
        "## First run (the numbers to quote)",
        "",
        "| | Scams caught | Genuine flagged (false alarm) | Not checked (other languages) |",
        "| --- | --- | --- | --- |",
        f"| Sahayak, Hindi, English, Hinglish | {pct(o.get('caught', 0), o['scams'])} (95% CI {ci(o['caught_ci'])}) | "
        f"{pct(o.get('false_alarm', 0), o['genuine'])} (95% CI {ci(o['false_alarm_ci'])}) | – |",
        f"| Keyword blocklist, same messages | {pct(bo.get('caught', 0), bo['scams'])} | "
        f"{pct(bo.get('false_alarm', 0), bo['genuine'])} | – |",
        f"| Sahayak, other Indian languages | {pct(x.get('caught', 0), x['scams'])} | "
        f"{pct(x.get('false_alarm', 0), x['genuine'])} | {x.get('not_checked', 0)} |",
        "",
        "Wrong answers in the dev half (ids only; the test half's stay unread): "
        + (", ".join(f"{w['id']} ({w['label']}, {w['category'] or 'no category'}, read as {w['verdict']})"
                     for w in first["systems"]["full"]["wrong_dev"]) or "none") + ".",
    ]
    if latest:
        t0, t1 = f["test_half"], latest["systems"]["full"]["groups"]["test_half"]
        md += ["", "## Post-freeze log", ""] + [f"- {n}" for n in notes] + [
            "",
            f"Re-scored {latest['date']} on fraud pack {latest['packs']['fraud']}. **Test half (never read, so a fair "
            f"estimate):** scams caught {pct(t0.get('caught', 0), t0['scams'])} before, {pct(t1.get('caught', 0), t1['scams'])} "
            f"after; genuine flagged {pct(t0.get('false_alarm', 0), t0['genuine'])} before, "
            f"{pct(t1.get('false_alarm', 0), t1['genuine'])} after. The first run stays the number to quote.",
        ]
    md += ["", "**What this does not show.** The people who shared messages are the ones the team could reach, so the set "
           "leans towards their towns, languages and phones. A message someone chose to share is one that worried them; "
           "the scams nobody noticed are not here."]
    return "\n".join(md) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--rerun-note", help="re-score after a fix; the note is added to the post-freeze log")
    ap.add_argument("--set", type=Path, default=SET)
    args = ap.parse_args()
    if not args.set.exists():
        print(f"no messages yet: {args.set} (bench/scambench/COLLECTING.md says how to collect them)")
        return 1
    rows = [json.loads(line) for line in args.set.read_text(encoding="utf-8").splitlines() if line.strip()]
    unredacted = [r.get("id", "?") for r in rows if r.get("redacted") is not True]
    if unredacted:
        raise SystemExit(f"{len(unredacted)} rows have not been redacted and read (e.g. {unredacted[:3]}); "
                         "run bench/redact_messages.py and read every message first")
    bad = [r.get("id", "?") for r in rows if r.get("label") not in ("scam", "genuine")]
    if bad:
        raise SystemExit(f"{len(bad)} rows have no scam/genuine label (e.g. {bad[:3]}); leave 'unsure' ones out")
    path = RESULTS / "scambench_v1.json"
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    result = score(rows)
    if saved and args.rerun_note:
        data = {"first": saved["first"], "latest": result, "notes": saved.get("notes", []) + [args.rerun_note]}
    elif saved:
        print("first run already saved; pass --rerun-note to re-score after a change")
        data = {**saved}
    else:
        data = {"first": result, "latest": None, "notes": []}
    for name, s in result["systems"].items():
        for g in ("all", "hindi_english_hinglish", "other_indian_languages", "test_half"):
            v = s["groups"][g]
            print(f"{name:9s} {g:24s} caught {v.get('caught', 0)}/{v['scams']} false alarms "
                  f"{v.get('false_alarm', 0)}/{v['genuine']} not checked {v.get('not_checked', 0)}")
    if args.report:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        (RESULTS / "scambench_v1.md").write_text(render(data["first"], data.get("latest"), data.get("notes", [])),
                                                 encoding="utf-8")
        print(f"wrote {RESULTS / 'scambench_v1.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
