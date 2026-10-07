"""Record what the node's Python Fraud-Shield answers, so tests/js/parity_fraud.mjs can require the phone
checker (web/checker.js) to answer the same, field by field.

The corpus holds, for each case, the inputs (text, sender, input_type) and the Python card from
check_message_full() (without the random id and the timing), plus the unrounded model scores and fold()
of the text for diagnosis. Cases:

  - every line of bench/scambench/scambench_v0.jsonl, bench/redteam/redteam_v0.jsonl (with its sender) and
    bench/callbench/calls_v0.jsonl (input_type "call");
  - every line of the blind red-team set bench/redteam/redteam_v1_blind.jsonl (a QR item through analyse(), as
    /api/qr does) and the dev half of PublicBench (bench/public/; the test half stays out of every tool but its
    scorer, see bench/eval_public_v0.py);
  - every message string in tests/test_signals.py, test_signals_1_6.py, test_signals_1_7.py, test_redteam.py,
    test_inputs.py and test_api.py (read with `ast`, so new test messages join automatically);
  - every example and QR example in packs/demo.v1.json (a QR goes through analyse(), then its check_text
    through the check with input_type "qr", as /api/qr does);
  - hand-written adversarial messages (Devanagari and other digits, homoglyphs, zero-width characters,
    emoji, Hinglish, defanged and odd links, leetspeak, amounts, phone-number series, sender headers,
    negations, very long and empty-ish text, CR/LF/tabs, characters newer than Unicode 14), run with
    several senders and input types;
  - seeded fuzz variants of the bench messages (the same disguises mixed at random);
  - QR payloads for analyse() and amounts for rupees().

  python tests/js/make_fraud_corpus.py [--out tests/js/fraud_corpus.json]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SAHAYAK_LLM", "none")

from sahayak.fraud.classifier import get_classifier  # noqa: E402
from sahayak.fraud.normalize import fold  # noqa: E402
from sahayak.fraud.patterns import get_matcher  # noqa: E402
from sahayak.fraud.pipeline import check_message_full  # noqa: E402
from sahayak.inputs.qr import analyse, rupees  # noqa: E402
from sahayak.packs import get_pack  # noqa: E402

TEST_FILES = ("test_signals.py", "test_signals_1_6.py", "test_signals_1_7.py", "test_redteam.py", "test_inputs.py",
              "test_api.py")


def jsonable(x):
    """JSON cannot carry inf or nan (Python's json writes Infinity, which JavaScript cannot parse)."""
    if isinstance(x, float) and not math.isfinite(x):
        return {"__float__": "nan" if math.isnan(x) else ("inf" if x > 0 else "-inf")}
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dev_half(item_id: str) -> bool:
    """bench/eval_public_v0.py half(): only PublicBench's dev half may be used outside its scorer."""
    return int(hashlib.sha256(item_id.encode()).hexdigest()[:8], 16) % 2 == 0


# ---------------------------------------------------------------- messages used in the tests

def from_tests() -> tuple[list[tuple], list[str], list[float]]:
    """(text, sender, input_type) triples, QR payloads and rupees() amounts found in the test files."""
    cases, payloads, amounts = [], [], []
    for name in TEST_FILES:
        tree = ast.parse((ROOT / "tests" / name).read_text(encoding="utf-8"))
        docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                      and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if fn == "parametrize" and len(node.args) >= 2:
                    names = [n.strip() for n in ast.literal_eval(node.args[0]).split(",")]
                    try:
                        rows = ast.literal_eval(node.args[1])
                    except ValueError:
                        continue
                    for row in rows:
                        d = dict(zip(names, row if isinstance(row, tuple) else (row,)))
                        if isinstance(d.get("text"), str):
                            cases.append((d["text"], d.get("sender"), d.get("itype", "text")))
                        for key in ("read", "fixed", "folded"):
                            if isinstance(d.get(key), str):
                                cases.append((d[key], None, "text"))
                        if isinstance(d.get("n"), (int, float)):
                            amounts.append(float(d["n"]))
                elif fn in ("check_message", "check_message_full") and node.args and isinstance(node.args[0], ast.Constant):
                    kw = {k.arg: k.value.value for k in node.keywords if isinstance(k.value, ast.Constant)}
                    cases.append((node.args[0].value, kw.get("sender"), kw.get("input_type", "text")))
                elif fn in ("analyse", "parse_upi", "qr_png") and node.args and isinstance(node.args[0], ast.Constant):
                    payloads.append(node.args[0].value)
            elif isinstance(node, ast.Dict):
                d = {k.value: v.value for k, v in zip(node.keys, node.values)
                     if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)}
                if isinstance(d.get("text"), str):
                    cases.append((d["text"], d.get("sender"), d.get("input_type", "text")))
            elif (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
                  and len(node.value) >= 12 and " " in node.value):
                cases.append((node.value, None, "text"))  # any other sentence in a test is a message too
    return cases, payloads, amounts


# ---------------------------------------------------------------- adversarial messages

LONG_GENUINE = ("Dear customer, your electricity bill for September is Rs 845 and is due on 15 Oct. "
                "Pay on the official app or at any BESCOM office. Thank you for being a valued customer. ")
LONG_SCAM = ("Dear customer, your SBI account KYC has expired and your account will be blocked today. "
             "Update immediately at http://sbi-kyc-update.xyz/login and share the OTP you receive. ")

ADVERSARIAL: list[tuple[str, str | None, str]] = [
    # Devanagari and other decimal digits
    ("आपका OTP ४८२९१० है। इसे किसी के साथ साझा न करें। - SBI", "AX-SBIBNK-T", "text"),
    ("प्रिय ग्राहक, ₹५,००० का इनाम जीतने के लिए ९८७६५४३२१० पर कॉल करें", None, "text"),
    ("Call ९८७६५ ४३२१० now to claim your lottery prize of रु ५ लाख", None, "text"),
    ("आपका बिजली कनेक्शन आज रात ९:३० बजे काट दिया जाएगा। तुरंत ९८१२३४५६७८ पर संपर्क करें", None, "text"),
    ("Your OTP is ৪৮২৯১০. Do not share it with anyone. -HDFC Bank", "VM-HDFCBK-T", "text"),
    ("Pay ₹١٢٣٤ now as processing fee to release your loan of ₹٥٠٠٠٠", None, "text"),
    ("Pay ₹१,२३,४५६.७८ now to release your refund. Call +९१ ९८७६५४३२१०", None, "text"),
    ("Earn ₹੩੦੦੦ per day from home, join our telegram group", None, "text"),
    # Cyrillic / Greek look-alikes, case folding
    ("Dеar customer, your SВI account is blocked. Call 9876543210 now.", None, "text"),
    ("Yоur ΗDFC аccount KYC hаs expirеd, updаte at http://hdfc-kyc.top", None, "text"),
    ("Ρaytm cashback ₹500: scan QR and enter PIN to receive", None, "text"),
    ("ІСІСІ Bank: share OTP to unblock your card", None, "text"),
    ("ΣΟΦΙΑΣ ΚΥΣ update now ς σ Σ, share otp", None, "text"),
    ("Straße ẞ STRASSE: send OTP to verify your account at strasse-kyc.top", None, "text"),
    ("ᏚᎢᎵᎬᎢᎬᏒ ꮎꮄ OTP share karo turant", None, "text"),
    ("İNR 5000 credited. Your ıncome tax refund is pending, visit ıncometax-refund.xyz and İNFO.top", None, "text"),
    ("SBİ KYC update: click http://sbı-kyc.xyz/İndex now", "AX-SBİBNK", "text"),
    ("Click http://ſbi-kyc.xyz for KYC, pay rs 500 to Kelvin K desk", None, "text"),
    ("ＳＢＩ ＫＹＣ ｅｘｐｉｒｅｄ ｕｐｄａｔｅ ａｔ ｈｔｔｐ://ｓｂｉ－ｋｙｃ．ｘｙｚ ｓｈａｒｅ ＯＴＰ", None, "text"),
    ("𝐒𝐁𝐈 account blocked, share 𝐎𝐓𝐏 now at 𝐬𝐛𝐢-𝐤𝐲𝐜.𝐱𝐲𝐳", None, "text"),
    ("ΟΔΥΣΣΕΑΣ ΣΟΦΟΣ: ﬁle ﬂow ﬀ Ǆ ǅ ǆ ŉ ǰ ΐ ᾳ ﬆ", None, "text"),
    # zero-width and invisible characters
    ("Share the O​T​P sent to your phone to unblock", None, "text"),
    ("K‌Y‍C exp­ired. upd⁠ate now: http://sbi​-kyc.top", None, "text"),
    ("﻿Dear customer﻿ your account will be blocked﻿, share OTP", None, "text"),
    ("O͏T͏P batao᠎ jaldi ⁡⁢⁣", None, "text"),
    # emoji (astral characters shift UTF-16 offsets)
    ("🎉🎉 Congratulations!! You have won ₹25,00,000 in KBC lottery 🎁 Call 9876543210 on WhatsApp 📞", None, "text"),
    ("😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀 please 😀 share 😀 the 😀 OTP 😀 now 😀😀", None, "text"),
    ("👨‍👩‍👧 Papa, I am in hospital 🏥 after accident, send money urgently to 9812345678 🙏", None, "text"),
    ("🇮🇳 Govt scheme: PM Kisan ₹6000 👉🏽 download pmkisan-new.apk 👈🏿", None, "text"),
    ("🫨🫎 Your parcel 📦 is seized by customs 🪿 pay customs fee now to release it 🛃", None, "text"),
    ("Never 🙅 share your OTP 🔐 with anyone. 482910 is your OTP 🔑 -SBI", "AX-SBIBNK-T", "text"),
    # Hinglish and mixed Hindi/English
    ("Aapka account block ho jayega, abhi KYC update karo: http://kyc-update.online", None, "text"),
    ("Beta, mera phone kho gaya, ye mera naya number hai. Jaldi 5000 bhej do, emergency hai", None, "text"),
    ("मैं बैंक से बोल रहा हूँ, आपका card block हो जाएगा, OTP बताइए", None, "call"),
    ("Sir aapka bijli bill pending hai, aaj raat 9.30 baje connection kat jayega. Turant 9876543210 pe call karein", None, "text"),
    ("Ghar baithe kamao ₹3000 roz, sirf YouTube videos like karo. Telegram group join karo", None, "text"),
    ("Pehle 499 rupaye registration fee bharo, phir job confirm hogi", None, "text"),
    ("UPI PIN daalo tab paise mil jayenge, cashback ₹2000", None, "text"),
    ("पैसे पाने के लिए अपना पिन डालें और QR स्कैन करें", None, "text"),
    ("Bhai galti se 2000 bhej diye, request accept kar do please, wapas chahiye", None, "text"),
    # links: IPs, ports, paths, punycode, defanging, case, trailing punctuation
    ("Login at http://192.168.1.10:8080/sbi/login.php to avoid block", None, "text"),
    ("Visit 103.21.244.0/kyc now or 10.0.0.1:443/x", None, "text"),
    ("Click https://xn--sbi-kyc-9za.com/verify for verification", None, "text"),
    ("go to www.sbi.co.in.kyc-verify.top/update?id=1&x=2#frag", None, "text"),
    ("Pay only at https://onlinesbi.sbi/ or https://www.hdfcbank.com/ or portal.bsnl.in", None, "text"),
    ("Download from bit.ly/3xYzAbC and install the APK file", None, "text"),
    ("Track parcel: https://indiapost-track.in:8443/track?id=123 (customs fee pending)", None, "text"),
    ("hxxps://refund-incometax[.]xyz/claim and paytm-cashback (dot) top and sbi dot xyz", None, "text"),
    ("Your link: HTTP://SBI-KYC.XYZ/LOGIN. WWW.PAYTM-REWARD.CLUB!", None, "text"),
    ("Contact us on wa.me/919876543210 for KYC, or https://api.whatsapp.com/send?phone=919812345678", None, "text"),
    ("Join https://t.me/stocktips_vip and chat.whatsapp.com/AbCdEf for 300% returns", None, "text"),
    ("Login: http://[2001:db8::1]/kyc and (see http://sbi-kyc.top/login).", None, "text"),
    ("email me at ramesh.kumar@gmail.com or pay ramesh@okaxis, RAMESH@YBL, 9876543210@paytm", None, "text"),
    ("sbi-rewards.apk.top/download and app.apk", None, "text"),
    # leetspeak
    ("Y0ur acc0unt has b33n bl0cked. Upd4te KYC n0w", None, "text"),
    ("Sh4re the 0TP to v3rify, c0de 0000, covid19 mp3 4g 5g", None, "text"),
    # amounts
    ("You have won Rs.5,00,000 lottery. Pay Rs 999 processing fee", None, "text"),
    ("Loan of ₹2 lakh approved, pay 1.5 lac? ₹ 2.5 crore, INR 10,000.50, rupees 500, रु. 5000, रुपये 2000 भेजो", None, "text"),
    ("₹10 करोड़ का इनाम! रुपए 99 का शुल्क भेजें", None, "text"),
    ("Rs.0.5 cashback, Rs 1,00,00,000.99 cr, INR1lakh, rs10cr", None, "text"),
    ("Pay rs " + "9" * 400 + " now to receive your prize", None, "text"),
    # phone numbers: toll-free, 1600 series, odd senders
    ("This is SBI fraud prevention team, did you make a txn of Rs 5000?", "1600123456", "call"),
    ("Call 1800-11-2211 or 1800 425 3800 or 18602677777 for help", None, "text"),
    ("Your HDFC account is blocked, call us", "+91 98765 43210", "text"),
    ("Your HDFC account is blocked, call us", "160012345678", "call"),
    ("Your HDFC account is blocked, call us", "(0)98765-43210", "text"),
    ("Your HDFC account is blocked, call us", "  ", "text"),
    # DLT sender headers
    ("Rs 1,200.00 debited from A/c XX7781 on 01-10-26. Not you? Call 18001234", "VM-SBIBNK-S", "text"),
    ("Your OTP is 4821 for login", "ab-xyz12-g", "text"),
    ("Your OTP is 4821 for login", "  AD-NPCIUP-G  ", "text"),
    ("Your OTP is 4821 for login", "VM-SBIBNK-X", "text"),
    ("Your OTP is 4821 for login", "VM-SBIBNK\n", "text"),
    # negations, English and Hindi
    ("Never share your OTP with anyone. SBI will never ask for it.", None, "text"),
    ("Do not click on links asking you to update KYC. Report fraud on 1930.", None, "text"),
    ("किसी के साथ OTP साझा न करें। बैंक कभी OTP नहीं माँगता।", None, "text"),
    ("OTP kisi ko mat batana, bank kabhi nahi poochta", None, "text"),
    ("Don't send money to unknown numbers claiming to be police. Digital arrest is a scam.", None, "text"),
    ("I did not receive any OTP, please don't call me again on 9876543210", None, "text"),
    ("नहीं, मैंने कोई पैसे नहीं मांगे, ना ही कोई लिंक भेजा", None, "text"),
    # long texts (the node accepts up to 4,000 characters)
    ((LONG_GENUINE * 40)[:4000], "VM-BESCOM-S", "text"),
    ((LONG_GENUINE * 39)[:3800] + " " + LONG_SCAM[:190], None, "text"),
    (("🙂 " + LONG_SCAM) * 18, None, "text"),
    # empty-ish
    ("", None, "text"), (" ", None, "text"), ("\n\n\t", None, "text"), (".", None, "text"),
    ("🙂", None, "text"), ("​", None, "text"), ("a", None, "voice"), ("OTP", None, "ocr"),
    # tabs, newlines, CRLF and Python-only whitespace
    ("Dear customer,\r\nyour account will be blocked.\r\nShare OTP\tnow.", None, "ocr"),
    ("OTP\n482910\nDo not share\n- SBI", "AX-SBIBNK-T", "ocr"),
    ("Line1\x1cLine2\x1d share otp \x85 now\x1e\x1f", None, "text"),
    ("Pay Rs 500 fee　now to release", None, "text"),
    ("share\vthe\fotp\r\n", None, "text"),
    # Python's "$" also matches before a final newline: "call...\n" right before a number is not a code
    ("Do not share your OTP with anyone. If this was not you, call...\n45678", "AX-SBIBNK-T", "text"),
    # other scam shapes
    ("Approve the collect request to receive your refund of Rs 5000", None, "text"),
    ("Your nude video will be viral, send 10000 to my UPI ramesh@ybl", None, "text"),
    ("Install AnyDesk and share the code with our executive", None, "call"),
    ("Do not install AnyDesk or TeamViewer on anyone's advice", None, "text"),
    ("Congratulations! You have earned 250 reward points on your card", "AX-HDFCBK-P", "text"),
    ("E-challan of Rs 500 pending, pay at echallan-pay.xyz today", None, "text"),
    ("Income tax refund of Rs 15,490 approved. Submit bank account number at it-refund.top", None, "text"),
    ("तुम्हारी वीडियो वायरल कर दूंगा, 10000 भेजो UPI पर", None, "text"),
    ("Your SIM will be blocked, upgrade to eSIM: reply with the code you received", None, "text"),
    ("फ़्री लैपटॉप योजना, अभी डाउनलोड करें और पाएँ ₹5000", None, "text"),  # precomposed फ़
    ("फ़्री लैपटॉप योजना, अभी डाउनलोड करें और पाएं ₹5000", None, "text"),  # decomposed nukta
    ("Dear user share your aadhaar number and the PIN, we will verify your account details " + "x " * 40 + " OTP", None, "text"),
    ("Hi, this is your delivery partner. Share OTP 4417 with the driver to start the ride", None, "call"),
    # rare card paths: reasons from hidden signals only; two categories tied on (total, priority)
    ("Your KYC is pending. Complete the task.", None, "text"),
    ("Stock tips and part time job and commission", None, "text"),
    # characters newer than Unicode 14 (unknown to the node's Python 3.11)
    ("Pay rs 𜳱𜳲𜳳 to 𜳖𜳗𜳘 bank, OTP 𑽑𑽒𑽓𑽔 share karo", None, "text"),
    ("Visit http://sbi-ꟋYC.xyz/𑼄 and enter OTP 𐵁𐵂𐵃𐵄", None, "text"),
    ("\U00100000 share OTP \U0001CCD6 now \U00100001", "VM-\U0001CCD6BNK-S", "text"),
    # code points unassigned in every Unicode version still sit inside Python's [Ͱ-Ͽ] range
    ("SB\u0382I account blocked, call 9876543210 \u0378x\u0379", None, "text"),
    # scripts Sahayak cannot read: "could not check", unless signs it can read are there anyway
    ("আপনার ব্যাংক অ্যাকাউন্ট আজ বন্ধ হয়ে যাবে। KYC আপডেট করতে এই নম্বরে কল করুন 9876543210 এবং OTP বলুন।", None, "text"),
    ("உங்கள் வங்கி கணக்கு முடக்கப்படும். உங்களுக்கு வந்த OTP எண்ணை எங்களிடம் சொல்லுங்கள்.", None, "text"),
    ("ನಿಮ್ಮ ಬ್ಯಾಂಕ್ ಖಾತೆ ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ. ನಿಮಗೆ ಬಂದ OTP ಹೇಳಿ.", "9876543210", "text"),
    ("మీ ఖాతా బ్లాక్ అవుతుంది, వెంటనే ఈ లింక్ క్లిక్ చేయండి http://sbi-kyc.xyz", None, "text"),
    ("तुमचे वीज बिल भरले नाही. आज रात्री वीज कापली जाईल. 9876543210 वर कॉल करा.", None, "text"),
    ("प्रिय ग्राहक, तुमचे खाते आज बंद होईल. OTP सांगा आणि लवकर KYC करा.", "VM-SBIBNK-S", "text"),
    ("आपका खाता बंद नहीं होगा, आप चिंता न करें। नाही आणि", None, "text"),
    ("मुझे नाही पता, आहे या नहीं है, यह आपका काम है", None, "text"),
    ("ਤੁਹਾਡਾ ਖਾਤਾ ਬੰਦ ਹੋ ਜਾਵੇਗਾ। OTP ਦੱਸੋ।", None, "call"),
    ("તમારું ખાતું બંધ થશે. OTP આપો.", None, "text"),
    ("ଆପଣଙ୍କ ଖାତା ବନ୍ଦ ହେବ।", None, "text"),
    ("നിങ്ങളുടെ അക്കൗണ്ട് ബ്ലോക്ക് ചെയ്യും. OTP പറയൂ.", None, "voice"),
    ("آپ کا بینک اکاؤنٹ آج بند ہو جائے گا۔ فوراً اس نمبر پر کال کریں 9876543210", None, "text"),
    ("ᱟᱢᱟᱜ ᱠᱷᱟᱛᱟ ᱵᱚᱸᱫ ᱦᱩᱭᱩᱜ-ᱟ", None, "text"),
    ("ꯅꯍꯥꯛꯀꯤ ꯑꯦꯀꯥꯎꯟꯠ ꯕ꯭ꯂꯣꯛ ꯇꯧꯔꯒꯅꯤ", None, "text"),
    ("Your OTP for login is 482910. Do not share it with anyone. -SBI உங்கள் OTP 482910. யாருடனும் பகிர வேண்டாம்.", "AX-SBIBNK-S", "text"),
    ("Your OTP is 482910 for login. Do not share it with anyone. வணக்கம்", None, "text"),
    ("வங்கி வங்கி বাংক বাংক ਬੈਂਕ ਬੈਂਕ OTP share", None, "text"),
    # the money a message asks for, not the prize, loan or "case" it names
    ("Congratulations! You have won Rs 25,00,000 in KBC lucky draw. Pay processing fee of Rs 4,999 to claim your prize. Call 9876543210.", None, "text"),
    ("This is CBI officer. A parcel in your name has drugs. Rs 2,00,00,000 money laundering case is filed. Stay on video call, do not tell family. Transfer Rs 50,000 for verification.", None, "call"),
    ("आपने ₹25,00,000 की लॉटरी जीती है। ₹4,999 प्रोसेसिंग फ़ीस जमा करें। कॉल करें 9876543210", None, "text"),
    ("Pay ₹500 to get a loan of ₹5 lakh today, limit Rs 2 lakh. Call 9876543210", None, "text"),
    ("Part time job: earn Rs 3000 per day. Registration fee Rs 499 only. WhatsApp 9876543210", None, "text"),
    ("Your account will be debited Rs 10,000 today unless you update KYC at http://sbi-kyc.top", None, "text"),
    ("Pay Rs 10 to activate cashback of Rs 5000: http://cash-back.xyz", None, "text"),
    # numbers and links banks publish themselves
    ("Give a missed call to 9223766666 to know your account balance. Save this number. -SBI", None, "text"),
    ("SBI Quick: missed call 09223866666 for mini statement, call 9223766666 for balance", None, "text"),
    ("Pre-approved Personal Loan up to Rs 5,00,000 for you at attractive rates. Apply in 2 mins: https://hdfcbk.io/a/Pl8xQ T&C -HDFC Bank", None, "text"),
    ("SBI customer care 9223766666, or call our officer on 9876543210 to unblock", None, "text"),
]

# a few base messages run with every input type and several senders
SENDERS = (None, "9812345678", "AX-HDFCBK-T", "1600123456", "+91-98123-45678", "HDFC Bank")
INPUT_TYPES = ("text", "voice", "ocr", "qr", "call", "fax")
VARIED = [
    "Sir main SBI bank se bol raha hu, aapka card block ho jayega. OTP batao turant.",
    "Your electricity will be disconnected tonight. Call officer 9876543210 immediately.",
    "482910 is your OTP for txn of Rs 2,500.00. Do not share OTP with anyone. -HDFC Bank",
    "Dear customer your HDFC account KYC has expired, update now: hdfc-kyc.top",
]

# ---------------------------------------------------------------- fuzz: the same disguises, mixed at random

NOISE = ["​", "‌", "‍", "­", "﻿", "🙂", "🎉", "👍🏽", "📞", " ", "\t", "\r\n", "\n", "  ",
         "।", "!!", "...", " ", "\x1c", "\U0001CCD6", "\U00011F50"]
SWAPS = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "i": "і", "s": "ѕ", "k": "к", "B": "В", "H": "Н",
         "O": "0", "I": "1", "E": "3", "A": "4", "S": "5"}
DIGITS = {str(d): chr(0x966 + d) for d in range(10)}


def fuzz(texts: list[str], n: int, seed: int = 20261006) -> list[str]:
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        t = list(rnd.choice(texts))
        for _ in range(rnd.randint(1, 6)):
            op = rnd.random()
            i = rnd.randrange(len(t) + 1)
            if op < 0.35:
                t.insert(i, rnd.choice(NOISE))
            elif op < 0.55 and t:
                j = min(i, len(t) - 1)
                t[j] = SWAPS.get(t[j], t[j])
            elif op < 0.7 and t:
                j = min(i, len(t) - 1)
                t[j] = DIGITS.get(t[j], t[j])
            elif op < 0.8:
                t = list("".join(t).upper() if rnd.random() < 0.5 else "".join(t).lower())
            elif op < 0.9:
                t.insert(i, rnd.choice([" http://sbi-kyc.xyz/a ", " 9876543210 ", " ₹5,000 ", " OTP ", " नहीं ", " never ",
                                        " wa.me/919812345678 ", " rs 1.5 lakh ", " ramesh@ybl ", " hxxp://x[.]top "]))
            else:
                t = t + list(" " + rnd.choice(texts))
        out.append("".join(t)[:4000])
    return out


# ---------------------------------------------------------------- QR payloads and amounts

QR_PAYLOADS = [
    "upi://pay?pa=shop@okaxis&pn=Shyam%20Kirana&am=250.50&cu=INR&tn=Atta&mc=5411",
    "UPI://PAY?PA=x@y&PN=SBI%20Bank&AM=1e5",
    "upi://pay?pa=a@b&pn=Police&am=nan",
    "upi://pay?pa=a@b&am=inf",
    "upi://pay?pa=a@b&am=-5.5",
    "upi://pay?pa=a@b&am=0.125",
    "upi://pay?pa=a@b&am=99.995",
    "upi://pay?pa=a@b&am=0.005",
    "upi://pay?pa=a@b&am=1e21",
    "upi://pay?pa=a@b&am=-123456.789",
    "upi://pay?pa=a@b&am=1_000",
    "upi://pay?pa=a@b&am=%E0%A5%A7%E0%A5%A8",
    "upi://pay?pa=a@b&am=%2B1.5E%2B3",
    "upi://pay?pa=a@b&am=%20%2012%20",
    "upi://pay?pa=a@b&am=12abc",
    "upi://pay?pa=a@b&am=",
    "upi://pay?pa=a@b&am=1__0",
    "upi://pay?pa=a@b&pn=%E0%A4",
    "upi://pay?pa=a@b&pn=%C0%AF%ED%A0%80%F0%9F%98",
    "upi://pay?pa=a@b&pn=Rs%25202&tn=%25%25%2",
    "upi://pay?pa=a@b&pn=A+B%2BC",
    "upi://pay?pa=a@b&pa=c@d",
    "upi://pay?PA=x@y&pa=z@w",
    "upi://pay?pa=a@b&pn=Lottery%20Winner&am=12000000.456",
    "upi://pay?pa=a@b&pn=SBI&mc=1234",
    "upi://pay?pa=a@b&pn=Income%20Tax%20Dept&am=15000",
    "upi://pay?pa=a@b&pn=SB%C4%B0%20Bank",
    "upi://pay?pa=a@b&pn=PM-Kisan&tn=Get%20cashback",
    "upi://pay?pa=a@b&pn=pmkisan&tn=%E0%A4%87%E0%A4%A8%E0%A4%BE%E0%A4%AE",
    "upi://[pay]?pa=a@b",
    "upi://[::1]?pa=a@b&pn=x",
    "upi://[1.2.3.4]?pa=a@b",
    "upi://[v1.x]?pa=a@b",
    "upi://pa[y?pa=a@b",
    "upi://pay℀?pa=a@b",
    "upi://pay#frag?pa=a@b",
    "upi:pay?pa=a@b",
    " upi://pay?pa=a@b",
    "upi://pay?tn=%F0%9F%8E%81%20Gift%20for%20you",
    "upi://pay?pa=a@b&pn=Won%20Prize",
    "upi://pay?pa=a@b&pn=Credited",
    "upi://pay?pa=a@b&pn=creditedx&tn=wonder",
    "upi://pay?pa=a@b&pn=customer%20care&am=0",
    "upi://pay?pa=a@b&pn=%F0%9D%90%92%F0%9D%90%81%F0%9D%90%88",
    "upi://pay?pa=a@b&pn=%F0%9C%B3%96%20bank",
    "upi://pay?pa=a@b&pn=\U0001CCD6%20\U00011F50&am=\U00011F51",
    "upi://pay\t?pa=a\r@b\n&pn=X",
    "upi://pay?&&pa=a@b&&=x&pn&tn=",
    "http://sbi-kyc-update.xyz/login",
    "www.example.com",
    "HTTPS://X.COM",
    "ſtrange text",
    "Just some text 🙂",
    "x" * 5000,
    ("🙂" * 499) + "abc" + ("😀" * 4000),
]

RUPEES = [0.0, 1.0, 99.5, 0.12, 0.125, 0.005, 999.999, 1000.0, 4999.0, 99999.99, 100000.0, 123456.789, 12345678.0,
          1e15, 1e21, 1.5e22, -5.5, -100000.5, -0.01, 250.5, 2.675, 0.015, 1234567.895,
          9.15069198658886e19, 1.0311237183699867e17, -2.4934856311223464e19, 9007199254740993.0, 2.0 ** 60]


# ---------------------------------------------------------------- build

def record(text: str, sender, input_type) -> dict:
    card, fired = check_message_full(text, sender=sender, input_type=input_type)
    card = {k: v for k, v in card.items() if k not in ("id", "timing_ms")}
    raw = {}
    matcher, clf = get_matcher(), get_classifier()
    if matcher:
        raw["pattern_similarity"] = matcher.best(fold(text)).score
    if clf:
        raw["classifier_p"] = clf.probability(fold(text), {f.id for f in fired if f.id != "classifier_flag"})
    return {"kind": "check", "text": text, "sender": sender, "input_type": input_type, "card": card,
            "raw": raw, "norm": fold(text)}


def build() -> dict:
    triples: list[tuple[str, tuple]] = []
    for r in read_jsonl(ROOT / "bench" / "scambench" / "scambench_v0.jsonl"):
        triples.append(("scambench", (r["text"], r.get("sender"), r.get("input_type", "text"))))
    for r in read_jsonl(ROOT / "bench" / "redteam" / "redteam_v0.jsonl"):
        triples.append(("redteam", (r["text"], r.get("sender"), "text")))
    for r in read_jsonl(ROOT / "bench" / "callbench" / "calls_v0.jsonl"):
        triples.append(("callbench", (r["text"], None, "call")))
    blind_qr = []
    for r in read_jsonl(ROOT / "bench" / "redteam" / "redteam_v1_blind.jsonl"):
        if r.get("input_type") == "qr":
            blind_qr.append(r["text"])
        else:
            triples.append(("redteam_v1", (r["text"], r.get("sender"), r.get("input_type", "text"))))
    public = ROOT / "bench" / "public" / "public_messages_v0.jsonl"
    if public.exists():
        for r in read_jsonl(public):
            if dev_half(r["id"]):
                triples.append(("public_dev", (r["text"], r.get("sender"), r.get("input_type", "text"))))
    test_cases, test_payloads, test_amounts = from_tests()
    triples += [("tests", c) for c in test_cases]
    demo = get_pack("demo").data
    for ex in demo.get("examples", []):
        triples.append(("demo", (ex["text"], ex.get("sender"), ex.get("input_type", "text"))))
    triples += [("adversarial", c) for c in ADVERSARIAL]
    for text in VARIED:
        for sender in SENDERS:
            for itype in INPUT_TYPES:
                triples.append(("varied", (text, sender, itype)))
    bench_texts = [t for src, (t, _, _) in triples if src in ("scambench", "redteam", "callbench")]
    triples += [("fuzz", (t, None, "text")) for t in fuzz(bench_texts, 600)]

    qr_payloads = [ex["payload"] for ex in demo.get("qr_examples", [])] + test_payloads + QR_PAYLOADS + blind_qr
    cases, seen = [], set()
    for payload in dict.fromkeys(qr_payloads):
        try:
            info = analyse(payload)
        except Exception as e:  # noqa: BLE001  (the node raises too; the phone must as well)
            cases.append({"kind": "qr", "source": "qr", "payload": payload, "error": type(e).__name__})
            continue
        cases.append({"kind": "qr", "source": "qr", "payload": payload, "analyse": info})
        triples.append(("qr", (info["check_text"], None, "qr")))
    for source, (text, sender, itype) in triples:
        key = (text, sender, itype)
        if key in seen:
            continue
        seen.add(key)
        case = record(text, sender, itype)
        case["source"] = source
        cases.append(case)
    for n in dict.fromkeys(test_amounts + RUPEES):
        cases.append({"kind": "rupees", "source": "rupees", "amount": n, "text": rupees(n)})
    fraud = get_pack("fraud")
    return {"fraud_sha256": fraud.sha256, "cases": [jsonable(c) for c in cases]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "tests" / "js" / "fraud_corpus.json"))
    args = ap.parse_args()
    corpus = build()
    Path(args.out).write_text(json.dumps(corpus, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    kinds: dict[str, int] = {}
    for c in corpus["cases"]:
        kinds[c.get("source", c["kind"])] = kinds.get(c.get("source", c["kind"]), 0) + 1
    print(f"wrote {args.out}: {len(corpus['cases'])} cases " + ", ".join(f"{k} {v}" for k, v in kinds.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
