"""Fraud pack 1.7.0 (7 Oct 2026): the live-demo traps still open after 1.6.0, each tested on new wordings (not the
benchmark messages themselves), and the genuine look-alikes that must stay alone."""
import pytest

from sahayak.fraud import check_message
from sahayak.fraud.normalize import fold
from sahayak.packs import get_pack

pytestmark = pytest.mark.skipif("call_forwarding" not in get_pack("fraud").data["signals"],
                                reason="fraud pack older than 1.7.0")
FLAG = ("scam", "suspicious")


def card(text, sender=None, input_type="text"):
    return check_message(text, sender=sender, input_type=input_type)


def signal_ids(c):
    return {s["id"] for s in c["signals"]}


@pytest.mark.parametrize("text,itype,category", [
    # a code that forwards your calls, typed or said aloud
    ("Airtel executive called saying my SIM will be blocked for KYC. He asked me to dial **21*9876543210# to verify.",
     "call", "call_forward"),
    ("Jio se call aaya, bole network upgrade ke liye *401*8800123456 dial karo, phir sab theek ho jayega.", "call",
     "call_forward"),
    ("The caller from the bank told me to press star star six one star and then his number. Is it OK?", "call",
     "call_forward"),
    ("उसने कहा स्टार 401 स्टार और फिर एक नंबर डायल करो, तभी पार्सल आएगा।", "call", "call_forward"),
    # an advance for something you cannot see first
    ("Badrinath helicopter seats available, pay 50% advance to 9876543210@ybl now, ticket on WhatsApp in 5 minutes.",
     "text", "deal_advance"),
    ("जयपुर में सस्ता प्लॉट, बिना देखे बुक करें। आज ही ₹11,000 बयाना जमा करें, कागज़ व्हाट्सएप पर।", "text",
     "deal_advance"),
    ("PG room near Koramangala, owner is in the army and posted in Assam so cannot show the room. Pay ₹8,000 deposit "
     "on UPI and he will send the keys by courier.", "text", None),
    # a fee for a failed delivery, through a link (one written with spaces)
    ("Your shipment AWB 1234 could not be delivered due to incomplete address. Pay Rs 12 redelivery fee: "
     "dlv-india.com/pay", "text", "courier"),
    ("Blue Dart: delivery failed. Pay a re-delivery fee of ₹12 within 24 hours at bluedart-redeliver . help/pay",
     "text", "courier"),
    # a link split on purpose
    ("Your electricity bill is pending. Pay at bijli-bill . top/pay (remove the spaces and open)", "text", None),
    ("KYC update karein: sbi-kyc . online/up (space hatakar kholen) warna account band.", "text", None),
    # a forwarded free-scheme post with the link in the picture
    ("प्रधानमंत्री फ्री लैपटॉप योजना 2026: निशुल्क पंजीकरण शुरू। फोटो पर क्लिक करें।", "text", "govt_scheme"),
    ("Government free solar panel scheme for every house! Click on the photo to register now.", "text", "govt_scheme"),
    # the card-limit "upgrade" call
    ("A man from the card department said my limit can be doubled for free; I only had to read out the confirmation "
     "code he sent.", "call", "otp_pin"),
])
def test_scams_are_flagged(text, itype, category):
    c = card(text, input_type=itype)
    assert c["verdict"] in FLAG, (c["verdict"], signal_ids(c))
    if category:
        assert c["category"]["id"] == category


@pytest.mark.parametrize("text,sender,itype", [
    # warnings and everyday USSD codes are not a forwarding code
    ("Never dial *401* or **21* followed by a number a stranger gives you. It forwards your calls. -DoT", None, "text"),
    ("To cancel all call forwarding on your phone, dial ##002#.", None, "text"),
    ("Dial *121# to check your balance and offers. -Airtel", None, "text"),
    ("Use *99# for UPI on a basic phone, even without internet.", None, "text"),
    # an advance already paid, or a deal you see first
    ("Thank you for booking Hotel Ganga View. We have received your advance of ₹3,100. Your confirmation is on "
     "WhatsApp.", None, "text"),
    ("Advance tax: pay the third instalment by 15 December on incometax.gov.in. -ITD", None, "text"),
    # couriers' own messages: a duty on the courier's own site, a delivery with its own tracking link
    ("DHL: Duty and tax of INR 1,240 is payable for your shipment 55120. Pay online at https://del.dhl.com/in/pay",
     None, "text"),
    ("India Post: Customs duty Rs 350 is payable for your parcel EE123456789IN. Please pay at your post office.",
     None, "text"),
    ("Your Delhivery parcel will arrive today. Track it at https://www.delhivery.com/track/package/1234", None, "text"),
    ("Your Amazon order #405-1234567 has shipped. Track: https://amzn.in/d/abc123", None, "text"),
    # "click a photo" is taking a picture; a warning not to click
    ("Free Ayushman card camp at the panchayat office on Sunday. Click a photo of your Aadhaar and bring it along.",
     None, "text"),
    ("सरकार की कोई भी योजना मुफ्त है। किसी अनजान फोटो पर क्लिक न करें।", None, "text"),
    ("मुफ्त होम डिलीवरी! ऑर्डर के लिए क्लिक करें।", None, "text"),
    # a code that is shown, not read out to a caller
    ("Your booking confirmation code is K7X2P. Show it at the counter. Do not share it with anyone.", None, "text"),
    ("IRCTC: PNR 4521345678 booked. Confirmation code 55123 for your e-ticket.", None, "text"),
    # ride and delivery codes given to the driver or delivery person
    ("Ola: Share OTP 4521 with your driver to start the ride. Driver Suresh, white Dzire KA01AB1234.", None, "text"),
    ("Zomato: Please share the OTP 3344 with the delivery partner only when you receive your order.", None, "text"),
])
def test_genuine_messages_stay_alone(text, sender, itype):
    c = card(text, sender, itype)
    assert c["verdict"] == "no_signs", (c["verdict"], signal_ids(c))


@pytest.mark.parametrize("raw,folded", [
    ("dlvry-in . help/pay", "dlvry-in.help/pay"),
    ("visit sbi-kyc . top now", "visit sbi-kyc.top now"),
    ("go to bit . ly/abc", "go to bit.ly/abc"),
    ("Welcome to SBI . In case of any query call us", "welcome to sbi . in case of any query call us"),
    ("Total Rs 5 . co-op bank", "total rs 5 . co-op bank"),
])
def test_a_link_split_with_spaces_is_joined_but_a_sentence_end_is_not(raw, folded):
    assert fold(raw) == folded


def test_the_forwarding_advice_gives_the_cancel_code():
    c = card("He told me to dial *401*9876543210 to get my parcel.", input_type="call")
    assert "call_forwarding" in signal_ids(c)
    assert any("##002#" in a for a in c["actions"]["en"])


@pytest.mark.parametrize("text,want", [
    ("आयुष्मान कार्ड बनवाने के लिए 500 रुपये इस नंबर पर भेजें 9876012345, कार्ड घर आ जाएगा। आज आखिरी दिन है।", 500),
    ("Your KYC is pending. Pay 499/- at sbi-kyc.top/pay today or your account will be blocked.", 499),
    ("मैं मुंबई पुलिस से बोल रहा हूँ, आप डिजिटल अरेस्ट में हैं। केस बंद करने के लिए तुरंत 10 हज़ार रुपये इस UPI पर भेजें: "
     "case.close@ybl", 10000),
])
def test_money_written_number_first_counts_as_money_at_risk(text, want):
    # "500 रुपये", "499/-", "10 हज़ार रुपये": Hindi puts the number first; the console's "money at risk" must see it
    c = card(text)
    assert c["verdict"] == "scam" and c["extracted"]["rupees_at_risk"] == want
