"""OneAdmin's Home: how the workspaces stand, and what needs the operator.

Two reads, both for the operator only on the admin site (`operator._may`):
`counts`, and `needs`, which OneAI's `console_today` reads too.
"""

import frappe
from frappe import _, _lt
from frappe.utils import add_to_date, now_datetime

DOMAIN_GRACE_HOURS = 24

MOST = 50

STALLED_MINUTES = 15

STALLED = {
	"Provision": _lt("Building {0} is stalled"),
	"Suspend": _lt("Suspending {0} is stalled"),
	"Restore": _lt("Restoring {0} is stalled"),
	"Archive": _lt("Archiving {0} is stalled"),
	"Drop": _lt("Deleting files of {0} is stalled"),
}

FAILED = {
	"Provision": _lt("Building {0} failed"),
	"Suspend": _lt("Suspending {0} failed"),
	"Restore": _lt("Restoring {0} failed"),
	"Archive": _lt("Archiving {0} failed"),
	"Drop": _lt("Deleting files of {0} failed"),
}


def _may() -> None:
	from onedesk.one_admin import operator

	operator._may()


def _filters() -> dict:
	"""What each count counts, as the list it opens filters it."""
	return {
		"live": ("Tenant", {"status": "Live", "is_house": 0}),
		"building": ("Provisioning Job", {"kind": "Provision", "status": ["in", ["Pending", "Waiting"]]}),
		"owing": ("Tenant", {"status": ["in", ["Overdue", "Suspended"]]}),
		"failed": ("Provisioning Job", {"status": "Failed"}),
		"signups": ("Account Request", {"status": ["in", ["Paid", "Failed"]], "tenant": ["is", "not set"]}),
	}


@frappe.whitelist()
@frappe.read_only()
def counts() -> list[dict]:
	"""The numbers along the top of Home, each with the list it opens."""
	_may()
	said = {
		"live": _("Live"),
		"building": _("Building"),
		"owing": _("Owing"),
		"failed": _("Failed"),
		"signups": _("Paid, Not Built"),
	}
	return [
		{
			"key": key,
			"label": said[key],
			"value": frappe.db.count(doctype, filters),
			"doctype": doctype,
			"filters": filters,
		}
		for key, (doctype, filters) in _filters().items()
	]


@frappe.whitelist()
@frappe.read_only()
def needs() -> list[dict]:
	"""Everything that needs the operator, the most pressing first: a job
	that failed, money taken for a workspace that was never built, a
	workspace owing, and a domain that has not come up."""
	_may()
	return [
		*_failed_jobs(),
		*_unbuilt_signups(),
		*_stalled_jobs(),
		*_slow_builds(),
		*_owing(),
		*_over_storage(),
		*_over_database(),
		*_mispriced(),
		*_domains(),
		*_filling(),
	]


def _failed_jobs() -> list[dict]:
	from onedesk.one_admin import steps

	rows = frappe.get_all(
		"Provisioning Job",
		filters={"status": "Failed"},
		fields=["name", "tenant", "kind", "step", "error", "modified"],
		order_by="modified desc",
		limit=MOST,
	)
	return [
		{
			"kind": "job",
			"doctype": "Provisioning Job",
			"name": one.name,
			"title": str(FAILED.get(one.kind, FAILED["Provision"])).format(_workspace(one.tenant)),
			"why": _("At: {0}").format(str(steps.SAID.get(one.step, one.step))) if one.step else "",
			"detail": (one.error or "").strip().splitlines()[0][:200] if one.error else "",
			"since": str(one.modified),
			"action": {
				"label": _("Resume"),
				"method": "onedesk.one_admin.operator.resume",
				"args": {"job": one.name},
			},
		}
		for one in rows
	]


def _stalled_jobs() -> list[dict]:
	"""Jobs due and not run: whatever their kind, since a suspension that never
	happens is as wrong as a build that never finishes."""
	from onedesk.one_admin import steps

	rows = frappe.get_all(
		"Provisioning Job",
		filters={
			"status": ["in", ["Pending", "Waiting"]],
			"next_run_at": ["<", add_to_date(now_datetime(), minutes=-STALLED_MINUTES)],
		},
		fields=["name", "tenant", "kind", "step", "next_run_at"],
		order_by="next_run_at asc",
		limit=MOST,
	)
	return [
		{
			"kind": "stalled",
			"doctype": "Provisioning Job",
			"name": one.name,
			"title": str(STALLED.get(one.kind, STALLED["Provision"])).format(_workspace(one.tenant)),
			"why": _("Next: {0}").format(str(steps.SAID.get(one.step, one.step))) if one.step else "",
			"detail": "",
			"badge": _("Stalled"),
			"since": str(one.next_run_at),
			"action": {
				"label": _("Run Now"),
				"method": "onedesk.one_admin.operator.run_now",
				"args": {"job": one.name},
			},
		}
		for one in rows
	]


def _unbuilt_signups() -> list[dict]:
	rows = frappe.get_all(
		"Account Request",
		filters={"status": ["in", ["Paid", "Failed"]], "tenant": ["is", "not set"]},
		fields=["name", "workspace_name", "email", "status", "failed_reason", "modified"],
		order_by="modified desc",
		limit=MOST,
	)
	return [
		{
			"kind": "signup",
			"doctype": "Account Request",
			"name": one.name,
			"title": _("{0} paid and has no workspace").format(one.workspace_name or one.email),
			"why": one.email,
			"detail": (one.failed_reason or "").strip()[:200],
			"since": str(one.modified),
			"action": {
				"label": _("Build Workspace"),
				"method": "onedesk.one_admin.operator.retry_signup",
				"args": {"request": one.name},
			},
		}
		for one in rows
	]


def _owing() -> list[dict]:
	rows = frappe.get_all(
		"Tenant",
		filters={"status": ["in", ["Overdue", "Suspended"]]},
		fields=["name", "workspace_name", "status", "status_since", "owner_email"],
		order_by="status_since asc",
		limit=MOST,
	)
	said = {"Overdue": _("Payment overdue"), "Suspended": _("Suspended for non-payment")}
	return [
		{
			"kind": "owing",
			"doctype": "Tenant",
			"name": one.name,
			"title": one.workspace_name or one.name,
			"why": said.get(one.status, _(one.status)),
			"detail": one.owner_email or "",
			"since": str(one.status_since) if one.status_since else "",
			"action": None,
		}
		for one in rows
	]


def _over_storage() -> list[dict]:
	"""Live workspaces holding more than their plan allows: storage we pay for
	and they do not. Their own site tells their administrators when nearly
	full; this is our side of it. Opening one is the action."""
	from onedesk.one_account.heads import size

	rows = frappe.get_all(
		"Tenant",
		filters={"status": "Live", "storage_limit": [">", 0]},
		fields=["name", "workspace_name", "storage_bytes", "storage_limit", "modified"],
		limit=MOST * 4,
	)
	return [
		{
			"kind": "storage",
			"doctype": "Tenant",
			"name": one.name,
			"title": one.workspace_name or one.name,
			"why": f"{size(one.storage_bytes)} / {size(one.storage_limit)}",
			"detail": "",
			"since": "",
			"badge": _("Over Storage"),
			"action": None,
		}
		for one in rows
		if (one.storage_bytes or 0) > one.storage_limit
	][:MOST]


def _over_database() -> list[dict]:
	"""Live workspaces whose database is past what they bought. On our own
	servers Frappe Cloud sets no limit, so this is the only place it is
	watched (quota.py). Opening one is the action."""
	from onedesk.one_account.heads import size

	rows = frappe.get_all(
		"Tenant",
		filters={"status": "Live", "database_limit": [">", 0]},
		fields=["name", "workspace_name", "database_bytes", "database_limit"],
		limit=MOST * 4,
	)
	return [
		{
			"kind": "storage",
			"doctype": "Tenant",
			"name": one.name,
			"title": one.workspace_name or one.name,
			"why": f"{size(one.database_bytes)} / {size(one.database_limit)}",
			"detail": "",
			"since": "",
			"badge": _("Over Database"),
			"action": None,
		}
		for one in rows
		if (one.database_bytes or 0) > one.database_limit
	][:MOST]


SLOW_BUILD_HOURS = 3


def _slow_builds() -> list[dict]:
	"""Builds still waiting on Frappe Cloud after hours. Waiting never fails a
	job (runner._waiting), so this is where a build that will never finish is
	seen."""
	from onedesk.one_admin import steps

	rows = frappe.get_all(
		"Provisioning Job",
		filters={
			"kind": "Provision",
			"status": "Waiting",
			"creation": ["<", add_to_date(now_datetime(), hours=-SLOW_BUILD_HOURS)],
		},
		fields=["name", "tenant", "step", "creation"],
		order_by="creation asc",
		limit=MOST,
	)
	return [
		{
			"kind": "stalled",
			"doctype": "Provisioning Job",
			"name": one.name,
			"title": _("Building {0} is taking hours").format(_workspace(one.tenant)),
			"why": _("At: {0}").format(str(steps.SAID.get(one.step, one.step))) if one.step else "",
			"detail": _("Check the site on its server."),
			"badge": _("Slow"),
			"since": str(one.creation),
			"action": None,
		}
		for one in rows
	]


FILLING = 0.7


def _filling() -> list[dict]:
	"""Servers new workspaces go on that are near their limit or at it, and a
	jurisdiction with no open server at all. Buying the next one takes a
	while, so this is said before a workspace fails to be placed."""
	from onedesk.one_admin import quota

	listed = [one for one in frappe.get_cached_doc("One Admin Settings").get("servers") or [] if one.server]
	if not listed:
		return []
	counts = quota.held_on_servers()
	said = [
		{
			"kind": "storage",
			"doctype": "One Admin Settings",
			"name": "One Admin Settings",
			"title": _("{0} is filling up").format(one.server),
			"why": _("{0} of {1} workspaces").format(counts.get(one.server, 0), one.capacity),
			"detail": _(
				"Order the next server. It takes about 25 minutes."
			),
			"since": "",
			"badge": _("Full") if counts.get(one.server, 0) >= one.capacity else _("Filling Up"),
			"action": {"label": _("Order Server"), "method": "onedesk.one_admin.operator.order_server", "args": {}},
		}
		for one in listed
		if one.open and one.capacity and counts.get(one.server, 0) >= FILLING * one.capacity
	]
	offers_eu = bool(frappe.get_cached_value("One Admin Settings", None, "bucket_eu"))
	for eu, title in (
		(False, _("No open server for new workspaces")),
		(True, _("No open server for EU workspaces")),
	):
		if eu and not offers_eu:
			continue
		if not any(one.open and (one.eu or not eu) for one in listed):
			said.append(
				{
					"kind": "storage",
					"doctype": "One Admin Settings",
					"name": "One Admin Settings",
					"title": title,
					"why": "",
					"detail": _("New workspaces can't be built until a server is added."),
					"since": "",
					"badge": _("Full"),
					"action": None,
				}
			)
	return said


def _mispriced() -> list[dict]:
	"""What Price Check calls wrong: a price under its cost, a plan nobody
	would move up to. A close call is left to the report."""
	from onedesk.one_admin import offerings

	return [
		{
			"kind": "price",
			"doctype": "Offering",
			"name": one["offering"],
			"title": frappe.db.get_value("Offering", one["offering"], "label") or one["offering"],
			"why": one["said"],
			"detail": "",
			"since": "",
			"badge": _("Wrong Price"),
			"action": None,
		}
		for one in offerings.findings()
		if one["level"] == "red"
	][:MOST]


def _domains() -> list[dict]:
	since = add_to_date(now_datetime(), hours=-DOMAIN_GRACE_HOURS)
	rows = frappe.get_all(
		"Tenant Domain",
		filters=[["status", "in", ["Pending", "Broken"]]],
		or_filters=[["status", "=", "Broken"], ["asked_on", "<", since]],
		fields=["name", "domain", "tenant", "status", "problem", "asked_on"],
		order_by="asked_on asc",
		limit=MOST,
	)
	return [
		{
			"kind": "domain",
			"doctype": "Tenant Domain",
			"name": one.name,
			"title": one.domain,
			"why": _("Not working") if one.status == "Broken" else _("Waiting for DNS"),
			"detail": (one.problem or "").strip()[:200] or _workspace(one.tenant),
			"since": str(one.asked_on) if one.asked_on else "",
			"action": {
				"label": _("Check Again"),
				"method": "onedesk.one_admin.operator.refresh_domain",
				"args": {"domain": one.name},
			},
		}
		for one in rows
	]


def _workspace(tenant: str | None) -> str:
	if not tenant:
		return _("a workspace")
	return frappe.db.get_value("Tenant", tenant, "workspace_name") or tenant
