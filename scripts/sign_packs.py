"""Sign content packs with this machine's Ed25519 key.

Each team member who signs keeps a private key in %USERPROFILE%/.sahayak/keys/<name>.key (never commit
it; back it up privately). SAHAYAK_SIGNER picks the name (default: the team key, "sahayak-packs"). The
matching public key is packs/keys/<name>.pub; the node trusts every key in that folder. Re-run after
editing any pack.

Usage: python scripts/sign_packs.py [--only fraud,demo] [--new-key]
  --only     sign only these packs (by pack name), e.g. the ones you changed
  --new-key  make this signer's key when it is not on this machine. For a new name this adds a signer that
             every node with the new packs/keys/<name>.pub will trust; for an existing name it replaces that
             signer's key. Either way, only on purpose.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.config import get_settings  # noqa: E402
from sahayak.signing import load_or_create_private_key, public_pem, sign_file, signer_name  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default="", help="comma-separated pack names to sign (default: every pack)")
    ap.add_argument("--new-key", action="store_true")
    args = ap.parse_args()
    settings, name = get_settings(), signer_name()
    key_file = settings.home / "keys" / f"{name}.key"
    pub = settings.packs_dir / "keys" / f"{name}.pub"
    if not key_file.exists() and not args.new_key:
        # Without this, a teammate's machine would quietly make a new key and change which keys every node trusts.
        raise SystemExit(f"No signing key for '{name}' at {key_file}. Copy it there, set SAHAYAK_SIGNER to your own "
                         f"signer name, or run with --new-key to make one on purpose ({pub.name} "
                         f"{'would be replaced' if pub.exists() else 'would be added to the keys the node trusts'}).")
    key = load_or_create_private_key(key_file)
    pub.parent.mkdir(exist_ok=True)
    if not pub.exists() or pub.read_bytes() != public_pem(key):
        pub.write_bytes(public_pem(key))
        print(f"public key -> {pub}")
    only = {n.strip() for n in args.only.split(",") if n.strip()}
    for pack in sorted(settings.packs_dir.glob("*.v*.json")):
        if only and pack.name.split(".v")[0] not in only:
            continue
        sign_file(pack, key)
        print(f"signed {pack.name} as {name}")


if __name__ == "__main__":
    main()
