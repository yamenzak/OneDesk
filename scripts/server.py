"""A Lightsail server for One, run from dev (one_admin/boxes.py does the work).
Keys come from a JSON file; what it makes goes in ~/.one-servers/<name>.json,
mode 600. `hand-over` writes the keys OneAdmin orders servers with.

    python scripts/server.py new NAME --domain D --release SHA --keys FILE --owner EMAIL \\
        --tenant-domain T --origin-zone Z
    python scripts/server.py drop NAME --domain D --keys FILE
    python scripts/server.py lock-admin HOST --keys FILE --owner EMAIL
    python scripts/server.py hand-over NAME --keys FILE --origin-zone Z --out FILE
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_admin import boxes


def _private(path: Path, value: dict) -> None:
	path.parent.mkdir(mode=0o700, exist_ok=True)
	with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as file:
		json.dump(value, file)


def _kept(name: str) -> Path:
	return Path.home() / ".one-servers" / f"{name}.json"


def _keys(args) -> dict:
	return json.loads(Path(args.keys).read_text())


def _cloudflare(keys: dict) -> boxes.Cloudflare:
	return boxes.Cloudflare.from_master(keys["cloudflare_master"], keys["cloudflare_account"])


def new(args) -> None:
	keys = _keys(args)
	cloudflare = _cloudflare(keys)
	try:
		boxes.new(
			keys, cloudflare, args.name, args.domain, args.tenant_domain, args.origin_zone, [args.owner], args.release,
			branch=args.branch, region=args.region, bundle=args.bundle, key=args.key, ssh_from=args.ssh_from,
			more_hosts=tuple(args.host), repository=args.repository, say=print,
			on_made=lambda made: _private(_kept(args.name), made),
		)
	finally:
		cloudflare.end()


def lock_admin(args) -> None:
	cloudflare = _cloudflare(_keys(args))
	try:
		cloudflare.lock_admin(args.host, args.owner)
	finally:
		cloudflare.end()
	print(f"{args.host} locked on {len(boxes.LOCKED_ON_ADMIN)} paths")


def drop(args) -> None:
	keys = _keys(args)
	path = _kept(args.name)
	cloudflare = _cloudflare(keys)
	try:
		boxes.drop(keys, cloudflare, args.name, json.loads(path.read_text()), args.domain, args.region)
	finally:
		cloudflare.end()
	path.unlink()
	print("box, tunnel, addresses and lock removed")


def hand_over(args) -> None:
	keys = _keys(args)
	token = boxes.Cloudflare.lasting(keys["cloudflare_master"], keys["cloudflare_account"], args.name)
	given = {key: value for key, value in keys.items() if key != "cloudflare_master"}
	_private(Path(args.out), {**given, "cloudflare_token": token, "origin_zone": args.origin_zone})
	print(f"keys for OneAdmin written to {args.out}")


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	commands = parser.add_subparsers(required=True)
	one = commands.add_parser("new")
	one.add_argument("name")
	one.add_argument("--domain", required=True)
	one.add_argument("--release", required=True)
	one.add_argument("--keys", required=True)
	one.add_argument("--tenant-domain", required=True)
	one.add_argument("--origin-zone", required=True)
	one.add_argument("--owner", required=True)
	one.add_argument("--host", action="append", default=[])
	one.add_argument("--repository", default=boxes.REPOSITORY)
	one.add_argument("--branch", default="main")
	one.add_argument("--region", default=boxes.REGION)
	one.add_argument("--bundle", default=boxes.BUNDLE)
	one.add_argument("--key", default="one-dev")
	one.add_argument("--ssh-from")
	one.set_defaults(run=new)
	locked = commands.add_parser("lock-admin")
	locked.add_argument("host")
	locked.add_argument("--keys", required=True)
	locked.add_argument("--owner", action="append", required=True)
	locked.set_defaults(run=lock_admin)
	gone = commands.add_parser("drop")
	gone.add_argument("name")
	gone.add_argument("--domain", required=True)
	gone.add_argument("--keys", required=True)
	gone.add_argument("--region", default=boxes.REGION)
	gone.set_defaults(run=drop)
	over = commands.add_parser("hand-over")
	over.add_argument("name")
	over.add_argument("--keys", required=True)
	over.add_argument("--origin-zone", required=True)
	over.add_argument("--out", required=True)
	over.set_defaults(run=hand_over)
	args = parser.parse_args()
	args.run(args)


if __name__ == "__main__":
	sys.exit(main())
