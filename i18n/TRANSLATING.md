# Translating Sahayak's screens

Sahayak is an offline scam check and benefits guide for people in India who are new to digital money: often older,
often new to a smartphone, sometimes reading little, reading a verdict in a hurry. These translations put the app's
screens and its answers into India's scheduled languages. They are display only: the scam rules, the benefits rules
and every verdict stay the same. A native speaker will review them later; until then the app labels them as machine
translations.

## Input and output

- Input: `i18n/source.json`.
  - `ui`: the app's own screen text, `key -> {en, hi}`.
  - `text`: what goes on a scam verdict card or a benefits result, `id -> {en, hi, where}`. `where` says where it
    appears (`fraud.signals(...).reason` is a reason under a verdict, `schemes.schemes.documents` a paper to carry,
    `schemes.schemes.counter.*` a sentence the person says at the CSC counter, and so on).
- Translate from the English. The Hindi was reviewed for meaning and tone; use it as a second reference, especially
  for register and for how Indian government and banking terms are put to ordinary people.
- Output: `i18n/<code>.json`, exactly this shape, every key of both sections, strings only:
  `{"lang": "<code>", "ui": {"<key>": "<text>", ...}, "text": {"t001": "<text>", ...}}`
- Check it with `python3 scripts/i18n_check.py <code>` and fix every problem it lists until it prints `<code>: OK`.

## Rules

1. **Meaning first, exactly.** These are safety instructions. Never soften, strengthen or flip them. Keep every
   "never", "do not", "only", "at once" and every condition ("if you clicked", "if you lost money"). Do not add advice.
2. **Never say "safe".** "No scam signs" means no warning signs were found, not that the message is safe. The four
   verdict labels must stay distinct and be used the same way everywhere:
   - Scam (a fraud, a cheating attempt)
   - Suspicious (looks doubtful, be careful)
   - No scam signs (no signs of fraud found; still verify)
   - Could not check (Sahayak could not read the message)
3. **Keep exactly as written:** every `{placeholder}` (do not translate or remove the name inside the braces); every
   number with ASCII digits 0-9, including amounts with their commas (`₹15,000`, `₹5 lakh` keeps the `5`), phone
   numbers, helpline `1930`, codes like `*401*`; every link and web address (`sancharsaathi.gov.in`,
   `cybercrime.gov.in`, `sbi-kyc-update.xyz`); and these words in Latin letters: OTP, PIN, UPI, KYC, QR, SMS, CSC,
   APK, BPL, AAY, PHH, APL, OPD, ATM, CVV, IFSC, UAN, SBI, RBI, NPCI, CBI, TRAI and the scheme short names PM-JAY,
   PMSBY, PMJJBY, APY, IGNOAPS, IGNWPS, IGNDPS, NFBS, PM-SYM, PMJDY, NSAP. Where the English has
   "Ayushman Bharat (PM-JAY)", write the scheme's usual name in your language and keep "(PM-JAY)".
4. **Plain, everyday words.** Write as a helpful person at the counter would speak: short sentences, common words
   over formal or literary ones, polite second person. Bank and government words people actually use may stay as
   loanwords (bank, account, link, app, card, Aadhaar, ration card).
5. **Short labels stay short.** Many `ui` strings are buttons or headings; keep them about as short as the English.
6. **Sentences said at the counter** (`counter`, `phrase` and the `age_phrase` items) are said by the person in the
   first person. Prefer forms that do not mark the speaker's gender; if your language must, use the form a woman
   would use (the app's default voice is female).
7. **Script.** Write in the script given for your language. Urdu, Kashmiri and Sindhi in Perso-Arabic script, written
   normally (the app turns the page right to left). Santali in Ol Chiki. Manipuri in Bengali script.
8. **Hindi-specific notes do not carry over.** A few `en` strings mention Hindi or English as the languages Sahayak
   reads (for example "Sahayak reads Hindi and English only"); translate them as they are: they are true statements
   about what the scam check can read.

## Working method

The output is long (about 570 strings). Write it with a short Python script that builds the dictionary and dumps it
with `json.dump(..., ensure_ascii=False, indent=1)`, in two or three parts if that is easier, then run the checker.
Do not edit any other file.
