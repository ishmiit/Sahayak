# Why not just ask an AI model? (LLM baseline)

qwen2.5:3b through Ollama, zero-shot, temperature 0, one fixed prompt (bench/eval_llm_baseline.py), on Apple M3 (Darwin arm64), 2026-10-07. Sahayak: fraud pack 1.5.0, on the same messages. A message counts as caught when the model says scam, or when Sahayak says Scam or Suspicious.

| Set | System | Scams caught (95% CI) | False alarms on genuine (95% CI) | Time per message |
| --- | --- | --- | --- | --- |
| scambench_v0_test | qwen2.5:3b | 36 / 37 (97%) (86–100%) | 7 / 23 (30%) (16–51%) | median 1.64 s, max 2.39 s |
| scambench_v0_test | Sahayak | 36 / 37 (97%) (86–100%) | 0 / 23 (0%) (0–14%) | median 1.05 ms |
| redteam_v1_blind | qwen2.5:3b | 108 / 118 (92%) (85–95%) | 24 / 64 (38%) (27–50%) | median 2.24 s, max 4.33 s |
| redteam_v1_blind | Sahayak | 97 / 118 (82%) (74–88%) | 15 / 64 (23%) (15–35%) | median 1.76 ms |
| redteam_v1_blind, other Indian languages only | qwen2.5:3b | 14 / 15 (93%) | 3 / 5 (60%) | |
| redteam_v1_blind, other Indian languages only | Sahayak | 5 / 15 (33%) (the rest: could not check) | 1 / 5 (20%) | |
| public_v0 | qwen2.5:3b | 99 / 103 (96%) (90–98%) | 21 / 34 (62%) (45–76%) | median 2.13 s, max 3.93 s |
| public_v0 | Sahayak | 67 / 103 (65%) (55–74%) | 11 / 34 (32%) (19–49%) | median 1.7 ms |
| public_v0, other Indian languages only | qwen2.5:3b | 6 / 6 (100%) | – | |
| public_v0, other Indian languages only | Sahayak | 0 / 6 (0%) (the rest: could not check) | – | |

**Reading it.** The model ran on the dev Mac's GPU (Metal); a CSC node's CPU is several times slower, so the model's seconds here are a best case. Sahayak's time is for the whole check on the same Mac's CPU.

**What this does not show.** One small model, one prompt, no tuning; a larger model or a tuned prompt may do better, and the messages were written for the test, not received by real people.
