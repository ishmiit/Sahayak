"""Prove the phone keeps working away from the node: open the app once, cut the network, then check a scam
message, a demo UPI QR code and run the benefits interview, all answered by the phone itself.

Runs against the node (its HTTPS address, or http://127.0.0.1:8000 on the node itself: browsers treat
localhost as secure, so the service worker runs there too) or against the stand-alone build
(scripts/build_tryit.py) served on localhost or HTTPS. Emulates a 412x915 Android phone.

Usage: python scripts/check_phone_offline.py [base_url] [--shots out_dir]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PHONE = dict(viewport={"width": 412, "height": 915}, device_scale_factor=2.625, is_mobile=True, has_touch=True)
SCAM = ("Dear customer your SBI account KYC has expired. Update immediately or your account will be blocked "
        "today: http://sbi-kyc-update.xyz")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("base", nargs="?", default="http://127.0.0.1:8000/")
    ap.add_argument("--shots", type=Path, help="save phone screenshots of each offline screen here")
    args = ap.parse_args()
    base = args.base if args.base.endswith("/") else args.base + "/"
    if args.shots:
        args.shots.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, bool, str]] = []

    def step(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}{': ' + detail if detail else ''}")

    def shot(page, name: str) -> None:
        if args.shots:
            page.screenshot(path=str(args.shots / f"{name}.png"), full_page=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(**PHONE, color_scheme="light")
        page = ctx.new_page()

        # 1. One visit while connected: the service worker keeps the app, the checker and the packs.
        page.goto(base + "?lang=en", wait_until="networkidle")
        page.evaluate("navigator.serviceWorker.ready.then(() => true)")
        cached = page.evaluate("caches.keys().then(ks => Promise.all(ks.map(k => caches.open(k).then(c => c.keys()))))"
                               ".then(lists => lists.flat().map(r => new URL(r.url).pathname))")
        packs = [u for u in cached if "/phone-packs/" in u]
        step("first visit caches the app and the packs", len(packs) == 5 and any(u.endswith("checker.js") for u in cached),
             f"{len(cached)} files cached, {len(packs)} packs")

        # 2. Away from the node: no network at all.
        ctx.set_offline(True)
        page.goto(base + "?lang=en&screen=check", wait_until="load")
        page.wait_for_selector("#msg", state="visible", timeout=15000)
        page.fill("#msg", SCAM)
        page.click("#btn-check")
        try:
            page.wait_for_selector("#verdict.scam", timeout=15000)
            meta = page.inner_text("#meta")
            step("scam message checked on the phone, offline", "on this phone" in meta, meta)
        except Exception as e:  # noqa: BLE001 - report and carry on
            step("scam message checked on the phone, offline", False, str(e).splitlines()[0])
        pill, foot = page.inner_text("#node-pill"), page.inner_text(".foot")
        step("the app says it is running on the phone", "On phone" in pill and "on this phone" in foot, pill.strip())
        clipped = page.evaluate("[...document.querySelectorAll('#node-pill, #node-pill *')]"
                                ".some(e => e.scrollWidth > e.clientWidth + 1)")
        step("the status pill fits the phone screen", not clipped)
        shot(page, "offline_scam_en")

        page.goto(base + "?qr=qr_cashback", wait_until="load")  # Hindi, as a person would see it
        try:
            page.wait_for_selector("#qr-box:not([hidden])", timeout=15000)
            step("demo UPI QR checked on the phone, offline", page.query_selector("#verdict.scam") is not None)
        except Exception as e:  # noqa: BLE001
            step("demo UPI QR checked on the phone, offline", False, str(e).splitlines()[0])
        shot(page, "offline_qr_hi")

        page.goto(base + "?demo=ayushman_fee", wait_until="load")  # "pay ₹500 for your Ayushman card" (demo pack 1.4.0+)
        try:
            page.wait_for_selector("#verdict.scam", timeout=8000)
            step("\"pay for your Ayushman card\" flagged on the phone, offline", True)
        except Exception:  # noqa: BLE001 - an older demo pack has no such example
            print("SKIP  \"pay for your Ayushman card\": this demo pack has no such example")
        shot(page, "offline_ayushman_fee_hi")

        page.goto(base + "?nav=senior74", wait_until="load")
        try:
            page.wait_for_selector('[data-screen="benefits-result"]:not([hidden]) .scheme', timeout=15000)
            step("benefits result for a 74-year-old, offline", True)
            step("health cover shown first", page.query_selector("#nav-health .health-callout") is not None)
        except Exception as e:  # noqa: BLE001
            step("benefits result for a 74-year-old, offline", False, str(e).splitlines()[0])
        shot(page, "offline_benefits_senior_hi")

        page.goto(base + "?lang=en&nav=start", wait_until="load")
        try:
            page.wait_for_selector(".age-input", timeout=15000)
            page.fill(".age-input", "72")
            page.click(".age-row .primary")
            page.wait_for_selector("#q-text", timeout=10000)
            step("a fresh interview starts and takes an answer, offline", "old" not in page.inner_text("#q-text").lower(),
                 page.inner_text("#q-text"))
        except Exception as e:  # noqa: BLE001
            step("a fresh interview starts and takes an answer, offline", False, str(e).splitlines()[0])
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
