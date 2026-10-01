"""Telling the operator, and a workspace's owner (one_admin/notifications.py).

Each is called where the thing happens rather than from a document hook,
because the machinery writes with `db_set`, which runs no hooks: a job stops
in `runner._stop`, a signup is paid for and built in `signup.accept`, a
workspace arrives on a rung in `steps._arrive`, and the domains are asked
about in `domains.nightly`. The owner is mailed from `steps._arrive` when
their workspace is suspended, archived or restored, and from `steps.live`
when a new one is ready. Nothing here may stop the thing it tells of, so
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

	walk = steps.WALKS.get(job.kind or "Provision", steps.ORDER)
	notify.notify(
		"Job Failed",
		operators(),
		link=HOME,
		sender="Administrator",
		record=("Provisioning Job", job.name),
		what=str(home.FAILED.get(job.kind, home.FAILED["Provision"])).format(home._workspace(job.tenant)),
		number=walk.index(job.step) + 1 if job.step in walk else 1,
		steps=len(walk),
		# `_lt`, so each operator reads it in their own language (notify._said).
		step=steps.SAID.get(job.step, job.step or ""),
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
	# They paid: they hear it is delayed rather than nothing. Once, since
	# Build Workspace failing again is not news to them.
	if asked.email and not _told_delayed(asked):
		notify.mail(
			"Workspace Delayed",
			asked.email,
			workspace=asked.workspace_name or asked.slug,
			reference_doctype="Account Request",
			reference_name=asked.name,
		)


def _told_delayed(asked) -> bool:
	return bool(
		frappe.db.exists(
			"Email Queue", {"reference_doctype": "Account Request", "reference_name": asked.name}
		)
	)


@_quietly
def paid_while_archived(tenant) -> None:
	"""Money arrived for a workspace whose site is gone (lifecycle.paid)."""
	notify.notify(
		"Paid While Archived",
		operators(),
		link=HOME,
		sender="Administrator",
		record=("Tenant", tenant.name),
		workspace=tenant.workspace_name or tenant.name,
		state=_(tenant.status),
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
	"""Whoever pays for the workspace, mailed when it is suspended, archived or
	restored (steps._arrive). Overdue is told on their own site
	(one/account.py); a suspended one cannot tell them anything."""
	# Whoever holds it in their One account is who pays, so who is told; the
	# address it was bought with only if nobody holds it yet.
	to = tenant.get("account") or tenant.get("owner_email")
	if not to:
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
		notify.mail("Workspace Suspended", to, date=on, **said)
	elif rung == "Archived":
		on = formatdate(add_days(today(), days["Archived"]))
		if tenant.get("closing_on"):
			# Closed because they asked, not because they did not pay.
			notify.mail("Workspace Closed", to, date=on, **said)
		else:
			notify.mail("Workspace Archived", to, date=on, **said)
	elif rung == "Live" and was == "Suspended":
		address = tenant.get("domain") or tenant.get("site") or tenant.name
		notify.mail("Workspace Restored", to, address=address, **said)


@_quietly
def ready(tenant) -> None:
	"""A build finished (steps.live): the owner hears their workspace is
	ready. Their invitation to it left the step before (steps.invite_owner)."""
	if not tenant.get("owner_email"):
		return
	notify.mail(
		"Workspace Ready",
		tenant.owner_email,
		workspace=tenant.workspace_name or tenant.name,
		address=tenant.get("domain") or tenant.get("site") or tenant.name,
		account=frappe.utils.get_url("/account"),
		reference_doctype="Tenant",
		reference_name=tenant.name,
	)


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


@_quietly
def models_gone(gone: list[dict]) -> None:
	"""Offered models the nightly sync took off sale (catalogue.sync): the
	provider stopped listing them, or their price stopped being readable.
	What ran on them now runs on the default (actions.default_model)."""
	from onedesk.one_admin import actions

	said = {"withdrawn": _("the provider withdrew it"), "unpriced": _("its price can no longer be read")}
	lines = []
	for one in gone:
		line = f"{one.get('label') or one['name']}: {said.get(one['why'], one['why'])}"
		if one.get("default_for"):
			now = actions.default_model(one["default_for"])
			line += " · " + (
				_("the default for {0} is now {1}").format(one["default_for"], now)
				if now
				else _("nothing can do {0} now").format(one["default_for"])
			)
		lines.append(line)
	notify.notify(
		"Model Withdrawn",
		operators(),
		link="/desk/ai-model",
		sender="Administrator",
		count=len(gone),
		models=Markup("<br>").join(lines),
	)


@_quietly
def settings_changed(said: list[str]) -> None:
	"""An operator saved OneAdmin Settings (one_admin_settings.py): the others
	hear what changed. A key is only ever said to have changed."""
	others = [one for one in operators() if one != frappe.session.user]
	if not others:
		return
	notify.notify(
		"Settings Changed",
		others,
		link="/desk/one-admin-settings",
		sender=frappe.session.user,
		who=frappe.utils.get_fullname(frappe.session.user),
		changes=Markup("<br>").join(said),
	)


@_quietly
def closing(tenant) -> None:
	"""Its payer asked for it to be closed (closing.ask). They and everybody in
	the workspace are told there (one/closing.py); the operators here."""
	from frappe.utils import formatdate

	from onedesk.one_admin import closing as closing_

	said = closing_.when(tenant)
	notify.notify(
		"Workspace Asked to Close",
		operators(),
		link=HOME,
		sender="Administrator",
		record=("Tenant", tenant.name),
		workspace=tenant.workspace_name or tenant.name,
		who=tenant.closing_asked_by or "",
		date=formatdate(said.get("closing_on")),
		deleted=formatdate(said.get("deleted_on")) if said.get("deleted_on") else _("never"),
	)
