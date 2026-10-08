# Running Sahayak: the operations runbook

For whoever runs Sahayak day to day: the operator at the counter, the person who looks after the nodes in a district,
and the maintainers who update the scam rules. Every command runs from the `sahayak` folder.

## Who does what

| Role | Does | Needs |
| --- | --- | --- |
| Operator (CSC or bank agent) | Starts the node each morning, helps people at the counter, ticks the cards made and forms filed in the console | The console PIN; this page's "Every morning" and "When something goes wrong" |
| Node keeper (one per district) | Installs pack updates, fixes nodes, sends the signed monthly export | A copy of each release; this whole page |
| Maintainers (at least two people) | Change the scam rules and scheme rules, measure every change, sign packs | A signing key each; the "Weekly pack cycle" and "Signing keys" sections |

## Every morning at the counter

1. Plug the node into power and switch on the counter's Wi-Fi router (it has no internet uplink).
2. Start the node: `python -m sahayak` (on a pilot node, set it to start at boot: Task Scheduler on Windows, a
   systemd unit on Linux, a launchd agent on macOS).
3. Run the preflight: `python scripts/demo_day.py`. It checks the packs and their signatures, the voices and the
   speech cache, gives every jury-kit card to the node and compares the answer, reads the zero-egress counter and the
   firewall, and ends with READY or a list of what to fix. It prints the address and QR code for phones and the
   console PIN. If it started the node itself, the node keeps running (`--stop` stops it).
4. Check that the sticker on the node shows the address the preflight printed. If the address changed, print a new
   sticker from the node page (`/app/node.html`).

## The weekly pack cycle

Scam wordings change every week; the rules are data in signed packs, so they change without a code release.

1. **Collect.** New scam patterns from public advisories (PIB Fact Check, I4C, RBI, banks, the police) and messages
   people chose to share with consent (`bench/scambench/COLLECTING.md`). Message text never comes from the node:
   it keeps none.
2. **Write the change** as a dated script (`scripts/pack_update_<version>.py`, like `pack_update_1_7.py`): new words
   and phrases, new signals with their Hindi and English reasons, new advice cards. If a rule needs code, the code
   goes into both engines (`sahayak/fraud/signals.py` and `web/checker.js`) and stays off until the pack defines it.
3. **Test new wordings,** not just the messages that prompted the change, and genuine look-alikes that must stay
   alone (`tests/test_signals_1_7.py` is the pattern). Four of 1.7.0's first drafts misfired here and were narrowed.
4. **Measure on every set** before keeping a change: ScamBench, both red teams, the call set and PublicBench's dev
   half. The bar is no lost catch and no new false alarm; a trade-off is written down with its numbers, never hidden.
   Then `python -m pytest` and `python bench/eval_phone_parity.py` (the phone must give the node's answer: 0 mismatches).
5. **Log it.** A post-freeze note in each re-scored results file (`--rerun-note`), and a line in `PROGRESS.md`. First
   runs stay the numbers to quote. PublicBench's test half is scored but never read.
6. **Review and sign.** The second maintainer reads the diff and the measurement and signs:
   `SAHAYAK_SIGNER=<name> python scripts/sign_packs.py --only fraud`.
7. **Ship.** On each node: `python -m sahayak.packs install fraud.v1.json` (it verifies the signature, then swaps the
   file in; the old copy is kept), then restart the node. Phones pick up the new rules the next time they open the
   app on the node's Wi-Fi; a phone that has not visited for 45 days shows "scam patterns are N days old".
8. **Roll back** if a node reports a problem: `python -m sahayak.packs rollback fraud.v1.json`, restart.

Version numbers: a new rule or advice card raises the middle number (1.6.0 to 1.7.0); a wording fix the last one; a
change to the pack's format the first one, and that needs a code release too. A new scam wave (like the "dial
*401*" calls) gets a same-day update through the same steps.

## Signing keys

- Each maintainer has their own key: the private key in `~/.sahayak/keys/<name>.key` (readable by its owner only),
  the public key in `packs/keys/<name>.pub`. A node trusts every public key in its `packs/keys/` folder and refuses an
  altered pack outright. Set `SAHAYAK_REQUIRE_SIGNED=1` on pilot nodes so an unsigned pack is refused too.
- A private key is never committed, emailed, put on a cloud drive or copied to a node. Back it up encrypted on two USB
  drives kept by two different people.
- Rule for the pilot: the person who prepared a change does not sign it. The code accepts one signature from any
  trusted key and does not enforce this yet; requiring two signatures per pack is on the roadmap.
- **Rotation** (once a year, or when someone leaves): make the new key (`SAHAYAK_SIGNER=<new name> python
  scripts/sign_packs.py --new-key`), ship its `.pub` in a release, re-sign the current packs with it, and remove the
  old `.pub` in the next release.
- **A lost or stolen key:** remove its `.pub` from `packs/keys/` in a release at once (nodes then refuse anything
  signed only by it), re-sign the current packs with another key, and check each node's page: every installed pack
  shows who signed it.

## When something goes wrong

| What you see | What to do |
| --- | --- |
| The node does not start: "address already in use" | Another node is running. Close it, or `python scripts/demo_day.py --stop` if the preflight started it. |
| The node does not start: a pack is refused (`PackSignatureError`) | A pack file was changed after signing. Never edit a pack on a node: reinstall it from the release, or roll back. Tell the maintainers. |
| Phones cannot open the app | Is the phone on the counter's Wi-Fi? Has the node's address changed (the preflight and the node page show it)? |
| No hold-to-talk on phones | The node is on plain HTTP: phones fall back to the recorder app. For hold-to-talk, set up HTTPS (`docs/NODE_HTTPS.md`). |
| Speech is slow | Build the speech cache once: `python scripts/build_speech_cache.py`. With many phones at once, raise `SAHAYAK_TTS_ENGINES`. |
| A person says Sahayak got a message wrong | Tell them what the card says to do anyway; "no scam signs" never means safe. With their consent, ask them to share the message (`bench/scambench/COLLECTING.md`); the node does not keep it. Tell the maintainers the kind of message and the answer it got. |
| A phone says "scam patterns are N days old" | The phone has not opened the app on the node's Wi-Fi for a while. Open it there once. |
| The node page shows an outside connection by Sahayak above 0 | This should never happen. Note the address it shows, unplug the router's uplink if it has one, and tell the maintainers. |
| A power cut | Nothing to recover: the node keeps no message text. Counters and the consented case log are on disk. |
| Anything that looks like tampering (an unknown key in `packs/keys/`, a refused pack you did not change) | Take the node off the network, reinstall from a signed release, tell the maintainers. |

## Privacy duties

- Messages, recordings and answers stay in the node's memory for at most 15 minutes and are never written to disk.
- The case log exists only with the person's consent, holds no names, numbers or message text, is encrypted and
  deletes itself after 30 days. One console button deletes everything.
- The monthly export holds counts only, shows counts under 5 as "<5", and is signed. Send it as it comes; do not add
  names or numbers to it.
- Never photograph a person's phone or messages for the team without their written consent (`docs/field/CONSENT.md`).

## Who to call

- A person who lost money: 1930 at once, and cybercrime.gov.in. An attempt with no loss: Chakshu on
  sancharsaathi.gov.in.
- The maintainers: [team contact to be filled in before the pilot].
