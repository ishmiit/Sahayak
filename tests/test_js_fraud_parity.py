"""The phone's scam check (web/checker.js) gives exactly the node's verdict card.

tests/js/make_fraud_corpus.py records what the Python Fraud-Shield answers for ~1,400 cases (all of
ScamBench, the red-team and call sets, every message in the scam tests, the demo examples, 110+
adversarial messages run with several senders and input types, 600 seeded fuzz variants, QR payloads
and rupee amounts); tests/js/parity_fraud.mjs replays them through checker.js in Node and requires
every card field to match, key order included, with the unrounded model scores within 1e-9.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "tests" / "js"
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_js_checker_matches_the_python_check(tmp_path):
    corpus = tmp_path / "fraud_corpus.json"
    made = subprocess.run([sys.executable, "-B", str(JS / "make_fraud_corpus.py"), "--out", str(corpus)],
                          cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert made.returncode == 0, made.stdout + made.stderr
    run = subprocess.run([NODE, str(JS / "parity_fraud.mjs"), str(corpus)], cwd=ROOT, capture_output=True, text=True,
                         timeout=600)
    assert run.returncode == 0, run.stdout[-6000:] + run.stderr[-3000:]
    assert "parity: 100% (0 mismatches)" in run.stdout


def test_checker_unicode_tables_match_this_python():
    """checker.js carries the Unicode version the node's Python knows (unassigned code points, case
    foldings, decimal digits). A node on another Python needs them regenerated."""
    run = subprocess.run([sys.executable, "-B", str(JS / "gen_unicode_tables.py"), "--check"], cwd=ROOT,
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stdout + run.stderr
