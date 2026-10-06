"""Record short screen clips of the main flows for the demo video (docs/video/*.mp4).

Drives the running node in Chromium and records each flow at a calm pace: a scam check, the
benefits interview with its slip and a UPI QR check on a phone screen (824 x 1720), then the
operator console and the node's status page (1920 x 1080). Frames come from Chromium's screencast
at the screen's full pixel density and are encoded as H.264, which every video editor opens.
Video only: the voice cannot be captured here, so record audio with a real phone.

Usage: python scripts/record_demo_clips.py [base_url]   (the node must be running; console PIN 246810
       unless SAHAYAK_CONSOLE_PIN says otherwise)
"""
from __future__ import annotations

import base64
import io
import os
import sys
import time
from pathlib import Path

import av
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "video"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PIN = os.environ.get("SAHAYAK_CONSOLE_PIN", "246810")
PHONE = dict(viewport={"width": 412, "height": 860}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESKTOP = dict(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)
FPS = 25
STEP = 900  # ms between taps: slow enough to follow


class Screencast:
    """Chromium screencast frames of one page, re-timed to a steady frame rate and encoded as H.264."""

    def __init__(self, page, size: tuple[int, int]):
        self.size, self.frames = size, []
        self.cdp = page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._frame)
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": size[0], "maxHeight": size[1]})

    def _frame(self, params: dict) -> None:
        self.frames.append((time.time(), base64.b64decode(params["data"])))
        self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})

    def save(self, path: Path) -> float:
        self.cdp.send("Page.stopScreencast")
        end, t0 = time.time(), self.frames[0][0]
        with av.open(str(path), "w", options={"movflags": "faststart"}) as out:
            stream = out.add_stream("libx264", rate=FPS, options={"crf": "20", "preset": "medium"})
            stream.width, stream.height, stream.pix_fmt = *self.size, "yuv420p"
            i, shown, image = 0, -1, None
            for n in range(int((end - t0) * FPS)):
                while i + 1 < len(self.frames) and self.frames[i + 1][0] <= t0 + n / FPS:
                    i += 1
                if i != shown:  # the screen changed: decode the new frame once
                    shown, image = i, Image.open(io.BytesIO(self.frames[i][1])).convert("RGB")
                    if image.size != self.size:
                        image = image.resize(self.size, Image.LANCZOS)
                frame = av.VideoFrame.from_image(image)
                frame.pts = n
                out.mux(stream.encode(frame))
            out.mux(stream.encode())
        return end - t0


def scroll(page, total: int, step: int = 220) -> None:
    for _ in range(0, total, step):
        page.mouse.wheel(0, step)
        page.wait_for_timeout(260)


def clip(browser, name: str, url: str, flow, desktop: bool = False) -> None:
    opts = DESKTOP if desktop else PHONE
    ctx = browser.new_context(**opts, service_workers="block")
    page = ctx.new_page()
    page.goto(f"{BASE}{url}", wait_until="networkidle")  # recording starts on a loaded page, not a blank one
    vp, dpr = opts["viewport"], opts["device_scale_factor"]
    cast = Screencast(page, (int(vp["width"] * dpr), int(vp["height"] * dpr)))
    page.wait_for_timeout(STEP)
    flow(page)
    page.wait_for_timeout(1200)
    seconds = cast.save(OUT / f"{name}.mp4")
    ctx.close()
    print(f"{name}.mp4  {seconds:.0f} s")


def scam_check(page):
    page.click(".tile-shield")
    page.wait_for_selector("#examples .chip")
    page.wait_for_timeout(STEP)
    page.click("#examples .chip >> nth=0")
    page.wait_for_selector("#verdict.scam")
    page.wait_for_timeout(2 * STEP)
    scroll(page, 1400)
    page.click("#btn-complaint")
    page.wait_for_timeout(2 * STEP)


def benefits(page):
    page.wait_for_timeout(STEP)
    page.click("#btn-nav-start")
    page.wait_for_selector(".age-input")
    page.wait_for_timeout(STEP)
    page.type(".age-input", "67", delay=200)
    page.click(".age-row .primary")
    page.wait_for_selector(".opt.toggle")
    page.wait_for_timeout(STEP)
    page.click(".opt.toggle >> nth=0")
    page.wait_for_timeout(STEP)
    page.click(".q-body .cta-row .primary")
    for nth in (0, 0, 5):  # Antyodaya card, has a bank account, not working
        page.wait_for_timeout(STEP)
        page.click(f".opts .opt >> nth={nth}")
    page.wait_for_selector('[data-screen="benefits-result"]:not([hidden]) .scheme')
    page.wait_for_timeout(2 * STEP)
    page.click(".g-likely .scheme >> nth=0 >> summary")
    page.wait_for_timeout(STEP)
    scroll(page, 1200)
    page.click("#btn-slip")
    page.wait_for_timeout(STEP)
    scroll(page, 900)


def qr(page):
    page.click(".modes label:has(input[value='qr'])")
    page.wait_for_selector("#qr-examples .chip")
    page.wait_for_timeout(STEP)
    page.click("#qr-examples .chip >> nth=0")
    page.wait_for_selector("#qr-box:not([hidden])")
    page.wait_for_timeout(2 * STEP)
    scroll(page, 900)


def console(page):
    # a citizen asks for the agent from a phone (another tab) while the operator logs in
    phone = page.context.new_page()
    phone.goto(f"{BASE}/?demo=otp_call", wait_until="networkidle")
    phone.wait_for_selector("#verdict.scam")
    phone.click("#btn-agent-check")
    phone.close()
    page.wait_for_selector("#c-login:not([hidden])")
    page.type("#c-pin", PIN, delay=150)
    page.click("#c-login-form button")
    page.wait_for_selector("#c-queue li .ticket")
    page.wait_for_timeout(2 * STEP)
    page.click("#c-queue li >> nth=-1 >> button")
    page.wait_for_selector("#c-serving:not([hidden]) .verdict")
    page.wait_for_timeout(STEP)
    scroll(page, 900)
    page.click(".c-nav button[data-tab='counters']")
    page.wait_for_timeout(2 * STEP)
    page.click(".c-nav button[data-tab='reference']")
    page.wait_for_timeout(2 * STEP)


def node(page):
    page.wait_for_selector("#nd-packs tr")
    page.wait_for_timeout(4000)
    scroll(page, 800)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        clip(b, "1_scam_check_hi", "/?lang=hi", scam_check)
        clip(b, "2_benefits_interview_hi", "/?screen=benefits&lang=hi", benefits)
        clip(b, "3_upi_qr_check_hi", "/?screen=check&lang=hi", qr)
        clip(b, "4_operator_console", "/app/console.html", console, desktop=True)
        clip(b, "5_node_zero_egress", "/app/node.html", node, desktop=True)
        b.close()


if __name__ == "__main__":
    main()
