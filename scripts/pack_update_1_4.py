"""Pack update prepared on 6 Oct 2026 (fraud pack 1.4.0, demo pack 1.4.0). Run it once on a machine with a
signer's key (SAHAYAK_SIGNER, default the team key; see scripts/sign_packs.py): it edits the packs and re-signs
them (scripts/packtool.save). Safe to run twice: every change is applied only if it is not there yet.

  python scripts/pack_update_1_4.py
  python -m pytest

What it changes, and why:
- fraud: official domains for utilities, insurers and couriers that are brand tokens but had no official
  domain, so their genuine bills and notices read as Suspicious (BESCOM, MSEDCL, UPPCL, Tata Power, BSES,
  ICICI Lombard, Blue Dart, FedEx, DHL). Each domain was checked against the company's own site.
- fraud: a new signal, scheme_fee: money sent to a phone number, UPI ID or link to get a government scheme
  or card ("आयुष्मान कार्ड बनवाने के लिए 500 रुपये इस नंबर पर भेजें"). Ayushman and e-Shram cards are free;
  a fee paid at the counter is not flagged. The detection is in sahayak/fraud/signals.py and
  web/checker.js and stays off until this definition is in the pack.
- fraud: the first "what to do" line for a fake government scheme now covers both tricks, paying a number and
  installing an app from a link (it used to name only the app).
- demo: a tap-to-try example of that scam, for the app, the jury kit and the deck.
Hindi strings here, like the rest of the pack, still need a native speaker's review.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.packtool import load, save  # noqa: E402

DOMAINS = ["bescom.co.in", "mahadiscom.in", "uppcl.org", "tatapower.com", "tatapower-ddl.com", "bsesdelhi.com",
           "icicilombard.com", "bluedart.com", "fedex.com", "dhl.com"]
SCHEME_FEE = {
    "weight": 3.0, "hard": False, "category": "govt_scheme", "show": True,
    "reason": {
        "en": "It asks you to send money to a phone number, UPI ID or link to get a government scheme or card. "
              "Government benefits are never given for money sent this way; Ayushman and e-Shram cards are free.",
        "hi": "इसमें सरकारी योजना या कार्ड के लिए किसी नंबर, UPI ID या लिंक पर पैसे भेजने को कहा गया है। सरकारी फ़ायदे "
              "ऐसे भेजे पैसों से नहीं मिलते; आयुष्मान और ई-श्रम कार्ड मुफ़्त बनते हैं।",
    },
}
SCHEME_ACTION = {  # replaces the first govt_scheme action ("…do not ask you to install apps from links.")
    # "never" stays close to "install": the safety gate reads negation only a few words back
    "en": "Government schemes never ask you to install an app from a link, or to send money to a phone number.",
    "hi": "सरकारी योजनाएँ लिंक से ऐप डालने या किसी नंबर पर पैसे भेजने को नहीं कहतीं।",
}
AYUSHMAN_EXAMPLE = {
    "id": "ayushman_fee",
    "label": {"en": "\"Pay ₹500 for your Ayushman card\"", "hi": "\"आयुष्मान कार्ड के लिए ₹500 भेजें\""},
    "text": "आयुष्मान कार्ड बनवाने के लिए 500 रुपये इस नंबर पर भेजें 9876012345, कार्ड घर आ जाएगा। आज आखिरी दिन है।",
    "sender": "9876012345",
}


def main() -> None:
    fraud_path, demo_path = ROOT / "packs" / "fraud.v1.json", ROOT / "packs" / "demo.v1.json"
    fraud = load(fraud_path)
    official = fraud["domains"]["official_domains"]
    official += [d for d in DOMAINS if d not in official]
    if "scheme_fee" not in fraud["signals"]:
        # keep it next to govt_scheme_bait, so the pack reads in order
        items = list(fraud["signals"].items())
        at = [k for k, _ in items].index("govt_scheme_bait") + 1
        fraud["signals"] = dict(items[:at] + [("scheme_fee", SCHEME_FEE)] + items[at:])
    actions = fraud["categories"]["govt_scheme"]["actions"]
    for lang in ("en", "hi"):
        actions[lang][0] = SCHEME_ACTION[lang]
    fraud["version"], fraud["date"] = "1.4.0", "2026-10-06"
    save(fraud_path, fraud)

    demo = load(demo_path)
    if not any(e["id"] == AYUSHMAN_EXAMPLE["id"] for e in demo["examples"]):
        at = [e["id"] for e in demo["examples"]].index("scheme_apk") + 1
        demo["examples"].insert(at, AYUSHMAN_EXAMPLE)
    demo["version"], demo["date"] = "1.4.0", "2026-10-06"
    save(demo_path, demo)
    print("fraud 1.4.0 and demo 1.4.0 written; signed if this machine has the signer's key (SAHAYAK_SIGNER). Now run: python -m pytest")


if __name__ == "__main__":
    main()
