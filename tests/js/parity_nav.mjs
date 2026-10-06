// Replay tests/js/nav_corpus.json through web/navigator.js and require exactly what the Python
// Navigator returned: every field, every string, and the key order of every object.
//
//   node tests/js/parity_nav.mjs [corpus.json]
//
// Exit 0 on full parity, 1 on any mismatch (each one printed), 2 if the corpus is missing or stale.
// Also reports how long next() and result() take here. SAHAYAK_NAVIGATOR_JS=<file> tests another
// copy of navigator.js (used to check that deliberately broken copies fail).
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const require = createRequire(import.meta.url);
const SahayakNavigator = require(resolve(process.env.SAHAYAK_NAVIGATOR_JS || resolve(ROOT, "web", "navigator.js")));

const corpusPath = resolve(process.argv[2] || resolve(ROOT, "tests", "js", "nav_corpus.json"));
let corpus;
try {
  corpus = JSON.parse(readFileSync(corpusPath, "utf8"));
} catch (e) {
  console.error(`cannot read ${corpusPath}: ${e.message}\nrun: python tests/js/make_nav_corpus.py`);
  process.exit(2);
}
// Each section names its pack: a file in the repo (which must not have changed since the corpus
// was written) or a synthetic pack carried in the corpus itself.
function packOf(section) {
  if (!section.pack_file) return section.pack;
  const raw = readFileSync(resolve(ROOT, section.pack_file));
  if (createHash("sha256").update(raw).digest("hex") !== section.pack_sha256) {
    console.error(`${section.pack_file} changed since the corpus was written; run: python tests/js/make_nav_corpus.py`);
    process.exit(2);
  }
  return JSON.parse(raw.toString("utf8"));
}

// ---------------------------------------------------------------- expected values: expand {"$ref": n}

const expanded = new Map();
function expand(v) {
  if (Array.isArray(v)) return v.map(expand);
  if (v === null || typeof v !== "object") return v;
  const keys = Object.keys(v);
  if (keys.length === 1 && keys[0] === "$ref") {
    const n = v.$ref;
    if (!expanded.has(n)) expanded.set(n, expand(corpus.table[n]));
    return expanded.get(n);
  }
  const out = {};
  for (const k of keys) out[k] = expand(v[k]);
  return out;
}

// ---------------------------------------------------------------- exact comparison

const show = (v) => {
  const s = JSON.stringify(v);
  return s === undefined ? String(v) : s.length > 300 ? s.slice(0, 300) + "…" : s;
};
const kind = (v) => (v === null ? "null" : Array.isArray(v) ? "array" : typeof v);

// The first difference between want and got, or null. Objects must have the same keys in the same order.
function diff(want, got, path) {
  if (kind(want) !== kind(got)) return `${path}: expected ${kind(want)} ${show(want)}, got ${kind(got)} ${show(got)}`;
  if (Array.isArray(want)) {
    if (want.length !== got.length) return `${path}: expected ${want.length} items ${show(want)}, got ${got.length} ${show(got)}`;
    for (let i = 0; i < want.length; i++) {
      const d = diff(want[i], got[i], `${path}[${i}]`);
      if (d) return d;
    }
    return null;
  }
  if (want !== null && typeof want === "object") {
    const wk = Object.keys(want), gk = Object.keys(got);
    if (wk.length !== gk.length || wk.some((k, i) => k !== gk[i])) return `${path}: expected keys ${show(wk)}, got ${show(gk)}`;
    for (const k of wk) {
      const d = diff(want[k], got[k], `${path}.${k}`);
      if (d) return d;
    }
    return null;
  }
  return want === got ? null : `${path}: expected ${show(want)}, got ${show(got)}`;
}

// ---------------------------------------------------------------- replay

const TODAY = new Date(`${corpus.today}T12:00:00`); // local noon: the local date is corpus.today
const times = { next: [], result: [] };
let compared = 0, cases = 0;
const mismatches = [];

function run(op, fn) {
  const t0 = performance.now();
  try {
    const ok = fn();
    times[op].push(performance.now() - t0);
    return { ok };
  } catch (e) {
    if (e instanceof SahayakNavigator.AnswerError) return { error: "AnswerError", message: e.message };
    if (e instanceof TypeError) return { error: "TypeError", message: e.message };
    return { error: `unexpected ${e && e.name}`, message: String(e && e.stack) };
  }
}

// The node's result has no timing_ms here (it is measured, not computed); the phone's must have
// one, as a number, just before "slip".
function dropTiming(got, where) {
  if (!got.ok) return got;
  const keys = Object.keys(got.ok);
  const at = keys.indexOf("timing_ms");
  if (at < 0 || at !== keys.length - 2 || keys[at + 1] !== "slip" || typeof got.ok.timing_ms !== "number" || !(got.ok.timing_ms >= 0)) {
    mismatches.push(`${where}: timing_ms missing, misplaced or not a number: ${show(keys)}`);
  }
  const ok = {};
  for (const k of keys) if (k !== "timing_ms") ok[k] = got.ok[k];
  return { ok };
}

function check(where, want, got) {
  compared++;
  const d = diff(expand(want), got, where);
  if (d) mismatches.push(d);
}

// The interview as Navigator.interview runs it: answer each question from the full answer set.
function answerFor(persona, q) {
  if (q.kind === "multi") {
    const shown = new Set(q.options.map((o) => o.id));
    return persona.situation.filter((s) => shown.has(s));
  }
  return persona[q.id];
}

for (const section of corpus.sections) {
  const nav = SahayakNavigator.create(packOf(section));
  const callNext = (answers) => run("next", () => nav.next(answers));
  const callResult = (answers, already, where) => dropTiming(run("result", () => nav.result(answers, already, TODAY)), where);
  const at = (id) => `[${section.name}] ${id}`;

  check(at("catalog"), section.catalog, nav.catalog());
  for (const c of section.cases) {
    cases++;
    if (c.kind === "call") {
      if (c.next) check(at(`${c.id} next`), c.next, callNext(c.answers));
      if (c.result) check(at(`${c.id} result`), c.result, callResult(c.answers, c.already, at(c.id)));
      continue;
    }
    // kind "interview": the phone picks each answer from its own question, so a wrong question
    // shows up as a wrong step, not as a replay of the node's choices.
    const answers = {};
    let failed = false;
    for (let i = 0; ; i++) {
      const got = callNext(answers);
      if (i >= c.steps.length) {
        mismatches.push(`${at(c.id)} step ${i}: the phone asks more than the node (${show(got)})`);
        failed = true;
        break;
      }
      const before = mismatches.length;
      check(at(`${c.id} step ${i}`), c.steps[i], got);
      if (mismatches.length > before) { failed = true; break; }
      if (got.ok.done || (c.stop !== null && Object.keys(answers).length >= c.stop)) {
        if (i !== c.steps.length - 1) {
          mismatches.push(`${at(c.id)} step ${i}: the phone stops, the node asks ${c.steps.length - 1 - i} more`);
          failed = true;
        }
        break;
      }
      answers[got.ok.question.id] = answerFor(c.persona, got.ok.question);
    }
    if (failed) continue;
    check(at(`${c.id} result`), c.result, callResult(answers, [], at(c.id)));
    if (c.result_already) {
      check(at(`${c.id} result already=${show(c.already)}`), c.result_already, callResult(answers, c.already, at(c.id)));
    }
  }
}

// ---------------------------------------------------------------- report

function stats(xs) {
  const s = [...xs].sort((a, b) => a - b);
  const q = (p) => s[Math.min(s.length - 1, Math.floor(p * s.length))];
  return `n=${s.length} median ${q(0.5).toFixed(3)} ms, p95 ${q(0.95).toFixed(3)} ms, max ${s[s.length - 1].toFixed(3)} ms`;
}

const real = packOf(corpus.sections[0]);
const t0 = performance.now();
for (let i = 0; i < 20; i++) SahayakNavigator.create(real);
const createMs = (performance.now() - t0) / 20;

for (const s of corpus.sections) console.log(`[${s.name}] ${s.cases.length} cases ${JSON.stringify(s.counts)}`);
console.log(`${cases} cases, ${compared} exact comparisons`);
console.log(`next():   ${stats(times.next)}`);
console.log(`result(): ${stats(times.result)}`);
console.log(`create(): ${createMs.toFixed(3)} ms`);
if (mismatches.length) {
  console.log(`\nMISMATCHES: ${mismatches.length}`);
  for (const m of mismatches.slice(0, 60)) console.log(`  ${m}`);
  if (mismatches.length > 60) console.log(`  … and ${mismatches.length - 60} more`);
  process.exit(1);
}
console.log("parity: 100% (0 mismatches)");
