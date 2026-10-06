"""Ed25519 signatures for content packs.

A pack update arrives by USB stick or the operator's next connection, so the node must be able
to tell a genuine pack from an altered one on its own. Each pack file `x.v1.json` may carry
`x.v1.json.sig`: the base64 Ed25519 signature of the file's exact bytes. The node trusts the
public keys in packs/keys/*.pub; the private key lives only with the team
(%USERPROFILE%/.sahayak/keys), never in the repository.

  python scripts/sign_packs.py          sign every pack (creates the key pair the first time)
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

KEY_NAME = "sahayak-packs"


class PackSignatureError(ValueError):
    """A pack whose signature does not match its bytes, or no signature where one is required."""


def sig_path(pack_path: Path) -> Path:
    return pack_path.with_name(pack_path.name + ".sig")


@lru_cache(maxsize=4)
def trusted_keys(keys_dir: Path) -> tuple[tuple[str, Ed25519PublicKey], ...]:
    keys = []
    for f in sorted(keys_dir.glob("*.pub")):
        key = serialization.load_pem_public_key(f.read_bytes())
        if isinstance(key, Ed25519PublicKey):
            keys.append((f.stem, key))
    return tuple(keys)


def verify(pack_path: Path, data: bytes, keys_dir: Path) -> str | None:
    """Name of the key that signed `data`, None if the pack has no signature file.
    Raises PackSignatureError if a signature exists but no trusted key accepts it."""
    sp = sig_path(pack_path)
    if not sp.exists():
        return None
    try:
        signature = base64.b64decode(sp.read_text(encoding="ascii").strip(), validate=True)
    except (ValueError, UnicodeDecodeError) as e:
        raise PackSignatureError(f"{sp.name}: unreadable signature ({e})") from None
    for name, key in trusted_keys(keys_dir):
        try:
            key.verify(signature, data)
            return name
        except InvalidSignature:
            continue
    raise PackSignatureError(f"{pack_path.name}: signature does not match the file (altered, or signed by an unknown key)")


def load_or_create_private_key(path: Path) -> Ed25519PrivateKey:
    if path.exists():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError(f"{path} is not an Ed25519 key")
        return key
    key = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    return key


def public_pem(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def sign_file(pack_path: Path, key: Ed25519PrivateKey) -> Path:
    sp = sig_path(pack_path)
    sp.write_text(base64.b64encode(key.sign(pack_path.read_bytes())).decode("ascii") + "\n", encoding="ascii")
    return sp
