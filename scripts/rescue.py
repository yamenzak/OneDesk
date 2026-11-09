"""The keys a new dev machine needs, in one file only a passphrase opens.

`pack` writes the file and sends it to the locked backup bucket through the
keeper, under `rescue/`, so it can be fetched from Cloudflare's dashboard if
this machine is gone. `unpack` puts the keys back. deploy/local/README.md.

    python scripts/rescue.py pack [--out FILE] [--no-send]
    python scripts/rescue.py unpack FILE [--into DIR]
"""

import argparse
import base64
import getpass
import json
import os
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

HOME = Path.home()
SITE_CONFIG = HOME / "one-bench" / "sites" / "admin.4dl.dev" / "site_config.json"
KEPT = (".one-local", ".one-dev.json", ".one-keys-dev.json", ".one-keys-prod.json", ".ssh/one_servers", ".ssh/one_servers.pub", ".config/gh/hosts.yml")
KEPT_FOLDERS = (".one-servers",)
PRODUCTION = HOME / ".one-servers" / "admin.json"
PRODUCTION_SITE = "admin.4dl.app"
PRODUCTION_KEEPER = "https://one-keeper.4dl.workers.dev"
SHORTEST = 12


def key_from(passphrase: str, salt: bytes) -> bytes:
	"""Pure."""
	return base64.urlsafe_b64encode(Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode()))


def sealed(files: dict[str, bytes], passphrase: str) -> bytes:
	"""The files, encrypted under the passphrase. Pure but for the salt."""
	salt = secrets.token_bytes(16)
	body = json.dumps({name: base64.b64encode(content).decode() for name, content in files.items()}).encode()
	return json.dumps({"salt": base64.b64encode(salt).decode(), "token": Fernet(key_from(passphrase, salt)).encrypt(body).decode()}).encode()


def opened(held: bytes, passphrase: str) -> dict[str, bytes]:
	"""Pure."""
	outer = json.loads(held)
	body = Fernet(key_from(passphrase, base64.b64decode(outer["salt"]))).decrypt(outer["token"].encode())
	return {name: base64.b64decode(content) for name, content in json.loads(body).items()}


def gathered() -> dict[str, bytes]:
	files = {name: (HOME / name).read_bytes() for name in KEPT if (HOME / name).exists()}
	for folder in KEPT_FOLDERS:
		files |= {str(path.relative_to(HOME)): path.read_bytes() for path in (HOME / folder).glob("*") if path.is_file()}
	return files


def passphrase_asked(twice: bool) -> str:
	given = os.environ.get("ONE_RESCUE_PASSPHRASE") or getpass.getpass("Passphrase: ")
	if twice and not os.environ.get("ONE_RESCUE_PASSPHRASE") and given != getpass.getpass("Again: "):
		raise SystemExit("The passphrases do not match.")
	if twice and len(given) < SHORTEST:
		raise SystemExit(f"Use at least {SHORTEST} characters.")
	return given


def production_secret() -> str:
	"""The production keeper's secret, read from OneAdmin's site through its
	box's Pilot, so it is never kept on this machine."""
	made = json.loads(PRODUCTION.read_text())
	pilot = requests.Session()
	pilot.headers.update({"CF-Access-Client-Id": made["access"]["client_id"], "CF-Access-Client-Secret": made["access"]["client_secret"]})
	base = f"https://{made['host']}/api/v1"
	pilot.post(f"{base}/auth/session", json={"password": made["pilot_password"]}, timeout=60).raise_for_status()
	answer = pilot.get(f"{base}/sites/{PRODUCTION_SITE}/configuration", timeout=60)
	answer.raise_for_status()
	return answer.json()["keeper_secret"]


def keeper() -> tuple[str, str]:
	"""The keeper the kit goes to and its secret: production's once it exists."""
	if PRODUCTION.exists():
		return PRODUCTION_KEEPER, production_secret()
	config = json.loads(SITE_CONFIG.read_text())
	return config.get("keeper_url") or os.environ["ONE_KEEPER_URL"], config["keeper_secret"]


def send(held: bytes) -> str:
	url, secret = keeper()
	key = f"rescue/{datetime.now(UTC).strftime('%Y-%m-%d-%H%M')}.one"
	requests.put(f"{url.rstrip('/')}/backup/{key}", data=held, headers={"x-one-secret": secret}, timeout=120).raise_for_status()
	return key


def pack(args) -> None:
	held = sealed(gathered(), passphrase_asked(True))
	if args.out:
		Path(args.out).write_bytes(held)
		print(f"written to {args.out}")
	if not args.no_send:
		print(f"kept as {send(held)}")


def unpack(args) -> None:
	into = Path(args.into) if args.into else HOME
	for name, content in opened(Path(args.file).read_bytes(), passphrase_asked(False)).items():
		path = into / name
		path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
		with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as file:
			file.write(content)
		print(name)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	commands = parser.add_subparsers(required=True)
	one = commands.add_parser("pack")
	one.add_argument("--out")
	one.add_argument("--no-send", action="store_true")
	one.set_defaults(run=pack)
	two = commands.add_parser("unpack")
	two.add_argument("file")
	two.add_argument("--into")
	two.set_defaults(run=unpack)
	args = parser.parse_args()
	args.run(args)


if __name__ == "__main__":
	sys.exit(main())
