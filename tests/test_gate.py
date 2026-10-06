"""Safety gate: blocks dangerous or invented content, passes every vetted template."""
import pytest

from sahayak.fraud.signals import Fired
from sahayak.fraud.verdict import build_card
from sahayak.packs import get_pack
from sahayak.safety import check_card_text, check_texts

PACK = get_pack("fraud").data


def _card_for(category: str, level: str):
    sig = next(s for s, d in PACK["signals"].items() if d.get("category") == category and d["weight"] > 0)
    return build_card([Fired(sig, PACK["signals"][sig]["weight"], False, {})], PACK, level=level)


@pytest.mark.parametrize("category", sorted(c for c in PACK["categories"] if c != "generic"))
@pytest.mark.parametrize("level", ["scam", "suspicious"])
def test_every_template_card_passes_the_gate(category, level):
    card = _card_for(category, level)
    result = check_card_text(card)
    assert result.passed, [c for c in result.checks if not c["passed"]]


def test_no_signs_template_passes():
    card = build_card([], PACK)
    assert card["verdict"] == "no_signs"
    assert check_card_text(card).passed


def ok(en, hi="यह ठगी है। किसी को OTP न बताएं।", verdict="scam", message=""):
    return check_texts({"en": en, "hi": hi}, verdict, message)


def test_blocks_dangerous_advice():
    assert not ok("Please share the OTP with the officer.").langs["en"]
    assert not ok("Click the link to update KYC.").langs["en"]
    assert not ok("Install the app from this page.").langs["en"]
    assert not ok("Pay the processing fee to get the loan.").langs["en"]
    assert not ok("This is fine", hi="लिंक पर क्लिक करें।").langs["hi"]
    assert not ok("This is fine", hi="अपना OTP बताएं।").langs["hi"]


def test_allows_negated_and_descriptive_advice():
    assert ok("Do not click the link and never share your OTP.").langs["en"]
    assert ok("This message asks you to share your OTP. Banks never ask for it.").langs["en"]
    assert ok("This is a scam.", hi="लिंक पर क्लिक न करें। OTP कभी न बताएं।").langs["hi"]


def test_blocks_invented_numbers_links_and_amounts():
    assert not ok("Call 9876543210 to report it.").langs["en"]
    assert not ok("Visit sbi-help.xyz for help.").langs["en"]
    assert not ok("You may lose Rs 75,000.", message="Pay Rs 999 now").langs["en"]
    assert ok("Call 1930 or report at cybercrime.gov.in.").langs["en"]
    assert ok("They ask for Rs 999.", message="Pay Rs 999 now").langs["en"]


def test_blocks_verdict_contradiction_and_wrong_script():
    assert not ok("Don't worry, this is not a scam.").langs["en"]
    assert not ok("No scam signs, it is completely safe.", verdict="no_signs").langs["en"]
    assert not ok("This is a scam.", hi="yah thagi hai").langs["hi"]


def test_blocks_saying_a_number_or_link_is_missing_when_it_is_there():
    # seen with qwen2.5:3b: "no phone number given" about a message asking you to call a mobile number
    msg = "Your electricity will be cut tonight. Call our officer at 9876543210 immediately."
    assert not ok("Electricity scam is fake, no phone number given.", message=msg).langs["en"]
    assert ok("No real electricity board cuts power after a call from a mobile number.", message=msg).langs["en"]
    link_msg = "Your KYC has expired. Update at http://sbi-kyc-update.xyz"
    assert not ok("It is fake; there is no link to check.", message=link_msg).langs["en"]
    # the same words are fine when the message really has no number or link
    assert ok("This message has no link and no phone number.", message="Hello, how are you?").langs["en"]
