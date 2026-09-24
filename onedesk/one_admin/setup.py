"""Cloudflare, set up from one key.

The operator gives One Admin Settings one API token and presses **Set up
Cloudflare**. Everything a workspace needs from Cloudflare is then found or
made here:
- the account and the zone;
- the KV namespace both Workers read;
- the two R2 buckets and the S3 keys to them;
- the web router and the mail Worker, with their routes and DNS;
- mail routing and sending for the mail domain.

**It never takes what is somebody else's.** A resource that exists under our
name is ours and is kept. One that exists but belongs to something else — a
route another Worker answers, a DNS record that points elsewhere — is left as
it is and reported. Nothing is deleted.

The one deliberate exception is the zone's email catch-all. There is only one
per zone, and the mail domain cannot work without it, so it is pointed at our
Worker whatever it held. The operator decided that for `4dl.app`.

**Running it twice is running it once.** Each step reads before it writes, so
the button is also the check: pressed on a set-up account it changes nothing
and says so. Our own Workers are the exception: their code is the
repository's, and a step redeploys one whose deployed code differs, which is
how a change to deploy/edge or deploy/mail reaches Cloudflare.

A setting already filled in on the form is never replaced. A step that finds
it empty writes what it found or made.
"""

import hashlib
import json
from pathlib import Path

import frappe
import requests
from frappe import _

from onedesk.one_admin import site

API = "https://api.cloudflare.com/client/v4"
TIMEOUT = 30

#: What is ours, by name. A second account, or a second environment on this
#: one, would change these, not the code.
KV_TITLE = "one-sites"
BUCKETS = {"Global": "one-global", "EU": "one-eu"}
ROUTER = "one-tenant-router"
MAILER = "one-mail"
#: A proxied record is never dialled: the Worker answers before the origin.
NOWHERE = "192.0.2.1"
DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
COMPATIBILITY = "2025-01-01"

#: Each step's verdict.
OURS, MADE, THEIRS, FAILED, WAITING = "ours", "created", "theirs", "failed", "needs attention"


class Setup:
	"""One run: what was found and made, step by step."""

	def __init__(self, token: str):
		self.token = token
		self.settings = frappe.get_doc("One Admin Settings")
		self.said: list[dict] = []
		self.account = None
		self.zone = None

	# ------------------------------------------------------------ the calls

	def call(self, method: str, path: str, **kwargs) -> dict:
		headers = {"Authorization": f"Bearer {self.token}", **kwargs.pop("headers", {})}
		answered = requests.request(method, f"{API}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
		try:
			body = answered.json()
		except ValueError:
			body = {"success": answered.ok, "result": None, "errors": [{"message": answered.text[:300]}]}
		if not body.get("success", answered.ok):
			raise Refused("; ".join(str(one.get("message")) for one in body.get("errors") or []) or answered.reason)
		return body

	def note(self, step: str, state: str, detail: str = "") -> None:
		self.said.append({"step": step, "state": state, "detail": detail})

	def keep(self, field: str, value) -> None:
		"""A setting is filled in once, and never replaced."""
		if value and not self.settings.get(field):
			self.settings.set(field, value)

	# ------------------------------------------------------------ the steps

	def run(self) -> list[dict]:
		for step in (
			self.find_account,
			self.find_zone,
			self.kv,
			self.buckets,
			self.r2_keys,
			self.router,
			self.mailer,
			self.mail_routing,
			self.catch_all,
			self.mail_sending,
		):
			try:
				step()
			except Refused as reason:
				self.note(step.__name__, FAILED, str(reason))
				if step in (self.find_account, self.find_zone):
					break
		self.settings.cloudflare_setup = json.dumps(self.said, indent=1)
		self.settings.flags.ignore_permissions = True
		self.settings.save()
		return self.said

	def find_account(self) -> None:
		accounts = self.call("GET", "/accounts")["result"]
		wanted = self.settings.cloudflare_account
		found = next((one for one in accounts if one["id"] == wanted), None) if wanted else None
		if not found:
			if len(accounts) != 1:
				raise Refused(_("The key reaches {0} accounts. Enter the Account ID to choose one.").format(len(accounts)))
			found = accounts[0]
		self.account = found["id"]
		self.keep("cloudflare_account", self.account)
		self.note("account", OURS, found["name"])

	def find_zone(self) -> None:
		"""The zone both domains are in: the workspace domain's, and the mail
		domain's, which must be the same one."""
		domain = self.settings.tenant_domain or "t.4dl.app"
		mail = self.settings.mail_domain or "m.4dl.app"
		zones = self.call("GET", "/zones", params={"per_page": 50})["result"]
		zone = next((one for one in zones if domain.endswith("." + one["name"]) or domain == one["name"]), None)
		if not zone:
			raise Refused(_("None of the key's zones holds {0}.").format(domain))
		if not (mail.endswith("." + zone["name"]) or mail == zone["name"]):
			raise Refused(_("{0} and {1} are not in one zone.").format(domain, mail))
		self.zone = zone
		self.keep("tenant_domain", domain)
		self.keep("mail_domain", mail)
		self.note("zone", OURS, zone["name"])

	def kv(self) -> None:
		if self.settings.cloudflare_kv:
			return self.note("kv", OURS, self.settings.cloudflare_kv)
		spaces = self.call("GET", f"/accounts/{self.account}/storage/kv/namespaces", params={"per_page": 100})["result"]
		found = next((one for one in spaces if one["title"] == KV_TITLE), None)
		if found:
			self.keep("cloudflare_kv", found["id"])
			return self.note("kv", OURS, KV_TITLE)
		made = self.call("POST", f"/accounts/{self.account}/storage/kv/namespaces", json={"title": KV_TITLE})["result"]
		self.keep("cloudflare_kv", made["id"])
		self.note("kv", MADE, KV_TITLE)

	def buckets(self) -> None:
		for jurisdiction, default in BUCKETS.items():
			field = "bucket_eu" if jurisdiction == "EU" else "bucket_global"
			name = self.settings.get(field) or default
			headers = {"cf-r2-jurisdiction": "eu"} if jurisdiction == "EU" else {}
			held = self.call("GET", f"/accounts/{self.account}/r2/buckets", headers=headers)["result"]
			if any(one["name"] == name for one in held.get("buckets", [])):
				self.note(f"bucket {jurisdiction}", OURS, name)
			else:
				self.call("POST", f"/accounts/{self.account}/r2/buckets", headers=headers, json={"name": name})
				self.note(f"bucket {jurisdiction}", MADE, name)
			self.keep(field, name)

	def r2_keys(self) -> None:
		"""R2's S3 keys are the token itself: its id, and the SHA-256 of its
		value. Nothing is created, and a rotated token rotates them."""
		if self.settings.r2_key_id:
			return self.note("r2 keys", OURS, _("already set"))
		verified = self.call("GET", "/user/tokens/verify")["result"]
		self.keep("r2_key_id", verified["id"])
		self.settings.r2_secret = hashlib.sha256(self.token.encode()).hexdigest()
		self.note("r2 keys", MADE, _("from the token"))

	def router(self) -> None:
		domain = self.settings.tenant_domain
		self.deploy(ROUTER, DEPLOY / "edge" / "worker.js", [self.kv_binding()])
		self.dns("A", f"*.{domain}", NOWHERE)
		self.route(f"*.{domain}/*", ROUTER)

	def mailer(self) -> None:
		bindings = [
			self.kv_binding(),
			{"type": "r2_bucket", "name": "FILES", "bucket_name": self.settings.bucket_global},
			{"type": "r2_bucket", "name": "FILES_EU", "bucket_name": self.settings.bucket_eu, "jurisdiction": "eu"},
			{"type": "plain_text", "name": "MAIL_DOMAIN", "text": self.settings.mail_domain},
		]
		self.deploy(MAILER, DEPLOY / "mail" / "worker.js", bindings)

	def mail_routing(self) -> None:
		"""Email Routing on the mail domain: Cloudflare adds and locks its MX
		and SPF records. Needs the key's Zone Settings: Edit."""
		mail = self.settings.mail_domain
		zone = self.zone["id"]
		try:
			held = self.call("GET", f"/zones/{zone}/email/routing/dns", params={"subdomain": mail})["result"]
		except Refused as reason:
			return self.note("mail routing", WAITING, _("{0}. The key needs Zone Settings: Edit.").format(reason))
		missing = [one for one in (held or {}).get("record", held or []) if isinstance(one, dict) and one.get("missing")]
		if held and not missing:
			return self.note("mail routing", OURS, mail)
		self.call("POST", f"/zones/{zone}/email/routing/dns", json={"name": mail})
		self.note("mail routing", MADE, mail)

	def catch_all(self) -> None:
		zone = self.zone["id"]
		held = self.call("GET", f"/zones/{zone}/email/routing/rules/catch_all")["result"] or {}
		actions = held.get("actions") or []
		if held.get("enabled") and actions and actions[0].get("type") == "worker" and actions[0].get("value") == [MAILER]:
			return self.note("catch-all", OURS, MAILER)
		self.call(
			"PUT",
			f"/zones/{zone}/email/routing/rules/catch_all",
			json={"matchers": [{"type": "all"}], "actions": [{"type": "worker", "value": [MAILER]}], "enabled": True},
		)
		self.note("catch-all", MADE, _("{0}, in place of what it held").format(MAILER))

	def mail_sending(self) -> None:
		mail = self.settings.mail_domain
		zone = self.zone["id"]
		held = self.call("GET", f"/zones/{zone}/email/sending/subdomains")["result"] or []
		found = next((one for one in held if one["name"] == mail), None)
		if found:
			return self.note("mail sending", OURS if found.get("enabled") else WAITING, mail)
		made = self.call("POST", f"/zones/{zone}/email/sending/subdomains", json={"name": mail})["result"]
		self.note("mail sending", MADE if made.get("enabled") else WAITING, mail)

	# ------------------------------------------------------------ helpers

	def kv_binding(self) -> dict:
		return {"type": "kv_namespace", "name": "SITES", "namespace_id": self.settings.cloudflare_kv}

	def deploy(self, name: str, path: Path, bindings: list[dict]) -> None:
		"""Upload our Worker if it is not there, or if the repository's code or
		bindings are not what is deployed."""
		code = path.read_text()
		wanted = hashlib.sha256((code + json.dumps(bindings, sort_keys=True)).encode()).hexdigest()
		held = json.loads(self.settings.cloudflare_deployed or "{}")
		scripts = self.call("GET", f"/accounts/{self.account}/workers/scripts")["result"]
		there = any(one["id"] == name for one in scripts)
		if there and held.get(name) == wanted:
			return self.note(f"worker {name}", OURS)
		metadata = {"main_module": "worker.js", "compatibility_date": COMPATIBILITY, "bindings": bindings}
		self.call(
			"PUT",
			f"/accounts/{self.account}/workers/scripts/{name}",
			files={
				"metadata": (None, json.dumps(metadata), "application/json"),
				"worker.js": ("worker.js", code, "application/javascript+module"),
			},
		)
		held[name] = wanted
		self.settings.cloudflare_deployed = json.dumps(held)
		self.note(f"worker {name}", OURS if there else MADE, _("deployed") if there else "")

	def dns(self, kind: str, name: str, content: str) -> None:
		zone = self.zone["id"]
		held = self.call("GET", f"/zones/{zone}/dns_records", params={"name": name})["result"]
		if not held:
			self.call(
				"POST", f"/zones/{zone}/dns_records", json={"type": kind, "name": name, "content": content, "proxied": True}
			)
			return self.note(f"dns {name}", MADE)
		mine = any(one["type"] == kind and one["content"] == content and one.get("proxied") for one in held)
		self.note(f"dns {name}", OURS if mine else THEIRS, "" if mine else _("left as it is"))

	def route(self, pattern: str, script: str) -> None:
		zone = self.zone["id"]
		held = self.call("GET", f"/zones/{zone}/workers/routes")["result"]
		found = next((one for one in held if one["pattern"] == pattern), None)
		if not found:
			self.call("POST", f"/zones/{zone}/workers/routes", json={"pattern": pattern, "script": script})
			return self.note(f"route {pattern}", MADE)
		self.note(f"route {pattern}", OURS if found.get("script") == script else THEIRS)


class Refused(Exception):
	pass


@frappe.whitelist(methods=["POST"])
def set_up() -> list[dict]:
	"""The button on One Admin Settings."""
	frappe.only_for(site.OPERATOR)
	site.require_admin()
	token = frappe.conf.get("cloudflare_token") or frappe.get_doc("One Admin Settings").get_password(
		"cloudflare_token", raise_exception=False
	)
	if not token:
		frappe.throw(_("Enter the Cloudflare API token first."))
	return Setup(token).run()
