"""Assemble the prototype submission folder (../Sahayak_Submission/) from the built documents.

Renders the Markdown documents (start-here, application-to-prototype, testing report) to PDF with
Chromium, copies the deck, one-pager, jury kit, video, clips and screenshots, packs a clean source zip
(no caches, test keys, models or videos), zips the documents and source together, and checks every
file against the challenge's 25 MB limit per file.

Run the document builders first (testing report, one-pager, deck, jury kit, video). Usage:
python scripts/build_submission.py
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import docstyle as D  # noqa: E402  (Rosh 27 type and colours, as in the app)
OUT = ROOT.parent / "Sahayak_Submission"
LIMIT = 25 * 1024 * 1024
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".sahayak-test", ".git", "node_modules", "console", "dist"}  # dist: built sites
SKIP_PATHS = {Path("docs/video"), Path("docs/screenshots")}  # shipped beside the zip

def css(html_dir: Path) -> str:
    return f"""
@page {{ size: A4; margin: 16mm 15mm; }}
{D.fonts_css(html_dir)}{D.BASE}
body {{ font-size: 9.5pt; line-height: 1.45; }}
h1 {{ font-size: 20pt; margin: 0 0 10px; letter-spacing: -.03em; }}
h2 {{ font-size: 13pt; margin: 20px 0 6px; padding-top: 10px; border-top: 1px solid {D.SEP}; }}
h3 {{ font-size: 11pt; margin: 14px 0 4px; letter-spacing: -.01em; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0 10px; }}
th, td {{ border-bottom: 1px solid {D.SEP}; padding: 5px 7px; text-align: left; vertical-align: top; font-size: 8.6pt; }}
th {{ background: {D.PAGE}; color: {D.LABEL2}; }}
code {{ font-family: {D.MONO}; background: {D.PAGE}; padding: 0 4px; border-radius: 5px; font-size: 8.6pt; }}
pre {{ font-family: {D.MONO}; background: {D.PAGE}; padding: 10px 12px; border-radius: 12px; font-size: 8.6pt; white-space: pre-wrap; }}
pre code {{ padding: 0; background: none; }}
blockquote {{ margin: 8px 0; padding: 8px 14px; border-radius: 12px; background: {D.TINT_SOFT}; }}
"""


def md_to_pdf(src: Path, dst: Path, page) -> None:
    body = markdown.markdown(src.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
    tmp = dst.with_suffix(".html")
    tmp.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>{css(tmp.parent)}</style></head><body>{body}</body></html>',
                   encoding="utf-8")
    page.goto(tmp.as_uri(), wait_until="load")
    page.pdf(path=str(dst), format="A4", print_background=True,
             margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
    tmp.unlink()


def source_zip(dst: Path) -> int:
    n = 0
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(ROOT.rglob("*")):
            rel = path.relative_to(ROOT)
            if path.is_dir() or SKIP_DIRS & set(rel.parts) or any(rel.is_relative_to(p) for p in SKIP_PATHS):
                continue
            if path.suffix in (".pyc", ".key", ".log") or path.name.endswith("_corpus.json"):  # corpora: rebuilt by the tests
                continue
            z.write(path, Path("sahayak") / rel)
            n += 1
    return n


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "screenshots").mkdir(parents=True)
    (OUT / "clips").mkdir()
    docs = ROOT / "docs"
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        md_to_pdf(docs / "SUBMISSION_README.md", OUT / "00_START_HERE.pdf", page)
        md_to_pdf(docs / "APPLICATION_TO_PROTOTYPE.md", OUT / "04_Application_to_Prototype.pdf", page)
        md_to_pdf(docs / "TESTING_REPORT.md", OUT / "05_Sahayak_Testing_Report.pdf", page)
        b.close()
    (docs / "submission").mkdir(exist_ok=True)  # the same PDFs, kept in the repo
    for name in ("00_START_HERE.pdf", "04_Application_to_Prototype.pdf", "05_Sahayak_Testing_Report.pdf"):
        shutil.copy2(OUT / name, docs / "submission" / name)
    # the newest deck that has both its slides and its PDF (v3 for the finale, else v2)
    deck = next(v for v in ("v3", "v2") if (docs / "deck" / f"Sahayak_Pitch_Deck_{v}.pdf").exists()
                and (docs / "deck" / f"Sahayak_Pitch_Deck_{v}.pptx").exists())
    copies = {
        docs / "video" / "Sahayak_demo_draft.mp4": "01_Sahayak_Demo_Video.mp4",
        docs / "deck" / f"Sahayak_Pitch_Deck_{deck}.pdf": "02_Sahayak_Pitch_Deck.pdf",
        docs / "deck" / f"Sahayak_Pitch_Deck_{deck}.pptx": "02_Sahayak_Pitch_Deck.pptx",
        docs / "Sahayak_OnePager.pdf": "03_Sahayak_OnePager.pdf",
        docs / "Sahayak_Jury_Kit.pdf": "06_Sahayak_Jury_Kit.pdf",
    }
    for src, name in copies.items():
        shutil.copy2(src, OUT / name)
    for f in sorted((docs / "screenshots").glob("*.png")):
        shutil.copy2(f, OUT / "screenshots" / f.name)
    for f in sorted((docs / "video").glob("[0-9]_*.mp4")):
        shutil.copy2(f, OUT / "clips" / f.name)
    files = source_zip(OUT / "07_Sahayak_Source_Code.zip")
    print(f"source zip: {files} files")
    # one bundle with the documents and the source (the video and media stay separate files)
    with zipfile.ZipFile(OUT / "Sahayak_Prototype_Submission.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.glob("0*")):
            if f.suffix != ".mp4":
                z.write(f, f.name)
    too_big = []
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            size = f.stat().st_size
            if f.parent == OUT:
                print(f"{size / 1024 / 1024:6.1f} MB  {f.name}")
            if size > LIMIT:
                too_big.append(f.name)
    print("all files under 25 MB" if not too_big else f"OVER 25 MB: {too_big}")
    print(f"wrote {OUT}")
    return 1 if too_big else 0


if __name__ == "__main__":
    raise SystemExit(main())
