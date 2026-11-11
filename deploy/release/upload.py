"""A release into the registry, run by build.sh. `publish` puts up the
screens' archive, the ready-made bench, the template site and the box's agent
of that commit, then what they are (`releases/<sha>.json`, last, since its
arrival is what makes the release exist), and tells OneAdmin. `config` prints
the template site's config without anything a site must not share."""

import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SHARED_NEVER = ("db_", "encryption_key", "admin_password", "pilot_", "cloud_", "onedesk_vapid", "host_name", "installed_apps", "maintenance", "pause_", "domains", "route", "ssl", "cert_name", "email_sender_name", "backup")
SECRET_WORDS = ("secret", "token", "password", "key")


def shareable(config: dict) -> dict:
	"""A site's config with only what every site from the template may hold. Pure."""
	return {key: value for key, value in config.items() if not key.startswith(SHARED_NEVER) and not any(word in key.lower() for word in SECRET_WORDS)}


def _part(out: Path, name: str) -> dict:
	path = out / name
	return {"sha256": Path(f"{path}.sha256").read_text().strip(), "size": path.stat().st_size}


def commit_of(repo: Path, sha: str) -> dict:
	"""The commit's subject and when it was made, or nothing when the
	checkout cannot say."""
	found = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%s%x00%cI", sha], capture_output=True, text=True, check=False)
	subject, _, at = found.stdout.strip().partition("\x00")
	return {"subject": subject, "committed_at": at} if found.returncode == 0 and at else {}


def publish(out: str, onedesk: str, frappe: str, erpnext: str, hrms: str) -> None:
	import boto3

	held = Path(out)
	bucket = os.environ["R2_ASSETS_BUCKET"]
	store = boto3.client(
		"s3",
		endpoint_url=os.environ["R2_ENDPOINT"],
		region_name="auto",
		aws_access_key_id=os.environ["R2_ASSETS_KEY"],
		aws_secret_access_key=os.environ["R2_ASSETS_SECRET"],
	)
	key = f"releases/{onedesk}"
	for suffix in ("tar.gz", "bench.tar.gz", "site.tar.gz"):
		store.upload_file(str(held / f"{onedesk}.{suffix}"), bucket, f"{key}.{suffix}")
	store.upload_file(str(Path(__file__).resolve().parents[1] / "server" / "agent.py"), bucket, f"{key}.agent.py")
	about = {
		"onedesk": onedesk,
		"frappe": frappe,
		"erpnext": erpnext,
		"hrms": hrms,
		**_part(held, f"{onedesk}.tar.gz"),
		"bench": {**_part(held, f"{onedesk}.bench.tar.gz"), "python": (held / f"{onedesk}.bench.python").read_text().split()},
		"template": _part(held, f"{onedesk}.site.tar.gz"),
		**commit_of(Path(__file__).resolve().parents[2], onedesk),
		"built_at": int(time.time()),
		"built_in": int(os.environ.get("BUILT_IN") or 0) or None,
	}
	store.put_object(Bucket=bucket, Key=f"{key}.json", Body=json.dumps(about).encode(), ContentType="application/json")
	print(json.dumps(about))
	announce(onedesk)


def signed(secret: str, body: str) -> str:
	"""Pure."""
	return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def announce(onedesk: str) -> None:
	"""OneAdmin told a release is up, signed with the secret it shares with
	this workflow. Without the two, the hourly check finds it."""
	url, secret = os.environ.get("ONE_ADMIN_URL"), os.environ.get("ONE_RELEASE_SECRET")
	if not url or not secret:
		return
	body = json.dumps({"release": onedesk, "at": int(time.time())})
	asked = urllib.request.Request(
		f"{url.rstrip('/')}/api/method/onedesk.one_admin.releases.released",
		data=body.encode(),
		headers={"Content-Type": "application/json", "User-Agent": "OneRelease/1.0", "X-One-Release": signed(secret, body)},
		method="POST",
	)
	try:
		print(urllib.request.urlopen(asked, timeout=30).status)
	except OSError as raised:
		print(f"OneAdmin was not told: {raised}")


if __name__ == "__main__":
	if sys.argv[1] == "config":
		print(json.dumps(shareable(json.loads(Path(sys.argv[2]).read_text())), indent=1))
	else:
		publish(*sys.argv[2:])
