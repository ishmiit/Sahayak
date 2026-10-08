"""The field-morning scoring script, on a tiny made-up sheet (never written to bench/results)."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("eval_field", ROOT / "bench" / "eval_field.py")
eval_field = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_field)

PEOPLE = """pid,age_band,gender,reads_hindi,phone,lang,understood,trust,use_again,donated_message
P01,70+,f,no,basic,hi,5,4,5,y
P02,35-54,m,yes,smart,hi,4,3,4,n
"""
TASKS = """pid,task,item,truth,before,verdict,action_right,seconds,helped,schemes_found,schemes_new,pmjay70_shown,worked,notes
P01,card,1,scam,genuine,scam,y,40,n,,,,,
P01,card,5,genuine,unsure,no_signs,y,35,y,,,,,
P02,card,1,scam,scam,scam,y,20,n,,,,,
P02,card,6,genuine,genuine,suspicious,n,25,n,,,,,
P01,benefits,benefits,,,,,180,n,3,2,y,,
P02,benefits,benefits,,,,,150,y,1,0,,,
P02,offline,1,scam,,scam,y,10,n,,,,y,
"""


@pytest.fixture
def sheets(tmp_path):
    (tmp_path / "p.csv").write_text(PEOPLE, encoding="utf-8")
    (tmp_path / "t.csv").write_text(TASKS, encoding="utf-8")
    return tmp_path


def test_paired_card_scores_and_benefits(sheets):
    res = eval_field.main(["--participants", str(sheets / "p.csv"), "--tasks", str(sheets / "t.csv"),
                           "--out", str(sheets / "out"), "--report"])
    c = res["cards"]
    assert (c["before"]["k"], c["with_sahayak"]["k"], c["attempts"]) == (2, 3, 4)  # 'unsure' counts as not right
    assert (c["right_only_with_sahayak"], c["right_only_on_their_own"]) == (2, 1)
    assert res["cards_aged_55_plus"]["attempts"] == 2
    b = res["benefits"]
    assert b["finished_unaided"]["k"] == 1 and b["found_something_new"]["k"] == 1 and b["schemes_new_total"] == 2
    assert b["seniors_70_shown_pmjay"] == {"k": 1, "n": 1, "rate": 1.0, "ci95": eval_field.wilson(1, 1)}
    assert res["offline_on_phone"]["k"] == 1
    assert res["opinions"]["trust"]["k"] == 1  # only answers of 4 or 5 count as agreeing
    written = json.loads((sheets / "out" / "field_v0.json").read_text(encoding="utf-8"))
    assert written["people"] == 2 and "What this does not show" in (sheets / "out" / "field_v0.md").read_text(encoding="utf-8")


def test_an_empty_sheet_is_refused(tmp_path):
    (tmp_path / "p.csv").write_text(PEOPLE.splitlines()[0] + "\n", encoding="utf-8")
    (tmp_path / "t.csv").write_text(TASKS.splitlines()[0] + "\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        eval_field.main(["--participants", str(tmp_path / "p.csv"), "--tasks", str(tmp_path / "t.csv")])


def test_wilson_interval():
    lo, hi = eval_field.wilson(8, 10)
    assert 0.49 < lo < 0.5 and 0.94 < hi < 0.95
