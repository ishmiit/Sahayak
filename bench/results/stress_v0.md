# Stress test v0

2026-10-07 on Apple M3, 8 cores, 16 GB. One node process, as on a CSC laptop; every phone is a client on the same machine. Reproduce: `python bench/stress/run_stress.py --report`.

| Scenario | Wall time | Endpoint | p50 | p95 | Slowest | Errors | Node memory |
| --- | --- | --- | --- | --- | --- | --- | --- |
| session × 30 | 6.69 s | page | 43 ms | 57 ms | 70 ms | 0 | 581.1 → 1123.3 MB |
| | | health | 69 ms | 194 ms | 310 ms | 0 | |
| | | examples | 46 ms | 308 ms | 467 ms | 0 | |
| | | check | 66 ms | 338 ms | 507 ms | 0 | |
| | | explain | 66 ms | 267 ms | 440 ms | 0 | |
| | | nav next | 62 ms | 340 ms | 823 ms | 0 | |
| | | nav result | 86 ms | 249 ms | 512 ms | 0 | |
| | | speech (new) | 2903 ms | 4714 ms | 4856 ms | 0 | |
| burst × 300 | 2.4 s | check | 1045 ms | 2179 ms | 2333 ms | 0 | 1123.3 → 1136.7 MB |
| tts × 20 | 3.28 s | speech (new) | 1865 ms | 3282 ms | 3282 ms | 0 | 1136.7 → 1184.5 MB |
| asr × 10 | 0.27 s | recognise | 226 ms | 271 ms | 271 ms | 0 | 1184.5 → 1303.7 MB |
| soak × 5000 | 9.87 s | check | 38 ms | 47 ms | 163 ms | 0 | 1303.7 → 1302.0 MB |

Hostile input: 360 cases, 0 unexpected answers, 0 files leaked, node still answering: yes. The console locks after 5 wrong PINs. Memory growth from a 144-megapixel PNG of 140 KB and from 200 MB bodies: /api/qr bomb +0.0 MB, /api/ocr bomb +0.0 MB, /api/qr 200 MB body -189.8 MB, /api/asr 200 MB body -236.5 MB, /api/check 200 MB body -61.7 MB.

A low-end phone (Chromium, CPU 6× slower, 400 ms RTT, 400 kbit/s): first visit 6.4 s, ready to work offline after 6.4 s; offline, the first scam check took 1.04 s from tap to verdict (it starts the engine), the next 0.88 s; a benefits result 2.44 s. Script errors: 0.

**What this does not show.** The clients run on the node's own machine, so Wi-Fi is not part of the test; a travel router serving 30 phones adds its own delay. Speech numbers are for sentences the node has not said before; the fixed sentences of every screen are made ahead of time (scripts/build_speech_cache.py) and play from disk.
