"""A customer's own name on their workspace, added through us rather than by us.

Two names reach a workspace and only one of them is asked for. `<slug>.t.4dl.app`
is given at provisioning and lives entirely at the edge: a proxied wildcard, a
Worker that rewrites `Host` to the press site name, and the Advanced Certificate
Manager wildcard on the zone. Press is never told that name exists, which is why
there is nothing to verify — press serves a request for its own site name and
answers it.

A customer's own name is the opposite in every respect. Press adds it, checks
the DNS itself, and issues a Let's Encrypt certificate over HTTP-01 on its proxy
server. So this module does almost nothing: it validates what was typed, records
it, and relays. The certificate is never ours and never Cloudflare's.

**Proxying is what breaks this, and it is worth knowing why.** Press refuses a
domain whose `server:` response header is anything but its own — a HEAD request,
and Cloudflare's orange cloud answers `server: cloudflare`. So a customer
pointing their name at us through their own Cloudflare, proxied, will be refused
by press with a sentence about turning proxying off. We relay that sentence
rather than rewriting it, because it is the true one and it names the fix.

**A refusal here is thrown rather than raised.** `faults.Refused` is the
runner's word — it stops a provisioning job — and nothing in this module is a
step. More to the point, a refusal here is something a customer has to act on:
the name is taken, the DNS is not pointing here yet. `frappe.throw` puts the
sentence in `_server_messages`, which is the only route by which it reaches the
workspace that asked; a raised exception arrives there as `exc_type` and nothing
else, which is a dialog saying something went wrong and not what.

**What we keep and what we ask.** A `Tenant Domain` row per name, so the
workspace's own screen draws without a round trip to press and keeps drawing
when press is slow. Status is press's to decide, and `refresh` is what asks.
Nothing here is the authority on whether a domain works.
"""

import frappe
from frappe.utils import now_datetime

from onedesk.one_admin import cloudflare, hosts, press

#: Press's own names for where a domain has got to. Kept as press says them
#: rather than mapped onto ours: a status we invented would be a status that
#: disagrees with the one in their dashboard.
SETTLED = ("Active",)

#: The most names one workspace may add. Not a technical limit — press has none
#: — but a number beyond which somebody is doing something we should look at.
MOST = 10


def add(tenant, raw: str) -> dict:
	"""Claim a name, once it is a name this workspace may claim.

	The row is written before press is asked, so a call that times out leaves a
	record of what was wanted rather than nothing at all. Press is the authority
	on whether it works; we are the authority on whether it was allowed.
	"""
	name = _claimable(raw)
	if frappe.db.exists("Tenant Domain", name):
		held = frappe.db.get_value("Tenant Domain", name, ["tenant", "status"], as_dict=True)
		if held.tenant != tenant.name:
			frappe.throw(frappe._("{0} is already on another workspace.").format(name))
		return _as_said(name)

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

	press.call("press.api.site.add_domain", name=tenant.site, domain=name)
	return _as_said(name)


def check(tenant, raw: str) -> dict:
	"""What press makes of the DNS, before anybody commits to anything.

	Relayed whole. Press's answer names the record it wanted and the one it
	found, and a summary of ours would lose exactly the part that helps.
	"""
	name = _claimable(raw)
	return press.call("press.api.site.check_dns", name=tenant.site, domain=name) or {}


def drop(tenant, raw: str) -> dict:
	"""Give a name back.

	Press refuses to remove the primary domain, and that refusal is relayed
	rather than pre-empted: making it primary again is the fix, and press's
	sentence says so.
	"""
	name = _held(tenant, raw)
	press.call("press.api.site.remove_domain", name=tenant.site, domain=name)
	frappe.delete_doc("Tenant Domain", name, ignore_permissions=True, force=True)
	return {"dropped": name}


def make_primary(tenant, raw: str) -> dict:
	"""Which name the workspace calls itself.

	Press writes `host_name` into the site's own config when this changes, which
	is what makes links in mail and in the desk use the new name. So this is the
	one call here that changes what the site believes about itself, rather than
	only what the world can reach it at.
	"""
	name = _held(tenant, raw)
	settled = frappe.db.get_value("Tenant Domain", name, "status")
	if settled not in SETTLED:
		frappe.throw(
			frappe._("{0} is not working yet, so it cannot be the main address.").format(name)
		)
	press.call("press.api.site.set_host_name", name=tenant.site, domain=name)
	frappe.db.set_value("Tenant", tenant.name, "primary_domain", name)
	return _as_said(name)


def mine(tenant) -> list[dict]:
	"""Every name on this workspace, ours first.

	The given name is not a `Tenant Domain` row — it is not press's and nothing
	about it can fail — so it is put at the front here rather than stored as a
	row that would need keeping true.
	"""
	given = {
		"domain": tenant.domain,
		"status": "Active",
		"primary": not tenant.primary_domain,
		"given": True,
	}
	held = frappe.get_all(
		"Tenant Domain",
		filters={"tenant": tenant.name},
		fields=["domain", "status", "said", "asked_on"],
		order_by="asked_on asc",
	)
	for one in held:
		one["primary"] = one["domain"] == tenant.primary_domain
		one["given"] = False
	return [given, *held]


def refresh(tenant) -> list[dict]:
	"""Ask press where each name got to, and keep what it said.

	Called when the workspace opens the screen and nightly. Press is the
	authority; this only writes down its answer so the screen has something to
	draw when press is slow.
	"""
	said = press.call("press.api.site.domains", name=tenant.site) or []
	seen = {}
	for one in said:
		if not isinstance(one, dict) or not one.get("domain"):
			continue
		seen[one["domain"]] = one

	for row in frappe.get_all(
		"Tenant Domain", filters={"tenant": tenant.name}, fields=["name", "domain", "status"]
	):
		found = seen.get(row.domain)
		if not found:
			frappe.db.set_value("Tenant Domain", row.name, "status", "Gone")
			continue
		frappe.db.set_value(
			"Tenant Domain",
			row.name,
			{"status": found.get("status") or "Pending", "said": frappe.as_json(found)},
		)
	return mine(frappe.get_doc("Tenant", tenant.name))


def nightly() -> None:
	"""Catch up on what press did while nobody was looking.

	A domain goes Active minutes after it is added, and nothing tells us. Only
	workspaces with a name of their own are asked about, so this costs one call
	per workspace that has one rather than one per workspace.
	"""
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
			frappe.log_error(f"asking press about {slug}'s domains")


def unroute(tenant) -> None:
	"""Take the given name off the edge, when a workspace is archived.

	Its own domains need nothing: they are press's records and go when the site
	does. Ours is a key we wrote and a key we remove.
	"""
	cloudflare.forget(tenant.slug)


def _claimable(raw: str) -> str:
	"""A name this workspace may add, or a refusal in words a customer can act on."""
	try:
		return hosts.claimable(raw, _tenant_domain(), _admin_host())
	except hosts.Unclaimable as why:
		frappe.throw(str(why))


def _held(tenant, raw: str) -> str:
	name = _claimable(raw)
	if frappe.db.get_value("Tenant Domain", name, "tenant") != tenant.name:
		frappe.throw(frappe._("{0} is not on this workspace.").format(name))
	return name


def _as_said(name: str) -> dict:
	held = frappe.db.get_value("Tenant Domain", name, ["domain", "status"], as_dict=True)
	return dict(held or {"domain": name, "status": "Pending"})


def _tenant_domain() -> str:
	return frappe.get_cached_value("One Admin Settings", None, "tenant_domain") or "t.4dl.app"


def _admin_host() -> str:
	return frappe.utils.get_url().split("://", 1)[-1].split("/", 1)[0]
