"""Build the stand-alone "try it" site (dist/tryit/): the phone app with no node behind it.

The scam check and the benefits interview run in the browser (web/checker.js, web/navigator.js) from the
same signed packs the node uses, so a juror or a citizen can open it from any HTTPS address, and after the
first visit it keeps working with the internet off (the service worker keeps everything). What needs the
node is left out or falls back: voice input and screenshot reading (both run on the node), the agent queue;
QR photos use the browser's own QR reader where there is one, and screens are read aloud by the phone's
own voice.

Every pack is checked against its signature before it is copied; the build refuses an altered pack.

Usage: python scripts/build_tryit.py [out_dir]     (default dist/tryit; host the folder on any HTTPS site)
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.packs import get_pack  # noqa: E402

WEB = ROOT / "web"
APP_FILES = ("styles.css", "app.js", "mic.js", "recorder.js", "checker.js", "navigator.js", "icons/icon.svg")
PACKS = ("fraud", "scam_patterns", "fraud_model", "schemes", "demo")  # the same list the node serves


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "tryit"
    if out.exists():
        shutil.rmtree(out)
    (out / "app" / "icons").mkdir(parents=True)
    (out / "phone-packs").mkdir()

    for f in APP_FILES:
        shutil.copy2(WEB / f, out / "app" / f)
    shutil.copy2(WEB / "sw.js", out / "sw.js")  # works from any folder: it caches relative to itself

    # The page: relative paths (the site may live in a sub-folder), and a marker that tells the app there is no
    # node behind it. A meta tag, not a script, so it is cached with the page and needs no inline code.
    html = (WEB / "index.html").read_text(encoding="utf-8").replace('"/app/', '"app/')
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="sahayak-standalone" content="1">', 1)
    (out / "index.html").write_text(html, encoding="utf-8")

    manifest = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
    # URLs in a manifest resolve against the manifest itself, which sits in app/
    manifest.update(start_url="../", scope="../")
    manifest["share_target"]["action"] = "../"
    manifest["icons"] = [dict(i, src=i["src"].replace("/app/", "")) for i in manifest["icons"]]
    (out / "app" / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    for name in PACKS:
        pack = get_pack(name)  # raises on a pack whose signature does not match
        if not pack.signed_by:
            raise SystemExit(f"{pack.path.name} is not signed; run scripts/sign_packs.py first")
        (out / "phone-packs" / f"{name}.json").write_text(json.dumps(
            {"name": pack.name, "version": pack.version, "date": pack.date, "sha256": pack.sha256,
             "signed_by": pack.signed_by, "data": pack.data}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    (out / ".nojekyll").write_text("", encoding="utf-8")  # GitHub Pages: serve files as they are
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"stand-alone site in {out} ({size / 1e6:.2f} MB); host it on HTTPS, e.g. GitHub Pages")


if __name__ == "__main__":
    main()
