# Collecting real messages with consent (ScamBench v1)

Every set Sahayak has been scored on so far was written by the team, written for the test by a separate AI model, or
published after a scam went viral. ScamBench v1 is the real test: messages people actually received, shared with
their consent. This page is the whole method, from asking to scoring.

## What we ask, and how

Ask in the person's language, in person or by message. Saying no changes nothing.

**हिंदी:** क्या आपके फ़ोन पर कोई ऐसा मैसेज या कॉल आई है जिस पर आपको शक हुआ, या कोई असली बैंक या सरकारी मैसेज? क्या
आप उसे हमें दिखाएँगे? हम उसमें से नाम, नंबर और खाते की जानकारी हटा देंगे, उसे सिर्फ़ एक लैपटॉप पर रखेंगे, और सिर्फ़
सहायक ऐप को जाँचने और बेहतर बनाने में इस्तेमाल करेंगे। हम आपको एक कोड देंगे (जैसे V1-023); वह कोड बताकर आप कभी भी
उसे मिटवा सकते हैं।

**English:** Have you received a message or call that worried you, or a genuine bank or government message? Would
you show it to us? We will remove names, numbers and account details, keep it on one laptop only, and use it only to
test and improve the Sahayak app. We give you a code (like V1-023); quote it at any time and we delete the message.

At the field morning this is question 2 of the consent (`docs/field/CONSENT.md`) and task 2b of the protocol.

## What to record, for each message

| Field | What |
| --- | --- |
| `id` | The code you gave the person: `v1-001`, `v1-002`, ... |
| `text` | The message exactly as received (copy it, or type it from the screen). For a call, what the caller said, in the person's words |
| `sender` | The sender line as shown (`VM-SBIINB-S`, a number, "WhatsApp"); numbers are redacted next |
| `input_type` | `text`, `call` or `qr` |
| `lang` | `hi`, `en`, `hinglish`, or the language's code (`ta`, `bn`, `mr`, ...) |
| `label` | `scam` or `genuine`, decided as below; leave out "unsure" ones |
| `category` | Optional: KYC, OTP, courier, job, ... |
| `source` | `field`, `friends`, `csc`, ... |
| `month` | When it was received (month and year only) |

Never record the person's name, number or anything else about them.

## Where it lives

- In `bench/scambench/private/` on the collection laptop. Git ignores that folder; the laptop's disk is encrypted
  (BitLocker or FileVault). Never in email, chat apps or cloud drives.
- If people forward messages to a team phone on WhatsApp, copy each one into the file the same day and delete the
  chat.

## Redact, then read

1. `python bench/redact_messages.py bench/scambench/private/raw.jsonl` writes `raw.redacted.jsonl`: mobile numbers
   become fictional ones of the same shape, account, card and Aadhaar numbers keep only their last four digits, UPI
   IDs lose the name, e-mail addresses and PAN numbers are replaced, personal tokens are cut from links, and names
   after "Dear", "Mr", "प्रिय" or "श्री" become [NAME].
2. A person reads every redacted message and removes anything the script missed (a name in the middle of a sentence,
   a village, a vehicle number). Then they set `"redacted": true` on it.
3. Delete `raw.jsonl` within 7 days. Keep the ids, so a person who quotes their code can have their message deleted.

## Label

- Two people label each message on their own, as scam or genuine, from the message and what the person said about
  it (did they lose money? did their bank confirm it?). A genuine label needs evidence: the bank's own sender
  header, a known official number, or the person's confirmation that it was real.
- Where the two disagree, a third decides; if nobody can be sure, the message is left out. Write down how often the
  first two agreed: it says how hard the set is.
- Labels are fixed before the messages are scored.

## Score once

- `python bench/eval_scambench_v1.py --report` reads `bench/scambench/private/scambench_v1.jsonl` and writes counts
  and message ids only to `bench/results/scambench_v1.json` and `.md`; no message text leaves the private folder. It
  refuses rows not marked as redacted and read.
- The first run is the number to quote. The set is split in two by a fixed hash of each id: fixes may learn from the
  dev half only; the test half is scored but its messages are never read, so its score after the fixes is a fair
  estimate. Later runs need `--rerun-note "what changed"`.

## How many, and from whom

Aim for 200 or more, at least a third of them genuine (bank alerts, OTPs, government messages), from people of
different ages, towns and phones, in Hindi, English and Hinglish, and some in other Indian languages (to measure
"could not check"). Count what you have by source and language before scoring; report it beside the numbers.
