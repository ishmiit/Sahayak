"""The red-team set (bench/redteam/redteam_v0.jsonl) stays caught, and the folding that catches it
leaves codes, masked numbers, amounts and real links alone."""
import json
from pathlib import Path

import pytest

from sahayak.fraud import check_message
from sahayak.fraud.normalize import fold

ROOT = Path(__file__).resolve().parent.parent
ROWS = [json.loads(line) for line in (ROOT / "bench" / "redteam" / "redteam_v0.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()]
# Flagged on purpose (see bench/results/redteam_v0.md): a short link hides where it goes. (rt-061, a debit alert
# ending "call 1800 1234 or SMS BLOCK to <mobile>", left this set with the SMS-block exemption in signals.py.)
BY_DESIGN = {"rt-065"}


@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_red_team_message(row):
    card = check_message(row["text"], sender=row["sender"])
    flagged = card["verdict"] in ("scam", "suspicious")
    if row["id"] in BY_DESIGN:
        assert flagged
    else:
        assert flagged == (row["label"] == "scam"), (row["technique"], card["verdict"], [s["id"] for s in card["signals"]])


@pytest.mark.parametrize("text,folded", [
    ("Y0ur acc0unt is bl0cked. Share the 0TP", "your account is blocked. share the otp"),
    ("KYC upd4te now", "kyc update now"),
    ("hxxp://cashback-paytm[.]top/claim", "http://cashback-paytm.top/claim"),
    ("visit sbi-pan-link dot xyz now", "visit sbi-pan-link.xyz now"),
    ("bijli-bill-update (dot) site", "bijli-bill-update.site"),
    # left alone: links, codes, masked numbers, amounts, times, ordinary words
    ("http://kyc-upd4te.top/login", "http://kyc-upd4te.top/login"),
    ("A/c XX4421 debited Rs 2,500.00 at 3pm, OTP 482913", "a/c xx4421 debited rs 2,500.00 at 3pm, otp 482913"),
    ("covid19 mp3 4g", "covid19 mp3 4g"),
    ("the dot on the i", "the dot on the i"),
])
def test_fold_undoes_disguises_only(text, folded):
    assert fold(text) == folded
