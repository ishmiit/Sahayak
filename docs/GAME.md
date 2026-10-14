# Spot the scam, and the new look

Added 14 Oct 2026, in this separate copy (`Sahayak-languages`). The `Sahayak` folder, its signed packs and the public
site are unchanged.

## The new look

The phone app now looks and behaves like one of Apple's own iOS apps (`web/app.css`, used by `index.html` only; the
operator console and the node page keep `web/styles.css`).

- **System font and colours.** San Francisco on an iPhone or a Mac, Roboto and Noto on Android. iOS system colours in
  light and dark, with darker text shades so secondary text reads at 5:1 or better.
- **Grouped inset lists.** Home, examples, answers, reasons and steps are white rows on the grey page, with hairline
  separators and chevrons, as in Settings. Each home row has a coloured rounded-square icon.
- **Bars.** A translucent bar at the top, and a tab bar at the bottom: Home, Check, Benefits, Learn. A tab's first
  screen has no back button. Every other screen has the iOS back button: a chevron and the word "Back".
- **Four appearances**, picked under Appearance on the home screen, as in iPhone Settings: Automatic (follows the
  phone), Light, **White Titanium** and Dark. White Titanium is a warm silver-white light look, after the metal frame
  of a phone. It has a soft stone-grey page, warm white cards with a fine metal edge, brushed bars and a titanium app
  mark. The tint and the verdict colours stay the same, so every verdict reads the same in all four. The choice is
  kept on the phone; `?theme=titanium` shows it for a demo without keeping it.
- **Large titles, segmented controls, bottom sheets.** The language list is a sheet with a grabber and a checkmark
  on the current language.
- **No gradients, glows or glass panels.** A verdict is a white card with a coloured symbol and the word.
- **Still there:** text size, reduced motion, reduced transparency, higher contrast, printing, and right to left
  for Urdu, Kashmiri and Sindhi.

## Motion

The app moves the way an iPhone app does. All of it uses only transform and opacity, and all of it stops when the
phone asks for reduced motion.

- **Pages push and pop.** Going deeper slides the new screen in from the side over the old one; going back slides it
  away; changing tab cross-fades (View Transitions, in Chrome on Android and in Safari 18; other browsers fade).
  Urdu, Kashmiri and Sindhi slide the other way.
- **The bar.** It is clear at the top of a screen and frosts once the page scrolls under it. When the large title
  scrolls away, the screen's title moves into the bar.
- **Live details.** A shield on the home screen keeps watch with a slow pulse, the offline dot breathes, and the
  waiting daily message beats. The home rows arrive one after another when the app opens.
- **The verdict arrives.** The symbol springs in (a scam pulses twice), then the words, the headline and the steps.
- **In the game:**
  - A card is dealt in, and flies off towards its answer.
  - A right answer draws its tick with a small burst of sparks; a wrong one draws a cross and shakes.
  - Points, the score and the level count up.
  - Earned medals are struck metal with a bevel and a passing sheen; they spin when tapped, and a new one spins in.
- **Sheets** fade the page behind them, spring up, slide away, and can be pulled down to close.
- **White Titanium:** light catches the metal of the app mark now and then.
- **A glass tab bar.** The tab bar floats as a capsule of glass, as in Apple's newest iOS. A lens slides to the
  chosen tab and stretches a little on the way.
- **Sahayak reading.** While a message or a QR code is checked, a glow of colour flows round the edge of the screen,
  as Apple Intelligence does, and a light sweeps the message. The answer waits for it at most about two-thirds of a
  second, so the person sees that the message was read.
- **The answer's colour.** The edges of the screen flash once: red for a scam, orange for suspicious, green for no
  scam signs. In the game they flash green for a right answer and red for a wrong one.
- **Depth.** On the home screen the title drifts up and fades as the cards slide over it. A slow halo of colour turns
  behind the shield. The game card tilts in 3D under the finger. A new level twinkles.

## Spot the scam (ठगी पहचानो)

A short game on the Learn tab, made to build awareness in a way people enjoy.

- **A round** is 5 cards. Each card is an SMS, shown as a received message bubble, or a phone call, shown as the words
  the caller said. The player taps **Scam** (red) or **Real** (green), like declining or accepting a call. They can
  also swipe the card towards an answer.
- **After each answer:**
  - "Right!" or "Not this time".
  - The checker's own headline.
  - **The clues**, which are Sahayak's own reasons for its verdict.
  - **Remember**, the first thing to do.
  - On a scam card, the links, phone numbers, UPI IDs and OTP or PIN words the checker found are marked.
  - On a real card, the lesson is what real messages do and never do.
- **Rewards:**
  - Points: 10 for each right answer, plus 5 more from three in a row.
  - Five levels, shown as a ring: Learner, Alert, Sharp Eyes, Scam Shield, Scam Guru.
  - A daily streak.
  - **Today's message**, the same for everyone that day, worth 20 bonus points if answered right.
  - **Eight badges**. Three right answers in a group earn its badge: OTP Guardian, QR Expert, Threat Buster, Fake Police
    Buster, Prize Skeptic, Easy-Money Alarm, Scheme Saathi, Real-Deal Detective.
  - Confetti for a perfect round.
  - "Challenge your family" shares the score, never a message.
- **Language.** All of it is in all 23 languages. The cards stay in the Hindi, English and Hinglish they arrive in,
  as real scam messages do.
- **Privacy.** Everything stays on the phone (`localStorage`). Nothing is sent, and nothing is counted on the node.

### Why the game can be trusted

- The 53 cards (`web/game.json`) come from messages the team already wrote and vetted: the demo examples,
  ScamBench and the call descriptions. None is a real person's message.
- `scripts/build_game.py` keeps a card only when Sahayak's own check agrees with its answer: Scam for a scam, No scam
  signs for a real one. So the game never teaches anything the checker would contradict.
- The feedback comes from the phone's own checker, at the moment of the answer, from the same signed packs.
- Real delivery-code messages are left out for now. They are genuine, but they ask you to hand over a code, which
  would contradict the lesson for real messages.
- `tests/test_game.py` fails if a card and the checker ever disagree, or if `game.json` is out of date.

### If a judge asks

> "Sahayak checks a message when you have one. Spot the scam trains people before the message arrives: 5 cards,
> a minute a day, and every lesson is Sahayak's own reasoning. A grandmother can play it on the CSC's Wi-Fi or at home
> with no internet, in her own language, and nothing about her leaves the phone."

## Run it

```
python -m sahayak                 # the node; open the phone page, tap Learn
python scripts/build_tryit.py     # the stand-alone site, with the game
python scripts/build_game.py      # rebuild web/game.json after a fraud pack changes
```

Deep links: `?screen=learn` opens the Learn tab, `?play=1` starts a round, `?play=daily` starts today's message.

## Measured (14 Oct)

- 53 cards: 39 scams in 7 groups and 14 real messages. Every card's verdict is the same on the phone and on the node.
- Tests on Python 3.11: 493 passed, 6 skipped, including the 4 new game tests.
- `scripts/i18n_screens.py`: all 23 languages × 3 screens pass with the new look.
- On the node: no script errors and no failed requests. On the stand-alone build: swiping answers in English and Urdu,
  and today's message, work.
