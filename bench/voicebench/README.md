# VoiceBench: recording protocol

VoiceBench measures how well Sahayak understands the people it is for. The PRD's acceptance:
at least 100 real recordings from at least 10 speakers, including 3 aged 55 or over and 2 with
regional accents, recorded with consent; Hindi word error rate at most 20%.

## What a speaker does (about 5 minutes)

43 short prompts (`prompts_v1.jsonl`), one per screen:

- 25 spoken answers to the Benefits Navigator ("मेरी उम्र पैंसठ साल है", "अंत्योदय कार्ड है", "पता नहीं"…).
  Each has a known right answer, so the benchmark scores whether the right option comes out,
  not just the words.
- 12 sentences a person might say about a scam call or message, read aloud.
- 6 English lines.

## How to collect

1. Start the node with recording switched on (it is off by default):
   `set SAHAYAK_VOICEBENCH=1` then `python -m sahayak` (PowerShell: `$env:SAHAYAK_VOICEBENCH = "1"`).
2. Open `http://localhost:8000/app/voicebench.html` on the node laptop. The microphone only works on
   `localhost` or the HTTPS address, so phones need the HTTPS setup (Phase 6) first; until then
   record on the laptop with a phone-style headset or the built-in mic.
3. Read the consent screen to the speaker in their language. Tick only if they agree.
4. Pick the speaker's age group, optional gender, state or region, and first language. No name,
   no phone number, nothing else.
5. The speaker holds the button, reads the sentence, lets go, listens back, and presses Next.
   Re-record if the take is cut off or noisy.
6. "Delete my recordings" removes the whole session at once, if the speaker changes their mind.

Recordings stay in `%USERPROFILE%\.sahayak\data\voicebench\<session>\` on the node. Do not copy
them anywhere else, do not upload them, and delete them when the evaluation is finished
unless the speaker agreed to longer use.

## Coverage to aim for

| Group | Target |
| --- | --- |
| Speakers | 10 or more |
| Aged 55+ | 3 or more |
| Regional accents (state or region other than the majority) | 2 or more |
| Women | about half |
| Recordings | 100 or more (10 speakers × 43 prompts gives 430) |

## Scoring

`python bench/eval_voicebench.py --report` scores every session against its prompts:
word error rate with a 95% bootstrap interval, the same per age group, gender and region,
and Navigator answer accuracy with a 95% Wilson interval. The report lands in
`bench/results/voicebench_team.md`.

For a public reference before the team data exists, `python bench/eval_voicebench.py --fleurs --report`
scores the same code on Google's FLEURS Hindi test split (CC BY 4.0), read Wikipedia sentences
from real speakers. Download it once into `%USERPROFILE%\.sahayak\data\fleurs\hi_in\`:
`test.tsv` and `audio/test.tar.gz` (unpacked to `test/`) from
`https://huggingface.co/datasets/google/fleurs/tree/main/data/hi_in`.
