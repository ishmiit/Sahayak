"""Voice latency on the node: from the moment a person lets go of the mic button to the moment
the reply's first audio is ready, for spoken Benefits Navigator answers.

The chain is the app's own: POST /api/asr (recognise and match) -> POST /api/navigator/next ->
POST /api/tts for the next question's first sentence. Measured twice: with the speech cache
(fixed sentences are pre-synthesised, the normal case) and with it bypassed (every sentence
synthesised live, the worst case). PRD targets: first audio within 4 s, within 2 s when templated.

Usage: python bench/voice_latency.py [--runs 3] [--report]   (the node must be running)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import statistics
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "bench" / "results"
BASE = "http://127.0.0.1:8000"

# (question, shown options, what the person says, the answers given before this question)
CASES = [
    ("age", None, "मेरी उम्र पैंसठ साल है", {}),
    ("situation", "widow,disability80,earner_died", "मैं विधवा हूँ", {"age": 65}),
    ("ration", "aay,bpl_phh,apl,none,dont_know", "अंत्योदय कार्ड है", {"age": 65, "situation": ["widow"]}),
    ("bank", "yes,no,dont_know", "हाँ, खाता है", {"age": 65, "situation": ["widow"], "ration": "aay"}),
]


def post(path: str, body: bytes, ctype: str) -> tuple[bytes, dict]:
    req = urllib.request.Request(BASE + path, data=body, headers={"Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), dict(r.headers)


def post_json(path: str, obj: dict) -> tuple[bytes, dict]:
    return post(path, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json")


def first_sentence(text: str) -> str:
    return re.split(r"(?<=[।.?!])\s+", text.strip())[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    # the spoken answers, made once with the node's own voice (male, so the female cache is not touched)
    clips = {said: post_json("/api/tts", {"text": said, "lang": "hi", "voice": "male", "speed": 1.0})[0]
             for _, _, said, _ in CASES}
    rows = []
    for run in range(args.runs):
        for mode in ("cached", "live"):
            for qid, options, said, before in CASES:
                t0 = time.perf_counter()
                params = f"lang=hi&question={qid}" + (f"&options={options}" if options else "")
                out = json.loads(post(f"/api/asr?{params}", clips[said], "audio/wav")[0])
                t_asr = time.perf_counter() - t0
                answers = {**before, qid: out["answer"]}
                nxt = json.loads(post_json("/api/navigator/next", {"answers": answers})[0])
                text = first_sentence(nxt["question"]["text"]["hi"]) if nxt["question"] else "धन्यवाद"
                # "live" changes the text and the speed slightly so the sentence misses both caches
                speech, speed = (text, 0.9) if mode == "cached" else (f"{text} जी", round(0.89 - 0.01 * run, 2))
                _, headers = post_json("/api/tts", {"text": speech, "lang": "hi", "voice": "female", "speed": speed})
                total = time.perf_counter() - t0
                rows.append({"run": run, "mode": mode, "question": qid, "answer": out["answer"], "asr_s": round(t_asr, 3),
                             "first_audio_s": round(total, 3), "tts_cache": headers.get("X-Sahayak-Cached", "")})
    summary = {"date": dt.date.today().isoformat(), "runs": args.runs, "cases": len(CASES)}
    for mode in ("cached", "live"):
        xs = sorted(r["first_audio_s"] for r in rows if r["mode"] == mode)
        asr = [r["asr_s"] for r in rows if r["mode"] == mode]
        summary[mode] = {"n": len(xs), "p50": round(statistics.median(xs), 2), "max": round(max(xs), 2),
                         "asr_p50": round(statistics.median(asr), 2)}
        print(f"{mode}: release -> first audio p50 {summary[mode]['p50']} s, max {summary[mode]['max']} s "
              f"(recognition p50 {summary[mode]['asr_p50']} s) over {len(xs)} answers")
    wrong = [r for r in rows if r["answer"] is None]
    summary["unrecognised"] = len(wrong)
    if args.report:
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "voice_latency.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
        c, lv = summary["cached"], summary["live"]
        md = [
            "# Voice latency on the node", "",
            f"Run {summary['date']} on the dev laptop (Intel i5-10210U, 4 cores, no GPU), node and models local. "
            "Time from releasing the mic to the reply's first audio being ready: recognise and match the answer, pick the "
            "next question, synthesise its first sentence. Reproduce with `python bench/voice_latency.py --report`.", "",
            "| Case | Median | Worst | Target |", "| --- | --- | --- | --- |",
            f"| Reply from the speech cache (fixed sentences, the normal case) | {c['p50']} s | {c['max']} s | ≤ 2 s |",
            f"| Reply synthesised live (worst case) | {lv['p50']} s | {lv['max']} s | ≤ 4 s |",
            "", f"Recognition alone took a median {c['asr_p50']} s. {summary['unrecognised']} of {len(rows)} spoken answers "
            "were not matched to an option.", "",
            "The spoken answers here are the node's own synthesised voice, so this measures speed, not accuracy; accuracy "
            "is VoiceBench's job (real speakers).", "",
        ]
        (RESULTS / "voice_latency.md").write_text("\n".join(md), encoding="utf-8")
        print(f"wrote {RESULTS / 'voice_latency.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
