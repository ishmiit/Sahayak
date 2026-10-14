"""Display languages: scripts/i18n_build.py builds web/i18n/ only from translations that pass scripts/i18n_check.py,
each built pack carries every string of i18n/source.json, and web/i18n.js puts the engines' filled-in English
(a reason with its web address, a counter sentence with its age phrase) into the chosen language."""
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
I18N = ROOT / "i18n"
BUILT = ROOT / "web" / "i18n"
NODE = shutil.which("node")
_PH = re.compile(r"\{\w+\}")
_TAMIL = re.compile("[஀-௿]")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _index() -> list[dict]:
    path = BUILT / "index.json"
    assert path.is_file(), "run python3 scripts/i18n_build.py"
    return _load(path)


def _built() -> list[str]:
    return [x["code"] for x in _index() if x["code"] not in ("hi", "en")]


def test_the_index_lists_hindi_english_and_every_built_pack_in_language_order():
    langs = _load(I18N / "languages.json")["languages"]
    by_code = {x["code"]: x for x in langs}
    index = _index()
    codes = [x["code"] for x in index]
    assert codes[:2] == ["hi", "en"]
    assert len(set(codes)) == len(codes)
    assert codes == [x["code"] for x in langs if x["code"] in codes]
    for x in index:
        lang = by_code[x["code"]]
        assert x == {"code": lang["code"], "name": lang["name"], "english": lang["english"], "dir": lang["dir"],
                     "base": lang["base"], "draft": bool(lang.get("draft"))}
    for code in codes[2:]:
        assert (BUILT / f"{code}.json").is_file(), code


def test_every_built_pack_carries_every_source_string():
    src = _load(I18N / "source.json")
    for code in _built():
        pack = _load(BUILT / f"{code}.json")
        assert pack["lang"] == code
        assert set(src["ui"]) <= set(pack["ui"]), code
        templates = {en for en, _ in pack["templates"]}
        assert all(_PH.search(en) for en in templates), code
        assert not any(_PH.search(en) for en in pack["text"]), code
        missing = [item["en"] for item in src["text"].values()
                   if item["en"] not in pack["text"] and item["en"] not in templates]
        assert missing == [], f"{code}: rebuild with scripts/i18n_build.py; missing {missing[:3]}"


def test_only_languages_that_pass_the_check_are_built():
    problems_for = _script("i18n_check").problems_for
    for code in _built():
        assert problems_for(code) == [], code


_LOOKUP = """
const I18n = require(process.argv[1]);
let data = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { data += chunk; });
process.stdin.on("end", () => {
  const { pack, inputs } = JSON.parse(data);
  const tr = I18n.create(pack);
  process.stdout.write(JSON.stringify(inputs.map((s) => tr.lookup(s))));
});
"""


def _lookup(pack, inputs: list) -> list:
    run = subprocess.run([NODE, "-e", _LOOKUP, str(ROOT / "web" / "i18n.js")], input=json.dumps({"pack": pack, "inputs": inputs}),
                         capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_lookup_fills_templates_and_translates_what_it_fills_in():
    pack = {"text": {"Hello": "Namaskara", "I am 80 or older.": "E"},
            "templates": [["The web address imitates a known name ({domain}).", "X {domain} Y"],
                          ["Namaste. {age_phrase} I want it.", "N {age_phrase} W"],
                          ["I am {n} years old.", "A {n} B"]]}
    cases = {
        "Hello": "Namaskara",
        "  Hello ": "Namaskara",
        "The web address imitates a known name (sbi-kyc-update.xyz).": "X sbi-kyc-update.xyz Y",
        "Namaste. I am 74 years old. I want it.": "N A 74 B W",
        "Namaste. I am 80 or older. I want it.": "N E W",
        "Namaste. I want it.": "N W",  # the engine's empty age phrase
        "unknown": None,
        "constructor": None,
        "": None,
    }
    assert _lookup(pack, list(cases)) == list(cases.values())
    assert _lookup(pack, [None, 5, {"en": "Hello"}, ["Hello"]]) == [None, None, None, None]
    assert _lookup(None, ["Hello"]) == [None]


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_the_tamil_pack_translates_filled_engine_text():
    if not (BUILT / "ta.json").is_file():
        pytest.skip("web/i18n/ta.json is not built")
    ta = _load(BUILT / "ta.json")
    signals = _load(ROOT / "packs" / "fraud.v1.json")["signals"]
    reasons = [s["reason"]["en"] for s in signals.values() if "{domain}" in s.get("reason", {}).get("en", "")]
    assert reasons
    filled = [r.replace("{domain}", "sbi-kyc-update.xyz") for r in reasons]
    counter = "Namaste. I am 74 years old. I want to apply for the old-age pension (IGNOAPS)."
    out = _lookup(ta, filled + [counter])
    for english, tamil in zip(filled, out):
        assert tamil and "sbi-kyc-update.xyz" in tamil and _TAMIL.search(tamil), english
    assert "74" in out[-1] and "IGNOAPS" in out[-1] and "{" not in out[-1] and "years" not in out[-1]
