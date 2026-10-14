"""Check every display language in a phone browser, and keep a screenshot of each screen.

Builds nothing: point it at a stand-alone build (python scripts/build_tryit.py <dir>). For each language in
web/i18n/index.json it opens three screens at phone size (412 x 915, true mobile emulation): home, the fake KYC
SMS verdict (?demo=kyc_hi) and the 74-year-old's benefits result (?nav=senior74). Each must load with no script
error, no horizontal scroll, no "undefined" or "null" on screen, the page's lang and dir set, and the verdict and
scheme text in the language (not left in English). It also opens the language list from the top bar and switches
language with it. Exit code 1 on any failure.

  python scripts/i18n_screens.py <tryit_dir> [out_dir] [--langs ta,ur,...]

Needs Playwright with Chromium (requirements-dev.txt). Indic and Perso-Arabic fonts must be installed for the
screenshots to show real letters (on Debian or Ubuntu: apt-get install fonts-noto-core).
"""
from __future__ import annotations

import functools
import http.server
import json
import re
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
LATIN = re.compile(r"[A-Za-z]")


def serve(directory: Path) -> tuple[socketserver.TCPServer, int]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:  # noqa: D401 - keep the report readable
            pass

    handler = functools.partial(Quiet, directory=str(directory))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def latin_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(1 for c in letters if LATIN.match(c)) / max(1, len(letters))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    site = Path(argv[0])
    out = Path(argv[1]) if len(argv) > 1 and not argv[1].startswith("--") else ROOT / "dist" / "i18n_screens"
    out.mkdir(parents=True, exist_ok=True)
    index = json.loads((site / "app" / "i18n" / "index.json").read_text(encoding="utf-8"))
    codes = [x["code"] for x in index]
    if "--langs" in argv:
        codes = argv[argv.index("--langs") + 1].split(",")
    httpd, port = serve(site)
    base = f"http://127.0.0.1:{port}/"
    failures: list[str] = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:  # noqa: BLE001 - a pre-installed Chromium outside Playwright's own folder
            browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        for code in codes:
            meta = next(x for x in index if x["code"] == code)
            for name, query, ready in (("home", "", "[data-screen=home]:not([hidden])"),
                                       ("scam", "&demo=kyc_hi", "[data-screen=result]:not([hidden])"),
                                       ("benefits", "&nav=senior74", "[data-screen=benefits-result]:not([hidden])")):
                ctx = browser.new_context(**{**p.devices["Pixel 7"], "viewport": {"width": 412, "height": 915}}, locale="en-IN")
                page = ctx.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                # Chrome's note that it held back the Scam buzz before the first tap is not a script error
                page.on("console", lambda m: errors.append(m.text)
                        if m.type == "error" and "navigator.vibrate" not in m.text else None)
                page.goto(f"{base}?lang={code}{query}")
                try:
                    page.wait_for_selector(ready, timeout=15000)
                    page.wait_for_function(f"document.documentElement.lang === {json.dumps(code)}", timeout=15000)
                    page.wait_for_timeout(700)  # the screen's fade-in, and a re-render once the language arrived
                except Exception as e:  # noqa: BLE001
                    failures.append(f"{code} {name}: did not open ({e.__class__.__name__})")
                    ctx.close()
                    continue
                shown = page.evaluate("document.querySelector('main').innerText")
                facts = page.evaluate("""() => ({dir: document.documentElement.dir,
                    wide: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
                    label: (document.querySelector('.v-label') || {}).textContent || '',
                    headline: (document.querySelector('#headline') || {}).textContent || '',
                    action: (document.querySelector('#actions li span') || {}).textContent || '',
                    scheme: (document.querySelector('.hc-name') || {}).textContent || ''})""")
                problems = []
                if errors:
                    problems.append(f"script errors: {errors[:2]}")
                if facts["wide"]:
                    problems.append("horizontal scroll")
                if re.search(r"\bundefined\b|\bnull\b", shown):
                    problems.append("'undefined' or 'null' on screen")
                if facts["dir"] != ("rtl" if meta["dir"] == "rtl" else "ltr"):
                    problems.append(f"dir is {facts['dir']}")
                if code != "en":
                    checks = {"scam": ("label", "headline", "action"), "benefits": ("scheme",)}.get(name, ())
                    for key in checks:
                        if not facts[key].strip() or latin_share(facts[key]) > 0.5:
                            problems.append(f"{key} not translated: {facts[key][:60]!r}")
                page.screenshot(path=str(out / f"{code}_{name}.png"), full_page=True)
                if problems:
                    failures.append(f"{code} {name}: " + "; ".join(problems))
                ctx.close()
            print(f"{code}: {'ok' if not any(f.startswith(code + ' ') for f in failures) else 'FAILED'}")
        # The language list: open it from the top bar and switch to the first other language, then back to Hindi.
        ctx = browser.new_context(**{**p.devices["Pixel 7"], "viewport": {"width": 412, "height": 915}})
        page = ctx.new_page()
        page.goto(base)
        page.wait_for_selector("[data-screen=home]:not([hidden])")
        page.click("#lang-toggle")
        page.wait_for_selector("#lang-sheet:not([hidden]) .lang-opt")
        page.screenshot(path=str(out / "picker.png"), full_page=False)
        pick = next((c for c in codes if c not in ("hi", "en")), "en")
        page.click(f'.lang-opt[lang="{pick}"]')
        page.wait_for_function(f"document.documentElement.lang === {json.dumps(pick)}", timeout=10000)
        try:  # the sheet slides away first (a third of a second)
            page.wait_for_selector("#lang-sheet", state="hidden", timeout=3000)
        except Exception:  # noqa: BLE001
            failures.append("picker: the list stayed open after choosing")
        page.click("#lang-toggle")
        page.click('.lang-opt[lang="hi"]')
        page.wait_for_function("document.documentElement.lang === 'hi'", timeout=10000)
        if page.evaluate("document.documentElement.dir") != "ltr":
            failures.append("picker: Hindi did not return to left-to-right")
        ctx.close()
        browser.close()
    httpd.shutdown()
    print(f"{len(codes)} languages, {len(failures)} failures; screenshots in {out}")
    for f in failures:
        print("  -", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
