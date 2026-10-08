"""Build the one-page summary (docs/Sahayak_OnePager.pdf) from the benchmark results.

An A4 page for the jury: what Sahayak does, how it works, the measured evidence (read from
bench/results/*.json, like the testing report and the deck; scam tests quote their first runs), privacy, and the
team. Rows for the blind red team, the AI-model baseline and the stress test appear when their result files exist.
Rendered by Chromium (Playwright) so the Hindi is shaped correctly. Keep it to one page: check with
`pdfinfo docs/Sahayak_OnePager.pdf` after any change.

Usage: python scripts/build_onepager.py
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import docstyle as D  # noqa: E402  (Rosh 27 type and colours, as in the app)

R = lambda f: json.loads((ROOT / "bench" / "results" / f).read_text(encoding="utf-8"))  # noqa: E731
pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731
pct0 = lambda x: f"{round(100 * x)}%"  # noqa: E731


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval: sound for small samples, where a bootstrap interval can reach 100%."""
    if not n:
        return 0.0, 0.0
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return max(0.0, c - h), min(1.0, c + h)


def main() -> None:
    sb, sch, fl, lat = R("scambench_v0_test.json"), R("schemebench_v1.json"), R("voicebench_fleurs_hi.json"), R("voice_latency.json")["summary"]
    full, block = sb["systems"]["full"]["flagged"], sb["systems"]["blocklist"]["flagged"]
    scams, genuine = full["tp"] + full["fn"], full["fp"] + full["tn"]
    lo, hi = wilson(full["tp"], scams)
    ocr = R("ocrbench_v0.json") if (ROOT / "bench" / "results" / "ocrbench_v0.json").exists() else None
    signals = len(json.loads((ROOT / "packs" / "fraud.v1.json").read_text(encoding="utf-8"))["signals"])
    facts = ROOT / "docs" / "deck" / "facts_v3.json"
    tryit = json.loads(facts.read_text(encoding="utf-8")).get("tryit_url", "") if facts.exists() else ""
    tryit = tryit.removeprefix("https://").rstrip("/")
    shot = lambda f: (ROOT / "docs" / "deck" / "img" / f).as_uri()  # noqa: E731
    pub = R("public_v0.json")["first"] if (ROOT / "bench" / "results" / "public_v0.json").exists() else None
    rows = []
    if pub:  # real messages first: the number to lead with
        pg, pb = pub["systems"]["full"]["groups"]["hindi_english_hinglish"], pub["systems"]["blocklist"]["groups"]["hindi_english_hinglish"]
        rows.append(("Real messages", f"{pub['messages']} that people received, as published by the Income Tax portal, PIB Fact Check, courts "
                     f"and fact-checkers, scored once. Hindi, English, Hinglish: {pg['caught']} / {pg['scams']} scams caught "
                     f"({pct0(pg['caught'] / pg['scams'])}), {pg['false_alarm']} / {pg['genuine']} genuine flagged; keyword blocklist "
                     f"{pb['caught']} and {pb['false_alarm']}. Lower than on our own messages: the honest number"))
    rows += [
        ("Scams caught", f"{full['tp']} / {scams} ({pct(full['recall'])}; 95% Wilson CI {pct0(lo)}–{pct0(hi)}) on a frozen test split of "
                         f"{sb['n']} messages our team wrote, vs {pct(block['recall'])} for a keyword blocklist; false alarms "
                         f"{full['fp']} / {genuine} ({pct(full['false_alarm_rate'])}) vs {pct(block['false_alarm_rate'])}; "
                         f"{sb['latency_ms_full']['p50']:.0f} ms a verdict on a laptop CPU"),
    ]
    if (ROOT / "bench" / "results" / "redteam_v1_blind.json").exists():
        bl = R("redteam_v1_blind.json")["first"]
        g, gb = bl["systems"]["full"]["groups"]["hindi_english_hinglish"], bl["systems"]["blocklist"]["groups"]["hindi_english_hinglish"]
        x = bl["systems"]["full"]["groups"]["other_indian_languages"]
        x_miss = x.get("missed", 0)
        x_nc = x["scams"] - x.get("caught", 0) - x_miss
        rows.append(("Blind red team", f"{bl['messages']} messages by a separate AI model that never saw the code, scored once. Hindi, English, Hinglish: "
                     f"{g['caught']} / {g['scams']} scams caught, {g['false_alarm']} / {g['genuine']} hard genuine flagged "
                     f"(blocklist {gb['caught']} and {gb['false_alarm']}). Other languages: {x.get('caught', 0)} / {x['scams']} caught, {x_nc} "
                     f"\"could not check\", {x_miss} false green{'' if x_miss == 1 else 's'}"))
    if (ROOT / "bench" / "results" / "llm_baseline.json").exists():
        lb = R("llm_baseline.json")
        ls = lb["sets"].get("public_v0") or lb["sets"].get("redteam_v1_blind")
        if ls:
            m, s = ls["llm"], ls["sahayak"]
            rows.append(("An AI model instead?", f"{lb['model']}, zero-shot on the same {ls['n']}: {m['caught']} / {m['scams']} scams caught but "
                         f"{m['false_alarms']} / {m['genuine']} genuine flagged ({pct0(m['false_alarms'] / m['genuine'])}), "
                         f"{ls['llm_seconds']['median']} s a message on a GPU. Sahayak: {s['caught']} / {s['scams']} and "
                         f"{s['false_alarms']} / {s['genuine']} ({pct0(s['false_alarms'] / s['genuine'])}), {ls['sahayak_ms_median']} ms"))
    rows += [
        ("Scheme rules", f"{sch['rules']['agree']:,} / {sch['rules']['decisions']:,} decisions match a re-derivation by the same author "
                         f"(a second person's check is to come); median {sch['interview']['median']:g} questions, never more than {sch['interview']['max']}"),
        ("Hindi speech", f"{pct(fl['wer'])} word error on Google FLEURS Hindi ({fl['utterances']} recordings of adults reading sentences aloud), "
                         f"offline; reply audio {lat['cached']['p50']} s after the mic is released"),
    ]
    if ocr:
        rows.append(("Screenshots", f"same scam decision as the typed message on {ocr['same_flag']} / {ocr['messages']} rendered SMS screenshots, read offline"))
    rt_path = ROOT / "bench" / "results" / "redteam_v0.json"
    if rt_path.exists() and not pub:  # the team-written red team gives way to real messages, to keep one page
        red = R("redteam_v0.json")
        rt, after = red["first"]["systems"], (red.get("latest") or red["first"])["systems"]["full"]
        rows.append(("Our red team", f"{rt['full']['scams_flagged']} / {rt['full']['scams']} disguised scams flagged on the first run "
                     f"(blocklist {rt['blocklist']['scams_flagged']} / {rt['blocklist']['scams']}); "
                     f"{after['scams_flagged']} / {after['scams']} after the fixes it found"))
    if (ROOT / "bench" / "results" / "stress_v0.json").exists():
        st = R("stress_v0.json")
        n = {s["scenario"]: s["n"] for s in st["load"]}
        errors = sum(v["errors"] for s in st["load"] for v in s["endpoints"].values())
        rows.append(("Under load", f"{n.get('session', 0)} phones doing a whole visit at once, {n.get('burst', 0)} checks at once and "
                     f"{n.get('soak', 0):,} in a row: {errors} errors; {st['fuzz']['cases']} hostile inputs, "
                     f"{len(st['fuzz']['unexpected'])} unexpected answers ({st['machine'].split(',')[0]})"))
    rows.append(("Offline", "0 outbound connections or outside DNS lookups, counted live by an audit hook; a firewall blocks the rest"))
    if (ROOT / "bench" / "results" / "phone_parity.json").exists():
        ph = R("phone_parity.json")
        rows.append(("On the phone", f"the node's exact answer on {ph['fraud']['cases']:,} scam checks and {ph['navigator']['cases']:,} "
                     f"benefits cases ({ph['fraud']['mismatches'] + ph['navigator']['mismatches']} mismatches)"))
    table = "".join(f"<tr><th>{html.escape(a)}</th><td>{html.escape(b)}</td></tr>" for a, b in rows)
    docs = ROOT / "docs"
    css = f"""@page {{ size: A4; margin: 12mm 13mm; }}
{D.fonts_css(docs)}{D.BASE}
body {{ font-size: 8.6pt; line-height: 1.32; }}
h1 {{ display: flex; align-items: baseline; gap: 8px; font-size: 22pt; line-height: 1.1; margin: 0; letter-spacing: -.035em; }}
h1 .mark {{ align-self: center; }}
h1 small {{ font-size: 11pt; color: {D.LABEL2}; font-weight: 500; letter-spacing: 0; }}
.tag {{ font-size: 10.5pt; font-weight: 600; margin: 4px 0 7px; letter-spacing: -.01em; }}
h2 {{ font: 500 7.6pt/1 {D.MONO}; margin: 9px 0 4px; color: {D.TINT}; text-transform: uppercase; letter-spacing: .09em; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
.box {{ border-radius: 12px; padding: 8px 11px; background: {D.PAGE}; }}
.box b {{ color: {D.LABEL}; }}
table {{ width: 100%; border-collapse: collapse; }} th, td {{ text-align: left; vertical-align: top; padding: 2.4px 6px; border-bottom: 1px solid {D.SEP}; }}
th {{ width: 17%; color: {D.LABEL2}; font-weight: 600; }}
.shots {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 7px; }}
.shots img {{ width: 100%; border-radius: 10px; border: 1px solid {D.SEP}; height: 104px; object-fit: cover; object-position: 50% 22%; }}  /* the verdict, below the app's top bar */
ul {{ margin: 2px 0; padding-left: 16px; }} li {{ margin: 1px 0; }}
.foot {{ margin-top: 7px; font-size: 8pt; color: {D.LABEL2}; }} .foot b {{ color: {D.LABEL}; }}
"""
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{css}</style></head><body>
<h1>{D.mark(docs, "1.15em")}Sahayak <small>· सहायक · Ideas for India 2026</small></h1>
<div class="tag">An offline scam shield and benefits guide for people new to digital money, in Hindi and English, by voice or touch.</div>
<div class="cols">
 <div class="box"><b>"Is this a scam?"</b> Paste, speak, photograph or describe a message, a call or a UPI QR code. In milliseconds: Scam, Suspicious, No scam signs (never "safe"), or Could not check (a language it cannot read yet: safe-default advice, no false green). Then the reasons, what to do (money lost: call 1930; an attempt: report on Chakshu) and a complaint draft. A QR card says: scanning sends money, never brings it in.</div>
 <div class="box"><b>"What am I owed?"</b> A short spoken interview finds which of 12 central schemes a person can get, health first: Ayushman Bharat pays up to ₹5 lakh a year for hospital admission (not OPD); at 70+, the Vay Vandana card (cover shared with a 70+ spouse). Then pensions, PMSBY, PMJJBY, APY, PM-KISAN, e-Shram, PM-SYM, Jan Dhan: the papers, the office, what to say, and a printed slip with a QR for the CSC operator.</div>
</div>
<h2>How it works</h2>
<ul>
 <li><b>One node at a CSC or bank-agent counter</b> (a laptop or mini-PC). Phones join its Wi-Fi, which has no internet; the app is a cached web page, no install.</li>
 <li><b>At home, too:</b> a phone that has opened Sahayak's secure web address once (the public site today; the node's own after a one-time HTTPS setup) keeps its own scam check and benefits interview, with no node or internet.</li>
 <li><b>Named signals decide, not a model:</b> {signals} signals in a signed content pack (lookalike links, .bank.in rule, UPI "scan to receive", OTP asks, digital arrest, "pay for your Ayushman card"…), a pattern matcher and a small classifier. Vetted templates explain each verdict; an optional local LLM (off by default) may add a line only through a safety gate.</li>
 <li><b>Scheme rules as data</b>, each traced to its official page and date; yes / likely / unknown / no; asks only what can change a result.</li>
 <li><b>Offline voice</b> both ways on the node; amounts spoken as words; "I heard …, is that right?" before any answer is used.</li>
 <li><b>Operator console:</b> "Ask the agent" queue, assisted checks read aloud, case log, 58 mm slips, counters with no personal data.</li>
</ul>
<h2>Measured, not claimed</h2>
<table>{table}</table>
<div class="shots"><img src="{shot('03_result_kyc_hi.png')}"><img src="{shot('09_benefits_result_widow_hi.png')}"><img src="{shot('13_qr_cashback_hi.png')}"></div>
<h2>Privacy and safety</h2>
<ul>
 <li>Messages, voices and answers stay in the node's memory for at most 15 minutes; nothing typed or said is written to disk.</li>
 <li>Case log only with consent: no names or numbers, encrypted, deleted after 30 days, one "delete everything" button.</li>
 <li>Green means "no signs found, still verify", never "safe"; a language it cannot read gets a grey "could not check". Every amount shown comes from a signed pack. Content updates are Ed25519-signed; an altered pack is refused.</li>
</ul>
<div class="foot"><b>Team:</b> Roshan Raj, Ishmiit Singh · {f'<b>Try it:</b> {html.escape(tryit)} · ' if tryit else ''}<b>Dates:</b> prototype due 8 Oct 2026; Grand Jury Round, Delhi, 14 Oct · <b>Caveats:</b> ScamBench v0 and our red team were written by our team (optimistic); the blind set was written for the test, not received by real people; v1 adds real messages with consent; no field test with real users yet. Method and limits: docs/TESTING_REPORT.md. Hindi voices and the optional language model are licensed for non-commercial use.</div>
</body></html>"""
    out_html = docs / "onepager.html"
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
