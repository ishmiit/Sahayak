"""Fraud pack 1.6.0 (7 Oct 2026): the fixes found by the blind red team and the dev half of PublicBench, each tested on
new wordings (not the benchmark messages themselves), and the genuine messages that must stay alone."""
import pytest

from sahayak.fraud import check_message
from sahayak.packs import get_pack

pytestmark = pytest.mark.skipif("doorstep_code" not in get_pack("fraud").data["signals"],
                                reason="fraud pack older than 1.6.0")
FLAG = ("scam", "suspicious")


def verdict(text, sender=None, input_type="text"):
    return check_message(text, sender=sender, input_type=input_type)


@pytest.mark.parametrize("text,sender,itype", [
    # a bank's own "SMS BLOCK ... to <long code>" footer beside its toll-free number
    ("Your A/c XX4521 is debited for Rs 1,250.00 on 06-10-26. Not you? Call 18001234 or SMS BLOCK 4521 to 9212299955 "
     "-Indian Bank", "VM-INDBNK-S", "text"),
    # family money with no hurry; the writer's own bank
    ("Mummy, rent ke ₹5,000 purane account me daal dena, koi jaldi nahi, kal tak chalega.", None, "text"),
    ("मेरे SBI वाले खाते में ₹6,000 डाल देना जब समय मिले।", None, "text"),
    # come in person and bring papers
    ("Walk-in interview on Friday 11 am at our office, Sector 62. Please bring your resume and an Aadhaar copy. "
     "Call 9876543210 for directions.", None, "text"),
    # the delivery code given at the door
    ("The delivery boy came to my door, handed me the parcel and then asked me for the OTP, so I told him.", None, "call"),
    # a power cut explained as maintenance; a shop's discount on bank cards
    ("Bijli vibhag: line ke maintenance ke liye kal 10 se 2 baje tak bijli band rahegi.", None, "text"),
    ("Big Diwali sale! Extra 10% instant discount on select bank cards. Shop now at www.flipkart.com", None, "text"),
    # real Income Tax wording stays clean: "pay the tax" was deliberately not made a fee phrase
    ("Refund of Rs 4,520 for AY 2026-27 has been credited to your bank account XX1234. -ITDEPT", "VM-ITDEPT-G", "text"),
    ("Dear taxpayer, please pay the tax due for AY 2026-27 by 31 March on incometax.gov.in to avoid interest. -ITD",
     "VM-ITDEPT-G", "text"),
])
def test_genuine_messages_stay_alone(text, sender, itype):
    assert verdict(text, sender, itype)["verdict"] == "no_signs"


@pytest.mark.parametrize("text,itype,category", [
    ("Your A/c XX4521 is debited for Rs 1,250.00. Not you? Call 9212299955 to block your card -Indian Bank", "text", None),
    ("I sent Rs 2,000 to your account by mistake. Please return it to this number 9876543210.", "text", "wrong_credit"),
    ("Video call ki recording mere paas hai. ₹10,000 bhejo warna saare contacts ko bhej dungi.", "text", "sextortion"),
    ("उसने वीडियो रिकॉर्ड कर लिया और पैसे न देने पर ब्लैकमेल करने की धमकी दी।", "call", "sextortion"),
    ("Please help baby Riya's heart surgery. Donate any amount to riyahelp@okaxis. Every rupee counts.", "text", "charity"),
    ("Join our gold trading platform and earn 5% every day. Message 9876543210.", "text", "investment"),
    ("Congratulations, you are selected for the post of ground staff. Pay Rs 3,500 for the training kit today to "
     "confirm your joining.", "text", "job_task"),
    ("A man called saying he is from the courier company and asked me to read out the OTP I just got on the phone.",
     "call", "otp_pin"),
    ("Hello, this is the cyber police. A complaint has been filed against you. Press 1 to speak to the officer.", "call", None),
    ("Hi, I accidentally sent you a message, can you forward it to me please?", "text", "otp_pin"),
    ("RBI notice: your payment of Rs 1,00,000 is on hold. Pay the tax for releasing the payment, Rs 5,000, today.",
     "text", None),
    ("He said he was a police officer and my son had been arrested, and that I should pay him Rs 50,000 to clear his name.",
     "call", None),
    ("The buyer sent me a QR code and told me to scan it to receive the payment for my sofa.", "call", "upi_receive"),
])
def test_scams_are_flagged(text, itype, category):
    card = verdict(text, input_type=itype)
    assert card["verdict"] in FLAG, card["verdict"]
    if category:
        assert card["category"]["id"] == category


def test_a_told_call_is_never_a_bank_alert():
    # "the amount got credited to my account" in a person's story of a call is not the bank's alert
    card = verdict("He sent me a QR code of Re 1 and asked me to scan it and receive money. The amount got credited to "
                   "my account, so I trusted him.", input_type="call")
    assert "genuine_txn_alert" not in {s["id"] for s in card["signals"]}
    assert card["verdict"] in FLAG
