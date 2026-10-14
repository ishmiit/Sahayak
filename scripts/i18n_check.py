"""Check a display-language translation before it is built into the app.

  python scripts/i18n_check.py ta            # one language (i18n/ta.json)
  python scripts/i18n_check.py --all         # every translated language

A translation file is {"lang": "<code>", "ui": {key: text}, "text": {id: text}} with the keys of i18n/source.json.
For every string it checks: present and not empty; the same {placeholders}; every number, link, phone number and
protected word (OTP, PIN, UPI, KYC, QR, scheme short names...) kept as written; mostly in the language's script;
not left in English. Exit code 1 if anything fails.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = {
    "Devanagari": "ऀ-ॿ꣠-ꣿ",
    "Bengali": "ঀ-৿",
    "Gujarati": "઀-૿",
    "Gurmukhi": "਀-੿",
    "Oriya": "଀-୿",
    "Tamil": "஀-௿",
    "Telugu": "ఀ-౿",
    "Kannada": "ಀ-೿",
    "Malayalam": "ഀ-ൿ",
    "Arabic": "؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿",
    "Ol Chiki": "᱐-᱿",
}
# Words kept in Latin letters in every language, as the Hindi text does.
PROTECTED = ["OTP", "PIN", "UPI", "KYC", "QR", "SMS", "CSC", "APK", "PM-JAY", "PMSBY", "PMJJBY", "APY",
             "IGNOAPS", "IGNWPS", "IGNDPS", "NFBS", "PM-SYM", "PMJDY", "NSAP", "UAN", "IFSC", "CVV", "BPL",
             "AAY", "PHH", "APL", "OPD", "ATM", "EPFO", "ESIC", "NPS", "SBI", "RBI", "NPCI", "CBI", "TRAI"]
_PH = re.compile(r"\{\w+\}")
_NUM = re.compile(r"\d[\d,.:/]*\d|\d")
_LINK = re.compile(r"(?:https?://)?(?:[a-z0-9-]+\.)+(?:in|com|xyz|org|net|io|gov\.in|bank\.in|top|site|link)\b(?:/\S*)?", re.I)
_LATIN_WORD = re.compile(r"[A-Za-z]{3,}")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def languages() -> dict:
    return {x["code"]: x for x in load(ROOT / "i18n" / "languages.json")["languages"]}


def problems_for(code: str) -> list[str]:
    lang = languages()[code]
    src = load(ROOT / "i18n" / "source.json")
    path = ROOT / "i18n" / f"{code}.json"
    if not path.exists():
        return [f"{path.name}: missing"]
    try:
        tr = load(path)
    except ValueError as e:
        return [f"{path.name}: not valid JSON ({e})"]
    letters = re.compile(f"[{SCRIPTS[lang['script']]}]")
    out: list[str] = []
    for section in ("ui", "text"):
        want, got = src[section], tr.get(section, {})
        missing = [k for k in want if k not in got]
        extra = [k for k in got if k not in want]
        if missing:
            out.append(f"{section}: missing {len(missing)}: {', '.join(missing[:12])}")
        if extra:
            out.append(f"{section}: unknown keys {', '.join(extra[:12])}")
        for key, item in want.items():
            if key not in got:
                continue
            en, t = item["en"], got[key]
            where = f"{section}.{key}"
            if not isinstance(t, str) or not t.strip():
                out.append(f"{where}: empty")
                continue
            if sorted(_PH.findall(en)) != sorted(_PH.findall(t)):
                out.append(f"{where}: placeholders {sorted(_PH.findall(en))} became {sorted(_PH.findall(t))}")
            nums_t = set(_NUM.findall(t))
            for n in set(_NUM.findall(en)):
                if n not in nums_t and n.replace(",", "") not in t.replace(",", ""):
                    out.append(f"{where}: number {n} missing")
            for link in set(m.group(0).lower() for m in _LINK.finditer(en)):
                if link not in t.lower():
                    out.append(f"{where}: link {link} missing")
            for word in PROTECTED:
                if re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", en) and word not in t:
                    out.append(f"{where}: keep '{word}' as written")
            # script: most letters outside protected words, links and placeholders are the language's own
            rest = _PH.sub(" ", t)
            rest = _LINK.sub(" ", rest)
            for word in PROTECTED:
                rest = rest.replace(word, " ")
            own = len(letters.findall(rest))
            latin = sum(len(w) for w in _LATIN_WORD.findall(rest))
            words_en = len(_LATIN_WORD.findall(_LINK.sub(" ", _PH.sub(" ", en))))
            if words_en >= 2 and own == 0:
                out.append(f"{where}: not in {lang['script']} script")
            elif latin > own and words_en >= 3:
                out.append(f"{where}: mostly Latin letters ({latin} Latin vs {own} {lang['script']})")
    return out


def main(argv: list[str]) -> int:
    codes = [c for c, x in languages().items() if not x.get("builtin")] if argv == ["--all"] else argv
    if not codes:
        print(__doc__)
        return 2
    bad = 0
    for code in codes:
        probs = problems_for(code)
        print(f"{code}: {'OK' if not probs else f'{len(probs)} problems'}")
        for p in probs[:60]:
            print(f"  - {p}")
        bad += bool(probs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
