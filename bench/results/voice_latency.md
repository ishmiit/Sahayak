# Voice latency on the node

Run 2026-10-03 on the dev laptop (Intel i5-10210U, 4 cores, no GPU), node and models local. Time from releasing the mic to the reply's first audio being ready: recognise and match the answer, pick the next question, synthesise its first sentence. Reproduce with `python bench/voice_latency.py --report`.

| Case | Median | Worst | Target |
| --- | --- | --- | --- |
| Reply from the speech cache (fixed sentences, the normal case) | 0.65 s | 1.58 s | ≤ 2 s |
| Reply synthesised live (worst case) | 2.44 s | 4.31 s | ≤ 4 s |

Recognition alone took a median 0.61 s. 0 of 24 spoken answers were not matched to an option.

The spoken answers here are the node's own synthesised voice, so this measures speed, not accuracy; accuracy is VoiceBench's job (real speakers).
