"""Pack update prepared on 7 Oct 2026 (fraud pack 1.5.0, schemes pack 1.1.0), after a stress test and three mock
jury panels. Run it once on a machine with a signer's key (SAHAYAK_SIGNER; see scripts/sign_packs.py): it edits
the packs and re-signs them (scripts/packtool.save). Safe to run twice: each change is applied only once.

  SAHAYAK_SIGNER=roshan python scripts/pack_update_1_5.py
  python -m pytest

What it changes, and why:
- fraud: a fourth verdict, "could not check", for a message mostly in a script Sahayak cannot read yet
  (Bengali, Tamil, Kannada, Urdu and seven more scripts, and Marathi; sahayak/fraud/normalize.py). A Tamil OTP scam
  used to get the green "no scam signs", because no Hindi or English signal could fire on it. The code
  falls back to the old behaviour with a pack that has no "unreadable" section.
- fraud: SBI's missed-call banking numbers (balance 9223766666, mini statement 9223866666) are official
  numbers, and HDFC Bank's SMS link domain hdfcbk.io (named in the bank's own advisory) is an official domain:
  pasted without a sender, both genuine messages read as Scam.
- fraud: what to do. 1930 is for money already lost; an attempt is reported on Chakshu at
  sancharsaathi.gov.in. The KYC card no longer says "delete the message": a complaint needs it as proof.
- fraud: Chakshu joins the helplines.
- schemes: an Aadhaar OTP is told only face to face at the counter while the card is being made, so the
  scheme slip ("bring Aadhaar for e-KYC") no longer contradicts the fraud note ("anyone asking for an OTP in
  a scheme's name is a fraudster"). PM-JAY covers hospital admission, not outpatient visits, and the 70+
  cover is shared with a spouse who is also 70 or more. Pension amounts say "from the centre; your state may
  add more" next to the figure, and only one of the three NSAP pensions is paid to a person.
Hindi strings here, like the rest of the packs, still need a native speaker's review.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.packtool import load, save  # noqa: E402

CHAKSHU = "sancharsaathi.gov.in"
UNREADABLE_VERDICT = {
    "label": {"en": "Could not check", "hi": "जाँच नहीं हो सकी"},
    "headline": {"en": "Sahayak cannot read {language} yet, so it cannot tell whether this message is genuine or a scam.",
                 "hi": "सहायक अभी {language} नहीं पढ़ सकता, इसलिए यह नहीं बता सकता कि यह संदेश असली है या ठगी।"},
}
UNREADABLE = {
    "reason": {"en": "Sahayak reads Hindi and English only, so finding nothing in this message would mean nothing.",
               "hi": "सहायक अभी सिर्फ़ हिंदी और अंग्रेज़ी पढ़ता है, इसलिए इस संदेश में कुछ न मिलने का कोई मतलब नहीं।"},
    "actions": {
        "en": ["Do not tell anyone an OTP, PIN or card number, and do not pay anything, because of this message.",
               "Before you act, ask someone you trust who reads this language, or the operator at this counter.",
               "To check a bank message, call the number printed on your passbook or card."],
        "hi": ["इस संदेश के कहने पर किसी को OTP, PIN या कार्ड नंबर न बताएं, और कोई पैसा न भेजें।",
               "कुछ करने से पहले किसी भरोसेमंद व्यक्ति से पूछें जो यह भाषा पढ़ सके, या इस काउंटर के ऑपरेटर से।",
               "बैंक के संदेश की जाँच के लिए पासबुक या कार्ड पर छपे नंबर पर कॉल करें।"],
    },
    "scripts": {
        "bn": {"en": "Bengali or Assamese", "hi": "बांग्ला या असमिया"},
        "pa": {"en": "Punjabi (Gurmukhi)", "hi": "पंजाबी (गुरमुखी)"},
        "gu": {"en": "Gujarati", "hi": "गुजराती"},
        "or": {"en": "Odia", "hi": "ओड़िया"},
        "ta": {"en": "Tamil", "hi": "तमिल"},
        "te": {"en": "Telugu", "hi": "तेलुगु"},
        "kn": {"en": "Kannada", "hi": "कन्नड़"},
        "ml": {"en": "Malayalam", "hi": "मलयालम"},
        "ur": {"en": "Urdu", "hi": "उर्दू"},
        "sat": {"en": "Santali (Ol Chiki)", "hi": "संथाली (ओल चिकी)"},
        "mni": {"en": "Manipuri (Meetei Mayek)", "hi": "मणिपुरी (मीतेई मयेक)"},
        "mr": {"en": "Marathi", "hi": "मराठी"},
    },
}
OFFICIAL_NUMBERS = ["9223766666", "9223866666"]  # SBI missed-call banking: balance, mini statement
OFFICIAL_DOMAINS = ["hdfcbk.io"]
HELPLINE = {"id": "chakshu", "kind": "web", "value": CHAKSHU,
            "label": {"en": "Report a fraud call or SMS (Chakshu)", "hi": "ठगी की कॉल या SMS की शिकायत (चक्षु)"}}
# (category, index of the action to replace, en, hi)
ACTIONS = [
    ("otp_pin", 2, "If money was taken, call 1930 at once: a quick report can stop it.",
     "अगर पैसे कट गए हैं, तो तुरंत 1930 पर कॉल करें; जल्दी शिकायत से पैसा रुक सकता है।"),
    ("kyc", 2, f"Keep the message as proof. If you clicked or shared anything, call 1930 at once; if not, report it on Chakshu at {CHAKSHU}.",
     f"मैसेज सबूत के तौर पर रखें। अगर आपने क्लिक किया या कुछ बताया है, तो तुरंत 1930 पर कॉल करें; नहीं तो {CHAKSHU} पर चक्षु में शिकायत करें।"),
    ("courier", 2, f"Report the number on Chakshu at {CHAKSHU}; if you paid anything, call 1930 at once.",
     f"इस नंबर की शिकायत {CHAKSHU} पर चक्षु में करें; अगर कुछ भी भुगतान किया है, तो तुरंत 1930 पर कॉल करें।"),
    ("electricity", 2, f"Report the number on Chakshu at {CHAKSHU}; call 1930 only if you lost money.",
     f"इस नंबर की शिकायत {CHAKSHU} पर चक्षु में करें; पैसे गए हों, तभी 1930 पर कॉल करें।"),
    ("prize", 2, f"Block the sender and report it on Chakshu at {CHAKSHU}.",
     f"भेजने वाले को ब्लॉक करें और {CHAKSHU} पर चक्षु में शिकायत करें।"),
]

FRAUD_NOTE = {
    "en": "If anyone calls, texts or sends a link in a scheme's name and asks for an OTP or money, it is a scam. "
          "Tell an Aadhaar OTP only face to face at the counter, while your card is being made in front of you. "
          "Do not pay agents for government forms. If you lose money, call 1930.",
    "hi": "योजना के नाम पर कोई फ़ोन, मैसेज या लिंक से OTP या पैसे माँगे, तो वह ठगी है। आधार का OTP सिर्फ़ काउंटर पर "
          "आमने-सामने बताएं, जब आपका कार्ड आपके सामने बन रहा हो। सरकारी फ़ॉर्म के लिए दलाल को पैसे न दें। पैसे गए हों, "
          "तो 1930 पर कॉल करें।",
}
PMJAY = {
    "what": {"en": "Free treatment when admitted to a listed hospital, up to ₹5 lakh a year. Outpatient visits "
                   "(OPD) are not covered.",
             "hi": "सूचीबद्ध अस्पताल में भर्ती होने पर हर साल ₹5 लाख तक मुफ़्त इलाज। बिना भर्ती के इलाज (OPD) इसमें नहीं।"},
    "benefit": {"en": "Free hospital treatment up to ₹5 lakh a year per family. Age 70 or more: up to ₹5 lakh a year "
                      "more (Ayushman Vay Vandana card), shared only with family members who are also 70 or more.",
                "hi": "परिवार को हर साल ₹5 लाख तक अस्पताल में मुफ़्त इलाज। 70 साल या ज़्यादा: हर साल ₹5 लाख तक और "
                      "(आयुष्मान वय वंदना कार्ड), जो सिर्फ़ परिवार के 70+ लोगों में बँटता है।"},
    "benefit_now": [
        {"when": {"age": [70, None]}, "hi": "अस्पताल में इलाज: हर साल ₹5 लाख तक, आपके लिए (70+ पति या पत्नी के साथ साझा)",
         "en": "Hospital care up to ₹5 lakh a year, for you (shared with a spouse who is 70+)"},
        {"when": {"age": [0, 69]}, "hi": "अस्पताल में इलाज: परिवार को हर साल ₹5 लाख तक",
         "en": "Hospital care up to ₹5 lakh a year, for the family"},
    ],
}
PENSION_NOW = {"en": "{amount} from the centre; your state may add more",  # "₹200 a month" -> ...
               "hi": "केंद्र से {amount}; राज्य इसमें और जोड़ सकता है"}
ONE_PENSION = {"en": "A person gets only one of these pensions. If more than one shows, ask the office which suits you.",
               "hi": "इनमें से एक ही पेंशन मिलती है। एक से ज़्यादा दिखें, तो दफ़्तर में पूछें कि आपके लिए कौन-सी सही है।"}


def update_fraud(fraud: dict) -> None:
    d = fraud["domains"]
    d["official_domains"] += [x for x in OFFICIAL_DOMAINS if x not in d["official_domains"]]
    d.setdefault("official_numbers", [])
    d["official_numbers"] += [x for x in OFFICIAL_NUMBERS if x not in d["official_numbers"]]
    fraud["verdicts"]["unreadable"] = UNREADABLE_VERDICT
    if "unreadable" not in fraud:  # keep it next to no_signs, so the pack reads in order
        items = list(fraud.items())
        at = [k for k, _ in items].index("no_signs") + 1
        fraud.clear()
        fraud.update(items[:at] + [("unreadable", UNREADABLE)] + items[at:])
    else:
        fraud["unreadable"] = UNREADABLE
    if not any(h["id"] == HELPLINE["id"] for h in fraud["helplines"]):
        fraud["helplines"].append(HELPLINE)
    for cat, i, en, hi in ACTIONS:
        acts = fraud["categories"][cat]["actions"]
        acts["en"][i], acts["hi"][i] = en, hi
    fraud["version"], fraud["date"] = "1.5.0", "2026-10-07"


def update_schemes(schemes: dict) -> None:
    schemes["fraud_note"] = FRAUD_NOTE
    for s in schemes["schemes"]:
        if s["id"] == "pmjay":
            s.update(PMJAY)
        if s["id"] in ("ignoaps", "ignwps", "igndps"):
            for v in s["benefit_now"]:
                for lang in ("en", "hi"):
                    if "{amount}" not in v[lang] and PENSION_NOW[lang].split("{amount}")[1] not in v[lang]:
                        v[lang] = PENSION_NOW[lang].replace("{amount}", v[lang])
            s["notes"] = [ONE_PENSION if n["en"].startswith("If more than one pension") else n for n in s["notes"]]
    schemes["version"], schemes["date"] = "1.1.0", "2026-10-07"


def _changed_strings(before, after, out: dict) -> dict:
    if isinstance(before, dict) and isinstance(after, dict):
        for k in before.keys() & after.keys():
            _changed_strings(before[k], after[k], out)
    elif isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        for b, a in zip(before, after):
            _changed_strings(b, a, out)
    elif isinstance(before, str) and isinstance(after, str) and before != after:
        out[before] = after
    return out


def save_in_place(path: Path, before: dict, after: dict) -> None:
    """Write `after` by swapping only the strings that changed, so the hand-laid-out schemes pack keeps its
    layout and the diff shows the real changes; packtool.save (which re-lays it out) is the fallback."""
    import json
    text = path.read_text(encoding="utf-8")
    top = {k for k, v in before.items() if isinstance(v, str) and after.get(k) != v}  # "version", "date"
    for k in top:  # once, by key: the same date also stands in every source's "checked" field
        text = text.replace(f'"{k}": {json.dumps(before[k], ensure_ascii=False)}',
                            f'"{k}": {json.dumps(after[k], ensure_ascii=False)}', 1)
    inner = _changed_strings({k: v for k, v in before.items() if k not in top},
                             {k: v for k, v in after.items() if k not in top}, {})
    for old, new in inner.items():
        text = text.replace(json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False))
    if json.loads(text) != after:
        save(path, after)
        return
    path.write_text(text, encoding="utf-8")
    save_signature(path)


def save_signature(path: Path) -> None:
    from sahayak.config import get_settings
    from sahayak.signing import load_or_create_private_key, sign_file, signer_name
    key_file = get_settings().home / "keys" / f"{signer_name()}.key"
    if key_file.exists():
        sign_file(path, load_or_create_private_key(key_file))
    else:
        print(f"note: {path.name} changed but no signing key is here; run scripts/sign_packs.py")


def main() -> None:
    import copy
    fraud_path, schemes_path = ROOT / "packs" / "fraud.v1.json", ROOT / "packs" / "schemes.v1.json"
    fraud = load(fraud_path)
    update_fraud(fraud)
    save(fraud_path, fraud)
    schemes = load(schemes_path)
    before = copy.deepcopy(schemes)
    update_schemes(schemes)
    save_in_place(schemes_path, before, schemes)
    print("fraud 1.5.0 and schemes 1.1.0 written; signed if this machine has the signer's key (SAHAYAK_SIGNER). "
          "Now run: python -m pytest")


if __name__ == "__main__":
    main()
