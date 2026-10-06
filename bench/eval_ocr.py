"""OCR bench: does reading a screenshot give the same verdict as the typed message?

Renders every ScamBench test message as a phone SMS screenshot in Chromium (sender line, message
bubble, the system's Devanagari/Latin font, proper Hindi text shaping), reads it back with the
node's offline OCR, and reports:
  character error rate of the read text against the original, and
  verdict agreement: the check on the read text gives the same verdict as on the original.

These are synthetic renders, so they are cleaner than real phone screenshots (no status bar
clutter, emoji, compression or photos of screens); real screenshots are a team task.

Usage: python bench/eval_ocr.py [--report] [--save-images]
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import re
import statistics
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from sahayak.fraud import check_message  # noqa: E402
from sahayak.inputs.ocr import get_reader  # noqa: E402

FONT = "C:/Windows/Fonts/Nirmala.ttc"
RESULTS = ROOT / "bench" / "results"


def render(text: str, sender: str | None) -> bytes:
    """A 720 px wide SMS screenshot: sender at the top, the message in a grey bubble."""
    font = ImageFont.truetype(FONT, 30)
    small = ImageFont.truetype(FONT, 26)
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, width=34) or [""]
    line_h = 44
    h = 170 + line_h * len(lines) + 60
    img = Image.new("RGB", (720, h), "#ffffff")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 720, 110], fill="#f1f3f4")
    d.text((40, 36), sender or "+91 98765 43210", font=small, fill="#202124")
    d.rounded_rectangle([30, 140, 690, 150 + line_h * len(lines) + 30], radius=28, fill="#e8eaed")
    for i, line in enumerate(lines):
        d.text((60, 160 + i * line_h), line, font=font, fill="#202124")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


_PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
body {{ margin: 0; width: 720px; background: #fff; font-family: "Nirmala UI", "Segoe UI", sans-serif; color: #202124; }}
.top {{ background: #f1f3f4; padding: 34px 40px; font-size: 26px; }}
.bubble {{ margin: 30px; padding: 22px 30px; background: #e8eaed; border-radius: 28px; font-size: 30px; line-height: 1.45;
          white-space: pre-wrap; overflow-wrap: anywhere; }}
</style></head><body><div class="top">{sender}</div><div class="bubble">{text}</div></body></html>"""


class HtmlRenderer:
    """Phone-like SMS screenshots drawn by Chromium, which shapes Devanagari correctly (Pillow
    without libraqm draws the short-i vowel sign after its consonant, as no phone does)."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._page = self._browser.new_page(viewport={"width": 720, "height": 400})
        return self

    def __call__(self, text: str, sender: str | None) -> bytes:
        import html
        self._page.set_content(_PAGE.format(sender=html.escape(sender or "+91 98765 43210"), text=html.escape(text)))
        return self._page.screenshot(full_page=True)

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()


def cer(ref: str, hyp: str) -> float:
    ref, hyp = re.sub(r"\s+", " ", ref).strip(), re.sub(r"\s+", " ", hyp).strip()
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, c in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != c))
    return d[len(hyp)] / max(1, len(ref))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--save-images", action="store_true")
    args = ap.parse_args()
    rows = [json.loads(line) for line in (ROOT / "bench" / "scambench" / "scambench_v0.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    rows = [r for r in rows if r["split"] == "test" and r.get("input_type", "text") != "call"]  # a screenshot is of a message, not a call
    reader = get_reader()
    out, times = [], []
    img_dir = RESULTS / "ocr_images"
    if args.save_images:
        img_dir.mkdir(parents=True, exist_ok=True)
    renderer = HtmlRenderer().__enter__()
    for i, r in enumerate(rows, 1):
        png = renderer(r["text"], r.get("sender"))
        if args.save_images and i <= 6:
            (img_dir / f"{r['id']}.png").write_bytes(png)
        t0 = time.perf_counter()
        read = reader.read(png)["text"]
        times.append(time.perf_counter() - t0)
        typed = check_message(r["text"], sender=r.get("sender"), input_type=r.get("input_type", "text"))["verdict"]
        seen = check_message(read, sender=r.get("sender"), input_type="ocr")["verdict"]
        flag = lambda v: v in ("scam", "suspicious")  # noqa: E731
        reference = f"{r.get('sender') or '+91 98765 43210'} {r['text']}"  # the screenshot shows the sender too
        out.append({"id": r["id"], "lang": r["lang"], "cer": cer(reference, read), "typed": typed, "read": seen,
                    "same_flag": flag(typed) == flag(seen), "same": typed == seen, "text": r["text"], "ocr": read})
        if i % 10 == 0:
            print(f"  {i}/{len(rows)}", flush=True)
    renderer.__exit__(None, None, None)
    by_lang = {}
    for lang in sorted({o["lang"] for o in out}):
        xs = [o for o in out if o["lang"] == lang]
        by_lang[lang] = {"n": len(xs), "cer": round(statistics.mean(o["cer"] for o in xs), 4),
                         "same_flag": sum(o["same_flag"] for o in xs)}
    summary = {
        "date": dt.date.today().isoformat(), "messages": len(out),
        "cer_mean": round(statistics.mean(o["cer"] for o in out), 4),
        "cer_median": round(statistics.median(o["cer"] for o in out), 4),
        "same_flag": sum(o["same_flag"] for o in out), "same_verdict": sum(o["same"] for o in out),
        "by_lang": by_lang, "seconds_p50": round(statistics.median(times), 2),
        "disagreements": [{k: o[k] for k in ("id", "typed", "read", "text", "ocr")} for o in out if not o["same_flag"]],
    }
    print(f"{len(out)} screenshots: mean character error {100 * summary['cer_mean']:.1f}% (median {100 * summary['cer_median']:.1f}%); "
          f"same scam/not-scam decision on {summary['same_flag']}/{len(out)}, identical verdict on {summary['same_verdict']}/{len(out)}; "
          f"{summary['seconds_p50']} s per screenshot")
    for lang, v in by_lang.items():
        print(f"  {lang}: n={v['n']} CER {100 * v['cer']:.1f}%, same decision {v['same_flag']}/{v['n']}")
    if args.report:
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "ocrbench_v0.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
        md = ["# Screenshot reading: OCR bench v0", "",
              f"Run {summary['date']}: the {len(out)} ScamBench test messages rendered as phone SMS screenshots and read back with "
              "the node's offline OCR (EasyOCR, Devanagari and Latin models, CPU), screenshots drawn by Chromium. Reproduce with `python bench/eval_ocr.py --report`.",
              "", "| Measure | Result |", "| --- | --- |",
              f"| Same scam / not-scam decision as the typed message | {summary['same_flag']} / {len(out)} |",
              f"| Identical verdict (Scam, Suspicious, No signs) | {summary['same_verdict']} / {len(out)} |",
              f"| Character error rate, mean (median) | {100 * summary['cer_mean']:.1f}% ({100 * summary['cer_median']:.1f}%) |",
              f"| Time per screenshot (median, laptop CPU) | {summary['seconds_p50']} s |", "",
              "| Language | Messages | Character error | Same decision |", "| --- | --- | --- | --- |"]
        md += [f"| {lang} | {v['n']} | {100 * v['cer']:.1f}% | {v['same_flag']}/{v['n']} |" for lang, v in by_lang.items()]
        md += ["", "Where the decision differed:", ""]
        md += [f"- {d['id']}: typed {d['typed']}, read {d['read']}. Read as: \"{d['ocr'][:160]}\"" for d in summary["disagreements"]] or ["- none"]
        md += ["", "The renders are clean, synthetic screenshots; real phone screenshots (status bars, emoji, photos of a screen) "
               "will read worse. The app always shows the read text for the person to correct before it is checked.", ""]
        (RESULTS / "ocrbench_v0.md").write_text("\n".join(md), encoding="utf-8")
        print(f"wrote {RESULTS / 'ocrbench_v0.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
