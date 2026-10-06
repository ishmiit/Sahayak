"""The printed case slip: the answers and results as plain text, plus a QR code holding
the same text so a CSC operator can fill the form without asking again.

The QR text is ASCII on purpose: it stays small enough to scan off a 58 mm thermal
print, and any phone's QR reader shows it as readable lines. It never holds a name.
"""
from __future__ import annotations

import base64
import datetime as dt
import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M

LABELS = {"eligible": "ELIGIBLE", "likely": "LIKELY (needs proof)", "check": "CHECK AT OFFICE",
          "unlock": "AFTER OPENING A BANK ACCOUNT", "have": "ALREADY GETS"}


def slip_text(result: dict, today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    pack = result["pack"]
    lines = [f"SAHAYAK SLIP | {pack['name']} pack {pack['version']} | {today.isoformat()}",
             "; ".join(f"{p['id']}={p['code']}" for p in result["profile"])]
    short = {c["id"]: c["short"] for c in result["schemes"]}
    for group, label in LABELS.items():
        ids = result["groups"].get(group, [])
        if ids:
            lines.append(f"{label}: " + ", ".join(short[i] for i in ids))
    lines.append("No name stored. Guidance only; the office decides.")
    return "\n".join(lines)


def qr_png(text: str) -> bytes:
    """A 1-bit PNG, 4 px per module: about 1 KB, crisp on a thermal print when scaled."""
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=4, border=2)
    qr.add_data(text.encode("utf-8"))
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").get_image().convert("1").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def qr_data_uri(text: str) -> str:
    return "data:image/png;base64," + base64.b64encode(qr_png(text)).decode("ascii")


def slip(result: dict, today: dt.date | None = None) -> dict:
    text = slip_text(result, today)
    return {"text": text, "qr": qr_data_uri(text), "date": (today or dt.date.today()).isoformat()}
