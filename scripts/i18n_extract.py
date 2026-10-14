"""Collect every string the phone app shows, for translation into India's scheduled languages.

Writes i18n/source.json: the app's own screen text (web/app.js, keys `ui`) and the text the engines put on a
verdict card or a benefits result (the fraud, schemes and demo packs, the UPI QR facts in sahayak/inputs/qr.py,
and the age label the benefits engine writes). Each item keeps its English, its Hindi and where it appears.

Translations are display only: the engines, the signed packs and every verdict stay exactly as they are.

  python scripts/i18n_extract.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Strings the app adds for the language picker (English and Hindi; the other languages are translated).
NEW_UI = {
    "lang_title": {"en": "Choose your language", "hi": "अपनी भाषा चुनें"},
    "lang_note": {"en": "This language is a machine translation, not yet checked by a native speaker.",
                  "hi": "यह भाषा मशीन से अनुवाद की गई है; किसी मूल वक्ता ने अभी इसे जाँचा नहीं है।"},
    "lang_detect": {"en": "Sahayak reads messages in Hindi, English and Hinglish. A message in another language gets “Could not check”.",
                    "hi": "सहायक हिंदी, अंग्रेज़ी और हिंग्लिश में लिखे मैसेज पढ़ता है। किसी और भाषा के मैसेज पर “जाँच नहीं हो सकी” आता है।"},
    "lang_mic_off": {"en": "Speaking to Sahayak works in Hindi and English only. Please type or paste.",
                     "hi": "सहायक से बोलकर बात सिर्फ़ हिंदी और अंग्रेज़ी में होती है। कृपया लिखें या चिपकाएँ।"},
    "lang_close": {"en": "Close", "hi": "बंद करें"},
}

# Text made by code rather than read from a pack (kept in step with sahayak/inputs/qr.py and navigator/engine.py).
CODE_TEXT = [
    ({"en": "Scanning this QR and entering your UPI PIN sends money from your account to {who} ({amount}). A QR never brings money in.",
      "hi": "इस QR को स्कैन करके UPI PIN डालने पर पैसे आपके खाते से {who} को जाते हैं ({amount})। QR से पैसे कभी आते नहीं।"},
     "UPI QR fact (placeholders: payee name, amount)"),
    ({"en": "Scanning this QR and entering your UPI PIN sends money from your account to {who}. A QR never brings money in.",
      "hi": "इस QR को स्कैन करके UPI PIN डालने पर पैसे आपके खाते से {who} को जाते हैं। QR से पैसे कभी आते नहीं।"},
     "UPI QR fact (placeholder: payee name)"),
    ({"en": "It says \"{name}\", but the money goes to the UPI ID {payee}. Banks, police and the government do not collect money by QR.",
      "hi": "नाम \"{name}\" लिखा है, पर पैसे UPI ID {payee} में जाएँगे। बैंक, पुलिस या सरकार QR से पैसे नहीं माँगते।"},
     "UPI QR warning (placeholders: name, UPI ID)"),
    ({"en": "someone", "hi": "someone"}, "UPI QR: payee when the code names nobody"),
    ({"en": "{n} years", "hi": "{n} साल"}, "benefits: an age the person typed, e.g. '74 years'"),
]


def ui_strings() -> dict:
    """The T dictionary of web/app.js, read by Node so the JS stays the one source."""
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    start = js.index("const T = {")
    end = js.index("\n  };\n", start) + 5
    block = js[start + len("const T = "):end].rstrip().rstrip(";")
    out = subprocess.run(["node", "-e", f"process.stdout.write(JSON.stringify({block}))"],
                         capture_output=True, text=True, check=True).stdout
    T = json.loads(out)
    ui = {k: {"en": T["en"][k], "hi": T["hi"].get(k, T["en"][k])} for k in T["en"]}
    ui.update(NEW_UI)
    return ui


def _where(path: str) -> str:
    p = re.sub(r"\[\d+\]", "", path)
    p = re.sub(r"\.(signals|categories|scripts)\.([\w-]+)", r".\1(\2)", p)
    return p


def pack_strings() -> list[tuple[dict, str]]:
    items: list[tuple[dict, str]] = []

    def walk(o, path):
        if isinstance(o, dict):
            if isinstance(o.get("en"), (str, list)) and isinstance(o.get("hi"), (str, list)):
                if isinstance(o["en"], list):
                    for i, (en, hi) in enumerate(zip(o["en"], o["hi"])):
                        items.append(({"en": en, "hi": hi}, _where(path) + f" #{i + 1}"))
                else:
                    items.append(({"en": o["en"], "hi": o["hi"]}, _where(path)))
                return
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    for name in ("fraud", "schemes", "demo"):
        walk(json.loads((ROOT / "packs" / f"{name}.v1.json").read_text(encoding="utf-8")), name)
    return items


def main() -> int:
    seen: dict[str, dict] = {}
    for obj, where in pack_strings() + CODE_TEXT:
        en = obj["en"].strip()
        if not en:
            continue
        if en in seen:
            if where not in seen[en]["where"]:
                seen[en]["where"].append(where)
            continue
        seen[en] = {"en": en, "hi": obj["hi"].strip(), "where": [where]}
    text = {f"t{i:03d}": {**v, "where": "; ".join(v["where"][:3])} for i, v in enumerate(seen.values(), 1)}
    out = {"note": "Source text for the display languages. ui: the app's own screens (web/app.js). text: what the engines "
                   "and packs put on a card. Keep every {placeholder}, number, link, phone number and acronym exactly.",
           "ui": ui_strings(), "text": text}
    path = ROOT / "i18n" / "source.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{path.relative_to(ROOT)}: {len(out['ui'])} screen strings, {len(text)} card and pack strings, "
          f"{sum(len(v['en'].split()) for v in list(out['ui'].values()) + list(text.values()))} English words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
