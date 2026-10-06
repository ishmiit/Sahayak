"""Build the one-page summary (docs/Sahayak_OnePager.pdf) from the benchmark results.

An A4 page for the jury: what Sahayak does, how it works, the measured evidence (read from
bench/results/*.json, like the testing report and the deck), privacy, and the team. Rendered by
Chromium (Playwright) so the Hindi is shaped correctly.

Usage: python scripts/build_onepager.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = lambda f: json.loads((ROOT / "bench" / "results" / f).read_text(encoding="utf-8"))  # noqa: E731
pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731


def main() -> None:
    sb, sch, fl, lat = R("scambench_v0_test.json"), R("schemebench_v1.json"), R("voicebench_fleurs_hi.json"), R("voice_latency.json")["summary"]
    full, block, ci = sb["systems"]["full"]["flagged"], sb["systems"]["blocklist"]["flagged"], sb["systems"]["full"]["flagged_ci95"]
    ocr = R("ocrbench_v0.json") if (ROOT / "bench" / "results" / "ocrbench_v0.json").exists() else None
    shot = lambda f: (ROOT / "docs" / "deck" / "img" / f).as_uri()  # noqa: E731
    rows = [
        ("Scams caught", f"{pct(full['recall'])} (95% CI {pct(ci['recall'][0])}–{pct(ci['recall'][1])}) vs {pct(block['recall'])} for a keyword blocklist; false alarms {pct(full['false_alarm_rate'])} vs {pct(block['false_alarm_rate'])}"),
        ("Verdict time", f"{sb['latency_ms_full']['p50']:.0f} ms median on a laptop CPU"),
        ("Scheme rules", f"{sch['rules']['agree']:,} / {sch['rules']['decisions']:,} decisions match an independent re-derivation; median {sch['interview']['median']:g} questions, never more than {sch['interview']['max']}"),
        ("Hindi speech", f"{pct(fl['wer'])} word error on Google FLEURS Hindi ({fl['utterances']} recordings); reply audio {lat['cached']['p50']} s after the mic is released"),
    ]
    if ocr:
        rows.append(("Screenshots", f"same scam decision as the typed message on {ocr['same_flag']} / {ocr['messages']} rendered SMS screenshots, read offline"))
    rt_path = ROOT / "bench" / "results" / "redteam_v0.json"
    if rt_path.exists():
        red = R("redteam_v0.json")
        rt, after = red["first"]["systems"], (red.get("latest") or red["first"])["systems"]["full"]
        rows.append(("Red team", f"{rt['full']['scams_flagged']} / {rt['full']['scams']} disguised scams flagged on the first run "
                     f"(blocklist {rt['blocklist']['scams_flagged']} / {rt['blocklist']['scams']}); "
                     f"{after['scams_flagged']} / {after['scams']} after the fixes it found"))
    rows.append(("Offline", "0 outbound connections or outside DNS lookups by the node, counted live by an audit hook; firewall blocks the rest"))
    table = "".join(f"<tr><th>{html.escape(a)}</th><td>{html.escape(b)}</td></tr>" for a, b in rows)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 12mm 13mm; }}
body {{ font-family: "Segoe UI", "Nirmala UI", sans-serif; color: #1b1f1d; font-size: 9.4pt; line-height: 1.34; margin: 0; }}
h1 {{ font-size: 22pt; margin: 0; color: #0e7c57; }} h1 small {{ font-size: 12pt; color: #4b524e; font-weight: 600; }}
.tag {{ font-size: 11pt; font-weight: 700; margin: 2px 0 8px; }}
h2 {{ font-size: 10.5pt; margin: 9px 0 4px; color: #0e7c57; text-transform: uppercase; letter-spacing: .04em; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.box {{ border: 1px solid #d9d3c6; border-radius: 8px; padding: 7px 10px; background: #faf8f3; }}
.box b {{ color: #0e7c57; }}
table {{ width: 100%; border-collapse: collapse; }} th, td {{ text-align: left; vertical-align: top; padding: 3px 6px; border-bottom: 1px solid #e2ddd2; }}
th {{ width: 22%; color: #4b524e; }}
.shots {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }} .shots img {{ width: 100%; border-radius: 6px; border: 1px solid #d9d3c6; height: 172px; object-fit: cover; object-position: top; }}
ul {{ margin: 2px 0; padding-left: 16px; }} li {{ margin: 1px 0; }}
.foot {{ margin-top: 8px; font-size: 8.5pt; color: #4b524e; }}
</style></head><body>
<h1>Sahayak <small>· सहायक · Ideas for India 2026</small></h1>
<div class="tag">An offline scam shield and benefits guide for people new to digital money, in Hindi and English, by voice or touch.</div>
<div class="cols">
 <div class="box"><b>"Is this a scam?"</b> Paste, speak, photograph or describe a message, a call or a UPI QR code. A verdict in milliseconds, the three reasons behind it, what to do next, and a ready-to-file 1930 complaint. A QR card always says: scanning sends money, it never brings money in.</div>
 <div class="box"><b>"What am I owed?"</b> A short spoken interview finds which of 12 central schemes (pensions, PMSBY, PMJJBY, APY, PM-KISAN, PM-JAY 70+, e-Shram, PM-SYM, Jan Dhan) a person can get, with the papers, the office, what to say at the counter, and a printed slip with a QR for the CSC operator.</div>
</div>
<h2>How it works</h2>
<ul>
 <li><b>One node at a CSC or bank-agent counter</b> (a laptop or mini-PC). Phones join its Wi-Fi, which has no internet; the app is a cached web page, no install.</li>
 <li><b>Named signals decide, not a model:</b> 51 signals in a signed content pack (lookalike links, .bank.in rule, UPI "scan to receive", OTP asks, digital arrest…), a pattern matcher and a small classifier. Vetted templates explain each verdict; an optional local LLM may add a line only through a safety gate (off in the demo).</li>
 <li><b>Scheme rules as data</b>, each traced to its official page and date; answers with yes / likely / unknown / no, asking only questions that can still change the result.</li>
 <li><b>Offline voice</b> both ways on the node; amounts spoken as words; "I heard …, is that right?" before any answer is used.</li>
 <li><b>An operator console:</b> "Ask the agent" queue, assisted checks read aloud, consented encrypted case log, 58 mm slips, impact counters with no personal data.</li>
</ul>
<h2>Measured, not claimed</h2>
<table>{table}</table>
<div class="shots"><img src="{shot('03_result_kyc_hi.png')}"><img src="{shot('09_benefits_result_widow_hi.png')}"><img src="{shot('13_qr_cashback_hi.png')}"></div>
<h2>Privacy and safety</h2>
<ul>
 <li>Messages, voices and answers stay in the node's memory for at most 15 minutes; nothing typed or said is written to disk.</li>
 <li>Case log only with consent, no names or numbers, encrypted, deleted after 30 days; one "delete everything" button. Counters hold counts only.</li>
 <li>Green means "no signs found, still verify", never "safe". Every amount shown comes from a signed pack. Content updates are Ed25519-signed; an altered pack is refused.</li>
</ul>
<div class="foot"><b>Team:</b> Roshan Raj, Ishmiit Singh · <b>Caveats:</b> ScamBench v0 was written by our team (optimistic); v1 adds real messages with consent. Full method and limits: docs/TESTING_REPORT.md. Hindi voices and the optional language model are licensed for non-commercial use.</div>
</body></html>"""
    out_html = ROOT / "docs" / "onepager.html"
    out_html.write_text(page, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(out_html.as_uri(), wait_until="load")
        pg.pdf(path=str(ROOT / "docs" / "Sahayak_OnePager.pdf"), format="A4", print_background=True,
               margin={"top": "12mm", "bottom": "12mm", "left": "13mm", "right": "13mm"})
        b.close()
    print(f"wrote {ROOT / 'docs' / 'Sahayak_OnePager.pdf'}")


if __name__ == "__main__":
    main()
