// Sahayak deck for the Grand Jury Round (Ideas for India 2026, Delhi, 14 Oct 2026): seven slides, readable from 3 m.
// Same colours, fonts and helpers as deck v3 (copied from docs/deck/build_deck_v3.js), with larger type and fewer words.
// Sahayak's own numbers are read from bench/results/*.json and the signed packs in packs/; outside numbers from
// docs/deck/facts_v3.json, each with its source on the slide. First runs are the numbers quoted; real published
// messages (PublicBench) lead the evidence. Results not in hand yet appear only when their files exist: the stress
// test (bench/results/stress_v0.json), the field morning (bench/results/field_v0.json), PublicBench's post-fix score
// on its unread half ("latest" in public_v0.json) and the budget appendix (../Finale_Prep/04_Budget_and_Who_Pays.md).
// Build: NODE_PATH=<folder with pptxgenjs> node docs/deck/build_deck_jury.js   (writes docs/deck/Sahayak_Jury_Round_Deck.pptx)
const fs = require("fs");
const path = require("path");
const pptx = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const R = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "bench", "results", f), "utf8"));
const RQ = (f) => (fs.existsSync(path.join(ROOT, "bench", "results", f)) ? R(f) : null);  // optional results
const PACK = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "packs", f), "utf8"));
const F = JSON.parse(fs.readFileSync(path.join(__dirname, "facts_v3.json"), "utf8"));
const SHOT = (f) => path.join(__dirname, "img", f);
function need(ok, what) { if (!ok) throw new Error(`build_deck_jury: ${what}`); }

/* ---------------------------------------------------------------- numbers, all read from files */
const pub = R("public_v0.json");                              // real published messages, first run (7 Oct)
const blind = R("redteam_v1_blind.json");                     // blind red team, first run (7 Oct)
const sb = R("scambench_v0_test.json");                      // our own frozen test split, scored once (2 Oct)
const llmb = R("llm_baseline.json");                          // language-model baseline, first run (7 Oct)
const stress = RQ("stress_v0.json"), field = RQ("field_v0.json"), parity = RQ("phone_parity.json");
const fraudPack = PACK("fraud.v1.json"), schemes = PACK("schemes.v1.json"), demo = PACK("demo.v1.json");

// 95% Wilson interval: sound for small samples, where a bootstrap interval can reach 100%
function wilson(k, n) {
  if (!n) return [0, 0];
  const z = 1.96, p = k / n, d = 1 + z * z / n;
  const c = (p + z * z / (2 * n)) / d, h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}
const pct0 = (x) => `${Math.round(100 * x)}%`;
const num = (x) => Number(x).toLocaleString("en-IN");
const of = (k, n) => `${num(k)} of ${num(n)}`;
const in10 = (k, n) => Math.round(10 * k / n);
const day = (iso) => new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const lowerFirst = (t) => t.charAt(0).toLowerCase() + t.slice(1);
const plain = (t) => t.replace(/"/g, "");

// PublicBench v0: real messages people received, as published; first run
const pF = pub.first.systems.full.groups, pB = pub.first.systems.blocklist.groups;
const pH = pF.hindi_english_hinglish, pHB = pB.hindi_english_hinglish, pO = pF.other_indian_languages;
const pOtherGreens = pO.missed || 0;  // scams in languages Sahayak cannot read that were given "No scam signs"
const pTest = pub.latest ? [pF.test_half, pub.latest.systems.full.groups.test_half] : null;  // the unread half, before and after fixes
// Blind red team, first run
const bF = blind.first.systems.full.groups, bB = blind.first.systems.blocklist.groups;
const heh = bF.hindi_english_hinglish, hehB = bB.hindi_english_hinglish, oth = bF.other_indian_languages;
const othScamsUnchecked = oth.scams - (oth.caught || 0) - (oth.missed || 0);
const othGenuineUnchecked = oth.genuine - (oth.false_alarm || 0) - (oth.left_alone || 0);
need(othScamsUnchecked + othGenuineUnchecked === (oth.not_checked || 0), "blind red team: 'could not check' counts do not add up");
// ScamBench v0, our own frozen test split
const full = sb.systems.full.flagged, block = sb.systems.blocklist.flagged;
const sbScams = full.tp + full.fn, sbGenuine = full.fp + full.tn;
const sbCi = wilson(full.tp, sbScams);
const verdictMs = Math.round(sb.latency_ms_full.p50);
// Language-model baseline (first run): on the real published messages when measured (else the blind set), and on
// the ScamBench test split; the other-language count comes from the blind set, which has genuine messages there too
const lb = llmb.sets.public_v0 || llmb.sets.redteam_v1_blind, lt = llmb.sets.scambench_v0_test;
const lo = llmb.sets.redteam_v1_blind.other_languages.llm;
const lbWhat = llmb.sets.public_v0 ? "real published messages" : "blind messages";
const model = llmb.model.replace(":", " ");                                    // "qwen2.5 3b"
const modelSize = (llmb.model.match(/:(\d+(?:\.\d+)?)b/i) || [])[1];           // "3"
const modelShort = modelSize ? `${modelSize}B model` : "Language model";
const gpu = (llmb.hardware.match(/^[^(]+/) || [llmb.hardware])[0].trim();      // "Apple M3"
need(lt.llm.genuine === sbGenuine && lt.llm.scams === sbScams, "LLM baseline and ScamBench test split differ in size");

// The demo persona (jury kit card P4) and the SMS it receives (jury kit card M1), from the signed packs
const persona = schemes.demos.find((d) => d.id === "senior74");
const kyc = demo.examples.find((e) => e.id === "kyc_hi");
const feeExample = demo.examples.find((e) => e.id === "ayushman_fee");
const pmjay = schemes.schemes.find((x) => x.id === "pmjay");
const pmjay70 = pmjay.benefit_now.find((b) => b.when.age && b.when.age[0] === 70);
need(persona && kyc && feeExample && pmjay && pmjay70, "demo persona, demo SMS or PM-JAY entry missing from the packs");
need(persona.answers.age >= pmjay70.when.age[0], "the demo persona is not 70 or older");
const cover = (pmjay70.en.match(/₹[\d.,]+\s*lakh/) || [])[0];                  // "₹5 lakh"
need(cover, "no rupee amount in the PM-JAY 70+ line");
const V = (k) => fraudPack.verdicts[k].label.en;              // Scam, Suspicious, No scam signs, Could not check
const hasSchemeFee = Boolean(fraudPack.signals.scheme_fee);   // "pay ₹500 for your Ayushman card" is flagged from pack 1.4.0

// The stand-alone app judges open on their own phones; its QR image encodes the same URL (see build_deck_v3.js)
const TRYIT = F.tryit_url, TRYIT_QR = SHOT("tryit_qr.png");
need(TRYIT && fs.existsSync(TRYIT_QR), "try-it URL or QR image missing");
const tryitShort = TRYIT.replace(/^https:\/\//, "").replace(/\/$/, "");

// Who pays: the budget appendix when it exists, else the round-1 figure from the application the jury holds
// (Section 1, "Estimated Implementation budget": ~₹35–40 lakh for a 6-month, ~20-village pilot; ~50 BC/CSC agents).
const BUDGET_MD = path.resolve(ROOT, "..", "Finale_Prep", "04_Budget_and_Who_Pays.md");
const ROUND1_BUDGET = "₹35–40 lakh";
// From the budget file: the line-item table's Total ("₹… lakh"), and the lines of its "## 1." summary list that say
// what the pilot covers ("One district, …: ₹… lakh, …"), the cost per counter ("At 500 counters: …") and the payers
// to test ("After month six: …"). Anything not found is left off the slide, and the build says so.
function budgetFromFile() {
  if (!fs.existsSync(BUDGET_MD)) return null;
  const md = fs.readFileSync(BUDGET_MD, "utf8"), lines = md.split(/\r?\n/);
  const strip = (t) => t.replace(/[*_`]/g, "").trim();
  const cells = (l) => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(strip);
  const totalRow = lines.filter((l) => l.trim().startsWith("|")).map(cells).find((c) => c.some((x) => /^total$/i.test(x)));
  const amount = totalRow ? totalRow.find((x) => /^₹\s?[\d.,]+\s*lakh$/i.test(x)) : null;
  const summary = (md.split(/^## /m).find((sec) => /^1\.\s/.test(sec)) || "").split(/\r?\n/)
    .filter((l) => /^\d+\.\s/.test(l)).map((l) => strip(l.replace(/^\d+\.\s*/, "")));
  const pick = (re) => summary.find((t) => re.test(t)) || null;
  const scopeLine = pick(/^One district\b/i);
  return { amount, scope: scopeLine ? scopeLine.split(":")[0].trim() : null, perCounter: pick(/^At [\d,]+ counters\b/i), after: pick(/^After month\b/i) };
}
const budget = budgetFromFile();
if (budget) {
  console.log(`budget from ${BUDGET_MD}: ${JSON.stringify(budget)}`);
  for (const k of ["amount", "scope", "perCounter", "after"]) if (!budget[k]) console.log(`WARNING: budget file: no ${k} found; that line is left off slide 6`);
}

// The stress test, when its result file exists
let st = null;
if (stress) {
  const by = Object.fromEntries(stress.load.map((x) => [x.scenario, x]));
  const errors = stress.load.reduce((a, x) => a + Object.values(x.endpoints).reduce((b, e) => b + (e.errors || 0), 0), 0);
  st = { date: day(stress.date), errors, session: by.session, burst: by.burst, soak: by.soak, fuzz: stress.fuzz, phone: stress.phone };
  // The first run (7 Oct) found faults that were then fixed (PROGRESS.md D29, D30); a clean result file is the re-run
  st.clean = errors === 0 && stress.fuzz.unexpected.length === 0 && stress.fuzz.node_alive_after !== false;
}

/* ---------------------------------------------------------------- design (from deck v3) */
const P = new pptx();
P.defineLayout({ name: "W", width: 13.33, height: 7.5 }); P.layout = "W"; P.author = "Roshan Raj, Ishmiit Singh";
P.title = "Sahayak: Grand Jury Round, Ideas for India 2026";
const BG = "0B0F14", CARD = "152017", CARD2 = "1B2A20", BORDER = "2C4636";
const INK = "EEF3EE", MUTE = "9DB0A4", FAINT = "6E8579";
const GRN = "27C08A", SAF = "FF9E3D", MINT = "4FE3B0";
const HF = "Arial", BF = "Calibri", DF = "Nirmala UI";  // DF: Devanagari, for Hindi text
function shadow() { return { type: "outer", color: "000000", opacity: .4, blur: 10, offset: 3, angle: 90 }; }
function bg(s) {
  s.background = { color: BG };
  s.addShape(P.ShapeType.ellipse, { x: 12.55, y: .42, w: .12, h: .12, fill: { color: SAF }, line: { type: "none" } });
  s.addShape(P.ShapeType.ellipse, { x: 12.75, y: .42, w: .12, h: .12, fill: { color: INK }, line: { type: "none" } });
  s.addShape(P.ShapeType.ellipse, { x: 12.95, y: .42, w: .12, h: .12, fill: { color: GRN }, line: { type: "none" } });
}
function eye(s, t) {
  s.addShape(P.ShapeType.ellipse, { x: .62, y: .66, w: .15, h: .15, fill: { color: GRN }, line: { type: "none" } });
  s.addText(t.toUpperCase(), { x: .87, y: .5, w: 11.4, h: .47, fontFace: HF, fontSize: 15, bold: true, color: GRN, charSpacing: 2, valign: "middle", margin: 0 });
}
function title(s, t, c) { s.addText(t, { x: .6, y: .98, w: 12.1, h: .95, fontFace: HF, fontSize: 32, bold: true, color: c || INK, valign: "middle", margin: 0 }); }
function card(s, x, y, w, h, f, edge) { s.addShape(P.ShapeType.roundRect, { x, y, w, h, rectRadius: .1, fill: { color: f || CARD }, line: { color: edge || BORDER, width: edge ? 1.5 : 1 }, shadow: shadow() }); }
// Three equal cards; each body is a string or an array of text runs
function cols3(s, items, y, h, headSize) {
  items.forEach((c, i) => {
    const x = .6 + i * 4.12; card(s, x, y, 3.85, h);
    s.addText(c[0], { x: x + .3, y: y + .2, w: 3.3, h: .5, fontFace: HF, fontSize: headSize || 21, bold: true, color: c[2], valign: "top", margin: 0 });
    if (c[1]) s.addText(c[1], { x: x + .3, y: y + .8, w: 3.3, h: h - .95, fontFace: BF, fontSize: 16, color: MUTE, valign: "top", margin: 0 });
  });
}
function sources(s, text) { s.addText(`Sources: ${text}`, { x: .6, y: 6.98, w: 12.1, h: .38, fontFace: BF, fontSize: 12, color: FAINT, margin: 0, valign: "top" }); }
// Bullet runs, for a text box of their own or a cols3 body
const bullets = (lines, color) => lines.map((t, i) => ({ text: t, options: { bullet: { code: "2022" }, color: color || MUTE, breakLine: i < lines.length - 1, paraSpaceAfter: 6 } }));
// A numbered chip
function chip(s, x, y, n, d) {
  s.addShape(P.ShapeType.ellipse, { x, y, w: d || .55, h: d || .55, fill: { color: GRN }, line: { type: "none" } });
  s.addText(String(n), { x, y, w: d || .55, h: d || .55, fontFace: HF, fontSize: 18, bold: true, color: BG, align: "center", valign: "middle", margin: 0 });
}
// A number with its denominator: "92" large, " of 103" smaller
const big = (n, rest, color, size) => [{ text: n, options: { fontSize: size || 40, bold: true, color } }, { text: rest, options: { fontSize: Math.round((size || 40) / 2), bold: true, color } }];
// An evidence tile: a label, one number with its denominator, what it counts, and one or two lines of detail
function tile(s, x, y, w, h, t) {
  card(s, x, y, w, h, CARD);
  s.addText(t.label.toUpperCase(), { x: x + .25, y: y + .14, w: w - .4, h: .3, fontFace: HF, fontSize: 12.5, bold: true, color: t.color, charSpacing: .5, valign: "middle", margin: 0 });
  s.addText(big(t.n, t.rest, t.color, 36), { x: x + .25, y: y + .46, w: w - .4, h: .56, fontFace: HF, valign: "middle", margin: 0 });
  s.addText(t.what, { x: x + .25, y: y + 1.02, w: w - .4, h: .34, fontFace: BF, fontSize: 16, bold: true, color: INK, valign: "middle", margin: 0 });
  s.addText(t.detail, { x: x + .25, y: y + 1.38, w: w - .4, h: h - 1.46, fontFace: BF, fontSize: 14, color: MUTE, valign: "top", margin: 0 });
}

/* 1 TITLE, with the opening line */
const OPENING = [`India opened ${F.jan_dhan.value} Jan Dhan accounts.`,
  "Sahayak helps those account holders spot a scam before the money moves, and claim what they are owed."];
let s = P.addSlide(); bg(s);
s.addText([{ text: "SAHAYAK", options: { color: INK } }, { text: "  सहायक", options: { color: GRN, fontFace: DF, fontSize: 40 } }],
  { x: .7, y: .95, w: 12, h: 1.15, fontFace: HF, fontSize: 60, bold: true, margin: 0, charSpacing: 1, valign: "middle" });
s.addText("Offline. Vernacular. On your side.", { x: .72, y: 2.12, w: 11.6, h: .55, fontFace: HF, fontSize: 24, bold: true, color: GRN, margin: 0 });
s.addShape(P.ShapeType.rect, { x: .72, y: 3.0, w: .09, h: 1.95, fill: { color: SAF }, line: { type: "none" } });
s.addText([{ text: OPENING[0], options: { breakLine: true } }, { text: OPENING[1] }],
  { x: 1.05, y: 2.95, w: 11.4, h: 2.05, fontFace: HF, fontSize: 30, bold: true, color: INK, valign: "middle", margin: 0, paraSpaceAfter: 8 });
s.addText("At the CSC counter and on their own phone · no internet · Hindi and English, by voice or touch · built and measured",
  { x: 1.05, y: 5.15, w: 11.4, h: .62, fontFace: BF, fontSize: 18, color: MUTE, valign: "top", margin: 0 });
s.addText([{ text: "Ideas for India 2026", options: { bold: true, color: INK } }, { text: "  ·  Inclusive Innovation for Bharat · Financial Inclusion  ·  Grand Jury Round, Delhi, 14 October 2026", options: { color: MUTE } }],
  { x: .72, y: 6.2, w: 12, h: .4, fontFace: BF, fontSize: 16, margin: 0 });
s.addText("Roshan Raj  ·  Ishmiit Singh", { x: .72, y: 6.62, w: 12, h: .4, fontFace: BF, fontSize: 16, color: MUTE, margin: 0 });
s.addNotes(`Say the opening line word for word, then go straight to slide 2. If the slot is 90 seconds: slides 1, 2, 5 and 7 (the QR code is on 3 and 7). In 4 minutes: all seven, with the judges trying it on slide 3. In 7 minutes: add a live check on the demo phone at slide 3 and take the round-1 story on slide 4 slowly. The ${F.jan_dhan.value} counts accounts, not people (${F.jan_dhan.source}).`);

/* 2 THE PROBLEM: one number, one demo persona */
s = P.addSlide(); bg(s); eye(s, "The problem"); title(s, "Lost to fraud, and missing what they are owed");
const [fraudNum, ...fraudUnit] = F.fraud_2025.value.split(" ");
card(s, .6, 2.05, 3.95, 4.75, CARD2);
s.addText(fraudNum, { x: .85, y: 2.3, w: 3.5, h: 1.0, fontFace: HF, fontSize: 52, bold: true, color: SAF, valign: "middle", margin: 0 });
s.addText(fraudUnit.join(" "), { x: .85, y: 3.25, w: 3.5, h: .6, fontFace: HF, fontSize: 30, bold: true, color: SAF, valign: "top", margin: 0 });
s.addText(F.fraud_2025.text, { x: .85, y: 4.05, w: 3.45, h: 1.4, fontFace: BF, fontSize: 21, color: INK, valign: "top", margin: 0 });
card(s, 4.8, 2.05, 5.3, 4.75, CARD);
s.addText("DEMO PERSONA · NOT A REAL PERSON", { x: 5.08, y: 2.2, w: 4.8, h: .34, fontFace: HF, fontSize: 13, bold: true, color: SAF, charSpacing: 1, valign: "middle", margin: 0 });
s.addText(`Aged ${persona.answers.age}, with a BPL ration card and a bank account`, { x: 5.08, y: 2.56, w: 4.85, h: .7, fontFace: HF, fontSize: 18, bold: true, color: INK, valign: "top", margin: 0 });
s.addText(`An SMS arrives from ${kyc.sender}:`, { x: 5.08, y: 3.3, w: 4.8, h: .32, fontFace: BF, fontSize: 16, color: MUTE, valign: "middle", margin: 0 });
s.addShape(P.ShapeType.roundRect, { x: 5.08, y: 3.66, w: 4.75, h: 1.52, rectRadius: .1, fill: { color: "26372B" }, line: { type: "none" } });
s.addText(kyc.text, { x: 5.22, y: 3.7, w: 4.5, h: 1.44, fontFace: DF, fontSize: 16, color: INK, valign: "middle", margin: 0 });
s.addText("And is likely owed:", { x: 5.08, y: 5.27, w: 4.8, h: .32, fontFace: BF, fontSize: 16, color: MUTE, valign: "middle", margin: 0 });
s.addText(`The Ayushman Vay Vandana card: ${lowerFirst(pmjay70.en)}.`, { x: 5.08, y: 5.62, w: 4.85, h: 1.1, fontFace: BF, fontSize: 17, bold: true, color: GRN, valign: "top", margin: 0 });
s.addImage({ path: SHOT("03_result_kyc_hi.png"), x: 10.33, y: 2.05, w: 2.4, h: 4.25 });
s.addText("Sahayak's answer to that SMS", { x: 10.1, y: 6.36, w: 2.86, h: .45, fontFace: BF, fontSize: 15, bold: true, color: INK, align: "center", valign: "top", margin: 0 });
sources(s, `${F.fraud_2025.source}. Persona and SMS: jury kit cards P4 and M1, written by the team (not real messages); screenshot of the running app.`);
s.addNotes(`One number: ${F.fraud_2025.value} ${F.fraud_2025.text}. Then the demo persona, and say it is a demo persona: aged ${persona.answers.age}, a BPL card, a bank account. The SMS is a fake KYC message; Sahayak says ${V("scam")} and names three reasons (a personal number, a lookalike link, the KYC threat). The same person is likely owed the Vay Vandana card: hospital care only, not OPD, shared with a spouse who is also 70+.`);

/* 3 TRY IT NOW */
s = P.addSlide(); bg(s); eye(s, "Try it now"); title(s, "Try it on your own phone, right now");
s.addShape(P.ShapeType.roundRect, { x: .6, y: 2.05, w: 4.15, h: 4.15, rectRadius: .12, fill: { color: "FFFFFF" }, line: { type: "none" } });
s.addImage({ path: TRYIT_QR, x: .78, y: 2.23, w: 3.79, h: 3.79 });
s.addText(tryitShort, { x: .45, y: 6.32, w: 4.45, h: .45, fontFace: BF, fontSize: 18, bold: true, color: GRN, align: "center", valign: "middle", margin: 0 });
s.addText("Three things to try", { x: 5.15, y: 2.05, w: 7.5, h: .5, fontFace: HF, fontSize: 21, bold: true, color: INK, valign: "middle", margin: 0 });
[[`Tap “${plain(feeExample.label.en)}”`, `Sahayak says ${V("scam")}, and why: the card is free at the CSC.`],
 ["Turn on airplane mode", "Check another message: it still answers, on the phone itself."],
 ["Tap “What am I owed?”", `Answer as someone aged ${persona.answers.age}: health cover comes first.`]].forEach((c, i) => {
  const y = 2.7 + i * 1.22; card(s, 5.15, y, 7.58, 1.08);
  chip(s, 5.38, y + .26, i + 1);
  s.addText(c[0], { x: 6.15, y: y + .1, w: 6.4, h: .46, fontFace: HF, fontSize: 20, bold: true, color: INK, valign: "middle", margin: 0 });
  s.addText(c[1], { x: 6.15, y: y + .56, w: 6.4, h: .42, fontFace: BF, fontSize: 17, color: MUTE, valign: "middle", margin: 0 });
});
s.addText("No install, no account. Tap EN for English.", { x: 5.15, y: 6.36, w: 7.58, h: .42, fontFace: BF, fontSize: 16, color: MUTE, valign: "middle", margin: 0 });
s.addNotes(`Stop talking and let them try; walk round with the demo phone for anyone whose phone will not load it, and never debug a judge's phone. The public site was rebuilt on 7 Oct with the node's packs (fraud ${fraudPack.version}), "${V("unreadable")}" included; before Delhi, open phone-packs/fraud.json on the site and check it matches the node page.`);

/* 4 HOW IT WORKS, and the round-1 change, measured */
s = P.addSlide(); bg(s); eye(s, "How it works, and what changed since round 1"); title(s, "How it works, and why rules decide");
[["Ask, at the counter or on the phone", "Paste, speak, photograph, describe a call, or scan a UPI QR. Nothing leaves the device."],
 ["Rules decide, offline", `Named signals, a pattern matcher and a small classifier, from signed packs: about ${verdictMs} ms a check.`],
 ["A clear answer, with reasons", `${V("scam")}, ${V("suspicious")}, ${V("no_signs")} (never “safe”) or ${V("unreadable")}; what to do; a complaint draft.`],
 ["The same answer on the phone", parity ? `After one visit the phone runs the same engines offline: the node's exact answer on ${of(parity.fraud.cases - parity.fraud.mismatches, parity.fraud.cases)} test checks.`
   : "After one visit the phone runs the same engines offline."]].forEach((c, i) => {
  const y = 2.05 + i * 1.2; card(s, .6, y, 6.25, 1.08);
  chip(s, .82, y + .27, i + 1);
  s.addText(c[0], { x: 1.6, y: y + .08, w: 5.1, h: .4, fontFace: HF, fontSize: 18, bold: true, color: INK, valign: "middle", margin: 0 });
  s.addText(c[1], { x: 1.6, y: y + .47, w: 5.1, h: .56, fontFace: BF, fontSize: 15, color: MUTE, valign: "top", margin: 0 });
});
card(s, 7.05, 2.05, 5.68, 4.68, CARD2);
const lab = (t, y, c) => s.addText(t, { x: 7.33, y, w: 5.2, h: .3, fontFace: HF, fontSize: 13, bold: true, color: c, charSpacing: 1, valign: "middle", margin: 0 });
lab("ROUND 1 SAID", 2.2, SAF);
s.addText("A 14B language model, offline on the Crucible runtime, would decide, with a fine-tuned finance model.",
  { x: 7.33, y: 2.52, w: 5.2, h: .62, fontFace: BF, fontSize: 16, color: INK, valign: "top", margin: 0 });
lab(`WE MEASURED A MODEL: ${model.toUpperCase()}, ZERO-SHOT`, 3.22, MINT);
const th = (t) => ({ text: t, options: { bold: true, color: FAINT, fontSize: 13 } });
const td = (t, c, b) => ({ text: t, options: { color: c || INK, bold: Boolean(b), fontSize: 15 } });
s.addTable([
  [th(""), th("Scams caught"), th("Genuine flagged"), th("Per message")],
  [td(modelShort, MUTE), td(of(lb.llm.caught, lb.llm.scams)), td(of(lb.llm.false_alarms, lb.llm.genuine), SAF, true), td(`${lb.llm_seconds.median} s, GPU`)],
  [td("Sahayak", GRN, true), td(of(lb.sahayak.caught, lb.sahayak.scams)), td(of(lb.sahayak.false_alarms, lb.sahayak.genuine), GRN, true), td(`${lb.sahayak_ms_median} ms, CPU`)],
], { x: 7.25, y: 3.55, w: 5.3, colW: [1.15, 1.3, 1.5, 1.35], rowH: .34, fontFace: BF, valign: "middle", margin: .04, border: { type: "none" } });
s.addText(`The same ${lb.n} ${lbWhat} · first runs, ${day(llmb.date)}`, { x: 7.33, y: 4.66, w: 5.2, h: .3, fontFace: BF, fontSize: 13, color: FAINT, valign: "middle", margin: 0 });
lab("SO", 5.05, GRN);
s.addText(`Rules decide every verdict. A model may only reword the explanation, through a safety gate, and is off by default. Next, a second opinion that can only raise a warning, in languages Sahayak cannot read yet: there the model caught ${of(lo.caught, lo.scams)} scams.`,
  { x: 7.33, y: 5.35, w: 5.2, h: 1.3, fontFace: BF, fontSize: 15, color: INK, valign: "top", margin: 0 });
sources(s, `bench/results/llm_baseline.md (${llmb.model} zero-shot, dev Mac's ${gpu} GPU; Sahayak on its CPU)${parity ? ", phone_parity.md" : ""}; docs/APPLICATION_TO_PROTOTYPE.md`);
s.addNotes(`Say it before they ask. Round 1 promised a 14B model on the Crucible runtime and a fine-tuned finance model; neither is in Sahayak, and Crucible has not been run with Sahayak. We measured a ${model} model zero-shot on the same ${lb.n} ${lbWhat}: it caught more scams (${of(lb.llm.caught, lb.llm.scams)} against ${lb.sahayak.caught}) but flagged ${of(lb.llm.false_alarms, lb.llm.genuine)} genuine messages (Sahayak ${lb.sahayak.false_alarms}), at ${lb.llm_seconds.median} s a message on a GPU; a CSC laptop's CPU is slower. A warning that fires on that many genuine messages teaches people to ignore warnings. So rules decide, and every verdict names its reasons.`);

/* 5 EVIDENCE: real messages first, then the sets written for the test, and what is not tested yet */
s = P.addSlide(); bg(s); eye(s, "Evidence: first runs");
title(s, `Real messages are harder: it caught ${in10(pH.caught, pH.scams)} in 10`);
const HY = 1.98, HH = 2.0;
card(s, .6, HY, 12.13, HH, CARD, SAF);
s.addText(`REAL MESSAGES PEOPLE RECEIVED, AS PUBLISHED · FIRST RUN, ${day(pub.first.date).toUpperCase()}`, { x: .88, y: HY + .14, w: 11.6, h: .32, fontFace: HF, fontSize: 13, bold: true, color: SAF, charSpacing: 1, valign: "middle", margin: 0 });
s.addText(big(num(pH.caught), ` of ${num(pH.scams)}`, GRN, 44), { x: .88, y: HY + .52, w: 2.7, h: .72, fontFace: HF, valign: "middle", margin: 0 });
s.addText(`scams caught (${pct0(pH.caught / pH.scams)})`, { x: .88, y: HY + 1.26, w: 2.7, h: .4, fontFace: BF, fontSize: 17, bold: true, color: INK, valign: "middle", margin: 0 });
s.addText(big(num(pH.false_alarm), ` of ${num(pH.genuine)}`, SAF, 44), { x: 3.68, y: HY + .52, w: 2.6, h: .72, fontFace: HF, valign: "middle", margin: 0 });
s.addText(`genuine flagged (${pct0(pH.false_alarm / pH.genuine)})`, { x: 3.68, y: HY + 1.26, w: 2.7, h: .4, fontFace: BF, fontSize: 17, bold: true, color: INK, valign: "middle", margin: 0 });
s.addText([
  { text: `${num(pub.first.messages)} messages published by the Income Tax portal, PIB Fact Check, courts and fact-checkers; gathered by an AI agent that never saw the code.`, options: { breakLine: true } },
  { text: `Keyword blocklist: ${of(pHB.caught, pHB.scams)} caught, ${of(pHB.false_alarm, pHB.genuine)} flagged. Other languages: ${of(pO.not_checked || 0, pO.scams)} scams “${V("unreadable")}”, ${num(pOtherGreens)} green.`, options: { breakLine: true } },
  { text: pTest ? `Fixes learned from one half only. The unread half: ${of(pTest[1].caught, pTest[1].scams)} caught (was ${num(pTest[0].caught)}), ${of(pTest[1].false_alarm || 0, pTest[1].genuine)} flagged (was ${num(pTest[0].false_alarm || 0)}).`
      : "Fixes may learn from one half only; the other half stays unread.", options: { color: INK } }],
  { x: 6.4, y: HY + .5, w: 6.15, h: HH - .58, fontFace: BF, fontSize: 13, color: MUTE, valign: "top", margin: 0, paraSpaceAfter: 3 });
const TW = 3.94, TY = HY + HH + .12, TH6 = 2.0, tx = (i) => .6 + i * (TW + .155);
tile(s, tx(0), TY, TW, TH6, { label: `Blind red team (${day(blind.first.date)})`, color: MINT, n: num(heh.caught), rest: ` of ${num(heh.scams)}`,
  what: "scams caught",
  detail: `${num(blind.first.messages)} by an AI model that never saw the code; ${of(heh.false_alarm, heh.genuine)} genuine flagged.` });
tile(s, tx(1), TY, TW, TH6, { label: `Our own set, frozen (${day(sb.date)})`, color: GRN, n: num(full.tp), rest: ` of ${num(sbScams)}`,
  what: `scams caught · 95% CI ${Math.round(100 * sbCi[0])}–${pct0(sbCi[1])}`,
  detail: `Genuine flagged: ${of(full.fp, sbGenuine)}. A ${modelShort}: ${of(lt.llm.caught, lt.llm.scams)} caught, ${of(lt.llm.false_alarms, lt.llm.genuine)} flagged.` });
if (st) {
  tile(s, tx(2), TY, TW, TH6, { label: `Stress test${st.clean ? " re-run" : ""} (${st.date})`, color: st.clean ? GRN : SAF, n: num(st.errors), rest: st.errors === 1 ? " error" : " errors",
    what: [st.session && `${num(st.session.n)} phones`, st.burst && `${num(st.burst.n)} checks at once`].filter(Boolean).join(", "),
    detail: `${st.soak ? `A ${num(st.soak.n)}-check soak. ` : ""}Hostile input: ${num(st.fuzz.cases)} cases, ${num(st.fuzz.unexpected.length)} unexpected.` });
} else if (parity) {
  tile(s, tx(2), TY, TW, TH6, { label: `Phone vs node (${day(parity.date)})`, color: GRN, n: num(parity.fraud.mismatches + parity.navigator.mismatches), rest: " differences",
    what: "between phone and node",
    detail: `${num(parity.fraud.cases)} scam checks and ${num(parity.navigator.cases)} benefits cases, field by field.` });
}
const fc = field && field.cards, SY = TY + TH6 + .1;
card(s, .6, SY, 12.13, 6.88 - SY, CARD2, SAF);
s.addText(field
  ? [{ text: `With real people: ${field.people} at ${field.meta.place}${field.meta.date ? `, ${field.meta.date}` : ""}. `, options: { bold: true, color: SAF } },
     { text: fc ? `Message cards judged right ${pct0(fc.before.rate)} on their own, ${pct0(fc.with_sahayak.rate)} with Sahayak (${of(fc.with_sahayak.k, fc.with_sahayak.n)}). ` : "", options: { color: INK } },
     { text: "Not yet: messages from people's own phones.", options: { bold: true, color: SAF } }]
  : [{ text: "Not yet: real users, and messages from people's own phones.  ", options: { bold: true, color: SAF } },
     { text: "Next: a field morning at a CSC.", options: { color: INK } }],
  { x: .85, y: SY, w: 11.7, h: 6.88 - SY, fontFace: BF, fontSize: 17, valign: "middle", margin: 0 });
sources(s, `bench/results/public_v0.md, redteam_v1_blind.md, scambench_v0_test.md, llm_baseline.md${st ? ", stress_v0.md" : parity ? ", phone_parity.md" : ""}${field ? ", field_v0.md" : ""}. First runs; later fixes are logged, not counted here.`);
s.addNotes(`Lead with the real messages and say it plainly: on ${num(pub.first.messages)} messages people actually received, published by the Income Tax portal, PIB Fact Check, courts, banks and fact-checkers and scored once, Sahayak caught ${of(pH.caught, pH.scams)} scams and flagged ${of(pH.false_alarm, pH.genuine)} genuine messages. That is lower than on messages written for the test (${of(heh.caught, heh.scams)} blind, ${of(full.tp, sbScams)} on our own), and it is the honest number. Never quote ${pct0(full.tp / sbScams)} without saying it was on our own messages. What it missed on the real set: calls with no link or number yet (a "press zero" traffic-police call, a fake officer asking for money), stock-tip groups, long official-looking letters; false alarms: a bank maintenance notice, an ITR e-verify reminder, a prepaid-power bill. ${pTest ? "" : "The fixes may learn from one fixed half only; the other half stays unread, so its score after the fixes is a fair estimate. "}Blind set: the keyword blocklist caught ${hehB.caught}; other languages got "${V("unreadable")}", never a false green. ${st ? `Stress test: the first run found a speech queue, an empty-photo crash, an image bomb and unlimited uploads${st.clean ? ", all fixed before this run" : "; this result file still shows errors, so say so"}${st.phone ? `; on a slow phone (CPU ${st.phone.cpu_slowdown}x slower) the first visit took ${st.phone.first_visit_s} s and a later offline check ${st.phone.second_check_s} s` : ""}. ` : ""}Say the last line out loud.`);

/* 6 HEALTH FIRST, IMPACT, WHO PAYS */
s = P.addSlide(); bg(s); eye(s, "Health first · impact · who pays"); title(s, "Health first, counted every month, and who pays");
const [vvNum, vvRest] = F.vay_vandana.value.split(/ of /);
cols3(s, [["Health first", "", GRN], ["Counted every month", "", MINT], ["Who pays", "", SAF]], 2.0, 4.85, 21);
// column 1: health first
s.addText([{ text: vvNum, options: { fontSize: 34, bold: true, color: SAF, breakLine: true } }, { text: vvRest ? `of ${vvRest}` : "", options: { fontSize: 20, bold: true, color: SAF } }],
  { x: .9, y: 2.72, w: 3.3, h: 1.0, fontFace: HF, valign: "top", margin: 0 });
s.addText(F.vay_vandana.text, { x: .9, y: 3.75, w: 3.3, h: .8, fontFace: BF, fontSize: 16, color: INK, valign: "top", margin: 0 });
s.addText(bullets([`For anyone 70+, results lead with it: hospital care up to ${cover} a year, shared with a 70+ spouse; not OPD.`,
  `The CSC makes the card, free.${hasSchemeFee ? " The scam check flags “pay ₹500 for your card”." : ""}`]),
  { x: .9, y: 4.65, w: 3.3, h: 2.05, fontFace: BF, fontSize: 15, valign: "top", margin: 0 });
// column 2: what the node counts (pilot measures)
s.addText("Counts only: never names, numbers or messages.", { x: 5.02, y: 2.72, w: 3.3, h: .55, fontFace: BF, fontSize: 16, color: INK, valign: "top", margin: 0 });
s.addText(bullets(["Checks, and each verdict",
  "Rupees at risk: the money a scam asks for, never called “saved”",
  "People found eligible, by scheme",
  "Cards made at the counter: the operator ticks each one",
  "A signed monthly export for the district; counts under 5 hidden"]),
  { x: 5.02, y: 3.35, w: 3.3, h: 2.85, fontFace: BF, fontSize: 15, valign: "top", margin: 0 });
s.addText("Pilot measures, not results yet.", { x: 5.02, y: 6.3, w: 3.3, h: .4, fontFace: BF, fontSize: 15, bold: true, color: SAF, valign: "middle", margin: 0 });
// column 3: who pays. The budget appendix when it exists; otherwise the round-1 figure.
const fromFile = Boolean(budget && budget.amount);
s.addText(fromFile ? budget.amount : ROUND1_BUDGET, { x: 9.14, y: 2.72, w: 3.3, h: .62, fontFace: HF, fontSize: 32, bold: true, color: INK, valign: "middle", margin: 0 });
s.addText(fromFile
  ? `${budget.scope ? `${budget.scope}. ` : ""}Estimates, not quotes (round 1 said ${ROUND1_BUDGET}). Line items in the appendix.`
  : "For a 6-month pilot: about 20 villages, about 50 CSC and bank-agent counters (the round-1 estimate). Line items in the appendix.",
  { x: 9.14, y: 3.38, w: 3.3, h: 1.15, fontFace: BF, fontSize: 15, color: MUTE, valign: "top", margin: 0 });
s.addText(bullets(fromFile ? [budget.perCounter, budget.after].filter(Boolean)
  : [`A node: ${F.node_cost.value} once; a check costs nothing.`,
     `After the pilot: not settled. To test: the district, a bank's financial-inclusion or CSR budget, and the CSC network's ${F.csc_card_fee.value} per first-time Ayushman card.`], INK),
  { x: 9.14, y: 4.6, w: 3.3, h: 2.1, fontFace: BF, fontSize: 15, valign: "top", margin: 0 });
sources(s, `${F.vay_vandana.source}; ${F.csc_card_fee.source}; budget: ${fromFile ? "the team's line-item estimate, 7 Oct 2026 (appendix)" : `the round-1 application; node: ${F.node_cost.source}`}.`);
s.addNotes(`Health first is in the product, not only on this slide: every benefits result for someone 70+ leads with the Vay Vandana card, hospital care only, not OPD. The CSC network is paid ${F.csc_card_fee.value} per first-time card; the citizen pays nothing. The counts are what a pilot would report; none are results yet. ${fromFile ? "Who pays in month seven: give the 30-second answer in the budget appendix (section 2). Nobody has agreed to pay; the payers are hypotheses to test; the coordinator and content upkeep have no payer yet. Say that before a judge finds it." : "Who pays after the pilot is not settled: say so, and name what we will test."} RBI's compensation from ${F.rbi_compensation.value} covers credentials taken from the customer or payments under coercion, reported within 5 days; money a person sends willingly is not covered, so do not pitch fraud-loss savings to banks.`);

/* 7 THE ASK, THE NEXT 30 DAYS, THE TEAM */
s = P.addSlide(); bg(s); eye(s, "The ask, and the next 30 days"); title(s, "Our ask, and what we do next");
card(s, .6, 2.0, 7.25, 4.8, CARD);
s.addText("Next 30 days", { x: .9, y: 2.15, w: 6.7, h: .45, fontFace: HF, fontSize: 21, bold: true, color: GRN, valign: "middle", margin: 0 });
[[field ? "A second field morning" : "A field morning at a CSC",
  field ? `Done once: ${field.people} people at ${field.meta.place}. Next: the same protocol at a second counter.`
    : "One morning, with consent: message cards before and after, the benefits interview, the operator's timing. Protocol, consent forms and scoring are ready."],
 ["Messages from people's own phones", "Real scam and genuine messages, collected with consent, scored once on a frozen pack, every miss shown."],
 ["A district partner", "One district, with a CSC or bank-agent network and an NGO, for a 6-month pilot. Letter-of-intent templates are ready."]].forEach((c, i) => {
  const y = 2.75 + i * 1.33;
  chip(s, .88, y + .02, i + 1, .5);
  s.addText(c[0], { x: 1.6, y, w: 6.05, h: .42, fontFace: HF, fontSize: 19, bold: true, color: INK, valign: "middle", margin: 0 });
  s.addText(c[1], { x: 1.6, y: y + .44, w: 6.05, h: .82, fontFace: BF, fontSize: 15, color: MUTE, valign: "top", margin: 0 });
});
card(s, 8.05, 2.0, 4.68, 2.45, CARD2, SAF);
s.addText("THE ASK", { x: 8.33, y: 2.14, w: 4.2, h: .35, fontFace: HF, fontSize: 14, bold: true, color: SAF, charSpacing: 2, valign: "middle", margin: 0 });
s.addText("Introduce us to one district: a CSC or bank-agent network, or a district office, to host the field morning and then a 6-month pilot.",
  { x: 8.33, y: 2.52, w: 4.2, h: 1.85, fontFace: BF, fontSize: 19, color: INK, valign: "top", margin: 0 });
card(s, 8.05, 4.6, 4.68, 2.2, CARD);
s.addText([
  { text: "Roshan Raj", options: { fontFace: HF, fontSize: 18, bold: true, color: INK, breakLine: true } },
  { text: "Manipal Institute of Technology · pitches", options: { fontSize: 14, color: MUTE, breakLine: true } },
  { text: "Ishmiit Singh", options: { fontFace: HF, fontSize: 18, bold: true, color: INK, breakLine: true } },
  { text: "Co-builder of the prototype", options: { fontSize: 14, color: MUTE, breakLine: true } },
  { text: "[Who built what: team to fill in before 14 Oct]", options: { fontSize: 14, bold: true, color: SAF } }],
  { x: 8.33, y: 4.72, w: 3.0, h: 1.98, fontFace: BF, valign: "middle", margin: 0, paraSpaceAfter: 2 });
s.addShape(P.ShapeType.roundRect, { x: 11.42, y: 4.98, w: 1.15, h: 1.15, rectRadius: .06, fill: { color: "FFFFFF" }, line: { type: "none" } });
s.addImage({ path: TRYIT_QR, x: 11.47, y: 5.03, w: 1.05, h: 1.05 });
s.addText("Try it", { x: 11.3, y: 6.17, w: 1.39, h: .3, fontFace: BF, fontSize: 13, bold: true, color: GRN, align: "center", valign: "middle", margin: 0 });
sources(s, "docs/field/ (field protocol, consent in Hindi and English, kit, scoring script, letter-of-intent templates).");
s.addNotes(`Close on the ask, then the opening line again: India opened ${F.jan_dhan.value} Jan Dhan accounts; Sahayak helps those account holders spot a scam before the money moves, and claim what they are owed. Before Delhi, replace the bracketed "who built what" line with what each of you built, and be ready for "Ishmiit, what did you build?".`);

P.writeFile({ fileName: path.join(__dirname, "Sahayak_Jury_Round_Deck.pptx") }).then((f) => console.log("WROTE", f));
