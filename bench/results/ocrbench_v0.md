# Screenshot reading: OCR bench v0

Run 2026-10-03: the 55 ScamBench test messages rendered as phone SMS screenshots and read back with the node's offline OCR (EasyOCR, Devanagari and Latin models, CPU), screenshots drawn by Chromium. Reproduce with `python bench/eval_ocr.py --report`.

| Measure | Result |
| --- | --- |
| Same scam / not-scam decision as the typed message | 51 / 55 |
| Identical verdict (Scam, Suspicious, No signs) | 50 / 55 |
| Character error rate, mean (median) | 2.2% (1.6%) |
| Time per screenshot (median, laptop CPU) | 6.86 s |

| Language | Messages | Character error | Same decision |
| --- | --- | --- | --- |
| en | 38 | 1.8% | 34/38 |
| hi | 8 | 5.4% | 8/8 |
| hinglish | 9 | 1.1% | 9/9 |

Where the decision differed:

- sb-0109: typed no_signs, read suspicious. Read as: "+91 98765 43210
Paytm customer support: there was a double deduction from your wallet: To reverse it approve the request we sent you:"
- sb-0119: typed scam, read no_signs. Read as: "+91 98765 43210
Free laptop yojana 2026: all students get a free laptop. Register now at free-laptop-yojana online"
- sb-0125: typed scam, read no_signs. Read as: "+91 98765 43210
Your gas subsidy of Rs 1,200 is pending: Update your bank details on the government portal: Ipg-subsidy click"
- sb-0136: typed scam, read no_signs. Read as: "+91 98765 43210
Your bank's security team detected malware: Install the Bank Protect app from bankprotectapk download now to secure your money:"

The renders are clean, synthetic screenshots; real phone screenshots (status bars, emoji, photos of a screen) will read worse. The app always shows the read text for the person to correct before it is checked.
