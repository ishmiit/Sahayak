# The phone gives the node's answer

Run 2026-10-07 with `python bench/eval_phone_parity.py --report` (packs: fraud 1.7.0, scam_patterns 1.0.0, fraud_model 1.0.0, schemes 1.1.1).

| Engine | Cases | Field-by-field comparisons | Mismatches |
| --- | --- | --- | --- |
| Scam check (`web/checker.js` against `sahayak/fraud`) | 1,841 | 41,861 | 0 |
| Benefits interview (`web/navigator.js` against `sahayak/navigator`) | 7,983 | 28,629 | 0 |

A scam check takes 0.154 ms (median) and 0.404 ms (95th percentile) in Node on the build laptop; a phone is several times slower and still far under the time a person notices.

The cases: every ScamBench, red-team (our own and the blind set) and call-bench message, the dev half of PublicBench, every message in the test files, the demo examples and QR codes, adversarial and fuzzed text (Unicode, homoglyphs, emoji, Hindi digits, long text); and the 200 SchemeBench personas replayed through the interview, 5,000 random answer sets, invalid answers and two extra rule packs that reach every branch of the engine.

**What this does not show.** Parity with the node, not accuracy: the phone is exactly as right and as wrong as the node on these cases. Unrounded classifier scores can differ in the last bit between machines; no card field or verdict does.
