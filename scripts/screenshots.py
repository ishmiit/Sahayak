"""Capture phone-size screenshots of the running app (true mobile emulation via Playwright).

Usage: python scripts/screenshots.py [out_dir] [base_url]
Emulates a 412x915 Android phone (touch, mobile viewport, 2.6x pixels). Used for
the README, the deck and the submission visuals, and as a layout regression check:
it fails if any screen is wider than the phone.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PHONE = dict(viewport={"width": 412, "height": 915}, device_scale_factor=2.625, is_mobile=True, has_touch=True)

SHOTS = [
    # name, path, what to wait for, optional click before the shot
    ("01_home_hi", "/", ".tiles", None),
    ("02_check_hi", "/?screen=check", "#examples .chip", None),
    ("03_result_kyc_hi", "/?demo=kyc_hi", "#verdict.scam", None),
    ("04_result_genuine_otp_en", "/?demo=genuine_otp&lang=en", "#verdict.no_signs", "explain"),
    ("05_result_digital_arrest_hi", "/?demo=digital_arrest", "#verdict.scam", None),
    ("06_complaint_hi", "/?demo=otp_call", "#verdict.scam", "#btn-complaint"),
    ("07_benefits_intro_hi", "/?screen=benefits", "#nav-demos .chip", None),
    ("08_benefits_question_hi", "/?nav=start", ".age-input", None),
    ("09_benefits_result_widow_hi", "/?nav=widow67", '[data-screen="benefits-result"]:not([hidden]) .scheme', None),
    ("10_benefits_result_worker_en", "/?nav=worker32&lang=en", '[data-screen="benefits-result"]:not([hidden]) .scheme', None),
    ("11_benefits_slip_hi", "/?nav=widow67", '[data-screen="benefits-result"]:not([hidden]) .scheme', "#btn-slip"),
    ("12_result_fake_scheme_hi", "/?demo=scheme_apk", "#verdict.scam", None),
    ("13_qr_cashback_hi", "/?qr=qr_cashback", "#qr-box:not([hidden])", None),
    ("14_qr_shop_en", "/?qr=qr_shop&lang=en", "#qr-box:not([hidden])", None),
]


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots").resolve()
    base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000"
    out.mkdir(parents=True, exist_ok=True)
    overflow = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, path, wait_for, action in SHOTS:
            ctx = browser.new_context(**PHONE, color_scheme="light", service_workers="block")
            page = ctx.new_page()
            # networkidle also waits for the model's explanation, which is slow on a busy laptop CPU
            page.goto(base + path, wait_until="networkidle" if action != "explain" else "load", timeout=180000)
            page.wait_for_selector(wait_for, timeout=15000)
            if action == "explain":
                # Wait for the local model's explanation (slow on a laptop CPU). A CSS selector,
                # not a JS predicate: the app's CSP forbids eval, which Playwright's predicates need.
                page.wait_for_selector("#explain:not(.loading)", state="attached", timeout=120000)
            elif action:
                page.click(action)
                page.wait_for_timeout(300)
            width = page.evaluate("document.documentElement.scrollWidth")
            if width > PHONE["viewport"]["width"]:
                overflow.append(f"{name}: page is {width}px wide")
            page.screenshot(path=str(out / f"{name}.png"), full_page=True)
            print(f"{name}: ok (scrollWidth {width}px)")
            ctx.close()
        browser.close()
    for line in overflow:
        print("OVERFLOW", line)
    return 1 if overflow else 0


if __name__ == "__main__":
    raise SystemExit(main())
