"""The keys a new dev machine needs, in one file only a passphrase opens.
deploy/local/README.md.

`pack` writes the kit and sends it to production's OneAdmin with an
operator's API key (`ONE_OPERATOR_KEY` in ~/.one-local), which adds it to the
locked backup bucket under `rescue/` through its keeper; this machine never
holds the keeper's secret. `unpack` puts the keys back. `key` makes the public
key OneAdmin seals its config copy with. `open` opens a sealed copy.
`restore` puts a test workspace back from the newest backup it sent itself,
and `fetch` brings OneAdmin's newest sealed config and backup down, both from
the locked bucket with nothing but a sign-in to Cloudflare (one_admin/AGENTS.md,
Rebuilding OneAdmin and Test workspaces).

    python scripts/rescue.py pack [--out FILE] [--no-send]
    python scripts/rescue.py unpack FILE [--into DIR]
    python scripts/rescue.py key
    python scripts/rescue.py open FILE [--out FILE]
    python scripts/rescue.py restore SITE [--keys FILE]
    python scripts/rescue.py fetch [--keys FILE] [--into DIR]
"""

import argparse
import base64
import time
import getpass
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from onedesk.one_admin import cloudflare_signin, seal  # noqa: E402

HOME = Path.home()
BENCH = HOME / "one-bench"
SITES = BENCH / "sites"
SITE_COPIES = ".one-site-configs"
ADMIN = "https://admin.4dl.app"
KEEP_KIT = "onedesk.one_admin.backups.keep_rescue_kit"
KEPT = (".one-local", ".one-keys-prod.json", ".ssh/one_servers", ".ssh/one_servers.pub", ".config/gh/hosts.yml")
KEPT_FOLDERS = (".one-servers", ".cloudflared")
SHORTEST = 12
FETCH_SALT = b"one-rescue-fetch"
API = "https://api.cloudflare.com/client/v4"
LOCKED = "one-backups"
OURS = "oneadmin"
READS = "Workers R2 Storage Bucket Item Read"
FETCH_FOR = 3600
SCOPES = "user-api-tokens.write account-api-tokens.write"


def key_from(passphrase: str, salt: bytes) -> bytes:
	"""Pure."""
	return base64.urlsafe_b64encode(Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode()))


def fetch_secret(passphrase: str) -> str:
	"""What a new machine shows the keeper to be given the kit. Pure."""
	return Scrypt(salt=FETCH_SALT, length=32, n=2**15, r=8, p=1).derive(passphrase.encode()).hex()


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
	for site in dev_sites():
		files[f"{SITE_COPIES}/{site}.json"] = (SITES / site / "site_config.json").read_bytes()
	return files


def dev_sites() -> list[str]:
	"""The sites of this machine marked one_dev."""
	return sorted(path.parent.name for path in SITES.glob("*/site_config.json") if json.loads(path.read_text()).get("one_dev"))


def operator_key() -> str:
	"""An operator's `key:secret` on production's OneAdmin: the environment's,
	or ~/.one-local's."""
	given = os.environ.get("ONE_OPERATOR_KEY")
	if not given and (HOME / ".one-local").exists():
		given = next((line.split("=", 1)[1] for line in (HOME / ".one-local").read_text().splitlines() if line.startswith("ONE_OPERATOR_KEY=")), "")
	if not given or ":" not in given:
		raise SystemExit("No ONE_OPERATOR_KEY=key:secret in ~/.one-local: make an API key for an operator on admin.4dl.app and add it there.")
	return given.strip()


def passphrase_asked(twice: bool) -> str:
	given = os.environ.get("ONE_RESCUE_PASSPHRASE") or getpass.getpass("Passphrase: ")
	if twice and not os.environ.get("ONE_RESCUE_PASSPHRASE") and given != getpass.getpass("Again: "):
		raise SystemExit("The passphrases do not match.")
	if twice and len(given) < SHORTEST:
		raise SystemExit(f"Use at least {SHORTEST} characters.")
	return given


def kit_body(held: bytes, passphrase: str) -> dict:
	"""What OneAdmin is sent: the sealed kit and the hash of what a new
	machine shows the keeper to fetch it. Neither opens it. Pure."""
	return {"kit": base64.b64encode(held).decode(), "fetch_hash": hashlib.sha256(fetch_secret(passphrase).encode()).hexdigest()}


def send(held: bytes, passphrase: str) -> str:
	admin = (os.environ.get("ONE_ADMIN_URL") or ADMIN).rstrip("/")
	answered = requests.post(f"{admin}/api/method/{KEEP_KIT}", json=kit_body(held, passphrase), headers={"Authorization": f"token {operator_key()}"}, timeout=120)
	if not answered.ok:
		raise SystemExit(f"{admin} did not keep the kit: {answered.status_code} {answered.text[:300]}")
	return answered.json()["message"]["kept"]


def pack(args) -> None:
	passphrase = passphrase_asked(True)
	held = sealed(gathered(), passphrase)
	if args.out:
		Path(args.out).write_bytes(held)
		print(f"written to {args.out}")
	if not args.no_send:
		print(f"kept as {send(held, passphrase)}")


def _written(path: Path, content: bytes) -> None:
	path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
	with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as file:
		file.write(content)


def unpack(args) -> None:
	into = Path(args.into) if args.into else HOME
	for name, content in opened(Path(args.file).read_bytes(), passphrase_asked(False)).items():
		_written(into / name, content)
		print(name)


def key(_args) -> None:
	"""Print the public key OneAdmin seals its config copy with."""
	print(seal.public_text(passphrase_asked(True)))


def open_copy(args) -> None:
	body = seal.opened(Path(args.file).read_bytes(), passphrase_asked(False))
	if args.out:
		_written(Path(args.out), body)
		print(f"written to {args.out}")
	else:
		sys.stdout.buffer.write(body)


def _bench(*args: str) -> None:
	subprocess.run([shutil.which("bench") or str(HOME / ".local/bin/bench"), *args], cwd=BENCH, check=True)


def _db_root_password() -> str:
	lines = (HOME / ".one-local").read_text().splitlines()
	return next(line.split("=", 1)[1] for line in lines if line.startswith("DB_ROOT_PASSWORD="))


def restore_args(site: str, files: dict[str, Path], root_password: str) -> list[str]:
	"""`bench restore`'s arguments, the files named only if they came. Pure."""
	args = ["--site", site, "restore", str(files["database"]), "--force", "--db-root-username", "root", "--db-root-password", root_password]
	for part, flag in (("public", "--with-public-files"), ("private", "--with-private-files")):
		if part in files:
			args += [flag, str(files[part])]
	return args


def newest_whole(keys: list[str], prefix: str) -> dict[str, str]:
	"""The parts of the newest night under `<prefix><day>/<part>/<name>` that
	has a database. Pure."""
	days: dict[str, dict[str, str]] = {}
	for key in keys:
		pieces = key[len(prefix):].split("/") if key.startswith(prefix) else []
		if len(pieces) == 3:
			days.setdefault(pieces[0], {})[pieces[1]] = key
	whole = [day for day, parts in days.items() if "database" in parts]
	return days[max(whole)] if whole else {}


def site_config_of(site: str) -> Path:
	"""The site's config as the kit kept it, else the bench's."""
	kept = HOME / SITE_COPIES / f"{site}.json"
	return kept if kept.exists() else SITES / site / "site_config.json"


def restore(args) -> None:
	"""A test workspace put back from the newest night it sent the keeper,
	its config first, from the kit, so the database is made under the name and
	password the site had and it is linked as it was."""
	config = site_config_of(args.site)
	slug = json.loads(config.read_text()).get("one_tenant") if config.exists() else None
	if not slug:
		raise SystemExit(f"{args.site} is not linked to a OneAdmin; nothing to restore it from.")
	with _locked_bucket(args.keys) as client:
		listed = _keys_under(client, f"daily/{slug}/")
		parts = {part: key for part, key in newest_whole(listed, f"daily/{slug}/").items() if part in ("database", "public", "private")}
		if not parts:
			print(f"{args.site}: no backup kept yet, left as it is")
			return
		with tempfile.TemporaryDirectory() as room:
			files = {part: Path(room) / key.rsplit("/", 1)[1] for part, key in parts.items()}
			for part, key in parts.items():
				client.download_file(LOCKED, key, str(files[part]))
			_written(SITES / args.site / "site_config.json", config.read_bytes())
			_bench(*restore_args(args.site, files, _db_root_password()))
	_bench("--site", args.site, "migrate")
	print(f"{args.site} restored")


def read_policy(groups: list[dict], account: str, bucket: str) -> list[dict]:
	"""A token's policy that reads one bucket and nothing else. Pure."""
	found = next((one for one in groups if one["name"] == READS), None)
	if not found:
		raise SystemExit(f"Cloudflare has no permission {READS}")
	return [{"effect": "allow", "permission_groups": [{"id": found["id"]}], "resources": {f"com.cloudflare.edge.r2.bucket.{account}_default_{bucket}": "*"}}]


def s3_of(made: dict) -> tuple[str, str]:
	"""An R2 token as S3 credentials: its id, and the SHA-256 of its value. Pure."""
	return made["id"], hashlib.sha256(made["value"].encode()).hexdigest()


def newest_under(keys: list[str], prefix: str) -> list[str]:
	"""Every object of the newest day under a prefix of `<prefix><day>/…`. Pure."""
	days = sorted({key[len(prefix):].split("/", 1)[0] for key in keys if key.startswith(prefix)})
	return [key for key in keys if days and key.startswith(f"{prefix}{days[-1]}/")]


@contextmanager
def _locked_bucket(keys_file: str):
	"""The locked bucket, read-only for an hour, through a sign-in to
	Cloudflare in the browser; the token is deleted after."""
	import boto3

	keys = json.loads(Path(keys_file).expanduser().read_text())
	account = keys["cloudflare_account"]
	admin = keys.get("admin_url") or f"https://admin.{keys['origin_zone']}"
	token, revoke = cloudflare_signin.signed_in_here(keys["cloudflare_oauth_client_id"], keys["cloudflare_oauth_client_secret"], admin, keys.get("cloudflare_oauth_scopes", SCOPES))
	headers = {"Authorization": f"Bearer {token}"}
	made = None
	try:
		groups = requests.get(f"{API}/user/tokens/permission_groups", headers=headers, timeout=30).json()["result"]
		until = datetime.fromtimestamp(time.time() + FETCH_FOR, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
		body = {"name": "One rescue fetch", "policies": read_policy(groups, account, LOCKED), "expires_on": until}
		made = requests.post(f"{API}/user/tokens", headers=headers, json=body, timeout=30).json()["result"]
		key_id, secret = s3_of(made)
		yield boto3.client("s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com", aws_access_key_id=key_id, aws_secret_access_key=secret, region_name="auto")
	finally:
		if made:
			requests.delete(f"{API}/user/tokens/{made['id']}", headers=headers, timeout=30)
		revoke()


def _keys_under(client, prefix: str) -> list[str]:
	"""Every key under a prefix. A new token takes a few seconds to work."""
	for _try in range(10):
		try:
			pages = client.get_paginator("list_objects_v2").paginate(Bucket=LOCKED, Prefix=prefix)
			return [one["Key"] for page in pages for one in page.get("Contents") or []]
		except client.exceptions.ClientError:
			time.sleep(3)
	return []


def fetch(args) -> None:
	with _locked_bucket(args.keys) as client:
		listed = _keys_under(client, f"config/{OURS}/") + _keys_under(client, f"daily/{OURS}/")
		copies = sorted(key for key in listed if key.startswith(f"config/{OURS}/"))
		wanted = copies[-1:] + newest_under(listed, f"daily/{OURS}/")
		into = Path(args.into).expanduser()
		into.mkdir(mode=0o700, parents=True, exist_ok=True)
		for key in wanted:
			client.download_file(LOCKED, key, str(into / key.replace("/", "__")))
			print(f"fetched {key}")
		if not wanted:
			print("nothing kept yet")


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
	commands.add_parser("key").set_defaults(run=key)
	three = commands.add_parser("open")
	three.add_argument("file")
	three.add_argument("--out")
	three.set_defaults(run=open_copy)
	four = commands.add_parser("restore")
	four.add_argument("site")
	four.add_argument("--keys", default=str(HOME / ".one-keys-prod.json"))
	four.set_defaults(run=restore)
	five = commands.add_parser("fetch")
	five.add_argument("--keys", default=str(HOME / ".one-keys-prod.json"))
	five.add_argument("--into", default=str(HOME / "one-rescue"))
	five.set_defaults(run=fetch)
	args = parser.parse_args()
	args.run(args)


if __name__ == "__main__":
	sys.exit(main())
