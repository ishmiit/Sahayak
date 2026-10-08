# PublicBench v0: real published messages

**What it is.** 137 messages (103 scams, 34 genuine) that people in India actually received, as published by the
government, courts, banks, news outlets and fact-checkers between January 2023 and September 2026. It is the first
set in Sahayak's evidence that the team did not write.

**Who collected it, and how.** On 6–7 October 2026 an AI research agent (a separate model session that never opened Sahayak's
code, rules, packs or test sets) searched public sources for scam messages and genuine messages that look like them, and copied each one with its
source, date and a note of every edit (`public_messages_v0.provenance.tsv` points each item to the screenshot or page
it was read from). 18 candidates were dropped: file names without a message, fragments, a "typical example" written by
an explainer, and near-duplicates.

**Sources** (most used): the Income Tax e-filing portal's archive of the SMS it sends; PIB Fact Check (on X and its
public Telegram channel); consumer-commission orders on Indian Kanoon that reproduce ICICI Bank and SBI SMS logs;
Vishvas News, Newschecker, BOOM, Fact Crescendo, Mathrubhumi Fact Check, CyberPeace Foundation; Cyble's research blog;
The Times of India, The Economic Times, India Today, Amar Ujala, Dainik Bhaskar, Livemint, CNBC TV18, BBC, South First,
Deccan Chronicle, All India Radio. Each item names its own source and date.

**What is in it.**
- Scams, 32 kinds: fake government schemes and KYC/PAN/Aadhaar updates (9 each), prizes and KBC (7), electricity
  disconnection (6), digital arrest, gas-bill disconnection and relatives in an emergency (5 each), courier and India
  Post, e-challan, free recharge, part-time tasks, sextortion and fake police notices (4 each), and 18 more kinds.
  80 are text messages and 23 are phone calls as victims or police described them.
- Genuine: Income Tax Department messages (10), OTPs (5), bank, card and UPI alerts, an emergency-alert test, LPG and
  electricity notices, UIDAI, EPFO, PM-KISAN and Passport Seva messages; several of them look alarming on purpose
  (a subsidy SMS with a link and a deadline, a prepaid-power disconnection warning, a "refund on hold" notice).
- Languages: 103 English, 25 Hindi, 3 Hinglish, and 6 scams in Malayalam (2), Tamil, Telugu, Gujarati and Marathi.
- 107 of the 137 are word for word (`"verbatim": true`); the rest are call scripts told by victims or police, or an
  outlet's own translation.

**Edits.** Every phone number, including official helplines in genuine messages, was replaced with a fictional
number of the same shape (so a test cannot pass because a number is on a list). Private people's names and one
account number were replaced; public figures named by scams and scammers' aliases were kept as published.

**How it is scored.** `python bench/eval_public_v0.py --report`, once, on the packs in place when the set arrived
(fraud pack 1.5.0, 7 Oct 2026); the first run is the number to quote. The set is split in two by a fixed hash of each
id, made before anyone read an error: fixes may learn from the dev half only, and the test half's messages stay
unread, so its score after the fixes is a fair estimate of the improvement.

**Limits.** Published messages are the ones that went viral or reached a fact-checker, so they lean towards
well-known scam types and away from what sits quietly in one person's inbox. The genuine side is small and mostly
English. No Kannada, Bengali, Punjabi or Odia, and only 3 Hinglish messages. Scams with no published text (SIM swap,
"scan to receive", FASTag, "Hi Mum, new number") are missing. Consented messages from people's own phones
(ScamBench v1) remain the real test.

**Use.** The messages are quoted from public sources for testing a scam check, with their sources named; they are not
for any other purpose.
