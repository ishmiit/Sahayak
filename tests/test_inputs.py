"""More ways in: UPI QR codes, screenshots, and descriptions of phone calls."""
import io
import json
from pathlib import Path

import pytest
import qrcode
from fastapi.testclient import TestClient

from sahayak.fraud import check_message
from sahayak.inputs.qr import analyse, parse_upi, rupees
from sahayak.server import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parent.parent


def qr_png(text: str) -> bytes:
    from qrcode.image.pil import PilImage
    buf = io.BytesIO()
    qrcode.make(text, image_factory=PilImage).get_image().save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- UPI QR

def test_upi_fields_are_parsed():
    u = parse_upi("upi://pay?pa=shop@okaxis&pn=Shyam%20Kirana&am=250.50&cu=INR&tn=Atta&mc=5411")
    assert u == {"action": "pay", "payee": "shop@okaxis", "name": "Shyam Kirana", "amount": 250.5, "currency": "INR",
                 "note": "Atta", "merchant_code": "5411"}
    assert parse_upi("https://example.com") is None


@pytest.mark.parametrize("n,text", [(250, "₹250"), (4999, "₹4,999"), (100000, "₹1,00,000"), (12345678, "₹1,23,45,678"), (99.5, "₹99.50")])
def test_rupees_use_indian_grouping(n, text):
    assert rupees(n) == text


def test_every_upi_card_says_scanning_sends_money():
    a = analyse("upi://pay?pa=shop@okaxis&pn=Shyam%20Kirana&am=250&mc=5411")
    assert "never brings money in" in a["facts"][0]["en"] and "₹250" in a["facts"][0]["en"]
    assert "QR से पैसे कभी आते नहीं" in a["facts"][0]["hi"]
    assert a["flags"] == []


@pytest.mark.parametrize("example,verdict,flag", [
    ("qr_cashback", "scam", "receive_claim"),
    ("qr_kyc", "scam", "official_name"),
    ("qr_shop", "no_signs", None),
])
def test_demo_qr_codes_end_to_end(example, verdict, flag):
    png = client.get(f"/api/demo/qr/{example}").content
    card = client.post("/api/qr", content=png, headers={"Content-Type": "image/png"}).json()
    assert card["verdict"] == verdict and card["input_type"] == "qr"
    assert card["qr"]["kind"] == "upi" and card["qr"]["facts"]
    if flag:
        assert flag in card["qr"]["flags"]


def test_a_qr_with_a_scam_link_goes_through_the_link_checks():
    card = client.post("/api/qr", content=qr_png("http://sbi-kyc-update.xyz/login")).json()
    assert card["verdict"] == "scam" and card["qr"]["kind"] == "link"


def test_bad_images():
    assert client.post("/api/qr", content=b"not an image").status_code == 422
    blank = io.BytesIO()
    from PIL import Image
    Image.new("RGB", (200, 200), "white").save(blank, format="PNG")
    assert client.post("/api/qr", content=blank.getvalue()).status_code == 422
    assert client.get("/api/demo/qr/nope").status_code == 404


# ---------------------------------------------------------------- screenshots

def test_screenshot_is_read_offline():
    from sahayak.inputs.ocr import get_reader
    if not get_reader().available():
        pytest.skip("OCR models not installed")
    import sys
    sys.path.insert(0, str(ROOT / "bench"))
    from eval_ocr import render
    png = render("Dear customer your SBI account KYC has expired. Update now: http://sbi-kyc-update.xyz", "9812345678")
    out = client.post("/api/ocr", content=png).json()
    assert "KYC" in out["text"] and "expired" in out["text"]
    card = check_message(out["text"], input_type="ocr")
    assert card["verdict"] == "scam"
    assert client.post("/api/ocr", content=b"nope").status_code == 422


# ---------------------------------------------------------------- calls described in words

CALLS = [json.loads(line) for line in (ROOT / "bench" / "callbench" / "calls_v0.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.mark.parametrize("row", CALLS, ids=[r["id"] for r in CALLS])
def test_call_descriptions(row):
    card = check_message(row["text"], input_type="call")
    flagged = card["verdict"] in ("scam", "suspicious")
    assert flagged == (row["label"] == "scam"), (card["verdict"], [s["id"] for s in card["signals"]])


@pytest.mark.parametrize("read,fixed", [
    ("Link now: aadhaar-link-dbtsite", "Link now: aadhaar-link-dbt.site"),
    ("Claim now! http:/Ispin-win-\nbonusxyz", "Claim now! http://spin-win-bonus.xyz"),
    ("portal: lpg-subsidy-click", "portal: lpg-subsidy.click"),
    ("bank-security-\napp.xyz/secure.apk", "bank-security-app.xyz/secure.apk"),
    ("http://spin-win-bonus.xyz", "http://spin-win-bonus.xyz"),
    # ordinary words are left alone
    ("visit our website today", "visit our website today"),
    ("double-click here", "double-click here"),
    ("check-in at 10", "check-in at 10"),
    ("well-being online", "well-being online"),
])
def test_ocr_link_repair(read, fixed):
    from sahayak.inputs.ocr import repair_links
    assert repair_links(read) == fixed


@pytest.mark.parametrize("read,fixed", [
    ("SBl never asks for OTP", "SBI never asks for OTP"),
    ("enter your UPl PlN to receive", "enter your UPI PIN to receive"),
    ("Hello all, call Ill", "Hello all, call Ill"),
    ("lCICI Bank", "ICICI Bank"),
])
def test_ocr_capital_i_repair(read, fixed):
    from sahayak.inputs.ocr import repair_capitals
    assert repair_capitals(read) == fixed


def test_ocr_wrapped_lines_become_one_paragraph():
    """The sender stays on its own line; lines wrapped inside the bubble join, so a warning split
    across two lines ("Never / share it") is still read as a warning, not as a request."""
    from sahayak.inputs.ocr import _lines
    box = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]  # noqa: E731
    boxes = [(box(38, 40, 202, 66), "VM-SBIBNK-T", 0.9),
             (box(57, 159, 420, 201), "OTP for login to YONO is 739204.", 0.9), (box(430, 160, 595, 200), "Never", 0.9),
             (box(55, 205, 641, 245), "share it with anyone. SBI never asks for OTP", 0.9),
             (box(55, 330, 300, 370), "Thank you", 0.9)]  # after a blank line: a new paragraph
    text = _lines(boxes)
    assert text == "VM-SBIBNK-T\nOTP for login to YONO is 739204. Never share it with anyone. SBI never asks for OTP\nThank you"
    assert check_message(text, input_type="ocr")["verdict"] == "no_signs"
