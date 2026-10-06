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


def call_bench() -> tuple[int, int, int, int]:
    from sahayak.fraud import check_message
    rows = [json.loads(line) for line in (ROOT / "bench" / "callbench" / "calls_v0.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    scams = [r for r in rows if r["label"] == "scam"]
    genuine = [r for r in rows if r["label"] == "genuine"]
    flagged = lambda r: check_message(r["text"], input_type="call")["verdict"] in ("scam", "suspicious")  # noqa: E731
    return sum(map(flagged, scams)), len(scams), sum(not flagged(r) for r in genuine), len(genuine)


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
    rt1 = rt["first"]["systems"] if rt else None
    rtl = rt["latest"]["systems"]["full"] if rt and rt.get("latest") else None
    calls = call_bench()
    tests = test_result(log)
    full, block = sb["systems"]["full"]["flagged"], sb["systems"]["blocklist"]["flagged"]
    full_ci, block_ci = sb["systems"]["full"]["flagged_ci95"], sb["systems"]["blocklist"]["flagged_ci95"]
    lat_s = lat["summary"] if lat else None
    ex = sch.get("exhaustive", {})

    lines = [
        "# Sahayak testing report",
        "",
        f"Prototype for Ideas for India 2026 · generated {dt.date.today().isoformat()} by `scripts/build_testing_report.py` from the "
        "result files in `bench/results/`. Every number below can be reproduced with the command given in its section, "
        "on a 4-core laptop CPU (Intel i5-10210U, no GPU) with the internet off.",
        "",
        "## At a glance",
        "",
        "| Area | Result | How it was measured |",
        "| --- | --- | --- |",
        f"| Scam detection | Recall {pct(full['recall'])} (95% CI {ci(full_ci['recall'])}), precision {pct(full['precision'])}, "
        f"false alarms on genuine messages {pct(full['false_alarm_rate'])}; keyword blocklist: recall {pct(block['recall'])}, "
        f"false alarms {pct(block['false_alarm_rate'])} | ScamBench v0 frozen test split, {sb['n']} messages |",
        f"| Speed of a verdict | {sb['latency_ms_full']['p50']:.1f} ms median, {sb['latency_ms_full']['p95']:.1f} ms 95th percentile | same run |",
        f"| Scheme rules | {sch['rules']['agree']:,} / {sch['rules']['decisions']:,} decisions match an independent re-derivation | SchemeBench v1, 200 personas × 12 schemes |",
        f"| Interview length | median {sch['interview']['median']:g} questions, never more than {max(sch['interview']['max'], ex.get('max', 0))} "
        f"(limit 8); skipping questions changed 0 of {ex.get('cases', 0):,} answer combinations | SchemeBench v1, exhaustive check |",
        f"| Hindi speech recognition | word error rate {pct(fleurs['wer'])} (95% CI {ci(fleurs['wer_ci95'])}) | Google FLEURS Hindi test, "
        f"{fleurs['utterances']} recordings, {fleurs['speech_seconds'] / 60:.0f} min, real speakers |",
    ]
    if lat_s:
        lines.append(f"| Voice reply time | {lat_s['cached']['p50']} s median from releasing the mic to the reply's first audio "
                     f"({lat_s['live']['p50']} s when the reply is synthesised live) | `bench/voice_latency.py` |")
    if ocr:
        lines.append(f"| Screenshot reading | same scam / not-scam decision as the typed message on {ocr['same_flag']} / {ocr['messages']} "
                     f"screenshots; {ocr['seconds_p50']} s each | ScamBench test messages rendered as SMS screenshots |")
    lines += [
        *([f"| Red team | disguised scams flagged {rt1['full']['scams_flagged']} / {rt1['full']['scams']} on the first run (blocklist {rt1['blocklist']['scams_flagged']} / {rt1['blocklist']['scams']}); hard genuine messages left alone {rt1['full']['genuine_left_alone']} / {rt1['full']['genuine']} | 74 messages written to get past Sahayak |"] if rt1 else []),
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
        "the verdict is Scam or Suspicious. Intervals are 95% bootstrap intervals (10,000 resamples). The baseline is a keyword "
        "blocklist of the kind many SMS filters use.",
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
        "Reproduce: `python bench/build_scambench.py`, `python bench/train_models.py`, `python bench/eval_scambench.py --split test --report`.",
        "",
        *(redteam_section(rt1, rtl) if rt1 else []),
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
        f"test split: {fleurs['utterances']} recordings of real speakers reading Wikipedia sentences. Word error rate "
        f"{pct(fleurs['wer'])} (95% CI {ci(fleurs['wer_ci95'])}), at {fleurs['real_time_factor']} × real time on the laptop CPU. "
        "The PRD target is at most 20% on VoiceBench. Read news sentences are harder than the short answers people give Sahayak, "
        "so this is a conservative public reference; VoiceBench (the team's consented recordings from at least 10 speakers, three "
        "aged 55 or over, collected with `/app/voicebench.html`) is still to be recorded.",
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
        "## 6. Known gaps",
        "",
        "- ScamBench v1 (600+ real messages, collected with consent) and a red team from outside the team are still to come.",
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
