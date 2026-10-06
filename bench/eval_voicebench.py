"""VoiceBench: how well the node hears people.

Two sources of speech:
  default        the team's consented recordings in %USERPROFILE%/.sahayak/data/voicebench/*/manifest.jsonl,
                 collected with the recorder at /app/voicebench.html (node started with SAHAYAK_VOICEBENCH=1)
  --fleurs [N]   public read speech: Google FLEURS Hindi test split (CC BY 4.0), first N utterances,
                 in %USERPROFILE%/.sahayak/data/fleurs/hi_in (fetch: see bench/voicebench/README.md)

Reports word error rate (over the whole set, with a 95% bootstrap interval over utterances),
the same by speaker group, answer accuracy for Navigator prompts (does the right option come
out, after the same open-then-grammar recognition the node uses), and recognition speed.

Usage: python bench/eval_voicebench.py [--fleurs [N]] [--model vosk-model-small-hi-0.22] [--report]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.config import get_settings  # noqa: E402
from sahayak.fraud.normalize import fold  # noqa: E402
from sahayak.navigator import get_navigator  # noqa: E402
from sahayak.voice.answers import grammar, match  # noqa: E402
from sahayak.voice.asr import MODELS, Listener  # noqa: E402
from sahayak.voice.numbers import words  # noqa: E402

RESULTS = ROOT / "bench" / "results"
_PUNCT = re.compile(r"[।॥,.?!;:\"'“”‘’()\[\]{}\-–—…/]")
_DIGITS = re.compile(r"\d+")


def norm_words(text: str, lang: str) -> list[str]:
    text = _DIGITS.sub(lambda m: f" {words(int(m.group()), lang)} ", text)
    return fold(_PUNCT.sub(" ", text)).split()


def edits(ref: list[str], hyp: list[str]) -> int:
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[len(hyp)]


def wer_ci(rows: list[dict], n_boot: int = 2000, seed: int = 7) -> tuple[float, float, float]:
    e, w = sum(r["edits"] for r in rows), sum(r["ref_words"] for r in rows)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        boots.append(sum(r["edits"] for r in sample) / max(1, sum(r["ref_words"] for r in sample)))
    boots.sort()
    return e / max(1, w), boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def load_audio(path: Path) -> tuple[bytes, float]:
    """16 kHz mono PCM from any WAV (FLEURS ships 32-bit float, the phone sends 16-bit)."""
    import numpy as np
    import soundfile as sf
    x, rate = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if rate != 16000:
        n = int(len(x) * 16000 / rate)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    return pcm, len(x) / 16000


def fleurs_items(limit: int | None) -> list[dict]:
    base = get_settings().home / "data" / "fleurs" / "hi_in"
    rows = list(csv.reader((base / "test.tsv").open(encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))
    items = [{"file": str(base / "test" / r[1]), "text": r[3], "lang": "hi", "group": {"gender": r[6]}} for r in rows]
    return items[:limit] if limit else items


def team_items() -> list[dict]:
    """Every recording in every session folder, joined to its prompt (what was read and, for a
    Navigator answer, which option is right) and to the session's speaker group."""
    prompts = {}
    for line in (ROOT / "bench" / "voicebench" / "prompts_v1.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            p = json.loads(line)
            prompts[p["id"]] = p
    items = []
    for meta in sorted((get_settings().data_dir / "voicebench").glob("*/session.json")):
        speaker = json.loads(meta.read_text(encoding="utf-8"))["speaker"]
        group = {"age": speaker.get("age_band", ""), "gender": speaker.get("gender", ""), "region": speaker.get("region", "")}
        for wav in sorted(meta.parent.glob("*.wav")):
            p = prompts.get(wav.stem)
            if p:
                items.append({**p, "file": str(wav), "group": {**group, "speaker": meta.parent.name}})
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fleurs", nargs="?", const=0, type=int, help="use FLEURS Hindi test (optionally first N)")
    ap.add_argument("--model", default=MODELS["hi"], help="Vosk model folder under the models directory")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    source = "fleurs_hi" if args.fleurs is not None else "team"
    items = fleurs_items(args.fleurs or None) if source == "fleurs_hi" else team_items()
    if not items:
        print("no recordings found: collect them with /app/voicebench.html (SAHAYAK_VOICEBENCH=1) or use --fleurs")
        return 1
    listener = Listener(get_settings().models_dir)
    MODELS["hi"] = args.model  # evaluate the chosen model through the node's own code path
    nav = get_navigator()

    rows, answers = [], []
    t_audio = t_asr = 0.0
    for i, it in enumerate(items, 1):
        pcm, seconds = load_audio(Path(it["file"]))
        t0 = time.perf_counter()
        out = listener.transcribe(pcm, it.get("lang", "hi"))
        t_asr += time.perf_counter() - t0
        t_audio += seconds
        ref, hyp = norm_words(it["text"], it.get("lang", "hi")), norm_words(out["text"], it.get("lang", "hi"))
        rows.append({"edits": edits(ref, hyp), "ref_words": len(ref), "group": it["group"], "hyp": out["text"],
                     "ref": it["text"]})
        if it.get("question"):  # a spoken Navigator answer: score the option that comes out
            nq = nav.by_id[it["question"]]
            q = {"id": nq["id"], "kind": nq["kind"],
                 "options": [o for o in nq.get("options", []) if not it.get("options") or o["id"] in it["options"]]}
            found = match(q, out["text"], it["lang"])
            if found is None:
                found = match(q, listener.transcribe(pcm, it["lang"], grammar=grammar(q, it["lang"]))["text"], it["lang"])
            answers.append({"ok": found is not None and found["answer"] == it["answer"], "group": it["group"]})
        if i % 50 == 0:
            print(f"  {i}/{len(items)} done", flush=True)

    wer, lo, hi = wer_ci(rows)
    groups = defaultdict(list)
    for r in rows:
        for k, v in r["group"].items():
            groups[f"{k}={v}"].append(r)
    by_group = {g: dict(zip(("wer", "lo", "hi"), (round(x, 4) for x in wer_ci(rs, 500))), n=len(rs))
                for g, rs in sorted(groups.items()) if len(rs) >= 5}
    ans_k = sum(a["ok"] for a in answers)
    summary = {
        "date": dt.date.today().isoformat(), "source": source, "model": args.model, "utterances": len(rows),
        "speech_seconds": round(t_audio, 1), "wer": round(wer, 4), "wer_ci95": [round(lo, 4), round(hi, 4)],
        "by_group": by_group,
        "answers": {"n": len(answers), "correct": ans_k, "rate": round(ans_k / len(answers), 4) if answers else None,
                    "ci95": [round(x, 4) for x in wilson(ans_k, len(answers))]},
        "real_time_factor": round(t_asr / max(t_audio, 1e-9), 3),
        "examples": [{"ref": r["ref"], "hyp": r["hyp"], "edits": r["edits"], "ref_words": r["ref_words"]}
                     for r in random.Random(3).sample(rows, min(8, len(rows)))],
    }
    print(f"{source}: {len(rows)} utterances, {t_audio / 60:.1f} min of speech, model {args.model}")
    print(f"WER {100 * wer:.1f}% (95% CI {100 * lo:.1f}–{100 * hi:.1f}); recognition at {summary['real_time_factor']}x real time")
    for g, v in by_group.items():
        print(f"  {g}: WER {100 * v['wer']:.1f}% (n={v['n']})")
    if answers:
        print(f"answers: {ans_k}/{len(answers)} right")
    if args.report:
        RESULTS.mkdir(parents=True, exist_ok=True)
        name = f"voicebench_{source}"
        (RESULTS / f"{name}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (RESULTS / f"{name}.md").write_text(report(summary), encoding="utf-8")
        print(f"wrote {RESULTS / (name + '.md')}")
    return 0


def report(s: dict) -> str:
    what = ("Google FLEURS Hindi test split: real speakers reading Wikipedia sentences (CC BY 4.0). Read news-style "
            "text is harder than the short answers and messages people give Sahayak, so this is a conservative "
            "public reference, not VoiceBench." if s["source"] == "fleurs_hi" else
            "The team's consented VoiceBench recordings (see bench/voicebench/README.md).")
    lines = [f"# VoiceBench interim: {s['source']}", "", f"Run {s['date']} with `{s['model']}` on the node's own "
             "recognition code (`sahayak/voice/asr.py`), offline on the dev laptop's CPU.", "", what, "",
             "| Measure | Result |", "| --- | --- |",
             f"| Utterances | {s['utterances']} ({s['speech_seconds'] / 60:.1f} min of speech) |",
             f"| Word error rate | {100 * s['wer']:.1f}% (95% CI {100 * s['wer_ci95'][0]:.1f}–{100 * s['wer_ci95'][1]:.1f}) |",
             f"| Recognition speed | {s['real_time_factor']} × real time |"]
    if s["answers"]["n"]:
        a = s["answers"]
        lines.append(f"| Navigator answers understood | {a['correct']}/{a['n']} ({100 * a['rate']:.1f}%, 95% CI "
                     f"{100 * a['ci95'][0]:.1f}–{100 * a['ci95'][1]:.1f}) |")
    if s["by_group"]:
        lines += ["", "| Group | Utterances | WER |", "| --- | --- | --- |"]
        lines += [f"| {g} | {v['n']} | {100 * v['wer']:.1f}% |" for g, v in s["by_group"].items()]
    lines += ["", "Examples (reference → heard):", ""]
    lines += [f"- {e['ref']} → {e['hyp']} ({e['edits']}/{e['ref_words']} word errors)" for e in s["examples"]]
    lines += ["", "Words are compared after the same Hindi folding the app uses (nukta, chandrabindu) with "
              "punctuation removed and digits written as words.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
