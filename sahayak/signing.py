"""Ed25519 signatures for content packs.

A pack update arrives by USB stick or the operator's next connection, so the node must be able
to tell a genuine pack from an altered one on its own. Each pack file `x.v1.json` may carry
`x.v1.json.sig`: the base64 Ed25519 signature of the file's bytes with line endings written as
LF (`canonical`), because git checks text files out with CRLF on Windows and LF elsewhere. The
node trusts every public key in packs/keys/*.pub, so more than one team member can sign: each
keeps a private key named after them in SAHAYAK_HOME/keys (%USERPROFILE%/.sahayak/keys), never
in the repository, and SAHAYAK_SIGNER says whose key signs on this machine (default: the team key).

  python scripts/sign_packs.py          sign every pack with this machine's key (--new-key to make one)
"""
from __future__ import annotations

import base64
import os
from functools import lru_cache
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

KEY_NAME = "sahayak-packs"


def signer_name() -> str:
    """Whose key signs on this machine: SAHAYAK_SIGNER, else the team key. A signer's private key is
    SAHAYAK_HOME/keys/<name>.key and its public key packs/keys/<name>.pub; the name is what the node
    page shows as "signed by"."""
    return os.environ.get("SAHAYAK_SIGNER", "").strip() or KEY_NAME


class PackSignatureError(ValueError):
    """A pack whose signature does not match its bytes, or no signature where one is required."""


def sig_path(pack_path: Path) -> Path:
    return pack_path.with_name(pack_path.name + ".sig")


def canonical(data: bytes) -> bytes:
    """The bytes that are signed and hashed: line endings as LF. In a JSON pack a raw line break
    can only sit between tokens (inside a string it must be escaped), so this never changes what
    the pack says; any other edit still breaks the signature."""
    return data.replace(b"\r\n", b"\n")


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
    lf = canonical(data)
    # Packs signed before 6 Oct 2026 were signed on Windows over CRLF bytes; accept that form too.
    forms = (lf, lf.replace(b"\n", b"\r\n"))
    for name, key in trusted_keys(keys_dir):
        for form in forms:
            try:
                key.verify(signature, form)
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
    path.chmod(0o600)  # readable by its owner only (on Windows this only clears read-only)
    return key


def public_pem(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def sign_file(pack_path: Path, key: Ed25519PrivateKey) -> Path:
    sp = sig_path(pack_path)
    sp.write_text(base64.b64encode(key.sign(canonical(pack_path.read_bytes()))).decode("ascii") + "\n", encoding="ascii")
    return sp
