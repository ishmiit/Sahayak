"""Pack update prepared on 7 Oct 2026 (fraud pack 1.7.0): the live-demo traps still open after 1.6.0.
Run it once on a machine with a signer's key (SAHAYAK_SIGNER; see scripts/sign_packs.py): it edits the pack and re-signs it.
Safe to run twice: each change is applied only once. The engine code that uses these entries is in
sahayak/fraud/signals.py and web/checker.js; each rule stays off until this pack defines its entries.

  SAHAYAK_SIGNER=roshan python scripts/pack_update_1_7.py
  python -m pytest

What it adds, and why (each change was measured on every benchmark set before it was adopted; PROGRESS.md D38):
- call_forwarding (+4.0, hard) and the category call_forward: a caller asks you to dial a code such as
  "*401*<number>" or "**21*<number>#" ("star 4 0 1 star"). It forwards your calls, and your bank's OTP calls, to the
  scammer. The advice gives ##002#, which cancels all forwarding.
- unseen_advance (+3.0) and the category deal_advance: an advance, token or deposit asked for something you cannot
  see first: a flat whose "officer" owner will courier the keys, a plot with "no site visit needed", a pilgrimage
  helicopter seat whose ticket comes on WhatsApp.
- delivery_fee (+3.0, courier) with delivery_problem: a small fee for a parcel whose delivery failed or whose
  address is "incomplete", paid through a link. Courier companies do not collect fees through an SMS link (their
  own sites, listed below, stay official); a COD amount beside a tracking link is not this.
- link_hiding (+2.0): "remove the spaces and open", "स्पेस हटाकर खोलें", beside a link that is not official.
- scheme_click (+1.5, govt_scheme): a forwarded "free scheme" or "free registration" post that says click on the
  photo or see the details, with no link in the text: the link sits in the image (PublicBench dev half). "Click a
  photo of your Aadhaar" is taking a picture, not this.
- otp_terms += "confirmation code" (the card-limit "upgrade" call that asks you to read out the code).
- Fewer false alarms on everyday messages: the brands' own short-link domains (amzn.in, fkrt.it, ...) and couriers'
  sites are official; "customs" alone no longer means a seized parcel (India Post's "customs duty is payable").
Hindi strings, like the rest of the pack, still need a native speaker's review.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.packtool import load, save  # noqa: E402

NEW_LEXICONS = {
    "link_hiding_terms": [
        "remove the space", "remove the spaces", "remove space", "remove spaces", "link without spaces",
        "open without spaces", "space hatakar", "space hata kar", "space hata ke", "space hatake",
        "bina space ke kholen", "bina space ke open", "स्पेस हटाकर", "स्पेस हटा कर", "स्पेस हटाके", "स्पेस हटा के",
        "बिना स्पेस के खोलें", "बिना स्पेस के लिंक"],
    "advance_ask": [
        "advance", "advance payment", "advance amount", "token", "token amount", "token money", "booking amount",
        "booking advance", "booking money", "deposit", "security deposit", "bayana", "beyana",
        "एडवांस", "टोकन", "बयाना", "बुकिंग राशि", "बुकिंग अमाउंट", "अग्रिम", "अग्रिम राशि", "जमानत राशि"],
    "unseen_terms": [
        "courier the keys", "courier the key", "keys by courier", "key by courier", "send the keys", "send you the keys",
        "can't show", "cannot show", "can not show", "can't come to show", "cannot come to show", "without seeing",
        "without visiting", "no site visit", "no need for site visit", "no need to visit", "site visit not required",
        "no need to see", "ticket pdf on whatsapp", "ticket on whatsapp", "pdf on whatsapp", "tickets on whatsapp",
        "bina dekhe", "dikha nahi sakta", "dikha nahi sakte", "dikha nahi sakti", "site visit ki zarurat nahi",
        "site visit ki jarurat nahi", "site visit ki zaroorat nahi", "chabi courier", "chaabi courier",
        "बिना देखे", "साइट विज़िट की ज़रूरत नहीं", "साइट विजिट की जरूरत नहीं", "साइट देखने की जरूरत नहीं",
        "देखने आने की जरूरत नहीं", "दिखा नहीं सकता", "दिखा नहीं सकते", "चाबी कूरियर", "चाबियाँ कूरियर",
        "टिकट व्हाट्सएप पर"],
    "free_terms": [
        "free", "free of cost", "free registration", "muft", "nishulk", "निशुल्क", "निःशुल्क", "नि:शुल्क", "मुफ्त",
        "मुफ़्त", "फ्री"],
    "click_terms": [
        "click here", "click on", "click the photo", "click the image", "click the link", "click the button",
        "click below", "click karein", "click karen", "click kare", "click kijiye", "click karo", "photo par click",
        "photo pe click", "tap here", "tap on", "learn more", "see details", "view details", "details dekhein",
        "details dekhe", "vivaran dekhein", "पर क्लिक", "यहाँ क्लिक", "यहां क्लिक", "विवरण देखें", "विवरण देखे",
        "डिटेल्स देखें"],
    # A delivery that failed or waits on you: the redelivery scam's opening (India Post "incomplete address").
    "delivery_problem": [
        "incomplete address", "address incomplete", "address is incomplete", "wrong address", "update your address",
        "update address", "address update", "confirm your address", "could not be delivered", "couldn't be delivered",
        "cannot be delivered", "can't be delivered", "unable to deliver", "delivery failed", "failed delivery",
        "delivery attempt failed", "redelivery", "re-delivery", "re delivery", "redeliver", "re-deliver",
        "reschedule delivery", "held at", "on hold", "pata adhura", "adhura pata", "delivery nahi ho", "dobara delivery",
        "पता अधूरा", "अधूरा पता", "गलत पता", "पता अपडेट", "डिलीवर नहीं", "डिलीवरी नहीं हो", "दोबारा डिलीवरी",
        "फिर से डिलीवरी"],
}

APPEND_LEXICONS = {"otp_terms": ["confirmation code"]}

# Couriers' own sites (a genuine "pay the duty" or COD link to them is not the redelivery scam), and the short-link
# domains that only Amazon, Flipkart, Myntra, Zomato, Paytm and PhonePe can issue (an Amazon shipping SMS with an
# amzn.in link was marked Suspicious).
APPEND_DOMAINS = {"official_domains": ["delhivery.com", "dtdc.in", "dtdc.com", "ecomexpress.in", "xpressbees.com",
                                       "shadowfax.in", "ekartlogistics.com", "amzn.in", "amzn.to", "a.co", "fkrt.it",
                                       "myntr.it", "zoma.to", "p-y.tm", "phon.pe"]}

# "customs" alone made India Post's genuine "customs duty is payable" notice read as a seized parcel; every seizure
# story in the sets also says seized, illegal, drugs or the like (removing it changed no verdict on any set).
REMOVE_LEXICONS = {"seized_terms": ["customs"]}

NEW_SIGNALS = {
    "call_forwarding": {
        "weight": 4.0, "hard": True, "category": "call_forward", "show": True,
        "reason": {"en": "It asks you to dial {code} followed by a number. That code forwards your calls, and your "
                         "bank's OTP calls, to that number.",
                   "hi": "इसमें {code} के बाद एक नंबर डायल करने को कहा गया है। यह कोड आपकी कॉल, बैंक की OTP कॉल भी, "
                         "उस नंबर पर भेज देता है।"}},
    "unseen_advance": {
        "weight": 3.0, "hard": False, "category": "deal_advance", "show": True,
        "reason": {"en": "It asks for an advance, token or deposit (\"{phrase}\") for something you cannot see first. "
                         "Fake flat owners, plot sellers and booking agents work this way.",
                   "hi": "इसमें ऐसी चीज़ के लिए एडवांस, टोकन या जमा राशि (\"{phrase}\") माँगी गई है जिसे आप पहले देख "
                         "नहीं सकते। नकली मकान मालिक, प्लॉट बेचने वाले और बुकिंग एजेंट ऐसे ही ठगते हैं।"}},
    "delivery_fee": {
        "weight": 3.0, "hard": False, "category": "courier", "show": True,
        "reason": {"en": "It asks for a fee for a parcel's delivery or address update through a link. Courier "
                         "companies do not collect fees through an SMS link.",
                   "hi": "इसमें लिंक से पार्सल की डिलीवरी या पता अपडेट के लिए फ़ीस माँगी गई है। कूरियर कंपनियाँ "
                         "SMS के लिंक से फ़ीस नहीं लेतीं।"}},
    "link_hiding": {
        "weight": 2.0, "hard": False, "category": None, "show": True,
        "reason": {"en": "It tells you to join a link written with gaps (\"{phrase}\"). Scammers split links so that "
                         "filters miss them.",
                   "hi": "इसमें टूटे हुए लिंक को जोड़कर खोलने को कहा गया है (\"{phrase}\")। ठग लिंक को तोड़कर लिखते "
                         "हैं ताकि फ़िल्टर उसे पकड़ न सकें।"}},
    "scheme_click": {
        "weight": 1.5, "hard": False, "category": "govt_scheme", "show": True,
        "reason": {"en": "It offers a free government scheme and asks you to click the picture or see the details. "
                         "Forwarded posts like this hide a fake link in the picture.",
                   "hi": "इसमें मुफ़्त सरकारी योजना बताकर फ़ोटो पर क्लिक करने या विवरण देखने को कहा गया है। ऐसे "
                         "फॉरवर्ड पोस्ट फ़ोटो में नकली लिंक छिपाते हैं।"}},
}

NEW_CATEGORIES = {
    "call_forward": {
        "priority": 93,
        "name": {"en": "Call-forwarding code fraud", "hi": "कॉल फ़ॉरवर्डिंग कोड वाली ठगी"},
        "actions": {
            "en": ["Do not dial a code that starts with * or ** and has a number someone gave you. It sends your "
                   "calls, and your bank's OTP calls, to them.",
                   "If you dialled one, dial ##002# now to cancel all call forwarding (or switch forwarding off in "
                   "the phone's call settings), then call your bank.",
                   "Report the number on Chakshu at sancharsaathi.gov.in; if money left your account, call 1930 at once."],
            "hi": ["* या ** से शुरू होने वाला ऐसा कोई कोड डायल न करें जिसमें किसी का दिया नंबर हो। इससे आपकी कॉल, "
                   "बैंक की OTP कॉल भी, उनके पास चली जाती हैं।",
                   "अगर डायल कर दिया है, तो अभी ##002# डायल करें, इससे सारी कॉल फ़ॉरवर्डिंग बंद हो जाती है (या फ़ोन की "
                   "कॉल सेटिंग में फ़ॉरवर्डिंग बंद करें)। फिर अपने बैंक को फ़ोन करें।",
                   "इस नंबर की शिकायत sancharsaathi.gov.in पर चक्षु में करें; अगर खाते से पैसे गए हैं, तो तुरंत 1930 पर "
                   "कॉल करें।"]}},
    "deal_advance": {
        "priority": 69,
        "name": {"en": "Advance for a deal you cannot see", "hi": "बिना देखे सौदे के लिए एडवांस"},
        "actions": {
            "en": ["Do not pay an advance, token or deposit before you have seen the flat or plot yourself and met "
                   "the owner.",
                   "Book pilgrimage helicopters, hotels and tickets only on the official website, not through an "
                   "agent on WhatsApp or Facebook.",
                   "If you paid, call 1930 at once; report the number on Chakshu at sancharsaathi.gov.in."],
            "hi": ["मकान या प्लॉट खुद देखे और मालिक से मिले बिना कोई एडवांस, टोकन या जमा राशि न दें।",
                   "तीर्थ यात्रा का हेलीकॉप्टर, होटल और टिकट सिर्फ़ आधिकारिक वेबसाइट पर बुक करें, WhatsApp या "
                   "Facebook के एजेंट से नहीं।",
                   "अगर पैसे दे दिए हैं, तो तुरंत 1930 पर कॉल करें; नंबर की शिकायत sancharsaathi.gov.in पर चक्षु में करें।"]}},
}


def update(fraud: dict) -> None:
    lex = fraud["lexicons"]
    for name, words in NEW_LEXICONS.items():
        lex[name] = list(words)
    for name, words in APPEND_LEXICONS.items():
        lex[name] += [w for w in words if w not in lex[name]]
    for name, words in REMOVE_LEXICONS.items():
        lex[name] = [w for w in lex[name] if w not in words]
    for name, items in APPEND_DOMAINS.items():
        fraud["domains"][name] += [d for d in items if d not in fraud["domains"][name]]
    fraud["signals"].update(NEW_SIGNALS)
    fraud["categories"].update(NEW_CATEGORIES)
    fraud["version"], fraud["date"] = "1.7.0", "2026-10-07"


def main() -> None:
    path = ROOT / "packs" / "fraud.v1.json"
    fraud = load(path)
    update(fraud)
    save(path, fraud)
    print("fraud 1.7.0 written; signed if this machine has the signer's key (SAHAYAK_SIGNER). Now run: python -m pytest")


if __name__ == "__main__":
    main()
