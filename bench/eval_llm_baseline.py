"""Why not just ask an AI model? A measured answer: a small local language model, asked zero-shot whether each
message is a scam, on the same messages as Sahayak.

Round 1 of the challenge proposed a large offline language model as the detector. The prototype decides with
signals, a pattern matcher and a small classifier instead, and keeps a model only for optional plain-language
explanations. This script measures the road not taken: qwen2.5:3b (the largest model that ran on the team's
laptop at a usable speed) through Ollama, temperature 0, a fixed prompt, the message's sender and channel given
as Sahayak gets them. Sets: ScamBench v0 test split (the 60 messages behind the headline number) and the blind
red-team set v1 (182 messages, 20 in languages Sahayak does not read).

The model runs on whatever Ollama uses on the machine: on the dev Mac that is the Apple GPU (Metal), which is
much faster than the CPU-only laptop a CSC node would have, so the seconds here flatter the model.

Usage: ollama serve; ollama pull qwen2.5:3b; python bench/eval_llm_baseline.py [--model qwen2.5:3b] [--report]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))

from eval_redteam_v1 import wilson  # noqa: E402
from sahayak.fraud.pipeline import check_message_full  # noqa: E402
from sahayak.inputs.qr import analyse  # noqa: E402
from sahayak.packs import get_pack  # noqa: E402

RESULTS = ROOT / "bench" / "results"
SYSTEM = (
    "You check messages for people in India who are new to digital money. You will see one message (an SMS, a "
    "WhatsApp message, a description of a phone call, or the text inside a UPI QR code), with its sender when known. "
    "Decide whether it is a scam or fraud attempt, or a genuine message. Genuine messages include real bank alerts and "
    "OTPs, real government and shop notices, and ordinary messages from family and employers. Answer only with JSON."
)
SCHEMA = {"type": "object", "properties": {"label": {"type": "string", "enum": ["scam", "genuine"]},
                                           "reason": {"type": "string"}}, "required": ["label", "reason"]}
CHANNEL = {"text": "SMS or chat message", "call": "description of a phone call", "qr": "text inside a UPI QR code",
           "voice": "spoken message", "ocr": "screenshot text"}


def load(path: Path, split: str | None = None) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if split is None or r.get("split") == split]


def ask(model: str, url: str, row: dict) -> tuple[str, float, str]:
    itype = row.get("input_type", "text")
    text = analyse(row["text"])["check_text"] if itype == "qr" else row["text"]
    user = (f"Channel: {CHANNEL.get(itype, 'message')}\nSender: {row.get('sender') or 'unknown'}\n"
            f"Message:\n<<<\n{text}\n>>>\nIs this a scam or genuine?")
    body = {"model": model, "stream": False, "format": SCHEMA, "keep_alive": "30m",
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            "options": {"temperature": 0, "num_predict": 120, "seed": 7}}
    t0 = time.perf_counter()
    r = httpx.post(f"{url}/api/chat", json=body, timeout=300)
    seconds = time.perf_counter() - t0
    r.raise_for_status()
    try:
        out = json.loads(r.json()["message"]["content"])
        label = out.get("label", "genuine")
    except (json.JSONDecodeError, KeyError, TypeError):
        label, out = "unparsed", {}
    return label, seconds, str(out.get("reason", ""))[:200]


def sahayak(row: dict) -> str:
    itype = row.get("input_type", "text")
    text = analyse(row["text"])["check_text"] if itype == "qr" else row["text"]
    return check_message_full(text, sender=row.get("sender"), input_type=itype)[0]["verdict"]


def score(rows: list[dict], preds: list[str], flagged) -> dict:
    scams = [p for r, p in zip(rows, preds) if r["label"] == "scam"]
    genuine = [p for r, p in zip(rows, preds) if r["label"] == "genuine"]
    caught, alarms = sum(map(flagged, scams)), sum(map(flagged, genuine))
    return {"scams": len(scams), "caught": caught, "caught_ci": wilson(caught, len(scams)),
            "genuine": len(genuine), "false_alarms": alarms, "false_alarm_ci": wilson(alarms, len(genuine))}


def hardware() -> str:
    try:
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    except OSError:
        chip = ""
    return f"{chip or platform.processor()} ({platform.system()} {platform.machine()})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--url", default="http://127.0.0.1:11434")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--only", help="comma list of sets to run; the others are kept from the saved results")
    args = ap.parse_args()
    sets = {
        "scambench_v0_test": load(ROOT / "bench" / "scambench" / "scambench_v0.jsonl", "test"),
        "redteam_v1_blind": load(ROOT / "bench" / "redteam" / "redteam_v1_blind.jsonl"),
        "public_v0": load(ROOT / "bench" / "public" / "public_messages_v0.jsonl"),
    }
    saved = RESULTS / "llm_baseline.json"
    if args.only:
        sets = {k: v for k, v in sets.items() if k in args.only.split(",")}
    ask(args.model, args.url, {"text": "warm up", "label": "genuine"})  # load the model before timing
    out = {"date": dt.date.today().isoformat(), "model": args.model, "hardware": hardware(),
           "fraud_pack": get_pack("fraud").version, "sets": {}}
    if args.only and saved.exists():  # keep the sets not re-run, with the pack they were run on
        old = json.loads(saved.read_text(encoding="utf-8"))
        out["sets"] = {k: dict(v, fraud_pack=v.get("fraud_pack", old.get("fraud_pack"))) for k, v in old["sets"].items()}
    for name, rows in sets.items():
        llm, secs, reasons = [], [], []
        for i, r in enumerate(rows):
            label, s, why = ask(args.model, args.url, r)
            llm.append(label), secs.append(s), reasons.append(why)
            if (i + 1) % 20 == 0:
                print(f"  {name}: {i + 1}/{len(rows)}", flush=True)
        ours = [sahayak(r) for r in rows]
        t_ours = []
        for r in rows[:60]:
            t0 = time.perf_counter()
            sahayak(r)
            t_ours.append(time.perf_counter() - t0)
        res = {"n": len(rows),
               "llm": score(rows, llm, lambda p: p == "scam"),
               "sahayak": score(rows, ours, lambda p: p in ("scam", "suspicious")),
               "sahayak_could_not_check": sum(1 for p in ours if p == "unreadable"),
               "llm_unparsed": sum(1 for p in llm if p == "unparsed"),
               "llm_seconds": {"median": round(statistics.median(secs), 2), "p95": round(sorted(secs)[int(0.95 * len(secs)) - 1], 2),
                               "max": round(max(secs), 2)},
               "sahayak_ms_median": round(1000 * statistics.median(t_ours), 2),
               "items": [{"id": r["id"], "label": r["label"], "lang": r.get("lang"), "llm": p, "sahayak": o, "llm_reason": w}
                         for r, p, o, w in zip(rows, llm, ours, reasons)]}
        res["fraud_pack"] = get_pack("fraud").version
        if name in ("redteam_v1_blind", "public_v0"):
            ours_langs = {"hi", "en", "hinglish"}
            idx = [i for i, r in enumerate(rows) if r.get("lang") not in ours_langs]
            sub = [rows[i] for i in idx]
            res["other_languages"] = {"llm": score(sub, [llm[i] for i in idx], lambda p: p == "scam"),
                                      "sahayak": score(sub, [ours[i] for i in idx], lambda p: p in ("scam", "suspicious"))}
        out["sets"][name] = res
        l, s = res["llm"], res["sahayak"]
        print(f"{name}: LLM caught {l['caught']}/{l['scams']}, false alarms {l['false_alarms']}/{l['genuine']}, "
              f"median {res['llm_seconds']['median']} s | Sahayak caught {s['caught']}/{s['scams']}, false alarms "
              f"{s['false_alarms']}/{s['genuine']}, median {res['sahayak_ms_median']} ms")
    if args.report:
        (RESULTS / "llm_baseline.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        (RESULTS / "llm_baseline.md").write_text(render(out), encoding="utf-8")
        print(f"wrote {RESULTS / 'llm_baseline.md'}")
    return 0


def render(out: dict) -> str:
    def pct(k, n):
        return f"{k} / {n} ({100 * k / n:.0f}%)" if n else "–"

    def ci(v):
        return f"{100 * v[0]:.0f}–{100 * v[1]:.0f}%"
    md = ["# Why not just ask an AI model? (LLM baseline)", "",
          f"{out['model']} through Ollama, zero-shot, temperature 0, one fixed prompt (bench/eval_llm_baseline.py), "
          f"on {out['hardware']}, {out['date']}. Sahayak: fraud pack {out['fraud_pack']}, on the same messages. A message "
          "counts as caught when the model says scam, or when Sahayak says Scam or Suspicious.", "",
          "| Set | System | Scams caught (95% CI) | False alarms on genuine (95% CI) | Time per message |",
          "| --- | --- | --- | --- | --- |"]
    for name, res in out["sets"].items():
        l, s = res["llm"], res["sahayak"]
        md.append(f"| {name} | {out['model']} | {pct(l['caught'], l['scams'])} ({ci(l['caught_ci'])}) | "
                  f"{pct(l['false_alarms'], l['genuine'])} ({ci(l['false_alarm_ci'])}) | median {res['llm_seconds']['median']} s, "
                  f"max {res['llm_seconds']['max']} s |")
        md.append(f"| {name} | Sahayak | {pct(s['caught'], s['scams'])} ({ci(s['caught_ci'])}) | "
                  f"{pct(s['false_alarms'], s['genuine'])} ({ci(s['false_alarm_ci'])}) | median {res['sahayak_ms_median']} ms |")
        if "other_languages" in res:
            ol, os_ = res["other_languages"]["llm"], res["other_languages"]["sahayak"]
            md.append(f"| {name}, other Indian languages only | {out['model']} | {pct(ol['caught'], ol['scams'])} | "
                      f"{pct(ol['false_alarms'], ol['genuine'])} | |")
            md.append(f"| {name}, other Indian languages only | Sahayak | {pct(os_['caught'], os_['scams'])} "
                      f"(the rest: could not check) | {pct(os_['false_alarms'], os_['genuine'])} | |")
    md += ["", "**Reading it.** The model ran on the dev Mac's GPU (Metal); a CSC node's CPU is several times slower, so "
           "the model's seconds here are a best case. Sahayak's time is for the whole check on the same Mac's CPU.", "",
           "**What this does not show.** One small model, one prompt, no tuning; a larger model or a tuned prompt may do "
           "better, and the messages were written for the test, not received by real people."]
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    sys.exit(main())
