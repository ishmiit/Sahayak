"""Cut Material Symbols Rounded down to the icons the web app uses: web/fonts/symbols.woff2 (+ symbols.txt).

The app writes an icon's name as text (<span class="ms">call</span>, icon("call") in JS, content: "call" in CSS) and
the font's ligatures draw it. The full font is over 5 MB; this keeps only the listed icons with their ligatures, the
FILL axis and weights 300-700, and pins grade 0 and optical size 24: about 50 KB, served by the node and kept by
the phone's service worker, so icons work with no internet at all.

symbols.txt lists what the font holds; tests/test_web_icons.py fails when the app uses an icon that is not in it.

Usage (needs fonttools and brotli, which the node itself does not):
  python scripts/build_icon_font.py "MaterialSymbolsRounded[FILL,GRAD,opsz,wght].woff2"
  python scripts/build_icon_font.py --used      print the icons web/ uses and the ones missing from ICONS
Source font: https://github.com/google/material-design-icons/tree/master/variablefont (Apache License 2.0).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
OUT = WEB / "fonts" / "symbols.woff2"
LIST = WEB / "fonts" / "symbols.txt"

ICONS = sorted(set("""
account_balance arrow_back arrow_forward badge bar_chart block call campaign cancel check check_box_outline_blank
check_circle chevron_right confirmation_number contrast currency_rupee delete description dns done_all download
error expand_more fact_check forum gpp_bad graphic_eq health_and_safety hearing help inbox info inventory_2
list_alt lock lock_open logout memory menu_book mic open_in_new person phone_in_talk photo_camera print
qr_code_2 qr_code_scanner receipt_long record_voice_over refresh restart_alt screenshot_monitor shield sms
support_agent task_alt undo verified verified_user volume_off volume_up warning
content_paste install_mobile person_off share wifi_off
""".split()))


def used_icons() -> set[str]:
    """Every icon name the web app writes, found in its HTML, JS and CSS."""
    name = r"([a-z][a-z0-9_]*)"
    found: set[str] = set()
    for path in sorted(WEB.glob("*.html")) + sorted(WEB.glob("*.js")):
        text = path.read_text(encoding="utf-8")
        found |= set(re.findall(r'<span class="ms[^"]*"[^>]*>' + name + r"</span>", text))
        if path.suffix == ".js":
            for args in re.findall(r"\bicon\(([^()]*(?:\([^()]*\)[^()]*)*)\)", text):
                first = args.split(", ")[0]
                found |= set(re.findall(r'"' + name + r'"', first))
            for body in re.findall(r"const (?:ICONS|TRUTH_ICON|VERDICT_ICON) = \{([^}]*)\}", text):
                found |= set(re.findall(r':\s*"' + name + r'"', body))
    for path in sorted(WEB.glob("*.css")):
        found |= set(re.findall(r'content:\s*"' + name + r'"', path.read_text(encoding="utf-8")))
    return found


def build(src: str) -> None:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    font = TTFont(src)
    rev = {g: chr(u) for u, g in font.getBestCmap().items()}
    ligatures = {}  # icon name -> glyph
    for lookup in font["GSUB"].table.LookupList.Lookup:
        for st in lookup.SubTable:
            st = getattr(st, "ExtSubTable", st)
            for first, ligs in getattr(st, "ligatures", {}).items():
                for lig in ligs:
                    ligatures[rev.get(first, "") + "".join(rev.get(c, "") for c in lig.Component)] = lig.LigGlyph
    missing = [n for n in ICONS if n not in ligatures]
    if missing:
        raise SystemExit(f"not in {src}: {missing}")
    order = set(font.getGlyphOrder())
    glyphs = {ligatures[n] for n in ICONS} | {ligatures[n] + ".fill" for n in ICONS if ligatures[n] + ".fill" in order}

    opts = subset.Options()
    opts.layout_closure = False  # keep only the ligature rules for these icons
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    sub = subset.Subsetter(options=opts)
    sub.populate(glyphs=sorted(glyphs), text="".join(sorted({c for n in ICONS for c in n})))
    sub.subset(font)
    font = instancer.instantiateVariableFont(font, {"GRAD": 0, "opsz": 24, "wght": (300, 700)})
    font.flavor = "woff2"
    font.save(OUT)
    LIST.write_text("# Icons in symbols.woff2, written by scripts/build_icon_font.py\n" + "\n".join(ICONS) + "\n",
                    encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(ICONS)} icons, {OUT.stat().st_size / 1024:.1f} KB")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--used":
        used = used_icons()
        print("used by web/:", " ".join(sorted(used)))
        print("missing from ICONS:", " ".join(sorted(used - set(ICONS))) or "none")
        print("listed but unused:", " ".join(sorted(set(ICONS) - used)) or "none")
        return
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    unlisted = used_icons() - set(ICONS)
    if unlisted:
        raise SystemExit(f"web/ uses icons that are not in ICONS: {sorted(unlisted)}")
    build(sys.argv[1])


if __name__ == "__main__":
    main()
