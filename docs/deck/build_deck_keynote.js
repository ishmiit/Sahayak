// Sahayak keynote deck for the Grand Jury Round (Ideas for India 2026, Delhi, 14 Oct 2026): fourteen slides, one idea
// each, in the order of the script in docs/deck/keynote_script.json (whose lines become the speaker notes). Every
// slide carries short cues and the speech tells the story around them, so nothing is read off the screen. One QR code, on slide 7.
// Sahayak's numbers come from bench/results/*.json, outside numbers from docs/deck/facts_v3.json, so the deck never
// drifts from the evidence. Screenshots are of the app as it runs on a phone (docs/deck/img).
// Build: NODE_PATH=<folder with pptxgenjs> [DECK_OUT=name.pptx] [PPTX_SKILL=<pptx skill dir>] node docs/deck/build_deck_keynote.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const R = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "bench", "results", f), "utf8"));
const F = JSON.parse(fs.readFileSync(path.join(__dirname, "facts_v3.json"), "utf8"));
const SCRIPT = JSON.parse(fs.readFileSync(path.join(__dirname, "keynote_script.json"), "utf8"));
const IMG = (f) => path.join(__dirname, "img", f);
const OUT = path.join(__dirname, process.env.DECK_OUT || "Sahayak_Keynote_v5.pptx");

/* ---------------------------------------------------------------- numbers, all read from files */
const pub = R("public_v0.json").first;                                     // real published messages, first run
const pH = pub.systems.full.groups.hindi_english_hinglish;
const blind = R("redteam_v1_blind.json").first.systems.full.groups.hindi_english_hinglish;
const sb = R("scambench_v0_test.json").systems.full.flagged;              // our own frozen test split
const llm = R("llm_baseline.json"), lp = llm.sets.public_v0;
const parity = R("phone_parity.json");
const lossCrore = Number(F.fraud_2025.value.replace(/[^\d]/g, ""));       // 22495
const perMin = (lossCrore * 1e7 * 60) / (365 * 24 * 3600);               // rupees lost every minute, on average
const lakhMin = Math.round(perMin / 1e5);                                 // 4
const num = (x) => Number(x).toLocaleString("en-IN");
const of = (k, n) => `${num(k)} of ${num(n)}`;
const in10 = Math.round((10 * pH.caught) / pH.scams);                    // 7
const [vvHave, vvAll] = F.vay_vandana.value.match(/[\d.]+/g).map(Number); // 1.1 of ~6 (crore)
const parityOk = parity.fraud.cases - parity.fraud.mismatches;
// The per-counter figures come from the team's budget appendix (../Finale_Prep/04_Budget_and_Who_Pays.md, 7 Oct).
const PILOT = { total: F.pilot_budget.value, perCounter: "₹24,000", operator: "₹9,600" };
function need(ok, what) { if (!ok) throw new Error(`build_deck_keynote: ${what}`); }
need(lakhMin === 4, `the script says "about four lakh rupees" a minute; the facts now give ${perMin.toFixed(0)}`);
need(in10 === 7, `the script says "seven in ten"; the real-message result is now ${pH.caught}/${pH.scams}`);
need(lp.llm.false_alarms === 21 && lp.llm.genuine === 34 && lp.sahayak.false_alarms === 11, "the script's 21 of 34 and 11 no longer match llm_baseline.json");
need(lp.llm.caught > lp.sahayak.caught, "the script says the model caught more scams");
need(sb.tp === 34 && sb.tp + sb.fn === 37, "the script says 34 of 37 on our own set");
need(blind.caught === 92 && blind.scams === 103, "the script says 92 of 103 on the blind red team");
need(parityOk === 1841 && parity.fraud.cases === 1841, "the script says 1,841 checks");
need(vvHave / vvAll < 0.2, "the script says fewer than one in five over-70s had the card");
need(F.cscs.value === "6 lakh", "the script says six lakh CSCs");
const KYC = JSON.parse(fs.readFileSync(path.join(ROOT, "packs", "demo.v1.json"), "utf8")).examples.find((e) => e.id === "kyc_hi");
const SITE = F.tryit_url.replace(/^https:\/\//, "").replace(/\/$/, "");
const REPO = "github.com/ishmiit/Sahayak";

/* ---------------------------------------------------------------- design: black stage, one accent per slide */
const THEME = {
  name: "Sahayak Keynote", headFontFace: "Arial", bodyFontFace: "Arial",
  colors: { dk1: "000000", lt1: "F5F5F7", dk2: "161618", lt2: "A1A1A6", accent1: "6FA8FF", accent2: "E2C28A", accent3: "4FD68A",
            accent4: "FF5A52", accent5: "1C1C1E", accent6: "6E6E73", hlink: "6FA8FF", folHlink: "91C1FF" },
};
const BG = "000000", CARD = "161618", CARD2 = "1C1C1E", EDGE = "2C2C30", LINE = "3A3A3E";
const INK = "F5F5F7", MUTE = "A1A1A6", FAINT = "6E6E73", BLUE = "6FA8FF", CHAMP = "E2C28A", MINT = "4FD68A", RED = "FF5A52";
const HF = "Arial", DF = "Nirmala UI";
const W = 13.333, H = 7.5, M = 0.9;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Ishmiit Singh, Roshan Raj";
pres.title = "Sahayak: keynote for the Grand Jury Round, Ideas for India 2026";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.defineSlideMaster({ title: "STAGE", background: { color: BG }, objects: [] });

const T = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, fontFace: HF, margin: 0, valign: "top", color: INK }, o));
const eyebrow = (s, text, color, x, y, w) => T(s, text.toUpperCase(), { x, y, w: w || 8, h: 0.34, fontSize: 14, bold: true, color, charSpacing: 3, objectName: "eyebrow" });
const source = (s, text) => T(s, text, { x: M, y: H - 0.5, w: W - 2 * M, h: 0.28, fontSize: 10.5, color: FAINT, objectName: "source" });
const rule = (s, x, y, w, name) => s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: LINE, width: 0.75 }, objectName: name || "rule" });
// Talking points: a hairline above each, the lead words in white and the rest in grey
function points(s, items, { x, y, w, step, size, lead }) {
  items.forEach((it, i) => {
    const [a, b, c] = Array.isArray(it) ? it : [it];
    const yy = y + i * step;
    rule(s, x, yy, w, `point ${i + 1} rule`);
    const runs = [{ text: a, options: { bold: true, color: c || lead || INK } }];
    if (b) runs.push({ text: ` ${b}`, options: { color: MUTE } });
    T(s, runs, { x, y: yy + 0.11, w, h: step - 0.14, fontSize: size || 20, objectName: `point ${i + 1}` });
  });
}
// The phones are English screenshots of the live app (402 x 874 CSS px at 3x, 14 Oct 2026), framed as an iPhone with a
// status bar by the team's frame script; each PNG already carries its own bezel.
function phone(s, img, x, y, h, name) {
  const w = h * (1302 / 2718);
  s.addImage({ path: img, x, y, w, h, objectName: name, altText: `Screenshot: ${name}` });
  return w;
}
function chip(s, x, y, n, color, d) {
  d = d || 0.5;
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: color || BLUE }, line: { type: "none" }, objectName: `number ${n}` });
  T(s, String(n), { x, y, w: d, h: d, fontSize: d > 0.45 ? 18 : 14, bold: true, color: BG, align: "center", valign: "middle", objectName: `number ${n} label` });
}
function pill(s, x, y, w, text) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.52, rectRadius: 0.26, fill: { color: CARD2 }, line: { color: EDGE, width: 0.75 }, objectName: `pill: ${text}` });
  T(s, text, { x, y, w, h: 0.52, fontSize: 15, color: INK, align: "center", valign: "middle", objectName: `pill text: ${text}` });
}

// Speaker notes from the script: what to do and what to say, in order
function notes(n) {
  const sl = SCRIPT.slides.find((x) => x.n === n);
  const who = { I: "ISHMIIT", R: "ROSHAN" };
  const lines = [`SHOW: ${sl.show}`, ""];
  for (const st of sl.steps) {
    if (st.do) lines.push(`DO: ${st.do}${st.hold ? ` (about ${st.hold} s)` : ""}`);
    else lines.push(`${who[st.who]}: ${st.say.replace(/\n/g, " ")}`);
  }
  return lines.join("\n");
}
let s;
const slide = (section) => { pres.addSection({ title: section }); s = pres.addSlide({ masterName: "STAGE", sectionTitle: section }); return s; };

/* ---------------------------------------------------------------- 1 THE MESSAGE: the scam SMS, as a phone shows it */
slide("The message");
const [smsText, smsLink] = KYC.text.split(/\s*लिंक:\s*/);
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.4, y: 1.15, w: 8.53, h: 4.0, rectRadius: 0.4, fill: { color: CARD2 }, line: { color: EDGE, width: 1 }, objectName: "SMS card" });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.85, y: 1.55, w: 0.48, h: 0.48, rectRadius: 0.12, fill: { color: MINT }, line: { type: "none" }, objectName: "SMS icon" });
T(s, [{ text: "SMS", options: { bold: true, color: INK } }, { text: `   ${KYC.sender}`, options: { color: MUTE } }], { x: 3.5, y: 1.55, w: 5, h: 0.48, fontSize: 19, valign: "middle", objectName: "sender" });
T(s, "9:02 PM", { x: 8.6, y: 1.55, w: 1.9, h: 0.48, fontSize: 17, color: MUTE, align: "right", valign: "middle", objectName: "time" });
T(s, smsText.trim(), { x: 2.85, y: 2.3, w: 7.65, h: 1.85, fontSize: 28, fontFace: DF, color: INK, objectName: "the SMS, in Hindi" });
T(s, `लिंक: ${smsLink || ""}`.trim(), { x: 2.85, y: 4.25, w: 7.65, h: 0.5, fontSize: 20, fontFace: DF, color: BLUE, objectName: "the link" });
T(s, "“Your SBI KYC has expired. Update now, or your account will be closed tonight.”", { x: 1.4, y: 5.55, w: 10.53, h: 0.5, fontSize: 20, italic: true, color: MUTE, align: "center", objectName: "English" });
source(s, "A demo message, written by the team in the style of real KYC scams");
s.addNotes(notes(1));

/* ---------------------------------------------------------------- 2 WHO READS IT */
slide("Who reads it");
eyebrow(s, "Who reads it", BLUE, 1.6, 0.95);
[["74.", INK], ["9 PM.", INK], ["Bank closed.", INK], ["Alone.", CHAMP]].forEach(([t, c], i) =>
  T(s, t, { x: 1.6, y: 1.45 + i * 1.12, w: 10, h: 1.0, fontSize: 60, bold: true, color: c, valign: "middle", objectName: `line ${i + 1}` }));
source(s, "A demo persona, not a real person");
s.addNotes(notes(2));

/* ---------------------------------------------------------------- 3 EVERY MINUTE */
slide("Every minute");
T(s, `₹${lakhMin} lakh`, { x: M, y: 0.95, w: 11.5, h: 2.5, fontSize: 160, bold: true, color: CHAMP, valign: "middle", objectName: "the number" });
T(s, "lost to cyber fraud in India, every minute, on average.", { x: M + 0.08, y: 3.55, w: 11.5, h: 0.7, fontSize: 30, color: INK, objectName: "what it means" });
[[F.fraud_2025.value, "lost in 2025, across 24 lakh complaints"], [F.seniors_2025.value, "of it, from senior citizens"]].forEach(([a, b], i) => {
  const x = M + 0.08 + i * 5.6;
  rule(s, x, 4.85, 5.0, `stat ${i + 1} rule`);
  T(s, a, { x, y: 5.0, w: 5.0, h: 0.65, fontSize: 32, bold: true, objectName: `stat ${i + 1}` });
  T(s, b, { x, y: 5.65, w: 5.0, h: 0.4, fontSize: 17, color: MUTE, objectName: `stat ${i + 1} label` });
});
source(s, `${F.fraud_2025.source}; seniors: ${F.seniors_2025.source}. Spread evenly over the year, ₹22,495 crore is about ₹${num(Math.round(perMin / 60))} a second.`);
s.addNotes(notes(3));

/* ---------------------------------------------------------------- 4 INTRODUCING SAHAYAK */
slide("Introducing Sahayak");
eyebrow(s, "Introducing", BLUE, M, 0.95);
T(s, [{ text: "Sahayak", options: { color: INK } }, { text: "  सहायक", options: { color: BLUE, fontFace: DF, fontSize: 48 } }],
  { x: M, y: 1.3, w: 8.5, h: 1.35, fontSize: 88, bold: true, valign: "middle", objectName: "name" });
T(s, "Someone to ask, before you tap.", { x: M, y: 2.75, w: 8, h: 0.5, fontSize: 24, italic: true, color: MUTE, objectName: "tagline" });
points(s, [["Spot a scam before the money moves."], ["Claim what you’re owed.", null, BLUE]], { x: M, y: 3.55, w: 7.6, step: 0.72, size: 26 });
[["CSC counter + your phone", 2.65], ["Works offline", 1.65], ["22 Indian languages", 2.4]].reduce((x, [t, w]) => { pill(s, x, 5.2, w, t); return x + w + 0.18; }, M);
T(s, "Ishmiit Singh  ·  Roshan Raj", { x: M, y: H - 0.85, w: 7, h: 0.35, fontSize: 15, color: FAINT, objectName: "team" });
phone(s, IMG("keynote_home_en.png"), 9.5, 0.65, 6.2, "Sahayak home screen");
s.addNotes(notes(4));

/* ---------------------------------------------------------------- 5 IT TELLS HER WHY */
slide("It tells her why");
phone(s, IMG("keynote_scam_en.png"), 1.0, 0.65, 6.2, "Sahayak's answer to the KYC SMS");
const RX = 4.95, RW = 7.5;
eyebrow(s, "Back to her message", BLUE, RX, 0.85);
T(s, "Scam.", { x: RX, y: 1.2, w: RW, h: 1.05, fontSize: 70, bold: true, color: RED, valign: "middle", objectName: "verdict" });
eyebrow(s, "Why", FAINT, RX, 2.5);
points(s, [["Personal number"], ["Fake SBI link"], ["KYC never by link"]], { x: RX, y: 2.85, w: RW, step: 0.55, size: 21 });
eyebrow(s, "What to do", FAINT, RX, 4.65);
points(s, [["Don’t tap · keep the proof"], ["Money gone? 1930"], ["Warn the family"]], { x: RX, y: 5.0, w: RW, step: 0.55, size: 21 });
source(s, "Demo persona and SMS written by the team · the app’s answer, on a phone, 14 Oct 2026");
s.addNotes(notes(5));

/* ---------------------------------------------------------------- 6 WHAT SHE IS OWED */
slide("What she is owed");
eyebrow(s, "What she’s owed", CHAMP, M, 0.85);
T(s, "₹5 lakh", { x: M, y: 1.2, w: 7.8, h: 1.45, fontSize: 100, bold: true, color: BLUE, valign: "middle", objectName: "cover" });
T(s, "of free hospital care, every year.", { x: M, y: 2.75, w: 7.8, h: 0.55, fontSize: 28, bold: true, objectName: "what it is" });
points(s, [["Vay Vandana card", "· every Indian 70+"], ["Fewer than 1 in 5", "· had it by Feb 2026", CHAMP], ["5 questions", "· the words to say"]],
  { x: M, y: 3.65, w: 7.6, step: 0.62, size: 20 });
T(s, [{ text: "Stop the scam. ", options: { color: INK } }, { text: "Claim what you’re owed.", options: { color: BLUE } }], { x: M, y: 5.75, w: 7.8, h: 0.5, fontSize: 24, bold: true, objectName: "both" });
source(s, `${vvHave} of ~${vvAll} crore aged 70+ had the card (${F.vay_vandana.source.split(";")[0]}) · shared with a spouse also 70+; hospital care only · screenshot: result for a 74-year-old`);
phone(s, IMG("keynote_owed_en.png"), 9.5, 0.65, 6.2, "Sahayak's benefits result for a 74-year-old");
s.addNotes(notes(6));

/* ---------------------------------------------------------------- 7 TRY IT: the deck's only QR code */
slide("Try it");
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 1.0, y: 1.25, w: 4.75, h: 4.75, rectRadius: 0.25, fill: { color: "FFFFFF" }, line: { type: "none" }, objectName: "QR card" });
s.addImage({ path: IMG("tryit_qr.png"), x: 1.2, y: 1.45, w: 4.35, h: 4.35, objectName: "QR code", altText: `QR code for ${F.tryit_url}` });
T(s, SITE, { x: 0.7, y: 6.25, w: 5.35, h: 0.4, fontSize: 17, bold: true, color: BLUE, align: "center", objectName: "address" });
T(s, "Try it.", { x: 6.6, y: 1.2, w: 6, h: 0.9, fontSize: 56, bold: true, objectName: "title" });
T(s, "Right now, on your phone.", { x: 6.6, y: 2.15, w: 6, h: 0.5, fontSize: 24, color: MUTE, objectName: "subtitle" });
[["Scan the code.", "Nothing to install. No account."],
 ["Tap “Check a message”", "then “Pay ₹500 for your Ayushman card”."],
 ["Turn on airplane mode.", "Try another. It still works."]].forEach(([a, b], i) => {
  const y = 3.1 + i * 1.08;
  chip(s, 6.6, y + 0.03, i + 1);
  T(s, a, { x: 7.35, y, w: 5.4, h: 0.45, fontSize: 21, bold: true, objectName: `step ${i + 1}` });
  T(s, b, { x: 7.35, y: y + 0.47, w: 5.4, h: 0.42, fontSize: 18, color: MUTE, objectName: `step ${i + 1} detail` });
});
T(s, [{ text: "Opens in English. Tap EN for any of 22 Indian languages." }], { x: 6.6, y: 6.25, w: 6, h: 0.4, fontSize: 16, color: FAINT, objectName: "language" });
s.addNotes(notes(7));

/* ---------------------------------------------------------------- 8 HOW IT WORKS */
slide("How it works");
T(s, "How it works", { x: M, y: 0.8, w: 10, h: 0.85, fontSize: 44, bold: true, objectName: "title" });
[["You ask.", ["Type · Speak", "A call · A UPI QR"], BLUE, null],
 ["Rules decide.", ["64 signals", "On the device"], MINT, null],
 ["A clear answer.", ["4 answers"], CHAMP, "Never “safe”."]].forEach(([a, list, c, last], i) => {
  const x = M + i * 3.95;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.15, w: 3.65, h: 3.1, rectRadius: 0.18, fill: { color: CARD }, line: { color: EDGE, width: 1 }, objectName: `card ${i + 1}` });
  chip(s, x + 0.35, 2.5, i + 1, c);
  T(s, a, { x: x + 0.35, y: 3.2, w: 3.1, h: 0.6, fontSize: 28, bold: true, objectName: `card ${i + 1} title` });
  const runs = list.map((t, j) => ({ text: t, options: { breakLine: j < list.length - 1 || !!last } }));
  if (last) runs.push({ text: last, options: { color: c, bold: true } });
  T(s, runs, { x: x + 0.35, y: 3.95, w: 3.1, h: 1.2, fontSize: 22, color: MUTE, paraSpaceAfter: 5, objectName: `card ${i + 1} points` });
});
T(s, [{ text: "Phone = counter: ", options: { color: MUTE } }, { text: `${of(parityOk, parity.fraud.cases)} checks.`, options: { bold: true, color: INK } }],
  { x: M, y: 5.7, w: W - 2 * M, h: 0.45, fontSize: 22, objectName: "parity" });
s.addNotes(notes(8));

/* ---------------------------------------------------------------- 9 WHY RULES DECIDE (Roshan) */
slide("Why rules decide");
eyebrow(s, "Round one: a large AI model would decide", CHAMP, M, 0.8, 11);
T(s, "So we tested one.", { x: M, y: 1.15, w: 11, h: 0.85, fontSize: 44, bold: true, objectName: "title" });
[["A 3B language model", lp.llm, CARD, EDGE, INK, RED], ["Sahayak", lp.sahayak, "111B2B", "2F4A75", BLUE, INK]].forEach(([name, r, fill, edge, nc, fc], i) => {
  const x = M + i * 5.85, y = 2.35, w = 5.6;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 3.05, rectRadius: 0.18, fill: { color: fill }, line: { color: edge, width: 1 }, objectName: `${name} panel` });
  T(s, name, { x: x + 0.4, y: y + 0.3, w: w - 0.8, h: 0.5, fontSize: 24, bold: true, color: nc, objectName: `${name} name` });
  [["Scams caught", of(r.caught, r.scams), INK], ["Genuine messages flagged", of(r.false_alarms, r.genuine), fc]].forEach(([lab, val, vc], j) => {
    const yy = y + 1.0 + j * 1.0;
    T(s, lab.toUpperCase(), { x: x + 0.4, y: yy, w: w - 0.8, h: 0.3, fontSize: 12, bold: true, color: FAINT, charSpacing: 1.5, objectName: `${name} ${lab} label` });
    T(s, val, { x: x + 0.4, y: yy + 0.3, w: w - 0.8, h: 0.6, fontSize: 36, bold: true, color: vc, objectName: `${name} ${lab}` });
  });
});
T(s, [{ text: "A warning that cries wolf gets ignored.", options: { color: MUTE, breakLine: true } }, { text: "So rules decide, and every answer says why.", options: { color: BLUE } }],
  { x: M, y: 5.6, w: W - 2 * M, h: 0.95, fontSize: 24, bold: true, objectName: "conclusion" });
source(s, `${llm.model}, zero-shot, on the same ${lp.n} real published messages, first runs, 7 Oct 2026. In languages Sahayak can’t read yet, the model caught ${of(llm.sets.redteam_v1_blind.other_languages.llm.caught, llm.sets.redteam_v1_blind.other_languages.llm.scams)} scams.`);
s.addNotes(notes(9));

/* ---------------------------------------------------------------- 10 THE HONEST NUMBER */
slide("The honest number");
eyebrow(s, "We could have shown you", FAINT, M, 0.95, 4);
[[of(sb.tp, sb.tp + sb.fn), "on messages we wrote"], [of(blind.caught, blind.scams), "on a blind red team, written by an AI that never saw our code"]].forEach(([n, l], i) => {
  const y = 1.45 + i * 1.75;
  rule(s, M, y, 3.6, `bigger number ${i + 1} rule`);
  T(s, n, { x: M, y: y + 0.15, w: 3.6, h: 0.7, fontSize: 40, bold: true, color: FAINT, objectName: `bigger number ${i + 1}` });
  T(s, l, { x: M, y: y + 0.85, w: 3.6, h: 0.7, fontSize: 15, color: FAINT, objectName: `bigger number ${i + 1} label` });
});
s.addShape(pres.shapes.LINE, { x: 5.0, y: 1.0, w: 0, h: 4.4, line: { color: LINE, width: 0.75 }, objectName: "divider" });
eyebrow(s, "The honest number", BLUE, 5.6, 0.95, 6);
T(s, `${in10} in 10`, { x: 5.55, y: 1.25, w: 7, h: 2.3, fontSize: 150, bold: true, color: BLUE, valign: "middle", objectName: "headline number" });
T(s, `scams caught on ${num(pub.messages)} real messages people in India received.`, { x: 5.6, y: 3.7, w: 6.9, h: 0.95, fontSize: 25, bold: true, objectName: "what it counts" });
T(s, "Scored once.", { x: 5.6, y: 4.7, w: 6.9, h: 0.45, fontSize: 22, color: MUTE, objectName: "scored once" });
rule(s, M, 5.75, W - 2 * M, "not yet rule");
T(s, [{ text: "Not yet: ", options: { bold: true, color: CHAMP } }, { text: "real users, and messages from people’s own phones. That’s next.", options: { color: INK } }],
  { x: M, y: 5.9, w: W - 2 * M, h: 0.45, fontSize: 21, objectName: "not yet" });
source(s, `In Hindi, English and Hinglish: ${of(pH.caught, pH.scams)} scams caught, ${of(pH.false_alarm, pH.genuine)} genuine flagged; published by the Income Tax portal, PIB Fact Check and fact-checkers · first runs, bench/results`);
s.addNotes(notes(10));

/* ---------------------------------------------------------------- 11 THE PILOT */
slide("The pilot");
eyebrow(s, "The pilot", BLUE, M, 0.85);
T(s, "One district.", { x: M, y: 1.2, w: 11, h: 1.05, fontSize: 64, bold: true, valign: "middle", objectName: "scope" });
[["20", "villages", INK], ["50", "counters", INK], ["6", "months", INK], [`₹${PILOT.total.match(/[\d]+/)[0]} lakh`, "estimated", CHAMP]].forEach(([n, l, c], i) => {
  const x = M + i * 2.75, w = i === 3 ? 3.28 : 2.5;
  rule(s, x, 2.6, w, `stat ${i + 1} rule`);
  T(s, n, { x, y: 2.75, w, h: 0.9, fontSize: 52, bold: true, color: c, objectName: `stat ${i + 1}` });
  T(s, l, { x, y: 3.65, w, h: 0.4, fontSize: 18, color: MUTE, objectName: `stat ${i + 1} label` });
});
eyebrow(s, "The next 30 days", FAINT, M, 4.75);
["A field morning at a CSC", "Real messages from people’s own phones", "A district partner"].forEach((t, i) => {
  const x = M + i * 3.95;
  chip(s, x, 5.2, i + 1, BLUE, 0.42);
  T(s, t, { x: x + 0.6, y: 5.18, w: 3.2, h: 0.8, fontSize: 19, bold: true, objectName: `next ${i + 1}` });
});
source(s, `Estimates, not quotes: the team’s line-item budget, 7 Oct 2026 (${PILOT.total}). At 500 counters, about ${PILOT.perCounter} a counter a year; the operator’s ${PILOT.operator} is the biggest part.`);
s.addNotes(notes(11));

/* ---------------------------------------------------------------- 12 THE ASK */
slide("The ask");
T(s, [{ text: "India has ", options: { color: MUTE } }, { text: `${F.cscs.value} CSCs.`, options: { color: INK, bold: true } }, { text: "  We’re asking for ", options: { color: MUTE } }, { text: "50 counters.", options: { color: INK, bold: true } }],
  { x: M, y: 1.55, w: 11.5, h: 0.55, fontSize: 26, objectName: "scale" });
eyebrow(s, "Our ask", CHAMP, M, 2.6);
T(s, "Introduce us to one district.", { x: M, y: 2.95, w: 11.6, h: 1.3, fontSize: 56, bold: true, valign: "middle", objectName: "the ask" });
["One morning.", "Six months.", "Real numbers."].forEach((t, i) => {
  const x = M + i * 3.95;
  rule(s, x, 5.0, 3.6, `step ${i + 1} rule`);
  T(s, t, { x, y: 5.15, w: 3.85, h: 0.8, fontSize: 21, bold: true, color: i === 2 ? BLUE : INK, objectName: `step ${i + 1}` });
});
source(s, `${F.cscs.value} functional CSCs, 4.7 lakh at gram-panchayat level (MeitY, Mar 2025) · the pilot’s 50 counters: nodes at 20 CSCs, the phone app at 30 bank-agent points`);
s.addNotes(notes(12));

/* ---------------------------------------------------------------- 13 ONE MORE THING */
slide("One more thing");
eyebrow(s, "One more thing", BLUE, M, 1.2);
T(s, "Spot the scam.", { x: M, y: 1.6, w: 6.2, h: 1.05, fontSize: 54, bold: true, valign: "middle", objectName: "title" });
T(s, "Know a scam before it arrives.", { x: M, y: 2.75, w: 6.2, h: 0.5, fontSize: 24, italic: true, color: MUTE, objectName: "tagline" });
points(s, [["5 cards a round", "· scam or real?"], ["Sahayak’s own clues", "after every answer", BLUE], ["Levels, badges", "· a new message daily"]],
  { x: M, y: 3.6, w: 5.6, step: 0.68, size: 21 });
phone(s, IMG("keynote_game_card.png"), 6.95, 0.75, 5.75, "Spot the scam: a card");
phone(s, IMG("keynote_game_clues.png"), 9.8, 0.75, 5.75, "Spot the scam: Sahayak's clues after the answer");
source(s, "The Learn tab of the same app · every card agrees with Sahayak’s own check (tests/test_game.py) · nothing leaves the phone");
s.addNotes(notes(13));

/* ---------------------------------------------------------------- 14 SOMEONE TO ASK */
slide("Someone to ask");
T(s, "Nine at night. The bank is closed.", { x: 0.5, y: 1.25, w: W - 1, h: 0.6, fontSize: 30, color: FAINT, align: "center", objectName: "then" });
T(s, "Now she has someone to ask.", { x: 0.5, y: 1.95, w: W - 1, h: 1.2, fontSize: 60, bold: true, align: "center", valign: "middle", objectName: "now" });
rule(s, W / 2 - 0.6, 3.75, 1.2, "divider");
T(s, [{ text: "Sahayak", options: { color: INK } }, { text: "  सहायक", options: { color: BLUE, fontFace: DF, fontSize: 30 } }],
  { x: 0.5, y: 4.1, w: W - 1, h: 0.8, fontSize: 44, bold: true, align: "center", valign: "middle", objectName: "name" });
T(s, [{ text: "Spot the scam before the money moves.  ", options: { color: INK } }, { text: "Claim what you’re owed.", options: { color: BLUE } }],
  { x: 0.5, y: 5.0, w: W - 1, h: 0.5, fontSize: 22, align: "center", objectName: "promise" });
T(s, "Ishmiit Singh  ·  Roshan Raj", { x: 0.5, y: 6.25, w: W - 1, h: 0.4, fontSize: 17, color: MUTE, align: "center", objectName: "team" });
T(s, `Open source: ${REPO}`, { x: 0.5, y: 6.75, w: W - 1, h: 0.3, fontSize: 12, color: FAINT, align: "center", objectName: "repo" });
s.addNotes(notes(14));

need(pres.slides.length === SCRIPT.slides.length, `the deck has ${pres.slides.length} slides, the script ${SCRIPT.slides.length}`);

/* ---------------------------------------------------------------- write, then the theme */
pres.writeFile({ fileName: OUT }).then(async (f) => {
  const skill = process.env.PPTX_SKILL;
  if (skill) { const { applyTheme } = require(path.join(skill, "scripts", "apply_theme.js")); await applyTheme(f, THEME); }
  console.log("WROTE", f);
});
