# SchemeBench v1: Benefits Navigator results

Run 2026-10-02 on the schemes pack v1.0.0 (2026-10-02), SHA-256 `6fdf4618444b6fed…`. Reproduce with `python bench/build_schemebench.py` then `python bench/eval_schemebench.py --report`.

## Summary

| Check | Result | Target |
| --- | --- | --- |
| Scheme decisions matching the independent oracle | 2400 / 2400 (100.0%) | 100% |
| Questions per interview (200 personas) | median 5.0, max 7 | median ≤ 5, max ≤ 8 |
| Short interview gives the same result as answering everything | 200 / 200 | all |
| Random answer sets: max questions, results changed by skipping | max 7; 0 of 5000 changed | ≤ 8; none |
| Every answer combination (224,640): max questions, results changed by skipping | max 7; 0 changed | ≤ 8; none |
| Rupee amounts not found in the pack | 0 | 0 |
| Time to compute a full result | p50 0.23 ms, p95 0.37 ms | — |

## 1. Rules: engine against the oracle

The 200 personas are 20 hand-written stories and 180 generated cases weighted towards the ages where a rule changes and towards "don't know" answers. Each answers all seven questions. The expected answer for each scheme comes from `bench/schemebench/oracle.py`, a separate transcription of the official rules as plain if/else that does not read the pack or call the engine.

| Scheme | Agree | Expected: eligible | likely | check | after bank account | not eligible |
| --- | --- | --- | --- | --- | --- | --- |
| IGNOAPS | 200/200 | 0 | 46 | 14 | 0 | 140 |
| IGNWPS | 200/200 | 0 | 9 | 8 | 0 | 183 |
| IGNDPS | 200/200 | 0 | 9 | 1 | 0 | 190 |
| NFBS | 200/200 | 0 | 16 | 10 | 0 | 174 |
| PMSBY | 200/200 | 78 | 0 | 13 | 38 | 71 |
| PMJJBY | 200/200 | 45 | 0 | 5 | 20 | 130 |
| APY | 200/200 | 21 | 0 | 7 | 10 | 162 |
| PM-KISAN | 200/200 | 0 | 22 | 5 | 0 | 173 |
| PM-JAY | 200/200 | 58 | 0 | 142 | 0 | 0 |
| e-Shram | 200/200 | 52 | 0 | 0 | 0 | 148 |
| PM-SYM | 200/200 | 10 | 0 | 5 | 0 | 185 |
| PMJDY | 200/200 | 58 | 0 | 17 | 0 | 125 |

No disagreements.

## 2. Interview length

Each persona is replayed through the real interview: the engine picks the next question, the persona answers it, and the engine stops when no remaining answer could change any scheme's result.

| Questions asked | Personas |
| --- | --- |
| 4 | 33 |
| 5 | 134 |
| 6 | 31 |
| 7 | 2 |

Median 5.0, mean 5.01, 90th percentile 6, maximum 7. In 200 of 200 cases the shortened interview reached exactly the result that answering all seven questions gives.

The same check on 5000 random answer sets (a fifth of them answering age as a range): median 5.0, maximum 7 questions, 0 results changed by skipping questions.

Exhaustive check: every combination of answers (224,640 answer sets), with age taken on both sides of every point where a rule changes and as each age band. Maximum 7 questions, median 5.0; 0 results changed by skipping questions.

## What this shows and what it does not

- It shows that the pack encodes the rules as the oracle reads them, that the interview never asks more than it needs, and that skipping questions never changes an answer.
- The oracle and the pack were written by the same author, from the same official pages. Agreement rules out transcription slips, not a shared misreading. The PRD's acceptance needs a second person to fill `bench/schemebench/worksheet_v1.csv` from the official pages alone (E, L, C, U or N per scheme) and score it with `python bench/eval_schemebench.py --worksheet <file>`. That is still to do.
- Both follow the pack's documented interpretations: a ration card stands in for BPL status, PM-JAY below 70 always needs a list check, and land-owning farmers are not treated as unorganised workers.
- Amounts are the central share. State top-ups are not modelled yet (PRD row 26).
