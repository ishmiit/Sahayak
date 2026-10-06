"""Sign every content pack with the team's Ed25519 key.

The private key is kept in %USERPROFILE%/.sahayak/keys/sahayak-packs.key (created on first
run; share it with teammates out of band, never commit it). The matching public key is written
to packs/keys/sahayak-packs.pub, which the node trusts. Re-run after editing any pack.

Usage: python scripts/sign_packs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.config import get_settings  # noqa: E402
from sahayak.signing import KEY_NAME, load_or_create_private_key, public_pem, sign_file  # noqa: E402


def main() -> None:
    settings = get_settings()
    key = load_or_create_private_key(settings.home / "keys" / f"{KEY_NAME}.key")
    pub = settings.packs_dir / "keys" / f"{KEY_NAME}.pub"
    pub.parent.mkdir(exist_ok=True)
    if not pub.exists() or pub.read_bytes() != public_pem(key):
        pub.write_bytes(public_pem(key))
        print(f"public key -> {pub}")
    for pack in sorted(settings.packs_dir.glob("*.v*.json")):
        sign_file(pack, key)
        print(f"signed {pack.name}")


if __name__ == "__main__":
    main()
