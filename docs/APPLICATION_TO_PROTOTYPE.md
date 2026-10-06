# Sahayak: from the application to the working prototype

The application (Inclusive Innovation for Bharat, Roshan Raj) described the idea and a clickable demo. The prototype submitted on
8 October 2026 is working software: a node, a phone web app and an operator console, with 334 automated tests and a benchmark
behind every number. Building it changed some choices. Each change below was made because a measurement said so.

| The application said | The prototype does | Why |
| --- | --- | --- |
| A compressed 14B-class model, offline on the Crucible runtime, answers questions | 51 named signals, a pattern matcher and a small classifier decide every verdict in about 2 ms. Vetted Hindi and English templates explain it. An optional local model (tested: qwen2.5:3b on llama.cpp) can add a sentence through the safety gate; it is off by default. The model interface is OpenAI-style, so Crucible or any local server can plug in | A verdict a juror can check, the same every time, on a cheap CPU. On the 4-core test laptop the 3B model took 11–21 s per answer and its sentences were weaker than the templates. Crucible has not been run with Sahayak yet |
| A fine-tuned FinTech-advisor model answers money questions | Scheme answers come from rules written as data, each traced to its official page and date. No model writes an eligibility answer or an amount | Eligibility and rupee amounts must never be invented. 2,400 of 2,400 decisions match an independent re-derivation. The Lenn Chartered fine-tune is past experience, not part of Sahayak |
| Every answer passes an evaluation gate | Every model sentence is checked before anyone sees it: dangerous advice, phone numbers or links not in the message, invented amounts, contradicting the verdict, denying a number or link that is there, wrong script | The same idea, built into the product and covered by tests. The benchmarks use the same rigour: frozen test split, 95% bootstrap intervals, McNemar's test, leakage check |
| Under 800 ms | 2 ms per verdict; 0.65 s from releasing the mic to the spoken reply (2.44 s when the sentence is synthesised live) | Measured on a 4-core laptop CPU with no GPU |
| 0 bytes outbound | An audit hook counts every connection and DNS lookup Sahayak makes to the internet, live on the node page: 0. Firewall scripts block the rest of the machine | Measured, not asserted. The node page also shows the machine's own internet connections, honestly |
| Voice-first, vernacular | Offline speech in and out in Hindi and English; Hinglish text; amounts read as words; "I heard …, is that right?" before an answer is used | Two languages done properly first. Hindi word error 15.4% on Google's FLEURS test set. More languages are a content pack |
| −90% query resolution; 70–90% lower cost per user | Not claimed for Sahayak | These were not measured for Sahayak |
| Health and learning on the same platform | Not built. Finance only: scam checks and benefits | The flagship first |
| An interactive phone-style demo | Working software you can run, plus a jury kit of test cards with an answer key produced by Sahayak itself | The prototype stage asked for a running product |

**Added beyond the application:** UPI QR checks ("a QR never brings money in"), screenshots read offline, phone-call
descriptions, a 1930 complaint draft, an operator console with an "Ask the agent" queue and impact counters with no
personal data, Ed25519-signed content packs, and a red team of 52 disguised scams (46 caught on the first run against 33
for a keyword blocklist; all 52 after the fixes it found).

**Unchanged:** the plan for a 6-month, ~20-village pilot through CSC and bank-correspondent points (budget estimate
₹35–40 lakh), and the partners we are asking for. The node's counters are how that pilot would report results.

**Team:** the application lists Roshan Raj; the prototype was built by Roshan Raj and Ishmiit Singh.
