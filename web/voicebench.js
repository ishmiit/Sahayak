/* VoiceBench recorder: consent, speaker group (no name), then one prompt per screen, hold to
   record, listen back, next. Each take is posted to the node as soon as it is accepted. */
(() => {
  "use strict";
  const $ = (sel) => document.querySelector(sel);
  const Mic = window.SahayakMic;
  const show = (id) => document.querySelectorAll("main > .screen").forEach((s) => { s.hidden = s.id !== id; });
  const vb = { session: null, prompts: [], i: 0, take: null, url: null, saved: 0 };

  async function api(path, opts = {}) {
    const res = await fetch(path, opts);
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
    return res.json();
  }

  $("#vb-agree").addEventListener("change", (e) => { $("#vb-next1").disabled = !e.target.checked; });
  $("#vb-next1").addEventListener("click", () => show("vb-speaker"));

  $("#vb-start").addEventListener("click", async () => {
    const f = $("#vb-form");
    const age = f.querySelector('input[name="age_band"]:checked');
    if (!age) { alert("उम्र चुनें / Pick an age group"); return; }
    try {
      vb.prompts = (await api("/api/voicebench/prompts")).prompts;
      vb.session = (await api("/api/voicebench/session", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          consent: true, age_band: age.value, gender: f.querySelector('input[name="gender"]:checked').value,
          region: f.region.value.trim(), first_language: f.first_language.value.trim(),
        }),
      })).session;
    } catch (e) {
      alert(e.message);
      return;
    }
    vb.i = 0; vb.saved = 0;
    renderPrompt();
    show("vb-prompt");
  });

  function renderPrompt() {
    const p = vb.prompts[vb.i];
    $("#vb-count").textContent = `${vb.i + 1} / ${vb.prompts.length}`;
    $("#vb-bar").style.width = `${Math.round((100 * (vb.i + 1)) / vb.prompts.length)}%`;
    $("#vb-text").textContent = p.text;
    $("#vb-text").lang = p.lang;
    vb.take = null;
    $("#vb-play").disabled = true;
    $("#vb-ok").disabled = true;
    $("#vb-status").textContent = "";
  }

  // hold-to-record button (same behaviour as the app's)
  function recordButton() {
    const bar = document.createElement("span"); bar.className = "mic-bar";
    const meter = document.createElement("span"); meter.className = "mic-meter"; meter.append(bar);
    const label = document.createElement("span"); label.className = "mic-label"; label.textContent = "दबाकर रखें और पढ़ें / Hold and read";
    const btn = document.createElement("button"); btn.type = "button"; btn.className = "mic"; btn.append(label, meter);
    if (!Mic || !Mic.canListen) {
      btn.classList.add("off");
      label.textContent = "माइक के लिए https या localhost चाहिए / The mic needs https or localhost";
      return btn;
    }
    let starting = null;
    btn.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      if (starting) return;
      btn.setPointerCapture(e.pointerId);
      btn.classList.add("on");
      label.textContent = "रिकॉर्ड हो रहा है… / Recording…";
      starting = Mic.start(bar).catch((err) => { alert(err.message); throw err; });
    });
    const end = async () => {
      if (!starting) return;
      const pending = starting; starting = null;
      try { await pending; } catch { return; }
      const wav = Mic.stop(0.5);
      btn.classList.remove("on"); bar.style.transform = "scaleX(0)";
      label.textContent = "दबाकर रखें और पढ़ें / Hold and read";
      if (!wav) { $("#vb-status").textContent = "बहुत छोटा, फिर से / Too short, try again"; return; }
      vb.take = wav;
      if (vb.url) URL.revokeObjectURL(vb.url);
      vb.url = URL.createObjectURL(wav);
      $("#vb-play").disabled = false;
      $("#vb-ok").disabled = false;
      $("#vb-status").textContent = "सुनकर देखें, फिर आगे दबाएँ / Listen back, then press Next";
    };
    btn.addEventListener("pointerup", end);
    btn.addEventListener("pointercancel", end);
    btn.addEventListener("contextmenu", (e) => e.preventDefault());
    return btn;
  }
  $("#vb-mic").append(recordButton());

  $("#vb-play").addEventListener("click", () => { if (vb.url) new Audio(vb.url).play(); });
  $("#vb-ok").addEventListener("click", async () => {
    const p = vb.prompts[vb.i];
    $("#vb-ok").disabled = true;
    try {
      await api(`/api/voicebench/${vb.session}/${p.id}`, { method: "POST", headers: { "Content-Type": "audio/wav" }, body: vb.take });
      vb.saved += 1;
    } catch (e) {
      $("#vb-status").textContent = e.message;
      $("#vb-ok").disabled = false;
      return;
    }
    vb.i += 1;
    if (vb.i < vb.prompts.length) { renderPrompt(); return; }
    $("#vb-summary").textContent = `${vb.saved} रिकॉर्डिंग सेव हुईं (सत्र ${vb.session}) / ${vb.saved} recordings saved (session ${vb.session})`;
    show("vb-done");
  });

  $("#vb-again").addEventListener("click", () => { location.reload(); });
  $("#vb-withdraw").addEventListener("click", async () => {
    if (!vb.session || !confirm("सभी रिकॉर्डिंग मिटाएँ? / Delete all recordings from this session?")) return;
    await api(`/api/voicebench/${vb.session}`, { method: "DELETE" });
    $("#vb-summary").textContent = "मिटा दी गईं / Deleted";
  });
})();
