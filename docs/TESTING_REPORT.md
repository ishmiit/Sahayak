# Sahayak testing report

Prototype for Ideas for India 2026 · generated 2026-10-06 by `scripts/build_testing_report.py` from the result files in `bench/results/`. Every number below can be reproduced with the command given in its section, on a 4-core laptop CPU (Intel i5-10210U, no GPU) with the internet off.

## At a glance

| Area | Result | How it was measured |
| --- | --- | --- |
| Scam detection | Recall 91.9% (95% CI 82.1%–100.0%), precision 94.4%, false alarms on genuine messages 8.7%; keyword blocklist: recall 51.4%, false alarms 43.5% | ScamBench v0 frozen test split, 60 messages |
| Speed of a verdict | 2.2 ms median, 3.0 ms 95th percentile | same run |
| Scheme rules | 2,400 / 2,400 decisions match an independent re-derivation | SchemeBench v1, 200 personas × 12 schemes |
| Interview length | median 5 questions, never more than 7 (limit 8); skipping questions changed 0 of 224,640 answer combinations | SchemeBench v1, exhaustive check |
| Hindi speech recognition | word error rate 15.4% (95% CI 14.0%–16.8%) | Google FLEURS Hindi test, 418 recordings, 81 min, real speakers |
| Voice reply time | 0.65 s median from releasing the mic to the reply's first audio (2.44 s when the reply is synthesised live) | `bench/voice_latency.py` |
| Screenshot reading | same scam / not-scam decision as the typed message on 51 / 55 screenshots; 6.86 s each | ScamBench test messages rendered as SMS screenshots |
| Red team | disguised scams flagged 46 / 52 on the first run (blocklist 33 / 52); hard genuine messages left alone 19 / 22 | 74 messages written to get past Sahayak |
| Call descriptions | 18 / 18 scam calls flagged, 8 / 8 genuine calls left alone | 26 descriptions written by the team (a tuning set) |
| Zero egress | Sahayak's own process opens no outbound connection and makes no outside DNS lookup (counted by an audit hook on every socket); the firewall scripts block everything but the local network | `/app/node.html`, `tests/test_node.py` |
| Privacy of the impact export | messages full of names, phone numbers and UPI IDs leave no trace in the export; counts under 5 are masked | `tests/test_console.py` |
| Signed content | an altered pack is refused; an unsigned one is refused in strict mode | `tests/test_node.py` |
| Automated tests | 334 tests pass | `python -m pytest` |

## 1. Scam detection: ScamBench v0

**Data.** 60 messages in the frozen test split (37 scams, 23 genuine) in English, Hindi and Hinglish, from a 256-message set written by the team to mirror publicly reported scam patterns and real bank, government and personal messages. Splits are made by message family, so near-copies never sit in both training and test (leakage check: 0). See `bench/scambench/DATA_CARD.md`.

**Method.** Rules, packs and thresholds were frozen, then the test split was scored once. A message counts as flagged when the verdict is Scam or Suspicious. Intervals are 95% bootstrap intervals (10,000 resamples). The baseline is a keyword blocklist of the kind many SMS filters use.

| System | Recall | Precision | False alarms on genuine |
| --- | --- | --- | --- |
| Keyword blocklist | 51.4% (35.1%–67.4%) | 65.5% | 43.5% |
| Sahayak (signals + patterns + classifier) | 91.9% (82.1%–100.0%) | 94.4% (85.7%–100.0%) | 8.7% (0.0%–22.2%) |

McNemar's exact test, Sahayak against the blocklist: p = 5.6e-06.

**What this does not show.** The same team wrote the rules and the messages, so these numbers are optimistic. Errors found on the test split were fixed afterwards and logged (`bench/results/scambench_v0_test.md`, post-freeze log); the frozen numbers above stay the ones to quote. ScamBench v1 adds real messages collected with consent and is the honest test.

Reproduce: `python bench/build_scambench.py`, `python bench/train_models.py`, `python bench/eval_scambench.py --split test --report`.

### Red team v0

74 messages written to get past Sahayak: 52 known scams each disguised with one technique (hidden characters, spaced, look-alike or digit-for-letter spelling, links written in words or behind a short link, a warning wrapped around the ask, a spoofed bank sender, no link at all, newer scam types) and 22 genuine messages that share words with scams. Scored once before any change: Sahayak flagged 46 / 52 disguised scams and left 19 / 22 genuine messages alone; the keyword blocklist 33 / 52 and 12 / 22.

The misses were then fixed (digits read as letters, written-out links undone, words people use instead of "OTP"); re-scored: 52 / 52 and 20 / 22, with ScamBench unchanged. Two genuine messages stay flagged by design: a shop offer on a short link, and a debit alert asking you to call or SMS a mobile number. The re-score is not an unbiased test; the first run is the number to quote.

Reproduce: `python bench/build_redteam.py`, `python bench/eval_redteam.py`; details in `bench/results/redteam_v0.md`.

## 2. Benefits Navigator: SchemeBench v1

**Data.** 200 personas (20 written as real-life stories, 180 generated around the ages where a rule changes) answering all seven interview questions. The expected answer for each of the 12 schemes comes from `bench/schemebench/oracle.py`, a separate transcription of the official rules as plain code that never reads the scheme pack.

| Check | Result |
| --- | --- |
| Decisions matching the oracle | 2,400 / 2,400 |
| Questions per interview | median 5, maximum 7 |
| Short interview reaches the same result as answering everything | 200 / 200 personas; 224,640 / 224,640 answer combinations in the exhaustive check |
| Rupee amounts not found in the signed pack | 0 |

**What this does not show.** The oracle and the pack share an author, so agreement rules out transcription slips, not a shared misreading of a rule. A second person deriving the answers from the official pages alone (`bench/schemebench/worksheet_v1.csv`) is the remaining acceptance step. Amounts are the central government's share; state top-ups are not modelled yet.

Reproduce: `python bench/build_schemebench.py`, `python bench/eval_schemebench.py --exhaustive --report`.

## 3. Voice

**Hindi speech recognition.** The node's own recognition code (Vosk small Hindi model, offline) on Google's FLEURS Hindi test split: 418 recordings of real speakers reading Wikipedia sentences. Word error rate 15.4% (95% CI 14.0%–16.8%), at 0.232 × real time on the laptop CPU. The PRD target is at most 20% on VoiceBench. Read news sentences are harder than the short answers people give Sahayak, so this is a conservative public reference; VoiceBench (the team's consented recordings from at least 10 speakers, three aged 55 or over, collected with `/app/voicebench.html`) is still to be recorded.

**Reply time.** From releasing the mic to the reply's first audio being ready (recognise and match the answer, pick the next question, synthesise its first sentence): median 0.65 s, worst 1.58 s with the speech cache (the normal case; targets: 2 s templated, 4 s overall); 2.44 s median and 4.31 s worst when the sentence has to be synthesised live. 0 of 24 spoken answers went unmatched.

Reproduce: `python bench/eval_voicebench.py --fleurs --report`, `python bench/voice_latency.py --report` (node running).

## 4. More ways in

**Screenshots.** The 55 ScamBench test messages rendered as phone SMS screenshots (Chromium, so Hindi is shaped as on a phone) and read back with the node's offline OCR: the same scam / not-scam decision as the typed message on 51 / 55, the identical verdict on 50 / 55; mean character error 2.2%. The app shows the read text so the person can correct it before checking. Clean renders read better than real screenshots; a set of real phone screenshots is still to be collected.

**Calls.** People describe calls in reported speech ("he asked for my OTP", "ओटीपी माँगा"). On 26 descriptions written by the team, 18 of 18 scam calls are flagged (digital arrest, courier, fake customer care, bank OTP, KYC, electricity, relative in trouble, lottery, UPI, loan, scheme) and 8 of 8 genuine calls are left alone. These descriptions were used to add the reported-speech phrases, so they are a tuning set, not an unbiased test; ScamBench did not change when the phrases were added.

**UPI QR codes.** Tests cover a shop's code (no signs, with the amount and payee spelled out), a "scan to receive cashback" code (scam), an official-sounding name on a personal UPI ID collecting a fee (scam, with a name-versus-ID warning) and a QR holding a lookalike link (scam). Every UPI card says that scanning and entering a PIN sends money and that a QR never brings money in.

## 5. Offline, privacy and safety

- **Zero egress.** A Python audit hook on the node counts every socket connection and DNS lookup the node process makes to an address outside the local network; the node page shows the count live, next to the machine's open internet connections and whether the firewall rules are active. The tests trigger the hook with a simulated outside connection and lookup and check they are counted. The firewall scripts (`scripts/firewall/`) add a block rule for every non-local address.
- **Signed packs.** Every content pack carries an Ed25519 signature; the tests alter one amount in the scheme pack and check the node refuses it, and that an unsigned pack is refused in strict mode.
- **Privacy.** The impact export is tested with messages full of names, phone numbers and UPI IDs: none appear in it; counts under 5 show as "<5"; the rupees-at-risk total is withheld until there are 5 flagged messages; the export's signature verifies. The case log refuses entries without consent, drops any name or number field, is unreadable on disk, and deletes entries older than 30 days.
- **Safety gate.** Every vetted template passes the runtime gate, and the tests check it blocks advice to share an OTP, click a link, install an app or pay a fee, catches verdict contradictions and invented amounts, and treats "never share your OTP" and "it asks you to share your OTP" as safe (`tests/test_gate.py`).

## 6. Known gaps

- ScamBench v1 (600+ real messages, collected with consent) and a red team from outside the team are still to come.
- VoiceBench recordings, real phone screenshots, and a field test with real users and an operator are team tasks.
- Known misses on the ScamBench test split: an "approve the request" refund scam and a "pay the booking amount" government-scheme scam.
- The Hindi voices and the optional language model are licensed for non-commercial use only.
- HTTPS on phones needs a domain and certificate; until then voice input on phones uses the recorder-app fallback.
