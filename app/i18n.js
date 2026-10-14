/* Display languages for the phone: puts what the engines answered (in English) into the chosen language.
 *
 * The engines, the signed packs and every verdict stay in Hindi and English; this only changes what the
 * screen shows. A pack is one web/i18n/<code>.json, built by scripts/i18n_build.py from the checked
 * translations in i18n/:
 *
 *   const tr = SahayakI18n.create(pack);   // the parsed web/i18n/<code>.json
 *   tr.lookup("It contains a link (sbi-kyc-update.xyz).")   // the translation, or null
 *
 * lookup() tries the exact text first (pack.text, keyed by its English), then each template in
 * pack.templates order (most specific first). A template's English becomes a pattern: each {name} matches
 * any text, whitespace may vary, and the parts it matched are put into the translated template, each one
 * itself translated when it is a known text (a scheme counter sentence carries an age phrase, a scam
 * headline a category name), up to three levels deep. It answers null when nothing fits, so the caller
 * shows the English (or the base language) instead; it never throws.
 *
 * Plain ES2018, no dependencies. UMD: window.SahayakI18n in a browser, module.exports in Node.
 */
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module && module.exports) module.exports = factory();
  else root.SahayakI18n = factory();
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const MAX_DEPTH = 3;      // a filled-in part may itself be a template's text, so far and no further
  const MEMO_MAX = 2000;    // results kept per pack
  const PLACEHOLDER = /\{(\w+)\}/g;
  const own = Object.prototype.hasOwnProperty;

  function escapeLiteral(s) {
    return s.replace(/[.*+?^${}()|[\]\\\/]/g, "\\$&").replace(/\s+/g, "\\s*");
  }

  function squash(s) {
    return s.replace(/\s+/g, " ").trim();
  }

  // "Namaste. {age_phrase} I want it." -> /^Namaste\.\s*(.*?)\s*I\s*want\s*it\.$/su, names ["age_phrase"]
  function compile(english, translated) {
    if (typeof english !== "string" || typeof translated !== "string") return null;
    const names = [];
    let source = "^", last = 0, literal = "", m;
    PLACEHOLDER.lastIndex = 0;
    while ((m = PLACEHOLDER.exec(english)) !== null) {
      literal += english.slice(last, m.index);
      source += escapeLiteral(english.slice(last, m.index)) + "\\s*(.*?)\\s*";
      names.push(m[1]);
      last = m.index + m[0].length;
    }
    literal += english.slice(last);
    source += escapeLiteral(english.slice(last)) + "$";
    if (!names.length || !literal.trim()) return null;  // nothing to fill, or a pattern that matches anything
    source = source.replace(/(?:\\s\*)+/g, "\\s*");
    try {
      return { re: new RegExp(source, "su"), names: names, translated: translated };
    } catch (e) {
      return null;
    }
  }

  function create(pack) {
    const text = pack && typeof pack.text === "object" && pack.text ? pack.text : {};
    const templates = [];
    if (pack && Array.isArray(pack.templates)) {
      for (const t of pack.templates) {
        const c = Array.isArray(t) ? compile(t[0], t[1]) : null;
        if (c) templates.push(c);
      }
    }
    const memo = new Map();

    function remember(key, value) {
      if (memo.size >= MEMO_MAX) memo.delete(memo.keys().next().value);
      memo.set(key, value);
    }

    function fill(t, groups, depth) {
      const values = {};
      t.names.forEach((name, i) => {
        if (own.call(values, name)) return;  // a name counts once: its first match
        const raw = groups[i] === undefined ? "" : groups[i];
        const value = raw.trim();
        const said = value ? find(value, depth + 1) : null;
        values[name] = said === null ? raw : said;
      });
      return squash(t.translated.replace(PLACEHOLDER, (whole, name) => (own.call(values, name) ? values[name] : whole)));
    }

    function find(english, depth) {
      const key = english.trim();
      if (!key) return null;
      if (memo.has(key)) return memo.get(key);
      let out = null;
      if (own.call(text, key) && typeof text[key] === "string") out = text[key];
      else if (depth < MAX_DEPTH) {
        for (const t of templates) {
          const m = t.re.exec(key);
          if (m) { out = fill(t, m.slice(1), depth); break; }
        }
      }
      if (depth === 0) remember(key, out);  // deeper answers may be cut short by the depth limit
      return out;
    }

    return {
      lookup(english) {
        if (typeof english !== "string") return null;
        try {
          return find(english, 0);
        } catch (e) {
          return null;
        }
      },
    };
  }

  return { create: create };
});
