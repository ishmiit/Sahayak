// Sahayak pitch deck v2: the built prototype and its measured evidence.
// Same design as the round-1 deck (IdeasForIndia_2026/_source/build_deck2.js); every number on a slide is
// read from bench/results/*.json, so the deck cannot drift from the testing report.
// Build: NODE_PATH=<folder with pptxgenjs> node docs/deck/build_deck_v2.js   (writes docs/deck/Sahayak_Pitch_Deck_v2.pptx)
const fs = require("fs");
const path = require("path");
const pptx = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const R = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "bench", "results", f), "utf8"));
const rt = R("redteam_v0.json").first.systems;
const SHOT = (f) => path.join(ROOT, "docs", "deck", "img", f);  // top of each phone screenshot, cropped to the frame
const sb = R("scambench_v0_test.json"), sch = R("schemebench_v1.json"), fl = R("voicebench_fleurs_hi.json");
const lat = R("voice_latency.json").summary;
const full = sb.systems.full.flagged, block = sb.systems.blocklist.flagged, fullCi = sb.systems.full.flagged_ci95;
const pct = (x) => `${(100 * x).toFixed(1)}%`;

const P = new pptx();
P.defineLayout({ name: "W", width: 13.33, height: 7.5 }); P.layout = "W"; P.author = "Roshan Raj, Ishmiit Singh";
const BG = "0B0F14", CARD = "152017", CARD2 = "1B2A20", BORDER = "2C4636";
const INK = "EEF3EE", MUTE = "9DB0A4", FAINT = "6E8579";
const GRN = "27C08A", SAF = "FF9E3D", MINT = "4FE3B0";
const HF = "Arial", BF = "Calibri";
function shadow() { return { type: "outer", color: "000000", opacity: .4, blur: 10, offset: 3, angle: 90 }; }
function bg(s) {
  s.background = { color: BG };
  s.addShape(P.ShapeType.ellipse, { x: 12.55, y: .42, w: .12, h: .12, fill: { color: SAF }, line: { type: "none" } });
  s.addShape(P.ShapeType.ellipse, { x: 12.75, y: .42, w: .12, h: .12, fill: { color: INK }, line: { type: "none" } });
  s.addShape(P.ShapeType.ellipse, { x: 12.95, y: .42, w: .12, h: .12, fill: { color: GRN }, line: { type: "none" } });
}
function eye(s, t) {
  s.addShape(P.ShapeType.ellipse, { x: .62, y: .66, w: .14, h: .14, fill: { color: GRN }, line: { type: "none" } });
  s.addText(t.toUpperCase(), { x: .85, y: .5, w: 11, h: .45, fontFace: HF, fontSize: 12.5, bold: true, color: GRN, charSpacing: 2, valign: "middle", margin: 0 });
}
function title(s, t, c) { s.addText(t, { x: .6, y: .95, w: 12.1, h: 1, fontFace: HF, fontSize: 31, bold: true, color: c || INK, valign: "middle", margin: 0 }); }
function card(s, x, y, w, h, f) { s.addShape(P.ShapeType.roundRect, { x, y, w, h, rectRadius: .1, fill: { color: f || CARD }, line: { color: BORDER, width: 1 }, shadow: shadow() }); }
function cols3(s, items, y, h, headSize) {
  items.forEach((c, i) => {
    const x = .6 + i * 4.12; card(s, x, y, 3.85, h);
    s.addText(c[0], { x: x + .33, y: y + .28, w: 3.2, h: .8, fontFace: HF, fontSize: headSize || 17, bold: true, color: c[2], valign: "top", margin: 0 });
    s.addText(c[1], { x: x + .33, y: y + 1.12, w: 3.25, h: h - 1.3, fontFace: BF, fontSize: 12.5, color: MUTE, valign: "top", margin: 0 });
  });
}

/* 1 TITLE */
let s = P.addSlide(); bg(s);
s.addText("SAHAYAK", { x: .7, y: 2.0, w: 12, h: 1.2, fontFace: HF, fontSize: 62, bold: true, color: INK, margin: 0, charSpacing: 1 });
s.addText("Offline. Vernacular. On your side.", { x: .72, y: 3.25, w: 11.6, h: .6, fontFace: HF, fontSize: 22, bold: true, color: GRN, margin: 0 });
s.addText("A scam shield and benefits guide that runs on one node at a CSC counter, with no internet, in Hindi and English, by voice or touch. Built and measured.",
  { x: .72, y: 3.95, w: 11.4, h: .8, fontFace: BF, fontSize: 15, color: MUTE, margin: 0 });
s.addText([{ text: "Ideas for India 2026", options: { bold: true, color: INK } }, { text: "   ·   Inclusive Innovation for Bharat", options: { color: MUTE } }],
  { x: .72, y: 6.1, w: 12, h: .4, fontFace: BF, fontSize: 13, margin: 0 });
s.addText("Roshan Raj  ·  Ishmiit Singh", { x: .72, y: 6.5, w: 12, h: .4, fontFace: BF, fontSize: 13, color: FAINT, margin: 0 });
s.addNotes("India banked half a billion people, then left them to be robbed. Sahayak protects them where they are: offline, in their language, privately.");

/* 2 PROBLEM */
s = P.addSlide(); bg(s); eye(s, "The problem"); title(s, "Banked, then left to be robbed");
s.addText("Hundreds of millions of first-time account holders now receive OTPs, UPI requests and scheme messages they were never taught to read.",
  { x: .6, y: 1.95, w: 12, h: .5, fontFace: BF, fontSize: 15.5, color: MUTE, margin: 0 });
cols3(s, [
  ["Fraud preys on the new", "Fake KYC SMS, \"scan to receive\" QR codes, digital-arrest calls, fake scheme apps: built to fool people who cannot yet tell a real bank message from a trap.", SAF],
  ["Benefits go unclaimed", "Pensions, insurance and income support are lost to paperwork and to not knowing they exist, or which office to ask.", GRN],
  ["Tools assume the connected", "Every safety tool assumes internet, a smartphone, English and the cloud: the four things the excluded lack.", MINT],
], 2.7, 3.6);
s.addNotes("The people most exposed to fraud and most in need of guidance are the ones digital services reach last.");

/* 3 SOLUTION */
s = P.addSlide(); bg(s); eye(s, "The solution"); title(s, "One offline node. Two questions answered.");
s.addText("Phones join the node's Wi-Fi, which has no internet, and ask in Hindi or English, by voice or touch.",
  { x: .6, y: 1.95, w: 12.1, h: .5, fontFace: BF, fontSize: 15, color: MUTE, margin: 0 });
cols3(s, [
  ["\"Is this a scam?\"", "Paste, speak, photograph or describe a message, a call or a UPI QR. Verdict in milliseconds, the three reasons, what to do, and a ready 1930 complaint.", SAF],
  ["\"What am I owed?\"", "A spoken interview (median 5 questions) across 12 central schemes: what you can get, the papers to carry, where to go, what to say, and a printed slip.", GRN],
  ["A counter, not an app", "The CSC or bank agent sees \"Ask the agent\" requests, prints 58 mm slips and reads monthly impact counters that hold no personal data.", MINT],
], 2.7, 3.65);
s.addNotes("Design principle is subtraction: no internet, no English-only, no cloud, no expensive phone.");

/* 4 SEE IT */
s = P.addSlide(); bg(s); eye(s, "See it working"); title(s, "Built, and on a phone today");
[["03_result_kyc_hi.png", "A fake KYC SMS"], ["09_benefits_result_widow_hi.png", "Widow, 67: what she can claim"], ["13_qr_cashback_hi.png", "\"Scan to get cashback\" QR"]].forEach((c, i) => {
  const x = .9 + i * 4.1;
  s.addImage({ path: SHOT(c[0]), x, y: 1.95, w: 2.6, h: 4.6 });
  s.addText(c[1], { x: x - .3, y: 6.62, w: 3.2, h: .4, fontFace: BF, fontSize: 13, bold: true, color: INK, align: "center", margin: 0 });
});
s.addNotes("Real screenshots from the running prototype: a scam verdict with reasons and 1930, a benefits result, and a UPI QR check.");

/* 5 HOW IT WORKS */
s = P.addSlide(); bg(s); eye(s, "How it works"); title(s, "Technology and implementation");
[["01", "Phone app", "A cached web app (no install), Hindi and English, every screen read aloud; works on a basic Android phone."],
 ["02", "Fraud-Shield", "51 named signals in a signed content pack, a pattern matcher and a small classifier decide. Vetted templates explain; an optional local LLM may add a line, only through a safety gate."],
 ["03", "Benefits Navigator", "Scheme rules as data, each traced to its official page and date; yes / likely / unknown / no logic; asks only what can change the answer."],
 ["04", "Offline voice", "Speech in and out on the node (Vosk, Piper); amounts spoken as words; \"I heard …, is that right?\" before any answer is used."],
 ["05", "The node", "One laptop or mini-PC at a CSC. Zero-egress monitor, Ed25519-signed packs updated by USB, operator console, captive portal."]]
  .forEach((c, i) => {
    const y = 1.95 + i * 1.03; card(s, .6, y, 12.1, .9);
    s.addShape(P.ShapeType.roundRect, { x: .85, y: y + .2, w: .5, h: .5, rectRadius: .06, fill: { color: CARD2 }, line: { color: GRN, width: 1 } });
    s.addText(c[0], { x: .85, y: y + .2, w: .5, h: .5, fontFace: HF, fontSize: 15, bold: true, color: GRN, align: "center", valign: "middle", margin: 0 });
    s.addText(c[1], { x: 1.6, y: y + .05, w: 3.2, h: .8, fontFace: HF, fontSize: 14.5, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(c[2], { x: 4.9, y: y + .05, w: 7.55, h: .8, fontFace: BF, fontSize: 12, color: MUTE, valign: "middle", margin: 0 });
  });
s.addNotes("The verdict never depends on the model alone; with the model switched off, everything still works.");

/* 6 INNOVATION */
s = P.addSlide(); bg(s); eye(s, "Innovation and uniqueness"); title(s, "What no one else ships together");
cols3(s, [
  ["Offline, and it proves it", "The node counts every outbound connection its own process makes, live on screen, next to the firewall's state. The judge's phone shows \"no internet\".", SAF],
  ["Explains, not a blocklist", `Named signals a judge can check. On ScamBench, ${pct(full.recall)} of scams caught against ${pct(block.recall)} for a keyword blocklist, with ${pct(full.false_alarm_rate)} false alarms against ${pct(block.false_alarm_rate)}.`, GRN],
  ["Rules, not guesses", `Scheme answers computed from official rules: ${sch.rules.agree.toLocaleString("en-IN")} of ${sch.rules.decisions.toLocaleString("en-IN")} decisions match an independent re-derivation; every rupee amount traces to a signed pack.`, MINT],
], 2.4, 2.9, 17);
s.addNotes("Turns the usual trade-off, advanced AI or reaching the unconnected, into advanced AI because it reaches the unconnected.");

/* 7 PROOF */
s = P.addSlide(); bg(s); eye(s, "Feasibility: measured, not claimed"); title(s, "It already works, and we measured it");
card(s, .6, 2.1, 12.1, 2.05, CARD);
[[pct(full.recall), `scams caught (blocklist: ${pct(block.recall)})`, GRN],
 [`${sb.latency_ms_full.p50.toFixed(0)} ms`, "per verdict on a laptop CPU", SAF],
 [pct(fl.wer), "Hindi word error, real speakers", MINT],
 [`${lat.cached.p50} s`, "from mic release to spoken reply", GRN],
 [`${sch.interview.median}`, "questions to find a person's schemes", SAF]].forEach((v, i) => {
  const x = .95 + i * 2.38;
  s.addText(v[0], { x, y: 2.45, w: 2.3, h: .8, fontFace: HF, fontSize: 30, bold: true, color: v[2], valign: "bottom", margin: 0 });
  s.addText(v[1], { x, y: 3.3, w: 2.25, h: .6, fontFace: BF, fontSize: 11.5, color: MUTE, valign: "top", margin: 0 });
});
card(s, .6, 4.45, 12.1, 1.95, CARD2);
s.addText("How we know, and what it does not show", { x: .9, y: 4.65, w: 11.5, h: .45, fontFace: HF, fontSize: 15, bold: true, color: INK, margin: 0 });
s.addText(`ScamBench v0 frozen test split (${sb.n} messages, 95% CI ${pct(fullCi.recall[0])}–${pct(fullCi.recall[1])}); SchemeBench (200 personas, exhaustive interview check); Google FLEURS Hindi (${fl.utterances} recordings). v0 messages were written by our team, so those numbers are optimistic; v1 adds real messages collected with consent. Red team: ${rt.full.scams_flagged} of ${rt.full.scams} scams disguised to slip past it caught on the first run (blocklist ${rt.blocklist.scams_flagged}). All in the testing report.`,
  { x: .9, y: 5.1, w: 11.5, h: 1.2, fontFace: BF, fontSize: 12.5, color: MUTE, valign: "top", margin: 0 });
s.addNotes("Every number here comes from a script in bench/ and the testing report; the caveats are on the slide.");

/* 8 IMPACT */
s = P.addSlide(); bg(s); eye(s, "Social and economic impact"); title(s, "From \"account opened\" to \"citizen safe\"");
cols3(s, [
  ["Rupees at risk", "The node adds up the money asked for in messages it flags, every month: never called \"saved\", always shown to the district without personal data.", SAF],
  ["Schemes found", "People found eligible, by scheme, with the papers and the office; each printed slip lets the CSC operator finish the form at the counter.", GRN],
  ["Nothing leaves", "Messages, voices and answers stay in the node's memory; the case log needs consent, holds no names and deletes itself after 30 days.", MINT],
], 2.3, 2.7, 18);
card(s, .6, 5.2, 12.1, 1.2, CARD2);
s.addText("Pilot target, not a result: one node per CSC in a 20-village district, with an operator and real users. The counters are how the district will know.",
  { x: .9, y: 5.35, w: 11.5, h: .9, fontFace: BF, fontSize: 13, color: MUTE, valign: "middle", margin: 0 });
s.addNotes("Impact is economic (rupees at risk, entitlements claimed) and social (safety, dignity, trust).");

/* 9 SCALE */
s = P.addSlide(); bg(s); eye(s, "Scalability and sustainability"); title(s, "Grow by replication, not reinvention");
cols3(s, [
  ["Replicable node", "A deployment is a node image plus signed content packs plus a one-page operator guide. A new scam pattern or scheme is a pack update by USB, not a code change.", SAF],
  ["Rides existing rails", "Delivered through CSCs, bank business correspondents and ASHA workers: networks people already trust, with an operator at the counter.", GRN],
  ["Sustainable by design", "No cloud or per-query cost; open, testable rules; counters give the district a monthly number to fund against.", MINT],
], 2.25, 3.0, 16.5);
s.addNotes("Every scheme the Navigator surfaces is a service the operator can complete at the counter, which keeps the node running.");

/* 10 NATIONAL ALIGNMENT */
s = P.addSlide(); bg(s); eye(s, "Alignment with national priorities"); title(s, "Built on India's own rails");
[["Digital India, last mile", "Extends digital public services to the citizens they reach last."],
 ["Jan Dhan · DBT · UPI", "Protects the financial-inclusion base the nation has already built."],
 ["1930 and cybercrime.gov.in", "Every scam verdict ends in the national helpline and a ready complaint."],
 ["Indian languages", "Hindi and English by voice today; the language data is a pack, so more languages follow."],
 ["DPDP Act", "Data stays on the node: consent first, nothing named, deleted by default."],
 ["CSC · BC · ASHA", "Delivered through the public networks already trusted on the ground."]].forEach((c, i) => {
  const x = .6 + (i % 3) * 4.12, y = 2.35 + Math.floor(i / 3) * 1.95; card(s, x, y, 3.85, 1.75);
  s.addText(c[0], { x: x + .3, y: y + .22, w: 3.3, h: .55, fontFace: HF, fontSize: 14.5, bold: true, color: GRN, margin: 0 });
  s.addText(c[1], { x: x + .3, y: y + .78, w: 3.3, h: .85, fontFace: BF, fontSize: 12, color: MUTE, valign: "top", margin: 0 });
});
s.addNotes("Maps Sahayak onto the rubric's national-priorities line.");

/* 11 TEAM + ASK */
s = P.addSlide(); bg(s); eye(s, "Team and the ask"); title(s, "Builders who ship, seeking last-mile partners");
card(s, .6, 2.15, 5.55, 4.25, CARD);
s.addText("Roshan Raj", { x: .95, y: 2.4, w: 5, h: .5, fontFace: HF, fontSize: 21, bold: true, color: INK, margin: 0 });
s.addText("Systems and AI-infrastructure engineer · Manipal Institute of Technology · 7 patents pending", { x: .95, y: 2.9, w: 5, h: .6, fontFace: BF, fontSize: 12.5, color: GRN, margin: 0 });
s.addText("Ishmiit Singh", { x: .95, y: 3.75, w: 5, h: .5, fontFace: HF, fontSize: 21, bold: true, color: INK, margin: 0 });
s.addText("Co-builder: product, content and evidence", { x: .95, y: 4.25, w: 5, h: .4, fontFace: BF, fontSize: 12.5, color: GRN, margin: 0 });
s.addText("Together: the node, the scam shield, the scheme navigator, offline voice, the operator console and the benchmarks behind every number in this deck.",
  { x: .95, y: 4.85, w: 5, h: 1.4, fontFace: BF, fontSize: 12.5, color: MUTE, valign: "top", margin: 0 });
card(s, 6.4, 2.15, 6.3, 4.25, CARD2);
s.addText("The ask", { x: 6.75, y: 2.4, w: 5.7, h: .4, fontFace: HF, fontSize: 14, bold: true, color: SAF, charSpacing: 2, margin: 0 });
s.addText("A single-district pilot with the natural last-mile partners:", { x: 6.75, y: 2.85, w: 5.7, h: .5, fontFace: BF, fontSize: 13, color: INK, margin: 0 });
s.addText([
  { text: "CSC e-Governance / State IT: village access points", options: { bullet: { code: "2022" }, color: MUTE, breakLine: true, paraSpaceAfter: 7 } },
  { text: "A bank BC network / SLBC: reach and real messages for ScamBench v1", options: { bullet: { code: "2022" }, color: MUTE, breakLine: true, paraSpaceAfter: 7 } },
  { text: "A reviewer for scheme rules and money answers", options: { bullet: { code: "2022" }, color: MUTE, breakLine: true, paraSpaceAfter: 7 } },
  { text: "A rural NGO: field testing and Hindi review", options: { bullet: { code: "2022" }, color: MUTE, breakLine: true } }],
  { x: 6.9, y: 3.45, w: 5.55, h: 2.2, fontFace: BF, fontSize: 12.5, valign: "top", margin: 0 });
s.addNotes("Honest: the technology is built; partnerships are what this challenge begins.");

/* 12 CLOSE */
s = P.addSlide(); bg(s);
s.addText("India banked half a billion people.", { x: .7, y: 2.0, w: 12, h: .7, fontFace: HF, fontSize: 26, bold: true, color: INK, margin: 0 });
s.addText("Sahayak helps keep them safe.", { x: .7, y: 2.7, w: 12, h: .7, fontFace: HF, fontSize: 26, bold: true, color: GRN, margin: 0 });
s.addText("Offline · vernacular · privacy-first · built and measured. The connectivity divide, turned into a bridge.",
  { x: .72, y: 3.7, w: 11.6, h: .8, fontFace: BF, fontSize: 15, color: MUTE, margin: 0 });
s.addText("Roshan Raj  ·  Ishmiit Singh", { x: .72, y: 5.6, w: 12, h: .4, fontFace: BF, fontSize: 13.5, bold: true, color: INK, margin: 0 });
s.addNotes("Close on the line: banked half a billion, and Sahayak helps keep them safe.");

P.writeFile({ fileName: path.join(__dirname, "Sahayak_Pitch_Deck_v2.pptx") }).then((f) => console.log("WROTE", f));
