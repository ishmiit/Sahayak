# Sahayak · सहायक: prototype submission (Ideas for India 2026)

**An offline scam shield and benefits guide for people who are new to digital money.** One small computer at a CSC or
bank-agent counter runs everything. Phones join its Wi-Fi, which has no internet, and ask in Hindi or English, by voice
or touch: *"Is this a scam?"* and *"What am I owed?"* Nothing a person types or says leaves the node.

A scam check gives one of four answers: Scam, Suspicious, No scam signs (never "safe"), or Could not check, for a
message mostly in a language Sahayak cannot read yet; that one gets safe-default advice, not a false green. A scam
answer ends in the right next step: lost money, call 1930 at once; an attempt with no loss, report it on Chakshu
(sancharsaathi.gov.in). Benefits results lead with health cover: Ayushman Bharat pays for hospital admission (not OPD
visits), and at 70 or older the Vay Vandana card gives cover shared with a spouse who is also 70 or older.

Team: Roshan Raj and Ishmiit Singh · Problem statement: Inclusive Innovation for Bharat (Financial Inclusion)

Dates: prototype due 8 Oct 2026 · Grand Jury Round in Delhi, in person, 14 Oct · Grand Finale on 22 Oct, only for
teams selected at the jury round

## What is in this submission

| File | What it is |
| --- | --- |
| `01_Sahayak_Demo_Video.mp4` | 2 min 16 s: the problem, the five main flows on screen, the measured results, real messages first |
| `02_Sahayak_Pitch_Deck.pdf` / `.pptx` | The pitch deck in the challenge's outline, with the measured results |
| `03_Sahayak_OnePager.pdf` | Everything on one A4 page |
| `04_Application_to_Prototype.pdf` | What changed since the application, and why each change was made |
| `05_Sahayak_Testing_Report.pdf` | How every number was measured, with confidence intervals and limits |
| `06_Sahayak_Jury_Kit.pdf` | Printable test cards (messages, UPI QR codes, benefit personas) with an answer key |
| `07_Sahayak_Source_Code.zip` | The full source: node, phone app, console, content packs, benchmarks, 486 tests |
| `screenshots/`, `clips/` | 16 phone screenshots and 5 silent screen recordings |

## See it in 2 minutes

Watch `01_Sahayak_Demo_Video.mp4`. The clips show the real app running on the node: a fake KYC SMS, a benefits interview
for a 67-year-old widow, a "scan to get cashback" UPI QR, the operator console, and the node page counting Sahayak's
internet connections (zero).

## Run it yourself (about 15 minutes, once)

Needs Python 3.10 or newer on Windows, macOS or Linux. No GPU. About 250 MB of speech models are downloaded once (300 MB more for screenshot reading). On Linux, install the CPU-only PyTorch first, as `requirements-ocr.txt` explains.

```
unzip 07_Sahayak_Source_Code.zip && cd sahayak
python -m pip install -r requirements.txt
python -m pip install -r requirements-ocr.txt   # optional: reading screenshots (adds PyTorch)
python scripts/get_models.py        # once, with internet: speech and screenshot-reading models
python -m sahayak                   # the node; prints its address and the console PIN
```

To try it on a phone with no node at all, open **https://roshworldwide.github.io/optum-v2/** (the stand-alone build,
`python scripts/build_tryit.py`); after the first visit it works with the internet off.

Open `http://<node-address>:8000` on a phone on the same Wi-Fi (or `http://127.0.0.1:8000` on the same computer). The
operator console is `/app/console.html` and the node's status page is `/app/node.html`. After the models are downloaded,
the internet can be switched off: everything keeps working. `python -m pytest` runs the 486 tests.

## Try it in 5 minutes

On your phone: open **https://roshworldwide.github.io/optum-v2/**, check a message, then switch on airplane mode and
check another. It still works: the scam check and the benefits interview run on the phone itself. A phone keeps this
offline copy only from a secure (HTTPS) address: the public site today, or the node's own address after its one-time
HTTPS setup (`docs/NODE_HTTPS.md` in the source).

Print `06_Sahayak_Jury_Kit.pdf`. Type, speak or photograph a message card; photograph a QR card in "QR code" mode;
answer the benefits interview as one of the persona cards. Try to fool it with your own message. The last page shows
what Sahayak answered when the kit was built. The demo QR codes use a UPI handle that does not exist, so a real UPI app
refuses them.

## Measured, not claimed

| Area | Result |
| --- | --- |
| Real published messages (PublicBench v0: 137 messages people in India received, as published by the Income Tax portal, PIB Fact Check, courts and fact-checkers; gathered by an AI research agent that never saw the code; scored once on 7 Oct) | In Hindi, English and Hinglish: 67 of 97 scams caught (69%) vs 62 for a keyword blocklist; 11 of 34 genuine messages flagged (32%) vs 17. The 6 scams in other languages: "could not check", no false green. Lower than on our own messages, and the honest number. After fixes learned from half of the set, the unread half went from 28 to 31 of 44 scams caught, false alarms unchanged |
| Scam detection (frozen test split, 60 messages written by our team) | 34 of 37 scams caught (91.9%; 95% Wilson CI 79–97%) vs 51.4% for a keyword blocklist; 2 of 23 genuine messages flagged (8.7%) vs 43.5% |
| Blind red team (182 messages written by a separate AI model that never saw the code, scored once on 7 Oct) | In Hindi, English and Hinglish: 92 of 103 scams caught (89%) vs 51 for the blocklist; 14 of 59 hard genuine messages flagged (24%) vs 25. Other Indian languages: 5 of 15 scams still caught, the other 10 "could not check"; no false green |
| An AI model as the judge (qwen2.5:3b, zero-shot) | On the 137 real messages: 99 of 103 scams caught but 21 of 34 genuine messages flagged (62%), 2.1 s a message on a GPU; Sahayak 67 and 11, 1.7 ms. On the blind set: 108 of 118 and 24 of 64; Sahayak 97 and 15 |
| Our red team (52 scams disguised to get past it) | 46 caught on the first run vs 33 for the blocklist; 52 after the fixes it found |
| Scheme rules (200 personas × 12 schemes) | 2,400 / 2,400 decisions match a separate re-derivation by the same author (a second person's check is still to do); median 5 questions |
| Hindi speech (Google FLEURS: 418 recordings of adults reading sentences aloud) | 15.4% word error, offline on a laptop CPU |
| Speed | 2 ms per verdict; 0.65 s from releasing the mic to the spoken reply |
| Under load (stress test on the dev Mac, 7 Oct) | The first run found four faults, all fixed: speech queueing (worst wait 14.5 s, now 3.8 s), an empty-photo crash, a 0.9 MB image that unpacks to 900 MB and took memory from 0.7 to 1.8 GB, and request bodies with no size limit. After the fixes: 30 phones doing a full visit at once, 300 checks at once and 5,000 in a row gave 0 errors and no memory growth; hostile input is refused |
| Offline | 0 connections from Sahayak to the internet, counted live by an audit hook |

ScamBench and our own red team were written by us, so those numbers are optimistic. The blind red team was written by
a separate AI model that never saw the code, but for the test: its messages were not received by real people.
PublicBench's messages are real, but published ones lean towards scams that went viral. The scam-detection
numbers are first runs (the red-team count after its fixes says so); fixes made after a run are logged, not hidden.
The testing report says what each number does not show. Next: real messages collected with consent, voice recordings
from older speakers, and a field test at a CSC with an operator (protocol, consent forms and scoring script ready; not
run yet).

## Privacy and safety

Messages, voices and answers stay in the node's memory for at most 15 minutes and are never written to disk. The case log
needs consent, holds no names or numbers, is encrypted and deletes itself after 30 days. "No signs found" never says
"safe", and a message Sahayak cannot read gets "Could not check", never a green. Every amount shown comes from an
Ed25519-signed content pack; an altered pack is refused.

Code: MIT licence. The Hindi voices and the optional language model are licensed for non-commercial use only.
