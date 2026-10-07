# ScamBench v0 results (test split)

60 messages (37 scam, 23 genuine), evaluated 2026-10-02. A message is flagged when the verdict is Scam or Suspicious. Intervals are 95% bootstrap (10,000 resamples).

| System | Recall | Precision | F1 | False alarms on genuine |
| --- | --- | --- | --- | --- |
| Keyword blocklist (baseline) | 51.4% (35.1%–67.4%) | 65.5% (48.0%–82.8%) | 57.6% (41.9%–70.6%) | 43.5% (22.7%–64.3%) |
| Signals only | 83.8% (71.1%–94.7%) | 93.9% (84.6%–100.0%) | 88.6% (80.0%–95.5%) | 8.7% (0.0%–22.2%) |
| Signals + pattern match | 83.8% (71.1%–94.7%) | 93.9% (84.6%–100.0%) | 88.6% (80.0%–95.5%) | 8.7% (0.0%–22.2%) |
| Full: signals + patterns + classifier | 91.9% (82.1%–100.0%) | 94.4% (85.7%–100.0%) | 93.2% (86.2%–98.6%) | 8.7% (0.0%–22.2%) |

McNemar exact test, full vs blocklist: full right where the blocklist was wrong on 25 messages, the reverse on 2; p = 5.6e-06.
Full-system latency on this laptop: p50 2.2 ms, p95 3.0 ms.

## Full system by language

| Language | Recall | Precision | F1 | False alarms |
| --- | --- | --- | --- | --- |
| en | 87.0% | 90.9% | 88.9% | 11.1% |
| hi | 100.0% | 100.0% | 100.0% | 0.0% |
| hinglish | 100.0% | 100.0% | 100.0% | 0.0% |

## Full system recall by scam category

| Category | Recall |
| --- | --- |
| courier | 100.0% |
| customer_care | 50.0% |
| digital_arrest | 100.0% |
| electricity | 100.0% |
| govt_scheme | 87.5% |
| impersonation | 100.0% |
| investment | 100.0% |
| kyc | 100.0% |
| loan_fee | 100.0% |
| malicious_app | 100.0% |
| otp_pin | 50.0% |
| prize | 100.0% |
| sextortion | 100.0% |
| upi_receive | 100.0% |

Missed scams: sb-0016, sb-0109, sb-0148. False alarms: sb-0227, sb-0235.

**Caveat.** ScamBench v0 was written by the team that wrote the rules, so these numbers are optimistic. v1 adds real messages collected with consent and is the honest test.

## Post-freeze log

The numbers above were taken once, with rules, pack and thresholds frozen beforehand (fraud pack 1.1.0,
pattern threshold 0.623, classifier threshold 0.75). The test errors were then reviewed. Fixes made afterwards are
listed here; they are **not** reflected in the numbers above and will be measured on the next fresh test set (v1).

| Test item | Error | Cause | Fix after freeze (pack 1.1.1) |
| --- | --- | --- | --- |
| sb-0227 | False alarm on an NPCI advisory ("you never need to enter your PIN") | Negation inside the matched phrase was not checked | UPI-receive matches now reject an inner negation |
| sb-0235 | False alarm on "No registration fee" | Fee phrases ignored a preceding "no" | Fee phrases now skip "no", "without", "free", "बिना" |
| sb-0016 | Missed "read it to me" OTP request | Phrase not in the share-verb list | Added "read it to me", "read it out", "read the code/OTP" |
| sb-0109 | Missed "approve the request" refund scam | Approval without an explicit receive/refund word nearby | Fixed 6 Oct in `signals.py` (no pack change): an instruction to approve or accept a request, tied to reversing, returning or refunding money or to "by mistake", fires `upi_receive`; reports such as "your refund request was accepted" and warnings such as "never approve a request" do not |
| sb-0148 | Missed "free solar panels, pay booking amount on this number" | No pay-to-book pattern | Not fixed; logged for v1 |
| (not a test item) | Found 3 Oct by the console tests: "card XX4421 ka OTP batao" was only Suspicious | A masked card number was read as an OTP code, which marks a message as delivering a code | Digits right after a mask (XX, **) no longer count as a code (`signals.py`); regression test added |

Re-running the test split with every fix above (3 Oct): full system recall 94.6%, precision 100%, false alarms 0%. These
numbers are **not** an unbiased estimate, because the split's own errors guided the fixes; the frozen numbers above
remain the result to quote until ScamBench v1.

6 Oct, with the sb-0109 fix: test split recall 97.3% (36/37), false alarms 0/23; train and dev, the red-team set and the
call set give the same verdict on every message as before the change (356 messages compared one by one). Same caveat:
not an unbiased estimate.

7 Oct, fraud pack 1.6.0 (the fixes from the blind red team and the dev half of PublicBench, PROGRESS.md D31–D37): test split recall 97.3% (36/37), false alarms 0/23; no message in any benchmark set lost its catch or became a false alarm. Same caveat: not an unbiased estimate. The fair estimate of these fixes is PublicBench's unread test half (`bench/results/public_v0.md`): scams caught 28 → 30 of 44, genuine flagged 6 → 6 of 20.
