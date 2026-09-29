"""OneAdmin's Home: how the workspaces stand, and what needs the operator.

Two reads, both for the operator only on the admin site (`operator._may`):

- `counts`: live workspaces, workspaces being built, workspaces owing, jobs
  that failed, and signups paid for but never built. Each says the list it
  opens, with its filters, so a number and the list it stands for cannot
  disagree.
- `needs`: one list of what needs a person, each with why and the one thing
  to do about it. A failed job is resumed where it stopped, a job that is
  due and has not moved is run now, a paid signup
  with no workspace is built again, a domain is asked about again, and a
  workspace owing is opened.

OneAI's `console_today` reads `needs` (one_admin/ai.py), and so does nothing
else: the page and the model are told the same thing.
"""

import frappe
from frappe import _, _lt
from frappe.utils import add_to_date, now_datetime

#: A domain asked for less than this long ago is still being set up, not waiting.
DOMAIN_GRACE_HOURS = 24

#: The most of each kind listed at once; the count says how many there are.
MOST = 50

#: A job due longer ago than this has not moved: the scheduler has stopped,
#: or a worker died holding it. Two ticks is four minutes; this is patient.
STALLED_MINUTES = 15

#: A job that has not moved, said by what it is doing.
STALLED = {
	"Provision": _lt("Building {0} has not moved"),
	"Suspend": _lt("Suspending {0} has not moved"),
	"Restore": _lt("Restoring {0} has not moved"),
	"Archive": _lt("Archiving {0} has not moved"),
	"Drop": _lt("Deleting the files of {0} has not moved"),
}

#: A failed job, said by what it was doing.
FAILED = {
	"Provision": _lt("Building {0} failed"),
	"Suspend": _lt("Suspending {0} failed"),
	"Restore": _lt("Restoring {0} failed"),
	"Archive": _lt("Archiving {0} failed"),
	"Drop": _lt("Deleting the files of {0} failed"),
}


def _may() -> None:
	from onedesk.one_admin import operator

	operator._may()


def _filters() -> dict:
	"""What each count counts, as the list it opens filters it."""
	return {
		"live": ("Tenant", {"status": "Live"}),
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
	return [*_failed_jobs(), *_unbuilt_signups(), *_stalled_jobs(), *_owing(), *_domains()]


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
			"badge": _("Not Moving"),
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
				"label": _("Build It"),
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
	said = {"Overdue": _("Payment overdue"), "Suspended": _("Suspended for not paying")}
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
			"why": _("Not working") if one.status == "Broken" else _("Waiting for its DNS"),
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
