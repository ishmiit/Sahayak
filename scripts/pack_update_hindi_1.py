"""Hindi wording fixes from the review of 7 Oct 2026: the fraud pack's strings (in fraud pack 1.7.0), schemes pack
1.1.1 and voice pack 1.0.1. Run it after scripts/pack_update_1_7.py, on a machine with a signer's key:

  SAHAYAK_SIGNER=roshan python scripts/pack_update_hindi_1.py
  python -m pytest

An AI-assisted review read every Hindi string on screen and in the packs against its English and listed problems; each
change kept here was checked against the English before it was kept (PROGRESS.md D39). A native speaker's review is
still to come. What it fixes:
- Meaning: "block your card or account" had become "close it" (बंद कराएं); "give into the hospital's own account" had
  become "give from it"; the PM-KISAN payment "once per family" read as "paid only once"; "a government job, now or
  retired" read as "now or ever"; the family question read as "is any of these people in your family?"; the KYC
  reason was garbled; a refund "through a link" read as "asking for a link".
- Words an older rural reader may not know: पंजीकृत, फंडरेज़र, सूचीबद्ध, सेवानिवृत्त, प्रेषक; "domestic work" (घरेलू
  काम) also means one's own housework, so a homemaker could pick the informal-worker answer, in writing or by voice.
- One word for one thing: the Scam label says ठगी like every other string (it said धोखा); the could-not-check card
  says मैसेज like the app (it said संदेश).
Each entry is a JSON path, the text it must have now, and the new text; a path with neither is reported and left
alone, so running the script twice changes nothing. Running an older pack_update script afterwards would bring some old
wording back.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.pack_update_1_5 import save_in_place, save_signature  # noqa: E402
from scripts.packtool import load, save  # noqa: E402

FRAUD = [
    ("signals.link_bank_unofficial.reason.hi",
     "लिंक बैंक का होने का दावा करता है, पर यह आधिकारिक पता ({domain}) नहीं है। बैंक अब .bank.in वाले पते इस्तेमाल करते हैं।",
     "लिंक बैंक का होने का दावा करता है, पर इसका पता ({domain}) आधिकारिक नहीं है। बैंक अब .bank.in वाले पते इस्तेमाल करते हैं।"),
    ("signals.link_suspicious_tld.reason.hi",
     "वेब पता ({domain}) ऐसे अंत वाला है जो ठग अक्सर इस्तेमाल करते हैं।",
     "वेब पते ({domain}) का आखिरी हिस्सा ऐसा है जो ठग अक्सर इस्तेमाल करते हैं।"),
    ("signals.kyc_threat.reason.hi",
     "इसमें कहा गया है कि आपका KYC खत्म हो गया है या खाता बंद हो जाएगा। बैंक KYC के लिए शाखा या अपने आधिकारिक ऐप में बुलाते हैं, लिंक या कॉल से नहीं।",
     "इसमें कहा गया है कि आपका KYC खत्म हो गया है या खाता बंद हो जाएगा। बैंक KYC अपडेट शाखा में या अपने आधिकारिक ऐप से करवाते हैं, लिंक या कॉल से नहीं।"),
    ("signals.new_number.reason.hi",
     "इसमें \"यह मेरा नया नंबर है\" कहा गया है। ठग जान-पहचान वाला बनने के लिए ऐसा करते हैं।",
     "इसमें \"यह मेरा नया नंबर है\" कहा गया है। ठग ऐसा कहकर खुद को आपका कोई जान-पहचान वाला बताते हैं।"),
    ("signals.tax_refund_bait.reason.hi",
     "इसमें लिंक या आपकी जानकारी माँगकर इनकम टैक्स रिफ़ंड देने की बात है।",
     "इसमें लिंक के ज़रिए या आपकी जानकारी माँगकर इनकम टैक्स रिफ़ंड देने की बात है।"),
    ("signals.official_link.reason.hi",
     "इसमें सिर्फ़ आधिकारिक पता ({domain}) है।",
     "इसमें सिर्फ़ आधिकारिक वेबसाइट का लिंक ({domain}) है।"),
    ("signals.dlt_sender.reason.hi",
     "यह एक पंजीकृत व्यावसायिक प्रेषक ({sender}) से आया है।",
     "यह किसी रजिस्टर्ड कंपनी के नाम ({sender}) से आया है।"),
    ("signals.bank_1600_caller.reason.hi",
     "कॉल 1600 वाले नंबर से आई, जो बैंकों और वित्तीय कंपनियों के लिए है।",
     "कॉल 1600 वाले नंबर से आई, जो सिर्फ़ बैंकों और फ़ाइनेंस कंपनियों के लिए है।"),
    ("signals.no_pressure.reason.hi",
     "इसमें कहा गया है कि कोई जल्दी नहीं (\"{phrase}\") और इसमें ठगी का कोई और संकेत नहीं है। ठग लगभग हमेशा जल्दबाज़ी कराते हैं।",
     "इसमें कहा गया है कि कोई जल्दी नहीं है (\"{phrase}\")। इसके अलावा इसमें ठगी का कोई संकेत नहीं है। ठग लगभग हमेशा जल्दबाज़ी कराते हैं।"),
    ("signals.donation_appeal.reason.hi",
     "इसमें किसी निजी UPI ID या फ़ोन नंबर पर दान माँगा गया है। इलाज और राहत की नकली अपीलें ऐसे ही चलती हैं; देने से पहले अस्पताल या किसी जाँचे-परखे फंडरेज़र से पुष्टि करें।",
     "इसमें किसी निजी UPI ID या फ़ोन नंबर पर दान माँगा गया है। इलाज और राहत की नकली अपीलें ऐसे ही चलती हैं; देने से पहले अस्पताल से या किसी जाँची-परखी संस्था से पुष्टि करें।"),
    ("signals.doorstep_code.reason.hi",
     "यह कोड दरवाज़े पर डिलीवरी वाले को, सामान हाथ में मिलने के बाद देना है। डिलीवरी कोड ऐसे ही काम करता है। फ़ोन कॉल पर किसी को कोड न बताएं।",
     "यह कोड दरवाज़े पर डिलीवरी वाले को, सामान हाथ में मिलने के बाद देना है। डिलीवरी कोड ऐसे ही काम करता है। फ़ोन कॉल पर किसी को कभी कोड न बताएं।"),
    ("categories.otp_pin.actions.hi.1",
     "अगर आपने बता दिया है, तो पासबुक में छपे बैंक नंबर पर फ़ोन करके कार्ड या खाता बंद कराएं।",
     "अगर आपने बता दिया है, तो पासबुक में छपे बैंक नंबर पर फ़ोन करके कार्ड या खाता ब्लॉक कराएं।"),
    ("categories.malicious_app.actions.hi.2",
     "पासबुक वाले नंबर पर बैंक को फ़ोन करके खाता बंद कराएं, फिर 1930 पर फ़ोन करें।",
     "पासबुक वाले नंबर पर बैंक को फ़ोन करके खाता ब्लॉक कराएं, फिर 1930 पर फ़ोन करें।"),
    ("categories.sextortion.actions.hi.0",
     "पैसे न दें। पैसे देने से माँगें और बढ़ती हैं।",
     "पैसे न दें। पैसे देने से अक्सर माँगें और बढ़ जाती हैं।"),
    ("categories.job_task.actions.hi.0",
     "असली नौकरी में काम शुरू करने या कमाई 'खोलने' के लिए पैसे नहीं माँगे जाते।",
     "असली नौकरी में काम शुरू करने या अपनी कमाई निकालने के लिए कभी पैसे नहीं माँगे जाते।"),
    ("categories.investment.actions.hi.1",
     "सिर्फ़ SEBI में पंजीकृत ब्रोकर के ज़रिए निवेश करें, जिसकी जाँच आप कर सकें।",
     "सिर्फ़ SEBI में रजिस्टर्ड ब्रोकर के ज़रिए निवेश करें, जिसकी जाँच आप कर सकें।"),
    ("categories.loan_fee.actions.hi.1",
     "लोन सिर्फ़ बैंक या RBI में पंजीकृत संस्था से ही लें।",
     "लोन सिर्फ़ बैंक या RBI में रजिस्टर्ड संस्था से ही लें।"),
    ("categories.impersonation.actions.hi.1",
     "कॉल या कोड से SIM बदलने या चालू करने का काम न करें; अपने ऑपरेटर के स्टोर जाएं।",
     "कॉल या कोड से SIM बदलने या चालू करने का काम न करें; अपनी SIM कंपनी के स्टोर पर जाएं।"),
    ("categories.charity.actions.hi.1",
     "किसी मरीज़ की मदद करनी हो तो अस्पताल के अपने खाते से या किसी ऐसे फंडरेज़िंग पेज से दें जिसकी आप जाँच कर सकें।",
     "किसी मरीज़ की मदद करनी हो तो अस्पताल के अपने खाते में पैसे दें, या किसी ऐसे चंदा जुटाने वाले पेज के ज़रिए दें जिसकी आप जाँच कर सकें।"),
    ("verdicts.scam.label.hi", "धोखा", "ठगी"),
    ("verdicts.unreadable.headline.hi",
     "सहायक अभी {language} नहीं पढ़ सकता, इसलिए यह नहीं बता सकता कि यह संदेश असली है या ठगी।",
     "सहायक अभी {language} नहीं पढ़ सकता, इसलिए यह नहीं बता सकता कि यह मैसेज असली है या ठगी।"),
    ("unreadable.reason.hi",
     "सहायक अभी सिर्फ़ हिंदी और अंग्रेज़ी पढ़ता है, इसलिए इस संदेश में कुछ न मिलने का कोई मतलब नहीं।",
     "सहायक अभी सिर्फ़ हिंदी और अंग्रेज़ी पढ़ता है, इसलिए इस मैसेज में कुछ न मिलने का कोई मतलब नहीं।"),
    ("unreadable.actions.hi.0",
     "इस संदेश के कहने पर किसी को OTP, PIN या कार्ड नंबर न बताएं, और कोई पैसा न भेजें।",
     "इस मैसेज के कहने पर किसी को OTP, PIN या कार्ड नंबर न बताएं, और कोई पैसा न भेजें।"),
    ("unreadable.actions.hi.2",
     "बैंक के संदेश की जाँच के लिए पासबुक या कार्ड पर छपे नंबर पर कॉल करें।",
     "बैंक के मैसेज की जाँच के लिए पासबुक या कार्ड पर छपे नंबर पर कॉल करें।"),
]

_CENTRE = ("केंद्र से ₹{n} हर महीने; राज्य इसमें और जोड़ सकता है", "केंद्र सरकार से ₹{n} हर महीने; आपका राज्य इसमें और जोड़ सकता है")
_UNORGANISED_SAY = ("असंगठित काम (दिहाड़ी, घरेलू, रेहड़ी-पटरी, खेत मज़दूरी…)",
                    "असंगठित काम (दिहाड़ी, दूसरों के घरों में काम, रेहड़ी-पटरी, खेत मज़दूरी…)")
SCHEMES = [
    ("questions.0.help.hi", "पूरे साल में बताएँ। ठीक उम्र नहीं पता, तो नीचे से चुनें।",
     "जितने साल पूरे हो चुके हैं, वही बताएँ। ठीक उम्र नहीं पता, तो नीचे से चुनें।"),
    ("questions.2.options.1.label.hi", "BPL या प्राथमिकता (PHH)", "BPL, प्राथमिकता या पात्र गृहस्थी (PHH)"),
    ("questions.4.options.2.label.hi",
     "दिहाड़ी, निर्माण, घरेलू काम, रेहड़ी-पटरी, घर से काम, छोटी दुकान, ड्राइवर या डिलीवरी",
     "दिहाड़ी, निर्माण, दूसरों के घरों में काम, रेहड़ी-पटरी, घर बैठे कमाई का काम, छोटी दुकान, ड्राइवर या डिलीवरी"),
    ("questions.4.options.5.label.hi", "अभी काम नहीं (गृहिणी, छात्र, सेवानिवृत्त)", "अभी काम नहीं (गृहिणी, छात्र, रिटायर)"),
    ("questions.6.text.hi", "क्या परिवार में (पति, पत्नी या 18 से कम उम्र के बच्चे) कोई इनमें से है?",
     "क्या आपके परिवार (पति, पत्नी या 18 साल से कम उम्र के बच्चे) में किसी पर नीचे दी गई कोई बात लागू होती है?"),
    ("questions.6.help.hi",
     "पिछले साल इनकम टैक्स भरा · सरकारी नौकरी, अभी या पहले (मल्टी-टास्किंग / ग्रुप D को छोड़कर) · ₹10,000 महीना या ज़्यादा की सरकारी पेंशन · डॉक्टर, इंजीनियर, वकील, CA या आर्किटेक्ट की प्रैक्टिस · मंत्री, सांसद, विधायक, मेयर या ज़िला पंचायत अध्यक्ष (अभी या पहले)",
     "पिछले साल इनकम टैक्स भरा · सरकारी नौकरी, अभी या रिटायर (मल्टी-टास्किंग / ग्रुप D को छोड़कर) · ₹10,000 महीना या ज़्यादा की सरकारी पेंशन · डॉक्टर, इंजीनियर, वकील, CA या आर्किटेक्ट की प्रैक्टिस · मंत्री, सांसद, विधायक, मेयर या ज़िला पंचायत अध्यक्ष (अभी या पहले)"),
    ("schemes.0.what.hi", "60 साल या ज़्यादा उम्र के गरीब (BPL) परिवारों के लोगों को हर महीने पेंशन।",
     "गरीब (BPL) परिवारों के 60 साल या ज़्यादा उम्र के लोगों को हर महीने पेंशन।"),
    ("schemes.0.benefit_now.0.hi", _CENTRE[0].format(n=200), _CENTRE[1].format(n=200)),
    ("schemes.0.benefit_now.1.hi", _CENTRE[0].format(n=500), _CENTRE[1].format(n=500)),
    ("schemes.1.what.hi", "40 से 79 साल की गरीब (BPL) परिवारों की विधवा महिलाओं को हर महीने पेंशन।",
     "गरीब (BPL) परिवारों की 40 से 79 साल की विधवा महिलाओं को हर महीने पेंशन।"),
    ("schemes.1.benefit_now.0.hi", _CENTRE[0].format(n=300), _CENTRE[1].format(n=300)),
    ("schemes.2.benefit_now.0.hi", _CENTRE[0].format(n=300), _CENTRE[1].format(n=300)),
    ("schemes.6.where.hi", "जिस बैंक या डाकघर में आपका बचत खाता है", "जिस बैंक शाखा या डाकघर में आपका बचत खाता है, वहीं"),
    ("schemes.6.notes.0.hi", "1 अक्टूबर 2022 से, जिसने कभी इनकम टैक्स भरा है, वह नया खाता नहीं खोल सकता।",
     "1 अक्टूबर 2022 से, जिसने कभी इनकम टैक्स भरा है, वह अटल पेंशन योजना में नया खाता नहीं खोल सकता।"),
    ("schemes.7.rule.all.1.say.hi", "परिवार में कोई रोक वाली श्रेणी नहीं (टैक्स, सरकारी नौकरी, बड़ी पेंशन, पेशेवर, पदाधिकारी)",
     "परिवार में कोई भी रोक वाली श्रेणी में नहीं (टैक्स, सरकारी नौकरी, बड़ी पेंशन, डॉक्टर-वकील जैसा पेशा, मंत्री-विधायक जैसा पद)"),
    ("schemes.7.notes.0.hi", "पैसा परिवार (पति, पत्नी और नाबालिग बच्चे) को एक बार ही मिलता है।",
     "पूरे परिवार (पति, पत्नी और नाबालिग बच्चे) में यह पैसा एक ही व्यक्ति को मिलता है, हर सदस्य को अलग-अलग नहीं।"),
    ("schemes.8.what.hi", "सूचीबद्ध अस्पताल में भर्ती होने पर हर साल ₹5 लाख तक मुफ़्त इलाज। बिना भर्ती के इलाज (OPD) इसमें नहीं।",
     "योजना से जुड़े अस्पताल में भर्ती होने पर हर साल ₹5 लाख तक मुफ़्त इलाज। बिना भर्ती के इलाज (OPD) इसमें नहीं।"),
    ("schemes.8.where.hi", "CSC केंद्र, सूचीबद्ध अस्पताल, आयुष्मान ऐप, या 14555 पर कॉल",
     "CSC केंद्र, योजना से जुड़ा अस्पताल, आयुष्मान ऐप, या 14555 पर कॉल"),
    ("schemes.9.rule.all.1.say.hi", *_UNORGANISED_SAY),
    ("schemes.10.rule.all.1.say.hi", *_UNORGANISED_SAY),
]

# Spoken answers to "What is your main work?": "घरेलू" also means one's own housework, so it no longer picks the
# informal-worker answer (an unclear answer is asked again); a domestic worker's own words do.
VOICE_WORK_UNORGANISED = {"remove": ["घरेलू"], "add": ["घरों में", "दूसरों के घर", "कामवाली", "बर्तन"]}


def _walk(data: dict, path: str) -> tuple:
    keys = [int(k) if k.isdigit() else k for k in path.split(".")]
    node = data
    for k in keys[:-1]:
        node = node[k]
    return node, keys[-1]


def apply(data: dict, fixes: list[tuple[str, str, str]], name: str) -> int:
    changed = 0
    for path, old, new in fixes:
        node, key = _walk(data, path)
        if node[key] == new:
            continue
        if node[key] != old:
            print(f"  {name}: {path} has unexpected text, left alone: {node[key]!r}")
            continue
        node[key] = new
        changed += 1
    return changed


def main() -> None:
    fraud_path = ROOT / "packs" / "fraud.v1.json"
    fraud = load(fraud_path)
    n = apply(fraud, FRAUD, "fraud")
    if n:
        save(fraud_path, fraud)
    print(f"fraud {fraud['version']}: {n} strings changed")

    schemes_path = ROOT / "packs" / "schemes.v1.json"  # laid out by hand: only the changed strings are swapped
    before = load(schemes_path)
    schemes = load(schemes_path)
    n = apply(schemes, SCHEMES, "schemes")
    if n:
        schemes["version"], schemes["date"] = "1.1.1", "2026-10-07"
        save_in_place(schemes_path, before, schemes)
    print(f"schemes {schemes['version']}: {n} strings changed")

    voice_path = ROOT / "packs" / "voice.v1.json"  # laid out by hand too: edit the one list in place
    voice = load(voice_path)
    words = voice["answers"]["work"]["unorganised"]["hi"]
    new_words = [w for w in words if w not in VOICE_WORK_UNORGANISED["remove"]]
    new_words += [w for w in VOICE_WORK_UNORGANISED["add"] if w not in new_words]
    if new_words != words:
        text = voice_path.read_text(encoding="utf-8")
        old_list, new_list = json.dumps(words, ensure_ascii=False), json.dumps(new_words, ensure_ascii=False)
        voice["answers"]["work"]["unorganised"]["hi"] = new_words
        voice["version"], voice["date"] = "1.0.1", "2026-10-07"
        text = text.replace(old_list, new_list, 1)
        text = text.replace('"version": "1.0.0"', '"version": "1.0.1"', 1).replace('"date": "2026-10-02"', '"date": "2026-10-07"', 1)
        if json.loads(text) == voice:
            voice_path.write_text(text, encoding="utf-8")
            save_signature(voice_path)
        else:
            save(voice_path, voice)
    print(f"voice {voice['version']}: work keywords {'updated' if new_words != words else 'already updated'}")
    print("Signed if this machine has the signer's key (SAHAYAK_SIGNER). Now run: python -m pytest")


if __name__ == "__main__":
    main()
