# Sahayak in India's 22 scheduled languages

Added 14 Oct 2026, in this separate copy (`Sahayak-languages`). The `Sahayak` folder, its signed packs and the public
site at roshworldwide.github.io/optum-v2 are unchanged.

## What changed

- **A language list.** The button at the top right now shows the current language and opens a list of 23: Hindi,
  English and the other 21 scheduled languages (Assamese, Bengali, Bodo, Dogri, Gujarati, Kannada, Kashmiri, Konkani,
  Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, Urdu). The
  choice is kept on the phone. The app opens in English until a language is picked. `?lang=ta` opens straight in
  Tamil, `?lang=hi` in Hindi.
- **What is translated:** every screen of the phone app, and every answer the engines give. That covers the verdict,
  the headline, what to do, the reasons, the UPI QR facts, the benefits questions, the scheme cards, the papers, what
  to say at the counter, and the slip. Each line still shows Hindi or English under it: English for most languages, and
  Hindi for Bodo, Dogri, Maithili and Sanskrit.
- **What does not change:** the scam rules, the benefits rules, the signed packs and every verdict. Messages are still
  read in Hindi, English and Hinglish. A message in another language still gets "Could not check" unless a sign
  Sahayak can read fires (a scam link, an OTP ask). The check screen says this in the chosen language. The operator
  console and the node page stay in Hindi and English.
- **Voice:** the node speaks and listens in Hindi and English only. In another language, "Listen" uses the phone's own
  voice for that language if the phone has one. If it has none, Sahayak stays silent rather than read the words
  wrongly. Speaking to Sahayak is replaced by a note to type or paste.
- **Right to left:** Urdu, Kashmiri and Sindhi turn the page right to left, and their arrows point the other way.
  Links and numbers keep their own order.
- **Offline:** the phone keeps the language it opened once (the service worker caches it, about 75–120 KB). The node
  and the stand-alone build serve all of them.

## How honest it is

Every language except Hindi and English is a machine translation, made by Claude on 14 Oct 2026. No native speaker
has checked any of them yet. The app says so on the home screen in that language, and the language list says so in
Hindi or English.

- `scripts/i18n_check.py` refuses a translation that drops or changes any of these: a number, an amount, a helpline,
  a link, a `{placeholder}` or a protected word (OTP, PIN, UPI, KYC, QR, the scheme short names). It also refuses one
  written in the wrong script or left in English. All 21 pass.
- The four verdict labels were checked to be used the same way everywhere, and no verdict says "safe".
- The Bodo, Dogri, Kashmiri, Konkani, Maithili, Manipuri, Sanskrit, Santali and Sindhi translations need extra care.
  They are marked `draft` in `i18n/languages.json`. Manipuri is written in Bengali script, and Santali in Ol Chiki.
  Some phones have no Ol Chiki font.
- Known limit: a message written in Marathi, Nepali, Maithili or another Devanagari language reads to the engine like
  Hindi, so it can get a misleading "No scam signs". Marathi is caught as "Could not check" by its own words; the
  others are not yet. This was true before this change too.

## If a judge asks

> "The screens and answers come in all 22 scheduled languages. They are machine translations, not yet checked by a
> native speaker, and the app says so. The scam check still reads Hindi, English and Hinglish. In any other language it
> says 'Could not check' instead of guessing. Reading those languages is the next real step."

Never say "Sahayak understands 22 languages". It shows 22. It reads three.

## Run it

```
python -m sahayak                          # the node, as before; pick a language from the top-right button
python scripts/build_tryit.py              # the stand-alone site, with every language
```

## Change a translation

1. Fix the line in `i18n/<code>.json`. The keys are listed in `i18n/source.json`, with the English, the Hindi and
   where each line appears.
2. Run `python scripts/i18n_check.py <code>`.
3. Run `python scripts/i18n_build.py`, which writes `web/i18n/`.
4. Run `python -m pytest tests/test_i18n.py`.

After the screen text or a pack's wording changes, run `python scripts/i18n_extract.py`, then translate the new keys
by the rules in `i18n/TRANSLATING.md`. `python scripts/i18n_screens.py <tryit_dir>` opens every language in a phone
browser and screenshots it; it needs Playwright and Indic fonts.

## Measured (14 Oct)

- 21 of 21 translations pass `scripts/i18n_check.py`: 255 screen strings (71 of them for the tab bar and the
  Spot the scam game, `docs/GAME.md`) and 390 card and scheme strings each.
- In Chromium at phone size, all 23 languages × 3 screens (home, the KYC scam verdict, the 74-year-old's benefits)
  passed. That means no script errors, no horizontal scroll, no "undefined", the right direction, and the verdict and
  scheme text in the language. The language list switched both ways.
- On the node, the scam check and benefits results in Tamil, Bengali and Urdu worked with no failed requests. The
  counters still record hi or en.
- Tests on Python 3.11, the team's version: 495 tests (489 passed, 6 skipped; the skips need speech or OCR models).
  This includes the five new language tests and the phone-versus-node parity checks, which still show 0 differences:
  the engines are byte-for-byte unchanged.
