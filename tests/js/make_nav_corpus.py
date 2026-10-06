"""Write tests/js/nav_corpus.json: what the Python Navigator answers, for web/navigator.js to match.

Every case holds the input and what the node's endpoints return for it, built the way
sahayak/server.py builds them:

  next:    {"done", "question", "asked", "max_questions"}            (POST /api/navigator/next)
  result:  Navigator.result() + "slip": {"text", "qr": null, "date"}  (POST /api/navigator/result)

with "timing_ms" dropped (it is measured, not computed), the slip dated 2026-10-06 and its QR
image left out (the phone draws none). A refused answer is recorded as its exact AnswerError
message (the node's 422 detail); the few inputs that make Python itself fail (a list inside the
multi-choice answer cannot be hashed) are recorded as that TypeError.

Sections, each with its own pack:
  schemes.v1 (packs/schemes.v1.json, the pack the node serves):
    * the catalog, the demo personas and the empty answer set;
    * the 200 SchemeBench personas, replayed through the real interview (every next() payload
      in order, then result() with already=[] and with two of the persona's useful schemes),
      plus next() and result() on the persona's full answers;
    * 5,000 seeded random answer sets: exact ages and age bands, 0-3 situations, "don't know"
      answers, full and partial sets in any key order, interviews stopped early, "already" lists;
    * 70+ invalid answer sets, each with its exact error message.
  synthetic and tiny (built here from the real pack, embedded in the corpus): rules and texts
    that reach engine paths schemes.v1 cannot (a "not" over a "likely" fact, a hole in an age
    range, "likely" in a benefit_now condition, a question with no help text, two questions
    setting one fact, a second actionable fact, a question cap below the question count...), so
    the port stays exact for the next pack too, not only for this one.

The expected values are deduplicated (any object or list whose JSON is long enough is stored
once in "table" and referenced as {"$ref": n}); parity_nav.mjs expands them before an exact,
key-order-aware comparison.

Usage: python tests/js/make_nav_corpus.py [--out tests/js/nav_corpus.json] [--random 5000] [--seed 20261006]
       (--random also sets the synthetic packs' share: 30% and 20% of it)
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SAHAYAK_LLM", "none")

from sahayak.navigator.engine import AnswerError, Navigator  # noqa: E402
from sahayak.navigator.slip import slip_text  # noqa: E402
from sahayak.packs import Pack, load_pack_file  # noqa: E402

PACK_FILE = "packs/schemes.v1.json"
PERSONAS = ROOT / "bench" / "schemebench" / "schemebench_v1.jsonl"
TODAY = dt.date(2026, 10, 6)
USEFUL = ("eligible", "likely", "check", "unlock")
MIN_SHARED = 48  # JSON length from which an object or list is stored once in the table


def load_navigator() -> Navigator:
    return Navigator(load_pack_file(ROOT / PACK_FILE))


# ---------------------------------------------------------------- the endpoints, as server.py builds them

def next_response(nav: Navigator, answers: dict) -> dict:
    question = nav.next_question(answers)
    return {"done": question is None, "question": question, "asked": len(answers), "max_questions": nav.max_questions}


def result_response(nav: Navigator, answers: dict, already: list | tuple = (), today: dt.date = TODAY) -> dict:
    result = nav.result(answers, already=already)
    result.pop("timing_ms")
    result["slip"] = {"text": slip_text(result, today), "qr": None, "date": today.isoformat()}
    return result


def outcome(fn: Callable[[], Any]) -> dict:
    try:
        return {"ok": fn()}
    except AnswerError as e:
        return {"error": "AnswerError", "message": str(e)}
    except TypeError as e:  # an unhashable value inside a multi-choice answer
        return {"error": "TypeError", "message": str(e)}


# ---------------------------------------------------------------- interviews

def answer_for(persona: dict) -> Callable[[dict], Any]:
    """Answer each question from a full answer set, like Navigator.interview's callers do."""
    def answer(q: dict) -> Any:
        if q["kind"] == "multi":
            shown = {o["id"] for o in q["options"]}
            return [s for s in persona["situation"] if s in shown]
        return persona[q["id"]]
    return answer


def replay(nav: Navigator, persona: dict, stop: int | None) -> tuple[dict, list[dict]]:
    """Run the interview, recording every next() payload; stop after `stop` answers if given."""
    answers: dict = {}
    steps = []
    answer = answer_for(persona)
    while True:
        out = next_response(nav, answers)
        steps.append({"ok": out})
        if out["done"] or (stop is not None and len(answers) >= stop):
            return answers, steps
        answers[out["question"]["id"]] = answer(out["question"])


def interview_case(nav: Navigator, cid: str, persona: dict, stop: int | None, already: list | None,
                   rng: random.Random | None = None) -> dict:
    answers, steps = replay(nav, persona, stop)
    base = outcome(lambda: result_response(nav, answers))
    if already is None:  # two of the persona's useful schemes
        groups = base["ok"]["groups"]
        useful = [i for g in USEFUL for i in groups[g]]
        already = rng.sample(useful, 2) if len(useful) >= 2 else (useful + groups["not_eligible"])[:2]
    case = {"id": cid, "kind": "interview", "persona": persona, "stop": stop, "already": already,
            "steps": steps, "result": base}
    if already:
        case["result_already"] = outcome(lambda: result_response(nav, answers, already))
    return case


def call_case(nav: Navigator, cid: str, answers: Any, already: list | None = None,
              do_next: bool = True, do_result: bool = True) -> dict:
    case: dict = {"id": cid, "kind": "call", "answers": answers, "already": already or []}
    if do_next:
        case["next"] = outcome(lambda: next_response(nav, answers))
    if do_result:
        case["result"] = outcome(lambda: result_response(nav, answers, already or []))
    return case


# ---------------------------------------------------------------- random answers

def random_persona(nav: Navigator, rng: random.Random, probes: list[int]) -> dict:
    qs = nav.by_id
    r = rng.random()
    if r < 0.3:
        age: Any = rng.choice([b["id"] for b in qs["age"]["bands"]])
    elif r < 0.75:  # where the rules change: the probe ages and their neighbours
        age = min(120, max(0, rng.choice(probes) + rng.choice((-1, 0, 1))))
    else:
        age = rng.randint(0, 120)
    situation = rng.sample([o["id"] for o in qs["situation"]["options"]], rng.choice((0, 0, 0, 1, 1, 2, 3)))
    if situation and rng.random() < 0.05:
        situation.append(situation[0])  # a repeated choice: allowed, counted once
    persona = {"age": age, "situation": situation}
    for q in nav.questions:
        if q["kind"] == "single":
            persona[q["id"]] = rng.choice([o["id"] for o in q["options"]])
    return persona


def random_already(nav: Navigator, rng: random.Random) -> list[str]:
    if rng.random() >= 0.35:
        return []
    ids = [s["id"] for s in nav.schemes]
    out = rng.sample(ids, rng.randint(1, min(4, len(ids))))
    if rng.random() < 0.1:
        out.append(out[0])
    return out


def random_cases(nav: Navigator, n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    probes = list(nav._age_probes)
    qids = [q["id"] for q in nav.questions]
    cases = []
    for i in range(n):
        persona = random_persona(nav, rng, probes)
        already = random_already(nav, rng)
        r = rng.random()
        if r < 0.4:  # an interview, sometimes stopped early (the person pressed back, or left)
            stop = rng.choice((None, None, None, 0, 1, 2, 3, 4, 5, 6))
            cases.append(interview_case(nav, f"random/{i}/interview", persona, stop, already))
            continue
        if r < 0.7:  # every question answered, in pack order or shuffled
            keys = list(qids)
            if rng.random() < 0.5:
                rng.shuffle(keys)
        else:  # some questions answered, in any order
            keys = rng.sample(qids, rng.randint(0, len(qids)))
        cases.append(call_case(nav, f"random/{i}/set", {k: persona[k] for k in keys}, already))
    return cases


# ---------------------------------------------------------------- invalid answers

def invalid_cases(nav: Navigator) -> list[dict]:
    valid = {"age": 45, "situation": [], "ration": "apl", "bank": "yes", "work": "farmer_land", "money": "le15k",
             "kisan": "no"}
    sets: list[tuple[str, dict]] = [
        ("unknown question", {"nope": 1}),
        ("unknown question after a valid one", {"age": 30, "foo": "bar"}),
        ("first error wins: unknown question first", {"foo": 1, "age": 121}),
        ("first error wins: bad age first", {"age": 121, "foo": 1}),
        ("empty question id", {"": "x"}),
        ("question id in another case", {"Age": 30}),
        ("question id in Hindi", {"उम्र": 30}),
        ("key named constructor", {"constructor": 1}),
        ("key named __proto__", {"__proto__": "x"}),
        ("key named toString", {"toString": "aay"}),
        ("key named hasOwnProperty", {"hasOwnProperty": []}),
        ("age 121", {"age": 121}),
        ("age -1", {"age": -1}),
        ("age 10**15", {"age": 10**15}),
        ("age 2**53", {"age": 2**53}),
        ("age true", {"age": True}),
        ("age false", {"age": False}),
        ("age null", {"age": None}),
        ("age as a string number", {"age": "67"}),
        ("age unknown band", {"age": "old"}),
        ("age band with a trailing space", {"age": "lt18 "}),
        ("age band in another case", {"age": "80P"}),
        ("age 67.5", {"age": 67.5}),
        ("age 1e-07", {"age": 1e-07}),
        ("age 0.0001", {"age": 0.0001}),
        ("age 1.5e300", {"age": 1.5e300}),
        ("age 1e21", {"age": 1e21}),
        ("age -0.5", {"age": -0.5}),
        ("age 120.5", {"age": 120.5}),
        ("age 0.1+0.2", {"age": 0.1 + 0.2}),
        ("age 1234567.891", {"age": 1234567.891}),
        ("age 1.2345e-10", {"age": 1.2345e-10}),
        ("age 4503599627370495.5 (largest float with a fraction)", {"age": 4503599627370495.5}),
        ("age as a list", {"age": [67]}),
        ("age as an empty list", {"age": []}),
        ("age as a dict", {"age": {"n": 67}}),
        ("single: unknown option", {"ration": "gold"}),
        ("single: another case", {"bank": "Yes"}),
        ("single: empty string", {"work": ""}),
        ("single: null", {"ration": None}),
        ("single: int", {"money": 15000}),
        ("single: float", {"money": 2.5}),
        ("single: true", {"kisan": True}),
        ("single: list", {"ration": ["aay"]}),
        ("single: dict", {"ration": {"id": "aay"}}),
        ("single: nested dict", {"ration": {"a": [1, None, "x'y"], "b": {"c": False, "d": 0.25}}}),
        ("single: apostrophe", {"kisan": "don't know"}),
        ("single: Hindi", {"bank": "हाँ"}),
        ("multi: a string", {"situation": "widow"}),
        ("multi: null", {"situation": None}),
        ("multi: a dict", {"situation": {"widow": True}}),
        ("multi: an int", {"situation": 3}),
        ("multi: unknown option", {"situation": ["queen"]}),
        ("multi: valid and unknown, repeated", {"situation": ["widow", "queen", "king", "widow", "queen"]}),
        ("multi: scalars", {"situation": [1, None, True, False, 2.5, -7, 1e-05]}),
        ("multi: quotes", {"situation": ["it's", 'say "hi"', "both ' and \"", ""]}),
        ("multi: escapes", {"situation": ["back\\slash", "tab\tnl\ncr\r", "\x00\x1f\x7f", "\x85\xa0\xad",
                                          "\u200b\u2028\ufeff", "\ue000", "a b\u3000c"]}),
        ("multi: Hindi and emoji", {"situation": ["विधवा", "😀", "e\u0301", "\U0001F1EE\U0001F1F3"]}),
        ("multi: astral non-printables", {"situation": ["\U000E0001", "\U000F0000", "\U0010FFFF"]}),
        ("multi: lone surrogate", {"situation": ["\ud800"]}),
        ("multi: a list inside (Python TypeError)", {"situation": [["widow"]]}),
        ("multi: a dict inside (Python TypeError)", {"situation": [{"a": 1}]}),
        ("multi: unknown, then a list (Python TypeError)", {"situation": ["queen", ["x"]]}),
        ("multi: dict, then a list (Python TypeError)", {"situation": [{"a": 1}, ["x"]]}),
        ("too many answers: 8", {**valid, "extra": 1}),
        ("too many answers: 9, all unknown", {f"q{i}": i for i in range(9)}),
        ("valid answers, then a bad one", {"age": 30, "ration": "aay", "bank": "maybe"}),
        ("all seven, last one bad", {**valid, "kisan": "dont know"}),
    ]
    cases = [call_case(nav, f"invalid/{name}", answers) for name, answers in sets]
    already_sets: list[tuple[str, dict, list]] = [
        ("already: unknown scheme", valid, ["nope"]),
        ("already: sorted, known ones left out", valid, ["zzz", "aaa", "ignoaps"]),
        ("already: repeated unknown", valid, ["x", "x"]),
        ("already: scheme id in another case", valid, ["IGNOAPS"]),
        ("already: sorted by code point", valid, ["it's", "😀", "！", "pmjay"]),
        ("already: empty string", valid, [""]),
        ("already: partial answers", {"age": "80p"}, ["pm-kisan"]),
        ("already: bad answers are reported first", {"age": 500}, ["nope"]),
    ]
    cases += [call_case(nav, f"invalid/{name}", answers, already, do_next=False)
              for name, answers, already in already_sets]
    return cases


# ---------------------------------------------------------------- corpus

def known_cases(nav: Navigator) -> list[dict]:
    rng = random.Random(1)
    cases = []
    personas = [json.loads(line) for line in PERSONAS.read_text(encoding="utf-8").splitlines() if line.strip()]
    for p in personas:
        cases.append(interview_case(nav, f"persona/{p['id']}", p["answers"], None, None, rng))
        cases.append(call_case(nav, f"persona/{p['id']}/full", p["answers"]))
    for demo in nav.pack.data.get("demos", []):
        cases.append(call_case(nav, f"demo/{demo['id']}", demo["answers"]))
    cases.append(call_case(nav, "empty", {}))
    return cases


# ---------------------------------------------------------------- packs that reach further than schemes.v1

def _t(en: str, hi: str) -> dict:
    return {"hi": hi, "en": en}


def synthetic_pack(real: dict) -> dict:
    """schemes.v1 plus a question and three schemes that reach what schemes.v1 cannot."""
    d = copy.deepcopy(real)
    d.update(pack="schemes-synthetic", version="0.1.0", date="2026-10-06", max_questions=6)  # 8 questions, cap 6
    d["age_phrase"] = {"exact": _t("I am {n} {{years}} old.", "मेरी उम्र {n} साल है। {{n}}")}
    d["actionable"]["disability80"] = {"to": "L", "hint": _t("Get the certificate first.", "पहले प्रमाण-पत्र बनवाएँ।")}
    d["sources"]["syn_src"] = {"id": "its-own-id", "publisher": "Synthetic", "title": "Test source",
                               "url": "https://example.org/", "checked": "2026-10-06"}
    d["questions"].append({  # no "help": next() must send help: null
        "id": "listed", "kind": "single", "short": _t("List", "सूची"),
        "text": _t("Is your family on the list?", "क्या परिवार सूची में है?"),
        "options": [
            {"id": "likely", "sets": {"pmjay_list": "L"}, "label": _t("Probably", "शायद")},
            {"id": "unknown", "sets": {"pmjay_list": "U"}, "label": _t("Unknown", "पता नहीं")},
            # also sets bank, like the bank question: whichever answer comes later wins
            {"id": "yes_no_bank", "sets": {"pmjay_list": "T", "bank": "F"}, "label": _t("Yes, no bank account", "हाँ, खाता नहीं")},
            {"id": "no", "sets": {"pmjay_list": "F"}, "label": _t("No", "नहीं")},
        ],
    })
    template = next(s for s in real["schemes"] if s["id"] == "ignoaps")

    one = copy.deepcopy(template)
    one.update(id="syn_not_likely", short="SYN-1", family="test")
    one["rule"] = {"all": [
        {"not": {"fact": "bpl", "say": _t("BPL (inside a not: never on the trail)", "BPL")}, "say": _t("Not BPL", "BPL नहीं")},
        {"any": [{"age": [0, 10], "say": _t("Age 10 or less", "उम्र 10 या कम")},
                 {"age": [50, None], "say": _t("Age 50 or more", "उम्र 50 या ज़्यादा")}], "say": _t("Young or old", "छोटा या बड़ा")},
        {"all": [], "say": _t("Nothing to check", "कुछ नहीं")},
        {"any": [{"fact": "farmer_land"}, {"fact": "pmjay_list"}]},
    ]}
    one["benefit_now"] = [
        {"when": {"fact": "farmer_land"}, "hi": "ज़मीन पक्की हो तो", "en": "Only when the land is certain"},
        {"when": {"any": []}, "hi": "कभी नहीं", "en": "Never"},
        {"when": None, "hi": "बाक़ी सब", "en": "Otherwise"},
    ]
    # Python's whitespace, not JS's: U+3000, U+0085, U+2028, \x1c and \x1d split; U+FEFF does not.
    one["counter"] = {
        "default": {"en": "Namaste.\N{IDEOGRAPHIC SPACE}{age_phrase}\N{ZERO WIDTH NO-BREAK SPACE}  x\x1c\x1dy {age_phrase}\x85end",
                    "hi": "  {age_phrase}\N{LINE SEPARATOR}नमस्ते\t\n"},
        "check": {},  # empty: falls back to the default
    }
    one["sources"] = ["syn_src", "pmjdy_scheme"]
    one.pop("notes")
    one.pop("check_how")

    two = copy.deepcopy(template)
    two.update(id="syn_any", short="SYN-2", family="test")
    two["rule"] = {"any": [
        {"fact": "pmjay_list", "say": _t("On the list", "सूची में")},
        {"all": [{"fact": "disability80", "say": _t("Disability", "विकलांगता")}, {"fact": "bank", "say": _t("Bank", "खाता")},
                 {"age": [30, 45]}], "say": _t("Disabled, banked, 30 to 45", "विकलांग, खाता, 30 से 45")},
        {"any": []},
    ]}
    two["benefit_now"] = [{"when": {"not": {"fact": "pmjay_list"}}, "hi": "सूची में नहीं", "en": "Not on the list"},
                          {"when": {}, "hi": "हमेशा", "en": "Always"}]
    two["counter"] = {"check": _t("Check, please. {age_phrase}", "जाँच करें। {age_phrase}"), "default": _t("Default.", "डिफ़ॉल्ट।")}
    two["check_how"] = _t("Ask.", "पूछें।")
    two["notes"] = [_t("A note.", "एक नोट।")]
    two["sources"] = ["syn_src"]

    three = copy.deepcopy(template)  # unlocked by the second actionable fact, not by a bank account
    three.update(id="syn_unlock", short="SYN-3", family="test")
    three["rule"] = {"all": [{"fact": "disability80", "say": _t("Disability", "विकलांगता")}, {"fact": "widow", "say": _t("Widow", "विधवा")}]}
    for key in ("benefit_now", "notes", "check_how"):
        three.pop(key)

    d["schemes"] += [one, two, three]
    return d


def tiny_pack(real: dict) -> dict:
    """Age asked last, no max_questions (the default applies), no demos, and an age rule with a
    hole in it: only the probe just past a range's end (hi + 1) shows that age still matters."""
    d = copy.deepcopy(real)
    d.update(pack="schemes-tiny", version="0.0.1", date="2026-10-06")
    d.pop("max_questions")
    d.pop("demos")
    by_id = {q["id"]: q for q in d["questions"]}
    d["questions"] = [by_id["situation"], by_id["bank"], by_id["ration"], by_id["age"]]
    template = next(s for s in real["schemes"] if s["id"] == "pmjdy")

    def scheme(sid: str, rule: dict, **extra: Any) -> dict:
        s = copy.deepcopy(template)
        s.update(id=sid, short=sid.upper(), rule=rule, **extra)
        return s

    d["schemes"] = [
        scheme("hole", {"all": [{"any": [{"age": [0, 10]}, {"age": [50, None]}], "say": _t("10 or less, or 50 or more", "10 या कम, या 50 या ज़्यादा")},
                                {"fact": "widow", "say": _t("Widow", "विधवा")}]}),
        scheme("upper", {"all": [{"age": [0, 30], "say": _t("Age 30 or less", "उम्र 30 या कम")},
                                 {"not": {"fact": "bank"}, "say": _t("No bank account", "खाता नहीं")}]}),
        scheme("straddle", {"all": [{"age": [55, 64], "say": _t("Age 55 to 64", "उम्र 55 से 64")}, {"fact": "bpl", "say": _t("BPL", "BPL")}]},
               counter={"default": _t("{age_phrase}", "{age_phrase}"), "check": _t("Check: {age_phrase}", "जाँच: {age_phrase}")},
               check_how=_t("Ask at the office.", "दफ़्तर में पूछें।")),
    ]
    return d


_INDEX_KEY = re.compile(r"0|[1-9][0-9]*")


def check_carried(obj: Any, where: str) -> None:
    """Refuse values JSON cannot carry into JS unchanged.

    JS objects put integer-like keys first, whatever their insertion order, so key order could not
    be compared. And JS has one number type: a float with no fraction below 1e21 (67.0) arrives as
    the int 67, an int from 1e21 up as a float. The phone never sends either (JSON.stringify writes
    every integer below 1e21 as an int), so they have no place in the corpus."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if "$ref" == k or (_INDEX_KEY.fullmatch(k) and int(k) < 2**32 - 1):
                raise ValueError(f"{where}: key {k!r} cannot be carried to JS in order")
            check_carried(v, where)
    elif isinstance(obj, list):
        for v in obj:
            check_carried(v, where)
    elif isinstance(obj, float) and obj.is_integer() and abs(obj) < 1e21:
        raise ValueError(f"{where}: {obj!r} would reach JS as an int")
    elif isinstance(obj, int) and not isinstance(obj, bool) and abs(obj) >= 1e21:
        raise ValueError(f"{where}: {obj!r} would reach JS as a float")


class Table:
    """Store each long object or list once; refer to it as {"$ref": n}."""

    def __init__(self) -> None:
        self.rows: list = []
        self.index: dict[str, int] = {}

    def __call__(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            new: Any = {k: self(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            new = [self(v) for v in obj]
        else:
            return obj
        key = json.dumps(new, ensure_ascii=False, separators=(",", ":"))
        if len(key) < MIN_SHARED:
            return new
        ref = self.index.get(key)
        if ref is None:
            ref = self.index[key] = len(self.rows)
            self.rows.append(new)
        return {"$ref": ref}


def shrink(case: dict, table: Table) -> dict:
    out = dict(case)
    for key in ("next", "result", "result_already"):
        if key in out:
            out[key] = table(out[key])
    if "steps" in out:
        out["steps"] = [table(s) for s in out["steps"]]
    return out


def section(name: str, nav: Navigator, cases: list[dict], table: Table, **source: Any) -> dict:
    counts: dict[str, int] = {}
    for c in cases:
        check_carried(c, f"{name}: {c['id']}")
        group = c["id"].split("/")[0]
        counts[group] = counts.get(group, 0) + 1
    return {"name": name, **source, "counts": counts, "catalog": table(nav.catalog()),
            "cases": [shrink(c, table) for c in cases]}


def build(n_random: int, seed: int) -> dict:
    table = Table()
    nav = load_navigator()
    sections = [section(
        "schemes.v1", nav, known_cases(nav) + random_cases(nav, n_random, seed) + invalid_cases(nav), table,
        pack_file=PACK_FILE, pack_sha256=hashlib.sha256((ROOT / PACK_FILE).read_bytes()).hexdigest())]
    for offset, (name, make, share) in enumerate((("synthetic", synthetic_pack, 0.3), ("tiny", tiny_pack, 0.2)), 1):
        data = make(nav.pack.data)
        check_carried(data, name)
        other = Navigator(Pack(name=data["pack"], version=data["version"], date=data["date"], sha256="",
                               path=Path(name), data=data))
        cases = [call_case(other, "empty", {})] + random_cases(other, int(n_random * share), seed + offset)
        sections.append(section(name, other, cases, table, pack=data))
    return {
        "about": "Expected Navigator outputs for web/navigator.js; written by tests/js/make_nav_corpus.py",
        "today": TODAY.isoformat(),
        "sections": sections,
        "table": table.rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out", type=Path, default=ROOT / "tests" / "js" / "nav_corpus.json")
    ap.add_argument("--random", type=int, default=5000, help="random answer sets for schemes.v1")
    ap.add_argument("--seed", type=int, default=20261006)
    args = ap.parse_args(argv)
    corpus = build(args.random, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(corpus, ensure_ascii=False, separators=(",", ":"))
    # UTF-8 cannot carry the corpus's lone surrogate raw; inside a JSON string its escape is the same value.
    text = re.sub(r"[\ud800-\udfff]", lambda m: "\\u%04x" % ord(m.group()), text)
    args.out.write_text(text, encoding="utf-8")
    counts = "; ".join(f"{s['name']} {s['counts']}" for s in corpus["sections"])
    print(f"wrote {args.out} ({args.out.stat().st_size // 1024} KB): {counts}; {len(corpus['table'])} shared values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
