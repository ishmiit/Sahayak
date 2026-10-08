"""The phone app's shell: every icon it draws is in its icon font, and everything the offline copy needs exists,
is served by the node, and goes into the stand-alone build."""
import importlib.util
import re
from pathlib import Path

from fastapi.testclient import TestClient

from sahayak.server import app

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
client = TestClient(app)


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _shell():
    sw = (WEB / "sw.js").read_text(encoding="utf-8")
    block = re.search(r"const SHELL = \[(.*?)\]", sw, re.S).group(1)
    return re.findall(r'"([^"]*)"', block)


def test_every_icon_the_app_uses_is_in_the_icon_font():
    icons = _script("build_icon_font")
    in_font = {line.strip() for line in (WEB / "fonts" / "symbols.txt").read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.startswith("#")}
    used = icons.used_icons()
    assert {"gpp_bad", "warning", "verified_user", "mic", "call"} <= used  # the scanner sees all three kinds of use
    assert used - in_font == set(), "rebuild web/fonts/symbols.woff2 with scripts/build_icon_font.py"
    assert in_font == set(icons.ICONS)


def test_the_offline_shell_exists_and_is_served_by_the_node():
    for entry in _shell():
        if entry.startswith("app/"):
            assert (WEB / entry[len("app/"):]).is_file(), entry
            r = client.get("/" + entry)
            assert r.status_code == 200, entry
    font = client.get("/app/fonts/symbols.woff2")
    assert font.headers["content-type"] == "font/woff2"


def test_the_stand_alone_build_carries_the_whole_shell():
    app_files = set(_script("build_tryit").APP_FILES)
    for entry in _shell():
        if entry.startswith("app/") and entry != "app/manifest.webmanifest":  # the manifest is rewritten, not copied
            assert entry[len("app/"):] in app_files, entry


def test_pages_load_nothing_from_outside_the_node():
    for page in ("index.html", "console.html", "node.html", "voicebench.html"):
        html = (WEB / page).read_text(encoding="utf-8")
        assert not re.search(r'(?:src|href)="(?:https?:)?//', html), page
    css = "".join((WEB / f).read_text(encoding="utf-8") for f in ("styles.css", "console.css"))
    assert not re.search(r"url\((?!fonts/)", css)
