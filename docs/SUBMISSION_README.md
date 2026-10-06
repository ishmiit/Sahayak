# Sahayak · सहायक: prototype submission (Ideas for India 2026)

**An offline scam shield and benefits guide for people who are new to digital money.** One small computer at a CSC or
bank-agent counter runs everything. Phones join its Wi-Fi, which has no internet, and ask in Hindi or English, by voice
or touch: *"Is this a scam?"* and *"What am I owed?"* Nothing a person types or says leaves the node.

Team: Roshan Raj and Ishmiit Singh · Problem statement: Inclusive Innovation for Bharat

## What is in this submission

| File | What it is |
| --- | --- |
| `01_Sahayak_Demo_Video.mp4` | 2 min 12 s: the problem, the five main flows on screen, the measured results |
| `02_Sahayak_Pitch_Deck.pdf` / `.pptx` | 12 slides in the challenge's outline |
| `03_Sahayak_OnePager.pdf` | Everything on one A4 page |
| `04_Application_to_Prototype.pdf` | What changed since the application, and why each change was made |
| `05_Sahayak_Testing_Report.pdf` | How every number was measured, with confidence intervals and limits |
| `06_Sahayak_Jury_Kit.pdf` | Printable test cards (messages, UPI QR codes, benefit personas) with an answer key |
| `07_Sahayak_Source_Code.zip` | The full source: node, phone app, console, content packs, benchmarks, 334 tests |
| `screenshots/`, `clips/` | 14 phone screenshots and 5 silent screen recordings |

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

Open `http://<node-address>:8000` on a phone on the same Wi-Fi (or `http://127.0.0.1:8000` on the same computer). The
operator console is `/app/console.html` and the node's status page is `/app/node.html`. After the models are downloaded,
the internet can be switched off: everything keeps working. `python -m pytest` runs the 334 tests.

## Try it in 5 minutes

Print `06_Sahayak_Jury_Kit.pdf`. Type, speak or photograph a message card; photograph a QR card in "QR code" mode;
answer the benefits interview as one of the persona cards. Try to fool it with your own message. The last page shows
what Sahayak answered when the kit was built. The demo QR codes use a UPI handle that does not exist, so a real UPI app
refuses them.

## Measured, not claimed

| Area | Result |
| --- | --- |
| Scam detection (frozen test split, 60 messages) | 91.9% of scams caught vs 51.4% for a keyword blocklist; false alarms 8.7% vs 43.5% |
| Red team (52 scams disguised to get past it) | 46 caught on the first run vs 33 for the blocklist; 52 after the fixes it found |
| Scheme rules (200 personas × 12 schemes) | 2,400 / 2,400 decisions match an independent re-derivation; median 5 questions |
| Hindi speech (Google FLEURS, 418 recordings) | 15.4% word error, offline on a laptop CPU |
| Speed | 2 ms per verdict; 0.65 s from releasing the mic to the spoken reply |
| Offline | 0 connections from Sahayak to the internet, counted live by an audit hook |

Our test messages were written by our team, so these numbers are optimistic. The testing report says what each number
does not show. Next: real messages collected with consent, voice recordings from older speakers, and a field test at a
CSC with an operator.

## Privacy and safety

Messages, voices and answers stay in the node's memory for at most 15 minutes and are never written to disk. The case log
needs consent, holds no names or numbers, is encrypted and deletes itself after 30 days. "No signs found" never says
"safe". Every amount shown comes from an Ed25519-signed content pack; an altered pack is refused.

Code: MIT licence. The Hindi voices and the optional language model are licensed for non-commercial use only.
