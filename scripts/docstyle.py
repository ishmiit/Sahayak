"""Rosh 27 on paper: the type and tokens of the app (web/styles.css), in its light appearance, for the documents that
Chromium renders to PDF (one-pager, jury kit, field kit, submission documents). The fonts load from web/fonts, so the
PDFs set the same Geist as the app; Devanagari comes from the system's font, as it does in the app."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "web" / "fonts"

# label.primary / .secondary (66%) / .tertiary (46%), blended onto white paper
LABEL, LABEL2, LABEL3 = "#0B0B0C", "#5E5E5F", "#8F8F90"
PAGE, SEP, SEP_STRONG = "#F4F3F0", "#E2E1DD", "#C9C8C4"
TINT, TINT_INK, TINT_SOFT = "#1F5FD6", "#0056AA", "#E6EDFA"
ALARM, ALARM_INK, ALARM_SOFT = "#C8102E", "#A60035", "#FAE9EC"
GO, GO_INK, GO_SOFT = "#1B7A45", "#006B27", "#E6F5EC"
CAUTION_INK, CAUTION_SOFT = "#774F00", "#FAF2DB"
FONT = '"Geist", "Noto Sans Devanagari", "Kohinoor Devanagari", "Nirmala UI", "Segoe UI", sans-serif'
MONO = '"Geist Mono", "SF Mono", Menlo, Consolas, monospace'

_FACES = (
    ("Geist", "geist-latin.woff2", "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, "
     "U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"),
    ("Geist", "geist-latin-ext.woff2", "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+1D00-1DBF, "
     "U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF"),
    ("Geist Mono", "geist-mono-latin.woff2", "U+0000-00FF, U+2000-206F"),
)


def rel(target: Path, html_dir: Path) -> str:
    """A URL for `target` relative to the HTML file's folder, so a saved page carries no machine paths."""
    return Path(os.path.relpath(target, html_dir)).as_posix()


def fonts_css(html_dir: Path) -> str:
    return "".join(f'@font-face {{ font-family: "{family}"; font-weight: 100 900; src: url("{rel(FONTS / name, html_dir)}") '
                   f'format("woff2"); unicode-range: {urange}; }}\n' for family, name, urange in _FACES)


def mark(html_dir: Path, size: str = "1em") -> str:
    """Sahayak's app icon, inline with a heading."""
    return (f'<img class="mark" src="{rel(ROOT / "web" / "icons" / "icon.svg", html_dir)}" alt="" '
            f'style="width:{size};height:{size};vertical-align:-.14em;border-radius:22%">')


BASE = f"""
body {{ font-family: {FONT}; color: {LABEL}; margin: 0; letter-spacing: -.003em; -webkit-font-smoothing: antialiased;
  font-synthesis-weight: none; }}
h1, h2, h3 {{ font-weight: 700; letter-spacing: -.02em; }}
b, strong, th {{ font-weight: 650; }}
a {{ color: {TINT_INK}; }}
"""
