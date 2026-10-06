# Field morning v0: one CSC, 20–30 people, about four hours

Every number Sahayak quotes so far comes from messages the team wrote. This protocol gets the first numbers from
the people Sahayak is for, in one morning, at one Common Service Centre (CSC) or bank-agent point, with the
operator who would run it. It is designed so that the results are honest even if they are disappointing, and so
that the scoring script (`bench/eval_field.py`) turns the filled sheets into `bench/results/field_v0.json`,
which the deck and the testing report read like every other result.

It is a usability and comprehension test with consenting adults, not a clinical or financial trial. No money,
OTP, PIN or real account is used at any point.

## What we want to know

| Question | Measured by | Target |
| --- | --- | --- |
| Can people tell a scam from a real message better with Sahayak than without? | Each person judges 3 printed message cards first on their own, then with Sahayak (paired) | Correct judgements rise; McNemar test on the pairs |
| Do they know what to do next? | After each Sahayak verdict: "What will you do now?" (right action or not) | 80% right action |
| Can they finish the benefits interview? | Completed without the volunteer touching the phone | 70% unaided |
| Does it find anything new? | Schemes shown as eligible or likely that the person did not know about | Median at least 1 |
| Health: are seniors 70+ found for Ayushman Vay Vandana? | Count of 70+ people shown PM-JAY 70+ who do not have the card | Counted, not targeted |
| Does it work at home, off the node? | On a phone set up once at the node, Wi-Fi off, check one card | Works on every phone tried |
| Would the operator keep it? | Operator questions at the end; time per assisted case | A yes, and a signed letter of intent if they offer one |

## Before the day

1. **Partner and place.** A CSC village-level entrepreneur (VLE) or bank business correspondent who agrees to host
   a morning (messages to send: `INVITATIONS.md`). Use the letter-of-intent template (`LOI_TEMPLATES.md`) only after
   the morning, if they want to continue.
2. **Kit.** The node laptop (charged, plus charger), the travel router, two Android phones of your own (one
   basic, about ₹6,000), the printed jury kit (`docs/Sahayak_Jury_Kit.pdf`: message cards and persona cards), the
   printed field kit (`Sahayak_Field_Morning_Kit.pdf`: run sheet with the right answer for each card, the consent in
   large print, 30 recording cards; `python scripts/build_field_kit.py [people]`), a timer, pens.
3. **Node.** Start it with the console PIN set, reset the impact counters (console, Counters tab), run the firewall
   script, check `/app/node.html` shows 0 outbound connections. If you have the HTTPS address, install the app on both
   phones from it, so the off-node test (task 4) works.
4. **Cards.** Pick 6 message cards: 4 scams of different kinds (KYC, OTP call, UPI "receive money", Ayushman fee or
   digital arrest) and 2 genuine (a bank OTP, a transaction alert). Each person gets 3, shuffled, at least one genuine.
   Number the cards; the sheet records the card number.
5. **People.** The VLE invites 20–30 adults who use or are starting to use a bank account or UPI: aim for half
   women, a third aged 55 or more, a few who read little. Nobody is paid to say good things; a cup of tea is fine.

## Roles

- **Host (VLE or operator):** welcomes people in their language, runs the assisted checks on the console.
- **Facilitator:** reads the consent, gives the tasks, never helps unless asked, and notes when they do.
- **Recorder:** fills the sheets, times the tasks, writes nothing that identifies a person.

## With each person (15–20 minutes)

1. **Consent** (read aloud, `CONSENT.md`). No name, phone number or photo is recorded. The person can stop at any
   time. A separate yes/no for donating a real message they received (task 2b).
2. **About them** (participants sheet): age band, gender, reads Hindi (yes / a little / no), phone (smartphone /
   basic / none), language used.
3. **Task 1, message cards (paired).** For each of 3 cards: first, without Sahayak, "Is this real or a fraud? What
   would you do?" Record their answer (real / fraud / not sure). Then they check the same card with Sahayak (typed,
   spoken or photographed, their choice; the facilitator may type for someone who cannot), and say what they will
   do now. Record the verdict, whether the action they say is right, the seconds from start to verdict, and whether
   they needed help.
4. **Task 2a, a call.** "Tell Sahayak what a caller said" using the phone-call mode: one described call (from the
   jury kit or their own experience). Record the same fields.
5. **Task 2b, their own message (optional, only with the separate consent).** If they have a message they were
   worried about, check it. With their yes, the recorder copies it with names, numbers, account digits and links
   that identify a person removed, into `bench/scambench/private/` on the node laptop (never anywhere else). These
   become ScamBench v1, the real-message test.
6. **Task 3, benefits.** "What am I owed?": they answer the questions themselves (touch or voice). Record whether
   they finished unaided, the seconds, the number of schemes shown as eligible or likely, how many of those they had
   not heard of or were not getting, and for anyone 70 or older without the card, whether PM-JAY 70+ (Ayushman Vay
   Vandana) was shown. Print the slip if they want it; it is theirs.
7. **Task 4, at home (on one of your phones, a few people only).** Wi-Fi off, mobile data off: check one card on the
   phone. Record whether it worked.
8. **Three questions** (1 = not at all, 5 = completely): "I understood what Sahayak told me." "I would trust it before
   paying or sharing a code." "I would use it again."

## At the end, with the operator

- Time 5 assisted checks on the console (walk-in, typed by the operator, read aloud).
- Ask: "Would you keep this at your counter? What would you need? What would make it worth your time?" Write the
  answers down in their words.
- Export the month's impact counters (console, signed CSV) and keep the file with the sheets.

## After the day

1. Type the two sheets into `bench/field/field_participants_v0.csv` and `bench/field/field_tasks_v0.csv` (the
   column meanings are below; keep the header row).
2. `python bench/eval_field.py --report` writes `bench/results/field_v0.json` and `field_v0.md`.
3. Rebuild the deck and the testing report; the field slide appears only when the results file exists.
4. Report what went wrong as plainly as what went right. A 60% on a first morning, with what you changed after it,
   is more convincing to a jury than a perfect score.

## Sheet columns

`field_participants_v0.csv`: `pid` (P01…), `age_band` (18-34, 35-54, 55-69, 70+), `gender` (f, m, other, not_said),
`reads_hindi` (yes, some, no), `phone` (smart, basic, none), `lang` (hi, en), `understood`, `trust`, `use_again`
(1–5), `donated_message` (y, n).

`field_tasks_v0.csv`, one row per attempt: `pid`, `task` (card, call, own, benefits, offline), `item` (card number,
"call", "own", "benefits"), `truth` (scam, genuine; blank for benefits), `before` (scam, genuine, unsure; cards only),
`verdict` (scam, suspicious, no_signs; blank for benefits), `action_right` (y, n), `seconds`, `helped` (y, n),
`schemes_found`, `schemes_new`, `pmjay70_shown` (y, n, or blank if under 70 or already has the card), `worked`
(y, n; offline task), `notes` (no names or numbers).

## Privacy

No names, phone numbers, photos of faces, or account details are written anywhere. Messages that people let us keep
are cleaned of anything that identifies a person before they are saved, stay on the node laptop, and are used only to
test Sahayak. The node itself keeps nothing a person types for more than 15 minutes.
