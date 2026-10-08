// Sahayak pitch deck v3 (prototype round and jury round): the prototype, its measured evidence, and the challenge's required sections
// (problem, technology differentiation, testing and validation, impact metrics, theme alignment, collaborations,
// scalability, elevator pitch). Same design as v2. Sahayak's own numbers are read from bench/results/*.json; outside
// numbers from docs/deck/facts_v3.json, each with its source on the slide. Slides that need results not yet in hand
// (the field morning, the phone parity run) show them only when the result file exists.
// Build: NODE_PATH=<folder with pptxgenjs> node docs/deck/build_deck_v3.js   (writes docs/deck/Sahayak_Pitch_Deck_v3.pptx)
const fs = require("fs");
const path = require("path");
const pptx = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const R = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "bench", "results", f), "utf8"));
const RQ = (f) => (fs.existsSync(path.join(ROOT, "bench", "results", f)) ? R(f) : null);  // optional results
const F = JSON.parse(fs.readFileSync(path.join(__dirname, "facts_v3.json"), "utf8"));
const rt = R("redteam_v0.json").first.systems;
const SHOT = (f) => path.join(ROOT, "docs", "deck", "img", f);  // top of each phone screenshot, cropped to the frame
const sb = R("scambench_v0_test.json"), sch = R("schemebench_v1.json"), fl = R("voicebench_fleurs_hi.json");
const lat = R("voice_latency.json").summary;
const field = RQ("field_v0.json"), parity = RQ("phone_parity.json");
const blind = RQ("redteam_v1_blind.json"), llmb = RQ("llm_baseline.json");  // outside tests (7 Oct): shown when present
const pub = RQ("public_v0.json");  // real published messages (7 Oct): the first set the team did not write
// 95% Wilson interval: sound for small samples, where a bootstrap interval can reach 100%
function wilson(k, n) {
  if (!n) return [0, 0];
  const z = 1.96, p = k / n, d = 1 + z * z / n;
  const c = (p + z * z / (2 * n)) / d, h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}
// Claims about the scam check follow the installed, signed pack: the Ayushman-fee signal arrives with fraud pack 1.4.0.
const fraudPack = JSON.parse(fs.readFileSync(path.join(ROOT, "packs", "fraud.v1.json"), "utf8"));
const hasSchemeFee = Boolean(fraudPack.signals.scheme_fee);
const nSignals = Object.keys(fraudPack.signals).length;  // counted from the installed pack, never typed
// The stand-alone app judges can open on their own phones. Its QR image is made from the same URL:
//   python -c "import json, qrcode; qrcode.make(json.load(open('docs/deck/facts_v3.json'))['tryit_url'], border=2, box_size=12).save('docs/deck/img/tryit_qr.png')"
const TRYIT = F.tryit_url, TRYIT_QR = SHOT("tryit_qr.png");
const hasTryit = Boolean(TRYIT) && fs.existsSync(TRYIT_QR);
const tryitShort = TRYIT ? TRYIT.replace(/^https:\/\//, "").replace(/\/$/, "") : "";
const full = sb.systems.full.flagged, block = sb.systems.blocklist.flagged, fullCi = sb.systems.full.flagged_ci95;
const pct = (x) => `${(100 * x).toFixed(1)}%`;
const pct0 = (x) => `${Math.round(100 * x)}%`;

const P = new pptx();
P.defineLayout({ name: "W", width: 13.33, height: 7.5 }); P.layout = "W"; P.author = "Roshan Raj, Ishmiit Singh";
// Rosh 27, dark appearance (as web/styles.css): Obsidian canvas, Graphite cards, Pearl labels, Bay Blue tint,
// Champagne for highlighted figures, the system's positive green.
const BG = "101010", CARD = "1C1C20", CARD2 = "26262B", BORDER = "34343A";
const INK = "F5F5F7", MUTE = "B4B4B8", FAINT = "7E7E84";
const GRN = "6FA8FF", SAF = "E2C28A", MINT = "4FD68A";
const FLAG = ["FF9933", "FFFFFF", "138808"];  // the tricolour dots in each slide's corner
const HF = "Arial", BF = "Calibri";
function shadow() { return { type: "outer", color: "000000", opacity: .4, blur: 10, offset: 3, angle: 90 }; }
function bg(s) {
  s.background = { color: BG };
  s.addShape(P.ShapeType.ellipse, { x: 12.55, y: .42, w: .12, h: .12, fill: { color: FLAG[0] }, line: { type: "none" } });
  s.addShape(P.ShapeType.ellipse, { x: 12.75, y: .42, w: .12, h: .12, fill: { color: FLAG[1] }, line: { type: "none" } });
  s.addShape(P.ShapeType.ellipse, { x: 12.95, y: .42, w: .12, h: .12, fill: { color: FLAG[2] }, line: { type: "none" } });
}
function eye(s, t) {
  s.addShape(P.ShapeType.ellipse, { x: .62, y: .66, w: .14, h: .14, fill: { color: GRN }, line: { type: "none" } });
  s.addText(t.toUpperCase(), { x: .85, y: .5, w: 11, h: .45, fontFace: HF, fontSize: 12.5, bold: true, color: GRN, charSpacing: 2, valign: "middle", margin: 0 });
}
function title(s, t, c) { s.addText(t, { x: .6, y: .95, w: 12.1, h: 1, fontFace: HF, fontSize: 30, bold: true, color: c || INK, valign: "middle", margin: 0 }); }
function card(s, x, y, w, h, f) { s.addShape(P.ShapeType.roundRect, { x, y, w, h, rectRadius: .1, fill: { color: f || CARD }, line: { color: BORDER, width: 1 }, shadow: shadow() }); }
function cols3(s, items, y, h, headSize) {
  items.forEach((c, i) => {
    const x = .6 + i * 4.12; card(s, x, y, 3.85, h);
    s.addText(c[0], { x: x + .33, y: y + .28, w: 3.2, h: .8, fontFace: HF, fontSize: headSize || 17, bold: true, color: c[2], valign: "top", margin: 0 });
    s.addText(c[1], { x: x + .33, y: y + 1.12, w: 3.25, h: h - 1.3, fontFace: BF, fontSize: 12.5, color: MUTE, valign: "top", margin: 0 });
  });
}
function sources(s, text) { s.addText(`Sources: ${text}`, { x: .6, y: 6.95, w: 12.1, h: .35, fontFace: BF, fontSize: 9.5, color: FAINT, margin: 0, valign: "top" }); }
function bullets(s, lines, opts) {
  s.addText(lines.map((t, i) => ({ text: t, options: { bullet: { code: "2022" }, color: MUTE, breakLine: i < lines.length - 1, paraSpaceAfter: 6 } })),
    { fontFace: BF, fontSize: 12.5, valign: "top", margin: 0, ...opts });
}

/* 1 TITLE */
let s = P.addSlide(); bg(s);
s.addText("SAHAYAK", { x: .7, y: 2.0, w: 12, h: 1.2, fontFace: HF, fontSize: 62, bold: true, color: INK, margin: 0, charSpacing: 1 });
s.addText("Offline. Vernacular. On your side.", { x: .72, y: 3.25, w: 11.6, h: .6, fontFace: HF, fontSize: 22, bold: true, color: GRN, margin: 0 });
s.addText("A scam shield and benefits guide for people new to digital money: at the CSC counter and on their own phone, with no internet, in Hindi and English, by voice or touch. Built and measured.",
  { x: .72, y: 3.95, w: 11.4, h: .8, fontFace: BF, fontSize: 15, color: MUTE, margin: 0 });
s.addText([{ text: "Ideas for India 2026", options: { bold: true, color: INK } }, { text: "   ·   Inclusive Innovation for Bharat · Financial Inclusion", options: { color: MUTE } }],
  { x: .72, y: 6.1, w: 12, h: .4, fontFace: BF, fontSize: 13, margin: 0 });
s.addText("Roshan Raj  ·  Ishmiit Singh", { x: .72, y: 6.5, w: 12, h: .4, fontFace: BF, fontSize: 13, color: FAINT, margin: 0 });
s.addNotes("India banked half a billion people, then left them to be robbed. Sahayak protects them where they are: at the counter and at home, offline, in their language, privately.");

/* 2 PROBLEM */
s = P.addSlide(); bg(s); eye(s, "Problem statement"); title(s, "Banked, then left to be robbed");
s.addText("Hundreds of millions of first-time account holders now get OTPs, UPI requests and scheme messages they were never taught to read, and miss benefits they are owed.",
  { x: .6, y: 1.9, w: 12.1, h: .55, fontFace: BF, fontSize: 15, color: MUTE, margin: 0 });
[[F.fraud_2025, SAF], [F.seniors_2025, SAF], [F.upi_families, MINT], [F.pension_awareness, GRN]].forEach(([f, c], i) => {
  const x = .6 + i * 3.08; card(s, x, 2.65, 2.88, 2.3);
  s.addText(f.value, { x: x + .25, y: 2.85, w: 2.5, h: .75, fontFace: HF, fontSize: 24, bold: true, color: c, valign: "bottom", margin: 0, fit: "shrink" });
  s.addText(f.text, { x: x + .25, y: 3.7, w: 2.45, h: 1.15, fontFace: BF, fontSize: 12.5, color: MUTE, valign: "top", margin: 0 });
});
card(s, .6, 5.2, 12.1, 1.15, CARD2);
s.addText("And most safety tools assume the internet, English, an app account and the cloud, and a person who already knows what a scam looks like: what the people most at risk are least likely to have, or trust.",
  { x: .9, y: 5.3, w: 11.5, h: .95, fontFace: BF, fontSize: 14, color: INK, valign: "middle", margin: 0 });
sources(s, [F.fraud_2025, F.seniors_2025, F.upi_families, F.pension_awareness].map((f) => f.source).join("; "));
s.addNotes("Losses were flat from 2024 to 2025 while complaints rose: the fraud is moving to the people least able to spot it. The pension figure is from LASI 2017–18, say so if asked.");

/* 3 SOLUTION */
s = P.addSlide(); bg(s); eye(s, "The solution"); title(s, "At the counter, and on the phone at home");
s.addText("One small computer at a CSC or bank-agent counter; phones join its Wi-Fi, which has no internet. A phone that has opened Sahayak's secure web address once (the public site today; the node's own after a one-time HTTPS setup) runs the same checks with no node at all.",
  { x: .6, y: 1.9, w: 12.1, h: .55, fontFace: BF, fontSize: 15, color: MUTE, margin: 0 });
cols3(s, [
  ["\"Is this a scam?\"", "Paste, speak, photograph or describe a message, a call or a UPI QR. A verdict in milliseconds, the three reasons, what to do now, and a ready 1930 complaint.", SAF],
  ["\"What am I owed?\"", "A spoken interview (median 5 questions) across 12 central schemes, health first: what you can get, the papers, where to go, what to say, and a printed slip.", GRN],
  ["Then, on their own phone", "At home, when the call actually comes: the same scam check and benefits interview, on the phone, with no node and no internet. Nothing leaves the phone.", MINT],
], 2.7, 2.9);
if (hasTryit) {
  card(s, .6, 5.85, 12.1, 1.3, CARD2);
  s.addImage({ path: TRYIT_QR, x: .78, y: 5.95, w: 1.1, h: 1.1 });
  s.addText([{ text: "Try it now, on your own phone: ", options: { bold: true, color: INK } }, { text: tryitShort, options: { bold: true, color: GRN } }],
    { x: 2.1, y: 6.0, w: 10.4, h: .45, fontFace: BF, fontSize: 15, margin: 0 });
  s.addText("Check a message, switch on airplane mode, check another: it still works, and gives the node's exact answer.",
    { x: 2.1, y: 6.48, w: 10.4, h: .45, fontFace: BF, fontSize: 12.5, color: MUTE, margin: 0 });
}
s.addNotes("The counter is where people meet Sahayak and claim benefits; the phone is where it protects them. Invite the judges to scan the code now.");

/* 4 SEE IT */
s = P.addSlide(); bg(s); eye(s, "See it working"); title(s, "Built, and on a phone today");
[["03_result_kyc_hi.png", "A fake KYC SMS, on the node"], ["20_phone_offline_scam_en.png", "Airplane mode: checked on the phone"],
 ["21_health_first_senior_hi.png", "Age 74: health cover first"], ["13_qr_cashback_hi.png", "\"Scan to get cashback\" QR"]].forEach((c, i) => {
  const x = .75 + i * 3.08;
  s.addImage({ path: SHOT(c[0]), x, y: 1.95, w: 2.45, h: 4.33 });
  s.addText(c[1], { x: x - .3, y: 6.38, w: 3.05, h: .5, fontFace: BF, fontSize: 12.5, bold: true, color: INK, align: "center", valign: "top", margin: 0 });
});
s.addNotes("Real screenshots from the running prototype. The second one was taken with the network switched off: the pill says 'On this phone · offline'.");

/* 5 HOW IT WORKS */
s = P.addSlide(); bg(s); eye(s, "How it works"); title(s, "Technology and implementation");
[["01", "Phone app", "A web app, no install, Hindi and English, every screen read aloud. After one visit it works offline on the phone."],
 ["02", "Fraud-Shield", `${nSignals} named signals in a signed content pack, a pattern matcher and a small classifier decide. Vetted templates explain; an optional local model may add a line, only through a safety gate.`],
 ["03", "Benefits Navigator", "Scheme rules as data, each traced to its official page and date; yes / likely / unknown / no logic; asks only what can change the answer."],
 ["04", "Offline voice", "Speech in and out on the node (Vosk, Piper); amounts spoken as words; \"I heard …, is that right?\" before any answer is used."],
 ["05", "The node", "One mini-PC or laptop at a CSC. Zero-egress monitor, Ed25519-signed packs updated by USB, operator console, captive portal."],
 ["06", "Same answer everywhere", parity ? `The phone runs the same rules from the same signed packs: identical results to the node on ${parity.fraud.cases.toLocaleString("en-IN")} messages and ${parity.navigator.cases.toLocaleString("en-IN")} interviews.` : "The phone runs the same rules from the same signed packs, tested to give the node's answer."]]
  .forEach((c, i) => {
    const y = 1.9 + i * .86; card(s, .6, y, 12.1, .78);
    s.addShape(P.ShapeType.roundRect, { x: .85, y: y + .15, w: .48, h: .48, rectRadius: .06, fill: { color: CARD2 }, line: { color: GRN, width: 1 } });
    s.addText(c[0], { x: .85, y: y + .15, w: .48, h: .48, fontFace: HF, fontSize: 14, bold: true, color: GRN, align: "center", valign: "middle", margin: 0 });
    s.addText(c[1], { x: 1.6, y: y + .04, w: 3.2, h: .7, fontFace: HF, fontSize: 14, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(c[2], { x: 4.9, y: y + .04, w: 7.6, h: .7, fontFace: BF, fontSize: 11.5, color: MUTE, valign: "middle", margin: 0 });
  });
s.addNotes("The verdict never depends on a model alone; with the model off, everything still works, on the node and on the phone.");

/* 5b FROM ROUND 1: what changed, and the measurement behind it */
if (llmb && blind) {
  const lt = llmb.sets.scambench_v0_test.llm, lbl = llmb.sets.redteam_v1_blind, lpub = llmb.sets.public_v0;
  s = P.addSlide(); bg(s); eye(s, "What changed since round 1, and why"); title(s, "We tested the big-model idea, and chose rules");
  cols3(s, [
    ["Round 1 proposed", "A 14-billion-parameter language model, offline on a GPU server, deciding whether a message is a scam, with a fine-tuned finance model behind it.", SAF],
    ["We built", `${nSignals} named signals, a pattern matcher and a small classifier decide, in about 2 ms on a laptop CPU, and name their reasons. A language model is optional: it may reword the explanation, through a safety gate, and never decides.`, GRN],
    ["Because we measured", lpub
      ? `A ${llmb.model.replace(":", " ")} model, asked zero-shot on ${lpub.n} real published messages, caught ${lpub.llm.caught} of ${lpub.llm.scams} scams (Sahayak ${lpub.sahayak.caught}) but flagged ${lpub.llm.false_alarms} of ${lpub.llm.genuine} genuine ones (Sahayak ${lpub.sahayak.false_alarms}), at ${lpub.llm_seconds.median} s a message on a GPU. Blind set: ${lbl.llm.false_alarms} of ${lbl.llm.genuine} genuine flagged (Sahayak ${lbl.sahayak.false_alarms}).`
      : `A ${llmb.model.replace(":", " ")} model, asked zero-shot on 182 blind messages, caught ${lbl.llm.caught} of ${lbl.llm.scams} scams (Sahayak ${lbl.sahayak.caught}) but flagged ${lbl.llm.false_alarms} of ${lbl.llm.genuine} genuine ones (Sahayak ${lbl.sahayak.false_alarms}), at ${lbl.llm_seconds.median} s a message on a GPU. On the 60 test messages it flagged ${lt.false_alarms} of ${lt.genuine} genuine; Sahayak's frozen run flagged ${full.fp}.`, MINT],
  ], 1.95, 3.55, 16);
  card(s, .6, 5.75, 12.1, 1.05, CARD2);
  s.addText(`${lpub ? `A warning that fires on ${Math.round(10 * lpub.llm.false_alarms / lpub.llm.genuine)} in 10 real genuine messages` : "A warning that fires on a third of genuine messages"} teaches people to ignore warnings, and the model cannot say what made it decide. Where a model earns its place: it caught ${lbl.other_languages.llm.caught} of ${lbl.other_languages.llm.scams} blind-test scams in languages Sahayak cannot read yet, so next it becomes a raise-only second opinion there.`,
    { x: .9, y: 5.83, w: 11.5, h: .9, fontFace: BF, fontSize: 13, color: INK, valign: "middle", margin: 0, fit: "shrink" });
  sources(s, "bench/results/llm_baseline.md, redteam_v1_blind.md (first runs, 7 Oct 2026); docs/APPLICATION_TO_PROTOTYPE.md");
  s.addNotes("Say it before they ask: we promised a big model, we measured one, and we chose rules for the verdict because it was right more often on genuine messages, 1,000 times faster, and every verdict explains itself. The Crucible server was never connected to Sahayak; the change note says so.");
}

/* 6 DIFFERENTIATION */
s = P.addSlide(); bg(s); eye(s, "Technology differentiation"); title(s, "What already exists, and what Sahayak adds");
const th = (t) => ({ text: t, options: { bold: true, color: INK, fill: { color: CARD2 }, fontFace: HF, fontSize: 12 } });
const td = (t, c) => ({ text: t, options: { color: c || MUTE, fill: { color: CARD }, fontFace: BF, fontSize: 11.5 } });
s.addTable([
  [th("Already out there"), th("What it does well"), th("What Sahayak adds")],
  [td("Airtel and Jio network filters", INK), td(`Block spam calls and links at network scale; Airtel reports ${F.airtel.value} lower fraud losses`), td("Checks the message, QR code or call story in front of the person and says why, in Hindi, offline")],
  [td("Truecaller", INK), td(`Caller ID and spam lists for ${F.truecaller.value} users`), td("No account and no upload: nothing leaves the phone; covers UPI QR codes and screenshots")],
  [td("Google on-device scam alerts", INK), td("On-device call analysis"), td(`Runs in any phone's browser; Google's works on ${F.google_scam.value} only (under 1% of phones)`)],
  [td("1930, cybercrime.gov.in, Sanchar Saathi", INK), td("Reporting and blocking after the fraud"), td("Catches it before the payment, and ends every scam verdict in a ready 1930 complaint")],
  [td("myScheme", INK), td(`${F.myscheme.value} schemes in 15 languages, online, self-serve`), td("Offline, spoken interview with a slip for the CSC; every rule and amount proven against official pages")],
  [td("Haqdarshak", INK), td(`${F.haqdarshak.value} in benefits through trained agents`), td("The offline front door and the scam shield; a content partner, not a rival")],
], { x: .6, y: 1.95, w: 12.1, colW: [3.0, 4.2, 4.9], border: { type: "solid", color: BORDER, pt: 1 }, rowH: .62, valign: "middle", margin: .08 });
sources(s, [F.airtel.source, F.truecaller.source, F.google_scam.source, F.myscheme.source, F.haqdarshak.source].join("; "));
s.addNotes("We complement the network filters and the helplines; no one else checks the thing in front of the person, offline, and explains it.");

/* 7 TESTING */
s = P.addSlide(); bg(s); eye(s, "Testing and validation"); title(s, "Measured on real messages, not just our own");
card(s, .6, 1.95, 12.1, 2.0, CARD);
const pg = pub ? pub.first.systems.full.groups.hindi_english_hinglish : null, pbg = pub ? pub.first.systems.blocklist.groups.hindi_english_hinglish : null;
const bg1 = blind ? blind.first.systems.full.groups.hindi_english_hinglish : null, bbg = blind ? blind.first.systems.blocklist.groups.hindi_english_hinglish : null;
[pg ? [pct0(pg.caught / pg.scams), `of ${pg.scams} real published scams caught, first run (keyword blocklist ${pct0(pbg.caught / pbg.scams)})`, SAF] : null,
 bg1 ? [pct0(bg1.caught / bg1.scams), `of scams caught in a blind test written by a separate AI model (blocklist ${pct0(bbg.caught / bbg.scams)})`, MINT] : null,
 [pct0(full.recall), `of our own test scams caught (blocklist ${pct0(block.recall)})`, GRN],
 [`${sb.latency_ms_full.p50.toFixed(0)} ms`, "per verdict on a laptop CPU", SAF],
 [pct(fl.wer), "Hindi word error, adults reading aloud", MINT]].filter(Boolean).slice(0, 5).forEach((v, i) => {
  const x = .95 + i * 2.38;
  s.addText(v[0], { x, y: 2.25, w: 2.3, h: .8, fontFace: HF, fontSize: 28, bold: true, color: v[2], valign: "bottom", margin: 0, fit: "shrink" });
  s.addText(v[1], { x, y: 3.1, w: 2.25, h: .75, fontFace: BF, fontSize: 11.5, color: MUTE, valign: "top", margin: 0 });
});
card(s, .6, 4.2, 12.1, field ? 1.2 : 2.5, CARD2);
s.addText("How we know, and what it does not show", { x: .9, y: 4.32, w: 11.5, h: .4, fontFace: HF, fontSize: 14.5, bold: true, color: INK, margin: 0 });
const wl = wilson(full.tp, full.tp + full.fn);
const pt = pub && pub.latest ? [pub.first.systems.full.groups.test_half, pub.latest.systems.full.groups.test_half] : null;
s.addText(
  (pg ? `Real messages: ${pub.first.messages} that people received, published by the Income Tax portal, PIB Fact Check, courts and fact-checkers, scored once: ${pg.caught} of ${pg.scams} scams caught, ${pg.false_alarm} of ${pg.genuine} genuine flagged (blocklist ${pbg.false_alarm}). ` : "") +
  (pt ? `Fixes then learned from half of them; on the other half, never read, scams caught went from ${pt[0].caught} to ${pt[1].caught} of ${pt[1].scams} and genuine flagged from ${pt[0].false_alarm} to ${pt[1].false_alarm} of ${pt[1].genuine}. ` : "") +
  (bg1 ? `Blind red team, ${blind.first.messages} messages: ${bg1.caught} of ${bg1.scams} caught, ${bg1.false_alarm} of ${bg1.genuine} hard genuine flagged; other languages get "could not check", never a false green. ` : "") +
  `Our own test split: ${full.tp} of ${full.tp + full.fn} (95% Wilson CI ${pct0(wl[0])}–${pct0(wl[1])}). ` +
  `Not yet: messages from people's own phones, and real users.`,
  { x: .9, y: 4.75, w: 11.5, h: field ? .6 : 1.85, fontFace: BF, fontSize: field ? 11 : 13, color: MUTE, valign: "top", margin: 0, fit: "shrink" });
if (field) {
  const c = field.cards;
  card(s, .6, 5.6, 12.1, 1.25, CARD2);
  s.addText(`With real people: ${field.meta.place}${field.meta.date ? `, ${field.meta.date}` : ""}`, { x: .9, y: 5.7, w: 11.5, h: .4, fontFace: HF, fontSize: 14.5, bold: true, color: SAF, margin: 0 });
  s.addText(`${field.people} people. Message cards judged right on their own ${pct0(c.before.rate)}, with Sahayak ${pct0(c.with_sahayak.rate)} (McNemar p = ${c.mcnemar_p.toPrecision(2)}). Benefits interview finished without help ${pct0(field.benefits.finished_unaided.rate || 0)}; ${pct0(field.benefits.found_something_new.rate || 0)} found a scheme new to them.`,
    { x: .9, y: 6.1, w: 11.5, h: .7, fontFace: BF, fontSize: 12, color: MUTE, valign: "top", margin: 0 });
}
s.addNotes("Every number comes from a script in bench/ and the testing report; the caveats are on the slide.");

/* 8 HEALTH */
s = P.addSlide(); bg(s); eye(s, "Health first"); title(s, "₹5 lakh of health cover most seniors have not claimed");
card(s, .6, 1.95, 7.6, 1.6, CARD2);
s.addText(F.vay_vandana.value, { x: .9, y: 2.05, w: 7.1, h: .75, fontFace: HF, fontSize: 30, bold: true, color: SAF, margin: 0, fit: "shrink" });
s.addText(F.vay_vandana.text, { x: .9, y: 2.8, w: 7.1, h: .6, fontFace: BF, fontSize: 13.5, color: INK, margin: 0 });
bullets(s, [
  "Every benefits result leads with Ayushman Bharat; for anyone 70 or older it is the Vay Vandana card: up to ₹5 lakh a year of hospital care whatever their income (shared with a spouse who is also 70 or more; not for outpatient visits).",
  "One question, their age, finds them; the slip tells the operator what to make.",
  `The CSC makes the card at the counter, and is paid ${F.csc_card_fee.value} per first-time card; the citizen pays nothing.`,
  hasSchemeFee ? "The scam check flags \"pay to get your Ayushman card\" messages; the node counts seniors found, every month, with no personal data."
    : "The node counts seniors found for the card, every month, with no personal data.",
], { x: .7, y: 3.8, w: 7.4, h: 2.9 });
s.addImage({ path: SHOT("21_health_first_senior_hi.png"), x: 9.15, y: 1.95, w: 2.75, h: 4.86 });
sources(s, `${F.vay_vandana.source}; ${F.csc_card_fee.source}`);
s.addNotes("Optum's mission is healthier lives: this is the shortest path from Sahayak to a hospital bill that never has to be paid.");

/* 9 IMPACT */
s = P.addSlide(); bg(s); eye(s, "Impact metrics"); title(s, "From \"account opened\" to \"citizen safe\"");
cols3(s, [
  ["Rupees at risk", "The node adds up the money asked for in messages it flags, every month: never called \"saved\", always shown to the district without personal data.", SAF],
  ["People found, health first", "People found eligible, by scheme, with seniors found for Ayushman Vay Vandana counted on their own; each slip lets the operator finish the form.", GRN],
  ["Reported in time", `From ${F.rbi_compensation.value}, RBI compensates small losses from stolen OTPs and PINs if reported within 5 days; Sahayak drafts the complaint on the spot. Money sent willingly is not compensated: there, stopping the payment is the only protection.`, MINT],
], 2.0, 2.75, 17);
card(s, .6, 5.0, 12.1, 1.75, CARD2);
s.addText(field ? "Measured with real people" : "Pilot target, not a result", { x: .9, y: 5.12, w: 11.5, h: .4, fontFace: HF, fontSize: 14.5, bold: true, color: INK, margin: 0 });
s.addText(field
  ? `${field.people} people at ${field.meta.place}: right action after a verdict ${pct0(field.right_action_after_verdict.rate || 0)}; seniors 70+ shown Vay Vandana ${field.benefits.seniors_70_shown_pmjay.k} of ${field.benefits.seniors_70_shown_pmjay.n}; it worked on a phone away from the node ${field.offline_on_phone.k} of ${field.offline_on_phone.n} times.`
  : `One district: about 20 villages and 50 counters (nodes at 20 CSCs, the phone app at 30 bank-agent points), six months, ${F.pilot_budget ? F.pilot_budget.value + " line by line" : "₹35–40 lakh"}. Scams flagged, people found eligible and cards made (the operator ticks each), all from the node's counters. A one-morning field test at a CSC (protocol and consent ready) comes first.`,
  { x: .9, y: 5.55, w: 11.5, h: 1.1, fontFace: BF, fontSize: 12.5, color: MUTE, valign: "top", margin: 0 });
sources(s, F.rbi_compensation.source);
s.addNotes("Impact is economic (rupees at risk, entitlements claimed, cards made) and social (safety, dignity, trust).");

/* 10 SCALE + WHO PAYS */
s = P.addSlide(); bg(s); eye(s, "Scalability and sustainability"); title(s, "Grow by replication; paid for by those who gain");
card(s, .6, 1.95, 5.85, 4.8, CARD);
s.addText("Replication, not reinvention", { x: .9, y: 2.15, w: 5.3, h: .45, fontFace: HF, fontSize: 16, bold: true, color: GRN, margin: 0 });
bullets(s, [
  `${F.cscs.value} ${F.cscs.text}: the counters already exist.`,
  "A deployment is a node image, signed packs and a one-page operator guide; a new scam or scheme is a pack update by USB.",
  "Every phone that visits can keep its own copy, so protection spreads beyond the counter at no extra cost.",
  "No cloud and no per-query fee; open, tested rules any state can audit.",
], { x: .9, y: 2.7, w: 5.35, h: 3.9 });
card(s, 6.65, 1.95, 6.05, 4.8, CARD2);
s.addText("Who pays", { x: 6.95, y: 2.15, w: 5.5, h: .45, fontFace: HF, fontSize: 16, bold: true, color: SAF, margin: 0 });
s.addText(F.node_cost.value, { x: 6.95, y: 2.65, w: 5.5, h: .6, fontFace: HF, fontSize: 24, bold: true, color: INK, margin: 0, fit: "shrink" });
s.addText(`once per node (${F.node_cost.text.replace(/^for a node: /, "")}); each check costs nothing.`, { x: 6.95, y: 3.25, w: 5.5, h: .5, fontFace: BF, fontSize: 12, color: MUTE, margin: 0 });
bullets(s, [
  "Banks: financial-inclusion or CSR budgets for their agent points, as customer education; fewer small-fraud payouts (shared with RBI from 1 Jan 2027) are a bonus, not the case.",
  `The CSC network: paid about ${F.csc_card_fee.value} per first-time Ayushman card or e-Shram registration Sahayak sends to the counter (how much reaches the operator varies); ${F.vle_income.value} of rural operators earn under ₹500 a month.`,
  "The State Health Agency and the district: Vay Vandana card drives at the CSCs, funded against a signed monthly count of cards made.",
], { x: 6.95, y: 3.85, w: 5.5, h: 2.8 });
sources(s, [F.cscs.source, F.node_cost.source, F.rbi_compensation.source, F.csc_card_fee.source, F.vle_income.source].join("; "));
s.addNotes("The operator's incentive matters: most rural operators earn very little, and every slip is a paid service at the counter.");

/* 11 THEME ALIGNMENT */
s = P.addSlide(); bg(s); eye(s, "Theme alignment"); title(s, "Inclusive innovation on India's own rails");
[["Financial inclusion, made safe", "Protects the 59 crore Jan Dhan accounts and the UPI base the nation built, for the people who opened them last."],
 ["1930 and RBI's 2027 rules", "Every scam verdict ends in the national helpline; fast reporting is what RBI's compensation now requires."],
 ["Ayushman Bharat", "Finds seniors for the Vay Vandana card and sends them to the counter that makes it."],
 ["Digital India, last mile", "Hindi and English by voice today, offline; the language data is a pack, so more languages follow."],
 ["DPDP Act", "Privacy by design: consent first, nothing named, nothing written to disk, deleted by default."],
 ["CSC · BC · ASHA", "Delivered through the public networks people already trust, with an operator at the counter."]].forEach((c, i) => {
  const x = .6 + (i % 3) * 4.12, y = 2.2 + Math.floor(i / 3) * 2.15; card(s, x, y, 3.85, 1.95);
  s.addText(c[0], { x: x + .3, y: y + .22, w: 3.3, h: .55, fontFace: HF, fontSize: 14.5, bold: true, color: GRN, margin: 0 });
  s.addText(c[1], { x: x + .3, y: y + .8, w: 3.3, h: 1.05, fontFace: BF, fontSize: 12, color: MUTE, valign: "top", margin: 0 });
});
s.addNotes("Maps Sahayak onto the track: financial inclusion first, with public service delivery and health on the same counter.");

/* 12 COLLABORATIONS */
s = P.addSlide(); bg(s); eye(s, "Collaborations"); title(s, "Built in the open; seeking last-mile partners");
F.partners.forEach((p, i) => {
  const y = 1.95 + i * 1.02; card(s, .6, y, 12.1, .88);
  s.addText(p.who, { x: .9, y: y + .06, w: 4.6, h: .76, fontFace: HF, fontSize: 13.5, bold: true, color: INK, valign: "middle", margin: 0 });
  s.addText(p.role, { x: 5.6, y: y + .06, w: 5.1, h: .76, fontFace: BF, fontSize: 12, color: MUTE, valign: "middle", margin: 0 });
  const done = /signed|agreed|confirmed/i.test(p.status);
  s.addShape(P.ShapeType.roundRect, { x: 10.85, y: y + .24, w: 1.6, h: .4, rectRadius: .08, fill: { color: done ? GRN : CARD2 }, line: { color: done ? GRN : SAF, width: 1 } });
  s.addText(p.status, { x: 10.85, y: y + .24, w: 1.6, h: .4, fontFace: BF, fontSize: 11, bold: true, color: done ? BG : SAF, align: "center", valign: "middle", margin: 0 });
});
s.addText("Ready for each partner: a one-morning field protocol with consent in Hindi and English, a scoring script, and letters of intent. The code is MIT-licensed and open.",
  { x: .6, y: 6.1, w: 12.1, h: .6, fontFace: BF, fontSize: 12.5, color: INK, margin: 0 });
s.addNotes("Honest: the technology is built; the partnerships are what this challenge begins. Update the status pills in docs/deck/facts_v3.json as letters come in.");

/* 13 TEAM + ASK */
s = P.addSlide(); bg(s); eye(s, "Team and the ask"); title(s, "Builders who ship, asking for one district");
card(s, .6, 2.0, 5.55, 4.4, CARD);
s.addText("Roshan Raj", { x: .95, y: 2.25, w: 5, h: .5, fontFace: HF, fontSize: 21, bold: true, color: INK, margin: 0 });
s.addText("Systems and AI-infrastructure engineer · Manipal Institute of Technology", { x: .95, y: 2.75, w: 5, h: .6, fontFace: BF, fontSize: 12.5, color: GRN, margin: 0 });
s.addText("Ishmiit Singh", { x: .95, y: 3.6, w: 5, h: .5, fontFace: HF, fontSize: 21, bold: true, color: INK, margin: 0 });
s.addText("Co-builder: product, content and evidence", { x: .95, y: 4.1, w: 5, h: .4, fontFace: BF, fontSize: 12.5, color: GRN, margin: 0 });
s.addText("Together: the node, the scam shield, the scheme navigator, offline voice, the phone engine, the operator console and the benchmarks behind every number in this deck.",
  { x: .95, y: 4.7, w: 5, h: 1.5, fontFace: BF, fontSize: 12.5, color: MUTE, valign: "top", margin: 0 });
card(s, 6.4, 2.0, 6.3, 4.4, CARD2);
s.addText("The ask", { x: 6.75, y: 2.25, w: 5.7, h: .4, fontFace: HF, fontSize: 14, bold: true, color: SAF, charSpacing: 2, margin: 0 });
s.addText("A six-month, single-district pilot (about 20 villages, 50 counters, roughly ₹35–40 lakh) with:", { x: 6.75, y: 2.7, w: 5.7, h: .7, fontFace: BF, fontSize: 13, color: INK, margin: 0 });
bullets(s, [
  "CSC e-Governance or the State IT department: the counters",
  "A bank BC network or SLBC: reach, and real messages for ScamBench v1",
  "NHA or the state health agency: Vay Vandana cards made at the counter",
  "A rural NGO: field testing and Hindi review",
], { x: 6.9, y: 3.5, w: 5.55, h: 2.7 });
s.addNotes("The technology is built and measured; the pilot is integration and field validation, not new research.");

/* 14 CLOSE */
s = P.addSlide(); bg(s); eye(s, "Elevator pitch");
s.addText("India banked half a billion people.", { x: .7, y: 2.0, w: 12, h: .7, fontFace: HF, fontSize: 26, bold: true, color: INK, margin: 0 });
s.addText("Sahayak helps keep them safe, and claim what they are owed.", { x: .7, y: 2.7, w: 12, h: .7, fontFace: HF, fontSize: 26, bold: true, color: GRN, margin: 0 });
s.addText("At the counter and on their own phone · offline · in their language · nothing leaves the device · built and measured. Starting with ₹5 lakh of health cover for every senior who does not yet have the card.",
  { x: .72, y: 3.75, w: 11.6, h: .9, fontFace: BF, fontSize: 15, color: MUTE, margin: 0 });
s.addText("Roshan Raj  ·  Ishmiit Singh", { x: .72, y: 5.6, w: 12, h: .4, fontFace: BF, fontSize: 13.5, bold: true, color: INK, margin: 0 });
if (hasTryit) {
  s.addImage({ path: TRYIT_QR, x: 11.05, y: 4.95, w: 1.55, h: 1.55 });
  s.addText(tryitShort, { x: 9.3, y: 6.55, w: 3.3, h: .35, fontFace: BF, fontSize: 11, color: MUTE, align: "right", margin: 0 });
}
s.addNotes("Close on the line: banked half a billion; Sahayak helps keep them safe and claim what they are owed.");

P.writeFile({ fileName: path.join(__dirname, "Sahayak_Pitch_Deck_v3.pptx") }).then((f) => console.log("WROTE", f));
