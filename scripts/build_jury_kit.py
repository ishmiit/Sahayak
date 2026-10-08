"""Build the printable jury kit (docs/Sahayak_Jury_Kit.pdf): cards a juror can test Sahayak with.

- How to try it (join the stand's Wi-Fi, open the app, what to watch for).
- Message cards: the demo messages, three red-team messages written to fool the checker, and a
  genuine delivery OTP, printed like phone SMS so they can be typed, read out or photographed
  ("Screenshot" mode).
- UPI QR cards to photograph in "QR code" mode. Their UPI handle (@sahayakdemo) does not exist, so
  scanning one with a real UPI app fails: a printed demo code can never pay anyone.
- Benefits persona cards: answer the interview as that person.
- An answer key, computed by running the real checker and benefits engine when the kit is built.

Rendered by Chromium (Playwright) so Hindi is shaped correctly.
Usage: python scripts/build_jury_kit.py
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.fraud.pipeline import check_message_full  # noqa: E402
from sahayak.inputs.qr import analyse  # noqa: E402
from sahayak.navigator.engine import get_navigator  # noqa: E402
from sahayak.navigator.slip import qr_data_uri  # noqa: E402
from sahayak.packs import get_pack  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import docstyle as D  # noqa: E402  (Rosh 27 type and colours, as in the app)

E = html.escape
VERDICT = {"scam": "Scam", "suspicious": "Suspicious", "no_signs": "No signs found"}
RED_TEAM = ("rt-007", "rt-025", "rt-042")  # digits for letters; a warning wrapped around the ask; "6 number wala"
GENUINE = "rt-055"


def messages() -> list[dict]:
    demo = get_pack("demo").data["examples"]
    rows = {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "bench" / "redteam" / "redteam_v0.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    out = [{"title": ex["label"]["en"], "text": ex["text"], "sender": ex.get("sender"), "kind": "demo"} for ex in demo]
    for rid in RED_TEAM:
        r = rows[rid]
        out.append({"title": f"Try to fool it: {r['technique'].replace('_', ' ')}", "text": r["text"], "sender": r["sender"], "kind": "red team"})
    g = rows[GENUINE]
    out.append({"title": "A genuine message with an OTP", "text": g["text"], "sender": g["sender"], "kind": "genuine"})
    for i, m in enumerate(out, 1):
        m["n"] = f"M{i}"
        card, _ = check_message_full(m["text"], sender=m["sender"])
        m["verdict"], m["why"] = card["verdict"], card["headline"]["en"]
    return out


def qr_cards() -> list[dict]:
    out = []
    for i, ex in enumerate(get_pack("demo").data["qr_examples"], 1):
        info = analyse(ex["payload"])
        card, _ = check_message_full(info["check_text"], input_type="qr")
        out.append({"n": f"Q{i}", "title": ex["label"]["en"], "img": qr_data_uri(ex["payload"]), "verdict": card["verdict"],
                    "who": info.get("name") or info.get("payee"), "amount": info.get("amount_text"), "flags": info.get("flags", [])})
    return out


def personas() -> list[dict]:
    nav = get_navigator()
    pack = get_pack("schemes").data
    questions = {q["id"]: q for q in pack["questions"]}
    names = {s["id"]: (s.get("name") or {}).get("en", s["id"]) for s in pack["schemes"]}
    out = []
    for i, d in enumerate(pack["demos"], 1):
        lines = []
        for qid, value in d["answers"].items():
            q = questions[qid]
            opts = {o.get("id") or o.get("value"): o.get("label", {}).get("en", "") for o in q.get("options", [])}
            shown = (", ".join(opts.get(v, v) for v in value) or "None of these") if isinstance(value, list) else opts.get(value, str(value))
            lines.append((q.get("text", {}).get("en", qid), shown))
        res = nav.result(d["answers"])
        groups = {g: [names[s] for s in ids] for g, ids in res["groups"].items() if ids}
        out.append({"n": f"P{i}", "title": d["label"]["en"], "lines": lines, "groups": groups})
    return out


CSS = f"""
@page {{ size: A4; margin: 12mm; }}
{D.fonts_css(ROOT / "docs")}{D.BASE}
body {{ font-size: 10.5pt; line-height: 1.4; }}
h1 {{ display: flex; align-items: center; gap: 10px; font-size: 24pt; margin: 0 0 6px; letter-spacing: -.035em; }}
h2 {{ font-size: 15pt; margin: 0 0 10px; }}
.page {{ page-break-after: always; }} .page:last-child {{ page-break-after: auto; }}
.lead {{ font-size: 12pt; margin: 4px 0 14px; color: {D.LABEL2}; }}
ol {{ padding-left: 22px; }} ol li {{ margin: 8px 0; font-size: 12pt; }}
.box {{ border-radius: 16px; padding: 12px 16px; background: {D.PAGE}; margin: 10px 0; }}
.tryit {{ overflow: hidden; }} .tryit img {{ float: right; width: 30mm; height: 30mm; margin: 0 0 4px 12px; image-rendering: pixelated; }}
.grid {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 10px; }}
.card {{ border: 1.5px dashed {D.SEP_STRONG}; border-radius: 18px; padding: 11px 13px; break-inside: avoid; }}
.tag {{ display: inline-block; font: 600 9pt/1.5 {D.MONO}; color: #fff; background: {D.TINT}; border-radius: 999px; padding: 0 9px; margin-right: 6px; }}
.kind {{ font: 500 8pt/1 {D.MONO}; color: {D.LABEL2}; text-transform: uppercase; letter-spacing: .08em; }}
.phone {{ background: {D.PAGE}; border-radius: 16px; padding: 9px; margin-top: 7px; }}
.sender {{ font-weight: 600; font-size: 9.5pt; color: {D.LABEL2}; margin-bottom: 5px; }}
.bubble {{ background: #fff; border-radius: 14px; padding: 9px 11px; font-size: 11pt; line-height: 1.45; white-space: pre-wrap; overflow-wrap: anywhere; }}
.qr {{ text-align: center; }} .qr img {{ width: 62mm; height: 62mm; image-rendering: pixelated; }}
.warn {{ font-size: 9pt; color: {D.ALARM_INK}; }}
.box.warn {{ background: {D.ALARM_SOFT}; }}
table {{ border-collapse: collapse; width: 100%; }} th, td {{ text-align: left; vertical-align: top; padding: 4px 6px; border-bottom: 1px solid {D.SEP}; font-size: 9.5pt; }}
th {{ color: {D.LABEL2}; }}
.persona td:first-child {{ color: {D.LABEL2}; width: 55%; }}
"""


def build() -> str:
    msgs, qrs, people = messages(), qr_cards(), personas()
    url = json.loads((ROOT / "docs" / "deck" / "facts_v3.json").read_text(encoding="utf-8")).get("tryit_url")
    tryit = (f'<div class="box tryit"><img src="{qr_data_uri(url)}" alt="QR code for {E(url)}"><b>No laptop? Try it on your own '
             f'phone.</b> Scan this code or open <b>{E(url.replace("https://", ""))}</b>. Check a card, then switch on airplane mode '
             "and check another: it still works, because the scam check and the benefits interview run on the phone itself, from the "
             "same signed packs as the node. Voice input and screenshot reading need the node.</div>") if url else ""
    p1 = f"""<div class="page"><h1>{D.mark(ROOT / "docs", "1.1em")}Try Sahayak yourself</h1>
<div class="lead">Sahayak runs on the laptop at our stand. Its Wi-Fi has no internet. Nothing you type, say or photograph leaves it.</div>
<ol>
<li><b>Join the Wi-Fi</b> named on the node's sticker, then scan the sticker's QR code (or open any web address): the app opens. No install.</li>
<li><b>Check a message.</b> Tap "Check a message", then type a card's message, say it with the mic, or choose <i>Screenshot</i> and photograph the card.</li>
<li><b>Check a UPI QR.</b> Choose <i>QR code</i> and photograph a Q card. Sahayak shows who the money would go to and how much.</li>
<li><b>Find benefits.</b> Tap "What am I owed?" and answer as one of the P cards. Print the slip if a printer is attached.</li>
<li><b>Try to fool it.</b> Write your own message, in Hindi, English or Hinglish. Tell us what it got wrong; we log every miss.</li>
<li><b>Watch the node page</b> on the laptop: the count of connections Sahayak made to the internet stays at 0.</li>
</ol>
<div class="box"><b>What to look for.</b> A verdict in milliseconds with the reasons in Hindi and English; "No signs found" never says "safe";
every amount comes from a signed pack; the app always asks "I heard …, is that right?" before using a spoken answer.</div>
{tryit}
<div class="box warn"><b>About the QR cards:</b> they use the UPI handle @sahayakdemo, which does not exist. A real UPI app will refuse them,
so they can never pay anyone. Scan them only with Sahayak.</div>
<p>The answer key is on the last page. It was produced by running Sahayak itself on every card.</p></div>"""

    def mcard(m):
        sender = E(m["sender"] or "+91 98765 43210")
        return (f'<div class="card"><span class="tag">{m["n"]}</span><span class="kind">{E(m["kind"])}</span>'
                f'<div><b>{E(m["title"])}</b></div><div class="phone"><div class="sender">{sender}</div>'
                f'<div class="bubble">{E(m["text"])}</div></div></div>')
    p2 = '<div class="page"><h2>Message cards</h2><div class="grid">' + "".join(mcard(m) for m in msgs) + "</div></div>"
    p3 = ('<div class="page"><h2>UPI QR cards: photograph in Sahayak\'s "QR code" mode</h2><div class="grid">'
          + "".join(f'<div class="card qr"><span class="tag">{q["n"]}</span><b>{E(q["title"])}</b><br><img src="{q["img"]}">'
                    '<div class="warn">Demo code: a real UPI app will refuse it.</div></div>' for q in qrs)
          + "</div></div>")

    def pcard(p):
        rows = "".join(f"<tr><td>{E(q)}</td><td><b>{E(a)}</b></td></tr>" for q, a in p["lines"])
        return (f'<div class="card persona"><span class="tag">{p["n"]}</span><b>{E(p["title"])}</b>'
                f'<p style="margin:6px 0">Answer the interview as this person:</p><table>{rows}</table></div>')
    p4 = '<div class="page"><h2>Benefits persona cards</h2><div class="grid">' + "".join(pcard(p) for p in people) + "</div></div>"
    key_m = "".join(f"<tr><td>{m['n']}</td><td>{E(m['title'])}</td><td><b>{VERDICT[m['verdict']]}</b></td><td>{E(m['why'])}</td></tr>" for m in msgs)
    key_q = "".join(f"<tr><td>{q['n']}</td><td>{E(q['title'])}</td><td><b>{VERDICT[q['verdict']]}</b></td>"
                    f"<td>Pays {E(q['who'] or '?')}{' ' + E(q['amount']) if q['amount'] else ''}"
                    f"{'; ' + ', '.join(f.replace('_', ' ') for f in q['flags']) if q['flags'] else ''}</td></tr>" for q in qrs)
    label = {"eligible": "Can get", "likely": "Likely", "check": "Check at the office", "unlock": "After opening a bank account", "have": "Already has"}
    key_p = "".join(f"<tr><td>{p['n']}</td><td>{E(p['title'])}</td><td colspan='2'>"
                    + "; ".join(f"<b>{label.get(g, g)}:</b> {E(', '.join(v))}" for g, v in p["groups"].items() if g != "not_eligible")
                    + "</td></tr>" for p in people)
    p5 = (f'<div class="page"><h2>Answer key (Sahayak\'s own output, fraud pack {get_pack("fraud").version}, '
          f'schemes pack {get_pack("schemes").version})</h2><table><tr><th>Card</th><th>What it is</th><th>Verdict</th><th>Why</th></tr>'
          f"{key_m}{key_q}{key_p}</table></div>")
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{p1}{p2}{p3}{p4}{p5}</body></html>'


def main() -> None:
    out_html = ROOT / "docs" / "jury_kit.html"
    out_html.write_text(build(), encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(out_html.as_uri(), wait_until="load")
        pg.pdf(path=str(ROOT / "docs" / "Sahayak_Jury_Kit.pdf"), format="A4", print_background=True,
               margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"})
        b.close()
    print(f"wrote {ROOT / 'docs' / 'Sahayak_Jury_Kit.pdf'}")


if __name__ == "__main__":
    main()
