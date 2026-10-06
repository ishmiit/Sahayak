"""Content packs: versioned JSON files holding everything that changes without a code change.

Each pack carries `pack`, `version` and `date`. The loader records a SHA-256 of the exact
bytes so the node's status screen (and the README) can show what is installed, and checks the
pack's Ed25519 signature (`<file>.sig`) against the team's public keys in packs/keys/. An
altered pack is refused outright; an unsigned one is refused when SAHAYAK_REQUIRE_SIGNED=1.

  python -m sahayak.packs install <file.json>   verify, then swap in atomically (old copy kept)
  python -m sahayak.packs rollback <file name>  put the previous copy back
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import get_settings
from .signing import PackSignatureError, sig_path, verify


@dataclass(frozen=True)
class Pack:
    name: str
    version: str
    date: str
    sha256: str
    path: Path
    data: dict[str, Any]
    signed_by: str | None = None


def keys_dir() -> Path:
    return get_settings().packs_dir / "keys"


def require_signed() -> bool:
    return os.environ.get("SAHAYAK_REQUIRE_SIGNED", "0") == "1"


def load_pack_file(path: Path) -> Pack:
    raw = path.read_bytes()
    signer = verify(path, raw, keys_dir())  # raises on an altered pack
    if signer is None and require_signed():
        raise PackSignatureError(f"{path.name}: unsigned, and this node only accepts signed packs")
    data = json.loads(raw.decode("utf-8"))
    for key in ("pack", "version", "date"):
        if key not in data:
            raise ValueError(f"{path.name}: missing '{key}'")
    return Pack(
        name=data["pack"],
        version=data["version"],
        date=data["date"],
        sha256=hashlib.sha256(raw).hexdigest(),
        path=path,
        data=data,
        signed_by=signer,
    )


@lru_cache(maxsize=None)
def get_pack(name: str) -> Pack:
    """Load the newest file for a pack name, e.g. 'fraud' -> packs/fraud.v1.json."""
    packs_dir = get_settings().packs_dir
    candidates = sorted(packs_dir.glob(f"{name}.v*.json"), key=_version_key)
    if not candidates:
        raise FileNotFoundError(f"No pack named '{name}' in {packs_dir}")
    return load_pack_file(candidates[-1])


def installed_packs() -> list[dict[str, Any]]:
    packs_dir = get_settings().packs_dir
    names = sorted({p.name.split(".v")[0] for p in packs_dir.glob("*.v*.json")})
    out = []
    for name in names:
        pack = get_pack(name)
        out.append({"name": pack.name, "version": pack.version, "date": pack.date, "sha256": pack.sha256,
                    "file": pack.path.name, "signed_by": pack.signed_by})
    return out


def _version_key(path: Path) -> tuple[int, ...]:
    # "fraud.v1.2.json" -> (1, 2)
    tail = path.name.split(".v", 1)[1].rsplit(".json", 1)[0]
    return tuple(int(p) for p in tail.split(".") if p.isdigit())


# ---------------------------------------------------------------- install and roll back

def install(src: Path) -> Path:
    """Verify `src` (and its .sig) and swap it into the packs folder; the copy it replaces is
    kept in packs/.previous/ for a one-step rollback. The node picks it up on restart."""
    load_pack_file(src)  # signature and format checks before anything is touched
    dest = get_settings().packs_dir / src.name
    previous = dest.parent / ".previous"
    previous.mkdir(exist_ok=True)
    for f in (dest, sig_path(dest)):
        if f.exists():
            shutil.copy2(f, previous / f.name)
    for s, d in ((src, dest), (sig_path(src), sig_path(dest))):
        if s.exists():
            tmp = d.with_name(d.name + ".tmp")
            shutil.copy2(s, tmp)
            os.replace(tmp, d)  # atomic on one filesystem
        elif d.exists() and d.suffix == ".sig":
            d.unlink()  # an unsigned replacement must not keep the old signature
    return dest


def rollback(file_name: str) -> Path:
    packs_dir = get_settings().packs_dir
    previous = packs_dir / ".previous" / file_name
    if not previous.exists():
        raise FileNotFoundError(f"no previous copy of {file_name}")
    dest = packs_dir / file_name
    for s, d in ((previous, dest), (sig_path(previous), sig_path(dest))):
        if s.exists():
            os.replace(s, d)
    load_pack_file(dest)
    return dest


def _main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("install", "rollback"):
        print(__doc__)
        return 2
    try:
        path = install(Path(argv[1])) if argv[0] == "install" else rollback(argv[1])
    except (PackSignatureError, ValueError, FileNotFoundError) as e:
        print(f"refused: {e}")
        return 1
    pack = load_pack_file(path)
    print(f"{argv[0]}ed {pack.name} v{pack.version} ({pack.date}), signed by {pack.signed_by or 'nobody'}; "
          "restart the node to use it")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
