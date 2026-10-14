"""Build the phone app's display-language packs from the checked translations.

For every language in i18n/languages.json that is not built in (Hindi and English are), in that file's order,
whose i18n/<code>.json exists and passes scripts/i18n_check.py, writes web/i18n/<code>.json:

  {"lang", "name", "english", "dir", "base", "tts", "draft",
   "ui": {key: text},                         the app's own screen text, by key
   "text": {english: translation},            what the engines write, looked up by its English
   "templates": [[english, translation], ...]}  the same for text with {placeholders}, most specific first

web/i18n.js reads a pack: it looks up each English string an engine answered with, and fills a template's
placeholders from the English (translating the filled-in part too when it is itself a known text). Then writes
web/i18n/index.json, the language picker's list: Hindi, English and every language built, in the same order.

A language that fails the check is skipped with a warning; its old web/i18n/<code>.json, if any, is left as it
was but is no longer listed. Translations are display only: no engine, pack or verdict changes.

  python scripts/i18n_build.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from i18n_check import problems_for  # noqa: E402

I18N = ROOT / "i18n"
OUT = ROOT / "web" / "i18n"
_PH = re.compile(r"\{\w+\}")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data) -> int:
    body = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    path.write_text(body, encoding="utf-8")
    return len(body.encode("utf-8"))


def specificity(english: str) -> int:
    """How much fixed text a template has to match: its characters outside placeholders and whitespace."""
    return len("".join(_PH.sub("", english).split()))


def build_pack(lang: dict, src: dict, tr: dict) -> dict:
    text, templates = {}, []
    for key, item in src["text"].items():
        if _PH.search(item["en"]):
            templates.append([item["en"], tr["text"][key]])
        else:
            text[item["en"]] = tr["text"][key]
    templates.sort(key=lambda t: -specificity(t[0]))  # stable: equal ones keep source.json order
    return {
        "lang": lang["code"], "name": lang["name"], "english": lang["english"], "dir": lang["dir"],
        "base": lang["base"], "tts": lang["tts"], "draft": bool(lang.get("draft")),
        "ui": {key: tr["ui"][key] for key in src["ui"]},
        "text": text,
        "templates": templates,
    }


def entry(lang: dict) -> dict:
    return {"code": lang["code"], "name": lang["name"], "english": lang["english"], "dir": lang["dir"],
            "base": lang["base"], "draft": bool(lang.get("draft"))}


def main() -> int:
    langs = load(I18N / "languages.json")["languages"]
    src = load(I18N / "source.json")
    OUT.mkdir(parents=True, exist_ok=True)
    index, built, skipped = [], 0, 0
    for lang in langs:
        code = lang["code"]
        if lang.get("builtin"):
            index.append(entry(lang))
            print(f"{code}: built in")
            continue
        if not (I18N / f"{code}.json").exists():
            skipped += 1
            print(f"{code}: skipped, no i18n/{code}.json yet")
            continue
        probs = problems_for(code)
        if probs:
            skipped += 1
            old = " (its earlier web/i18n file is left in place, unlisted)" if (OUT / f"{code}.json").exists() else ""
            print(f"WARNING {code}: skipped, {len(probs)} problem{'s' * (len(probs) != 1)} in i18n/{code}.json{old}: "
                  + "; ".join(probs[:3]))
            continue
        pack = build_pack(lang, src, load(I18N / f"{code}.json"))
        size = dump(OUT / f"{code}.json", pack)
        index.append(entry(lang))
        built += 1
        print(f"{code}: {len(pack['ui'])} ui, {len(pack['text'])} text, {len(pack['templates'])} templates"
              f"{', draft' if pack['draft'] else ''} -> web/i18n/{code}.json ({size / 1024:.0f} KB)")
    dump(OUT / "index.json", index)
    print(f"total: {built} languages built, {skipped} skipped; web/i18n/index.json lists {len(index)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
