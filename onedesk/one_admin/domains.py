"""A customer's own name on their workspace, served at the edge like ours.

Two names reach a workspace. `<slug>.t.4dl.app` is given at provisioning and
lives entirely at the edge: a proxied wildcard, a Worker that rewrites `Host`
to the Frappe Cloud site name, and the Advanced Certificate Manager wildcard on
the zone. Frappe Cloud is never told that name exists.

**A customer's own name goes the same way.** It is a *custom hostname* on our
zone (Cloudflare for SaaS). The customer makes one CNAME record, from their
name to their `<slug>.t.4dl.app`; Cloudflare sees the name arrive, validates
it over HTTP and issues its certificate; a Worker route for the name sends it
to the same router, which finds the site under `host:<name>` in KV. So the
customer only ever sees our name, Frappe Cloud never sees theirs, and nothing
issues a certificate but Cloudflare.

This replaced adding the name to Frappe Cloud, which had three costs: the
CNAME pointed at `*.frappe.cloud`, Frappe Cloud's Let's Encrypt check failed
for anybody who kept Cloudflare's proxy on, and a workspace that made its
name primary could not go back. Both at once would clash: Frappe Cloud's
check would reach Cloudflare and fail. So press is only asked one thing
here, to write `host_name` into the site's config (`_call_itself`).

**What we keep and what we ask.** A `Tenant Domain` row per name, with
Cloudflare's id for it, so the workspace's screen draws without a round trip.
Status is Cloudflare's to decide (`hosts.standing` puts it in our words), and
`refresh` is what asks: when the screen's Check Again is pressed and nightly
for names not yet working.

**A refusal here is thrown rather than raised.** It is something a customer
has to act on, the name is taken or is ours, and `frappe.throw` is the route
by which the sentence reaches the workspace that asked.

**Bare domains.** A CNAME at the apex (`acme.com`) only works where the
customer's DNS flattens it (Cloudflare, Route 53's ALIAS and many others).
Pointing an apex at fixed addresses is an Enterprise feature of Cloudflare
for SaaS, so the screen says to use a subdomain otherwise.
"""

import frappe
from frappe.utils import now_datetime

from onedesk.one_admin import cloudflare, hosts, press

#: Our word for a name that works.
SETTLED = ("Active",)

#: The most names one workspace may add. Not a technical limit, but a number
#: beyond which somebody is doing something we should look at.
MOST = 10


def add(tenant, raw: str) -> dict:
	"""Claim a name: the row, the custom hostname, the route and the KV key.

	Nothing waits on the customer's DNS. Cloudflare keeps checking and issues
	the certificate once the CNAME is there, and `refresh` notices.
	"""
	name = _claimable(raw)
	if frappe.db.exists("Tenant Domain", name):
		if frappe.db.get_value("Tenant Domain", name, "tenant") != tenant.name:
			frappe.throw(frappe._("{0} is already on another workspace.").format(name))
	else:
		if frappe.db.count("Tenant Domain", {"tenant": tenant.name}) >= MOST:
			frappe.throw(frappe._("A workspace may have at most {0} of its own domains.").format(MOST))
		frappe.get_doc(
			{
				"doctype": "Tenant Domain",
				"domain": name,
				"tenant": tenant.name,
				"status": "Pending",
				"asked_on": now_datetime(),
			}
		).insert(ignore_permissions=True)

	said = cloudflare.hostname_add(name)
	cloudflare.host_route(name, tenant.site)
	_keep(name, said)
	return _as_said(name)


def drop(tenant, raw: str) -> dict:
	"""Give a name back. The main address cannot go: make another one main
	first, or links in mail would point at a name that no longer answers."""
	name = _held(tenant, raw)
	if tenant.primary_domain == name:
		frappe.throw(frappe._("{0} is the main address. Make another address the main one first.").format(name))
	ident = frappe.db.get_value("Tenant Domain", name, "cloudflare_id")
	cloudflare.host_unroute(name)
	if ident:
		cloudflare.hostname_drop(ident)
	frappe.delete_doc("Tenant Domain", name, ignore_permissions=True, force=True)
	return {"dropped": name}


def make_primary(tenant, raw: str) -> dict:
	"""Which name the workspace calls itself: `host_name` in the site's own
	config, which is what makes links in mail and in the desk use it. The
	given name can always be made main again."""
	if (raw or "").strip().lower().rstrip(".") == tenant.domain:
		_call_itself(tenant, tenant.domain)
		frappe.db.set_value("Tenant", tenant.name, "primary_domain", None)
		_mark_main(tenant.name, None)
		return {"domain": tenant.domain, "status": "Active"}
	name = _held(tenant, raw)
	if frappe.db.get_value("Tenant Domain", name, "status") not in SETTLED:
		frappe.throw(frappe._("{0} is not working yet, so it cannot be the main address.").format(name))
	_call_itself(tenant, name)
	frappe.db.set_value("Tenant", tenant.name, "primary_domain", name)
	_mark_main(tenant.name, name)
	return _as_said(name)


def _mark_main(tenant: str, name: str | None) -> None:
	"""The console's copy of which name is main (`Tenant Domain.is_main`),
	so its list can say so; the workspace's `primary_domain` is the truth."""
	for one in frappe.get_all("Tenant Domain", filters={"tenant": tenant}, pluck="name"):
		frappe.db.set_value("Tenant Domain", one, "is_main", 1 if one == name else 0)


def mine(tenant) -> list[dict]:
	"""Every name on this workspace, ours first.

	The given name is not a `Tenant Domain` row, since nothing about it can
	fail, so it is put at the front here rather than stored.
	"""
	held = frappe.get_all(
		"Tenant Domain",
		filters={"tenant": tenant.name},
		fields=["domain", "status", "problem", "asked_on"],
		order_by="asked_on asc",
	)
	for one in held:
		one["primary"] = one["domain"] == tenant.primary_domain
		one["given"] = False
	given = {
		"domain": tenant.domain,
		"status": "Active",
		# Ours is the main address unless one of theirs is.
		"primary": not any(one["primary"] for one in held),
		"given": True,
	}
	return [given, *held]


def refresh(tenant) -> list[dict]:
	"""Ask Cloudflare where each name has got to, and keep its answer."""
	for row in frappe.get_all("Tenant Domain", filters={"tenant": tenant.name}, fields=["domain", "cloudflare_id"]):
		said = cloudflare.hostname(row.cloudflare_id) if row.cloudflare_id else cloudflare.hostname_find(row.domain)
		_keep(row.domain, said)
	return mine(frappe.get_doc("Tenant", tenant.name))


def nightly() -> None:
	"""Catch up on what Cloudflare did while nobody was looking. Only
	workspaces with a name not yet working are asked about."""
	from onedesk.one_admin import site

	if not site.is_admin():
		return
	waiting = frappe.get_all(
		"Tenant Domain",
		filters={"status": ["not in", SETTLED]},
		distinct=True,
		pluck="tenant",
	)
	for slug in waiting:
		try:
			refresh(frappe.get_doc("Tenant", slug))
		except Exception:
			frappe.log_error(f"asking Cloudflare about {slug}'s domains")
		frappe.db.commit()
	# What is still waiting a day on, or broken, told to the operator.
	from onedesk.one_admin import tell

	tell.domains_waiting()


def unroute(tenant) -> None:
	"""Take every name off the edge when a workspace is archived: ours, and
	each of the customer's with its custom hostname."""
	for row in frappe.get_all("Tenant Domain", filters={"tenant": tenant.name}, fields=["domain", "cloudflare_id"]):
		cloudflare.host_unroute(row.domain)
		if row.cloudflare_id:
			cloudflare.hostname_drop(row.cloudflare_id)
	cloudflare.forget(tenant.slug)


def _keep(name: str, said: dict | None) -> None:
	status, problem = hosts.standing(said)
	frappe.db.set_value(
		"Tenant Domain",
		name,
		{
			"status": status,
			"problem": problem,
			"cloudflare_id": (said or {}).get("id") or frappe.db.get_value("Tenant Domain", name, "cloudflare_id"),
			"said": frappe.as_json(said) if said else None,
		},
	)
	# Published, so a domain open in the console changes as Cloudflare answers.
	frappe.get_doc("Tenant Domain", name).notify_update()


def _call_itself(tenant, name: str) -> None:
	"""Write the name the site calls itself into its config, as provisioning
	first did (steps.py). Press's own `set_host_name` wants a domain press
	serves, and neither of ours is one."""
	press.call(
		"press.api.site.update_config",
		name=tenant.site,
		config=frappe.as_json([{"key": "host_name", "value": f"https://{name}", "type": "String"}]),
	)


def _claimable(raw: str) -> str:
	"""A name this workspace may add, or a refusal in words a customer can act on."""
	try:
		return hosts.claimable(raw, _tenant_domain(), _admin_host())
	except hosts.Unclaimable as why:
		frappe.throw(why.translated(frappe._))


def _held(tenant, raw: str) -> str:
	name = _claimable(raw)
	if frappe.db.get_value("Tenant Domain", name, "tenant") != tenant.name:
		frappe.throw(frappe._("{0} is not on this workspace.").format(name))
	return name


def _as_said(name: str) -> dict:
	held = frappe.db.get_value("Tenant Domain", name, ["domain", "status", "problem"], as_dict=True)
	return dict(held or {"domain": name, "status": "Pending"})


def _tenant_domain() -> str:
	return frappe.get_cached_value("One Admin Settings", None, "tenant_domain") or "t.4dl.app"


def _admin_host() -> str:
	return frappe.utils.get_url().split("://", 1)[-1].split("/", 1)[0]
