"""Training Copies, this workspace's optional service: while it is on, the
workspace says so to One's account every hour (one_admin/sessions.py reads it
to decide whether a copy may be made, and to delete one that has lost it),
and its administrators make, open and end copies from AccountCenter's
Training Copies (account_center/center.py), each asked of OneAdmin with the
workspace's token (one_admin/proxy.py, copies_*). On a copy itself,
`open_on` makes the field's demo company the default once."""

import frappe
from frappe import _

from onedesk.one import account, roles
from onedesk.one_admin import faults
from onedesk.trust_center import services

KEY = "training_copies"
START = "onedesk.one_admin.proxy.copies_start"
KINDS = ("fresh", "demo", "data")
LASTS = ("8 Hours", "1 Day", "7 Days", "30 Days")
OPENED = "one_copy_opened"


def said() -> None:
	"""Hourly: on, and agreed to, or nothing is sent at all."""
	if account.configured():
		services.call(KEY, account.ask, "onedesk.one_admin.proxy.copies_agreed")


def refused(why: str, most: int = 3) -> str:
	"""What an administrator is told when OneAdmin refuses a copy, by the
	key it gave (sessions.why_not_started and start_for)."""
	return {
		"asked": _("Choose what the copy starts from and how long it lasts."),
		"field": _("Choose one of the fields offered."),
		"plan": _("The workspace's plan doesn't include Training Copies."),
		"agreed": _("Training Copies is off for this workspace. Turn it on in Optional Services first."),
		"many": _("The workspace has {0} training copies already. End one first.").format(most),
		"data": _("There's no nightly backup of the workspace yet. Try again tomorrow."),
		"answers": _("The workspace's setup answers aren't kept, so a fresh copy can't be set up like it."),
		"room": _("There's no room for a training copy right now. Try again in an hour."),
	}.get(why) or _("The copy was not made.")


def _plainly(raised: faults.Refused) -> str:
	"""OneAdmin's sentence, in the reader's language where it is one of ours."""
	import re

	return _(re.sub(r"^[\w.]+: ", "", str(raised.detail or raised)).strip())


def _ask(endpoint: str, **params):
	try:
		return account.ask(f"onedesk.one_admin.proxy.{endpoint}", **params)
	except faults.Refused as raised:
		frappe.throw(_plainly(raised), title=_("Training Copies"))


def _fields() -> list[dict]:
	from onedesk.one.registry import fields

	return [{"value": one.id, "label": str(one.label)} for one in fields.FIELDS]


def why_not(offered: bool, on: bool, linked: bool) -> str | None:
	"""Why no copy can be made from here: the workspace is not connected
	(`linked`), its plan has no Training Copies (`plan`), or they are off
	(`agreed`). Pure."""
	if not linked:
		return "linked"
	if not offered:
		return "plan"
	if not on:
		return "agreed"
	return None


def section() -> dict:
	"""AccountCenter's Training Copies: whether a copy may be made and why
	not, the choices a new one offers, and the copies there are."""
	roles.require()
	linked = account.configured()
	why = why_not(services.offered(KEY), services.on(KEY), linked)
	copies, unheard = [], False
	if linked:
		try:
			copies = account.ask("onedesk.one_admin.proxy.copies_listed") or []
		except faults.Refused:
			unheard = True
	return {
		"why_not": why,
		"copies": copies,
		"unheard": unheard,
		"kinds": list(KINDS),
		"lasts": list(LASTS),
		"fields": _fields(),
		"field": frappe.db.get_default("one_field") or "",
	}


@frappe.whitelist(methods=["POST"])
def start(kind: str, lasts: str, field: str | None = None) -> dict:
	"""A new training copy, asked of OneAdmin: only an administrator, only
	while the plan has Training Copies and they are on."""
	roles.require()
	why = why_not(services.offered(KEY), services.on(KEY), account.configured())
	if why == "linked":
		frappe.throw(_("This workspace isn't connected to its account yet, so a copy can't be made."), title=_("Training Copies"))
	if why:
		frappe.throw(refused(why), title=_("Training Copies"))
	if kind not in KINDS or lasts not in LASTS:
		frappe.throw(refused("asked"), title=_("Training Copies"))
	try:
		said()
		made = services.call(KEY, account.ask, START, kind=kind, lasts=lasts, field=field if kind == "demo" else None, by=frappe.session.user) or {}
	except faults.Refused as raised:
		frappe.throw(_plainly(raised), title=_("Training Copies"))
	if made.get("refused"):
		frappe.throw(refused(made["refused"], made.get("most") or 3), title=_("Training Copies"))
	return made


@frappe.whitelist(methods=["POST"])
def end(session: str) -> dict:
	"""A copy deleted now, with everything done in it."""
	roles.require()
	return _ask("copies_end", session=session) or {}


@frappe.whitelist(methods=["POST"])
def open_copy(session: str) -> dict:
	"""A one-time sign-in to a copy, for the administrator asking."""
	roles.require()
	return _ask("copies_sign_in", session=session) or {}


def open_on(conf) -> None:
	"""On a copy from the demo: the company its field opens on
	(`one_copy_company`, one_admin/sessions.py config_for) becomes the
	default, once, as soon as the demo has made it."""
	company = conf.get("one_copy_company")
	if not company or frappe.db.get_default(OPENED) == company or not frappe.db.exists("Company", company):
		return
	frappe.defaults.set_global_default("company", company)
	frappe.db.set_default(OPENED, company)
	frappe.db.commit()
