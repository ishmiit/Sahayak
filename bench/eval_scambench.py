"""Evaluate Fraud-Shield on ScamBench with 95% bootstrap intervals and an ablation.

Systems compared on the same messages:
  blocklist  a naive keyword filter (the baseline most "spam" checkers resemble)
  signals    Sahayak's signal layer only
  patterns   signals + similarity to known scams (pattern pack)
  full       signals + patterns + classifier (no LLM; the LLM never decides a verdict)

A message counts as "flagged" when the verdict is Scam or Suspicious (the app warns in
both). Precision, recall, F1 and the false-alarm rate on genuine messages get 95%
bootstrap intervals (10,000 resamples). McNemar's exact test compares full vs blocklist.

Usage:
  python bench/eval_scambench.py --split dev           # tune on train/dev only
  python bench/eval_scambench.py --split test --report # the final, frozen number
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.fraud.normalize import fold  # noqa: E402
from sahayak.fraud.pipeline import check_message_full  # noqa: E402

BENCH = ROOT / "bench" / "scambench" / "scambench_v0.jsonl"
RESULTS = ROOT / "bench" / "results"

BLOCKLIST = ["otp", "kyc", "lottery", "prize", "winner", "won", "click", "link", "http", "urgent", "blocked",
             "suspend", "refund", "loan", "job", "police", "arrest", "pin", "cvv", "password", "offer", "free",
             "cashback", "ओटीपी", "केवाईसी", "लॉटरी", "इनाम", "बंद", "पुलिस", "लोन"]
SYSTEMS = {
    "blocklist": None,
    "signals": dict(use_patterns=False, use_classifier=False),
    "patterns": dict(use_patterns=True, use_classifier=False),
    "full": dict(use_patterns=True, use_classifier=True),
}


def load(splits: list[str]) -> list[dict]:
    rows = [json.loads(line) for line in BENCH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if r["split"] in splits]


def predict(system: str, row: dict) -> tuple[str, float]:
    if system == "blocklist":
        t = fold(row["text"])
        return ("scam" if any(k in t for k in BLOCKLIST) else "no_signs"), 0.0
    t0 = time.perf_counter()
    card, _ = check_message_full(row["text"], sender=row.get("sender"), input_type=row.get("input_type", "text"),
                                 **SYSTEMS[system])
    return card["verdict"], (time.perf_counter() - t0) * 1000


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    tp = int(((p == 1) & (y == 1)).sum()); fp = int(((p == 1) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum()); tn = int(((p == 0) & (y == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    far = fp / (fp + tn) if fp + tn else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "false_alarm_rate": far, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def bootstrap(y: np.ndarray, p: np.ndarray, n: int = 10_000, seed: int = 7) -> dict[str, list[float]]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(y), size=(n, len(y)))
    out = defaultdict(list)
    for row in idx:
        m = metrics(y[row], p[row])
        for k in ("precision", "recall", "f1", "false_alarm_rate"):
            out[k].append(m[k])
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in out.items()}


def mcnemar(y: np.ndarray, a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    a_ok, b_ok = a == y, b == y
    only_a, only_b = int((a_ok & ~b_ok).sum()), int((~a_ok & b_ok).sum())
    p = binomtest(min(only_a, only_b), only_a + only_b, 0.5).pvalue if only_a + only_b else 1.0
    return {"full_right_baseline_wrong": only_a, "baseline_right_full_wrong": only_b, "p_value": float(p)}


def run(splits: list[str], write_report: bool) -> dict:
    rows = load(splits)
    y = np.array([1 if r["label"] == "scam" else 0 for r in rows])
    results, preds, latencies = {}, {}, {}
    for system in SYSTEMS:
        verdicts, lat = zip(*(predict(system, r) for r in rows))
        flagged = np.array([1 if v != "no_signs" else 0 for v in verdicts])
        strict = np.array([1 if v == "scam" else 0 for v in verdicts])
        preds[system] = flagged
        results[system] = {
            "flagged": metrics(y, flagged), "flagged_ci95": bootstrap(y, flagged),
            "strict_scam": metrics(y, strict),
            "by_lang": {lang: metrics(y[[i for i, r in enumerate(rows) if r["lang"] == lang]],
                                      flagged[[i for i, r in enumerate(rows) if r["lang"] == lang]])
                        for lang in ("en", "hi", "hinglish")},
            "recall_by_category": {},
            "misses": [], "false_alarms": [],
        }
        cats = defaultdict(list)
        for i, r in enumerate(rows):
            if r["label"] == "scam":
                cats[r["category"]].append(flagged[i])
                if not flagged[i]:
                    results[system]["misses"].append(r["id"])
            elif flagged[i]:
                results[system]["false_alarms"].append(r["id"])
        results[system]["recall_by_category"] = {c: float(np.mean(v)) for c, v in sorted(cats.items())}
        if system != "blocklist":
            latencies[system] = lat
    out = {
        "bench": BENCH.name, "splits": splits, "n": len(rows), "n_scam": int(y.sum()), "n_genuine": int(len(y) - y.sum()),
        "date": dt.date.today().isoformat(), "systems": results,
        "mcnemar_full_vs_blocklist": mcnemar(y, preds["full"], preds["blocklist"]),
        "latency_ms_full": {"p50": float(np.percentile(latencies["full"], 50)), "p95": float(np.percentile(latencies["full"], 95))},
    }
    if write_report:
        RESULTS.mkdir(parents=True, exist_ok=True)
        tag = "-".join(splits)
        (RESULTS / f"scambench_v0_{tag}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        (RESULTS / f"scambench_v0_{tag}.md").write_text(render_markdown(out), encoding="utf-8")
    return out


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def render_markdown(out: dict) -> str:
    s = out["systems"]
    lines = [
        f"# ScamBench v0 results ({', '.join(out['splits'])} split)",
        "",
        f"{out['n']} messages ({out['n_scam']} scam, {out['n_genuine']} genuine), evaluated {out['date']}. "
        "A message is flagged when the verdict is Scam or Suspicious. Intervals are 95% bootstrap (10,000 resamples).",
        "",
        "| System | Recall | Precision | F1 | False alarms on genuine |",
        "| --- | --- | --- | --- | --- |",
    ]
    names = {"blocklist": "Keyword blocklist (baseline)", "signals": "Signals only", "patterns": "Signals + pattern match",
             "full": "Full: signals + patterns + classifier"}
    for k, label in names.items():
        m, ci = s[k]["flagged"], s[k]["flagged_ci95"]
        lines.append(f"| {label} | {pct(m['recall'])} ({pct(ci['recall'][0])}–{pct(ci['recall'][1])}) | "
                     f"{pct(m['precision'])} ({pct(ci['precision'][0])}–{pct(ci['precision'][1])}) | "
                     f"{pct(m['f1'])} ({pct(ci['f1'][0])}–{pct(ci['f1'][1])}) | "
                     f"{pct(m['false_alarm_rate'])} ({pct(ci['false_alarm_rate'][0])}–{pct(ci['false_alarm_rate'][1])}) |")
    mc = out["mcnemar_full_vs_blocklist"]
    lines += [
        "",
        f"McNemar exact test, full vs blocklist: full right where the blocklist was wrong on {mc['full_right_baseline_wrong']} "
        f"messages, the reverse on {mc['baseline_right_full_wrong']}; p = {mc['p_value']:.2g}.",
        f"Full-system latency on this laptop: p50 {out['latency_ms_full']['p50']:.1f} ms, p95 {out['latency_ms_full']['p95']:.1f} ms.",
        "",
        "## Full system by language",
        "",
        "| Language | Recall | Precision | F1 | False alarms |",
        "| --- | --- | --- | --- | --- |",
        *[f"| {lang} | {pct(m['recall'])} | {pct(m['precision'])} | {pct(m['f1'])} | {pct(m['false_alarm_rate'])} |"
          for lang, m in s["full"]["by_lang"].items()],
        "",
        "## Full system recall by scam category",
        "",
        "| Category | Recall |",
        "| --- | --- |",
        *[f"| {c} | {pct(v)} |" for c, v in s["full"]["recall_by_category"].items()],
        "",
        f"Missed scams: {', '.join(s['full']['misses']) or 'none'}. False alarms: {', '.join(s['full']['false_alarms']) or 'none'}.",
        "",
        "**Caveat.** ScamBench v0 was written by the team that wrote the rules, so these numbers are optimistic. "
        "v1 adds real messages collected with consent and is the honest test.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", help="comma list: train,dev,test")
    ap.add_argument("--report", action="store_true", help="write bench/results files")
    ap.add_argument("--show", default="", help="print misses/false alarms for this system")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    result = run(args.split.split(","), args.report)
    print(render_markdown(result))
    if args.show:
        rows = {r["id"]: r for r in load(args.split.split(","))}
        for kind in ("misses", "false_alarms"):
            print(f"\n--- {args.show} {kind}")
            for rid in result["systems"][args.show][kind]:
                r = rows[rid]
                card, _ = check_message_full(r["text"], sender=r.get("sender"), input_type=r.get("input_type", "text"),
                                             **(SYSTEMS[args.show] or {}))
                print(f"{rid} [{r['category']}/{r['lang']}] {card['verdict']} risk={card['risk_score']} "
                      f"{[x['id'] for x in card['signals']]}\n    {r['text'][:160]}")
