# Sahayak: from the application to the working prototype

The application (Inclusive Innovation for Bharat, Roshan Raj) described the idea and a clickable demo. The prototype
submitted for the 8 October 2026 deadline is working software: a node, a phone web app and an operator console, with
360 automated tests and a benchmark behind every number. Building it changed some choices. Each change below gives its
reason; most come from a measurement.

Dates: prototype due 8 Oct 2026; Grand Jury Round in Delhi, in person, on 14 Oct; Grand Finale and National Summit on
22 Oct, only for teams selected at the jury round.

## The biggest change: rules decide, not a language model

The application had a large language model judge each message: a compressed 14B-class model, offline on Roshan's
Crucible runtime, with a finance model Roshan had fine-tuned at Lenn Chartered behind it, and it called these parts
already built. They were Roshan's earlier work, not Sahayak. Crucible was never connected to Sahayak, and neither model
decides anything in Sahayak.

We tested the model idea instead (7 Oct, first runs, `bench/results/llm_baseline.md`). qwen2.5:3b, asked zero-shot on
137 real published messages, caught 99 of 103 scams but flagged 21 of 34 genuine ones (62%), at 2.1 s a message on a
GPU; Sahayak caught 67 and flagged 11, in 1.7 ms. On 182 blind messages written by a separate AI model that never saw
our code, it caught 108 of 118 scams (92%) but flagged 24 of 64 genuine messages (38%), at 2.24 s a message. Sahayak's rules caught 97 (82%) and flagged 15 (23%), in 1.76 ms
on the same machine's CPU. On the 60 ScamBench test messages the model flagged 7 of 23 genuine messages; Sahayak's
frozen run flagged 2.

Why rules decide: false alarms on a third to two thirds of genuine messages would teach people to ignore the warning; a rule
names its reason and gives the same answer every time; and it runs on a cheap CPU. On the team's 4-core laptop the 3B
model took 11–21 s per answer, and a 14B model could not run there at all. The model did catch 14 of 15 scams in
languages Sahayak cannot read yet (it also flagged 3 of 5 genuine messages there). That is where a model may come back:
as a second opinion that can only raise a warning.

## What changed, row by row

| The application said | The prototype does | Why |
| --- | --- | --- |
| A compressed 14B-class model, offline on the Crucible runtime, answers questions | 52 named signals, a pattern matcher and a small classifier decide every verdict in about 2 ms and name their reasons. Vetted Hindi and English templates explain it. An optional local model (tested: qwen2.5:3b on llama.cpp) can add a sentence through the safety gate; it is off by default. The model interface is OpenAI-style, so Crucible or any local server could plug in | A verdict a juror can check, the same every time, on a cheap CPU, with fewer false alarms than a model judging alone (above). On the 4-core test laptop the 3B model took 11–21 s per answer and its sentences were weaker than the templates. Crucible was never connected to Sahayak |
| A fine-tuned FinTech-advisor model answers money questions | Scheme answers come from rules written as data, each traced to its official page and date. No model writes an eligibility answer or an amount | Eligibility and rupee amounts must never be invented. 2,400 of 2,400 decisions match a separate re-derivation of the rules by the same author; a second person's check is still to do. The Lenn Chartered fine-tune is past experience, not part of Sahayak |
| Every answer passes an evaluation gate | Every model sentence is checked before anyone sees it: dangerous advice, phone numbers or links not in the message, invented amounts, contradicting the verdict, denying a number or link that is there, wrong script | The same idea, built into the product and covered by tests. The benchmarks use the same rigour: frozen test split, 95% bootstrap and Wilson intervals, McNemar's test, leakage check, and a blind red team written by someone who never saw the code |
| Under 800 ms | 2 ms per verdict; 0.65 s from releasing the mic to the spoken reply (2.44 s when the sentence is synthesised live) | Measured on a 4-core laptop CPU with no GPU |
| 0 bytes outbound | An audit hook counts every connection and DNS lookup Sahayak makes to the internet, live on the node page: 0. Firewall scripts block the rest of the machine | Measured, not asserted. The node page also shows the machine's own internet connections, honestly |
| Voice-first, vernacular | Offline speech in and out in Hindi and English; Hinglish text; amounts read as words; "I heard …, is that right?" before an answer is used. A message mostly in another Indian language gets "Could not check" and safe-default advice, never a false green; signs Sahayak can read, such as a scam link, still count | Two languages done properly first. Hindi word error 15.4% on Google's FLEURS test set (418 recordings of adults reading sentences aloud). A Tamil OTP scam used to get the green "no scam signs", because no Hindi or English signal could fire on it; a false green is the worst answer Sahayak can give. Each new language needs its own word lists, patterns and voices |
| −90% query resolution; 70–90% lower cost per user | Not claimed for Sahayak | These were not measured for Sahayak |
| Health and learning on the same platform | Health cover is part of the benefits guide and leads every result: Ayushman Bharat (PM-JAY) pays up to ₹5 lakh a year for treatment on admission to a listed hospital, not for OPD visits; at 70 or older it is the Vay Vandana card, whose cover is shared with a spouse who is also 70 or older. The scam check flags "pay to get your Ayushman card" messages. Health advice and learning are not built | The flagship first. Free hospital cover is often the most valuable line on the page, and the CSC makes the card at the counter |
| No expensive phone: it lives at a shared access point | The node at the counter is still the shared access point: for someone without a smartphone, the operator types the message into the console and the answer is read aloud. A person with a smartphone can also keep the checks on it | Scams arrive at home, on the person's own phone |
| An interactive phone-style demo | Working software you can run, plus a jury kit of test cards with an answer key produced by Sahayak itself. A phone that has opened Sahayak's secure web address once (the public site today; the node's own after a one-time HTTPS setup) checks messages and runs the benefits interview by itself, offline, with answers identical to the node's on every benchmark case. The round-1 demo address (roshworldwide.github.io/optum-v2) now opens this working app instead of the clickable mock | The prototype stage asked for a running product, and scams arrive at home, not at the counter |

**Added beyond the application:** UPI QR checks ("a QR never brings money in"), screenshots read offline, phone-call
descriptions, a complaint draft with the right next step (lost money: call 1930 at once; an attempt: report it on
Chakshu at sancharsaathi.gov.in), the "Could not check" answer, an operator console with an "Ask the agent" queue and
impact counters with no personal data ("rupees at risk" counts the money a message asks for), Ed25519-signed content
packs, and a red team of 52 disguised scams (46 caught on the first run against 33 for a keyword blocklist; all 52
after the fixes it found).

**Tested since the application (7 Oct):** 137 real messages people in India received, as published by the Income Tax
portal, PIB Fact Check, courts and fact-checkers, scored once: in Hindi, English and Hinglish, 67 of 97 scams caught
(69%) and 11 of 34 genuine messages flagged (32%), against 62 and 17 for a keyword blocklist; lower than on our own
messages, and the number we lead with. Fixes learned from half of those messages lifted the other, unread half from
28 to 30 of 44 scams caught (fraud pack 1.6.0). Also a blind red team of 182 messages written by a separate AI model that never saw the code, scored
once. In Hindi, English and Hinglish, 92 of 103 scams were caught (89%) and 14 of 59 hard genuine messages flagged
(24%); a keyword blocklist caught 51 and flagged 25. In other Indian languages, 5 of 15 scams were still caught and the
other 10 got "Could not check", with no false green. A stress test on the dev Mac found four faults on its first run
(speech queueing, an empty-photo crash, an image that unpacks to 900 MB, request bodies with no size limit), all fixed;
after the fixes, 30 phones doing a full visit at once, 300 checks at once and 5,000 checks in a row gave 0 errors.

**Unchanged:** the plan for a 6-month, ~20-village pilot through CSC and bank-correspondent points (budget estimate
₹35–40 lakh), and the partners we are asking for (none signed yet). The node's counters are how that pilot would
report results.

**Team:** the application lists Roshan Raj; the prototype was built by Roshan Raj and Ishmiit Singh.
