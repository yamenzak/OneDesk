"""Cloudflare, set up from one master key: One's own tokens made from it, and
everything a workspace needs from Cloudflare found or made with them. It takes
nothing of anybody else's, running it twice is running it once, and a run cut
off anywhere loses nothing (AGENTS.md, under setup.py). A workspace's setup
wizard asks nothing for OneAdmin (STEPS)."""

import datetime
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import frappe
import requests
from frappe import _

from onedesk.one_admin import site, tell, vault

STEPS = []

API = "https://api.cloudflare.com/client/v4"
TIMEOUT = 30

KV_TITLE = "one-sites"
BUCKETS = {"Global": "one-global", "EU": "one-eu"}
# Help's pictures and clips, every environment's (one_admin/media.py).
DOCS_BUCKET = "one-docs"
ROUTER = "one-tenant-router"
MAILER = "one-mail"
OFFICE = "one-office"
OFFICE_IMAGE = "docker.io/gotenberg/gotenberg:8"
OFFICE_TYPE = "standard-1"
OFFICE_MOST = 2
DEPLOYED_AT = re.compile(r"https://[\w.-]+\.workers\.dev")
BACKUPS = "one-backups"
KEEPER = "one-keeper"
KEEPER_NEEDS = (("Workers R2 Storage Write", "Workers R2 Storage Edit"),)
WATCHER = "one-watch"
WATCHER_NEEDS = (("Email Sending*",),)
WATCHER_CRON = "*/5 * * * *"
RUN = "Setup"
RUN_NEEDS = (
	("Account Settings Read",),
	("Workers Scripts Write", "Workers Scripts Edit"),
	("Workers KV Storage Write", "Workers KV Storage Edit"),
	("Workers R2 Storage Write", "Workers R2 Storage Edit"),
	("AI Gateway Write", "AI Gateway Edit"),
	("Email Routing Addresses Write", "Email Routing Addresses Edit"),
	("Email Sending*",),
	("Zone Read",),
	("DNS Write", "DNS Edit"),
	("Workers Routes Write", "Workers Routes Edit"),
	("SSL and Certificates Write", "SSL and Certificates Edit"),
	("Zone Settings Write", "Zone Settings Edit"),
	("Email Routing Rules Write", "Email Routing Rules Edit"),
	("Workers Containers Write", "Workers Containers Edit"),
	("Cloudchamber Write", "Cloudchamber Edit"),
)
LOCKED_DAYS = 30
RECENT_DAYS = 7
DAILY_DAYS = 31
MONTHLY_DAYS = 366
A_DAY = 86400
NOWHERE = "192.0.2.1"
DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
COMPATIBILITY = "2025-01-01"
COMPATIBILITY_CONTAINERS = "2025-10-01"
GATEWAY = "one"

# One's own tokens: each one's settings field and the names Cloudflare may give
# each permission it needs (Write or Edit). A * name is any that starts so,
# left out quietly when there is none.
TOKENS = {
	"OneAdmin": (
		"cloudflare_token",
		(
			("Account Settings Read",),
			("Workers KV Storage Write", "Workers KV Storage Edit"),
			("Email Routing Addresses Write", "Email Routing Addresses Edit"),
			# Not named in Cloudflare's documentation: whichever it has.
			("Email Sending*",),
			("Zone Read",),
			("DNS Write", "DNS Edit"),
			("Workers Routes Write", "Workers Routes Edit"),
			("SSL and Certificates Write", "SSL and Certificates Edit"),
			("Zone Settings Write", "Zone Settings Edit"),
			("Email Routing Rules Write", "Email Routing Rules Edit"),
		),
	),
	"OneAdmin Storage": ("r2_secret", (("Workers R2 Storage Bucket Item Write",),)),
	"OneAI": (
		"ai_gateway_token",
		(
			("AI Gateway Run",),
			("Workers AI Read",),
		),
	),
}
ACCOUNT = "com.cloudflare.api.account"
ZONE = "com.cloudflare.api.account.zone"
BUCKET = "com.cloudflare.edge.r2.bucket"
# How long a run may hold the lock: one cut off frees it by itself.
LOCK = "one_cloudflare_setup"
LOCKED_FOR = 15 * 60

# Prompt injection (P1) and Llama Guard's hazards (S1-S13), flagged, never
# blocked: one_ai/reading/guard.py is what stops OneAI acting by itself.
FLAGGED = tuple(f"S{n}" for n in range(1, 14))
GUARDRAILS = {
	"prompt": {"P1": "FLAG", **dict.fromkeys(FLAGGED, "FLAG")},
	"response": dict.fromkeys(FLAGGED, "FLAG"),
}

OURS, MADE, THEIRS, FAILED, WAITING = "ours", "created", "theirs", "failed", "needs attention"


class Setup:
	"""One run: what was found and made, step by step, each saved as it is."""

	def __init__(self, master: str | None, signed_in: bool = False):
		self.master = master
		self.signed_in = signed_in
		self.token = None
		self.settings = frappe.get_doc("One Admin Settings")
		self.said: list[dict] = []
		self.account = self.settings.cloudflare_account or None
		self.zone = None
		self.mail_zone = None
		self.groups = None
		# Production leaves Environment empty. Any other environment on the
		# same account (dev) gets its own Workers, store, buckets, gateway and
		# tokens, each named after it, and must bring its own domains.
		self.env = (self.settings.get("environment") or "").strip().lower() or None
		self.kv_title = for_env(self.env, KV_TITLE)
		self.router_name = for_env(self.env, ROUTER)
		self.mailer_name = for_env(self.env, MAILER)

	def call(self, method: str, path: str, token: str | None = None, **kwargs) -> dict:
		"""A call to Cloudflare, with this run's own token unless another is
		named (AGENTS.md, Keys)."""
		headers = {"Authorization": f"Bearer {token or self.token}", **kwargs.pop("headers", {})}
		answered = requests.request(method, f"{API}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
		try:
			body = answered.json()
		except ValueError:
			body = {"success": answered.ok, "result": None, "errors": [{"message": answered.text[:300]}]}
		if not body.get("success", answered.ok):
			raise Refused("; ".join(str(one.get("message")) for one in body.get("errors") or []) or answered.reason)
		return body

	def patiently(self, method: str, path: str, **kwargs) -> dict:
		"""A call right after a token is made: Cloudflare's services take a
		few seconds to accept a new token, and say Authentication error
		until they do."""
		for wait in (2, 4, 8, 16, 0):
			try:
				return self.call(method, path, **kwargs)
			except Refused as refused:
				if "Authentication error" not in str(refused) or not wait:
					raise
				time.sleep(wait)

	def note(self, step: str, state: str, detail: str = "") -> None:
		self.said = [one for one in self.said if one["step"] != step]
		self.said.append({"step": step, "state": state, "detail": detail})
		frappe.db.set_single_value("One Admin Settings", "cloudflare_setup", json.dumps(self.said, indent=1))
		frappe.db.commit()
		frappe.publish_realtime("cloudflare_setup", {"said": self.said}, user=frappe.session.user)

	def keep(self, field: str, value) -> None:
		"""A setting is filled in once, never replaced, and saved at once."""
		if value and not self.settings.get(field):
			self.settings.set(field, value)
			frappe.db.set_single_value("One Admin Settings", field, value)
			frappe.db.commit()

	def own(self, field: str, value: str, secret: bool = True) -> None:
		"""What only this setup makes, One's tokens and R2 keys: replaced
		whenever it makes them anew, and saved before anything else is done."""
		if secret:
			vault.keep(field, value)
		else:
			self.settings.set(field, value)
			frappe.db.set_single_value("One Admin Settings", field, value)
		frappe.db.commit()

	def run(self) -> list[dict]:
		for step in (
			self.run_token,
			self.find_account,
			self.find_zone,
			self.kv,
			self.buckets,
			self.docs_media,
			self.tokens,
			self.router,
			self.certificate,
			self.custom_hostnames,
			self.mailer,
			self.mail_routing,
			self.catch_all,
			self.mail_sending,
			self.sender_sending,
			self.sender_account,
			self.ai_gateway,
			self.office,
			self.backups,
			self.keeper,
			self.watcher,
		):
			try:
				step()
			except Refused as reason:
				self.note(step.__name__, FAILED, str(reason))
				if step in (self.run_token, self.find_account, self.find_zone):
					break
			except requests.RequestException as reason:
				self.note(step.__name__, FAILED, _("Cloudflare did not answer: {0}. Set up again.").format(reason))
				break
		return self.said

	# One's tokens

	def permission_groups(self) -> list[dict]:
		if self.groups is None:
			self.groups = self.call("GET", "/user/tokens/permission_groups", token=self.master)["result"]
		return self.groups

	def held_tokens(self) -> list[dict]:
		found, page = [], 1
		while True:
			body = self.call("GET", "/user/tokens", token=self.master, params={"per_page": 50, "page": page})
			found += body["result"] or []
			info = body.get("result_info") or {}
			if page >= (info.get("total_pages") or 1):
				return found
			page += 1

	def verified(self, value: str | None) -> str | None:
		"""The id of the token a secret belongs to, or None when it is no
		token any more."""
		if not value:
			return None
		try:
			return self.call("GET", "/user/tokens/verify", token=value)["result"].get("id")
		except Refused:
			return None

	def ensure_token(self, name: str) -> str:
		"""One of One's tokens, found by its name or made, allowed what TOKENS
		says on what this setup has found so far. A token whose secret is not
		the one held, because a run was cut off between Cloudflare making it
		and us saving it, is rolled: the same token with a new secret, saved
		before anything else."""
		field, needs = TOKENS[name]
		called = token_for_env(self.env, name)
		groups = self.permission_groups()
		wanted, missing = policies(groups, needs, self.account, self.zone_ids(), self.buckets_held())
		tokens = self.held_tokens()
		# Production's tokens were first made with the bare name; found by it,
		# they are renamed below rather than made again.
		held = next((one for one in tokens if one["name"] == called), None) or (
			None if self.env else next((one for one in tokens if one["name"] == name), None)
		)
		value = vault.get(field)
		if name == "OneAdmin Storage":
			# Its secret is kept only as a hash, so it cannot be checked
			# against Cloudflare: held means the id matches and a secret is
			# kept. Either missing, the token is rolled and both are saved.
			kept = held and self.settings.r2_key_id == held["id"] and vault.get("r2_secret")
			value = "held" if kept else None
		state = OURS
		if not held:
			try:
				made = self.call("POST", "/user/tokens", token=self.master, json={"name": called, "policies": wanted})["result"]
			except Refused as refused:
				asked = {one["id"] for policy in wanted for one in policy["permission_groups"]}
				raise Refused(f"{refused} ({', '.join(one['name'] for one in groups if one['id'] in asked)})") from refused
			held, value, state = made, made["value"], MADE
			self.store(name, made["id"], value)
		else:
			if name != "OneAdmin Storage" and self.verified(value) != held["id"]:
				value = None
			if not value:
				value = self.call("PUT", f"/user/tokens/{held['id']}/value", token=self.master, json={})["result"]
				self.store(name, held["id"], value)
				state = MADE
			if not same(held.get("policies") or [], wanted) or held.get("status") != "active" or held.get("name") != called:
				self.call("PUT", f"/user/tokens/{held['id']}", token=self.master, json={"name": called, "policies": wanted, "status": "active"})
		detail = _("missing permissions: {0}").format(", ".join(missing)) if missing else called
		self.note(f"token {name}", WAITING if missing else state, detail)
		return value

	def zone_ids(self) -> list[str]:
		"""The zones found so far, the workspace domain's and the mail
		domain's, once each."""
		return list(dict.fromkeys(one["id"] for one in (self.zone, self.mail_zone) if one))

	def store(self, name: str, ident: str, value: str) -> None:
		field = TOKENS[name][0]
		if name == "OneAdmin Storage":
			# R2's S3 keys are the token: its id, and the SHA-256 of its secret.
			self.own("r2_key_id", ident, secret=False)
			self.own("r2_secret", hashlib.sha256(value.encode()).hexdigest())
		else:
			self.own(field, value)

	def buckets_held(self) -> list[tuple[str, str]]:
		"""The buckets the storage token may write: the workspaces' two, and
		Help's pictures (one_admin/media.py) once there are those."""
		held = [
			("eu" if field == "bucket_eu" else "default", self.settings.get(field))
			for field in ("bucket_global", "bucket_eu")
			if self.settings.get(field)
		]
		return held + [("default", DOCS_BUCKET)] if held else held

	def run_token(self) -> None:
		"""The token this run works with, made from the master key: allowed
		what a run makes and changes (Workers, buckets and their locks, the
		gateway, containers), for an hour, on any account and zone, and
		deleted when the run ends (`end`). OneAdmin's own token is never given
		these (AGENTS.md, Keys). A run from Sign In to Cloudflare works with the
		sign-in's own token instead."""
		if self.signed_in:
			self.token = self.master
			return self.note("sign-in", OURS, _("Signed in to Cloudflare for this run."))
		called = token_for_env(self.env, RUN)
		for stale in (one for one in self.held_tokens() if one["name"] == called):
			self.call("DELETE", f"/user/tokens/{stale['id']}", token=self.master)
		wanted, _missing = policies(self.permission_groups(), RUN_NEEDS, None, None, [])
		until = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
		made = self.call("POST", "/user/tokens", token=self.master, json={"name": called, "policies": wanted, "expires_on": until})["result"]
		self.run_id, self.token = made["id"], made["value"]
		for _try in range(5):
			if self.verified(self.token):
				return
			time.sleep(1)
		raise Refused(_("The setup token was made but Cloudflare does not accept it yet. Set up again."))

	def end(self) -> None:
		"""The run's own token deleted, whatever happened."""
		if getattr(self, "run_id", None):
			try:
				self.call("DELETE", f"/user/tokens/{self.run_id}", token=self.master)
			except (Refused, requests.RequestException):
				pass
			self.run_id = None

	def tokens(self) -> None:
		"""One's own tokens, each allowed only its own work on what was
		found: the account, the zone and the two buckets."""
		self.ensure_token("OneAdmin")
		if self.buckets_held():
			self.ensure_token("OneAdmin Storage")
		self.ensure_token("OneAI")

	def find_account(self) -> None:
		accounts = self.call("GET", "/accounts")["result"]
		wanted = self.settings.cloudflare_account
		found = next((one for one in accounts if one["id"] == wanted), None) if wanted else None
		if not found:
			if len(accounts) != 1:
				raise Refused(_("The token has access to {0} accounts. Enter the Account ID.").format(len(accounts)))
			found = accounts[0]
		self.account = found["id"]
		if wanted != self.account:
			# what was typed named no account the token reaches (a browser can fill an email in)
			self.settings.set("cloudflare_account", None)
		self.keep("cloudflare_account", self.account)
		self.note("account", OURS, found["name"])

	def find_zone(self) -> None:
		"""The workspace domain's zone and the mail domain's, which may be
		another one: Email Routing's catch-all belongs to a whole zone, so an
		environment sharing production's zone takes its mail elsewhere. Only
		production has the defaults; any other environment names its own."""
		domain = self.settings.tenant_domain or (None if self.env else "t.4dl.app")
		mail = self.settings.mail_domain or (None if self.env else "m.4dl.app")
		if not (domain and mail):
			raise Refused(_("Enter the workspace and mail domains for {0}.").format(self.env))
		zones = self.call("GET", "/zones", params={"per_page": 50})["result"]
		zone, mail_zone = within(zones, domain), within(zones, mail)
		for found, name in ((zone, domain), (mail_zone, mail)):
			if not found:
				raise Refused(_("The token has no zone for {0}.").format(name))
		self.zone, self.mail_zone = zone, mail_zone
		self.keep("cloudflare_zone", zone["id"])
		self.keep("tenant_domain", domain)
		self.keep("mail_domain", mail)
		self.note("zone", OURS, zone["name"] if zone is mail_zone else f"{zone['name']}, {mail_zone['name']}")

	def kv(self) -> None:
		if self.settings.cloudflare_kv:
			return self.note("kv", OURS, self.settings.cloudflare_kv)
		spaces = self.patiently("GET", f"/accounts/{self.account}/storage/kv/namespaces", params={"per_page": 100})["result"]
		found = next((one for one in spaces if one["title"] == self.kv_title), None)
		if found:
			self.keep("cloudflare_kv", found["id"])
			return self.note("kv", OURS, self.kv_title)
		made = self.call("POST", f"/accounts/{self.account}/storage/kv/namespaces", json={"title": self.kv_title})["result"]
		self.keep("cloudflare_kv", made["id"])
		self.note("kv", MADE, self.kv_title)

	def buckets(self) -> None:
		for jurisdiction, default in BUCKETS.items():
			field = "bucket_eu" if jurisdiction == "EU" else "bucket_global"
			name = self.settings.get(field) or for_env(self.env, default)
			headers = {"cf-r2-jurisdiction": "eu"} if jurisdiction == "EU" else {}
			held = self.call("GET", f"/accounts/{self.account}/r2/buckets", headers=headers)["result"]
			if any(one["name"] == name for one in held.get("buckets", [])):
				self.note(f"bucket {jurisdiction}", OURS, name)
			else:
				self.call("POST", f"/accounts/{self.account}/r2/buckets", headers=headers, json={"name": name})
				self.note(f"bucket {jurisdiction}", MADE, name)
			self.keep(field, name)

	def docs_media(self) -> None:
		"""Help's pictures and clips: a bucket of their own, shared by every
		environment and holding nothing else, public on media.<zone>
		(one/media.py). A workspace's bucket is never made public."""
		held = self.call("GET", f"/accounts/{self.account}/r2/buckets")["result"]
		if any(one["name"] == DOCS_BUCKET for one in held.get("buckets", [])):
			self.note("bucket docs", OURS, DOCS_BUCKET)
		else:
			self.call("POST", f"/accounts/{self.account}/r2/buckets", json={"name": DOCS_BUCKET})
			self.note("bucket docs", MADE, DOCS_BUCKET)
		domain = f"media.{self.zone['name']}"
		path = f"/accounts/{self.account}/r2/buckets/{DOCS_BUCKET}/domains/custom"
		domains = self.call("GET", path)["result"].get("domains", [])
		if any(one.get("domain") == domain for one in domains):
			return self.note(f"domain {domain}", OURS)
		self.call("POST", path, json={"domain": domain, "zoneId": self.zone["id"], "enabled": True, "minTLS": "1.2"})
		self.note(f"domain {domain}", MADE)

	def router(self) -> None:
		if not self.settings.cloudflare_kv:
			return self.note("router", WAITING, _("Needs the KV namespace first."))
		domain = self.settings.tenant_domain
		bindings = [self.kv_binding(), {"type": "plain_text", "name": "TENANT_DOMAIN", "text": domain}]
		self.deploy(self.router_name, DEPLOY / "edge" / "worker.js", bindings)
		self.dns("A", f"*.{domain}", NOWHERE)
		self.route(f"*.{domain}/*", self.router_name)

	def certificate(self) -> None:
		"""The certificate for `*.t.4dl.app`, which the zone's free one does not
		cover: an Advanced Certificate Manager pack, ordered once, naming the
		zone's apex too as Cloudflare requires. A pack that already names both,
		issued or on its way, is kept. Needs ACM enabled on the zone, a paid
		add-on, and SSL and Certificates: Edit."""
		domain = self.settings.tenant_domain
		wanted = {domain, f"*.{domain}"}
		zone = self.zone["id"]
		held = self.call("GET", f"/zones/{zone}/ssl/certificate_packs", params={"status": "all"})["result"] or []
		found = next((one for one in held if wanted <= set(one.get("hosts") or [])), None)
		if found:
			return self.note("certificate", OURS if found.get("status") == "active" else WAITING, found.get("status") or "")
		if not acm(self.quota(zone)):
			return self.note(
				"certificate", WAITING, _("Turn on Advanced Certificate Manager for {0} in Cloudflare, then set up again.").format(self.zone["name"])
			)
		try:
			made = self.call(
				"POST",
				f"/zones/{zone}/ssl/certificate_packs/order",
				json={
					"type": "advanced",
					"hosts": sorted(wanted | {self.zone["name"]}),
					"validation_method": "txt",
					"validity_days": 90,
					"certificate_authority": "lets_encrypt",
				},
			)["result"] or {}
		except Refused as reason:
			return self.note(
				"certificate", WAITING, _("{0}. Enable Advanced Certificate Manager on the zone, then set up again.").format(reason)
			)
		self.note("certificate", MADE, made.get("status") or "")

	def quota(self, zone: str) -> dict | None:
		try:
			return self.call("GET", f"/zones/{zone}/ssl/certificate_packs/quota")["result"]
		except Refused:
			return None

	def custom_hostnames(self) -> None:
		"""Cloudflare for SaaS on the zone, for customers' own domains
		(domains.py). A custom hostname needs a fallback origin on the zone
		before it works; each one gets its own route to the router, so the
		origin is never actually dialled. One the zone already has is kept:
		another product on the zone may be using it."""
		zone = self.zone["id"]
		try:
			self.call("GET", f"/zones/{zone}/custom_hostnames", params={"per_page": 1})
		except Refused as reason:
			return self.note(
				"custom hostnames", WAITING, _("{0}. The OneAdmin token needs SSL and Certificates: Edit on the zone.").format(reason)
			)
		try:
			held = self.call("GET", f"/zones/{zone}/custom_hostnames/fallback_origin").get("result") or {}
		except Refused:
			held = {}
		if held.get("origin"):
			return self.note("fallback origin", OURS if held["origin"] == self.fallback() else THEIRS, held["origin"])
		self.dns("A", self.fallback(), NOWHERE)
		self.call("PUT", f"/zones/{zone}/custom_hostnames/fallback_origin", json={"origin": self.fallback()})
		self.note("fallback origin", MADE, self.fallback())

	def fallback(self) -> str:
		return f"fallback.{self.settings.tenant_domain}"

	def mailer(self) -> None:
		if not self.settings.cloudflare_kv:
			return self.note("mailer", WAITING, _("Needs the KV namespace first."))
		bindings = [
			self.kv_binding(),
			{"type": "r2_bucket", "name": "FILES", "bucket_name": self.settings.bucket_global},
			{"type": "r2_bucket", "name": "FILES_EU", "bucket_name": self.settings.bucket_eu, "jurisdiction": "eu"},
			{"type": "plain_text", "name": "MAIL_DOMAIN", "text": self.settings.mail_domain},
		]
		self.deploy(self.mailer_name, DEPLOY / "mail" / "worker.js", bindings)

	def mail_routing(self) -> None:
		"""Email Routing on the mail domain: Cloudflare adds and locks its MX
		and SPF records. Needs the key's Zone Settings: Edit."""
		mail = self.settings.mail_domain
		zone = self.mail_zone["id"]
		try:
			held = self.call("GET", f"/zones/{zone}/email/routing/dns", params={"subdomain": mail})["result"]
		except Refused as reason:
			return self.note("mail routing", WAITING, _("{0}. The OneAdmin token needs Zone Settings: Edit.").format(reason))
		missing = [one for one in (held or {}).get("record", held or []) if isinstance(one, dict) and one.get("missing")]
		if held and not missing:
			return self.note("mail routing", OURS, mail)
		self.call("POST", f"/zones/{zone}/email/routing/dns", json={"name": mail})
		self.note("mail routing", MADE, mail)

	def catch_all(self) -> None:
		"""The mail zone's catch-all, to our mail Worker. One that already
		hands mail to another Worker is left as it is: on a zone two
		environments share, it is the other one's."""
		zone = self.mail_zone["id"]
		mailer = self.mailer_name
		held = self.call("GET", f"/zones/{zone}/email/routing/rules/catch_all")["result"] or {}
		actions = held.get("actions") or []
		if held.get("enabled") and actions and actions[0].get("type") == "worker":
			if actions[0].get("value") == [mailer]:
				return self.note("catch-all", OURS, mailer)
			return self.note("catch-all", THEIRS, _("left to {0}").format(", ".join(actions[0].get("value") or [])))
		self.call(
			"PUT",
			f"/zones/{zone}/email/routing/rules/catch_all",
			json={"matchers": [{"type": "all"}], "actions": [{"type": "worker", "value": [mailer]}], "enabled": True},
		)
		self.note("catch-all", MADE, _("{0}, replacing the previous rule").format(mailer))

	def mail_sending(self) -> None:
		mail = self.settings.mail_domain
		zone = self.mail_zone["id"]
		held = self.call("GET", f"/zones/{zone}/email/sending/subdomains")["result"] or []
		found = next((one for one in held if one["name"] == mail), None)
		if found:
			return self.note("mail sending", OURS if found.get("enabled") else WAITING, mail)
		made = self.call("POST", f"/zones/{zone}/email/sending/subdomains", json={"name": mail})["result"]
		self.note("mail sending", MADE if made.get("enabled") else WAITING, mail)

	def sender_sending(self) -> None:
		"""Sending for the domain One's own mails come from (Sender Email), the
		way mail_sending does it for the mail domain. Nothing to do when the
		sender is on the mail domain itself."""
		sender = self.sender()
		self.keep("sender_email", sender)
		domain = sender.rpartition("@")[2]
		if domain == self.settings.mail_domain:
			return self.note("sender", OURS, _("{0}, on the mail domain").format(sender))
		zone = within([one for one in (self.zone, self.mail_zone) if one], domain)
		if not zone:
			raise Refused(_("{0} is not in the zone {1}.").format(domain, self.mail_zone["name"]))
		held = self.call("GET", f"/zones/{zone['id']}/email/sending/subdomains")["result"] or []
		found = next((one for one in held if one["name"] == domain), None)
		if found:
			return self.note("sender", OURS if found.get("enabled") else WAITING, sender)
		made = self.call("POST", f"/zones/{zone['id']}/email/sending/subdomains", json={"name": domain})["result"]
		self.note("sender", MADE if made.get("enabled") else WAITING, sender)

	def sender_account(self) -> None:
		"""The admin site's own outgoing account, as the sender: frappe's
		queue sends from it, and outbound.deliver hands it to Cloudflare
		(mailing.send_ours). It becomes the default, so no mail of ours goes
		out from a workspace's address."""
		sender = self.sender()
		name = frappe.db.get_value("Email Account", {"email_id": sender})
		held = frappe.get_doc("Email Account", name) if name else frappe.new_doc("Email Account")
		held.update(
			{
				"email_account_name": held.email_account_name or "One",
				"email_id": sender,
				"enable_incoming": 0,
				"enable_outgoing": 1,
				"default_outgoing": 1,
				"smtp_server": sender.rpartition("@")[2],
				"no_smtp_authentication": 1,
				"always_use_account_email_id_as_sender": 1,
				"always_use_account_name_as_sender_name": 1,
			}
		)
		held.flags.ignore_permissions = True
		held.save()
		for other in frappe.get_all(
			"Email Account", filters={"default_outgoing": 1, "name": ["!=", held.name]}, pluck="name"
		):
			frappe.db.set_value("Email Account", other, "default_outgoing", 0)
		self.note("sender account", OURS if name else MADE, sender)

	def sender(self) -> str:
		"""Sender Email, with production's default; any other environment
		names its own."""
		sender = (self.settings.sender_email or ("" if self.env else "noreply@4dl.app")).strip().lower()
		if not sender:
			raise Refused(_("Enter the Sender Email for {0}.").format(self.env))
		return sender

	def ai_gateway(self) -> None:
		"""The AI gateway OneAI calls through, found or made, with Guardrails
		on. What it already holds (caching, rate limits, spend limits) is kept;
		only its logs and its Guardrails are set. OneAI calls it with the OneAI
		token tokens() makes."""
		name = self.settings.ai_gateway or for_env(self.env, GATEWAY)
		base = f"/accounts/{self.account}/ai-gateway/gateways"
		try:
			held = self.call("GET", f"{base}/{name}")["result"]
		except Refused:
			held = None
		if not held:
			self.call("POST", base, json=guarded({"id": name}))
			self.note("ai gateway", MADE, name)
		else:
			self.note("ai gateway", OURS, name)
		self.call("PUT", f"{base}/{name}", json=guarded(held or {}))
		self.keep("ai_gateway", name)

	def backups(self) -> None:
		"""The backup bucket (deploy/keeper/README.md): every object in it
		locked for `LOCKED_DAYS`, `recent/` gone after `RECENT_DAYS`, `daily/`
		after `DAILY_DAYS` and `monthly/` after `MONTHLY_DAYS`. The lock wins
		over a lifecycle rule, so `recent/` really goes at `LOCKED_DAYS`. Both
		kinds of rule are set on every run, so a lock somebody lifted comes
		back."""
		name = self.settings.get("backup_bucket") or for_env(self.env, BACKUPS)
		base = f"/accounts/{self.account}/r2/buckets"
		held = self.call("GET", base)["result"]
		if any(one["name"] == name for one in held.get("buckets", [])):
			self.note("bucket backups", OURS, name)
		else:
			self.call("POST", base, json={"name": name})
			self.note("bucket backups", MADE, name)
		self.keep("backup_bucket", name)
		self.call("PUT", f"{base}/{name}/lock", json={"rules": [{"id": "one-kept", "enabled": True, "prefix": "", "condition": {"type": "Age", "maxAgeSeconds": LOCKED_DAYS * A_DAY}}]})
		self.call(
			"PUT",
			f"{base}/{name}/lifecycle",
			json={
				"rules": [
					{"id": f"one-{prefix}", "enabled": True, "conditions": {"prefix": f"{prefix}/"}, "deleteObjectsTransition": {"condition": {"type": "Age", "maxAge": days * A_DAY}}}
					for prefix, days in (("recent", RECENT_DAYS), ("daily", DAILY_DAYS), ("monthly", MONTHLY_DAYS), ("config", DAILY_DAYS))
				]
			},
		)
		self.note("backup lock", OURS, _("{0} days").format(LOCKED_DAYS))

	def keeper_token(self) -> str:
		"""The Keeper token, which may make R2's temporary credentials (and
		so could lift a lock): made or rolled for a new secret on every run,
		and given only to the keeper Worker, never kept here."""
		return self.rolled_token("Keeper", KEEPER_NEEDS)

	def rolled_token(self, name: str, needs: tuple) -> str:
		"""A token given to one Worker and never kept here: made, or rolled
		for a new secret on every run."""
		called = token_for_env(self.env, name)
		wanted, missing = policies(self.permission_groups(), needs, self.account, self.zone_ids(), self.buckets_held())
		if missing:
			raise Refused(_("missing permissions: {0}").format(", ".join(missing)))
		held = next((one for one in self.held_tokens() if one["name"] == called), None)
		if not held:
			return self.call("POST", "/user/tokens", token=self.master, json={"name": called, "policies": wanted})["result"]["value"]
		if not same(held.get("policies") or [], wanted) or held.get("status") != "active":
			self.call("PUT", f"/user/tokens/{held['id']}", token=self.master, json={"name": called, "policies": wanted, "status": "active"})
		return self.call("PUT", f"/user/tokens/{held['id']}/value", token=self.master, json={})["result"]

	def keeper(self) -> None:
		"""The keeper Worker (deploy/keeper): the only way into the backup
		bucket, adding and reading, never deleting, and the maker of the
		search index's temporary credentials. Deployed on every run, with
		the Keeper token rolled."""
		bucket, files, files_eu = self.settings.get("backup_bucket"), self.settings.bucket_global, self.settings.bucket_eu
		key_id = self.settings.r2_key_id
		if not (bucket and files and files_eu and key_id):
			return self.note("keeper", WAITING, _("Needs the buckets and the storage token first."))
		name = for_env(self.env, KEEPER)
		secret = vault.get("keeper_secret") or secrets.token_urlsafe(32)
		bindings = [
			{"type": "r2_bucket", "name": "BACKUPS", "bucket_name": bucket},
			{"type": "r2_bucket", "name": "FILES", "bucket_name": files},
			{"type": "r2_bucket", "name": "FILES_EU", "bucket_name": files_eu, "jurisdiction": "eu"},
			{**self.kv_binding()},
			{"type": "plain_text", "name": "ACCOUNT", "text": self.account},
			{"type": "plain_text", "name": "PARENT_KEY", "text": key_id},
			{"type": "plain_text", "name": "TENANT_BUCKETS", "text": json.dumps([files, files_eu])},
			{"type": "plain_text", "name": "EU_BUCKET", "text": files_eu},
			{"type": "secret_text", "name": "ONE_SECRET", "text": secret},
			{"type": "secret_text", "name": "R2_TOKEN", "text": self.keeper_token()},
		]
		metadata = {"main_module": "worker.js", "compatibility_date": COMPATIBILITY, "bindings": bindings}
		code = (DEPLOY / "keeper" / "worker.js").read_text()
		self.call(
			"PUT",
			f"/accounts/{self.account}/workers/scripts/{name}",
			files={"metadata": (None, json.dumps(metadata), "application/json"), "worker.js": ("worker.js", code, "application/javascript+module")},
		)
		self.call("POST", f"/accounts/{self.account}/workers/scripts/{name}/subdomain", json={"enabled": True})
		subdomain = self.call("GET", f"/accounts/{self.account}/workers/subdomain")["result"]["subdomain"]
		vault.keep("keeper_secret", secret)
		self.own("keeper_url", f"https://{name}.{subdomain}.workers.dev", secret=False)
		self.note(f"worker {name}", MADE, _("deployed"))

	def watcher(self) -> None:
		"""The outside watcher (deploy/watch): a Worker on a cron asking
		whether this site answers, and mailing the operators when it stops.
		It runs on Cloudflare, so it still works with this site down. Deployed
		on every run, with its mail token rolled."""
		if not self.settings.cloudflare_kv:
			return self.note("watcher", WAITING, _("Needs the KV namespace first."))
		operators = tell.operators()
		if not operators:
			return self.note("watcher", WAITING, _("Needs an operator to tell."))
		name = for_env(self.env, WATCHER)
		bindings = [
			self.kv_binding(),
			{"type": "plain_text", "name": "ACCOUNT", "text": self.account},
			{"type": "plain_text", "name": "ADMIN_URL", "text": frappe.utils.get_url().rstrip("/")},
			{"type": "plain_text", "name": "OPERATORS", "text": json.dumps(operators)},
			{"type": "plain_text", "name": "SENDER", "text": self.sender()},
			{"type": "secret_text", "name": "MAIL_TOKEN", "text": self.rolled_token("Watch", WATCHER_NEEDS)},
		]
		metadata = {"main_module": "worker.js", "compatibility_date": COMPATIBILITY, "bindings": bindings}
		code = (DEPLOY / "watch" / "worker.js").read_text()
		self.call(
			"PUT",
			f"/accounts/{self.account}/workers/scripts/{name}",
			files={"metadata": (None, json.dumps(metadata), "application/json"), "worker.js": ("worker.js", code, "application/javascript+module")},
		)
		self.call("PUT", f"/accounts/{self.account}/workers/scripts/{name}/schedules", json=[{"cron": WATCHER_CRON}])
		self.note(f"worker {name}", MADE, _("deployed"))

	def office(self) -> None:
		"""One's office containers (deploy/office): deployed with wrangler,
		which hands Cloudflare the image to pull, then its secret put, and
		both kept in the settings. Done again only when the code or the
		image changes."""
		name = for_env(self.env, OFFICE)
		source = DEPLOY / "office"
		wanted = hashlib.sha256(
			"".join((source / one).read_text() for one in ("worker.js", "package.json")).encode() + f"{OFFICE_IMAGE}{OFFICE_TYPE}{OFFICE_MOST}".encode()
		).hexdigest()
		held = json.loads(self.settings.cloudflare_deployed or "{}")
		secret = vault.get("office_secret")
		if held.get(name) == wanted and self.settings.office_url and secret:
			return self.note(f"office {name}", OURS)
		secret = secret or secrets.token_urlsafe(32)
		said = self.wrangle(name, source, secret)
		found = DEPLOYED_AT.search(said)
		if not found:
			raise Refused(_("wrangler did not say where {0} is").format(name))
		self.own("office_secret", secret)
		self.own("office_url", found[0], secret=False)
		held[name] = wanted
		self.own("cloudflare_deployed", json.dumps(held), secret=False)
		self.note(f"office {name}", MADE, found[0])

	def wrangle(self, name: str, source: Path, secret: str) -> str:
		"""npm install and wrangler deploy in a room of its own, as OneAdmin's
		token: what wrangler said."""
		config = {
			"name": name,
			"main": "worker.js",
			"compatibility_date": COMPATIBILITY_CONTAINERS,
			"containers": [{"class_name": "Office", "image": OFFICE_IMAGE, "instance_type": OFFICE_TYPE, "max_instances": OFFICE_MOST}],
			"durable_objects": {"bindings": [{"name": "OFFICE", "class_name": "Office"}]},
			"migrations": [{"tag": "v1", "new_sqlite_classes": ["Office"]}],
			"observability": {"enabled": True},
		}
		env = {**os.environ, "CLOUDFLARE_API_TOKEN": self.token, "CLOUDFLARE_ACCOUNT_ID": self.account, "WRANGLER_SEND_METRICS": "false", "CI": "1"}
		with tempfile.TemporaryDirectory() as room:
			for one in ("worker.js", "package.json"):
				shutil.copy(source / one, room)
			Path(room, "wrangler.jsonc").write_text(json.dumps(config, indent=1))
			try:
				subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=room, env=env, check=True, capture_output=True, text=True, timeout=600)
				deployed = subprocess.run(["npx", "wrangler", "deploy"], cwd=room, env=env, check=True, capture_output=True, text=True, timeout=900)
				subprocess.run(["npx", "wrangler", "secret", "put", "ONE_SECRET"], cwd=room, env=env, input=secret, check=True, capture_output=True, text=True, timeout=300)
			except FileNotFoundError as missing:
				raise Refused(_("Node is not on this server: {0}").format(missing)) from missing
			except subprocess.TimeoutExpired as slow:
				raise Refused(_("wrangler took too long: {0}").format(slow.cmd[1])) from slow
			except subprocess.CalledProcessError as failed:
				raise Refused(((failed.stderr or "") + (failed.stdout or "")).strip()[-600:]) from failed
		return deployed.stdout + deployed.stderr

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
		self.own("cloudflare_deployed", json.dumps(held), secret=False)
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
		self.note(f"dns {name}", OURS if mine else THEIRS, "" if mine else _("unchanged"))

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


def guarded(held: dict) -> dict:
	"""The gateway as One sets it: what it holds, with the fields Cloudflare
	requires filled where it has none, logs of counts and costs kept, and
	Guardrails flagging. Pure."""
	body = {
		"cache_invalidate_on_update": False,
		"cache_ttl": 0,
		"rate_limiting_interval": 0,
		"rate_limiting_limit": 0,
		"rate_limiting_technique": "fixed",
	}
	body.update({key: value for key, value in held.items() if key in body or key in KEPT})
	body["collect_logs"] = True
	body["guardrails"] = GUARDRAILS
	return body


# What a gateway already holds that One leaves as it is.
KEPT = ("id", "authentication", "spend_limits", "retry_backoff", "retry_delay", "retry_max_attempts", "log_management", "log_management_strategy", "byok_only", "zdr")


def for_env(env: str | None, name: str) -> str:
	"""What Set Up Cloudflare calls a thing it makes: the name itself in
	production, the name and the environment anywhere else. Pure."""
	return f"{name}-{env}" if env else name


def token_for_env(env: str | None, name: str) -> str:
	"""One of One's tokens as Cloudflare lists it: the environment first, in
	brackets, so a token setup made reads apart from a person's own. Pure."""
	return f"[one-{env or 'prod'}] {name}"


def within(zones: list[dict], domain: str) -> dict | None:
	"""The zone a domain is in, or None. Pure."""
	return next((one for one in zones if domain == one["name"] or domain.endswith("." + one["name"])), None)


def policies(groups: list[dict], needs: tuple, account: str | None, zone, buckets: list) -> tuple[list[dict], list[str]]:
	"""A token's policies from the permissions it needs: each granted on the
	account, the zones (one, or the workspace's and the mail's) or the
	buckets, as its own scope says, and on all accounts or zones while which
	is not known yet. Also the needs Cloudflare has no permission for, by
	their first name. Pure."""
	zones = [zone] if isinstance(zone, str) else [one for one in zone or [] if one]
	where = {
		ACCOUNT: {f"{ACCOUNT}.{account}" if account else f"{ACCOUNT}.*": "*"},
		ZONE: {f"{ZONE}.{one}": "*" for one in zones} if zones else {f"{ZONE}.*": "*"},
		BUCKET: {f"{BUCKET}.{account}_{jurisdiction}_{name}": "*" for jurisdiction, name in buckets} if account else {},
	}
	granted: dict[str, list[str]] = {}
	missing = []
	for names in needs:
		group = next((one for name in names for one in groups if named(one["name"], name) and plain(one)), None)
		scope = group and next((one for one in (BUCKET, ZONE, ACCOUNT) if one in (group.get("scopes") or [])), None)
		if not scope:
			if not names[0].endswith("*"):
				missing.append(names[0])
			continue
		if where[scope]:
			granted.setdefault(scope, []).append(group["id"])
	made = [
		{"effect": "allow", "permission_groups": [{"id": one} for one in ids], "resources": where[scope]}
		for scope, ids in granted.items()
	]
	return made, missing


def plain(group: dict) -> bool:
	"""Whether a permission is one a user token may hold: granted on the
	account, a zone or a bucket and nothing narrower. Cloudflare also lists
	roles scoped to single resources, which a user token is refused. Pure."""
	scopes = set(group.get("scopes") or [])
	return bool(scopes) and scopes <= {ACCOUNT, ZONE, BUCKET}


def named(name: str, wanted: str) -> bool:
	"""Whether a permission is the one wanted: by its name, or for a name
	ending in *, any that starts so and is not only Read. Pure."""
	if wanted.endswith("*"):
		return name.startswith(wanted[:-1]) and not name.endswith("Read")
	return name == wanted


def same(held: list[dict], wanted: list[dict]) -> bool:
	"""Whether a token already allows what it should, whatever order
	Cloudflare keeps it in. Pure."""

	def shape(policies):
		return sorted(
			(sorted(one["id"] for one in policy.get("permission_groups") or []), json.dumps(policy.get("resources"), sort_keys=True))
			for policy in policies
			if policy.get("effect", "allow") == "allow"
		)

	return shape(held) == shape(wanted)


def acm(quota: dict | None) -> bool:
	"""Whether the zone may order an advanced certificate: Advanced
	Certificate Manager is on. Unknown counts as on, and the order says. Pure."""
	if quota is None:
		return True
	return bool((quota.get("advanced") or {}).get("allocated"))


@frappe.whitelist(methods=["POST"])
def set_up() -> dict:
	"""The button on One Admin Settings: one run at a time, in the background,
	so closing the page or losing the connection stops nothing."""
	frappe.only_for(site.OPERATOR)
	site.require_admin()
	if not master():
		frappe.throw(_("Enter the Cloudflare master token first."))
	frappe.enqueue(
		"onedesk.one_admin.setup.run",
		queue="long",
		timeout=LOCKED_FOR,
		job_id=LOCK,
		deduplicate=True,
		user=frappe.session.user,
	)
	return {"running": True}


def master() -> str | None:
	return vault.get(vault.MASTER)


def run(user: str | None = None, signed_in: bool = False) -> list[dict]:
	"""One Set Up Cloudflare, holding the lock while it runs. A run that dies
	frees the lock when it expires, and the next one carries on from what the
	last one saved. `signed_in` runs from Sign In to Cloudflare's token,
	revoked when the run ends."""
	if user:
		frappe.set_user(user)
	key = frappe.cache.make_key(LOCK)
	if not frappe.cache.set(key, 1, nx=True, ex=LOCKED_FOR):
		return []
	from onedesk.one_admin import cloudflare_signin

	token = cloudflare_signin.taken() if signed_in else master()
	held = Setup(token, signed_in=signed_in)
	try:
		said = held.run() if token else []
	finally:
		held.end()
		frappe.cache.delete(key)
		vault.forget_master()
		frappe.db.commit()
		if signed_in:
			cloudflare_signin.discard(token)
	frappe.publish_realtime("cloudflare_setup", {"said": said, "done": True}, user=frappe.session.user)
	return said
