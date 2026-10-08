"""Build docs/TESTING_REPORT.md from the benchmark results, so the report never drifts from them.

Reads bench/results/*.json (written by the bench scripts), runs the call-description set and
runs the automated tests (or reads a saved run), then writes one report for the jury: what was tested, how, the
numbers with their uncertainty, and what each number does not show.

Usage: python scripts/build_testing_report.py [pytest_log]   (a saved `python -m pytest` output, to skip the re-run)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "bench" / "results"


def load(name: str) -> dict | None:
    f = RESULTS / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def pct(x: float, digits: int = 1) -> str:
    return f"{100 * x:.{digits}f}%"


def ci(pair) -> str:
    return f"{pct(pair[0])}–{pct(pair[1])}"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval: sound for small samples, where a bootstrap interval can touch 100%."""
    if not n:
        return 0.0, 0.0
    p = k / n
    centre, half = (p + z * z / (2 * n)) / (1 + z * z / n), z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def frac(k: int, n: int) -> str:
    return f"{k} / {n} ({100 * k / n:.0f}%)" if n else "0 / 0"


def blind_section(rb: dict) -> list[str]:
    f, b = rb["first"]["systems"]["full"]["groups"], rb["first"]["systems"]["blocklist"]["groups"]
    o, bo, x = f["hindi_english_hinglish"], b["hindi_english_hinglish"], f["other_indian_languages"]
    x_nc_scam = sum(1 for i in rb["first"]["systems"]["full"]["not_checked"] if i["label"] == "scam")
    out = [
        "### Blind red team v1",
        "",
        f"{rb['first']['messages']} messages written on 6–7 Oct 2026 by a separate AI model working blind: it never saw Sahayak's code, rules, packs or test "
        "sets, from 2025–26 advisories by I4C, police, banks and news reports: scams old and new (digital arrest, \"wrong number\" "
        "investment openers, call forwarding by USSD code, eSIM swap, e-challan and wedding-invitation APKs, voter-roll OTPs) and "
        "deliberately hard genuine messages (the delivery OTP you do give at the door, the government's own \"there is no digital "
        f"arrest\" message, bank alerts). {o['scams'] + x['scams']} scams, {o['genuine'] + x['genuine']} genuine; "
        f"{x['scams'] + x['genuine']} of them in Indian languages Sahayak does not read yet. Scored once on "
        f"{rb['first']['date']} (fraud pack {rb['first']['packs']['fraud']}, on the dev Mac), before anyone on the team read them.",
        "",
        "| | Scams caught (95% Wilson CI) | False alarms on genuine (95% Wilson CI) |",
        "| --- | --- | --- |",
        f"| Sahayak, Hindi / English / Hinglish | {frac(o.get('caught', 0), o['scams'])} ({ci(o['caught_ci'])}) | "
        f"{frac(o.get('false_alarm', 0), o['genuine'])} ({ci(o['false_alarm_ci'])}) |",
        f"| Keyword blocklist, same messages | {frac(bo.get('caught', 0), bo['scams'])} | {frac(bo.get('false_alarm', 0), bo['genuine'])} |",
        f"| Sahayak, other Indian languages | {frac(x.get('caught', 0), x['scams'])} caught; {x_nc_scam} \"could not check\"; "
        f"{x.get('missed', 0)} given a false green | {frac(x.get('false_alarm', 0), x['genuine'])} |",
        "",
        "On the first run Sahayak missed scams that arrive as a story with no link, number or code yet (a matrimonial match moving "
        "to \"gold trading\", a medical-charity appeal, a flat rented by an \"officer\" who cannot show it) and flagged genuine "
        "messages that look like scams on purpose (a delivery OTP given at the door, a gas-booking code, salary and debit alerts "
        "with an \"SMS BLOCK\" line, job-interview calls, family money requests). Every miss is listed in "
        "`bench/results/redteam_v1_blind.md`.",
        "",
    ]
    if rb.get("latest"):
        lo = rb["latest"]["systems"]["full"]["groups"]["hindi_english_hinglish"]
        out += [f"**After the first run** (post-freeze log in the results file): {' '.join(rb.get('notes', []))} Re-scored on fraud "
                f"pack {rb['latest']['packs']['fraud']}: {frac(lo.get('caught', 0), lo['scams'])} scams caught and "
                f"{frac(lo.get('false_alarm', 0), lo['genuine'])} false alarms in Hindi / English / Hinglish. These messages "
                "shaped the fixes, so this is not an unbiased test; the first run stays the number to quote.", ""]
    return out + ["Reproduce: `python bench/redteam/build_redteam_v1.py`, `python bench/eval_redteam_v1.py --report`.", ""]


def public_section(pb: dict) -> list[str]:
    f, b = pb["first"]["systems"]["full"]["groups"], pb["first"]["systems"]["blocklist"]["groups"]
    o, bo, v = f["hindi_english_hinglish"], b["hindi_english_hinglish"], f["verbatim_only"]
    x = f["other_indian_languages"]
    out = [
        "### Real published messages: PublicBench v0",
        "",
        f"The first set the team did not write: {pb['first']['messages']} messages people in India actually received "
        f"({f['all']['scams']} scams, {f['all']['genuine']} genuine), as published by the Income Tax portal's archive of its own "
        "SMS, PIB Fact Check, consumer-court orders that quote bank SMS, and fact-checkers and newspapers, 2023–2026; "
        "collected by an AI research agent that never saw the code, phone numbers replaced (`bench/public/DATA_CARD.md`). Scored once on "
        f"{pb['first']['date']} (fraud pack {pb['first']['packs']['fraud']}), before anyone read an error.",
        "",
        "| | Scams caught (95% Wilson CI) | Genuine flagged (95% Wilson CI) |",
        "| --- | --- | --- |",
        f"| Sahayak, Hindi / English / Hinglish | {frac(o.get('caught', 0), o['scams'])} ({ci(o['caught_ci'])}) | "
        f"{frac(o.get('false_alarm', 0), o['genuine'])} ({ci(o['false_alarm_ci'])}) |",
        f"| Keyword blocklist, same messages | {frac(bo.get('caught', 0), bo['scams'])} | {frac(bo.get('false_alarm', 0), bo['genuine'])} |",
        f"| Sahayak, word-for-word messages only | {frac(v.get('caught', 0), v['scams'])} | {frac(v.get('false_alarm', 0), v['genuine'])} |",
        f"| Sahayak, other Indian languages | {x.get('caught', 0)} caught, {x.get('not_checked', 0)} \"could not check\", "
        f"{x.get('missed', 0)} false greens | – |",
        "",
        "Real messages are harder than the team's own: the same engine caught 92% of ScamBench's test scams. What it missed "
        "on the first run: police and court-notice threats that ask for nothing yet, \"letters of guarantee\" from \"RBI\" "
        "asking for a tax, investment-group openers, \"I sent you a message by mistake, forward it\". What it flagged: "
        "genuine notices that use a scam's own words (an SBI maintenance notice, a prepaid-power warning, Income Tax "
        "\"urgent\" reminders).",
        "",
        "**Method for what came next.** The set is split in two by a fixed hash of each id, made before anyone read an "
        "error. Fixes may learn from the dev half only; the test half's messages stay unread, so its score after the fixes "
        "is a fair estimate of the improvement.",
        "",
    ]
    if pb.get("latest"):
        lt, ft = pb["latest"]["systems"]["full"]["groups"]["test_half"], pb["first"]["systems"]["full"]["groups"]["test_half"]
        la = pb["latest"]["systems"]["full"]["groups"]["hindi_english_hinglish"]
        out += [f"**After the fixes.** {' '.join(pb.get('notes', []))} On the "
                f"unread test half, scams caught {frac(ft.get('caught', 0), ft['scams'])} → {frac(lt.get('caught', 0), lt['scams'])}, "
                f"genuine flagged {frac(ft.get('false_alarm', 0), ft['genuine'])} → {frac(lt.get('false_alarm', 0), lt['genuine'])}. "
                f"All Hindi / English / Hinglish messages: {frac(la.get('caught', 0), la['scams'])} caught, "
                f"{frac(la.get('false_alarm', 0), la['genuine'])} flagged (the dev half informed the fixes). The first run stays "
                "the number to quote.", ""]
    return out + ["Reproduce: `python bench/eval_public_v0.py --report`; every item's source is in "
                  "`bench/public/public_messages_v0.provenance.tsv`.", ""]


def llm_section(lb: dict) -> list[str]:
    out = [
        "### Why not just ask an AI model?",
        "",
        f"The first-round proposal had a large language model decide. The prototype measures that road: {lb['model']} (the largest "
        "model that ran at a usable speed on the team's laptop), zero-shot, temperature 0, one fixed prompt, on the same messages, "
        f"through Ollama on {lb['hardware']} (its GPU; a CSC node's CPU would be several times slower).",
        "",
        "| Set | System | Scams caught | False alarms on genuine | Time per message |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, res in lb["sets"].items():
        l, s = res["llm"], res["sahayak"]
        label = {"scambench_v0_test": "ScamBench v0 test split", "redteam_v1_blind": "Blind red team v1",
                 "public_v0": "PublicBench v0 (real messages)"}.get(name, name)
        out.append(f"| {label} | {lb['model']} | {frac(l['caught'], l['scams'])} | {frac(l['false_alarms'], l['genuine'])} | "
                   f"median {res['llm_seconds']['median']} s |")
        out.append(f"| {label} | Sahayak | {frac(s['caught'], s['scams'])} | {frac(s['false_alarms'], s['genuine'])} | "
                   f"median {res['sahayak_ms_median']} ms |")
    return out + ["", "Reproduce: `ollama pull " + lb["model"] + "`, `python bench/eval_llm_baseline.py --report`; every answer "
                  "and the model's one-line reason are in `bench/results/llm_baseline.json`.", ""]


def stress_section(st: dict) -> list[str]:
    rows = []
    for s in st["load"]:
        for ep, v in s["endpoints"].items():
            if ep in ("check", "speech (new)", "recognise", "nav next"):
                rows.append(f"| {s['scenario']} × {s['n']} | {ep} | {v['p50_ms']} ms | {v['p95_ms']} ms | {v['max_ms']} ms | {v['errors']} |")
    f, ph = st["fuzz"], st.get("phone")
    out = [
        "## 6. Under load and under attack",
        "",
        f"`bench/stress/run_stress.py` starts a node and plays a busy counter against it ({st['machine']}): 30 phones doing a whole "
        "visit at once, 300 checks in the same instant, 20 new sentences to speak at once, 10 recordings at once, and 5,000 checks "
        "in a row while the node's memory is watched.",
        "",
        "| Scenario | Request | Median | 95th percentile | Slowest | Errors |",
        "| --- | --- | --- | --- | --- | --- |",
        *rows,
        "",
        f"Hostile input ({f['cases']} cases: Unicode soup, malformed and 20,000-deep JSON, broken audio and images, a 144-megapixel "
        "PNG packed into 140 KB, 200 MB request bodies, path traversal, console calls without a login, PIN guessing): "
        f"{len(f['unexpected'])} unexpected answers, {f['path_leaks']} files leaked, and the node kept answering. The console locks "
        f"after {f['pin_lockout_after']} wrong PINs.",
        "",
        "What the first run of this test found, and what changed: live speech for many phones queued behind one voice engine "
        "(now a small pool that grows only while phones wait, and one synthesis shared by every phone asking for the same "
        "sentence; a phone that waits more than 4 s reads the screen in its own voice); an empty photo crashed the QR and "
        "screenshot readers; a 0.9 MB image that unpacks to 900 MB took the node from 0.7 to 1.8 GB of memory (now refused from "
        "its header); and request bodies were read whole before their size was checked (now refused unread, by declared or "
        "streamed size).",
        "",
    ]
    if ph:
        out += [f"**A low-end phone** (Chromium with the CPU {ph['cpu_slowdown']}× slower and a slow 3G link): first visit "
                f"{ph['first_visit_s']} s, ready to work offline after {ph['offline_ready_s']} s; offline, the first scam check took "
                f"{ph['first_check_s']} s from tap to verdict (it starts the engine) and the next {ph['second_check_s']} s; a "
                f"benefits result {ph['benefits_result_s']} s. Safari's engine (WebKit, as an iPhone 13) runs every flow, on the node "
                "and stand-alone (`scripts/check_phone_offline.py --browser webkit`).", ""]
    return out


def call_bench() -> tuple[int, int, int, int]:
    from sahayak.fraud import check_message
    rows = [json.loads(line) for line in (ROOT / "bench" / "callbench" / "calls_v0.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    scams = [r for r in rows if r["label"] == "scam"]
    genuine = [r for r in rows if r["label"] == "genuine"]
    flagged = lambda r: check_message(r["text"], input_type="call")["verdict"] in ("scam", "suspicious")  # noqa: E731
    return sum(map(flagged, scams)), len(scams), sum(not flagged(r) for r in genuine), len(genuine)


def sender_stripped() -> tuple[int, int, int]:
    """Genuine ScamBench messages, checked with their sender removed (as when a person pastes only the text):
    how many are flagged with the sender, and without it."""
    from sahayak.fraud import check_message
    rows = [json.loads(line) for line in (ROOT / "bench" / "scambench" / "scambench_v0.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    genuine = [r for r in rows if r["label"] == "genuine"]
    flag = lambda r, snd: check_message(r["text"], sender=snd, input_type=r.get("input_type", "text"))["verdict"] in ("scam", "suspicious")  # noqa: E731
    return sum(flag(r, r.get("sender")) for r in genuine), sum(flag(r, None) for r in genuine), len(genuine)


def test_result(log: Path | None = None) -> str:
    """The outcome of a real test run: the given pytest log, or a fresh run (a few minutes)."""
    out = log.read_text(encoding="utf-8", errors="replace") if log else subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:warnings"], cwd=ROOT, capture_output=True, text=True).stdout
    counts = {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|skipped|errors?)\b", out.strip().splitlines()[-1])}
    passed, failed = counts.get("passed", 0), counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)
    text = f"{passed} tests pass" if not failed else f"{passed} of {passed + failed} tests pass"
    return text + (f", {counts['skipped']} skipped" if counts.get("skipped") else "")


def redteam_section(first: dict, latest: dict | None) -> list[str]:
    f, b = first["full"], first["blocklist"]
    out = [
        "### Red team v0",
        "",
        f"74 messages written to get past Sahayak: {f['scams']} known scams each disguised with one technique (hidden characters, "
        "spaced, look-alike or digit-for-letter spelling, links written in words or behind a short link, a warning wrapped around "
        "the ask, a spoofed bank sender, no link at all, newer scam types) and "
        f"{f['genuine']} genuine messages that share words with scams. Scored once before any change: Sahayak flagged "
        f"{f['scams_flagged']} / {f['scams']} disguised scams and left {f['genuine_left_alone']} / {f['genuine']} genuine messages "
        f"alone; the keyword blocklist {b['scams_flagged']} / {b['scams']} and {b['genuine_left_alone']} / {b['genuine']}.",
        "",
    ]
    if latest:
        out += [f"The misses were then fixed (digits read as letters, written-out links undone, words people use instead of "
                f"\"OTP\"); re-scored: {latest['scams_flagged']} / {latest['scams']} and {latest['genuine_left_alone']} / "
                f"{latest['genuine']}, with ScamBench unchanged. Two genuine messages stay flagged by design: a shop offer on a "
                "short link, and a debit alert asking you to call or SMS a mobile number. The re-score is not an unbiased "
                "test; the first run is the number to quote.", ""]
    return out + ["Reproduce: `python bench/build_redteam.py`, `python bench/eval_redteam.py`; details in "
                  "`bench/results/redteam_v0.md`.", ""]


def main(log: Path | None = None) -> None:
    sb, sch, fleurs, lat, ocr = (load("scambench_v0_test.json"), load("schemebench_v1.json"), load("voicebench_fleurs_hi.json"),
                                 load("voice_latency.json"), load("ocrbench_v0.json"))
    rt = load("redteam_v0.json")
    phone, field = load("phone_parity.json"), load("field_v0.json")
    rb, lb, st = load("redteam_v1_blind.json"), load("llm_baseline.json"), load("stress_v0.json")
    pb = load("public_v0.json")
    rt1 = rt["first"]["systems"] if rt else None
    rtl = rt["latest"]["systems"]["full"] if rt and rt.get("latest") else None
    calls = call_bench()
    stripped = sender_stripped()
    tests = test_result(log)
    full, block = sb["systems"]["full"]["flagged"], sb["systems"]["blocklist"]["flagged"]
    full_ci, block_ci = sb["systems"]["full"]["flagged_ci95"], sb["systems"]["blocklist"]["flagged_ci95"]
    lat_s = lat["summary"] if lat else None
    ex = sch.get("exhaustive", {})

    lines = [
        "# Sahayak testing report",
        "",
        f"Prototype for Ideas for India 2026 · generated {dt.date.today().isoformat()} by `scripts/build_testing_report.py` from the "
        "result files in `bench/results/`. Every number below can be reproduced with the command given in its section. "
        "The benchmarks of 2–6 Oct ran on a 4-core laptop CPU (Intel i5-10210U, no GPU) with the internet off; the outside "
        "tests of 7 Oct (real messages, blind red team, the language-model baseline, the stress test) ran on an Apple M3 "
        "Mac, and each of those sections says so.",
        "",
        "## At a glance",
        "",
        "| Area | Result | How it was measured |",
        "| --- | --- | --- |",
        f"| Scam detection | {full['tp']} / {full['tp'] + full['fn']} scams caught, recall {pct(full['recall'])} (95% Wilson CI "
        f"{ci(wilson(full['tp'], full['tp'] + full['fn']))}); false alarms {full['fp']} / {full['fp'] + full['tn']} genuine "
        f"({ci(wilson(full['fp'], full['fp'] + full['tn']))}); keyword blocklist: recall {pct(block['recall'])}, false alarms "
        f"{pct(block['false_alarm_rate'])} | ScamBench v0 frozen test split, {sb['n']} messages written by the team |",
        f"| Speed of a verdict | {sb['latency_ms_full']['p50']:.1f} ms median, {sb['latency_ms_full']['p95']:.1f} ms 95th percentile | same run |",
        f"| Scheme rules | {sch['rules']['agree']:,} / {sch['rules']['decisions']:,} decisions match a second transcription of the rules by the same author | SchemeBench v1, 200 personas × 12 schemes |",
        f"| Interview length | median {sch['interview']['median']:g} questions, never more than {max(sch['interview']['max'], ex.get('max', 0))} "
        f"(limit 8); skipping questions changed 0 of {ex.get('cases', 0):,} answer combinations | SchemeBench v1, exhaustive check |",
        f"| Hindi speech recognition | word error rate {pct(fleurs['wer'])} (95% CI {ci(fleurs['wer_ci95'])}) | Google FLEURS Hindi test, "
        f"{fleurs['utterances']} recordings, {fleurs['speech_seconds'] / 60:.0f} min of adults reading sentences aloud |",
    ]
    if lat_s:
        lines.append(f"| Voice reply time | {lat_s['cached']['p50']} s median from releasing the mic to the reply's first audio "
                     f"({lat_s['live']['p50']} s when the reply is synthesised live) | `bench/voice_latency.py` |")
    if ocr:
        lines.append(f"| Screenshot reading | same scam / not-scam decision as the typed message on {ocr['same_flag']} / {ocr['messages']} "
                     f"screenshots; {ocr['seconds_p50']} s each | ScamBench test messages rendered as SMS screenshots |")
    lines += [
        *([f"| Red team | disguised scams flagged {rt1['full']['scams_flagged']} / {rt1['full']['scams']} on the first run (blocklist {rt1['blocklist']['scams_flagged']} / {rt1['blocklist']['scams']}); hard genuine messages left alone {rt1['full']['genuine_left_alone']} / {rt1['full']['genuine']} | 74 messages written to get past Sahayak |"] if rt1 else []),
        *([(lambda g, bg: f"| Real published messages | {frac(g.get('caught', 0), g['scams'])} scams caught (blocklist "
            f"{frac(bg.get('caught', 0), bg['scams'])}), {frac(g.get('false_alarm', 0), g['genuine'])} genuine flagged (blocklist "
            f"{frac(bg.get('false_alarm', 0), bg['genuine'])}), Hindi / English / Hinglish, first run | PublicBench v0: "
            f"{pb['first']['messages']} messages published by the Income Tax portal, PIB Fact Check, courts and fact-checkers |")(
            pb["first"]["systems"]["full"]["groups"]["hindi_english_hinglish"],
            pb["first"]["systems"]["blocklist"]["groups"]["hindi_english_hinglish"])] if pb else []),
        *([(lambda g, bg: f"| Blind red team | Hindi / English / Hinglish: {frac(g.get('caught', 0), g['scams'])} scams caught "
            f"(blocklist {frac(bg.get('caught', 0), bg['scams'])}), {frac(g.get('false_alarm', 0), g['genuine'])} false alarms on hard "
            f"genuine messages; other Indian languages: \"could not check\", never a false green | {rb['first']['messages']} messages by a "
            "separate AI model working blind, scored once |")(rb["first"]["systems"]["full"]["groups"]["hindi_english_hinglish"],
                                                           rb["first"]["systems"]["blocklist"]["groups"]["hindi_english_hinglish"])] if rb else []),
        *([(lambda r, name: f"| An AI model as the judge | {lb['model']} zero-shot on {name}: {frac(r['llm']['caught'], r['llm']['scams'])} "
            f"scams caught but {frac(r['llm']['false_alarms'], r['llm']['genuine'])} genuine flagged, {r['llm_seconds']['median']} s a "
            f"message on a GPU; Sahayak {frac(r['sahayak']['caught'], r['sahayak']['scams'])} and "
            f"{frac(r['sahayak']['false_alarms'], r['sahayak']['genuine'])}, {r['sahayak_ms_median']} ms | `bench/eval_llm_baseline.py` |")(
            *((lb["sets"]["public_v0"], "the real published messages") if "public_v0" in lb["sets"]
              else (lb["sets"]["scambench_v0_test"], "the ScamBench test split")))] if lb else []),
        *([f"| Under load | 30 phones at once: a check in {next(v['p50_ms'] for s in st['load'] if s['scenario'] == 'session' for k, v in s['endpoints'].items() if k == 'check')} ms "
           f"median; {sum(v['errors'] for s in st['load'] for v in s['endpoints'].values())} errors in "
           f"{sum(v['n'] for s in st['load'] for v in s['endpoints'].values()):,} requests; {st['fuzz']['cases']} hostile inputs, "
           f"{len(st['fuzz']['unexpected'])} unexpected answers | `bench/stress/run_stress.py` |"] if st else []),
        f"| Call descriptions | {calls[0]} / {calls[1]} scam calls flagged, {calls[2]} / {calls[3]} genuine calls left alone | "
        "26 descriptions written by the team (a tuning set) |",
        *([f"| On the phone, offline | the phone's own engines give the node's exact answer on {phone['fraud']['cases']:,} scam checks "
           f"and {phone['navigator']['cases']:,} benefits cases ({phone['fraud']['mismatches'] + phone['navigator']['mismatches']} "
           f"mismatches); a check takes {phone['fraud']['check_ms_median']} ms | `bench/eval_phone_parity.py`, "
           "`scripts/check_phone_offline.py` |"] if phone else []),
        *([f"| With real people | {field['people']} people at {field['meta']['place']}: message cards judged right "
           f"{pct(field['cards']['before']['rate'], 0)} on their own, {pct(field['cards']['with_sahayak']['rate'], 0)} with Sahayak | "
           "`bench/eval_field.py`, `docs/field/FIELD_TEST_PROTOCOL.md` |"] if field and field.get("cards") else []),
        "| Zero egress | Sahayak's own process opens no outbound connection and makes no outside DNS lookup (counted by an audit hook "
        "on every socket); the firewall scripts block everything but the local network | `/app/node.html`, `tests/test_node.py` |",
        "| Privacy of the impact export | messages full of names, phone numbers and UPI IDs leave no trace in the export; counts under 5 "
        "are masked | `tests/test_console.py` |",
        "| Signed content | an altered pack is refused; an unsigned one is refused in strict mode | `tests/test_node.py` |",
        f"| Automated tests | {tests} | `python -m pytest` |",
        "",
        "## 1. Scam detection: ScamBench v0",
        "",
        f"**Data.** {sb['n']} messages in the frozen test split ({sb['n_scam']} scams, {sb['n_genuine']} genuine) in English, Hindi and "
        "Hinglish, from a 256-message set written by the team to mirror publicly reported scam patterns and real bank, "
        "government and personal messages. Splits are made by message family, so near-copies never sit in both training and test "
        "(leakage check: 0). See `bench/scambench/DATA_CARD.md`.",
        "",
        "**Method.** Rules, packs and thresholds were frozen, then the test split was scored once. A message counts as flagged when "
        "the verdict is Scam or Suspicious. Intervals in the table are 95% bootstrap intervals (10,000 resamples), as frozen; with "
        "only 37 scams, a bootstrap interval can reach 100%, so the summary above gives the 95% Wilson interval instead. The "
        "baseline is a keyword blocklist of the kind many SMS filters use.",
        "",
        "| System | Recall | Precision | False alarms on genuine |",
        "| --- | --- | --- | --- |",
        f"| Keyword blocklist | {pct(block['recall'])} ({ci(block_ci['recall'])}) | {pct(block['precision'])} | {pct(block['false_alarm_rate'])} |",
        f"| Sahayak (signals + patterns + classifier) | {pct(full['recall'])} ({ci(full_ci['recall'])}) | {pct(full['precision'])} "
        f"({ci(full_ci['precision'])}) | {pct(full['false_alarm_rate'])} ({ci(full_ci['false_alarm_rate'])}) |",
        "",
        f"McNemar's exact test, Sahayak against the blocklist: p = {sb['mcnemar_full_vs_blocklist']['p_value']:.1e}.",
        "",
        "**What this does not show.** The same team wrote the rules and the messages, so these numbers are optimistic. Errors found "
        "on the test split were fixed afterwards and logged (`bench/results/scambench_v0_test.md`, post-freeze log); the frozen "
        "numbers above stay the ones to quote. ScamBench v1 adds real messages collected with consent and is the honest test.",
        "",
        "**Without the sender.** No ScamBench scam carries a sender, while most genuine messages carry a bank-style header, "
        "so a reviewer asked what happens when a person pastes only the text. Checked today with the "
        f"installed packs: {stripped[0]} of {stripped[2]} genuine ScamBench messages are flagged with their sender, "
        f"{stripped[1]} of {stripped[2]} without it.",
        "",
        "Reproduce: `python bench/build_scambench.py`, `python bench/train_models.py`, `python bench/eval_scambench.py --split test --report`.",
        "",
        *(redteam_section(rt1, rtl) if rt1 else []),
        *(public_section(pb) if pb else []),
        *(blind_section(rb) if rb else []),
        *(llm_section(lb) if lb else []),
        "## 2. Benefits Navigator: SchemeBench v1",
        "",
        "**Data.** 200 personas (20 written as real-life stories, 180 generated around the ages where a rule changes) answering all "
        "seven interview questions. The expected answer for each of the 12 schemes comes from `bench/schemebench/oracle.py`, a "
        "separate transcription of the official rules as plain code that never reads the scheme pack.",
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| Decisions matching the oracle | {sch['rules']['agree']:,} / {sch['rules']['decisions']:,} |",
        f"| Questions per interview | median {sch['interview']['median']:g}, maximum {sch['interview']['max']} |",
        f"| Short interview reaches the same result as answering everything | {sch['interview']['equivalent']} / {sch['personas']} personas; "
        f"{ex.get('cases', 0):,} / {ex.get('cases', 0):,} answer combinations in the exhaustive check |",
        f"| Rupee amounts not found in the signed pack | {len(sch['amounts']['untraced'])} |",
        "",
        "**What this does not show.** The oracle and the pack share an author, so agreement rules out transcription slips, not a shared "
        "misreading of a rule. A second person deriving the answers from the official pages alone (`bench/schemebench/worksheet_v1.csv`) "
        "is the remaining acceptance step. Amounts are the central government's share; state top-ups are not modelled yet.",
        "",
        "Reproduce: `python bench/build_schemebench.py`, `python bench/eval_schemebench.py --exhaustive --report`.",
        "",
        "## 3. Voice",
        "",
        f"**Hindi speech recognition.** The node's own recognition code (Vosk small Hindi model, offline) on Google's FLEURS Hindi "
        f"test split: {fleurs['utterances']} recordings of adults reading Wikipedia sentences aloud. Word error rate "
        f"{pct(fleurs['wer'])} (95% CI {ci(fleurs['wer_ci95'])}), at {fleurs['real_time_factor']} × real time on the laptop CPU. "
        "The PRD target is at most 20% on VoiceBench. This is a public reference point, not a field result: long formal sentences "
        "are harder than the short answers people give Sahayak, but clear read speech by literate adults is easier than an older "
        "person speaking in a noisy shop. VoiceBench (the team's consented recordings from at least 10 speakers, three aged 55 or "
        "over, collected with `/app/voicebench.html`) is still to be recorded.",
        "",
    ]
    if lat_s:
        lines += [
            f"**Reply time.** From releasing the mic to the reply's first audio being ready (recognise and match the answer, pick the "
            f"next question, synthesise its first sentence): median {lat_s['cached']['p50']} s, worst {lat_s['cached']['max']} s with the "
            f"speech cache (the normal case; targets: 2 s templated, 4 s overall); {lat_s['live']['p50']} s median and "
            f"{lat_s['live']['max']} s worst when the sentence has to be synthesised live. {lat_s['unrecognised']} of "
            f"{lat_s['cases'] * lat_s['runs'] * 2} spoken answers went unmatched.",
            "",
        ]
    lines += [
        "Reproduce: `python bench/eval_voicebench.py --fleurs --report`, `python bench/voice_latency.py --report` (node running).",
        "",
        "## 4. More ways in",
        "",
    ]
    if ocr:
        lines += [
            f"**Screenshots.** The {ocr['messages']} ScamBench test messages rendered as phone SMS screenshots (Chromium, so Hindi is "
            f"shaped as on a phone) and read back with the node's offline OCR: the same scam / not-scam decision as the typed message on "
            f"{ocr['same_flag']} / {ocr['messages']}, the identical verdict on {ocr['same_verdict']} / {ocr['messages']}; mean character "
            f"error {pct(ocr['cer_mean'])}. The app shows the read text so the person can correct it before checking. Clean renders "
            "read better than real screenshots; a set of real phone screenshots is still to be collected.",
            "",
        ]
    lines += [
        f"**Calls.** People describe calls in reported speech (\"he asked for my OTP\", \"ओटीपी माँगा\"). On 26 descriptions "
        f"written by the team, {calls[0]} of {calls[1]} scam calls are flagged (digital arrest, courier, fake customer care, bank OTP, "
        f"KYC, electricity, relative in trouble, lottery, UPI, loan, scheme) and {calls[2]} of {calls[3]} genuine calls are left alone. "
        "These descriptions were used to add the reported-speech phrases, so they are a tuning set, not an unbiased test; "
        "ScamBench did not change when the phrases were added.",
        "",
        "**UPI QR codes.** Tests cover a shop's code (no signs, with the amount and payee spelled out), a \"scan to receive cashback\" "
        "code (scam), an official-sounding name on a personal UPI ID collecting a fee (scam, with a name-versus-ID warning) and a QR "
        "holding a lookalike link (scam). Every UPI card says that scanning and entering a PIN sends money and that a QR never brings "
        "money in.",
        "",
        "## 5. Offline, privacy and safety",
        "",
        "- **Zero egress.** A Python audit hook on the node counts every socket connection and DNS lookup the node process makes to an "
        "address outside the local network; the node page shows the count live, next to the machine's open internet connections "
        "and whether the firewall rules are active. The tests trigger the hook with a simulated outside connection and lookup and "
        "check they are counted. The firewall scripts (`scripts/firewall/`) add a block rule for every non-local address.",
        "- **Signed packs.** Every content pack carries an Ed25519 signature; the tests alter one amount in the scheme pack and check "
        "the node refuses it, and that an unsigned pack is refused in strict mode.",
        *(["- **On the phone.** After one visit to the node's HTTPS address (or to the stand-alone site, `scripts/build_tryit.py`), "
           "the phone keeps the app, its own scam check (`web/checker.js`) and benefits interview (`web/navigator.js`) and the signed "
           "packs, and answers by itself with no node and no internet; nothing leaves the phone. `bench/eval_phone_parity.py` replays "
           f"{phone['fraud']['cases']:,} scam-check and {phone['navigator']['cases']:,} benefits cases through both and compares every "
           f"field: {phone['fraud']['mismatches'] + phone['navigator']['mismatches']} mismatches. `scripts/check_phone_offline.py` "
           "drives a phone browser: one visit, network off, then a scam check, a UPI QR check and a benefits interview."] if phone else []),
        "- **Privacy.** The impact export is tested with messages full of names, phone numbers and UPI IDs: none appear in it; counts "
        "under 5 show as \"<5\"; the rupees-at-risk total is withheld until there are 5 flagged messages; the export's signature "
        "verifies. The case log refuses entries without consent, drops any name or number field, is unreadable on disk, and "
        "deletes entries older than 30 days.",
        "- **Safety gate.** Every vetted template passes the runtime gate, and the tests check it blocks advice to share an OTP, click a "
        "link, install an app or pay a fee, catches verdict contradictions and invented amounts, and treats \"never share your OTP\" "
        "and \"it asks you to share your OTP\" as safe (`tests/test_gate.py`).",
        "",
        *(stress_section(st) if st else []),
        f"## {7 if st else 6}. Known gaps",
        "",
        "- ScamBench v1 (600+ real messages, collected with consent) and the field morning with real users are still to come; "
        "the blind red team was written for the test, not received by real people.",
        "- Sahayak reads Hindi, English and Hinglish. A message mostly in another script (Bengali, Tamil, Telugu, Kannada, "
        "Malayalam, Gujarati, Punjabi, Odia, Urdu, Santali, Manipuri) or in Marathi gets \"could not check\" and safe-default "
        "advice instead of a false \"no scam signs\"; reading those languages is future work.",
        "- VoiceBench recordings, real phone screenshots, and a field test with real users and an operator are team tasks.",
        "- Known miss on the ScamBench test split: a \"pay the booking amount\" government-scheme scam. The \"approve the "
        "request\" refund scam was fixed after the freeze (6 Oct); the frozen numbers above still count it as missed.",
        "- The Hindi voices and the optional language model are licensed for non-commercial use only.",
        "- HTTPS on phones needs a domain and certificate; until then voice input on phones uses the recorder-app fallback, and "
        "phones keep no offline copy from the node (the stand-alone site, on any HTTPS host, works offline after one visit).",
        "",
    ]
    out = ROOT / "docs" / "TESTING_REPORT.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
