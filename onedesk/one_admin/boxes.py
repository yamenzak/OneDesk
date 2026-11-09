"""A server for One: the tunnel, its addresses and Access lock on Cloudflare,
and the box, set up by deploy/server/first-boot.sh from a release in the
registry. On AWS it is a Lightsail box ordered here; on any other provider a
machine we connect ourselves, which runs the same first boot inside a container
(deploy/server/connect.sh). Shared by scripts/server.py, which builds the first
OneAdmin from dev, and servers.py, which orders the rest. Needs no frappe.
"""

import base64
import gzip
import json
import secrets
import shlex
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3
import requests

API = "https://api.cloudflare.com/client/v4"
ROOT = Path(__file__).resolve().parents[2]
FIRST_BOOT = ROOT / "deploy/server/first-boot.sh"
AGENT = ROOT / "deploy/server/agent.py"
CONNECT = ROOT / "deploy/server/connect.sh"
PIPE = 60
READY_AFTER = 5
READY_WITHIN = 90 * 60
SNAPSHOT_AT = "03:00"
ACCOUNT = "com.cloudflare.api.account"
ZONE = "com.cloudflare.api.account.zone"
REGION = "eu-north-1"
BUNDLE = "medium_3_0"
OWN_BUNDLE = "large_3_0"
CONTAINER_MEMORY = "5g"
CONTAINER_MEMORY_WITH_SWAP = "6g"
MEMORY_SHARE = 0.7
CONTAINER_MEMORY_SHARE = 0.3
REPOSITORY = "yamenzak/onedesk"
LOCKED_ON_ADMIN = ("/desk", "/desk/*", "/app", "/app/*", "/api/resource/*", "/api/v2/*")
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
			raise RuntimeError(f"Cloudflare has no permission {name}")
		out.setdefault(scope, []).append({"id": found["id"]})
	return [{"effect": "allow", "permission_groups": ids, "resources": where[scope]} for scope, ids in out.items()]


def user_data(values: dict[str, str]) -> str:
	"""first-boot.sh with its values exported ahead of it, written out and
	run by bash, since Lightsail puts its own /bin/sh lines first."""
	head = "".join(f"export ONE_{key}={shlex.quote(value)}\n" for key, value in values.items())
	packed = base64.b64encode(gzip.compress(AGENT.read_bytes())).decode()
	agent = f"echo {packed} | base64 -d | gunzip > /root/one-agent.py\n"
	return f"umask 077\n{agent}cat > /root/first-boot <<'ONE_FIRST_BOOT'\n{head}{FIRST_BOOT.read_text()}ONE_FIRST_BOOT\nbash /root/first-boot\nrm -f /root/first-boot /root/one-agent.py\n"


class Cloudflare:
	"""What one server needs from Cloudflare, with the token it is given."""

	def __init__(self, account: str, token: str):
		self.account, self.token, self.master, self.token_id = account, token, None, None

	@classmethod
	def from_master(cls, master: str, account: str) -> "Cloudflare":
		"""With a token that lasts an hour, made from the master key."""
		one = cls(account, "")
		one.master = master
		groups = one.call("GET", "/user/tokens/permission_groups", master)["result"]
		until = (datetime.now(UTC) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
		body = {"name": "One Server Run", "policies": wanted_policies(groups, account), "expires_on": until}
		made = one.call("POST", "/user/tokens", master, json=body)["result"]
		one.token_id, one.token = made["id"], made["value"]
		time.sleep(READY_AFTER)
		return one

	@staticmethod
	def lasting(master: str, account: str, name: str) -> str:
		"""A token that stays, for OneAdmin to order servers with."""
		one = Cloudflare(account, "")
		groups = one.call("GET", "/user/tokens/permission_groups", master)["result"]
		return one.call("POST", "/user/tokens", master, json={"name": name, "policies": wanted_policies(groups, account)})["result"]["value"]

	def call(self, method: str, path: str, token: str | None = None, **kwargs) -> dict:
		headers = {"Authorization": f"Bearer {token or self.token}"}
		answer = requests.request(method, f"{API}{path}", headers=headers, timeout=PIPE, **kwargs)
		body = answer.json()
		if not body.get("success"):
			raise RuntimeError(f"Cloudflare refused {method} {path}: {body.get('errors')}")
		return body

	def end(self) -> None:
		if self.token_id:
			self.call("DELETE", f"/user/tokens/{self.token_id}", self.master)

	def tunnel(self, name: str, hosts: list[str]) -> tuple[str, str]:
		base = f"/accounts/{self.account}/cfd_tunnel"
		made = self.call("POST", base, json={"name": name, "config_src": "cloudflare"})["result"]
		self.call("PUT", f"{base}/{made['id']}/configurations", json={"config": {"ingress": ingress(hosts)}})
		return made["id"], self.call("GET", f"{base}/{made['id']}/token")["result"]

	def tunnel_token(self, tunnel: str) -> str:
		return self.call("GET", f"/accounts/{self.account}/cfd_tunnel/{tunnel}/token")["result"]

	def address(self, zone: str, host: str, tunnel: str) -> None:
		found = self.call("GET", "/zones", params={"name": zone})["result"]
		if not found:
			raise RuntimeError(f"{zone} is not on this Cloudflare account")
		records = f"/zones/{found[0]['id']}/dns_records"
		body = {"type": "CNAME", "name": host, "content": f"{tunnel}.cfargotunnel.com", "proxied": True}
		held = self.call("GET", records, params={"name": host})["result"]
		if held:
			self.call("PUT", f"{records}/{held[0]['id']}", json=body)
		else:
			self.call("POST", records, json=body)

	def lock(self, name: str, host: str, owners: list[str]) -> dict:
		base = f"/accounts/{self.account}/access"
		token = self.call("POST", f"{base}/service_tokens", json={"name": name, "duration": "8760h"})["result"]
		policies = [
			{"name": "Owner", "decision": "allow", "include": [{"email": {"email": one}} for one in owners]},
			{"name": "OneAdmin", "decision": "non_identity", "include": [{"service_token": {"token_id": token["id"]}}]},
		]
		body = {"name": f"Pilot {name}", "domain": host, "type": "self_hosted", "session_duration": "24h", "policies": policies}
		self.call("POST", f"{base}/apps", json=body)
		return {"client_id": token["client_id"], "client_secret": token["client_secret"]}


	def lock_admin(self, host: str, owners: list[str]) -> None:
		"""OneAdmin's desk and raw record API behind Access for its operators.
		The rest stays open: signup, payment, and the account pages customers
		sign in to on this site."""
		base = f"/accounts/{self.account}/access/apps"
		people = [{"email": {"email": one}} for one in owners]
		wanted = {f"{host}{path}" for path in LOCKED_ON_ADMIN}
		for one in self.call("GET", base)["result"]:
			if one.get("domain") in wanted:
				self.call("DELETE", f"{base}/{one['id']}")
		for domain in sorted(wanted):
			body = {"name": f"OneAdmin {domain}", "domain": domain, "type": "self_hosted", "session_duration": "24h", "policies": [{"name": "Operators", "decision": "allow", "include": people}]}
			self.call("POST", base, json=body)

	def add_bench(self, name: str, tunnel: str, hosts: list[str], host: str, zone: str, owners: list[str]) -> None:
		"""A new bench's Pilot address on the box's tunnel, behind the box's lock."""
		base = f"/accounts/{self.account}"
		self.call("PUT", f"{base}/cfd_tunnel/{tunnel}/configurations", json={"config": {"ingress": ingress(hosts)}})
		self.address(zone, host, tunnel)
		token = self.call("GET", f"{base}/access/service_tokens", params={"name": name})["result"][0]
		policies = [
			{"name": "Owner", "decision": "allow", "include": [{"email": {"email": one}} for one in owners]},
			{"name": "OneAdmin", "decision": "non_identity", "include": [{"service_token": {"token_id": token["id"]}}]},
		]
		if not any(one.get("domain") == host for one in self.call("GET", f"{base}/access/apps")["result"]):
			self.call("POST", f"{base}/access/apps", json={"name": f"Pilot {host}", "domain": host, "type": "self_hosted", "session_duration": "24h", "policies": policies})

	def forget(self, name: str, tunnel: str, host: str, zones: list[str]) -> None:
		for zone in zones:
			found = self.call("GET", "/zones", params={"name": zone})["result"]
			if not found:
				continue
			records = f"/zones/{found[0]['id']}/dns_records"
			for one in self.call("GET", records, params={"content": f"{tunnel}.cfargotunnel.com"})["result"]:
				self.call("DELETE", f"{records}/{one['id']}")
		base = f"/accounts/{self.account}"
		for one in self.call("GET", f"{base}/access/apps")["result"]:
			if one.get("domain") == host or one.get("domain", "").startswith(f"pilot-{name.removeprefix('one-')}-"):
				self.call("DELETE", f"{base}/access/apps/{one['id']}")
		for one in self.call("GET", f"{base}/access/service_tokens", params={"name": name})["result"]:
			self.call("DELETE", f"{base}/access/service_tokens/{one['id']}")
		self.call("DELETE", f"{base}/cfd_tunnel/{tunnel}")


def release_of(keys: dict, sha: str) -> dict:
	"""What the registry says a release holds."""
	store = boto3.client("s3", endpoint_url=keys["r2_endpoint"], region_name="auto", aws_access_key_id=keys["assets_read_key"], aws_secret_access_key=keys["assets_read_secret"])
	return json.loads(store.get_object(Bucket=keys["assets_bucket"], Key=f"releases/{sha}.json")["Body"].read())


def wait_ready(host: str, access: dict, stopped=lambda: False) -> None:
	"""Until Pilot answers through the tunnel and the lock. A box whose first
	boot failed powers itself off, and `stopped` says so."""
	headers = {"CF-Access-Client-Id": access["client_id"], "CF-Access-Client-Secret": access["client_secret"]}
	until = time.monotonic() + READY_WITHIN
	while time.monotonic() < until:
		if stopped():
			raise RuntimeError("first boot failed; start the box and read /var/log/one-first-boot.log")
		try:
			if requests.get(f"https://{host}/api/v1/health", headers=headers, timeout=20, allow_redirects=False).status_code == 200:
				return
		except requests.RequestException:
			pass
		time.sleep(30)
	raise RuntimeError("not ready in time; read /var/log/one-first-boot.log in the browser terminal")


def settle(host: str, access: dict, password: str, keys: dict, share: float = MEMORY_SHARE) -> None:
	"""MariaDB's share of memory, and backups to R2 when there is a bucket."""
	pilot = requests.Session()
	pilot.headers.update({"CF-Access-Client-Id": access["client_id"], "CF-Access-Client-Secret": access["client_secret"]})
	base = f"https://{host}/api/v1"
	pilot.post(f"{base}/auth/session", json={"password": password}, timeout=PIPE).raise_for_status()
	pilot.post(f"{base}/database/quick-actions/memory-share", json={"memory_share": share}, timeout=PIPE).raise_for_status()
	if keys.get("backup_key"):
		s3 = {"provider": "cloudflare", "region": "auto", "bucket": keys["backup_bucket"], "endpoint_url": keys["r2_endpoint"], "access_key": keys["backup_key"], "secret_key": keys["backup_secret"]}
		pilot.patch(f"{base}/settings", json={"s3": s3}, timeout=PIPE).raise_for_status()


def latest_release(keys: dict) -> str:
	"""The newest release in the registry: its OneDesk commit."""
	store = boto3.client("s3", endpoint_url=keys["r2_endpoint"], region_name="auto", aws_access_key_id=keys["assets_read_key"], aws_secret_access_key=keys["assets_read_secret"])
	found = [one for one in store.list_objects_v2(Bucket=keys["assets_bucket"], Prefix="releases/").get("Contents", []) if one["Key"].endswith(".json")]
	if not found:
		raise RuntimeError("the registry holds no release")
	return max(found, key=lambda one: one["LastModified"])["Key"].removeprefix("releases/").removesuffix(".json")


def _aws(keys: dict, region: str, config=None):
	return boto3.client("lightsail", region_name=region, aws_access_key_id=keys["aws_access_key_id"], aws_secret_access_key=keys["aws_secret_access_key"], config=config)


def _on_cloudflare(cloudflare: Cloudflare, name: str, domain: str, tenant_domain: str, origin_zone: str, owners: list[str], more_hosts: tuple, on_made, say) -> tuple[dict, str]:
	"""A server's tunnel, addresses and lock, and what was made: every key it
	will need, given to `on_made` before anything can go wrong with the box."""
	host = admin_host(name, domain)
	origin = f"origin-{name}.{origin_zone}"
	password = f"Pi{secrets.token_hex(14)}-Z9"
	tunnel, tunnel_token = cloudflare.tunnel(f"one-{name}", [host, *more_hosts, origin, f"*.{tenant_domain}"])
	for one in [host, *more_hosts]:
		cloudflare.address(domain, one, tunnel)
	cloudflare.address(origin_zone, origin, tunnel)
	access = cloudflare.lock(f"one-{name}", host, owners)
	made = {"tunnel": tunnel, "host": host, "origin": origin, "origin_zone": origin_zone, "access": access, "pilot_password": password, "agent": secrets.token_hex(24)}
	on_made(made)
	say("Cloudflare ready")
	return made, tunnel_token


def _boot_values(keys: dict, name: str, made: dict, tunnel_token: str, release: str, branch: str, repository: str, admin_url: str) -> dict:
	"""What first-boot.sh is given."""
	about = release_of(keys, release)
	return {
		"TUNNEL_TOKEN": tunnel_token,
		"PILOT_PASSWORD": made["pilot_password"],
		"ADMIN_HOST": made["host"],
		"GITHUB_TOKEN": keys["github_token"],
		"REPOSITORY": repository,
		"BRANCH": branch,
		"RELEASE": release,
		"FRAPPE": about["frappe"],
		"ERPNEXT": about["erpnext"],
		"HRMS": about["hrms"],
		"R2_ENDPOINT": keys["r2_endpoint"],
		"R2_BUCKET": keys["assets_bucket"],
		"R2_KEY": keys["assets_read_key"],
		"R2_SECRET": keys["assets_read_secret"],
		"SERVER": name,
		"AGENT_SECRET": made["agent"],
		"ADMIN_URL": admin_url,
	}


def new(keys: dict, cloudflare: Cloudflare, name: str, domain: str, tenant_domain: str, origin_zone: str, owners: list[str], release: str, branch: str = "main", region: str = REGION, bundle: str = BUNDLE, key: str | None = None, ssh_from: str | None = None, more_hosts: tuple = (), repository: str = REPOSITORY, say=lambda _said: None, on_made=lambda _made: None, admin_url: str = "") -> dict:
	"""A box from nothing to Pilot answering behind its lock: what was made."""
	made, tunnel_token = _on_cloudflare(cloudflare, name, domain, tenant_domain, origin_zone, owners, more_hosts, on_made, say)
	host, tunnel, access = made["host"], made["tunnel"], made["access"]
	script = user_data(_boot_values(keys, name, made, tunnel_token, release, branch, repository, admin_url))
	aws = _aws(keys, region)
	order = {"instanceNames": [name], "availabilityZone": f"{region}a", "blueprintId": "ubuntu_24_04", "bundleId": bundle, "userData": script, "tags": [{"key": "one", "value": "server"}], "addOns": [{"addOnType": "AutoSnapshot", "autoSnapshotAddOnRequest": {"snapshotTimeOfDay": SNAPSHOT_AT}}]}
	try:
		aws.create_instances(**order, **({"keyPairName": key} if key else {}))
	except Exception:
		cloudflare.forget(f"one-{name}", tunnel, host, [domain, origin_zone])
		raise
	say(f"{name} ordered, {bundle} in {region}")
	while aws.get_instance_state(instanceName=name)["state"]["name"] != "running":
		time.sleep(10)
	ports = {"fromPort": 22, "toPort": 22, "protocol": "tcp", "cidrListAliases": ["lightsail-connect"]}
	if ssh_from:
		ports["cidrs"] = [ssh_from]
	aws.put_instance_public_ports(instanceName=name, portInfos=[ports])
	say("firewall closed; waiting for first boot")
	wait_ready(host, access, lambda: aws.get_instance_state(instanceName=name)["state"]["name"] in ("stopped", "stopping"))
	settle(host, access, made["pilot_password"], keys)
	aws.update_instance_metadata_options(instanceName=name, httpEndpoint="disabled")
	say(f"ready at https://{host}")
	return made


def connect(keys: dict, cloudflare: Cloudflare, name: str, domain: str, tenant_domain: str, origin_zone: str, owners: list[str], on_made=lambda _made: None) -> dict:
	"""A machine that is not on AWS, ready to be joined: its tunnel, addresses
	and lock are made here, and `connect_script` is run on it."""
	made, _token = _on_cloudflare(cloudflare, name, domain, tenant_domain, origin_zone, owners, (), on_made, lambda _said: None)
	return made


def connect_script(keys: dict, cloudflare: Cloudflare, name: str, made: dict, release: str, admin_url: str, branch: str = "main", repository: str = REPOSITORY) -> str:
	"""What runs on a connected machine, as root: deploy/server/connect.sh, with
	the first boot it runs inside a container and that container's memory."""
	values = _boot_values(keys, name, made, cloudflare.tunnel_token(made["tunnel"]), release, branch, repository, admin_url)
	box = user_data({**values, "IN_CONTAINER": "1"})
	head = "".join(f"{key}={shlex.quote(value)}\n" for key, value in (("ONE_BOX", base64.b64encode(box.encode()).decode()), ("ONE_MEMORY", CONTAINER_MEMORY), ("ONE_MEMORY_SWAP", CONTAINER_MEMORY_WITH_SWAP)))
	return f"{head}{CONNECT.read_text()}"


def reboot(keys: dict, name: str, region: str = REGION) -> None:
	_aws(keys, region).reboot_instance(instanceName=name)


def drop(keys: dict, cloudflare: Cloudflare, name: str, made: dict, domain: str, region: str = REGION) -> None:
	"""The box, its tunnel, addresses and lock gone."""
	_aws(keys, region).delete_instance(instanceName=name, forceDeleteAddOns=True)
	time.sleep(30)
	cloudflare.forget(f"one-{name}", made["tunnel"], made["host"], [domain, made.get("origin_zone") or domain])
