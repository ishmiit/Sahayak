"""The phone's Navigator (web/navigator.js) gives exactly the node's questions and results.

tests/js/make_nav_corpus.py records what the Python engine answers for ~8,000 answer sets (the
200 SchemeBench interviews, 5,000 random sets, 70+ invalid ones, and two synthetic packs that
reach rules schemes.v1 does not); tests/js/parity_nav.mjs replays them through navigator.js in
Node and requires every field to match, key order included. The second test checks that the
corpus is built the way the endpoints answer, so matching the corpus means matching the node.
"""
import datetime as dt
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sahayak.navigator import get_navigator
from sahayak.server import app

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "tests" / "js"
NODE = shutil.which("node")


def _corpus_module():
    spec = importlib.util.spec_from_file_location("make_nav_corpus", JS / "make_nav_corpus.py")
    module = importlib.util.module_from_spec(spec)
    write, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # leave no __pycache__ in tests/js
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = write
    return module


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_js_navigator_matches_the_python_engine(tmp_path):
    corpus = tmp_path / "nav_corpus.json"
    made = subprocess.run([sys.executable, str(JS / "make_nav_corpus.py"), "--out", str(corpus)],
                          cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert made.returncode == 0, made.stdout + made.stderr
    run = subprocess.run([NODE, str(JS / "parity_nav.mjs"), str(corpus)], cwd=ROOT, capture_output=True, text=True,
                         timeout=600)
    assert run.returncode == 0, run.stdout[-6000:] + run.stderr[-3000:]
    assert "parity: 100% (0 mismatches)" in run.stdout


def test_the_corpus_is_what_the_endpoints_return():
    corpus = _corpus_module()
    nav = get_navigator()
    client = TestClient(app)
    assert nav.pack.path.resolve() == (ROOT / corpus.PACK_FILE).resolve()  # the corpus's pack is the node's

    assert client.get("/api/navigator").json() == nav.catalog()
    full = {"age": 67, "situation": ["widow"], "ration": "aay", "bank": "yes", "work": "not_working", "money": "le15k",
            "kisan": "no"}
    for answers, already in [({}, []), ({"age": "60_69"}, []), (full, []), (full, ["ignoaps", "pmjay"]),
                             ({"situation": [], "bank": "no", "age": 32}, ["pmjdy"])]:
        got = client.post("/api/navigator/next", json={"answers": answers}).json()
        assert got == corpus.next_response(nav, answers)
        got = client.post("/api/navigator/result", json={"answers": answers, "already": already}).json()
        assert got.pop("timing_ms") >= 0
        assert got["slip"].pop("qr").startswith("data:image/png;base64,")
        want = corpus.result_response(nav, answers, already, today=dt.date.fromisoformat(got["slip"]["date"]))
        want["slip"].pop("qr")
        assert list(got) == list(want) and got == want

    # A refused answer: the endpoint's 422 detail is the message the corpus records.
    for answers, already in [({"age": True}, []), ({"situation": ["queen"]}, []), (full, ["nope", "aaa"])]:
        detail = client.post("/api/navigator/result", json={"answers": answers, "already": already}).json()["detail"]
        assert {"error": "AnswerError", "message": detail} == corpus.outcome(
            lambda: corpus.result_response(nav, answers, already))
