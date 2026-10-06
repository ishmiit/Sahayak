/* Node status page: live zero-egress counters, what is installed (with hashes), and the QR
   sticker. Everything is read from this node; all text goes in through textContent. */
(() => {
  "use strict";
  const $ = (sel) => document.querySelector(sel);
  const short = (h) => (h ? `${h.replace(/^sha256:/, "").slice(0, 12)}…` : "—");
  const mb = (bytes) => `${(bytes / 1e6).toFixed(bytes < 1e6 ? 2 : 1)} MB`;

  function row(cells) {
    const tr = document.createElement("tr");
    for (const c of cells) {
      const td = document.createElement("td");
      td.textContent = c;
      tr.append(td);
    }
    return tr;
  }

  function setBig(id, value) {
    const el = $(id);
    el.textContent = value === null || value === undefined ? "?" : String(value);
    el.parentElement.classList.toggle("zero", value === 0);
    el.parentElement.classList.toggle("nonzero", typeof value === "number" && value > 0);
  }

  async function egress() {
    try {
      const e = await (await fetch("/api/egress", { cache: "no-store" })).json();
      setBig("#nd-connects", e.sahayak.external_connects);
      setBig("#nd-lookups", e.sahayak.external_lookups);
      setBig("#nd-machine", e.machine.available ? e.machine.external : null);
      const own = e.sahayak.external_connects + e.sahayak.external_lookups;
      const head = $("#nd-headline");
      head.textContent = own > 0 ? "⚠ Sahayak ने इंटरनेट से जुड़ने की कोशिश की · Sahayak tried to reach the internet"
        : e.machine.external === 0 ? "इंटरनेट पर कुछ नहीं गया · Nothing went to the internet"
          : "Sahayak ने इंटरनेट पर कुछ नहीं भेजा · Sahayak sent nothing to the internet (this machine itself is online)";
      head.className = own > 0 ? "warn-text" : "";
      const fw = e.firewall;
      const f = $("#nd-firewall");
      f.textContent = fw.offline_rules === true ? `✓ फ़ायरवॉल इंटरनेट रोक रहा है · Firewall blocks the internet (${fw.detail})`
        : fw.offline_rules === false ? `✗ फ़ायरवॉल नियम नहीं लगे · Offline firewall rules not installed (${fw.detail})`
          : `… ${fw.detail}`;
      f.className = `fw ${fw.offline_rules === true ? "ok" : fw.offline_rules === false ? "bad" : ""}`;
      $("#nd-interfaces").replaceChildren(...e.interfaces.map((i) => {
        const li = document.createElement("li");
        li.textContent = `${i.name}: ↑ ${mb(i.sent)} · ↓ ${mb(i.received)}`;
        return li;
      }));
      $("#nd-since").textContent = `${e.since} से · since ${e.since} (${Math.round(e.uptime_s / 60)} min)`;
      $("#nd-recent").replaceChildren(...(e.sahayak.recent_external.length ? e.sahayak.recent_external : [{ host: "—" }]).map((r) => {
        const li = document.createElement("li");
        li.textContent = r.at ? `${r.at} ${r.kind} ${r.host}:${r.port ?? ""}` : "कोई नहीं · none";
        return li;
      }));
    } catch { /* node restarting; keep the last numbers */ }
  }

  async function status() {
    try {
      const s = await (await fetch("/api/status", { cache: "no-store" })).json();
      $("#nd-version").textContent = `v${s.version} · ${s.https ? "HTTPS" : "HTTP"} · ${s.lan_addresses.join(", ")}`;
      $("#nd-app-qr").src = s.app_qr;
      $("#nd-app-url").textContent = s.app_url;
      if (s.wifi) {
        $("#nd-wifi").hidden = false;
        $("#nd-wifi img").src = s.wifi.qr;
        $("#nd-wifi figcaption").textContent = `Wi-Fi: ${s.wifi.ssid}`;
      }
      $("#nd-signed-mode").textContent = s.require_signed
        ? "यह नोड सिर्फ़ हस्ताक्षरित पैक लेता है · This node accepts signed packs only"
        : "हस्ताक्षर जाँचे जाते हैं; बदला हुआ पैक नहीं चलता · Signatures are checked; an altered pack is refused";
      $("#nd-packs").replaceChildren(...s.packs.map((p) =>
        row([p.name, p.version, p.date, p.signed_by ? "✓" : "✗", short(p.sha256)])));
      const models = s.speech_models.map((m) => row([m.name, `${m.mb} MB`, short(m.sha256)]));
      if (s.llm && s.llm.model) models.unshift(row([`${s.llm.model} (${s.llm.backend})`, s.llm.size_mb ? `${s.llm.size_mb} MB` : "—", short(s.llm.digest)]));
      $("#nd-models").replaceChildren(...models);
    } catch { /* keep what is shown */ }
  }

  $("#nd-print").addEventListener("click", () => {
    const s = $("#nd-sticker");
    s.classList.add("printing");
    window.print();
    s.classList.remove("printing");
  });

  egress();
  status();
  setInterval(egress, 2000);
  setInterval(status, 30000);
})();
