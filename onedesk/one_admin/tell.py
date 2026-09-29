"""Telling the operator, and a workspace's owner (one_admin/notifications.py).

Each is called where the thing happens rather than from a document hook,
because the machinery writes with `db_set`, which runs no hooks: a job stops
in `runner._stop`, a signup is paid for and built in `signup.accept`, a
workspace arrives on a rung in `steps._arrive`, and the domains are asked
about in `domains.nightly`. The owner is mailed from `steps._arrive` when
their workspace is suspended, archived or restored. Nothing here may stop the thing it tells of, so
each is wrapped: a notice that fails is logged, and the job carries on.
"""

import functools

import frappe
from frappe import _
from markupsafe import Markup

from onedesk.one import notify
from onedesk.one_admin import site

HOME = "/desk/one-admin"


def operators() -> list[str]:
	"""Everybody who may run the console, and nobody else."""
	held = frappe.get_all("Has Role", filters={"role": site.OPERATOR, "parenttype": "User"}, pluck="parent")
	if not held:
		return []
	return frappe.get_all(
		"User", filters={"name": ["in", held], "enabled": 1, "user_type": "System User"}, pluck="name"
	)


def _quietly(fn):
	"""A notice is told on the admin site only, and one that fails is logged
	rather than stopping the job it tells of."""

	@functools.wraps(fn)
	def telling(*args, **kwargs):
		if not site.is_admin():
			return
		try:
			fn(*args, **kwargs)
		except Exception:
			frappe.log_error(f"telling the operators: {fn.__name__}")

	return telling


@_quietly
def job_failed(job) -> None:
	"""A job stopped on a step (runner._stop)."""
	from onedesk.one_admin import home, steps

	notify.notify(
		"Job Failed",
		operators(),
		link=HOME,
		sender="Administrator",
		record=("Provisioning Job", job.name),
		what=str(home.FAILED.get(job.kind, home.FAILED["Provision"])).format(home._workspace(job.tenant)),
		step=_(steps.SAID.get(job.step, job.step or "")),
		error=(job.error or "").strip()[:300],
	)


@_quietly
def signup_paid(asked) -> None:
	"""Somebody paid for a workspace (signup.accept)."""
	plan = frappe.db.get_value("Offering", asked.offering, "label") if asked.get("offering") else None
	notify.notify(
		"New Signup",
		operators(),
		link=HOME,
		sender="Administrator",
		record=("Account Request", asked.name),
		workspace=asked.workspace_name or asked.email,
		email=asked.email,
		plan=f" · {plan}" if plan else "",
	)


@_quietly
def signup_not_built(asked, error: str) -> None:
	"""A paid signup's workspace could not be made (signup.accept)."""
	notify.notify(
		"Signup Not Built",
		operators(),
		link=HOME,
		sender="Administrator",
		record=("Account Request", asked.name),
		workspace=asked.workspace_name or asked.email,
		email=asked.email,
		error=(error or "")[:300],
	)


@_quietly
def owing(tenant, rung: str, why: str) -> None:
	"""A workspace arrived on Overdue or Suspended (steps._arrive)."""
	said = {"Overdue": _("Payment overdue"), "Suspended": _("Suspended for not paying")}
	if rung not in said:
		return
	notify.notify(
		"Workspace Owing",
		operators(),
		link=HOME,
		sender="Administrator",
		record=("Tenant", tenant.name),
		workspace=tenant.workspace_name or tenant.name,
		state=said[rung],
		why=why or "",
	)


@_quietly
def owner(tenant, rung: str, was: str | None) -> None:
	"""The workspace's owner, mailed when it is suspended, archived or
	restored (steps._arrive). Overdue is told on their own site
	(one/account.py); a suspended one cannot tell them anything."""
	if not tenant.get("owner_email"):
		return
	from frappe.utils import add_days, formatdate, today

	from onedesk.one_admin import lifecycle

	days = lifecycle._days()
	said = {
		"workspace": tenant.workspace_name or tenant.name,
		"reference_doctype": "Tenant",
		"reference_name": tenant.name,
	}
	if rung == "Suspended":
		on = formatdate(add_days(today(), days["Suspended"]))
		notify.mail("Workspace Suspended", tenant.owner_email, date=on, **said)
	elif rung == "Archived":
		on = formatdate(add_days(today(), days["Archived"]))
		notify.mail("Workspace Archived", tenant.owner_email, date=on, **said)
	elif rung == "Live" and was == "Suspended":
		address = tenant.get("domain") or tenant.get("site") or tenant.name
		notify.mail("Workspace Restored", tenant.owner_email, address=address, **said)


@_quietly
def domains_waiting() -> None:
	"""Each morning, after the domains were asked about (domains.nightly)."""
	from onedesk.one_admin import home

	waiting = home._domains()
	if not waiting:
		return
	notify.notify(
		"Domains Waiting",
		operators(),
		link=HOME,
		sender="Administrator",
		count=len(waiting),
		domains=Markup("<br>").join(f"{one['title']} · {one['why']}" for one in waiting),
	)
