# Sahayak · सहायक

**An offline scam shield and benefits guide for people who are new to digital money.**
Sahayak runs on one small computer (the "node") at a CSC or bank-agent counter. Phones join its
Wi-Fi, which has no internet, and get two things in Hindi or English, by voice or by touch:

- **"Is this a scam?"** Paste, speak, photograph or describe a message, a call or a UPI QR code. A verdict
  in milliseconds, the three reasons behind it, what to do next, and a ready-to-file 1930 complaint.
- **"What am I owed?"** A short spoken interview (median 5 questions) finds which of 12 central schemes
  (old-age, widow and disability pensions, PMSBY, PMJJBY, APY, PM-KISAN, PM-JAY, e-Shram, PM-SYM, Jan Dhan…)
  the person can get, with the papers to carry, where to go, what to say at the counter, and a printed slip.

Nothing a person types or says leaves the node. The node page shows it live: outbound connections
and DNS lookups by Sahayak, open internet connections on the machine, and whether the firewall blocks
the internet.

**At home, too.** Scam calls and messages arrive at home, not at the counter. After one visit, the phone keeps
its own copy of the scam check and the benefits interview (the same rules, from the same signed packs) and answers
by itself, with no node and no internet; nothing leaves the phone. The phone's answers match the node's on every
benchmark case (`bench/results/phone_parity.md`). A stand-alone build of the app runs from any HTTPS site, offline
after the first visit: **try it at https://roshworldwide.github.io/optum-v2/** (`python scripts/build_tryit.py`).

Built for Ideas for India 2026 (Times of India) by Roshan Raj and Ishmiit Singh.

| | |
| --- | --- |
| ![Scam verdict](docs/screenshots/03_result_kyc_hi.png) | ![Benefits result](docs/screenshots/09_benefits_result_widow_hi.png) |
| A fake KYC SMS: verdict, reasons, steps, 1930 | A 67-year-old widow: pensions and cover she can claim |

## What is in the box

| Part | What it does | Where |
| --- | --- | --- |
| Fraud-Shield | 51 named signals from a signed content pack (lookalike links, `.bank.in` rule, UPI collect and "scan to receive", OTP or PIN asks with negation handling, digital arrest, fake customer care, 1600-series and TRAI sender rules…), a pattern matcher and a small classifier. Vetted Hindi and English templates explain every verdict; an optional local LLM (off by default) may add a sentence and can only raise a verdict, never lower it. | `sahayak/fraud/`, `packs/fraud.v1.json` |
| Safety gate | Every model sentence is checked for forbidden advice, wrong numbers or links, verdict contradictions, invented amounts and script, in each language, before anyone sees it | `sahayak/safety/gate.py` |
| Benefits Navigator | Scheme rules as data (each with its official source and date), evaluated with yes / likely / unknown / no logic; asks only questions that can still change an answer; never more than 8 | `sahayak/navigator/`, `packs/schemes.v1.json` |
| Voice | Offline Hindi and English speech out (every fixed sentence pre-synthesised) and speech in; amounts spoken as words; "I heard …, is that right?" | `sahayak/voice/`, `packs/voice.v1.json` |
| On the phone | The scam check and the benefits interview in the browser, from the packs the node serves (`/phone-packs/`) and the service worker keeps; identical answers to the node, checked case by case. Benefits results lead with health cover (Ayushman Bharat; the Vay Vandana card for anyone 70+) | `web/checker.js`, `web/navigator.js`, `web/sw.js`, `scripts/build_tryit.py` |
| More ways in | Call descriptions, photographed UPI QR codes ("a QR never brings money in"), screenshots read offline | `sahayak/inputs/` |
| Operator console | PIN-protected: "Ask the agent" queue, assisted checks read aloud, consented and encrypted case log, 58 mm slips, impact counters with a signed export that holds no personal data | `/app/console.html`, `sahayak/node/` |
| Node and proof | Zero-egress monitor, captive-portal DNS, HTTPS with redirect, firewall scripts, Ed25519-signed packs with install and rollback, hashes of every model and pack | `/app/node.html`, `sahayak/node/`, `scripts/firewall/` |

## Evidence

Every number we quote comes from a script in `bench/` and a report in `bench/results/`. The summary is in
**[docs/TESTING_REPORT.md](docs/TESTING_REPORT.md)**: scam detection with 95% confidence intervals against a keyword
blocklist, scheme rules checked against an independent re-derivation, Hindi speech recognition on a public test set,
voice latency, screenshot reading, a red team of disguised scams, the phone-versus-node parity check, and the limits of each.

With real people: `docs/field/` holds a one-morning field protocol for a CSC (consent in Hindi and English, paired
before/after message cards, the benefits interview, the off-node check), a print-ready kit
(`Sahayak_Field_Morning_Kit.pdf`: run sheet, consent, 30 recording cards; `scripts/build_field_kit.py`), invitations
to send, the sheets to fill, letters of intent, and `bench/eval_field.py`, which turns the filled sheets into
`bench/results/field_v0.json` for the report and the deck.

## Run it

Needs Python 3.10+ on Windows, macOS or Linux. No GPU. About 2 GB of disk for the speech, OCR and (optional) language models.

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-ocr.txt   # optional: screenshot reading (PyTorch; on Linux see the file)
python scripts/get_models.py            # once, with internet: speech models into %USERPROFILE%\.sahayak\models
python scripts/build_speech_cache.py    # optional: pre-synthesise every fixed sentence (~30 min)
python -m sahayak                       # the node: http://<this-machine>:8000 on the local network
```

Then open `http://<node-address>:8000` on a phone on the same Wi-Fi. The node prints the operator console PIN
(or set `SAHAYAK_CONSOLE_PIN`). The status page is `/app/node.html`.

- **Language model (optional, off by default).** Every verdict is explained by vetted Hindi and English templates. A
  local model can add an extra sentence in English, checked by the safety gate: run llama.cpp's `llama-server` with
  `qwen2.5:3b` on port 8081 and set `SAHAYAK_LLM=llamacpp` (or `SAHAYAK_LLM=ollama` with Ollama, which checks the
  internet for updates, so block it on a demo node). On the 4-core laptop it adds 11–21 s and its sentences are often
  weaker than the templates, so the demo runs without it.
- **Offline demo network.** A travel router with no internet uplink, the node as its DNS server
  (`python -m sahayak.node.dns --ip <node-address>`), and the firewall script for the node's OS
  (`scripts/firewall/`). With a certificate for a domain the team owns (`SAHAYAK_TLS_CERT`, `SAHAYAK_TLS_KEY`,
  `SAHAYAK_PUBLIC_HOST`), phones get HTTPS, which unlocks hold-to-talk; on plain HTTP the app falls back to the
  phone's recorder app.
- **Memory.** On an 8 GB machine the screenshot reader (PyTorch, about 1 GB) loads on its first use, so the first
  screenshot takes longer; `SAHAYAK_WARM_OCR=1` loads it at start-up on a node with room to spare.
- **On the phone, offline.** Browsers keep an offline copy only for a secure page: the node's HTTPS address (above), or
  `http://127.0.0.1:8000` on the node itself. `python scripts/check_phone_offline.py <address>` proves it in a phone
  browser (one visit, network off, then a scam check, a QR check and a benefits interview).
- **Stand-alone site.** Live at **https://roshworldwide.github.io/optum-v2/** (try it on a phone, then switch on
  airplane mode). `python scripts/build_tryit.py` writes it to `dist/tryit/` for any HTTPS host (GitHub Pages works).
  Voice input and screenshot reading need the node and are left out; QR photos use the phone browser's own QR reader
  where it has one.
- **HTTPS for the node.** `docs/NODE_HTTPS.md`: a certificate for a name under a domain you own (one DNS TXT record),
  then three environment variables.
- **Signing packs.** Each team member who signs keeps their own key (`SAHAYAK_SIGNER=<name>`, private key in
  `~/.sahayak/keys/<name>.key`); the node trusts every public key in `packs/keys/`. `python scripts/sign_packs.py --only
  <pack>` re-signs what you changed.
- **Tests.** `python -m pytest` (360 tests; the voice and OCR tests use the installed models, and the JavaScript
  parity tests need `node`).

Settings are environment variables (`SAHAYAK_*`); see `sahayak/config.py`.

## Privacy and safety

- Message text, recordings and answers stay in the node's memory for at most 15 minutes and are never written to disk.
  Speech synthesised from a person's own text is kept in memory only.
- The case log exists only with the person's consent, holds no names, numbers or message text, is encrypted, and
  deletes itself after 30 days. One console button deletes everything.
- Impact counters hold counts only; counts under 5 show as "<5"; the monthly export is signed.
- The verdict comes from named signals, never from the model alone. Green means "no signs found, still verify", never "safe".
- Scheme answers are computed by rules from official pages; the app never states an amount that is not in the signed pack.

## Licences

Our code: MIT (see `LICENSE`). Third-party models keep their own licences, and some are for
non-commercial use only, which is fine for this prototype but not for a commercial deployment:

| Model | Use | Licence |
| --- | --- | --- |
| Qwen2.5-3B-Instruct (via Ollama) | optional explanations | Qwen research licence (non-commercial) |
| Piper voices hi_IN priyamvada, pratham | Hindi speech | CC BY-NC-SA 4.0 (dataset) |
| Piper voice en_US lessac | English speech | Lessac / Blizzard 2013 dataset licence (research use) |
| Vosk small Hindi and Indian-English models | speech recognition | Apache-2.0 |
| EasyOCR CRAFT + Devanagari models | screenshot reading | Apache-2.0 |

Scheme rules were transcribed from official government pages (PIB, PFRDA, pmkisan.gov.in, eshram.gov.in,
pmjdy.gov.in, state NSAP pages); each rule cites its page and the date it was checked.

## Repository map

```
sahayak/            the node: server, fraud, navigator, voice, inputs, node (egress, console, counters), safety
web/                the phone app (with its own scam check and benefits engine), console, node page and VoiceBench
                    recorder (vanilla JS, no build step)
packs/              signed content packs: fraud signals, scheme rules, voice data, demo examples
bench/              ScamBench, SchemeBench, VoiceBench, OCR, call and phone-parity benches, field scoring, and results
scripts/            models, speech cache, pack signing and updates, screenshots, offline phone check, stand-alone build,
                    firewall scripts
tests/              pytest suite; tests/js/ holds the phone-versus-node parity harness
docs/               testing report, one-pager, jury kit, pitch decks (v3 for the finale), field kit (field/),
                    screenshots, demo clips and narrated draft video (video/)
PROGRESS.md         what is built, what is left, and every decision taken while building
```
