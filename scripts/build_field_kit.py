"""Build the printable field-morning kit (docs/field/Sahayak_Field_Morning_Kit.pdf): what to print for one morning
at a CSC with docs/field/FIELD_TEST_PROTOCOL.md.

- A run sheet: the day in order, the roles, and the message cards to use with the right answer for each (the
  jury kit's M cards, numbered the same way).
- The consent text in Hindi and English, in large print, to read aloud.
- One recording card per person (two to a page): every box matches a column of bench/field/*.csv, so typing the
  cards up afterwards is mechanical, and `python bench/eval_field.py --report` scores them.

Rendered by Chromium (Playwright) so Hindi is shaped correctly.
Usage: python scripts/build_field_kit.py [people]     (default 30 recording cards)
"""
from __future__ import annotations

import html
import importlib.util
import json
import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.packs import get_pack  # noqa: E402

E = html.escape
OUT = ROOT / "docs" / "field" / "Sahayak_Field_Morning_Kit.pdf"

CSS = """
@page { size: A4; margin: 11mm 12mm; }
body { font-family: "Segoe UI", "Nirmala UI", "Noto Sans", sans-serif; color: #1b1f1d; font-size: 10pt; line-height: 1.35; margin: 0; }
h1 { font-size: 18pt; color: #0e7c57; margin: 0 0 4px; } h2 { font-size: 12pt; color: #0e7c57; margin: 10px 0 4px; }
.page { page-break-after: always; } .page:last-child { page-break-after: auto; }
table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #c9c2b4; padding: 3px 5px; text-align: left; vertical-align: top; }
th { background: #f1ede4; font-size: 8.6pt; }
ol, ul { margin: 2px 0; padding-left: 18px; } li { margin: 1px 0; }
.consent { font-size: 12.5pt; line-height: 1.5; } .consent h1 { display: none; } .consent h2 { font-size: 14pt; }
.card { border: 1.5px solid #0e7c57; border-radius: 8px; padding: 7px 9px; height: 132mm; box-sizing: border-box; margin-bottom: 6mm; }
.card h3 { margin: 0 0 4px; font-size: 11pt; } .pid { float: right; font-weight: 700; }
.card td { height: 6.2mm; font-size: 8.4pt; } .opts { color: #4b524e; font-size: 8pt; }
.box { display: inline-block; width: 11mm; border-bottom: 1px solid #555; }
.small { font-size: 8.4pt; color: #4b524e; }
"""


def cards() -> list[dict]:
    """The jury kit's message cards (M1, M2, …) with the right answer for each."""
    spec = importlib.util.spec_from_file_location("jury_kit", ROOT / "scripts" / "build_jury_kit.py")
    jury = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jury)
    demo_ids = [ex["id"] for ex in get_pack("demo").data["examples"]]
    out = []
    for i, m in enumerate(jury.messages()):
        if i < len(demo_ids):
            truth = "genuine" if demo_ids[i].startswith("genuine") else "scam"
        else:
            truth = "genuine" if m["kind"] == "genuine" else "scam"
        out.append({"n": m["n"], "title": m["title"], "truth": truth})
    return out


def run_sheet(msg_cards: list[dict]) -> str:
    rows = "".join(f"<tr><td><b>{c['n']}</b></td><td>{E(c['title'])}</td><td><b>{c['truth']}</b></td></tr>" for c in msg_cards)
    return f"""<div class="page"><h1>Field morning: run sheet</h1>
<p class="small">Full protocol: docs/field/FIELD_TEST_PROTOCOL.md. No names, phone numbers or photos of people are written anywhere.</p>
<h2>Before people arrive</h2>
<ol><li>Node on, console PIN set, impact counters reset (console, Counters), firewall script run, node page shows 0 outbound connections.</li>
<li>Two of your own phones: open the app once from the node's HTTPS address or the stand-alone site, so task 4 works.</li>
<li>Pick 6 message cards from the jury kit: 4 scams of different kinds and 2 genuine (table below). Each person gets 3, shuffled, at least one genuine.</li>
<li>Number the recording cards P01, P02, … before you start.</li></ol>
<h2>Roles</h2>
<ul><li><b>Host</b> (the operator): welcomes people, runs the assisted checks on the console.</li>
<li><b>Facilitator</b>: reads the consent, gives the tasks, never helps unless asked (and then ticks "helped").</li>
<li><b>Recorder</b>: fills one recording card per person, times each task.</li></ul>
<h2>With each person (15–20 minutes)</h2>
<ol><li>Consent (next page), read aloud. Stop if they say no.</li>
<li>About them: tick the boxes on their card.</li>
<li>Task 1, three message cards: first their own judgement (real / fraud / unsure), then Sahayak, then "what will you do now?"</li>
<li>Task 2a, a phone call they describe. Task 2b, their own worrying message, only with the second consent.</li>
<li>Task 3, "What am I owed?": they answer the questions themselves.</li>
<li>Task 4, a few people: Wi-Fi and mobile data off on your phone, check one card.</li>
<li>Three questions, 1 (not at all) to 5 (completely).</li></ol>
<h2>Message cards and the right answers</h2>
<table><tr><th>Card</th><th>Message</th><th>Right answer</th></tr>{rows}</table>
<h2>After the day</h2>
<ol><li>Type the cards into bench/field/field_participants_v0.csv and field_tasks_v0.csv (one row per attempt; "truth" from the table above).</li>
<li>python bench/eval_field.py --report --place "CSC name, village" --date YYYY-MM-DD</li>
<li>Rebuild the deck (node docs/deck/build_deck_v3.js) and the testing report: the field results appear on their own.</li></ol></div>"""


def consent_page() -> str:
    body = markdown.markdown((ROOT / "docs" / "field" / "CONSENT.md").read_text(encoding="utf-8"))
    return f'<div class="page consent"><h2 style="font-size:16pt">Read aloud before anything else · पहले यह पढ़कर सुनाएँ</h2>{body}</div>'


def person_card(pid: str) -> str:
    line = "<span class='box'></span>"
    msg_rows = "".join(f"<tr><td>{label}</td><td>{line}</td><td class='opts'>real · fraud · unsure</td>"
                       f"<td class='opts'>scam · susp. · no signs</td><td class='opts'>Y · N</td><td>{line}</td><td class='opts'>Y · N</td></tr>"
                       for label in ("Card 1", "Card 2", "Card 3"))
    return f"""<div class="card"><h3>Sahayak field morning · recording card <span class="pid">{pid}</span></h3>
<table><tr><td class="opts"><b>Age</b> 18-34 · 35-54 · 55-69 · 70+</td><td class="opts"><b>Gender</b> f · m · other · not said</td>
<td class="opts"><b>Reads Hindi</b> yes · some · no</td><td class="opts"><b>Phone</b> smart · basic · none</td><td class="opts"><b>Lang</b> hi · en</td></tr></table>
<table style="margin-top:4px"><tr><th>Task</th><th>Card no.</th><th>On their own</th><th>Sahayak said</th><th>Right action?</th><th>Seconds</th><th>Helped?</th></tr>
{msg_rows}
<tr><td>2a Call</td><td>call</td><td class='opts'>truth: scam · genuine</td><td class='opts'>scam · susp. · no signs</td><td class='opts'>Y · N</td><td>{line}</td><td class='opts'>Y · N</td></tr>
<tr><td>2b Own msg</td><td class='opts'>consent Y · N</td><td></td><td class='opts'>scam · susp. · no signs</td><td class='opts'>Y · N</td><td>{line}</td><td class='opts'>Y · N</td></tr></table>
<table style="margin-top:4px"><tr><th>3 Benefits</th><th>Finished without help?</th><th>Seconds</th><th>Schemes shown</th><th>New to them</th><th>70+ without card: Vay Vandana shown?</th></tr>
<tr><td></td><td class='opts'>Y · N</td><td>{line}</td><td>{line}</td><td>{line}</td><td class='opts'>Y · N · not 70+ / has card</td></tr></table>
<table style="margin-top:4px"><tr><th>4 Off the node (your phone, Wi-Fi and data off)</th><th>Worked?</th><th>"I understood" 1-5</th><th>"I would trust it" 1-5</th><th>"I would use it again" 1-5</th></tr>
<tr><td class='opts'>card no. {line}</td><td class='opts'>Y · N · not tried</td><td></td><td></td><td></td></tr></table>
<p class="small" style="margin:5px 0 0">Notes (what went wrong or surprised you; no names or numbers):</p></div>"""


def build(people: int) -> str:
    persons = [person_card(f"P{i:02d}") for i in range(1, people + 1)]
    pages = "".join('<div class="page">' + "".join(persons[i:i + 2]) + "</div>" for i in range(0, len(persons), 2))
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
            f"{run_sheet(cards())}{consent_page()}{pages}</body></html>")


def main() -> None:
    people = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    tmp = OUT.with_suffix(".html")
    tmp.write_text(build(people), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(tmp.as_uri(), wait_until="load")
        page.pdf(path=str(OUT), format="A4", print_background=True)
        browser.close()
    tmp.unlink()
    print(f"wrote {OUT} ({people} recording cards)")


if __name__ == "__main__":
    main()
