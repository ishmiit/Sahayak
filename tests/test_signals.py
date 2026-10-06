"""Signal layer and verdict behaviour on hand-picked messages, including the genuine
messages most likely to cause false alarms."""
import pytest

from sahayak.fraud import check_message
from sahayak.packs import get_pack


def ids(card):
    return {s["id"] for s in card["signals"]}


@pytest.mark.parametrize("text,sender,itype,verdict,signal", [
    # scams, one per major pattern, in English, Hindi and Hinglish
    ("Dear customer your SBI account KYC has expired. Update immediately or your account will be blocked today: http://sbi-kyc-update.xyz/login",
     None, "text", "scam", "kyc_threat"),
    ("Sir main SBI bank se bol raha hu, aapka card block ho jayega. Aapke mobile pe jo OTP aaya hai woh batao turant.",
     None, "text", "scam", "otp_request"),
    ("मैं मुंबई पुलिस से बोल रहा हूँ। आपके आधार से मनी लॉन्ड्रिंग हुई है। आप डिजिटल अरेस्ट में हैं, वीडियो कॉल पर बने रहें और किसी को मत बताना।",
     None, "call", "scam", "digital_arrest"),
    ("Dear Consumer your electricity power will be disconnected tonight at 9.30pm because your previous month bill was not updated. Please immediately contact our electricity officer 9876543210",
     None, "text", "scam", "electricity_cut"),
    ("Congratulations! You have received a cashback of Rs 5000 from PhonePe. Scan the QR code and enter your UPI PIN to receive the money.",
     None, "text", "scam", "upi_receive"),
    ("Part time job! Earn Rs 3000 per day by liking YouTube videos. Join our Telegram group now",
     None, "text", "scam", "easy_money"),
    ("Your FedEx parcel containing illegal drugs and fake passports has been seized by customs. Press 1 to talk to the officer.",
     None, "call", "scam", "courier_seized"),
    ("Install AnyDesk from the Play Store and share the code so our bank executive can fix your account.",
     None, "text", "scam", "remote_access"),
    ("PM Kisan new list jari. Apna naam dekhne ke liye PM-Kisan.apk download karein",
     None, "text", "scam", "link_apk"),
    ("Your loan of Rs 2,00,000 is approved. Pay Rs 999 processing fee to release the amount today.",
     None, "text", "scam", "advance_fee"),
    ("Guaranteed 300% returns in 30 days! Join our VIP stock tips group on WhatsApp.",
     None, "text", "scam", "investment_promise"),
    ("Dear customer, your HDFC Bank account will be suspended. Update PAN now: hdfc-pan-update.top",
     "9812345678", "text", "scam", "link_lookalike"),
    ("If you did not make this payment of Rs 4,999, approve the request in Google Pay to reverse it.",
     None, "text", "scam", "upi_receive"),
])
def test_scams(text, sender, itype, verdict, signal):
    card = check_message(text, sender=sender, input_type=itype)
    assert card["verdict"] == verdict, (card["verdict"], ids(card))
    assert signal in ids(card)
    assert card["reasons"], "every scam verdict explains itself"
    assert card["helplines"], "scam verdicts always offer 1930"


@pytest.mark.parametrize("text,sender", [
    ("482910 is your OTP for txn of Rs 2,500.00 at AMAZON on HDFC Bank card XX4421. Valid for 5 mins. Do not share OTP with anyone. -HDFC Bank", "AX-HDFCBK-T"),
    ("OTP for your Flipkart order delivery is 4821. Share it with the delivery agent only after you receive the product.", "VM-FLPKRT-S"),
    ("Rs 1,200.00 debited from A/c XX7781 on 01-10-26 to VPA ravi@okaxis. UPI Ref 427811902. Not you? Call 18001234 -SBI", "JD-SBIINB-S"),
    ("SBI never asks for your OTP, PIN or passwords. Beware of digital arrest scams; police never arrest anyone on a video call. Report fraud on 1930.", "AD-SBIBNK-G"),
    ("आपका OTP 482910 है। इसे किसी के साथ साझा न करें। - SBI", "AX-SBIBNK-T"),
    ("Dear Customer, your KYC is due for periodic update. Please visit your nearest branch with valid documents.", "VM-SBIBNK-S"),
    ("Beta khana kha liya? Kal subah 9 baje station pe milte hain.", None),
    ("Your electricity bill of Rs 845 for September is generated. Pay on the official app before 15 Oct.", "VM-BESCOM-S"),
])
def test_genuine_messages_are_not_flagged(text, sender):
    card = check_message(text, sender=sender)
    assert card["verdict"] == "no_signs", (card["verdict"], ids(card))
    assert card["category"] is None
    assert card["helplines"] == []


@pytest.mark.parametrize("text,sender", [
    # regressions found on the ScamBench v0 test split (post-freeze log)
    ("To receive money on UPI you never need to enter your PIN or scan a QR. -NPCI", "AD-NPCIUP-G"),
    ("Free eye check-up camp at Government Hospital this Sunday 9 AM to 1 PM. No registration fee.", "VM-DHSKAR-G"),
    # regressions found on train/dev during tuning
    ("Do not install screen-sharing apps like AnyDesk on the advice of unknown callers. Stay alert, stay safe. -HDFC Bank", "AX-HDFCBK-S"),
    ("Your Ola ride is confirmed. Driver Suresh arriving in 4 minutes. Share OTP 4417 with the driver to start the ride.", "VM-OLACAB-S"),
    ("Congratulations! You have earned 250 reward points on your HDFC Bank credit card.", "AX-HDFCBK-P"),
    ("Your BSNL landline bill of Rs 590 is generated. Pay by 20 Oct at portal.bsnl.in or any BSNL office.", "VM-BSNLIN-S"),
    # found 6 Oct: warnings about refund and collect-request scams were themselves called scams, and a
    # refund report must not read as the collect-request trick
    ("Never approve a collect request from strangers to get a refund. A request always takes money from you. -NPCI", "AD-NPCIUP-G"),
    ("Beware: fraudsters ask you to approve requests or scan QR codes for refunds. Report on 1930.", None),
    ("We have accepted your request for a refund of Rs 499. It will reach your account in 5-7 days. -Myntra", "VM-MYNTRA-S"),
    ("आपकी रिफंड रिक्वेस्ट स्वीकार कर ली गई है। ₹499 पांच दिन में आपके खाते में आ जाएंगे।", None),
])
def test_known_false_alarms_stay_fixed(text, sender):
    assert check_message(text, sender=sender)["verdict"] == "no_signs"


@pytest.mark.parametrize("text,itype", [
    ("Hello sir, Amazon delivery executive here, an OTP has come on your phone, just read it to me so I can mark the parcel delivered", "call"),
    ("मैं बैंक से बोल रहा हूँ, आपका एटीएम पिन बदलना है। अपना पुराना पिन और कार्ड नंबर बता दीजिए।", "call"),
    ("Delhi Police: your mobile number is used in a cyber fraud. To avoid arrest, verify yourself by paying a security amount of Rs 25,000.", "text"),
    ("Tumhari photos edit karke ghar walon ko bhej dunga, 10,000 abhi bhejo is UPI pe", "text"),
    # found by the console tests: a masked card number ("XX4421") was taken for an OTP code
    ("Sunita ji, aapke card XX4421 ka OTP batao turant warna block ho jayega", "text"),
    # the collect-request trick (ScamBench sb-0109, logged 2 Oct, fixed 6 Oct): approving a request sends money
    ("I am sending Rs 5000 to you by mistake, please accept the request on PhonePe and return it", "text"),
    ("Bhai galti se maine aapko 2000 bhej diye, request accept kar do, paise wapas chahiye", "text"),
    ("मैंने गलती से आपको 3000 रुपये भेज दिए हैं। कृपया रिक्वेस्ट स्वीकार करें और पैसे वापस करें।", "text"),
])
def test_known_misses_stay_fixed(text, itype):
    assert check_message(text, input_type=itype)["verdict"] in ("scam", "suspicious")


SCHEME_FEE_ON = "scheme_fee" in get_pack("fraud").data["signals"]


@pytest.mark.skipif(not SCHEME_FEE_ON, reason="fraud pack 1.4.0 not signed and installed yet (scripts/pack_update_1_4.py)")
@pytest.mark.parametrize("text,sender,want", [
    # money sent to a number, UPI ID or link for a free government card or scheme
    ("आयुष्मान कार्ड बनवाने के लिए 500 रुपये इस नंबर पर भेजें 9876012345, कार्ड घर आ जाएगा।", "9876012345", "scam"),
    ("Aapka Ayushman card band hone wala hai. Card chalu rakhne ke liye 299 rupaye is UPI par bhejein: ayushman.help@ybl", None, "scam"),
    ("e-Shram card yojana: Rs 100 registration ke liye 9812233445 par Google Pay karein, card 2 din mein aayega.", None, "scam"),
    ("Pension yojana list mein naam ke liye Rs 500 pay karein is number par 9123456780", None, "scam"),
    # the same words, but advice, a counter, or a genuine notice
    ("आयुष्मान कार्ड मुफ़्त है। कार्ड के लिए किसी को पैसे न भेजें। शिकायत 14555 पर करें।", "VM-NHAPMJ-G", "no_signs"),
    ("Do not pay anyone for an Ayushman or e-Shram card. Both are free at your CSC. Report agents to 14555.", "VM-CSCSPV-G", "no_signs"),
    ("Ayushman card camp at Gram Panchayat Bhavan on 9 Oct, 10 AM. Bring Aadhaar. Free of cost. -CSC", "VM-CSCSPV-G", "no_signs"),
    ("PM-KISAN: Rs 2000 ki kist aapke bank khate mein bhej di gayi hai. Status pmkisan.gov.in par dekhein.", "VM-PMKSAN-G", "no_signs"),
])
def test_paying_for_a_free_scheme_card(text, sender, want):
    card = check_message(text, sender=sender)
    assert card["verdict"] == want, (card["verdict"], ids(card))
    if want == "scam":
        assert "scheme_fee" in ids(card) and card["category"]["id"] == "govt_scheme"


def test_never_says_safe():
    card = check_message("Beta khana kha liya?")
    assert "safe" not in card["headline"]["en"].lower()
    assert card["verdict"] == "no_signs"


def test_delivery_otp_with_unofficial_link_is_still_caught():
    card = check_message("Your parcel is on hold. Share the OTP to reschedule delivery: http://parcel-reschedule.xyz")
    assert card["verdict"] == "scam"


def test_homoglyph_brand_is_flagged():
    card = check_message("Dеar customer, your SВI account is blocked. Call 9876543210 now.")  # Cyrillic е and В
    assert "lookalike_text" in ids(card)
    assert card["verdict"] in ("scam", "suspicious")


def test_reason_templates_are_filled():
    card = check_message("Update KYC now at http://sbi-kyc.xyz or account blocked", sender="9812345678")
    for r in card["reasons"]:
        assert "{" not in r["text"]["en"] and "{" not in r["text"]["hi"]


def test_rupees_at_risk_only_for_scams():
    scam = check_message("Pay Rs 999 processing fee to receive your Rs 50,000 lottery prize")
    assert scam["verdict"] == "scam" and scam["extracted"]["rupees_at_risk"] == 50000
    genuine = check_message("Rs 1,200.00 debited from A/c XX7781. Not you? Call 18001234", sender="JD-SBIINB-S")
    assert genuine["extracted"]["rupees_at_risk"] == 0


def test_fast():
    check_message("warm up")
    card = check_message("Dear customer your SBI account KYC has expired. Update immediately: http://sbi-kyc-update.xyz")
    assert card["timing_ms"]["total"] < 50
