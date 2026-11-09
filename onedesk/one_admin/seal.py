"""A file sealed so the server that writes it cannot read it back: the
server holds only a public key, the matching private key is worked out from
the rescue passphrase each time and stored nowhere. Needs no frappe, so
scripts/rescue.py opens what backups.py seals (README, Backups)."""

import base64
import json
import secrets

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

SALT = 16
NONCE = 12
RAW = serialization.Encoding.Raw, serialization.PublicFormat.Raw


def _text(raw: bytes) -> str:
	return base64.urlsafe_b64encode(raw).decode()


def _raw(text: str) -> bytes:
	return base64.urlsafe_b64decode(text.encode())


def _private(passphrase: str, salt: bytes) -> X25519PrivateKey:
	seed = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())
	return X25519PrivateKey.from_private_bytes(seed)


def _key(shared: bytes, salt: bytes, ephemeral: bytes) -> bytes:
	return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=ephemeral).derive(shared)


def public_text(passphrase: str) -> str:
	"""What a server is given to seal with, salt and public key in one line.
	Pure but for the salt."""
	salt = secrets.token_bytes(SALT)
	public = _private(passphrase, salt).public_key().public_bytes(*RAW)
	return f"{_text(salt)}.{_text(public)}"


def sealed(body: bytes, public: str) -> bytes:
	"""`body` sealed to a `public_text`: only the passphrase opens it."""
	salt_text, public_part = public.strip().split(".", 1)
	salt = _raw(salt_text)
	ephemeral = X25519PrivateKey.generate()
	ephemeral_raw = ephemeral.public_key().public_bytes(*RAW)
	key = _key(ephemeral.exchange(X25519PublicKey.from_public_bytes(_raw(public_part))), salt, ephemeral_raw)
	nonce = secrets.token_bytes(NONCE)
	return json.dumps(
		{"salt": salt_text, "ephemeral": _text(ephemeral_raw), "nonce": _text(nonce), "body": _text(AESGCM(key).encrypt(nonce, body, None))}
	).encode()


def opened(held: bytes, passphrase: str) -> bytes:
	"""A sealed file opened with the passphrase."""
	outer = json.loads(held)
	salt, ephemeral_raw = _raw(outer["salt"]), _raw(outer["ephemeral"])
	shared = _private(passphrase, salt).exchange(X25519PublicKey.from_public_bytes(ephemeral_raw))
	return AESGCM(_key(shared, salt, ephemeral_raw)).decrypt(_raw(outer["nonce"]), _raw(outer["body"]), None)
