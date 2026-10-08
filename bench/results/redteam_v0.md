# Red-team set v0

74 messages written on 6 Oct 2026 to get past Sahayak (52 disguised scams, 22 hard genuine messages), scored once on 2026-10-06 before any change. Each scam is a known scam disguised with one technique: hidden characters, spaced or look-alike letters, links written in words, a warning wrapped around the ask, a spoofed bank sender, short links, no link at all, newer scam types. The genuine messages share words with scams (OTPs for a delivery agent, bank awareness SMS, a shop offer on a short link). Reproduce: `python bench/build_redteam.py`, `python bench/eval_redteam.py --report`.

## First run (the number to quote)

| System | Disguised scams flagged | Genuine messages left alone |
| --- | --- | --- |
| Keyword blocklist (baseline) | 33 / 52 (63%) | 12 / 22 (55%) |
| Sahayak | 46 / 52 (88%) | 19 / 22 (86%) |

| Technique | Sahayak right | Blocklist right |
| --- | --- | --- |
| advisory wrapped | 2 / 3 | 3 / 3 |
| callback only | 2 / 2 | 0 / 2 |
| devanagari english | 2 / 2 | 1 / 2 |
| emoji | 2 / 2 | 2 / 2 |
| genuine awareness | 2 / 3 | 0 / 3 |
| genuine bill | 1 / 1 | 1 / 1 |
| genuine courier | 1 / 1 | 1 / 1 |
| genuine delivery otp | 2 / 2 | 0 / 2 |
| genuine govt | 2 / 2 | 2 / 2 |
| genuine insurance | 1 / 1 | 1 / 1 |
| genuine job | 1 / 1 | 1 / 1 |
| genuine kyc official | 1 / 1 | 0 / 1 |
| genuine otp | 2 / 2 | 0 / 2 |
| genuine personal | 2 / 2 | 2 / 2 |
| genuine personal money | 1 / 1 | 1 / 1 |
| genuine refund | 1 / 1 | 0 / 1 |
| genuine short link promo | 0 / 1 | 0 / 1 |
| genuine txn alert | 1 / 2 | 2 / 2 |
| genuine upi request | 1 / 1 | 1 / 1 |
| leetspeak | 1 / 2 | 1 / 2 |
| line breaks | 1 / 1 | 0 / 1 |
| link in words | 2 / 3 | 2 / 3 |
| link shouted | 1 / 1 | 1 / 1 |
| lookalike letters | 2 / 2 | 2 / 2 |
| not a scam claim | 2 / 2 | 0 / 2 |
| novel courier fee | 1 / 1 | 0 / 1 |
| novel crypto | 1 / 1 | 0 / 1 |
| novel electricity app | 1 / 1 | 0 / 1 |
| novel family voice | 1 / 1 | 1 / 1 |
| novel olx buyer | 1 / 1 | 1 / 1 |
| novel sextortion | 1 / 1 | 0 / 1 |
| novel sim swap | 1 / 1 | 1 / 1 |
| novel task job | 2 / 2 | 1 / 2 |
| novel traffic challan | 1 / 1 | 1 / 1 |
| official name in link | 3 / 3 | 3 / 3 |
| otp synonym | 0 / 2 | 1 / 2 |
| padded | 2 / 2 | 1 / 2 |
| polite | 1 / 2 | 0 / 2 |
| punycode | 1 / 1 | 1 / 1 |
| romanised variants | 2 / 2 | 2 / 2 |
| short link | 2 / 2 | 2 / 2 |
| spaced letters | 3 / 3 | 1 / 3 |
| spoofed sender | 2 / 2 | 2 / 2 |
| zero width | 3 / 3 | 3 / 3 |

Sahayak's misses on the first run:

- rt-007 (leetspeak, scam, read as no_signs): 'Y0ur acc0unt is bl0cked. Share the 0TP to verify y0ur identity and rest0re access.'
- rt-012 (link_in_words, scam, read as no_signs): 'Claim your Rs 5,000 cashback before midnight: hxxp://cashback-paytm[.]top/claim'
- rt-023 (polite, scam, read as no_signs): "Good afternoon sir. This is Priya from your bank's customer desk. For the annual verification, kindly share the 6 digit number you received "
- rt-025 (advisory_wrapped, scam, read as no_signs): 'SBI never asks for your OTP. For your safety our verification officer will call you shortly; tell him the code you receive so he can confirm'
- rt-041 (otp_synonym, scam, read as no_signs): 'Our system sent you a 6 digit verification number just now. Please read it out to our agent to complete your account update.'
- rt-042 (otp_synonym, scam, read as no_signs): 'Aapke phone pe ek message aaya hoga 6 number wala, woh number mujhe bata do, aapka refund process ho jayega.'
- rt-059 (genuine_awareness, genuine, read as suspicious): 'Digital arrest is a scam. No police, CBI or customs officer arrests anyone over a video call. If you get such a call, hang up and dial 1930.'
- rt-061 (genuine_txn_alert, genuine, read as scam): 'Rs 2,500.00 debited from A/c XX4421 on 05-10-26 to VPA shyamkirana@okaxis. Not you? Call 1800 1234 or SMS BLOCK to 9223008333. -SBI'
- rt-065 (genuine_short_link_promo, genuine, read as suspicious): 'Diwali sale at Sharma Electronics, Lajpat Nagar: 20% off on all fans and coolers till Sunday. Catalogue: https://bit.ly/sharma-diwali'

## Post-freeze log

- 6 Oct, fraud pack 1.3.0: digits read as letters inside words (0TP, bl0cked, upd4te); written-out links undone (hxxp://, [.], (dot), ' dot xyz'); OTP stand-ins added ('6 digit number', 'verification number', 'number wala', 'code you receive'); awareness phrasing about what police never do ('no police', 'arrests anyone'). Kept by design: a shop offer on a bit.ly link stays Suspicious (a short link hides where it goes), and a debit alert asking you to call or SMS a mobile number is flagged even under a bank header (scammers copy exactly that). ScamBench train, dev and test unchanged.
- 7 Oct, fraud pack 1.6.0: rt-061 (a debit alert ending 'call 1800... or SMS BLOCK to <long code>') is no longer flagged: a bank's SMS-block line beside its toll-free number is not a number to call (PROGRESS.md D37). rt-065 stays flagged on purpose.

Re-scored 2026-10-07 after the changes above: 52 / 52 disguised scams flagged, 21 / 22 genuine messages left alone. These messages informed the fixes, so the re-score is not an unbiased test; the first run above stays the number to quote.

Still missed:

- rt-065 (genuine_short_link_promo, read as suspicious)

**What this does not show.** The set is small and written by the same team as the rules, so it finds blind spots rather than measuring a rate; a red team from outside the team is the next step.
