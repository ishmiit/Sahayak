"""bench/redact_messages.py: what identifies a person is replaced; what makes a scam a scam is kept."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("redact", ROOT / "bench" / "redact_messages.py")
redact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(redact)


def red(text):
    return redact.Redactor().text(text)


def test_mobiles_become_the_same_fictional_number_everywhere():
    r = redact.Redactor()
    out = r.text("Call 98765 43210 or +91-9876543210 now, or 9123456780")
    assert "98765" not in out and "9123456780" not in out
    assert out.count("9000000001") == 2 and "9000000002" in out


def test_account_card_and_aadhaar_numbers_keep_only_the_last_four():
    assert red("A/c 123456789012 credited") == "A/c XXXXXXXX9012 credited"
    assert red("Aadhaar 2345 6789 0123") == "Aadhaar XXXX XXXX 0123"
    assert red("card 4111-1111-1111-1234") == "card XXXX-XXXX-XXXX-1234"


def test_upi_ids_lose_the_name_and_keep_the_bank_handle():
    assert red("pay to ramesh.kumar@okaxis today") == "pay to payee1@okaxis today"


def test_emails_pan_and_link_tokens():
    out = red("Mail rk.sharma@gmail.com, PAN ABCDE1234F, open https://sbi-kyc.top/verify?id=88213&u=ramesh")
    assert "person1@example.com" in out and "XXXXX0000X" in out
    assert "https://sbi-kyc.top/verify?…" in out and "ramesh" not in out
    assert red("pay at indpost-help.top/pay?u=suresh now") == "pay at indpost-help.top/pay?… now"
    assert red("Is it real? Rs. 500? Tell me.") == "Is it real? Rs. 500? Tell me."


def test_names_after_a_greeting_or_title():
    assert red("Dear Ramesh Kumar, your KYC") == "Dear [NAME], your KYC"
    assert red("प्रिय राम जी, आपका खाता") == "प्रिय [NAME], आपका खाता"
    assert red("Mr. Sharma, pay now") == "Mr. [NAME], pay now"


def test_what_makes_a_scam_a_scam_is_kept():
    for text in ("Dear Customer, your SBI account will be blocked", "Hi Mum, this is my new number",
                 "प्रिय ग्राहक, आपका KYC खत्म", "Call 1930 or 1800 425 3800 or 1600123456",
                 "Your OTP is 482913. Rs 2,500.00 on 07-10-26 at AMAZON",
                 "नमस्ते आपके खाते में 5000 रुपये आए हैं"):
        assert red(text) == text, text
