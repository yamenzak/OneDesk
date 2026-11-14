"""Telling people about the workspace itself: its account, its people and what
they may do, their data and their sign-in (one/notifications.py)."""

import frappe
from frappe import _, _lt
from frappe.automation.doctype.reminder.reminder import Reminder as _FrappeReminder

from onedesk.one import notify, registry, roles


def credits_running_low(people: list[str], balance: str, days: int) -> None:
	"""The credits fell under a tenth of a month's use (account._tell)."""
	from onedesk.one import account

	slots = {"balance": balance, "days": days}
	notify.notify("Credits Running Low", people, link=account.PAGE, sender="Administrator", **slots)


def credits_ran_out(people: list[str]) -> None:
	"""The credits are gone: OneAI and Intake stop until more come."""
	from onedesk.one import account

	notify.notify("Credits Ran Out", people, link=account.PAGE, sender="Administrator")


def credits_added(people: list[str], balance: str, gift: dict | None = None) -> None:
	"""Credits came in: bought, or given by One with the operator's note."""
	from onedesk.one import account

	note = ""
	if gift:
		from frappe.utils import formatdate
		from markupsafe import Markup, escape

		said = [frappe._("A note from {1}: {0}").format(gift["why"], registry.name("one"))] if gift.get("why") else []
		if gift.get("expires_on"):
			said.append(frappe._("They expire on {0}.").format(formatdate(gift["expires_on"])))
		note = Markup("<br><br>") + escape(" ".join(said)) if said else ""
	notify.notify(
		"Credits Added", people, link=account.PAGE, sender="Administrator", balance=balance, note=note
	)


def credits_expiring(people: list[str], credits: str, date: str) -> None:
	"""Credits expire within the week."""
	from onedesk.one import account

	notify.notify(
		"Credits Expiring",
		people,
		link=account.PAGE,
		sender="Administrator",
		credits=credits,
		date=date,
	)


def storage_nearly_full(people: list[str], used, limit) -> None:
	"""The files crossed nine tenths of what the plan holds."""
	from onedesk.account_center.heads import size
	from onedesk.one import account

	slots = {"used": size(used), "limit": size(limit)}
	notify.notify("Storage Nearly Full", people, link=account.PAGE, sender="Administrator", **slots)


def database_nearly_full(people: list[str], used, limit) -> None:
	"""The database crossed nine tenths of what the plan holds."""
	from onedesk.account_center.heads import size
	from onedesk.one import account

	slots = {"used": size(used), "limit": size(limit)}
	notify.notify("Database Nearly Full", people, link=account.PAGE, sender="Administrator", **slots)


def payment_overdue(people: list[str], date: str) -> None:
	"""A payment is owed, and the workspace changes on `date`."""
	from onedesk.one import account

	notify.notify("Payment Overdue", people, link=account.PAGE, sender="Administrator", date=date)


def plan_changed(plan: str, said: dict) -> None:
	"""The plan changed, told to every other administrator."""
	from onedesk.one import account

	people = [one for one in account._administrators() if one != frappe.session.user]
	if people:
		notify.notify(
			"Plan Changed",
			people,
			link=account.PAGE,
			by=frappe.utils.get_fullname(),
			plan=plan,
			monthly=frappe.utils.fmt_money(said.get("monthly") or 0, currency=said.get("currency") or "USD"),
		)


def payer_changed(email: str) -> None:
	"""Somebody else pays now, told to every other administrator."""
	from onedesk.one import account

	people = [one for one in account._administrators() if one != frappe.session.user]
	if people:
		notify.notify(
			"Payer Changed",
			people,
			link=account.PAGE,
			by=frappe.utils.get_fullname(),
			email=email,
		)


def main_address_changed(domain: str) -> None:
	"""The workspace calls itself by another name, told to every other administrator."""
	from onedesk.one import account

	people = [one for one in account._administrators() if one != frappe.session.user]
	if people:
		slots = {"by": frappe.utils.get_fullname(), "domain": domain}
		notify.notify("Main Address Changed", people, link=account.DOMAINS, **slots)


def domain_working(people: list[str], domain: str) -> None:
	"""One of the workspace's own names started working."""
	from onedesk.one import account

	slots = {"domain": domain}
	notify.notify("Domain Working", people, link=account.DOMAINS, sender="Administrator", **slots)


def domain_stopped_working(people: list[str], domain: str, target: str | None) -> None:
	"""One of the workspace's own names stopped working."""
	from onedesk.one import account

	slots = {"domain": domain, "target": target or ""}
	notify.notify("Domain Stopped Working", people, link=account.DOMAINS, sender="Administrator", **slots)


def _everybody() -> list[str]:
	"""Everybody who signs in to the workspace, the payer included."""
	from onedesk.one.people import NOT_PEOPLE

	return frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User", "name": ["not in", list(NOT_PEOPLE)]},
		pluck="name",
	)


def full_download_ready(user: str, size: str, missing: list) -> None:
	"""The zip of everything is made, told to whoever asked for it."""
	from onedesk.one import account

	notify.notify(
		"Full Download Ready",
		user,
		link=account.PAGE,
		sender="Administrator",
		size=size,
		missing=_("{0} files could not be read and are listed in it.").format(len(missing))
		if missing
		else "",
	)


def workspace_closing(held) -> None:
	"""The workspace is to close, told to everybody, the payer too: the sender is One."""
	from frappe.utils import formatdate

	from onedesk.one import account

	notify.notify(
		"Workspace Closing",
		_everybody(),
		link=account.PAGE,
		sender="Administrator",
		by=frappe.utils.get_fullname(),
		date=formatdate(held.closing_on),
		deleted=formatdate(held.deleted_on) if held.deleted_on else _("later"),
	)


def workspace_staying_open() -> None:
	"""The workspace stays open after all, told to everybody."""
	from onedesk.one import account

	notify.notify(
		"Workspace Staying Open",
		_everybody(),
		link=account.PAGE,
		sender="Administrator",
		by=frappe.utils.get_fullname(),
	)


def invited(email: str, apps: list[str] | None, **said) -> None:
	"""Somebody just added is invited, with what they may use besides the five."""
	apps_said = (" " + _("You can use {0}.").format(", ".join(apps))) if apps else ""
	notify.mail("Invitation", email, apps=apps_said, **said)


def invited_to_portal(email: str, what: str, **said) -> None:
	"""A customer's or supplier's contact is invited, with what they will see."""
	notify.mail("Portal Invitation", email, what=what, **said)


def portal_link(email: str, **said) -> None:
	"""A signed link to a record, mailed to whoever it is for (portal_share.py)."""
	notify.mail("Portal Link", email, **said)


def access_changed(user: str, changes: str) -> None:
	"""What a person may use changed, told to them."""
	notify.notify("Access Changed", user, link="/desk", changes=changes, by=frappe.utils.get_fullname())


def administrator_added(doc) -> None:
	"""A new administrator, told to every other one, and always mailed."""
	from onedesk.one.people import NOT_PEOPLE

	admins = [
		one for one in roles.administrators() if one not in (doc.name, frappe.session.user, *NOT_PEOPLE)
	]
	slots = {"person": doc.full_name or doc.name, "by": frappe.utils.get_fullname()}
	notify.notify(
		"Administrator Added",
		admins,
		link="/desk/one?center=account&at=people",
		sender="Administrator",
		**slots,
	)


def _said() -> dict:
	"""When, from which device and address: what a security notice says."""
	from frappe.utils import now_datetime

	from onedesk.account_center.signin import device

	agent = frappe.request.headers.get("User-Agent") if getattr(frappe.local, "request", None) else None
	return {
		"device": device(agent),
		"when": frappe.utils.format_datetime(now_datetime(), "d MMM yyyy, HH:mm"),
		"address": getattr(frappe.local, "request_ip", None) or "",
	}


def new_sign_in(user: str) -> None:
	"""A person signed in from a device they had not used before."""
	notify.notify(
		"New Sign-in", user, link="/desk/one?center=account&at=signin", sender="Administrator", **_said()
	)


def password_changed(user: str) -> None:
	"""A person's password changed."""
	slots = _said()
	notify.notify(
		"Password Changed", user, link="/desk/one?center=account&at=signin", sender="Administrator", **slots
	)


def two_factor_reset(user: str) -> None:
	"""Two-factor was reset on a person's account, by them or an administrator."""
	notify.notify(
		"Two-Factor Reset", user, link="/desk/one?center=account&at=signin", sender="Administrator", **_said()
	)


def passkey_added(user: str) -> None:
	"""A passkey was added to a person's account."""
	slots = _said()
	notify.notify(
		"Passkey Added", user, link="/desk/one?center=account&at=signin", sender="Administrator", **slots
	)


def passkey_turned_off(user: str, device: str) -> None:
	"""An administrator sorted, lost or retired a device a passkey of theirs was on."""
	notify.notify(
		"Passkey Turned Off", user, link="/desk/one?center=account&at=signin", sender="Administrator", device=device
	)


def asked_to_confirm_deletion(email: str, url: str, hours: int) -> None:
	"""Somebody without a password asked to be deleted, and confirms by the link."""
	notify.notify("Confirm Deletion", email, link=url, url=url, hours=hours)


def deletion_asked(doc) -> None:
	"""A request to be deleted reached the administrators."""
	from onedesk.one import privacy

	notify.notify(
		"Deletion Asked",
		privacy._administrators(),
		record=(privacy.DELETION, doc.name),
		person=frappe.utils.get_fullname(doc.email),
		email=doc.email,
	)


def deletion_held(doc, why: str) -> None:
	"""A request to be deleted is on hold, told to whoever asked, and why."""
	from onedesk.one import privacy

	if privacy._is_user(doc.email):
		notify.notify("Deletion On Hold", doc.email, link=privacy.where(doc.email), why=why)
	else:
		notify.mail("Your Request Is On Hold", doc.email, why=why)


def deletion_approved(doc, user: bool) -> None:
	"""A deletion approved, told while there is still somebody to tell, and to
	the other administrators."""
	from onedesk.one import privacy

	person = frappe.utils.get_fullname(doc.email)
	if user:
		notify.notify("Account Deleted", doc.email)
	else:
		notify.mail("Your Data Is Being Deleted", doc.email)
	others = [one for one in privacy._administrators() if one not in (frappe.session.user, doc.email)]
	if others:
		notify.notify("Person Deleted", others, by=frappe.utils.get_fullname(), person=person)


def privacy_requests_waiting(count: int) -> None:
	"""Requests nobody has decided after a week, said again to the administrators."""
	from onedesk.one import privacy

	notify.notify(
		"Privacy Requests Waiting",
		privacy._administrators(),
		link="/desk/personal-data-download-request",
		count=count,
	)


def request_to_confirm(email: str, workspace: str, kind: str, url: str, hours: int) -> None:
	"""Somebody outside asked for a copy of their data or its deletion, and confirms by the link."""
	notify.mail(
		"Confirm Your Request",
		email,
		now=False,
		workspace=workspace,
		asked=_("a copy of your data") if kind == "copy" else _("your data to be deleted"),
		hours=hours,
		url=url,
	)


def copy_asked(doc, person: str) -> None:
	"""A copy of somebody's data was asked for, for an administrator to review."""
	from onedesk.one import privacy

	notify.notify(
		"Copy Asked",
		privacy._administrators(),
		record=(privacy.DOWNLOAD, doc.name),
		person=person,
	)


def copy_ready(user: str, withheld: str) -> None:
	"""A user's copy of their data is ready on their account."""
	from onedesk.one import privacy

	notify.notify(
		"Your Data Is Ready",
		user,
		link=privacy.where(user),
		withheld=withheld,
	)


def copy_ready_to_download(request: str, address: str, withheld: str) -> None:
	"""The copy for somebody who is not a user is ready, by a link that works for a week."""
	from onedesk.one import privacy_public

	notify.mail(
		"Your Data Is Ready to Download",
		address,
		url=privacy_public.download_link(request),
		days=privacy_public.DOWNLOAD_DAYS,
		withheld=withheld,
	)


def announced(doc) -> None:
	"""A note made public, told once to everybody but whoever posted it."""
	from onedesk.one.announcements import NOTE, SAID
	from onedesk.one.people import NOT_PEOPLE

	people = frappe.get_all(
		"User",
		filters={
			"enabled": 1,
			"user_type": "System User",
			"name": ["not in", [*NOT_PEOPLE, frappe.session.user]],
		},
		pluck="name",
	)
	text = frappe.utils.strip_html(doc.content or "").strip()
	notify.notify(
		"Announcement",
		people,
		record=(NOTE, doc.name),
		title=doc.title,
		by=frappe.utils.get_fullname(),
		text=text[:SAID] + ("…" if len(text) > SAID else ""),
	)


def approval_waiting(record, state: str | None, held_by: list[str], actions: list[str]) -> None:
	"""A record reached a step, told to whoever holds a role it is for and may open it."""
	people = {
		row.parent
		for row in frappe.get_all(
			"Has Role", filters={"role": ["in", held_by], "parenttype": "User"}, fields=["parent"], limit=0
		)
	}
	told = [
		one
		for one in sorted(people)
		if one not in ("Administrator", "Guest")
		and frappe.db.get_value("User", one, "enabled")
		and frappe.has_permission(record.doctype, "read", record, user=one)
	]
	if told:
		notify.notify(
			"Approval Waiting",
			told,
			record=(record.doctype, record.name),
			kind=_(record.doctype),
			record_name=record.name
			if (record.get_title() or record.name) == record.name
			else f"{record.name} ({record.get_title()})",
			state=_(state or ""),
			actions=_or([_(one) for one in dict.fromkeys(actions)]) or _("move it on"),
		)


def told_by_automation(people: list[str], doc, subject: str, message: str) -> None:
	"""An automation's Tell People step."""
	from markupsafe import Markup

	notify.notify(
		"Automation Notice",
		people,
		record=(doc.doctype, doc.name) if doc else None,
		subject=frappe.utils.strip_html(subject or ""),
		message=Markup(frappe.utils.sanitize_html(message or "")),
	)


def rule_fired(carried: str, people: list[str], doc, words: tuple) -> None:
	"""A standard rule of erpnext's or hrms's fired, told as the type that carries it."""
	notify.notify(carried, people, record=(doc.doctype, doc.name), words=words)


def form_customized(doctype: str) -> None:
	"""A form changed for everybody, told to the administrators: who, and which."""
	notify.notify(
		"Form Customized",
		roles.administrators(),
		link=f"/desk/workspace-field?form={doctype}",
		who=frappe.utils.get_fullname(),
		form=_(doctype),
	)


def intake_changed(doc, changed: list[str]) -> None:
	"""OneAI's switches changed, told to every other administrator in the page's words."""
	from onedesk.one.account import _administrators

	people = [one for one in _administrators() if one != frappe.session.user]
	if not people:
		return
	meta = frappe.get_meta("Reading Settings")
	said = []
	for name in changed:
		label = _(meta.get_label(name))
		if name == "floor":
			said.append(_("{0} to {1}%").format(label, frappe.utils.cint(doc.floor)))
		else:
			said.append(_("{0} on").format(label) if doc.get(name) else _("{0} off").format(label))
	notify.notify(
		"Reading Changed",
		people,
		link="/desk/one?center=ai&at=reading",
		by=frappe.utils.get_fullname(),
		what=", ".join(said),
	)


def holidays_changed(what: str, holiday_list: str) -> None:
	"""The company's holidays changed, told to the administrators."""
	notify.notify(
		"Holidays Changed",
		roles.administrators(),
		link="/desk/one?center=settings&module=OneHR&at=holidays",
		by=frappe.utils.get_fullname(),
		what=what,
		holiday_list=holiday_list,
	)


def holidays_run_out_soon(holiday_list: str, end, left: int) -> None:
	"""The holiday list in force ends soon with nothing after it."""
	from frappe.utils import add_days

	notify.notify(
		"Holidays Run Out Soon",
		roles.administrators(),
		link="/desk/one?center=settings&module=OneHR&at=holidays",
		holiday_list=holiday_list,
		last_day=frappe.utils.formatdate(end),
		days=left,
		first_day=frappe.utils.formatdate(add_days(end, 1)),
	)


def webhooks_failing(rows: list) -> None:
	"""Webhooks whose calls gave up yesterday, told to the administrators."""
	from onedesk.one.account import _administrators

	people = _administrators()
	if not people:
		return
	said = ", ".join(_("{0} ({1})").format(one.webhook, one.calls) for one in rows[:10])
	notify.notify(
		"Webhooks Failing",
		people,
		link="/desk/webhook-request-log?status=Exhausted",
		sender="Administrator",
		webhooks=said,
	)


def _or(said: list[str]) -> str:
	"""Approve, Reject or Send Back."""
	if len(said) < 2:
		return "".join(said)
	return _("{0} or {1}").format(", ".join(said[:-1]), said[-1])


def repeats_failed() -> None:
	"""Hourly: a repeat frappe switched off because the next one could not be
	made, from the hour's Error Log, told to whoever set it up, and accounts
	for an invoice, bill or entry. frappe mails System Managers, nobody's
	role in a workspace."""
	from frappe.utils import add_to_date, now_datetime
	from frappe.utils.user import get_users_with_role

	books = ("Sales Invoice", "Purchase Invoice", "Journal Entry", "Sales Order", "Purchase Order")
	for repeat in dict.fromkeys(
		frappe.get_all(
			"Error Log",
			filters={
				"reference_doctype": "Auto Repeat",
				"creation": [">=", add_to_date(now_datetime(), hours=-1)],
			},
			pluck="reference_name",
		)
	):
		one = frappe.db.get_value(
			"Auto Repeat",
			repeat,
			["owner", "reference_doctype", "reference_document", "disabled"],
			as_dict=True,
		)
		if not one or not one.disabled:
			continue
		people = [
			one.owner,
			*(get_users_with_role("Accounts Manager") if one.reference_doctype in books else []),
		]
		notify.notify(
			"Repeat Failed",
			frappe.get_all("User", filters={"name": ["in", people], "enabled": 1}, pluck="name"),
			record=("Auto Repeat", repeat),
			sender="Administrator",
			kind=_lt(one.reference_doctype),
			document=one.reference_document,
		)


class Reminder(_FrappeReminder):
	"""frappe's Remind Me, told as One's Reminder: frappe writes an Alert,
	which neither pushes nor mails, so a reminder set for the morning was a
	bell entry found in the afternoon."""

	def send_reminder(self):
		if self.notified:
			return
		self.db_set("notified", 1, update_modified=False)
		try:
			notify.notify(
				"Reminder",
				self.user,
				record=(self.reminder_doctype, self.reminder_docname)
				if self.reminder_doctype and self.reminder_docname
				else None,
				sender="Administrator",
				said=self.description or "",
			)
		except Exception:
			self.log_error("Failed to send reminder")


def administrator_removed(doc) -> None:
	"""An administrator no more, told to every other one, and always mailed."""
	from onedesk.one.people import NOT_PEOPLE

	admins = [
		one for one in roles.administrators() if one not in (doc.name, frappe.session.user, *NOT_PEOPLE)
	]
	notify.notify(
		"Administrator Removed",
		admins,
		link="/desk/one?center=account&at=people",
		sender="Administrator",
		person=doc.full_name or doc.name,
		by=frappe.utils.get_fullname(),
	)


def sign_in_rules_changed(said: list[str]) -> None:
	"""Two-factor, the password policy, lockouts or sharing changed, told to
	every other administrator, and always mailed."""
	from onedesk.one.people import NOT_PEOPLE

	admins = [one for one in roles.administrators() if one not in (frappe.session.user, *NOT_PEOPLE)]
	notify.notify(
		"Sign-in Rules Changed",
		admins,
		link="/desk/one?center=settings&module=One&at=signin",
		sender="Administrator",
		by=frappe.utils.get_fullname(),
		what=", ".join(said),
	)


def automations_failing() -> None:
	"""Each morning: automations whose runs failed yesterday, told to the
	administrators, as Webhooks Failing is."""
	from collections import Counter

	from frappe.utils import add_days, getdate

	from onedesk.one.account import _administrators

	rows = Counter(
		frappe.get_all(
			"Automation Run",
			filters=[
				["status", "in", ["Failed", "Partially Failed"]],
				["creation", ">=", add_days(getdate(), -1)],
				["creation", "<", getdate()],
			],
			pluck="automation_title",
		)
	)
	people = _administrators()
	if rows and people:
		notify.notify(
			"Automations Failing",
			people,
			link="/desk/automation",
			sender="Administrator",
			automations=", ".join(_("{0} ({1})").format(title, runs) for title, runs in rows.most_common(10)),
		)


def storage_full() -> None:
	"""A file refused because storage is full, told to the administrators once
	a day: the person refused may be a guest on a link."""
	from onedesk.one import account

	key = "one_cloud_full_told"
	if frappe.cache.get_value(key):
		return
	frappe.cache.set_value(key, 1, expires_in_sec=24 * 60 * 60)
	people = account._administrators()
	if people:
		notify.notify("Storage Full", people, link=account.PAGE, sender="Administrator")


def approval_answered(action, record, state: str) -> None:
	"""A record moved on from a step: whoever made it and whoever sent it to
	the step hear where it went, but whoever moved it."""
	people = [
		one
		for one in (record.owner, action.owner)
		if one not in ("Administrator", "Guest", frappe.session.user)
	]
	if people:
		notify.notify(
			"Approval Answered",
			sorted(set(people)),
			record=(record.doctype, record.name),
			who=frappe.utils.get_fullname(frappe.session.user),
			title=record.get_title() or record.name,
			state=_lt(state),
		)


def approval_decided(doc) -> None:
	"""Whoever asked for a second person's approval (one/second.py), once it
	is approved or refused."""
	from frappe.utils import get_fullname

	notify.notify(
		"Approval Decided",
		doc.asked_by,
		record=("Second Approval", doc.name),
		what=doc.title,
		status=_lt("approved") if doc.status == "Approved" else _lt("refused"),
		by=get_fullname(doc.decided_by),
		remarks=doc.remarks or "",
	)


def export_waiting(row, people: list[str]) -> None:
	"""The administrators, of an export larger than the workspace allows (one/exports.py)."""
	from frappe.utils import fmt_money, get_fullname

	notify.notify(
		"Export Waiting for Approval",
		people,
		record=("Second Approval", row.name),
		who=get_fullname(row.asked_by),
		records=fmt_money(row.records, precision=0),
		doctype=_(row.export_from),
		method=row.method,
	)


def export_held(row) -> None:
	"""Whoever asked for an export by mail that waits for an administrator instead."""
	from frappe.utils import fmt_money

	notify.notify(
		"Export Held",
		row.asked_by,
		record=("Second Approval", row.name),
		records=fmt_money(row.records, precision=0),
		doctype=_(row.export_from),
	)
