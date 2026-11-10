"""OneAdmin's part of the integration suite (one_demo/check.py runs it). Its
records live on the admin site, so on a workspace each check stands in for
that site, reads back what it did and leaves nothing behind."""

import frappe

from onedesk.one_demo.check import check


@check
def oneadmin_a_code_installs_a_private_app_that_stays():
	"""The operator makes a code for a workspace; typed there (in any case,
	without its dashes) it queues one Install App job, and typing it again
	queues no second. The job checks the app is on the bench group, asks press
	to install it and waits until press lists it. A claimed app can't be
	offered again or taken off the record. A wrong code, or another
	workspace's, opens nothing; an app missing from the bench fails its job
	and leaves the workspace Live."""
	from unittest.mock import patch

	from onedesk.one_admin import press, private, runner

	app = "acme_fleet"
	installed: list = []
	asked: list = []

	def pressed(method, **kwargs):
		asked.append(method)
		if method == "press.api.site.installed_apps":
			return [{"app": one} for one in installed]
		if method == "press.api.site.install_app":
			installed.append(kwargs["app"])
		return None

	with patch("onedesk.one_admin.site.is_admin", return_value=True), patch("frappe.sendmail"), patch.object(press, "call", side_effect=pressed), patch.object(
		press, "apps", return_value=[{"name": app}]
	):
		for slug in ("acme-private", "other-private"):
			frappe.get_doc({"doctype": "Tenant", "slug": slug, "status": "Live", "jurisdiction": "Global", "site": f"{slug}.frappe.cloud", "bench": "bench-1"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Private App", "app": app, "title": "Acme Fleet", "said": "Acme's vans, drivers and routes."}).insert(ignore_permissions=True)
		code = private.new_code(app, "acme-private")
		assert len(private.normal(code)) == private.LENGTH and code.count("-") == 2, code
		for wrong in ("", "ABCD-EFGH-JKLM"):
			try:
				private.claim("acme-private", wrong)
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError(f"{wrong!r} opened an app")
		try:
			private.claim("other-private", code)
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("another workspace's code opened the app")
		said = private.claim("acme-private", code.lower().replace("-", " "), by="owner@acme.test")
		assert said["title"] == "Acme Fleet" and said["state"] == "Installing", said
		job = frappe.db.get_value("Private App Grant", {"tenant": "acme-private"}, "job")
		assert private.claim("acme-private", code)["state"] == "Installing"
		assert frappe.db.count("Provisioning Job", {"tenant": "acme-private", "kind": private.KIND}) == 1, "typed twice, queued twice"
		for _ in range(6):
			if runner.advance(job) in ("Done", "Failed"):
				break
		assert frappe.db.get_value("Provisioning Job", job, "status") == "Done", frappe.db.get_value("Provisioning Job", job, "error")
		assert installed == [app] and asked.count("press.api.site.install_app") == 1, asked
		assert private.mine("acme-private") == [{"app": app, "title": "Acme Fleet", "said": "Acme's vans, drivers and routes.", "icon": "", "state": "Installed"}]
		try:
			private.new_code(app, "acme-private")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a claimed app was offered again")
		doc = frappe.get_doc("Private App", app)
		doc.set("grants", [row for row in doc.grants if row.tenant != "acme-private"])
		try:
			doc.save(ignore_permissions=True)
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("an installed app came off the record")

		other = private.new_code(app, "other-private")
		with patch.object(press, "apps", return_value=[]):
			private.claim("other-private", other)
			job = frappe.db.get_value("Private App Grant", {"tenant": "other-private"}, "job")
			assert runner.advance(job) == "Failed"
		assert frappe.db.get_value("Tenant", "other-private", "status") == "Live", "a failed install took the workspace down"
		assert private.mine("other-private")[0]["state"] == "Failed"


class FakeCloudflare:
	"""Cloudflare's API as Set Up Cloudflare uses it, held in memory, which can
	be told to drop the connection once a given call has been done. Nothing
	here reaches Cloudflare."""

	GROUPS = tuple(
		{"id": f"g{n}", "name": name, "scopes": [scope]}
		for n, (name, scope) in enumerate(
			[
				("Account Settings Read", "com.cloudflare.api.account"),
				("Workers Scripts Write", "com.cloudflare.api.account"),
				("Workers KV Storage Write", "com.cloudflare.api.account"),
				("Workers R2 Storage Write", "com.cloudflare.api.account"),
				("AI Gateway Write", "com.cloudflare.api.account"),
				("AI Gateway Run", "com.cloudflare.api.account"),
				("Workers AI Read", "com.cloudflare.api.account"),
				("Email Routing Addresses Write", "com.cloudflare.api.account"),
				("Workers Containers Write", "com.cloudflare.api.account"),
				("Cloudchamber Write", "com.cloudflare.api.account"),
				("Zone Read", "com.cloudflare.api.account.zone"),
				("DNS Write", "com.cloudflare.api.account.zone"),
				("Workers Routes Write", "com.cloudflare.api.account.zone"),
				("SSL and Certificates Write", "com.cloudflare.api.account.zone"),
				("Zone Settings Write", "com.cloudflare.api.account.zone"),
				("Email Routing Rules Write", "com.cloudflare.api.account.zone"),
				("Workers R2 Storage Bucket Item Write", "com.cloudflare.edge.r2.bucket"),
			]
		)
	)

	def __init__(self):
		self.tokens: dict[str, dict] = {}
		self.made: list[str] = []
		self.kv: list[dict] = []
		self.buckets: dict[str, list] = {"": [], "eu": []}
		self.drop_after = None
		self.n = 0

	def answer(self, result=None, ok=True, status=200):
		from unittest.mock import Mock

		return Mock(ok=ok, status_code=status, reason="", json=lambda: {"success": ok, "result": result, "errors": [] if ok else [{"message": "refused"}], "result_info": {"total_pages": 1}})

	def __call__(self, method, url, headers=None, json=None, params=None, files=None, timeout=None):
		import requests

		path = url.split("/client/v4", 1)[1]
		bearer = (headers or {}).get("Authorization", "").removeprefix("Bearer ")
		self.n += 1
		said = self.handle(method, path, bearer, json or {}, headers or {})
		if self.drop_after and self.drop_after(method, path, json or {}):
			self.drop_after = None
			raise requests.ConnectionError("cut off")
		return said

	def handle(self, method, path, bearer, body, headers):
		if path.startswith("/user/tokens"):
			if path == "/user/tokens/verify":
				found = next((one for one in self.tokens.values() if one["value"] == bearer and one["status"] == "active"), None)
				return self.answer({"id": found["id"], "status": "active"}) if found else self.answer(ok=False, status=401)
			assert bearer == "MASTER", f"only the master token makes tokens: {path}"
			if path == "/user/tokens/permission_groups":
				return self.answer(list(self.GROUPS))
			if path == "/user/tokens" and method == "GET":
				return self.answer([{key: value for key, value in one.items() if key != "value"} for one in self.tokens.values()])
			if path == "/user/tokens" and method == "POST":
				self.counted = getattr(self, "counted", -1) + 1
				ident = f"t{self.counted}"
				self.tokens[ident] = {"id": ident, "name": body["name"], "policies": body["policies"], "status": "active", "value": f"secret-{ident}-1"}
				self.made.append(body["name"])
				return self.answer(self.tokens[ident])
			ident = path.split("/")[3]
			if method == "DELETE":
				self.tokens.pop(ident, None)
				return self.answer({"id": ident})
			if path.endswith("/value"):
				one = self.tokens[ident]
				one["value"] = f"secret-{ident}-{int(one['value'].rsplit('-', 1)[1]) + 1}"
				return self.answer(one["value"])
			self.tokens[ident].update(policies=body["policies"], status=body.get("status", "active"))
			return self.answer(self.tokens[ident])
		known = {one["value"] for one in self.tokens.values() if one["name"] == "[one-prod] Setup"}
		assert bearer in known, f"everything else runs with the run's own token: {path}"
		if path == "/accounts":
			return self.answer([{"id": "acc1", "name": "One"}])
		if path == "/zones":
			return self.answer([{"id": "zone1", "name": "4dl.app"}])
		if path.endswith("/storage/kv/namespaces"):
			if method == "POST":
				self.kv.append({"id": f"kv{len(self.kv)}", "title": body["title"]})
				return self.answer(self.kv[-1])
			return self.answer(self.kv)
		if path.endswith("/r2/buckets"):
			held = self.buckets["eu" if headers.get("cf-r2-jurisdiction") else ""]
			if method == "POST":
				held.append({"name": body["name"]})
			return self.answer({"buckets": held})
		if path.endswith("/domains/custom") and method == "GET":
			return self.answer({"domains": []})
		if path.endswith("/ssl/certificate_packs/quota"):
			return self.answer({"advanced": {"allocated": 0, "used": 0}})
		if "/ai-gateway/gateways/" in path and method == "GET":
			return self.answer(ok=False, status=404)
		if path.endswith("/lock") or path.endswith("/lifecycle"):
			self.rules = {**getattr(self, "rules", {}), path.rsplit("/", 1)[1]: body}
			return self.answer({})
		if path.endswith("/workers/subdomain"):
			return self.answer({"subdomain": "acc1"})
		if method == "GET":
			return self.answer([])
		return self.answer({"enabled": True, "id": "x"})


@check
def oneadmin_sets_up_cloudflare_from_a_master_token():
	"""Set Up Cloudflare makes One's own three tokens from the master one, each
	allowed only its work, and a run cut off anywhere loses nothing: a token
	made but never saved is rolled for a new secret, nothing is made twice,
	and the next run carries on (one_admin/setup.py). Cloudflare is stood in
	for: nothing leaves."""
	from unittest.mock import patch

	from onedesk.one_admin import setup, vault

	fake = FakeCloudflare()
	kept = {}
	settings = frappe.get_doc("One Admin Settings")
	was = {field: settings.get(field) for field in ("cloudflare_account", "cloudflare_zone", "cloudflare_kv", "bucket_global", "bucket_eu", "r2_key_id", "cloudflare_deployed", "cloudflare_setup", "ai_gateway", "office_url", "backup_bucket", "keeper_url")}
	for field in was:
		frappe.db.set_single_value("One Admin Settings", field, None)
	with patch("requests.request", side_effect=fake), patch.object(frappe.db, "commit"), patch("time.sleep"), patch.object(setup, "master", return_value="MASTER"), patch("frappe.publish_realtime"), patch.object(vault, "keep", side_effect=kept.__setitem__), patch.object(vault, "get", side_effect=kept.get), patch.object(vault, "forget_master") as forgot, patch.object(setup.Setup, "wrangle", return_value="Deployed https://one-office.acc1.workers.dev"):
		# Cut off right after Cloudflare made the OneAI token: its secret was never seen.
		fake.drop_after = lambda method, path, body: method == "POST" and path == "/user/tokens" and body.get("name") == "[one-prod] OneAI"
		first = setup.run()
		assert first[-1]["state"] == setup.FAILED and "did not answer" in first[-1]["detail"], first[-1]
		kv = frappe.db.get_single_value("One Admin Settings", "cloudflare_kv")
		assert kv and frappe.db.get_single_value("One Admin Settings", "cloudflare_account") == "acc1", "what was found is kept as it was found"

		second = setup.run()
		kept_tokens = [name for name in fake.made if name not in ("[one-prod] Setup",)]
		assert sorted(kept_tokens) == ["[one-prod] Keeper", "[one-prod] OneAI", "[one-prod] OneAdmin", "[one-prod] OneAdmin Storage"], f"each token made once: {fake.made}"
		assert not any(one["name"] == "[one-prod] Setup" for one in fake.tokens.values()), "the run's own token is deleted when it ends"
		runtime = next(one for one in fake.tokens.values() if one["name"] == "[one-prod] OneAdmin")
		given = {group["id"] for policy in runtime["policies"] for group in policy["permission_groups"]}
		mighty = {one["id"] for one in fake.GROUPS if one["name"] in ("Workers Scripts Write", "Workers R2 Storage Write", "Workers Containers Write", "Cloudchamber Write", "AI Gateway Write")}
		assert not given & mighty, "OneAdmin's own token can't deploy a Worker or change a bucket"
		assert fake.rules["lock"]["rules"][0]["condition"] == {"type": "Age", "maxAgeSeconds": setup.LOCKED_DAYS * setup.A_DAY}, "every backup is locked"
		assert kept["keeper_secret"] and frappe.db.get_single_value("One Admin Settings", "keeper_url") == "https://one-keeper.acc1.workers.dev"
		assert len(fake.kv) == 1 and frappe.db.get_single_value("One Admin Settings", "cloudflare_kv") == kv, "nothing is made twice"
		ai = next(one for one in fake.tokens.values() if one["name"] == "[one-prod] OneAI")
		held = kept["ai_gateway_token"]
		assert ai["value"] == held and held.endswith("-2"), "the token whose secret was lost is rolled, and the new one saved, in the config"
		assert forgot.called, "the master key is forgotten when a run ends"
		assert kept["office_secret"] and frappe.db.get_single_value("One Admin Settings", "office_url") == "https://one-office.acc1.workers.dev"
		admin = next(one for one in fake.tokens.values() if one["name"] == "[one-prod] OneAdmin")
		assert {key for policy in admin["policies"] for key in policy["resources"]} == {"com.cloudflare.api.account.acc1", "com.cloudflare.api.account.zone.zone1"}, "OneAdmin is narrowed to what was found"
		storage = next(one for one in fake.tokens.values() if one["name"] == "[one-prod] OneAdmin Storage")
		assert all(key.startswith("com.cloudflare.edge.r2.bucket.acc1_") for policy in storage["policies"] for key in policy["resources"])
		assert frappe.db.get_single_value("One Admin Settings", "r2_key_id") == storage["id"]
		steps = {one["step"]: one for one in second}
		assert steps["certificate"]["state"] == setup.WAITING and "Advanced Certificate Manager" in steps["certificate"]["detail"]
		assert "token OneAdmin" in steps and steps["token OneAdmin"]["state"] in (setup.OURS, setup.MADE)

		made = len(fake.tokens)
		setup.run()
		assert len(fake.tokens) == made and len(fake.kv) == 1, "a third run finds everything and makes nothing but its own token, gone again"
		assert next(one for one in fake.tokens.values() if one["name"] == "[one-prod] OneAI")["value"].endswith("-2"), "a held secret that works is not rolled"
	frappe.db.rollback()
	for field, value in was.items():
		frappe.db.set_single_value("One Admin Settings", field, value)


@check
def oneadmin_makes_its_first_operators():
	"""One has no desk to give a role from, so on the admin site the
	workspace's administrators become operators while there are none, and
	OneAdmin Settings adds and removes the rest, keeping the last
	(one_admin/site.py)."""
	from unittest.mock import patch

	from onedesk.one_admin import site

	with patch.object(site, "is_admin", return_value=True), patch.object(frappe.db, "commit"):
		frappe.db.delete("Has Role", {"role": site.OPERATOR, "parenttype": "User"})
		site.first_operators()
		from onedesk.one import roles

		managers = set(roles.administrators())
		assert managers and set(site._operators()) == managers, "every workspace administrator is an operator"

		keep, *rest = sorted(managers)
		for user in rest:
			site.make_operator(user, 0)
		assert site._operators() == [keep]
		try:
			site.make_operator(keep, 0)
			raise AssertionError("the last operator was removed")
		except frappe.ValidationError:
			pass
		try:
			site.make_operator("Guest", 1)
			raise AssertionError("Guest became an operator")
		except frappe.ValidationError:
			pass
		site.first_operators()
		assert site._operators() == [keep], "someone is already an operator, so nobody is added"
	frappe.db.rollback()
