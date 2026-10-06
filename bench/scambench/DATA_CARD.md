# ScamBench v0 data card

256 messages: 151 scams and 105 genuine messages, in English, Hindi and Hinglish.

**Provenance and its limit.** Every v0 message was written by the Sahayak team, modelled on publicly reported
scam patterns and on the format of real bank, government and delivery messages. No real person's message is
included. Phone numbers are dummy patterns and links are invented. Because the same team wrote the detection
rules, v0 scores are optimistic; the honest test is v1, which adds real messages collected with consent.

## Splits

| Split | Scam | Genuine |
| --- | --- | --- |
| train | 90 | 59 |
| dev | 24 | 23 |
| test | 37 | 23 |

Splits are assigned per group (a scam and its translations share a group) with a stable hash.
Leakage check: 0 near-duplicate pair(s) across splits (5-gram Jaccard >= 0.8); 0 test item(s) dropped.

## Languages

| Language | Scam | Genuine |
| --- | --- | --- |
| en | 92 | 81 |
| hi | 27 | 17 |
| hinglish | 32 | 7 |

## Scam categories

| Category | Messages |
| --- | --- |
| otp_pin | 13 |
| kyc | 12 |
| investment | 12 |
| digital_arrest | 11 |
| job_task | 11 |
| loan_fee | 11 |
| upi_receive | 10 |
| prize | 10 |
| courier | 10 |
| electricity | 10 |
| customer_care | 9 |
| govt_scheme | 9 |
| impersonation | 9 |
| malicious_app | 6 |
| sextortion | 5 |
| govt_payment | 3 |

## Adding real messages (v1)

Put real messages in `bench/scambench/private/` (git-ignored) first. Remove names, numbers, account digits and
links that identify a person, get the owner's consent, then move them to a `*_v1.jsonl` source file with
`source` set to how they were collected.
