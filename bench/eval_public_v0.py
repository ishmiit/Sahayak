"""Score PublicBench v0: real scam and genuine messages that Indian authorities, banks, courts and fact-checkers have
published (PIB Fact Check, the Income Tax portal's archive of its own SMS, consumer-court orders quoting bank SMS,
Vishvas News, Newschecker, BOOM and others). bench/public/DATA_CARD.md says how they were collected and edited;
bench/public/public_messages_v0.provenance.tsv traces each one to its screenshot or page.

Scored once, on the packs in place when the set arrived; that first run is the number to quote. Fixes made after it
are logged under "Post-freeze log" and the set is re-scored, but the first numbers stay. Outcomes as in the blind red
team (bench/eval_redteam_v1.py): caught / missed / could not check for scams; left alone / flagged / could not check
for genuine messages.

Usage: python bench/eval_public_v0.py [--report] [--rerun-note "what changed"]
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

from eval_redteam_v1 import OURS, outcome, predict, tally  # noqa: E402
from sahayak.packs import get_pack  # noqa: E402

SET = ROOT / "bench" / "public" / "public_messages_v0.jsonl"
RESULTS = ROOT / "bench" / "results"


def half(item_id: str) -> str:
    """A fixed split, made before anyone read an error: fixes may learn from the "dev" half only, and the "test"
    half's messages stay unread, so its score after the fixes is a fair estimate of the improvement."""
    import hashlib
    return "dev" if int(hashlib.sha256(item_id.encode()).hexdigest()[:8], 16) % 2 == 0 else "test"


def score(rows: list[dict]) -> dict:
    packs = {p: get_pack(p).version for p in ("fraud", "scam_patterns", "fraud_model")}
    out = {"date": dt.date.today().isoformat(), "messages": len(rows), "packs": packs, "systems": {}}
    for system in ("blocklist", "full"):
        items = []
        for r in rows:
            verdict = predict(system, r)
            items.append({"id": r["id"], "label": r["label"], "category": r["category"], "lang": r["lang"],
                          "input_type": r["input_type"], "verbatim": r["verbatim"], "half": half(r["id"]),
                          "verdict": verdict, "outcome": outcome(r["label"], verdict)})
        by_cat = defaultdict(lambda: defaultdict(int))
        for i in items:
            by_cat[(i["label"], i["category"])][i["outcome"]] += 1
        out["systems"][system] = {
            "groups": {
                "all": tally(items),
                "hindi_english_hinglish": tally([i for i in items if i["lang"] in OURS]),
                "other_indian_languages": tally([i for i in items if i["lang"] not in OURS]),
                "verbatim_only": tally([i for i in items if i["verbatim"]]),
                "text": tally([i for i in items if i["input_type"] == "text"]),
                "call": tally([i for i in items if i["input_type"] == "call"]),
                "dev_half": tally([i for i in items if i["half"] == "dev"]),
                "test_half": tally([i for i in items if i["half"] == "test"]),
            },
            "by_category": {f"{lab}:{cat}": dict(v) for (lab, cat), v in sorted(by_cat.items())},
            "wrong": [i for i in items if i["outcome"] in ("missed", "false_alarm")],
            "not_checked": [i for i in items if i["outcome"] == "not_checked"],
        }
    return out


def pct(k: int, n: int) -> str:
    return f"{k} / {n} ({100 * k / n:.0f}%)" if n else "0 / 0"


def ci(v: list[float]) -> str:
    return f"{100 * v[0]:.0f}–{100 * v[1]:.0f}%"


def render(first: dict, latest: dict | None, notes: list[str], rows: dict) -> str:
    f, b = first["systems"]["full"]["groups"], first["systems"]["blocklist"]["groups"]
    md = [
        "# PublicBench v0: real published messages",
        "",
        f"{first['messages']} messages ({f['all']['scams']} scams, {f['all']['genuine']} genuine) that authorities, banks, "
        "courts and fact-checkers have published, collected on 6–7 Oct 2026 by an AI research agent that never saw Sahayak's code, rules "
        f"or test sets. {sum(1 for r in rows.values() if r['verbatim'])} are word for word; the rest are call scripts told by "
        "victims or police, or an outlet's translation. Private names and every phone number were replaced with fictional "
        "ones of the same shape. Scored once on "
        f"{first['date']} (fraud pack {first['packs']['fraud']}), before anyone on the team read the messages. "
        "Reproduce: `python bench/eval_public_v0.py --report`; sources in `bench/public/`.",
        "",
        "## First run (the numbers to quote)",
        "",
        "| Messages | Scams caught (95% Wilson CI) | Scams missed | Could not check | Genuine flagged (95% Wilson CI) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key, name in (("all", "All"), ("hindi_english_hinglish", "Hindi, English, Hinglish"),
                      ("verbatim_only", "Word-for-word only"), ("text", "Text messages"), ("call", "Call scripts"),
                      ("other_indian_languages", "Other Indian languages"), ("dev_half", "Dev half (fixes may learn from it)"),
                      ("test_half", "Test half (kept unread)")):
        g = f[key]
        md.append(f"| {name} | {pct(g.get('caught', 0), g['scams'])} ({ci(g['caught_ci'])}) | {g.get('missed', 0)} | "
                  f"{g.get('not_checked', 0)} | {pct(g.get('false_alarm', 0), g['genuine'])} ({ci(g['false_alarm_ci'])}) |")
    md.append(f"| Keyword blocklist, all | {pct(b['all'].get('caught', 0), b['all']['scams'])} | {b['all'].get('missed', 0)} | – | "
              f"{pct(b['all'].get('false_alarm', 0), b['all']['genuine'])} |")
    wrong = first["systems"]["full"]["wrong"]
    md += ["", f"Sahayak's wrong answers on the first run, dev half only ({sum(1 for m in wrong if m.get('half') == 'test')} more "
           "in the test half are counted above but not listed, so that half stays unread until the fixes are done):", ""]
    for m in [m for m in wrong if m.get("half", half(m["id"])) == "dev"]:
        r = rows[m["id"]]
        md.append(f"- {m['id']} ({m['label']}, {m['category']}, {m['lang']}, {m['input_type']}{', verbatim' if m['verbatim'] else ''}; "
                  f"read as {m['verdict']}): {r['text'][:150]!r}")
    if latest:
        lf, lt = latest["systems"]["full"]["groups"]["all"], latest["systems"]["full"]["groups"]["test_half"]
        ft = first["systems"]["full"]["groups"]["test_half"]
        md += ["", "## Post-freeze log", ""] + [f"- {n}" for n in notes] + [
            "",
            f"Re-scored {latest['date']} on fraud pack {latest['packs']['fraud']}. **Test half (never read, so a fair "
            f"estimate):** scams caught {pct(ft.get('caught', 0), ft['scams'])} before, {pct(lt.get('caught', 0), lt['scams'])} "
            f"after; genuine flagged {pct(ft.get('false_alarm', 0), ft['genuine'])} before, "
            f"{pct(lt.get('false_alarm', 0), lt['genuine'])} after. All {latest['messages']} (the dev half informed the fixes): "
            f"{pct(lf.get('caught', 0), lf['scams'])} caught, {pct(lf.get('false_alarm', 0), lf['genuine'])} flagged. "
            "The first run stays the number to quote."]
    md += ["", "**What this does not show.** Published messages are the ones that went viral or reached a fact-checker, "
           "so they lean towards well-known scam types; nobody's own inbox is here. The genuine set is small and mostly "
           "English (Income Tax, bank and OTP messages). Consented messages from people's own phones (ScamBench v1) and "
           "the field morning remain the next steps."]
    return "\n".join(md) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--rerun-note", help="re-score after a fix; the note is added to the post-freeze log")
    args = ap.parse_args()
    rows = [json.loads(line) for line in SET.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {r["id"]: r for r in rows}
    path = RESULTS / "public_v0.json"
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
        for g in ("all", "hindi_english_hinglish", "verbatim_only", "call", "other_indian_languages", "dev_half", "test_half"):
            v = s["groups"][g]
            print(f"{name:9s} {g:24s} caught {v.get('caught', 0)}/{v['scams']} missed {v.get('missed', 0)} "
                  f"false alarms {v.get('false_alarm', 0)}/{v['genuine']} not checked {v.get('not_checked', 0)}")
    if args.report:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        (RESULTS / "public_v0.md").write_text(render(data["first"], data.get("latest"), data.get("notes", []), by_id),
                                              encoding="utf-8")
        print(f"wrote {RESULTS / 'public_v0.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
