"""Telling the operator, and a workspace's owner (notifications/one_admin/).

Each is called where the thing happens, since the machinery writes with
`db_set`, which runs no document hooks.
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
		state=_(tenant.status).lower(),
	)


@_quietly
def owing(tenant, rung: str, why: str) -> None:
	"""A workspace arrived on Overdue or Suspended (steps._arrive)."""
	said = {"Overdue": _("Payment overdue"), "Suspended": _("Suspended for non-payment")}
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
def owner(tenant, rung: str, was: str | None, why: str | None = None) -> None:
	"""Whoever pays for the workspace, mailed when its payment fails, and when
	it is suspended, archived or restored (steps._arrive): the payer need not
	be anybody on the site, and a suspended one cannot tell them anything.
	Not when a cancelled subscription starts the fall, which no card caused,
	nor when a build that failed is archived, which they never had."""
	from frappe.utils import add_days, formatdate, today

	from onedesk.one_admin import lifecycle, log

	to = tenant.get("account") or tenant.get("owner_email")
	if not to or (rung == "Overdue" and why == log.said("cancelled")) or (rung == "Archived" and was == "Failed"):
		return
	days = lifecycle._days()
	said = {
		"workspace": tenant.workspace_name or tenant.name,
		"reference_doctype": "Tenant",
		"reference_name": tenant.name,
	}
	if rung == "Overdue":
		on = formatdate(add_days(today(), days["Overdue"]))
		notify.mail("Payment Failed", to, date=on, account=frappe.utils.get_url("/account"), **said)
	elif rung == "Suspended":
		on = formatdate(add_days(today(), days["Suspended"]))
		notify.mail("Workspace Suspended", to, date=on, **said)
	elif rung == "Archived":
		on = formatdate(add_days(today(), days["Archived"]))
		if tenant.get("closing_on"):
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
	the workspace are told there (one_account/closing.py); the operators here."""
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


def sign_in_link(email: str, link: str, minutes) -> None:
	"""An account asked for a link to sign in (accounts.send_login_link)."""
	notify.mail("Sign-in Link", email, link=link, minutes=minutes, now=True)


def workspace_moved(tenant: str, workspace: str | None, by: str | None, now: str, was: str | None) -> None:
	"""A workspace went to another account (accounts.move): the new holder and the old one hear it."""
	from frappe.utils import get_url

	said = {
		"workspace": workspace or tenant,
		"by": by or _("An administrator"),
		"reference_doctype": "Tenant",
		"reference_name": tenant,
	}
	notify.mail("Workspace Moved to You", now, account=get_url("/account"), **said)
	if was:
		notify.mail("Workspace Moved Away", was, **said)


def email_change_asked(email: str, link: str, minutes: int) -> None:
	"""An account asked to change its address (accounts.ask_email_change): the new one is mailed a link."""
	notify.mail("Confirm Your New Email", email, link=link, minutes=minutes, now=True)


def account_email_changed(was: str, now: str) -> None:
	"""An account's address changed (accounts.confirm_email): the old address is told."""
	notify.mail("Account Email Changed", was, address=now, now=True)


def finish_signing_up(asked) -> None:
	"""A signup was never paid for (signup.remind): one mail back to the welcome page."""
	from frappe.utils import get_url

	notify.mail(
		"Finish Signing Up",
		asked.email,
		workspace=asked.workspace_name or asked.slug,
		link=f"{get_url()}/welcome?request={asked.name}&key={asked.access_key}",
		reference_doctype="Account Request",
		reference_name=asked.name,
	)


@_quietly
def trials_ending() -> None:
	"""Each night: a workspace whose free trial has three days left, mailed
	to whoever pays for it, before their card is first charged."""
	from frappe.utils import add_days, fmt_money, formatdate, getdate, today

	for tenant in frappe.get_all(
		"Tenant",
		filters={"status": "Live", "offering": ["is", "set"]},
		fields=["name", "workspace_name", "offering", "live_on", "creation", "account", "owner_email"],
	):
		plan = frappe.db.get_value(
			"Offering", tenant.offering, ["label", "trial_days", "amount", "currency"], as_dict=True
		)
		if not plan or not plan.trial_days:
			continue
		ends = add_days(getdate(tenant.live_on or tenant.creation), plan.trial_days)
		to = tenant.account or tenant.owner_email
		if not to or ends != add_days(getdate(today()), 3):
			continue
		notify.mail(
			"Trial Ending",
			to,
			workspace=tenant.workspace_name or tenant.name,
			date=formatdate(ends),
			plan=plan.label,
			price=fmt_money(plan.amount, currency=plan.currency),
			account=frappe.utils.get_url("/account"),
			reference_doctype="Tenant",
			reference_name=tenant.name,
		)


@_quietly
def builds_slow() -> None:
	"""Hourly: a build still waiting on Frappe Cloud after hours, told once to
	the operators, and its payer mailed that it is delayed. Waiting never
	fails a job, so Job Failed never comes."""
	from onedesk.one_admin import home

	for one in home._slow_builds():
		notify.notify(
			"Build Slow",
			operators(),
			link=HOME,
			sender="Administrator",
			record=("Provisioning Job", one["name"]),
			dedupe_on=["document_type", "document_name"],
			title=one["title"],
			at=one["why"],
		)
		tenant = frappe.db.get_value("Provisioning Job", one["name"], "tenant")
		to = tenant and frappe.db.get_value(
			"Tenant", tenant, ["account", "owner_email", "workspace_name"], as_dict=True
		)
		if (
			to
			and (to.account or to.owner_email)
			and not frappe.db.exists("Email Queue", {"reference_doctype": "Tenant", "reference_name": tenant})
		):
			notify.mail(
				"Workspace Delayed",
				to.account or to.owner_email,
				workspace=to.workspace_name or tenant,
				reference_doctype="Tenant",
				reference_name=tenant,
			)


@_quietly
def servers_filling() -> None:
	"""Each morning: a server near or at its limit, told to the operators once
	for each step it reaches. A full server fails the next build."""
	from onedesk.one_admin import home

	for one in home._filling():
		told = f"one_admin_filling_{one['title']}"
		if frappe.db.get_default(told) == str(one["badge"]):
			continue
		frappe.db.set_default(told, str(one["badge"]))
		notify.notify(
			"Server Filling Up",
			operators(),
			link=HOME,
			sender="Administrator",
			title=one["title"],
			held=one["why"],
		)


@_quietly
def release_set(at, apps: list[str]) -> None:
	"""An update is set for its window: the operators hear when, and what."""
	notify.notify(
		"Update Set",
		operators(),
		link=HOME,
		sender="Administrator",
		at=frappe.utils.format_datetime(at, "EEEE d MMMM, HH:mm 'UTC'"),
		apps=", ".join(apps),
	)
