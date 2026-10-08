"""Small helpers for editing content packs without losing their compact layout.

    from scripts.packtool import load, save
    pack = load("packs/fraud.v1.json"); ...; save("packs/fraud.v1.json", pack)

Lists of plain values stay on one line; objects are indented. Used by the team to
apply reviewed lexicon changes in bulk.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(value: Any, indent: int) -> str:
    pad, inner = "  " * indent, "  " * (indent + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{inner}{json.dumps(k, ensure_ascii=False)}: {_dump(v, indent + 1)}" for k, v in value.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(value, list) and all(not isinstance(v, (dict, list)) for v in value):
        return "[" + ", ".join(json.dumps(v, ensure_ascii=False) for v in value) + "]"
    if isinstance(value, list):
        return "[\n" + ",\n".join(inner + _dump(v, indent + 1) for v in value) + "\n" + pad + "]"
    return json.dumps(value, ensure_ascii=False)


def save(path: str | Path, pack: dict[str, Any]) -> None:
    """Write the pack and, when this machine's signing key (SAHAYAK_SIGNER, default the team key) is here,
    re-sign it: the node refuses a pack whose bytes no longer match its signature."""
    path = Path(path)
    path.write_text(_dump(pack, 0) + "\n", encoding="utf-8")
    from sahayak.config import get_settings
    from sahayak.signing import load_or_create_private_key, sig_path, sign_file, signer_name
    key_file = get_settings().home / "keys" / f"{signer_name()}.key"
    if key_file.exists():
        sign_file(path, load_or_create_private_key(key_file))
    elif sig_path(path).exists():
        sig_path(path).unlink()  # a stale signature would make the node refuse the pack
        print(f"note: {path.name} is now unsigned (no signing key here); run scripts/sign_packs.py")


def add(pack: dict[str, Any], lexicon: str, *phrases: str) -> None:
    lst = pack["lexicons"][lexicon]
    for p in phrases:
        if p not in lst:
            lst.append(p)


def remove(pack: dict[str, Any], lexicon: str, *phrases: str) -> None:
    pack["lexicons"][lexicon] = [p for p in pack["lexicons"][lexicon] if p not in phrases]
