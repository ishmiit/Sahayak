"""UPI QR check: read a photographed QR code on the node and say what it really does.

A UPI QR is a payment request. Scanning it and entering the UPI PIN sends money from the
person's account; it never brings money in. "Scan this QR to receive your cashback" is therefore
always a scam, and the card says so in plain words, with the payee name, UPI ID and amount the
code actually carries. Any other QR is a link or text, and goes through the normal scam check.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlsplit

from .image import ImageError, load

# words that claim the scan will bring money in: what a payment QR can never do
_RECEIVE_CLAIM = re.compile(
    r"receive|refund|cashback|cash\s*back|prize|reward|lottery|winning|won\b|credit(?:ed)?\b|bonus|gift|"
    r"milega|milenge|paane|पाने|मिलेगा|मिलेंगे|इनाम|कैशबैक|रिफंड|लॉटरी|जीत", re.I)
_OFFICIAL_NAME = re.compile(
    r"\b(?:sbi|hdfc|icici|axis|pnb|bank|rbi|npci|police|cbi|customs|court|government|govt|sarkar|pm[\s-]?kisan|"
    r"electricity|bijli|kyc|customer\s*care|helpline|income\s*tax|uidai|aadhaar)\b", re.I)


class QRError(ValueError):
    pass


def decode(image: bytes) -> str:
    """The text inside the first QR code found in a photo or screenshot."""
    import cv2
    try:
        img = load(image, color=False, longest=1600)
    except ImageError as e:
        raise QRError(str(e)) from None
    detector = cv2.QRCodeDetector()
    for candidate in (img, cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)):
        text, _, _ = detector.detectAndDecode(candidate)
        if text:
            return text
    raise QRError("no QR code found in the photo")


def parse_upi(payload: str) -> dict | None:
    """upi://pay?pa=…&pn=…&am=… -> its fields, or None if this is not a UPI payment code."""
    if not payload.lower().startswith("upi://"):
        return None
    parts = urlsplit(payload)
    q = {k.lower(): unquote(v[0]).strip() for k, v in parse_qs(parts.query, keep_blank_values=True).items()}
    amount = None
    if q.get("am"):
        try:
            amount = round(float(q["am"]), 2)
        except ValueError:
            amount = None
    return {"action": parts.netloc.lower() or "pay", "payee": q.get("pa", ""), "name": q.get("pn", ""),
            "amount": amount, "currency": q.get("cu", "INR") or "INR", "note": q.get("tn", ""),
            "merchant_code": q.get("mc", "")}


def rupees(amount: float) -> str:
    whole = int(amount)
    s = f"{whole:,}"
    if whole >= 100000:  # Indian grouping: 1,00,000
        head, tail = str(whole)[:-3], str(whole)[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = f"{head},{tail}"
    return f"₹{s}" + (f".{int(round(amount * 100)) % 100:02d}" if amount != whole else "")


def analyse(payload: str) -> dict:
    """What the QR does, in words, and the text to run through the scam check."""
    upi = parse_upi(payload)
    if upi is None:
        return {"kind": "link" if re.match(r"(?i)https?://|www\.", payload) else "text", "payload": payload[:500],
                "check_text": payload[:4000], "facts": []}
    who = upi["name"] or upi["payee"] or "someone"
    amount = rupees(upi["amount"]) if upi["amount"] else None
    facts = [{
        "hi": f"इस QR को स्कैन करके UPI PIN डालने पर पैसे आपके खाते से {who} को जाते हैं" + (f" ({amount})" if amount else "") +
              "। QR से पैसे कभी आते नहीं।",
        "en": f"Scanning this QR and entering your UPI PIN sends money from your account to {who}" +
              (f" ({amount})" if amount else "") + ". A QR never brings money in.",
    }]
    flags = []
    claim = " ".join([upi["note"], upi["name"]])
    if _RECEIVE_CLAIM.search(claim):
        flags.append("receive_claim")
    if _OFFICIAL_NAME.search(upi["name"]) and not upi["merchant_code"]:
        flags.append("official_name")
        facts.append({"hi": f"नाम \"{upi['name']}\" लिखा है, पर पैसे UPI ID {upi['payee']} में जाएँगे। बैंक, पुलिस या सरकार QR से पैसे नहीं माँगते।",
                      "en": f"It says \"{upi['name']}\", but the money goes to the UPI ID {upi['payee']}. Banks, police and the government do not collect money by QR."})
    if upi["amount"] and upi["amount"] >= 10000:
        flags.append("large_amount")
    # What the code claims, written out, so the same signals and categories decide the verdict.
    if "receive_claim" in flags:
        text = f"Scan the QR and enter your UPI PIN to receive money. {upi['note']} {upi['name']}"
    else:
        text = f"Pay {amount or 'money'} to {upi['name']} ({upi['payee']}). {upi['note']}"
    return {"kind": "upi", **upi, "amount_text": amount, "facts": facts, "flags": flags, "check_text": text.strip()}
