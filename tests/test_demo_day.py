"""scripts/demo_day.py, the demo-day preflight: its expected answers are the demo pack's, and they are right."""
import importlib.util
from pathlib import Path

import pytest

from sahayak.fraud import check_message
from sahayak.inputs.qr import analyse
from sahayak.packs import get_pack

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("demo_day", ROOT / "scripts" / "demo_day.py")
demo_day = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_day)
DEMO = get_pack("demo").data


def test_every_demo_card_has_an_expected_answer():
    assert set(demo_day.EXPECTED) == {ex["id"] for ex in DEMO["examples"]}
    assert set(demo_day.EXPECTED_QR) == {ex["id"] for ex in DEMO["qr_examples"]}


@pytest.mark.parametrize("ex", DEMO["examples"], ids=lambda ex: ex["id"])
def test_the_expected_answers_are_what_sahayak_says(ex):
    card = check_message(ex["text"], sender=ex.get("sender"), input_type=ex.get("input_type", "text"))
    assert card["verdict"] == demo_day.EXPECTED[ex["id"]]


@pytest.mark.parametrize("ex", DEMO["qr_examples"], ids=lambda ex: ex["id"])
def test_the_expected_qr_answers_are_what_sahayak_says(ex):
    card = check_message(analyse(ex["payload"])["check_text"], input_type="qr")
    assert card["verdict"] == demo_day.EXPECTED_QR[ex["id"]]


def test_the_tamil_sample_is_could_not_check():
    assert check_message(demo_day.TAMIL)["verdict"] == "unreadable"


def test_the_packs_pass_the_preflight():
    demo_day.RESULTS.clear()
    demo_day.check_packs()
    assert demo_day.RESULTS and not [r for r in demo_day.RESULTS if r[0] == demo_day.FAIL]
