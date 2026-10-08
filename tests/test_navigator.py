"""Benefits Navigator: the logic, the scheme rules, the interview, the API and the slip."""
import base64
import json
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sahayak.navigator import AnswerError, get_navigator
from sahayak.navigator.engine import AGE_MAX, Facts, F, L, T, U, evaluate
from sahayak.navigator.slip import slip_text
from sahayak.server import app

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench" / "schemebench"))
from oracle import expected  # noqa: E402

nav = get_navigator()
client = TestClient(app)
FULL = dict(age=67, situation=["widow"], ration="aay", bank="yes", work="not_working", money="le15k", kisan="no")


def status(answers, sid, **kw):
    return next(c for c in nav.result(answers, **kw)["schemes"] if c["id"] == sid)


def replay(answers):
    def answer_for(q):
        if q["kind"] == "multi":
            return [s for s in answers["situation"] if s in {o["id"] for o in q["options"]}]
        return answers[q["id"]]
    return nav.interview(answer_for)


# ---------------------------------------------------------------- logic

@pytest.mark.parametrize("node,facts,want", [
    ({"all": [{"fact": "a"}, {"fact": "b"}]}, {"a": T, "b": L}, L),
    ({"all": [{"fact": "a"}, {"fact": "b"}]}, {"a": L, "b": U}, U),
    ({"all": [{"fact": "a"}, {"fact": "b"}]}, {"a": U, "b": F}, F),
    ({"any": [{"fact": "a"}, {"fact": "b"}]}, {"a": L, "b": U}, L),
    ({"any": [{"fact": "a"}, {"fact": "b"}]}, {"a": F, "b": U}, U),
    ({"not": {"fact": "a"}}, {"a": T}, F),
    ({"not": {"fact": "a"}}, {"a": U}, U),
    ({"not": {"fact": "a"}}, {"a": L}, U),  # "probably true" does not make the opposite "probably false"
    ({"fact": "missing"}, {}, U),
])
def test_four_valued_logic(node, facts, want):
    assert evaluate(node, Facts(values=facts)) == want


@pytest.mark.parametrize("age,cond,want", [
    ((60, 60), [60, None], T), ((59, 59), [60, None], F), ((60, 69), [60, None], T),
    ((70, 79), [18, 70], U), ((80, AGE_MAX), [40, 79], F), ((0, AGE_MAX), [18, 40], U),
])
def test_age_ranges(age, cond, want):
    assert evaluate({"age": cond}, Facts(age=age)) == want


# ---------------------------------------------------------------- the pack

def test_pack_has_twelve_sourced_schemes():
    d = nav.pack.data
    assert len(nav.schemes) == 12
    for s in nav.schemes:
        assert s["sources"], s["id"]
        for sid in s["sources"]:
            src = d["sources"][sid]
            assert src["url"].startswith("https://") and src["checked"]
        assert s["documents"] and s["where"]["hi"] and s["counter"]["default"]["hi"]


def test_every_rupee_amount_comes_from_the_pack():
    pack_text = nav.pack.path.read_text(encoding="utf-8")
    rupees = re.compile(r"₹\s?[\d,]+(?:\s?(?:लाख|lakh))?")
    for answers in (FULL, dict(age=32, situation=[], bank="no", work="unorganised", money="le15k"),
                    dict(age=82, situation=["earner_died"], ration="bpl_phh", bank="no", work="farmer_land", kisan="no")):
        blob = json.dumps(nav.result(answers), ensure_ascii=False)
        for amount in rupees.findall(blob):
            assert amount in pack_text, amount


def test_engine_matches_the_independent_oracle_on_schemebench():
    rows = [json.loads(line) for line in (ROOT / "bench/schemebench/schemebench_v1.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 200
    for r in rows:
        got = {c["id"]: c["status"] for c in nav.result(r["answers"])["schemes"]}
        assert got == expected(r["answers"]) == r["expected"], r["id"]


# ---------------------------------------------------------------- rules, person by person

def test_widow_on_antyodaya_card():
    r = nav.result(FULL)
    assert r["groups"]["likely"] == ["ignoaps", "ignwps"]  # BPL is only "likely" from a ration card
    assert r["groups"]["eligible"] == ["pmsby"]
    assert r["groups"]["check"] == ["pmjay"]  # under 70: the family list decides
    oap = status(FULL, "ignoaps")
    assert oap["benefit_now"]["en"] == "₹200 a month from the centre; your state may add more"
    assert "I am 67 years old." in oap["counter"]["en"]


def test_old_age_amount_rises_at_80_and_widow_pension_stops_at_79():
    a = dict(FULL, age=81)
    assert status(a, "ignoaps")["benefit_now"]["en"] == "₹500 a month from the centre; your state may add more"
    assert status(a, "ignwps")["status"] == "not_eligible"


def test_seventy_plus_get_pmjay_whatever_their_income():
    a = dict(FULL, age=70, ration="apl", money="taxpayer")
    assert status(a, "pmjay")["status"] == "eligible"
    assert status(dict(a, age=69), "pmjay")["status"] == "check"


def test_no_bank_account_unlocks_the_insurance_schemes():
    a = dict(age=30, situation=[], ration="apl", bank="no", work="not_working", money="le15k", kisan="no")
    r = nav.result(a)
    assert r["groups"]["eligible"] == ["pmjdy"]
    assert r["groups"]["unlock"] == ["pmsby", "pmjjby", "apy"]
    card = status(a, "apy")
    assert card["unlock"]["fact"] == "bank" and "Jan Dhan" in card["unlock"]["hint"]["en"]


def test_taxpayers_cannot_join_apy_even_after_opening_an_account():
    a = dict(age=30, situation=[], ration="apl", bank="no", work="salaried_pf", money="taxpayer", kisan="no")
    assert status(a, "apy")["status"] == "not_eligible"


def test_pmkisan_needs_land_and_no_excluded_family_member():
    farmer = dict(age=45, situation=[], ration="apl", bank="yes", work="farmer_land", money="le15k", kisan="no")
    assert status(farmer, "pmkisan")["status"] == "likely"  # land records still to show
    assert status(dict(farmer, kisan="yes"), "pmkisan")["status"] == "not_eligible"
    assert status(dict(farmer, kisan="dont_know"), "pmkisan")["status"] == "check"
    assert status(dict(farmer, work="farm_labour"), "pmkisan")["status"] == "not_eligible"
    assert status(dict(farmer, work="farm_labour"), "eshram")["status"] == "eligible"


def test_already_getting_moves_a_scheme_to_have():
    r = nav.result(FULL, already=["ignoaps"])
    assert r["groups"]["have"] == ["ignoaps"] and "ignoaps" not in r["groups"]["likely"]


def test_not_eligible_cards_say_only_what_rules_them_out():
    card = status(dict(FULL, age=30), "ignoaps")
    assert card["status"] == "not_eligible"
    assert [r["truth"] for r in card["reasons"]] == ["F"]


# ---------------------------------------------------------------- interview

def test_demo_personas_are_what_a_real_interview_asks():
    for demo in nav.catalog()["demos"]:
        assert replay(demo["answers"]) == demo["answers"], demo["id"]  # a KeyError means it asked something more


def test_interview_skips_what_cannot_matter():
    # 30, nothing special: no pension can apply, so the ration card is never asked
    asked = replay(dict(age=30, situation=[], ration="aay", bank="yes", work="salaried_pf", money="gt15k", kisan="no"))
    assert "ration" not in asked and "kisan" not in asked
    # the widow option is only offered between 40 and 79
    q = nav.next_question({"age": 30})
    assert q["id"] == "situation" and "widow" not in [o["id"] for o in q["options"]]


def test_interview_stops_and_respects_the_cap():
    assert nav.next_question({**FULL}) is None
    for r in (json.loads(line) for line in (ROOT / "bench/schemebench/schemebench_v1.jsonl").read_text(encoding="utf-8").splitlines()):
        asked = replay(r["answers"])
        assert len(asked) <= nav.max_questions
        assert [c["status"] for c in nav.result(asked)["schemes"]] == [c["status"] for c in nav.result(r["answers"])["schemes"]]


@pytest.mark.parametrize("answers", [
    {"nope": 1}, {"age": 121}, {"age": True}, {"age": "old"}, {"ration": "gold"}, {"situation": "widow"},
    {"situation": ["queen"]},
])
def test_bad_answers_are_refused(answers):
    with pytest.raises(AnswerError):
        nav.next_question(answers)


# ---------------------------------------------------------------- API and slip

def test_api_flow_and_slip():
    cat = client.get("/api/navigator").json()
    assert len(cat["schemes"]) == 12 and cat["demos"]
    first = client.post("/api/navigator/next", json={"answers": {}}).json()
    assert first["question"]["id"] == "age" and not first["done"]
    assert client.post("/api/navigator/next", json={"answers": FULL}).json()["done"] is True
    r = client.post("/api/navigator/result", json={"answers": FULL}).json()
    assert r["slip"]["qr"].startswith("data:image/png;base64,")
    png = base64.b64decode(r["slip"]["qr"].split(",", 1)[1])
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) < 4000
    assert "name" not in r["slip"]["text"].lower().replace("no name stored", "")
    assert client.post("/api/navigator/next", json={"answers": {"age": 500}}).status_code == 422
    assert client.post("/api/navigator/result", json={"answers": FULL, "already": ["nope"]}).status_code == 422


def test_slip_qr_decodes_to_the_slip_text():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    r = client.post("/api/navigator/result", json={"answers": FULL}).json()
    img = cv2.imdecode(np.frombuffer(base64.b64decode(r["slip"]["qr"].split(",", 1)[1]), np.uint8), cv2.IMREAD_GRAYSCALE)
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    assert text == r["slip"]["text"]


def test_slip_text_lists_groups_and_answers():
    text = slip_text(nav.result(FULL))
    assert "age=67" in text and "situation=widow" in text
    assert "LIKELY (needs proof): IGNOAPS, IGNWPS" in text and "CHECK AT OFFICE: PM-JAY" in text
