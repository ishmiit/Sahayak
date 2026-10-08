"""Does the phone give the node's answer? Replays both parity corpora through the phone's engines.

Regenerates the corpora from the live Python (tests/js/make_fraud_corpus.py, make_nav_corpus.py) into a
temporary folder, runs web/checker.js and web/navigator.js over them in Node (tests/js/parity_*.mjs), and
reports cases, field-by-field comparisons and mismatches for each. Needs `node` on PATH.

Usage: python bench/eval_phone_parity.py [--report]   (--report writes bench/results/phone_parity.json and .md)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.packs import get_pack  # noqa: E402

RESULTS = ROOT / "bench" / "results"


def run(cmd: list[str]) -> str:
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if out.returncode not in (0, 1):  # 1 means mismatches, which we report; anything else is a broken run
        raise SystemExit(f"{' '.join(cmd)} failed ({out.returncode}):\n{out.stdout}\n{out.stderr}")
    return out.stdout


def parse(text: str, cases_re: str, comparisons_re: str) -> dict:
    mismatch = re.search(r"MISMATCHES: (\d+)", text)
    return {"cases": int(re.search(cases_re, text).group(1)), "comparisons": int(re.search(comparisons_re, text).group(1)),
            "mismatches": int(mismatch.group(1)) if mismatch else 0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if not shutil.which("node"):
        raise SystemExit("node is not on PATH")
    py = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        fc, nc = str(Path(tmp) / "fraud_corpus.json"), str(Path(tmp) / "nav_corpus.json")
        run([py, "tests/js/make_fraud_corpus.py", "--out", fc])
        run([py, "tests/js/make_nav_corpus.py", "--out", nc])
        fraud_out = run(["node", "tests/js/parity_fraud.mjs", fc])
        nav_out = run(["node", "tests/js/parity_nav.mjs", nc])
    timing = re.search(r"check\(\): median ([\d.]+) ms, p95 ([\d.]+) ms", fraud_out)
    res = {
        "date": time.strftime("%Y-%m-%d"),
        "packs": {name: get_pack(name).version for name in ("fraud", "scam_patterns", "fraud_model", "schemes")},
        "fraud": {**parse(fraud_out, r"corpus: (\d+) cases", r"(\d+) comparisons"),
                  "check_ms_median": float(timing.group(1)), "check_ms_p95": float(timing.group(2))},
        "navigator": parse(nav_out, r"(\d+) cases, \d+ exact comparisons", r"\d+ cases, (\d+) exact comparisons"),
    }
    f, n = res["fraud"], res["navigator"]
    md = "\n".join([
        "# The phone gives the node's answer",
        "",
        f"Run {res['date']} with `python bench/eval_phone_parity.py --report` (packs: "
        + ", ".join(f"{k} {v}" for k, v in res["packs"].items()) + ").",
        "",
        "| Engine | Cases | Field-by-field comparisons | Mismatches |",
        "| --- | --- | --- | --- |",
        f"| Scam check (`web/checker.js` against `sahayak/fraud`) | {f['cases']:,} | {f['comparisons']:,} | {f['mismatches']} |",
        f"| Benefits interview (`web/navigator.js` against `sahayak/navigator`) | {n['cases']:,} | {n['comparisons']:,} | {n['mismatches']} |",
        "",
        f"A scam check takes {f['check_ms_median']} ms (median) and {f['check_ms_p95']} ms (95th percentile) in Node on the "
        "build laptop; a phone is several times slower and still far under the time a person notices.",
        "",
        "The cases: every ScamBench, red-team (our own and the blind set) and call-bench message, the dev half of "
        "PublicBench, every message in the test files, the demo examples and QR codes, adversarial and fuzzed text "
        "(Unicode, homoglyphs, emoji, Hindi digits, long text); and "
        "the 200 SchemeBench personas replayed through the interview, 5,000 random answer sets, invalid answers and two "
        "extra rule packs that reach every branch of the engine.",
        "",
        "**What this does not show.** Parity with the node, not accuracy: the phone is exactly as right and as wrong as "
        "the node on these cases. Unrounded classifier scores can differ in the last bit between machines; no card field "
        "or verdict does.",
        "",
    ])
    print(md)
    if args.report:
        (RESULTS / "phone_parity.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        (RESULTS / "phone_parity.md").write_text(md, encoding="utf-8")
        print(f"wrote {RESULTS / 'phone_parity.json'}")
    return 1 if f["mismatches"] or n["mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
