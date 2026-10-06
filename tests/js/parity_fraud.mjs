// Replay tests/js/fraud_corpus.json through web/checker.js and require exactly what the node's Python
// Fraud-Shield returned: every card field, every string, every number, and the key order of every
// object (the random id and the timings excepted; the id must still be 12 hex digits).
//
//   node tests/js/parity_fraud.mjs [corpus.json]
//
// Exit 0 on full parity, 1 on any mismatch (each one printed: case, field, python value, js value),
// 2 if the corpus is missing or was written for another fraud pack. Also compares fold() and the
// unrounded model scores (a difference above 1e-9 is a mismatch; smaller ones are reported), and
// times check() here. SAHAYAK_CHECKER_JS=<file> tests another copy of checker.js.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { performance } from "node:perf_hooks";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const require = createRequire(import.meta.url);
const SahayakChecker = require(resolve(process.env.SAHAYAK_CHECKER_JS || resolve(ROOT, "web", "checker.js")));

const corpusPath = resolve(process.argv[2] || resolve(ROOT, "tests", "js", "fraud_corpus.json"));
let corpus;
try {
  corpus = JSON.parse(readFileSync(corpusPath, "utf8"));
} catch (e) {
  console.error(`cannot read ${corpusPath}: ${e.message}\nrun: python tests/js/make_fraud_corpus.py`);
  process.exit(2);
}

// The packs, as the phone gets them; the fraud pack's hash as the node computes it (LF line endings).
const packBytes = (name) => readFileSync(resolve(ROOT, "packs", name));
const fraudRaw = packBytes("fraud.v1.json");
const fraudSha256 = createHash("sha256").update(Buffer.from(fraudRaw.toString("latin1").replace(/\r\n/g, "\n"), "latin1")).digest("hex");
if (fraudSha256 !== corpus.fraud_sha256) {
  console.error("packs/fraud.v1.json changed since the corpus was written; run: python tests/js/make_fraud_corpus.py");
  process.exit(2);
}
const packs = {
  fraud: JSON.parse(fraudRaw.toString("utf8")),
  patterns: JSON.parse(packBytes("scam_patterns.v1.json").toString("utf8")),
  model: JSON.parse(packBytes("fraud_model.v1.json").toString("utf8")),
};
let t0 = performance.now();
const checker = SahayakChecker.create({ ...packs, fraudSha256 });
const createMs = performance.now() - t0;

// ---------------------------------------------------------------- comparison

// JSON cannot carry inf/nan; the corpus writes them as {"__float__": "inf"}.
function plain(x) {
  if (typeof x === "number" && !Number.isFinite(x)) return { __float__: Number.isNaN(x) ? "nan" : x > 0 ? "inf" : "-inf" };
  if (Array.isArray(x)) return x.map(plain);
  if (x && typeof x === "object") {
    const out = {};
    for (const k of Object.keys(x)) out[k] = plain(x[k]);
    return out;
  }
  return x;
}
const show = (v) => (v === undefined ? "(missing)" : JSON.stringify(v));

/** Differences between Python's value and ours: [path, python, js] for each, keys in order. */
function diff(py, js, path, out) {
  if (py === js) return out;
  if (typeof py === "number" && typeof js === "number") {
    if (py !== js) out.push([path, py, js]);
    return out;
  }
  if (Array.isArray(py) && Array.isArray(js)) {
    if (py.length !== js.length) out.push([path + ".length", py.length, js.length]);
    for (let i = 0; i < Math.min(py.length, js.length); i++) diff(py[i], js[i], `${path}[${i}]`, out);
    return out;
  }
  if (py && js && typeof py === "object" && typeof js === "object" && !Array.isArray(py) && !Array.isArray(js)) {
    const pk = Object.keys(py), jk = Object.keys(js);
    if (pk.join("\u0000") !== jk.join("\u0000")) out.push([path + " (keys)", pk, jk]);
    for (const k of pk) if (k in js) diff(py[k], js[k], `${path}.${k}`, out);
    return out;
  }
  out.push([path, py, js]);
  return out;
}

const mismatches = [];
const fieldsCompared = new Map();  // field -> count
const tally = (f) => fieldsCompared.set(f, (fieldsCompared.get(f) || 0) + 1);
const rawStats = {};
const counts = {};
let comparisons = 0;

function label(c, i) {
  const what = c.kind === "check" ? c.text : c.kind === "qr" ? c.payload : String(c.amount);
  const short = what.length > 70 ? what.slice(0, 70) + "…" : what;
  const extra = c.kind === "check" ? ` sender=${show(c.sender)} input_type=${c.input_type}` : "";
  return `#${i} ${c.source}/${c.kind} ${show(short)}${extra}`;
}
function report(c, i, field, py, js) {
  mismatches.push(`${label(c, i)}\n      field ${field}\n      python ${show(py).slice(0, 400)}\n      js     ${show(js).slice(0, 400)}`);
}

corpus.cases.forEach((c, i) => {
  counts[c.source] = (counts[c.source] || 0) + 1;
  if (c.kind === "check") {
    const card = checker.check(c.text, { sender: c.sender, inputType: c.input_type, debug: true });
    const dbg = card._debug;
    const js = plain(card);
    // every Python field, in Python's order, then the two that are not compared
    const keys = Object.keys(c.card);
    const jsKeys = Object.keys(js).filter((k) => k !== "id" && k !== "timing_ms");
    tally("(card keys)"); comparisons++;
    if (keys.join() !== jsKeys.join()) report(c, i, "(card keys)", keys, jsKeys);
    for (const k of keys) {
      tally(k); comparisons++;
      for (const [path, a, b] of diff(c.card[k], js[k], k, [])) report(c, i, path, a, b);
    }
    tally("id"); comparisons++;
    if (!/^[0-9a-f]{12}$/.test(card.id)) report(c, i, "id", "12 hex digits", card.id);
    tally("timing_ms"); comparisons++;
    if (!card.timing_ms || typeof card.timing_ms.signals !== "number" || typeof card.timing_ms.total !== "number") {
      report(c, i, "timing_ms", "{signals, total}", card.timing_ms);
    }
    tally("fold"); comparisons++;
    if (dbg.norm !== c.norm) report(c, i, "fold(text)", c.norm, dbg.norm);
    for (const k of Object.keys(c.raw)) {
      const st = (rawStats[k] ||= { n: 0, exact: 0, maxDiff: 0, worst: null });
      const d = Math.abs(dbg[k] - c.raw[k]);
      st.n++;
      if (dbg[k] === c.raw[k]) st.exact++;
      else if (d > st.maxDiff) { st.maxDiff = d; st.worst = label(c, i); }
      tally(`raw ${k}`); comparisons++;
      if (!(d <= 1e-9)) report(c, i, `raw ${k} (unrounded)`, c.raw[k], dbg[k]);
    }
  } else if (c.kind === "qr") {
    tally("analyseQR"); comparisons++;
    let js, err = null;
    try { js = plain(checker.analyseQR(c.payload)); } catch (e) { err = e.name || "Error"; }
    if (c.error) {
      if (err !== c.error) report(c, i, "analyseQR (raises)", c.error, err || js);
    } else if (err) report(c, i, "analyseQR", c.analyse, `raised ${err}`);
    else for (const [path, a, b] of diff(c.analyse, js, "analyse", [])) report(c, i, path, a, b);
  } else if (c.kind === "rupees") {
    tally("rupees"); comparisons++;
    const js = SahayakChecker.rupees(c.amount);
    if (js !== c.text) report(c, i, "rupees", c.text, js);
  }
});

// ---------------------------------------------------------------- timing (no debug, cards discarded)

const texts = corpus.cases.filter((c) => c.kind === "check");
for (let r = 0; r < 2; r++) for (const c of texts.slice(0, 200)) checker.check(c.text, { sender: c.sender, inputType: c.input_type });
const times = [];
let longest = { ms: 0, label: "" };
for (let r = 0; r < 3; r++) {
  for (const c of texts) {
    const s = performance.now();
    checker.check(c.text, { sender: c.sender, inputType: c.input_type });
    const ms = performance.now() - s;
    times.push(ms);
    if (ms > longest.ms) longest = { ms, label: `${c.source} (${c.text.length} chars)` };
  }
}
times.sort((a, b) => a - b);
const q = (p) => times[Math.min(times.length - 1, Math.floor(p * times.length))];

// ---------------------------------------------------------------- summary

console.log(`corpus: ${corpus.cases.length} cases (${Object.entries(counts).map(([k, v]) => `${k} ${v}`).join(", ")})`);
console.log(`fields compared: ${[...fieldsCompared.entries()].map(([k, v]) => `${k}×${v}`).join(", ")}`);
console.log(`${comparisons} comparisons`);
for (const [k, st] of Object.entries(rawStats)) {
  console.log(`raw ${k}: ${st.exact}/${st.n} bit-identical to Python; largest difference ${st.maxDiff.toExponential(2)}` +
    (st.worst ? ` (${st.worst.slice(0, 90)})` : ""));
}
console.log(`check(): median ${q(0.5).toFixed(3)} ms, p95 ${q(0.95).toFixed(3)} ms, max ${times[times.length - 1].toFixed(3)} ms ` +
  `[${longest.label}] over ${times.length} runs`);
console.log(`create(): ${createMs.toFixed(1)} ms`);
if (mismatches.length) {
  console.log(`\nMISMATCHES: ${mismatches.length}`);
  for (const m of mismatches.slice(0, 80)) console.log(`  ${m}`);
  if (mismatches.length > 80) console.log(`  … and ${mismatches.length - 80} more`);
  process.exit(1);
}
console.log("parity: 100% (0 mismatches)");
