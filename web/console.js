/* Operator console. Talks only to this node. All text goes in through textContent. */
(() => {
  "use strict";
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    node.append(...kids.flat(2).filter((kid) => kid != null && kid !== false));
    return node;
  }

  async function api(path, body, method) {
    const res = await fetch(path, {
      method: method || (body ? "POST" : "GET"),
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
      credentials: "same-origin",
    });
    if (res.status === 401) { await res.text().catch(() => ""); showLogin(); throw new Error("login"); }
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
    return res.json();
  }

  // ---------------------------------------------------------------- login
  function showLogin() { $("#c-app").hidden = true; $("#c-login").hidden = false; $("#c-logout").hidden = true; }
  function showApp() { $("#c-login").hidden = true; $("#c-app").hidden = false; $("#c-logout").hidden = false; tab("queue"); }
  $("#c-login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/console/login", { pin: $("#c-pin").value.trim() });
      $("#c-pin").value = "";
      showApp();
    } catch (err) {
      $("#c-login-msg").textContent = err.message === "login" ? "गलत PIN · Wrong PIN" : err.message;
    }
  });
  $("#c-logout").addEventListener("click", async () => { await api("/api/console/logout", {}).catch(() => {}); showLogin(); });

  // ---------------------------------------------------------------- tabs
  let current = "queue";
  function tab(name) {
    current = name;
    $$(".c-nav button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
    $$(".c-tab").forEach((s) => { s.hidden = s.dataset.tab !== name; });
    ({ queue: loadQueue, cases: loadCases, counters: loadCounters, reference: loadReference, status: loadStatus })[name]?.();
  }
  $$(".c-nav button").forEach((b) => b.addEventListener("click", () => tab(b.dataset.tab)));

  // ---------------------------------------------------------------- speaking for the person
  async function speak(text, lang) {
    try {
      for (const part of text.split(/(?<=[।.?!])\s+/).filter(Boolean)) {
        const res = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: part, lang, voice: "female", speed: 0.85 }) });
        if (!res.ok) return;
        const url = URL.createObjectURL(await res.blob());
        await new Promise((resolve) => { const a = new Audio(url); a.onended = resolve; a.onerror = resolve; a.play().catch(resolve); });
        URL.revokeObjectURL(url);
      }
    } catch { /* speaking is best effort */ }
  }

  // ---------------------------------------------------------------- verdict card, slip and case log
  function verdictCard(card, lang, ticket) {
    const other = lang === "hi" ? "en" : "hi";
    const box = el("div", {},
      el("div", { class: `verdict ${card.verdict}` }, el("div", {},
        el("div", { class: "v-label" }, card.label[lang]), el("div", { class: "v-label-2" }, card.label[other]))),
      el("h3", {}, card.headline[lang]),
      el("ul", { class: "reasons" }, card.reasons.map((r) => el("li", {}, r.text[lang], el("span", { class: "en" }, r.text[other])))),
      el("ol", { class: "actions" }, card.actions[lang].map((a, i) => el("li", {}, a, el("span", { class: "en" }, card.actions[other][i])))));
    const consent = el("input", { type: "checkbox" });
    let printed = false;
    const actions = el("div", { class: "cta-row" },
      el("button", { class: "secondary", type: "button", onclick: () => speak(`${card.label[lang]}. ${card.headline[lang]} ${card.actions[lang].join(" ")}`, lang) }, "पढ़कर सुनाएँ · Read aloud"),
      el("button", { class: "primary", type: "button", onclick: () => { printFraud(card, lang); printed = true; } }, "58 mm स्लिप · Print slip"),
      el("button", { class: "secondary", type: "button", onclick: async () => {
        try {
          await api("/api/console/caselog", { consent: consent.checked, entry: {
            kind: "check", verdict: card.verdict, category: card.category ? card.category.id : null,
            rupees_at_risk: card.extracted.rupees_at_risk, lang, slip_printed: printed } });
          toast("केस लॉग में रखा · Saved to the case log");
        } catch (e) { toast(e.message); }
      } }, "केस लॉग में रखें · Save to case log"),
      ticket ? el("button", { class: "ghost", type: "button", onclick: () => finish(ticket) }, "पूरा हुआ · Done") : null);
    box.append(el("label", { class: "consent" }, consent, "व्यक्ति ने रिकॉर्ड रखने की अनुमति दी · The person agrees to keep a record"), actions);
    return box;
  }

  function stamp() { return new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }); }

  function printSlip(build, kind) {
    $("#print58").replaceChildren(...build());
    window.print();
    fetch("/api/counters/slip", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind }) }).catch(() => {});
  }

  function printFraud(card, lang) {
    printSlip(() => [
      el("h1", {}, lang === "hi" ? "सहायक — मैसेज जाँच" : "Sahayak — message check"),
      el("div", { class: "small" }, stamp()),
      el("div", { class: "big" }, card.label[lang]),
      el("div", {}, card.headline[lang]),
      el("hr"),
      el("b", {}, lang === "hi" ? "क्यों:" : "Why:"),
      el("ul", {}, card.reasons.map((r) => el("li", {}, r.text[lang]))),
      el("b", {}, lang === "hi" ? "अब क्या करें:" : "What to do:"),
      el("ol", {}, card.actions[lang].map((a) => el("li", {}, a))),
      el("hr"),
      el("div", {}, lang === "hi" ? "पैसे गए? तुरंत 1930 पर कॉल करें या cybercrime.gov.in पर शिकायत करें।" : "Lost money? Call 1930 at once or report at cybercrime.gov.in."),
      el("div", { class: "small" }, lang === "hi" ? "बैंक कभी OTP या PIN नहीं माँगता।" : "Banks never ask for an OTP or PIN."),
    ], "fraud");
  }

  async function printBenefits(answers, lang) {
    const r = await api("/api/navigator/result", { answers });
    const byId = Object.fromEntries(r.schemes.map((s) => [s.id, s]));
    const ids = ["eligible", "likely", "check", "unlock"].flatMap((g) => r.groups[g]);
    printSlip(() => [
      el("h1", {}, lang === "hi" ? "सहायक — योजना पर्ची" : "Sahayak — scheme slip"),
      el("div", { class: "small" }, stamp()),
      el("img", { src: r.slip.qr, alt: "QR" }),
      ...ids.map((id) => {
        const s = byId[id];
        return el("div", {}, el("b", {}, s.name[lang]), s.benefit_now ? el("div", {}, s.benefit_now[lang]) : null,
          el("div", { class: "small" }, s.documents.map((d) => `☐ ${d[lang]}`).join("  ")), el("hr"));
      }),
      el("div", { class: "small" }, r.notes.amount[lang]),
      el("div", { class: "small" }, r.notes.decision[lang]),
    ], "scheme");
  }

  // ---------------------------------------------------------------- queue
  async function loadQueue() {
    if (current !== "queue") return;
    try {
      const { items } = await api("/api/console/queue");
      $("#c-qcount").textContent = String(items.length);
      $("#c-queue").replaceChildren(...(items.length ? items.map(queueItem) : [el("li", { class: "empty" }, "अभी कोई इंतज़ार में नहीं · Nobody waiting")]));
    } catch { /* login screen shown by api() */ }
  }

  function queueItem(item) {
    const s = item.summary;
    const what = item.kind === "check"
      ? `${s.label ? s.label[item.lang] : s.verdict}${s.category ? ` · ${s.category[item.lang]}` : ""}${s.rupees_at_risk ? ` · ₹${s.rupees_at_risk.toLocaleString("en-IN")} at risk` : ""}`
      : Object.entries(s.groups || {}).map(([g, names]) => `${g}: ${names.join(", ")}`).join(" · ") || "—";
    return el("li", { class: item.state === "serving" ? "serving" : "" },
      el("span", { class: "ticket" }, item.ticket),
      el("div", {}, el("b", {}, item.kind === "check" ? "मैसेज जाँच · Message check" : "योजनाएँ · Benefits"),
        el("div", { class: "meta" }, `${item.at} · ${item.lang === "hi" ? "हिंदी" : "English"} · ${what}`)),
      el("button", { class: "primary", type: "button", onclick: () => serve(item) }, "बुलाएँ · Serve"));
  }

  async function serve(item) {
    await api(`/api/console/queue/${item.ticket}`, { state: "serving" }).catch(() => {});
    const box = $("#c-serving");
    box.hidden = false;
    box.replaceChildren(el("h3", {}, `${item.ticket} · ${item.kind === "check" ? "Message check" : "Benefits"}`));
    if (item.kind === "check") {
      try {
        const card = await api(`/api/console/case/${item.summary.check_id}`);
        box.append(verdictCard(card, item.lang, item.ticket));
      } catch (e) {
        box.append(el("p", {}, e.message), el("button", { class: "ghost", type: "button", onclick: () => finish(item.ticket) }, "पूरा हुआ · Done"));
      }
    } else {
      const consent = el("input", { type: "checkbox" });
      const answers = item.summary.answers;
      const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(answers)))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
      // A tick per scheme once the card is made or the form filed here: the node then reports what people actually
      // claimed, not only who was found eligible.
      const doneRow = el("div", { class: "cta-row" });
      api("/api/navigator/result", { answers }).then((r) => {
        const ids = ["eligible", "likely"].flatMap((g) => r.groups[g] || []);
        const byId = Object.fromEntries(r.schemes.map((sc) => [sc.id, sc]));
        doneRow.replaceChildren(...ids.map((id) => el("button", { class: "secondary", type: "button", onclick: async (e) => {
          try {
            await api("/api/console/done", { scheme: id });
            e.target.disabled = true;
            e.target.textContent = `✓ ${byId[id].short}`;
          } catch (err) { toast(err.message); }
        } }, `${byId[id].short}: कार्ड / फ़ॉर्म बना · done`)));
      }).catch(() => {});
      box.append(
        el("ul", {}, Object.entries(item.summary.groups || {}).map(([g, names]) => el("li", {}, `${g}: ${names.join(", ")}`))),
        doneRow,
        el("label", { class: "consent" }, consent, "व्यक्ति ने रिकॉर्ड रखने की अनुमति दी · The person agrees to keep a record"),
        el("div", { class: "cta-row" },
          el("a", { class: "secondary", href: `/?answers=${encoded}&lang=${item.lang}`, target: "_blank", rel: "noopener" }, "ऐप में खोलें · Open in the app"),
          el("button", { class: "primary", type: "button", onclick: () => printBenefits(answers, item.lang).catch((e) => toast(e.message)) }, "58 mm स्लिप · Print slip"),
          el("button", { class: "secondary", type: "button", onclick: async () => {
            try {
              await api("/api/console/caselog", { consent: consent.checked, entry: { kind: "benefits", schemes: item.summary.groups, lang: item.lang } });
              toast("केस लॉग में रखा · Saved to the case log");
            } catch (e) { toast(e.message); }
          } }, "केस लॉग में रखें · Save to case log"),
          el("button", { class: "ghost", type: "button", onclick: () => finish(item.ticket) }, "पूरा हुआ · Done")));
    }
    loadQueue();
  }

  async function finish(ticket) {
    await api(`/api/console/queue/${ticket}`, { state: "done" }).catch(() => {});
    $("#c-serving").hidden = true;
    loadQueue();
  }

  // ---------------------------------------------------------------- assisted check
  $("#a-check").addEventListener("click", async () => {
    const text = $("#a-text").value.trim();
    if (!text) return;
    const lang = $("#a-lang").value;
    try {
      const card = await api("/api/check", { text, sender: $("#a-sender").value.trim() || null, input_type: $("#a-type").value, lang });
      const box = $("#a-result");
      box.hidden = false;
      box.replaceChildren(verdictCard(card, lang, null));
      speak(`${card.label[lang]}. ${card.headline[lang]}`, lang);
    } catch (e) { toast(e.message); }
  });
  $("#a-lang").addEventListener("change", () => { $("#a-benefits").href = `/?nav=start&lang=${$("#a-lang").value}`; });

  // ---------------------------------------------------------------- case log
  async function loadCases() {
    const { entries, keep_days: days } = await api("/api/console/caselog");
    $("#c-cases-note").textContent = `सिर्फ़ अनुमति से, बिना नाम-नंबर, ${days} दिन बाद अपने-आप मिटता है · Only with consent, no names or numbers, deleted automatically after ${days} days. Encrypted on this node.`;
    $("#c-cases").replaceChildren(...(entries.length ? entries.map((e) => {
      const tr = document.createElement("tr");
      const schemes = e.schemes ? Object.entries(e.schemes).map(([g, n]) => `${g}: ${n.join(", ")}`).join("; ") : "";
      for (const v of [e.at, e.kind, e.verdict || schemes, e.category || "", e.rupees_at_risk ? `₹${e.rupees_at_risk}` : "", e.lang || "", e.slip_printed ? "✓" : ""]) {
        const td = document.createElement("td"); td.textContent = v; tr.append(td);
      }
      return tr;
    }) : [el("tr", {}, el("td", { colspan: "7" }, "कोई केस नहीं · No cases"))]));
  }
  $("#c-delete-all").addEventListener("click", async () => {
    if (!confirm("केस लॉग, कतार और याद में रखी जाँचें मिटाएँ? · Delete the case log, the queue and every check held in memory?")) return;
    await api("/api/console/delete-everything", {});
    toast("सब मिटा दिया · Everything deleted");
    loadCases();
  });

  // ---------------------------------------------------------------- counters
  const LABELS = { checks: "जाँचें · Checks run", verdicts: "नतीजे · Verdicts", categories: "ठगी के प्रकार · Top categories",
    schemes: "योजनाएँ मिलीं · Schemes identified", done: "कार्ड / फ़ॉर्म बने · Cards and forms done",
    slips: "पर्चियाँ छपीं · Slips printed", languages: "भाषाएँ · Languages" };
  async function loadCounters() {
    const { month, export_rows: rows } = await api("/api/console/counters");
    const by = {};
    for (const [field, key, value] of rows) (by[field] = by[field] || []).push([key, value]);
    const boxes = Object.entries(LABELS).map(([field, label]) => el("div", { class: "box" }, el("h4", {}, label),
      el("ul", {}, (by[field] || [["—", "0"]]).map(([k, v]) => el("li", {}, `${k}: ${v}`)))));
    const money = (by.rupees_at_risk || [["", "0"]])[0][1];
    const esc = (by.escalations || [["", "0"]])[0][1];
    $("#c-counters").replaceChildren(
      el("div", { class: "box" }, el("h4", {}, `महीना · Month`), el("div", { class: "n" }, month)),
      el("div", { class: "box" }, el("h4", {}, "ठगी वाले मैसेज में दाँव पर रकम · Rupees at risk in flagged messages"),
        el("div", { class: "n" }, /^\d+$/.test(money) ? `₹${Number(money).toLocaleString("en-IN")}` : money)),
      el("div", { class: "box" }, el("h4", {}, "एजेंट से पूछा · Escalations"), el("div", { class: "n" }, esc)),
      ...boxes);
  }
  $("#c-export").addEventListener("click", async () => {
    const out = await api("/api/console/export");
    for (const [name, text] of [[`sahayak-counters-${out.month}.csv`, out.csv], [`sahayak-counters-${out.month}.csv.sig`, out.signature],
      ["sahayak-node-export.pub", out.public_key]]) {
      const a = el("a", { href: URL.createObjectURL(new Blob([text], { type: "text/plain" })), download: name });
      document.body.append(a); a.click(); a.remove();
    }
  });
  $("#c-reset").addEventListener("click", async () => {
    if (!confirm("इस महीने की गिनती शून्य करें? · Reset all counters?")) return;
    await api("/api/console/counters/reset", {});
    loadCounters();
  });

  // ---------------------------------------------------------------- quick reference
  async function loadReference() {
    const { categories } = await api("/api/console/reference");
    $("#c-reference").replaceChildren(...categories.map((c) => el("div", { class: "ref" },
      el("h4", {}, c.name.hi, " · ", c.name.en, c.seen ? el("span", { class: "seen" }, `इस महीने ${c.seen} · ${c.seen} this month`) : null),
      el("ol", {}, c.actions.hi.map((a, i) => el("li", {}, a, el("span", { class: "en" }, c.actions.en[i])))))));
  }

  // ---------------------------------------------------------------- status
  async function loadStatus() {
    try {
      const e = await (await fetch("/api/egress")).json();
      const box = (n, label) => el("div", { class: `bign ${n === 0 ? "zero" : n > 0 ? "nonzero" : ""}` }, el("span", {}, String(n ?? "?")), el("small", {}, label));
      $("#c-status").replaceChildren(
        box(e.sahayak.external_connects, "Sahayak के बाहरी कनेक्शन · outbound connections by Sahayak"),
        box(e.sahayak.external_lookups, "बाहरी DNS सवाल · outside DNS lookups by Sahayak"),
        box(e.machine.external, "इस मशीन के इंटरनेट कनेक्शन · internet connections, whole machine"));
    } catch { /* ignore */ }
  }

  // ---------------------------------------------------------------- toast
  let toastTimer;
  function toast(msg) {
    let t = $(".toast");
    if (!t) { t = el("div", { class: "toast", role: "status" }); document.body.append(t); }
    t.textContent = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.remove(), 3500);
  }

  // start: if a session cookie is still valid, go straight in
  api("/api/console/queue").then(showApp).catch(() => showLogin());
  setInterval(() => { if (!$("#c-app").hidden) { loadQueue(); if (current === "status") loadStatus(); } }, 2000);
})();
