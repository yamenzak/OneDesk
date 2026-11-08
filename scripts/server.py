"""A new Lightsail server for One, run from dev: the tunnel, its addresses
and Access lock on Cloudflare, the box on AWS, set up by
deploy/server/first-boot.sh from a release in the registry. Keys come from
a JSON file; what it makes goes in ~/.one-servers/<name>.json, mode 600.

    python scripts/server.py new NAME --domain D --release SHA --keys FILE --owner EMAIL
    python scripts/server.py drop NAME --domain D --keys FILE
"""

import argparse
import json
import os
import secrets
import shlex
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3
import requests

API = "https://api.cloudflare.com/client/v4"
ROOT = Path(__file__).resolve().parent.parent
FIRST_BOOT = ROOT / "deploy/server/first-boot.sh"
PIPE = 60
READY_WITHIN = 90 * 60
SNAPSHOT_AT = "03:00"
ACCOUNT = "com.cloudflare.api.account"
ZONE = "com.cloudflare.api.account.zone"
NEEDS = (
	("Cloudflare Tunnel Write", ACCOUNT),
	("Access: Apps Write", ACCOUNT),
	("Access: Policies Write", ACCOUNT),
	("Access: Service Tokens Write", ACCOUNT),
	("Zone Read", ZONE),
	("DNS Write", ZONE),
)


def admin_host(name: str, domain: str) -> str:
	"""The address of a server's Pilot page. Pure."""
	return f"pilot-{name}.{domain}"


def ingress(hosts: list[str]) -> list[dict]:
	"""The tunnel's rules: each address to nginx on the box. Pure."""
	return [{"hostname": one, "service": "http://localhost:80"} for one in hosts] + [{"service": "http_status:404"}]


def wanted_policies(groups: list[dict], account: str) -> list[dict]:
	"""A run token's policies, by permission name and scope. Pure."""
	where = {ACCOUNT: {f"{ACCOUNT}.{account}": "*"}, ZONE: {f"{ZONE}.*": "*"}}
	out: dict[str, list[dict]] = {}
	for name, scope in NEEDS:
		found = next((one for one in groups if one["name"] == name and one.get("scopes") == [scope]), None)
		if not found:
			raise SystemExit(f"Cloudflare has no permission {name}")
		out.setdefault(scope, []).append({"id": found["id"]})
	return [{"effect": "allow", "permission_groups": ids, "resources": where[scope]} for scope, ids in out.items()]


def user_data(values: dict[str, str]) -> str:
	"""first-boot.sh with its values exported ahead of it, written out and
	run by bash, since Lightsail puts its own /bin/sh lines first."""
	head = "".join(f"export ONE_{key}={shlex.quote(value)}\n" for key, value in values.items())
	return f"umask 077\ncat > /root/first-boot <<'ONE_FIRST_BOOT'\n{head}{FIRST_BOOT.read_text()}ONE_FIRST_BOOT\nbash /root/first-boot\nrm -f /root/first-boot\n"


class Cloudflare:
	"""What one server needs from Cloudflare, with a token that lasts an hour."""

	def __init__(self, master: str, account: str):
		self.account = account
		self.master = master
		groups = self.call("GET", "/user/tokens/permission_groups", master)["result"]
		until = (datetime.now(UTC) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
		body = {"name": "One Server Run", "policies": wanted_policies(groups, account), "expires_on": until}
		made = self.call("POST", "/user/tokens", master, json=body)["result"]
		self.token_id, self.token = made["id"], made["value"]

	def call(self, method: str, path: str, token: str | None = None, **kwargs) -> dict:
		headers = {"Authorization": f"Bearer {token or self.token}"}
		answer = requests.request(method, f"{API}{path}", headers=headers, timeout=PIPE, **kwargs)
		body = answer.json()
		if not body.get("success"):
			raise SystemExit(f"Cloudflare refused {method} {path}: {body.get('errors')}")
		return body

	def end(self) -> None:
		self.call("DELETE", f"/user/tokens/{self.token_id}", self.master)

	def tunnel(self, name: str, hosts: list[str]) -> tuple[str, str]:
		base = f"/accounts/{self.account}/cfd_tunnel"
		made = self.call("POST", base, json={"name": name, "config_src": "cloudflare"})["result"]
		self.call("PUT", f"{base}/{made['id']}/configurations", json={"config": {"ingress": ingress(hosts)}})
		return made["id"], self.call("GET", f"{base}/{made['id']}/token")["result"]

	def address(self, zone: str, host: str, tunnel: str) -> None:
		found = self.call("GET", "/zones", params={"name": zone})["result"]
		if not found:
			raise SystemExit(f"{zone} is not on this Cloudflare account")
		body = {"type": "CNAME", "name": host, "content": f"{tunnel}.cfargotunnel.com", "proxied": True}
		self.call("POST", f"/zones/{found[0]['id']}/dns_records", json=body)

	def lock(self, name: str, host: str, owner: str) -> dict:
		base = f"/accounts/{self.account}/access"
		token = self.call("POST", f"{base}/service_tokens", json={"name": name, "duration": "8760h"})["result"]
		policies = [
			{"name": "Owner", "decision": "allow", "include": [{"email": {"email": owner}}]},
			{"name": "OneAdmin", "decision": "non_identity", "include": [{"service_token": {"token_id": token["id"]}}]},
		]
		body = {"name": f"Pilot {name}", "domain": host, "type": "self_hosted", "session_duration": "24h", "policies": policies}
		self.call("POST", f"{base}/apps", json=body)
		return {"client_id": token["client_id"], "client_secret": token["client_secret"]}


	def forget(self, name: str, tunnel: str, host: str, zone: str) -> None:
		found = self.call("GET", "/zones", params={"name": zone})["result"]
		if found:
			records = f"/zones/{found[0]['id']}/dns_records"
			for one in self.call("GET", records, params={"content": f"{tunnel}.cfargotunnel.com"})["result"]:
				self.call("DELETE", f"{records}/{one['id']}")
		base = f"/accounts/{self.account}"
		for one in self.call("GET", f"{base}/access/apps")["result"]:
			if one.get("domain") == host:
				self.call("DELETE", f"{base}/access/apps/{one['id']}")
		for one in self.call("GET", f"{base}/access/service_tokens", params={"name": name})["result"]:
			self.call("DELETE", f"{base}/access/service_tokens/{one['id']}")
		self.call("DELETE", f"{base}/cfd_tunnel/{tunnel}")


def release_of(keys: dict, sha: str) -> dict:
	"""What the registry says a release holds."""
	store = boto3.client("s3", endpoint_url=keys["r2_endpoint"], region_name="auto", aws_access_key_id=keys["assets_read_key"], aws_secret_access_key=keys["assets_read_secret"])
	return json.loads(store.get_object(Bucket=keys["assets_bucket"], Key=f"releases/{sha}.json")["Body"].read())


def keep(name: str, made: dict) -> Path:
	"""What was made, readable only by this user."""
	folder = Path.home() / ".one-servers"
	folder.mkdir(mode=0o700, exist_ok=True)
	path = folder / f"{name}.json"
	descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
	with os.fdopen(descriptor, "w") as file:
		json.dump(made, file)
	return path


def wait_ready(host: str, access: dict) -> None:
	"""Until Pilot answers through the tunnel and the lock."""
	headers = {"CF-Access-Client-Id": access["client_id"], "CF-Access-Client-Secret": access["client_secret"]}
	until = time.monotonic() + READY_WITHIN
	while time.monotonic() < until:
		try:
			if requests.get(f"https://{host}/api/v1/health", headers=headers, timeout=20, allow_redirects=False).status_code == 200:
				return
		except requests.RequestException:
			pass
		time.sleep(30)
	raise SystemExit("not ready in time; read /var/log/one-first-boot.log in the browser terminal")


def settle(host: str, access: dict, password: str, keys: dict) -> None:
	"""MariaDB's share of memory, and backups to R2 when there is a bucket."""
	pilot = requests.Session()
	pilot.headers.update({"CF-Access-Client-Id": access["client_id"], "CF-Access-Client-Secret": access["client_secret"]})
	base = f"https://{host}/api/v1"
	pilot.post(f"{base}/auth/session", json={"password": password}, timeout=PIPE).raise_for_status()
	pilot.post(f"{base}/database/quick-actions/memory-share", json={"memory_share": 0.7}, timeout=PIPE).raise_for_status()
	if keys.get("backup_key"):
		s3 = {"provider": "cloudflare", "region": "auto", "bucket": keys["backup_bucket"], "endpoint_url": keys["r2_endpoint"], "access_key": keys["backup_key"], "secret_key": keys["backup_secret"]}
		pilot.patch(f"{base}/settings", json={"s3": s3}, timeout=PIPE).raise_for_status()


def new(args: argparse.Namespace) -> None:
	keys = json.loads(Path(args.keys).read_text())
	about = release_of(keys, args.release)
	host = admin_host(args.name, args.domain)
	hosts = [host, *args.host]
	password = f"Pi{secrets.token_hex(14)}-Z9"
	cloudflare = Cloudflare(keys["cloudflare_master"], keys["cloudflare_account"])
	try:
		tunnel, tunnel_token = cloudflare.tunnel(f"one-{args.name}", hosts)
		for one in hosts:
			cloudflare.address(args.domain, one, tunnel)
		access = cloudflare.lock(f"one-{args.name}", host, args.owner)
	finally:
		cloudflare.end()
	path = keep(args.name, {"tunnel": tunnel, "host": host, "access": access, "pilot_password": password})
	print(f"Cloudflare ready, kept in {path}")

	script = user_data(
		{
			"TUNNEL_TOKEN": tunnel_token,
			"PILOT_PASSWORD": password,
			"ADMIN_HOST": host,
			"GITHUB_TOKEN": keys["github_token"],
			"REPOSITORY": args.repository,
			"BRANCH": args.branch,
			"RELEASE": args.release,
			"FRAPPE": about["frappe"],
			"ERPNEXT": about["erpnext"],
			"HRMS": about["hrms"],
			"R2_ENDPOINT": keys["r2_endpoint"],
			"R2_BUCKET": keys["assets_bucket"],
			"R2_KEY": keys["assets_read_key"],
			"R2_SECRET": keys["assets_read_secret"],
		}
	)
	aws = boto3.client("lightsail", region_name=args.region, aws_access_key_id=keys["aws_access_key_id"], aws_secret_access_key=keys["aws_secret_access_key"])
	aws.create_instances(
		instanceNames=[args.name],
		availabilityZone=f"{args.region}a",
		blueprintId="ubuntu_24_04",
		bundleId=args.bundle,
		keyPairName=args.key,
		userData=script,
		tags=[{"key": "one", "value": "server"}],
		addOns=[{"addOnType": "AutoSnapshot", "autoSnapshotAddOnRequest": {"snapshotTimeOfDay": SNAPSHOT_AT}}],
	)
	print(f"{args.name} ordered, {args.bundle} in {args.region}")
	while aws.get_instance_state(instanceName=args.name)["state"]["name"] != "running":
		time.sleep(10)
	ports = {"fromPort": 22, "toPort": 22, "protocol": "tcp", "cidrListAliases": ["lightsail-connect"]}
	if args.ssh_from:
		ports["cidrs"] = [args.ssh_from]
	aws.put_instance_public_ports(instanceName=args.name, portInfos=[ports])
	print("firewall closed; waiting for first boot")
	wait_ready(host, access)
	settle(host, access, password, keys)
	aws.update_instance_metadata_options(instanceName=args.name, httpEndpoint="disabled")
	print(f"ready at https://{host}")


def drop(args: argparse.Namespace) -> None:
	keys = json.loads(Path(args.keys).read_text())
	path = Path.home() / ".one-servers" / f"{args.name}.json"
	made = json.loads(path.read_text())
	aws = boto3.client("lightsail", region_name=args.region, aws_access_key_id=keys["aws_access_key_id"], aws_secret_access_key=keys["aws_secret_access_key"])
	aws.delete_instance(instanceName=args.name, forceDeleteAddOns=True)
	print(f"{args.name} deleted; waiting for its tunnel to go quiet")
	time.sleep(30)
	cloudflare = Cloudflare(keys["cloudflare_master"], keys["cloudflare_account"])
	try:
		cloudflare.forget(f"one-{args.name}", made["tunnel"], made["host"], args.domain)
	finally:
		cloudflare.end()
	path.unlink()
	print("tunnel, addresses and lock removed")


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	commands = parser.add_subparsers(required=True)
	one = commands.add_parser("new")
	one.add_argument("name")
	one.add_argument("--domain", required=True)
	one.add_argument("--release", required=True)
	one.add_argument("--keys", required=True)
	one.add_argument("--owner", required=True)
	one.add_argument("--host", action="append", default=[])
	one.add_argument("--repository", default="yamenzak/onedesk")
	one.add_argument("--branch", default="main")
	one.add_argument("--region", default="eu-north-1")
	one.add_argument("--bundle", default="medium_3_0")
	one.add_argument("--key", default="one-dev")
	one.add_argument("--ssh-from")
	one.set_defaults(run=new)
	gone = commands.add_parser("drop")
	gone.add_argument("name")
	gone.add_argument("--domain", required=True)
	gone.add_argument("--keys", required=True)
	gone.add_argument("--region", default="eu-north-1")
	gone.set_defaults(run=drop)
	args = parser.parse_args()
	args.run(args)


if __name__ == "__main__":
	sys.exit(main())
