"""Score the blind red-team set v1: 182 messages written by a separate AI model that never saw Sahayak's code, rules
or test sets, from scam advisories of 2025-26 (bench/redteam/build_redteam_v1.py lists the techniques; the report lists
the sources). It is scored once, on the packs in place when it arrived; that first run is the number to quote.
Fixes made after it are logged under "Post-freeze log" and the set is re-scored, but the first numbers stay.

Three outcomes, not two. A scam is caught (Scam or Suspicious), missed (No scam signs), or not checked: Sahayak
said "could not check" because the message is in a language it cannot read yet. A genuine message is left alone,
flagged (a false alarm), or not checked. A QR item goes through the same path as a photographed QR on the node:
the UPI payload is analysed, then its text is checked.

Usage: python bench/eval_redteam_v1.py [--report] [--rerun-note "what changed"]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))

from eval_scambench import BLOCKLIST  # noqa: E402
from sahayak.fraud.normalize import fold  # noqa: E402
from sahayak.fraud.pipeline import check_message_full  # noqa: E402
from sahayak.inputs.qr import analyse  # noqa: E402
from sahayak.packs import get_pack  # noqa: E402

SET = ROOT / "bench" / "redteam" / "redteam_v1_blind.jsonl"
RESULTS = ROOT / "bench" / "results"
OURS = {"hi", "en", "hinglish"}  # the languages Sahayak reads


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    """95% Wilson interval for k out of n (sound for small n, unlike a bootstrap that can reach 100%)."""
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def predict(system: str, row: dict) -> str:
    text, itype = row["text"], row.get("input_type", "text")
    if itype == "qr":  # as /api/qr: what the code really does, then the usual check
        text = analyse(text)["check_text"]
    if system == "blocklist":
        t = fold(text)
        return "scam" if any(k in t for k in BLOCKLIST) else "no_signs"
    card, _ = check_message_full(text, sender=row.get("sender"), input_type=itype)
    return card["verdict"]


def outcome(label: str, verdict: str) -> str:
    if verdict == "unreadable":
        return "not_checked"
    flagged = verdict in ("scam", "suspicious")
    if label == "scam":
        return "caught" if flagged else "missed"
    return "false_alarm" if flagged else "left_alone"


def tally(items: list[dict]) -> dict:
    out = defaultdict(int)
    for i in items:
        out[i["outcome"]] += 1
    out["scams"] = sum(1 for i in items if i["label"] == "scam")
    out["genuine"] = sum(1 for i in items if i["label"] == "genuine")
    out["caught_ci"] = wilson(out["caught"], out["scams"])
    out["false_alarm_ci"] = wilson(out["false_alarm"], out["genuine"])
    return dict(out)


def score(rows: list[dict]) -> dict:
    packs = {p: get_pack(p).version for p in ("fraud", "scam_patterns", "fraud_model")}
    out = {"date": dt.date.today().isoformat(), "messages": len(rows), "packs": packs, "systems": {}}
    for system in ("blocklist", "full"):
        items = []
        for r in rows:
            verdict = predict(system, r)
            items.append({"id": r["id"], "label": r["label"], "category": r["category"], "lang": r["lang"],
                          "input_type": r["input_type"], "verdict": verdict, "outcome": outcome(r["label"], verdict)})
        groups = {
            "all": items,
            "hindi_english_hinglish": [i for i in items if i["lang"] in OURS],
            "other_indian_languages": [i for i in items if i["lang"] not in OURS],
        }
        by_type = {t: tally([i for i in items if i["input_type"] == t]) for t in sorted({i["input_type"] for i in items})}
        by_cat = defaultdict(lambda: defaultdict(int))
        for i in items:
            by_cat[(i["label"], i["category"])][i["outcome"]] += 1
        out["systems"][system] = {
            "groups": {g: tally(v) for g, v in groups.items()},
            "by_input_type": by_type,
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
    f, b = first["systems"]["full"], first["systems"]["blocklist"]
    fa, ba = f["groups"]["all"], b["groups"]["all"]
    fo, bo = f["groups"]["hindi_english_hinglish"], b["groups"]["hindi_english_hinglish"]
    fx = f["groups"]["other_indian_languages"]
    md = [
        "# Blind red-team set v1",
        "",
        f"{first['messages']} messages ({fa['scams']} scams, {fa['genuine']} genuine) written on 6–7 Oct 2026 by a separate "
        "AI model working blind (it never saw Sahayak's code, rules, packs or test sets), from 2025–26 scam advisories (I4C, police, banks, "
        "news). The genuine messages are deliberately hard: real OTPs for a delivery agent, the government's own 'there is "
        "no digital arrest' message, bank alerts, a gas-booking code. 15 scams and 5 genuine messages are in Indian "
        "languages Sahayak does not read yet (Tamil, Telugu, Bengali, Marathi, Malayalam, Gujarati, Kannada, Punjabi, "
        f"Odia, Urdu). Scored once on {first['date']}, on fraud pack {first['packs']['fraud']}, before anyone on the team "
        "read the messages. Reproduce: `python bench/redteam/build_redteam_v1.py`, `python bench/eval_redteam_v1.py --report`.",
        "",
        "## First run (the numbers to quote)",
        "",
        "A scam counts as caught when Sahayak says Scam or Suspicious. \"Not checked\" means Sahayak said it could not "
        "read the language and gave the safe-default advice instead of a verdict.",
        "",
        "| | Scams caught | Scams missed | Scams not checked | Genuine flagged (false alarm) | Genuine not checked |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| Sahayak, Hindi, English, Hinglish | {pct(fo.get('caught', 0), fo['scams'])} (95% CI {ci(fo['caught_ci'])}) | "
        f"{fo.get('missed', 0)} | {fo.get('not_checked', 0)} | {pct(fo.get('false_alarm', 0), fo['genuine'])} "
        f"(95% CI {ci(fo['false_alarm_ci'])}) | {fo.get('not_checked', 0) and sum(1 for i in f['not_checked'] if i['label'] == 'genuine' and i['lang'] in OURS)} |",
        f"| Keyword blocklist, same messages | {pct(bo.get('caught', 0), bo['scams'])} | {bo.get('missed', 0)} | – | "
        f"{pct(bo.get('false_alarm', 0), bo['genuine'])} | – |",
        f"| Sahayak, other Indian languages | {pct(fx.get('caught', 0), fx['scams'])} | {fx.get('missed', 0)} | "
        f"{fx.get('not_checked', 0) - sum(1 for i in f['not_checked'] if i['label'] == 'genuine' and i['lang'] not in OURS)} | "
        f"{pct(fx.get('false_alarm', 0), fx['genuine'])} | "
        f"{sum(1 for i in f['not_checked'] if i['label'] == 'genuine' and i['lang'] not in OURS)} |",
        f"| Sahayak, all {fa['scams'] + fa['genuine']} | {pct(fa.get('caught', 0), fa['scams'])} | {fa.get('missed', 0)} | "
        f"{sum(1 for i in f['not_checked'] if i['label'] == 'scam')} | {pct(fa.get('false_alarm', 0), fa['genuine'])} | "
        f"{sum(1 for i in f['not_checked'] if i['label'] == 'genuine')} |",
        f"| Keyword blocklist, all | {pct(ba.get('caught', 0), ba['scams'])} | {ba.get('missed', 0)} | – | "
        f"{pct(ba.get('false_alarm', 0), ba['genuine'])} | – |",
        "",
        "By input type (Sahayak, all languages):",
        "",
        "| Input | Scams caught | Genuine flagged |",
        "| --- | --- | --- |",
    ]
    for t, v in f["by_input_type"].items():
        md.append(f"| {t} | {pct(v.get('caught', 0), v['scams'])} | {pct(v.get('false_alarm', 0), v['genuine'])} |")
    md += ["", "Sahayak's wrong answers on the first run (missed scams and false alarms):", ""]
    for m in f["wrong"]:
        r = rows[m["id"]]
        md.append(f"- {m['id']} ({m['label']}, {m['category']}, {m['lang']}, {m['input_type']}; read as {m['verdict']}): "
                  f"{r['text'][:150]!r}")
    if latest:
        lf = latest["systems"]["full"]["groups"]
        md += ["", "## Post-freeze log", ""] + [f"- {n}" for n in notes] + [
            "",
            f"Re-scored {latest['date']} on fraud pack {latest['packs']['fraud']}: Hindi/English/Hinglish scams caught "
            f"{pct(lf['hindi_english_hinglish'].get('caught', 0), lf['hindi_english_hinglish']['scams'])}, genuine flagged "
            f"{pct(lf['hindi_english_hinglish'].get('false_alarm', 0), lf['hindi_english_hinglish']['genuine'])}. These "
            "messages informed the fixes, so the re-score is not an unbiased test; the first run stays the number to quote.",
        ]
    md += ["", "**What this does not show.** The messages are realistic but written for the test, not received by real "
           "people; real messages collected with consent (ScamBench v1) and the field morning are the next steps. A "
           "\"could not check\" protects a person from a false green, but it does not protect them from the scam: "
           "reading more languages is on the roadmap."]
    return "\n".join(md) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--rerun-note", help="re-score after a fix; the note is added to the post-freeze log")
    args = ap.parse_args()
    rows = [json.loads(line) for line in SET.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {r["id"]: r for r in rows}
    path = RESULTS / "redteam_v1_blind.json"
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
        for g, v in s["groups"].items():
            print(f"{name:9s} {g:24s} caught {v.get('caught', 0)}/{v['scams']} missed {v.get('missed', 0)} "
                  f"false alarms {v.get('false_alarm', 0)}/{v['genuine']} not checked {v.get('not_checked', 0)}")
    if args.report:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        (RESULTS / "redteam_v1_blind.md").write_text(
            render(data["first"], data.get("latest"), data.get("notes", []), by_id), encoding="utf-8")
        print(f"wrote {RESULTS / 'redteam_v1_blind.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
