"""Settings: one place for everything a person or a workspace sets.

Two groups, You for everybody and Workspace for its administrators. Nothing new
is stored: each section reads and writes the records that already hold it.
"""

from typing import Annotated

import frappe
from frappe import _, _lt

from onedesk.one import roles, tell
from onedesk.one.access import all_levels
from onedesk.one.people import APP_SAID, APPS, levels_of
from onedesk.one.sections import as_opened
from onedesk.one.sections import fields as fields_of
from onedesk.one.sections import opened as opened_of

SECTIONS = [
	("notifications", _lt("Notifications"), "bell", "you"),
	("calendar", _lt("Calendar"), "calendar", "you"),
	("memory", _lt("What OneAI Remembers"), "brain", "you"),
	("reads", _lt("What OneAI Reads"), "oneintake", "you"),
	("general", _lt("General"), "building-2", "workspace"),
	("access", _lt("Access"), "shield-check", "workspace"),
	("notification_types", _lt("Workspace Notifications"), "bell-ring", "workspace"),
	("numbering", _lt("Numbering"), "hash", "workspace"),
	("printing", _lt("Printing"), "printer", "workspace"),
	("approvals", _lt("Approvals"), "route", "workspace"),
	("oneai", _lt("OneAI"), "sparkles", "workspace"),
	("intake", _lt("Reading"), "oneintake", "workspace"),
	("holidays", _lt("Holidays"), "calendar-days", "workspace"),
]

# Sections whose row opens a centre over the page rather than drawing one
# (settings.js `show`): OneAI, what it remembers and its reading are AICenter's.
OPENS = ("memory", "oneai", "intake")


NOTIFY = (
	"enabled",
	"enable_email_notifications",
	"enable_email_threads_on_assigned_document",
)

NOTIFY_SAID = {
	"enabled": (
		_lt("Notifications"),
		_lt("Turn off to stop all notifications."),
	),
	"enable_email_notifications": (
		_lt("Also by Email"),
		_lt("Emails you the notifications turned on for email below."),
	),
	"enable_email_threads_on_assigned_document": (
		_lt("Mail About What Is Assigned to You"),
		_lt("Mails you each new mail on a record you were given to do."),
	),
}

INTAKE = ("records", "most_pages", "floor", "audit", "keep_in_place", "quiet_minutes", "household", "submit_einvoices")

SYSTEM = ("date_format", "time_format", "number_format", "first_day_of_the_week", "one_calendar_links")

NEEDS_AI = ("memory", "oneai")
NEEDS_INTAKE = ("reads", "intake")

ON_A_RECORD = ("notification_types", "holidays", "access")

NOTIFICATION_TYPE = (
	"enabled",
	"one_subject",
	"one_message",
	"one_allow_email",
	"one_allow_push",
)


@frappe.whitelist()
@frappe.read_only()
def sections() -> dict:
	"""The sections this person may open, and who they are."""
	from onedesk.one import apps

	admin = roles.administers()
	gone = {*(() if apps.ai_on() else NEEDS_AI), *(() if apps.intake_on() else NEEDS_INTAKE)}
	return {
		"sections": [
			{"key": key, "label": str(label), "icon": icon, "group": group}
			for key, label, icon, group in SECTIONS
			if (not _needs_admin(key) or admin) and key not in gone
		],
		"admin": admin,
		"user": frappe.session.user,
	}


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section."],
	record: Annotated[str | None, "The one record the section is open on, where it lists several."] = None,
) -> dict:
	loaders = {
		"notifications": _notifications,
		"calendar": _calendar,
		"memory": _memory,
		"reads": _reads,
		"general": _general,
		"access": _access,
		"holidays": _holidays,
		"notification_types": _notification_types,
		"numbering": _numbering,
		"printing": _printing,
		"approvals": _approvals,
	}
	if section not in loaders:
		frappe.throw(_("There is no such section."))
	if _group(section) == "workspace":
		roles.require()
	return loaders[section](record) if section in ON_A_RECORD else loaders[section]()


@frappe.whitelist(methods=["POST"])
def save(
	section: Annotated[str, "Which section."],
	values: Annotated[str | dict, "What was changed."],
	opened: Annotated[str | list | None, "The records as the page loaded them: doctype, name and modified."] = None,
	record: Annotated[str | None, "The one record the section is open on, where it lists several."] = None,
) -> dict:
	values = frappe.parse_json(values) or {}
	frappe.flags.one_opened = {f"{one['doctype']}:{one['name']}": one["modified"] for one in frappe.parse_json(opened) or []}
	savers = {
		"notifications": _save_notifications,
		"general": _save_general,
		"holidays": _save_holidays,
		"notification_types": _save_notification_type,
		"access": _save_access,
	}
	if section not in savers:
		frappe.throw(_("There is nothing to save here."))
	if _group(section) == "workspace":
		roles.require()
	if section in ON_A_RECORD:
		record = savers[section](record, values) or record
	else:
		savers[section](values)
	frappe.db.commit()
	said = load(section, record)
	if section in ON_A_RECORD and isinstance(said, dict):
		said["record"] = record
	return said


def _group(section: str) -> str:
	return next((group for key, _label, _icon, group in SECTIONS if key == section), "")


def _needs_admin(section: str) -> bool:
	return _group(section) == "workspace"


def _notifications() -> dict:
	"""A person's own notifications: the bell and email on or off, the browsers
	they turned push on in, and for each kind they can receive, whether it is
	also mailed to them and pushed to them."""
	from frappe.desk.doctype.notification_settings.notification_settings import create_notification_settings

	from onedesk.one import notify, push

	if not frappe.db.exists("Notification Settings", frappe.session.user):
		create_notification_settings(frappe.session.user)
	doc = frappe.get_doc("Notification Settings", frappe.session.user)
	mailed = {row.notification_type for row in doc.email_notification_types}
	pushed = {row.notification_type for row in doc.get(notify.PUSH_FIELD) or []}
	fields = fields_of("Notification Settings", NOTIFY)
	for field in fields:
		label, description = NOTIFY_SAID[field["fieldname"]]
		field.update({"fieldtype": "Switch", "label": str(label), "description": str(description)})
		if field["fieldname"] not in ("enabled", "enable_email_notifications"):
			field["depends_on"] = "eval:doc.enabled && doc.enable_email_notifications"
	values = {name: doc.get(name) for name in NOTIFY}
	groups: dict[str, list] = {}
	esc = frappe.utils.escape_html
	for one in notify.choosable():
		kind, email, pushing = (_kind_field(prefix, one["name"]) for prefix in ("kind", "email", "push"))
		fields += [
			{
				"fieldname": kind,
				"fieldtype": "HTML",
				"options": f'<div class="os-kind-name">{esc(one["label"])}'
				+ ("<span data-oneai-tag></span>" if one.get("oneai") else "")
				+ f'</div><div class="os-kind-about">{esc(_said_of(one))}</div>',
				"depends_on": "eval:doc.enabled",
			},
			{
				"fieldname": email,
				"fieldtype": "Switch",
				"label": str(_("Email")),
				"read_only": 0 if one["allowed"] else 1,
				"depends_on": "eval:doc.enabled",
			},
			{
				"fieldname": pushing,
				"fieldtype": "Switch",
				"label": str(_("Push")),
				"read_only": 0 if one["push"] else 1,
				"depends_on": "eval:doc.enabled",
			},
		]
		values[email] = 1 if one["always"] or (one["allowed"] and one["name"] in mailed) else 0
		values[pushing] = 1 if one["push"] and one["name"] in pushed else 0
		groups.setdefault(one["app"] or "", []).append([kind, email, pushing])
	return {
		"fields": fields,
		"values": values,
		"groups": [
			{"app": _(app) if app else str(_("Across One")), "mark": _mark(app), "rows": rows}
			for app, rows in groups.items()
		],
		"push": push.devices(),
		"opened": opened_of(doc),
	}


MARK_OF = {"OneCloud": "onestorage", "OneWriter": "onedoc", "OneWorkbook": "onesheet"}


def _mark(app: str) -> str | None:
	"""The mark drawn beside an app's name (brand/): One's own for what every
	app shares, none for the workspace's rules. Pure."""
	if not app:
		return "one"
	if not app.startswith("One"):
		return None
	return MARK_OF.get(app, app.lower())


def _said_of(one: dict) -> str:
	"""What a kind is, and why a tick cannot be changed when it cannot."""
	said = [one["about"]]
	if one.get("always"):
		said.append(_("Always mailed, so you can answer it by replying."))
	elif not one["allowed"]:
		said.append(_("Not mailed in this workspace."))
	if not one["push"]:
		said.append(_("Not pushed in this workspace."))
	return " ".join(filter(None, said))


def _kind_field(prefix: str, name: str) -> str:
	"""A kind's field, named after it: `email_shared_with_you`. Pure."""
	import re

	return f"{prefix}_" + re.sub(r"\W+", "_", name.lower()).strip("_")


def _save_notifications(values: dict) -> None:
	"""Their own switches, and their email and push choices for the kinds
	shown. A kind not shown to them (another role's, or not sent here that way)
	is left as it was."""
	from onedesk.one import notify

	doc = as_opened(frappe.get_doc("Notification Settings", frappe.session.user))
	doc.update({name: values[name] for name in NOTIFY if name in values})
	kinds = notify.choosable()
	for field, prefix, may in (
		(notify.EMAIL_FIELD, "email", lambda one: one["allowed"]),
		(notify.PUSH_FIELD, "push", lambda one: one["push"]),
	):
		chosen = {
			one["name"]: frappe.utils.cint(values.get(_kind_field(prefix, one["name"])))
			for one in kinds
			if may(one) and _kind_field(prefix, one["name"]) in values
		}
		for one in kinds:
			if one["name"] in chosen:
				chosen.update(dict.fromkeys(one.get("twins", []), chosen[one["name"]]))
		kept = [row.notification_type for row in doc.get(field) or [] if row.notification_type not in chosen]
		doc.set(field, [{"notification_type": name} for name in kept + [name for name, on in chosen.items() if on]])
	doc.save(ignore_permissions=True)


def _calendar() -> dict:
	from onedesk.one_calendar import feed

	return {"link": feed.current(), "allowed": feed.allowed()}


def _memory() -> dict:
	"""What OneAI keeps for the reader, with when and the record each is about,
	and what the workspace's administrators wrote down for everybody, which
	OneAI also uses and which the reader can read but not change."""
	rows = frappe.get_all(
		"AI Memory",
		filters={"owner": frappe.session.user},
		fields=["name", "fact", "about_doctype", "about_name", "creation"],
		order_by="creation desc",
		limit=200,
	)
	for one in rows:
		one["about_title"] = _title_of(one.about_doctype, one.about_name)
	knowledge = frappe.get_all(
		"AI Knowledge",
		filters={"enabled": 1},
		fields=["title", "applies_to"],
		order_by="title asc",
		ignore_permissions=True,
	)
	return {
		"facts": rows,
		"knowledge": [{"title": one.title, "applies_to": _(one.applies_to) if one.applies_to else None} for one in knowledge],
	}


def _title_of(doctype: str | None, name: str | None) -> str | None:
	"""A record as a person reads it: its title, or its id where it has none."""
	if not doctype or not name or not frappe.db.exists("DocType", doctype):
		return None
	field = frappe.get_meta(doctype).title_field
	return (frappe.db.get_value(doctype, name, field) if field else None) or name


def _mine(name: str):
	"""One of the reader's own memories. Administrator is not held by the
	doctype's if-owner rule, so the owner is checked here too."""
	doc = frappe.get_doc("AI Memory", name)
	if doc.owner != frappe.session.user:
		frappe.throw(_("That is not one of your memories."), frappe.PermissionError)
	return doc


@frappe.whitelist(methods=["POST"])
def keep(
	fact: Annotated[str, "What OneAI should keep in mind."],
	about_doctype: Annotated[str | None, "The type of record it is about."] = None,
	about_name: Annotated[str | None, "That record."] = None,
	name: Annotated[str | None, "The memory to change; empty for a new one."] = None,
) -> dict:
	"""A memory the reader adds or corrects themselves."""
	said = " ".join((fact or "").split())[:500]
	if not said:
		frappe.throw(_("Say what OneAI should keep in mind."))
	about = {"about_doctype": about_doctype or None, "about_name": about_name or None}
	if about["about_doctype"] and about["about_name"] and not frappe.has_permission(about["about_doctype"], "read", doc=about["about_name"]):
		frappe.throw(_("You cannot open that record."), frappe.PermissionError)
	if name:
		doc = _mine(name)
		doc.update({"fact": said, **about})
		doc.save()
	else:
		frappe.get_doc({"doctype": "AI Memory", "fact": said, **about}).insert()
	return _memory()


@frappe.whitelist(methods=["POST"])
def forget(name: Annotated[str, "The AI Memory to forget."]) -> dict:
	"""One thing OneAI remembers about the reader, forgotten."""
	doc = _mine(name)
	doc.check_permission("delete")
	doc.delete()
	return _memory()


@frappe.whitelist(methods=["POST"])
def forget_all() -> dict:
	"""Everything OneAI remembers about the reader, forgotten."""
	for name in frappe.get_all("AI Memory", filters={"owner": frappe.session.user}, pluck="name"):
		frappe.delete_doc("AI Memory", name)
	return _memory()


def _company():
	name = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	return frappe.get_doc("Company", name) if name else None


def _general() -> dict:
	from onedesk.one_calendar import feed

	company = _company()
	system = frappe.get_single("System Settings")
	account = frappe.get_single("Workspace Account")
	defaults = frappe.get_single("Global Defaults")
	address = _company_address(company)
	fields = (
		fields_of("Company", ("company_logo", *ON_DOCUMENTS, *ON_SCREEN))
		+ fields_of("Address", ADDRESS)
		+ _zones(_switches(fields_of("System Settings", ("language", "time_zone", *SYSTEM, *SIGNING_IN, *FOOTER))))
		+ _switches(fields_of("Global Defaults", AMOUNTS))
	)
	return {
		"name": account.workspace_name,
		"company": company.company_name if company else None,
		"country": company.country if company else system.country,
		"currency": company.default_currency if company else None,
		"fields": [{**one, **_said_on_general(one["fieldname"], system)} for one in fields] + _signing_in_fields() + _sharing_fields(),
		"values": {
			"company_logo": company.company_logo if company else None,
			**{name: company.get(name) if company else None for name in (*ON_DOCUMENTS, *ON_SCREEN)},
			**{name: address.get(name) if address else None for name in ADDRESS},
			"language": system.language,
			"time_zone": system.time_zone,
			**{name: system.get(name) for name in (*SYSTEM, *SIGNING_IN, *FOOTER)},
			**{name: defaults.get(name) for name in AMOUNTS},
			"allow_login_after_fail": str(system.allow_login_after_fail or 60),
			"one_record_sharing": 0 if system.disable_document_sharing else 1,
			"one_calendar_links": 1 if feed.allowed() else 0,
			"one_two_factor": _two_factor(system),
			"one_password": str(system.minimum_password_score or "") if system.enable_password_policy else "",
		},
		"opened": opened_of(company, system, address, defaults),
	}


AMOUNTS = ("hide_currency_symbol", "disable_rounded_total", "disable_in_words")

ON_DOCUMENTS = ("one_brand_colour", "phone_no", "email", "website", "tax_id")
ON_SCREEN = ("one_frame_colour",)
ADDRESS = ("address_line1", "address_line2", "city", "state", "pincode")


def _company_address(company):
	"""The company's own primary address, as ERPNext finds it for a document."""
	if not company:
		return None
	name = frappe.db.get_value(
		"Address",
		{"is_your_company_address": 1, "name": ["in", _linked_addresses(company.name)]},
		"name",
		order_by="is_primary_address desc, modified desc",
	)
	return frappe.get_doc("Address", name) if name else None


def _linked_addresses(company: str) -> list[str]:
	return frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Company", "link_name": company},
		pluck="parent",
	) or [""]


def _save_company_address(company, values: dict) -> None:
	wanted = {name: (values.get(name) or "").strip() for name in ADDRESS if name in values}
	if not wanted:
		return
	address = _company_address(company)
	if not address:
		if not wanted.get("address_line1"):
			return
		address = frappe.new_doc("Address")
		address.update(
			{
				"address_title": company.company_name,
				"address_type": "Billing",
				"country": company.country,
				"is_your_company_address": 1,
				"is_primary_address": 1,
				"links": [{"link_doctype": "Company", "link_name": company.name}],
			}
		)
	else:
		as_opened(address)
	if all(address.get(name) == value for name, value in wanted.items()) and not address.is_new():
		return
	address.update(wanted)
	address.save(ignore_permissions=True)


SIGNING_IN = (
	"two_factor_method",
	"session_expiry",
	"one_login_with_passkey",
	"login_with_email_link",
	"deny_multiple_sessions",
	"allow_consecutive_login_attempts",
	"allow_login_after_fail",
	"force_user_to_reset_password",
)

FOOTER = ("email_footer_address",)

LOCKOUT = (("60", _lt("1 minute")), ("300", _lt("5 minutes")), ("900", _lt("15 minutes")), ("3600", _lt("1 hour")))

EXPIRY = (
	("08:00", _lt("8 hours")),
	("24:00", _lt("1 day")),
	("168:00", _lt("1 week")),
	("240:00", _lt("10 days")),
	("720:00", _lt("30 days")),
)

GENERAL_SAID = {
	"company_logo": _lt("On printed and sent invoices, quotes and orders."),
	"one_brand_colour": _lt("Used for the company name, lines and banner in letter heads."),
	"one_frame_colour": _lt("The rail and the bars around every screen, for everyone. Leave it empty for One's own."),
	"language": _lt("For everyone who hasn't chosen their own in Profile."),
	"time_zone": _lt("For everyone who hasn't chosen their own in Profile."),
	"one_login_with_passkey": _lt("People sign in with the passkey on their own device, without a password."),
	"session_expiry": _lt("How long someone stays signed in while inactive."),
	"two_factor_method": _lt("An authenticator app on their phone, or a code by email."),
	"email_footer_address": _lt("At the foot of every mail the workspace sends. Leave it empty for none."),
	"login_with_email_link": _lt("People can sign in with a link sent to their email instead of a password."),
	"deny_multiple_sessions": _lt("Signing in somewhere new signs a person out everywhere else."),
	"allow_consecutive_login_attempts": _lt("After this many wrong passwords in a row, signing in is refused for a while."),
	"allow_login_after_fail": _lt("How long signing in is refused after too many wrong passwords."),
	"force_user_to_reset_password": _lt("Then a new one is asked for at sign-in. 0 means they never expire."),
	"hide_currency_symbol": _lt("Amounts are shown without their currency symbol."),
	"disable_rounded_total": _lt("Sales and purchases are not rounded to a whole amount."),
	"disable_in_words": _lt("Sales and purchases don't say their total in words."),
}

GENERAL_LABELS = {
	"one_login_with_passkey": _lt("Passkey Sign-in"),
	"email_footer_address": _lt("Address in Mails"),
	"login_with_email_link": _lt("Email Link Sign-in"),
	"deny_multiple_sessions": _lt("One Device at a Time"),
	"allow_consecutive_login_attempts": _lt("Wrong Passwords Before a Lockout"),
	"allow_login_after_fail": _lt("Locked Out For"),
	"force_user_to_reset_password": _lt("Passwords Expire After (Days)"),
}


def _said_on_general(fieldname: str, system) -> dict:
	said = {"description": str(GENERAL_SAID[fieldname])} if fieldname in GENERAL_SAID else {}
	if fieldname in GENERAL_LABELS:
		said["label"] = str(GENERAL_LABELS[fieldname])
	if fieldname == "allow_login_after_fail":
		options = [{"value": value, "label": str(label)} for value, label in LOCKOUT]
		now = str(system.allow_login_after_fail or 60)
		if now not in dict(LOCKOUT):
			options.append({"value": now, "label": _("{0} seconds").format(now)})
		said.update({"fieldtype": "Select", "options": options})
	if fieldname == "session_expiry":
		options = [{"value": value, "label": str(label)} for value, label in EXPIRY]
		if system.session_expiry and system.session_expiry not in dict(EXPIRY):
			options.append({"value": system.session_expiry, "label": _("{0} hours").format(system.session_expiry.split(":")[0])})
		said.update({"fieldtype": "Select", "options": options, "label": _("Signed Out After")})
	if fieldname == "two_factor_method":
		said.update(
			{
				"options": [{"value": "OTP App", "label": _("Authenticator App")}, {"value": "Email", "label": _("Email")}],
				"label": _("The Code Comes From"),
				"depends_on": "eval:doc.one_two_factor && doc.one_two_factor != 'off'",
			}
		)
	return said


def _signing_in_fields() -> list:
	"""Two of System Settings' rules as one choice each: two-factor is a switch
	plus a flag on every role, and the password rule a switch plus a score."""
	return [
		{
			"fieldname": "one_two_factor",
			"fieldtype": "Select",
			"label": _("Two-Factor Sign-in"),
			"options": [
				{"value": "off", "label": _("Off")},
				{"value": "admins", "label": _("Administrators")},
				{"value": "everybody", "label": _("Everyone")},
			],
			"description": _("A code after the password. Each person sets it up the next time they sign in."),
		},
		{
			"fieldname": "one_password",
			"fieldtype": "Select",
			"label": _("Passwords"),
			"options": [
				{"value": "", "label": _("Any password")},
				{"value": "2", "label": _("Hard to guess")},
				{"value": "3", "label": _("Very hard to guess")},
				{"value": "4", "label": _("Strongest")},
			],
			"description": _("Checked when someone sets or changes their password."),
		},
	]


def _sharing_fields() -> list:
	"""Frappe's switch says sharing is off; the page's says it is on."""
	return [
		{
			"fieldname": "one_record_sharing",
			"fieldtype": "Switch",
			"label": _("Record Sharing"),
			"description": _("Lets people share a record with someone who can't otherwise open it."),
		}
	]


EVERYBODY = "All"


def _two_factor(system) -> str:
	if not system.enable_two_factor_auth:
		return "off"
	if frappe.db.get_value("Role", EVERYBODY, "two_factor_auth"):
		return "everybody"
	return "admins"


def _zones(fields: list) -> list:
	"""System Settings' form fills its Time Zone list in the browser, so the
	field arrives with none: shown blank, and saved blank, which frappe refuses."""
	from frappe.utils.momentjs import get_all_timezones

	return [{**one, "options": "\n".join(get_all_timezones())} if one["fieldname"] == "time_zone" else one for one in fields]


def _switches(fields: list) -> list:
	"""A Check on a settings page is drawn as frappe's Switch, as the rest of
	Settings draws them. The value is the same 0 or 1."""
	return [{**one, "fieldtype": "Switch"} if one["fieldtype"] == "Check" else one for one in fields]


def _save_general(values: dict) -> None:
	company = _company()
	if company:
		changed = {
			name: values[name] or None
			for name in ("company_logo", *ON_DOCUMENTS, *ON_SCREEN)
			if name in values and (values[name] or None) != (company.get(name) or None)
		}
		if changed:
			as_opened(company).update(changed)
			company.save(ignore_permissions=True)
		if "one_frame_colour" in changed:
			from onedesk.one import company as workspace_company

			frappe.publish_realtime(
				"one_frame",
				{"colour": company.one_frame_colour or "", "ink": workspace_company.frame_ink(company.one_frame_colour)},
				after_commit=True,
			)
		_save_company_address(company, values)
	_save_amounts(values)
	system = as_opened(frappe.get_single("System Settings"))
	guarded = (*SIGNING_IN, "enable_two_factor_auth", "enable_password_policy", "minimum_password_score", "disable_document_sharing")
	was = {name: system.get(name) for name in guarded}
	system.update({name: values[name] for name in ("language", "time_zone", *SYSTEM, *SIGNING_IN, *FOOTER) if name in values})
	if "one_record_sharing" in values:
		system.disable_document_sharing = 0 if frappe.utils.cint(values["one_record_sharing"]) else 1
	if "one_password" in values:
		system.enable_password_policy = 1 if values["one_password"] else 0
		system.minimum_password_score = values["one_password"] or system.minimum_password_score
	wanted = values.get("one_two_factor") or "off"
	if "one_two_factor" in values:
		system.enable_two_factor_auth = 0 if wanted == "off" else 1
	system.save(ignore_permissions=True)
	changed = [name for name in guarded if str(was[name] or "") != str(system.get(name) or "")]
	if changed:
		meta = frappe.get_meta("System Settings")
		tell.sign_in_rules_changed([_(meta.get_label(name)) for name in changed])
	if "one_two_factor" in values and wanted != "off":
		frappe.db.set_value("Role", roles.ADMINISTRATOR, "two_factor_auth", 1)
		frappe.db.set_value("Role", EVERYBODY, "two_factor_auth", 1 if wanted == "everybody" else 0)


def _save_amounts(values: dict) -> None:
	"""Global Defaults' on_update hides or shows the rounded total and the
	amount in words on every sale and purchase form."""
	defaults = frappe.get_single("Global Defaults")
	wanted = {name: frappe.utils.cint(values[name]) for name in AMOUNTS if name in values}
	if any(frappe.utils.cint(defaults.get(name)) != value for name, value in wanted.items()):
		as_opened(defaults).update(wanted)
		defaults.save(ignore_permissions=True)


def _intake() -> dict:
	"""OneAI's reading settings, with the defaults written in where the record is
	empty (an empty floor is 70%, not nothing), and the month: what arrived,
	what OneAI handled, what needed a person, what was undone, and what waits
	now, for everybody."""
	from onedesk.one_ai.reading import act, pipeline

	doc = frappe.get_single("Reading Settings")
	values = {name: doc.get(name) for name in INTAKE}
	values["most_pages"] = values["most_pages"] or pipeline.MOST_PAGES
	values["floor"] = values["floor"] or act.FLOOR
	fields = [
		{**one, "fieldtype": "Switch"} if one["fieldtype"] == "Check" else one
		for one in fields_of("Reading Settings", INTAKE)
	]
	from onedesk.one_ai.reading import switches

	return {
		"fields": fields,
		"values": values,
		"month": _intake_month(),
		"marks": {app: _mark(app) for app in ("OneBook", "OneMail", "OneCloud")},
		**switches.overview(),
		"opened": opened_of(doc),
	}


def _reads() -> dict:
	"""The mailboxes and folders OneAI reads that are the reader's to switch:
	the mailboxes they hold and the folders they may change. Every one of
	them, for an administrator, is AICenter › Reading."""
	from onedesk.one import apps
	from onedesk.one_ai.reading import switches

	if not apps.intake_on():
		return {"off": True}
	return {**switches.overview(mine=True), "marks": {app: _mark(app) for app in ("OneMail", "OneCloud")}}


INTAKE_HR = ("one_ai_screen", "one_ai_prepare", "one_ai_transcribe", "one_ai_grievances")


def _intake_month() -> dict:
	from frappe.utils import get_first_day, today

	from onedesk.one_ai.reading import digest, inbox

	month = digest.this_month()
	start = get_first_day(today())
	waiting = frappe.db.sql(f"select count(*) from `tabReading` r where {inbox._box('waiting')}")[0][0]
	undone = frappe.db.count("Reading Action", {"level": "Undone", "modified": [">=", start]})
	return {**month, "waiting": int(waiting or 0), "undone": int(undone or 0)}


TOLD_OF = ("audit", "household", "submit_einvoices", "floor")


def _save_intake(values: dict) -> None:
	from onedesk.one_ai.reading import act

	doc = as_opened(frappe.get_single("Reading Settings"))

	def meant(name):
		value = frappe.utils.flt(doc.get(name))
		return (value or act.FLOOR) if name == "floor" else value

	was = {name: meant(name) for name in TOLD_OF}
	doc.update({name: values[name] for name in INTAKE if name in values})
	doc.save(ignore_permissions=True)
	changed = [name for name in TOLD_OF if was[name] != meant(name)]
	if changed:
		tell.intake_changed(doc, changed)


def _holidays(record: str | None = None) -> dict:
	"""One holiday list, as the page edits it: the list in force today unless
	another is asked for (next year's). Its day off, its country and its
	public holidays are the form; the week's days off are made from the day
	off rather than listed (one/holidays.py)."""
	from onedesk.one import holidays

	held = holidays.company()
	now = holidays.in_force(held=held)
	name = record if record and frappe.db.exists("Holiday List", record) else now
	if not name:
		return {"fields": [], "values": {}, "empty": True, "opened": []}
	doc = frappe.get_doc("Holiday List", name)
	public = [one for one in doc.holidays if not one.weekly_off]
	upcoming = [one for one in public if frappe.utils.getdate(one.holiday_date) >= frappe.utils.getdate(frappe.utils.today())]
	off = holidays.days_off(doc)
	fields = [
		{
			"fieldname": "weekly_offs",
			"fieldtype": "MultiCheck",
			"label": _("Days Off Each Week"),
			"columns": 4,
			"sort_options": False,
			"options": [{"label": _(day), "value": day, "checked": day in off} for day in holidays.WEEK],
			"description": _("Every one of these days in the list is a day off. Tick two for a weekend of two days."),
		},
		*fields_of("Holiday List", ("country", "subdivision")),
	]
	for one in fields:
		if one["fieldname"] == "country":
			one.update({"label": _("Country"), "options": holidays.countries(), "description": None})
		elif one["fieldname"] == "subdivision":
			one.update({"label": _("State or Region"), "options": holidays.subdivisions(doc.country) if doc.country else [], "description": _("Some countries have holidays only in part of the country.")})
	fields.append(
		{
			"fieldname": "holidays",
			"fieldtype": "Table",
			"label": _("Public Holidays"),
			"fields": [
				{"fieldname": "holiday_date", "fieldtype": "Date", "label": _("Date"), "in_list_view": 1, "reqd": 1, "columns": 3},
				{"fieldname": "description", "fieldtype": "Data", "label": _("Holiday"), "in_list_view": 1, "reqd": 1, "columns": 7},
			],
		}
	)
	rows = [{"holiday_date": str(one.holiday_date), "description": frappe.utils.strip_html_tags(one.description or "")} for one in public]
	fields[-1]["data"] = [dict(one) for one in rows]
	next_list = holidays.after(name, held)
	return {
		"fields": fields,
		"values": {
			"country": doc.country,
			"subdivision": doc.subdivision,
			"holidays": rows,
		},
		"list": {
			"name": doc.name,
			"from_date": str(doc.from_date),
			"to_date": str(doc.to_date),
			"days_left": frappe.utils.date_diff(doc.to_date, frappe.utils.today()),
			"in_force": name == now,
			"weekly": off,
			"days_off": len(doc.holidays) - len(public),
			"public": len(public),
		},
		"coming": [{"date": str(one.holiday_date), "what": frappe.utils.strip_html_tags(one.description or "")} for one in upcoming[:1]],
		"next": next_list,
		"now": now,
		"elsewhere": holidays.elsewhere(held),
		"opened": opened_of(doc),
	}


def _save_holidays(record: str | None, values: dict) -> str:
	"""The list's day off, country and public holidays, saved against when the
	page loaded it. A new day off remakes the week's days off; the other
	administrators and the HR managers hear what changed."""
	from onedesk.one import holidays

	name = record or holidays.in_force()
	doc = as_opened(frappe.get_doc("Holiday List", name))
	was_off = holidays.days_off(doc)
	was = {str(one.holiday_date): frappe.utils.strip_html_tags(one.description or "") for one in doc.holidays if not one.weekly_off}
	wanted = {}
	for one in values.get("holidays") or []:
		if one.get("holiday_date"):
			wanted[str(frappe.utils.getdate(one["holiday_date"]))] = (one.get("description") or "").strip() or _("Holiday")
	off = [day for day in holidays.WEEK if day in (values["weekly_offs"] if "weekly_offs" in values else was_off)]
	doc.country = values.get("country") or None
	doc.subdivision = (values.get("subdivision") or None) if doc.country else None
	doc.set("holidays", [])
	for day, what in sorted(wanted.items()):
		doc.append("holidays", {"holiday_date": day, "description": what, "weekly_off": 0})
	holidays.set_days_off(doc, off)
	doc.flags.ignore_permissions = True
	doc.save()
	said = []
	if off != was_off:
		said.append(_("the days off each week are now {0}").format(", ".join(_(day) for day in off) or _("none")))
	added = [day for day in wanted if day not in was]
	dropped = [day for day in was if day not in wanted]
	renamed = [day for day in wanted if day in was and was[day] != wanted[day]]
	for label, days, names in (
		(_("added {0}"), added, wanted),
		(_("removed {0}"), dropped, was),
		(_("renamed {0}"), renamed, wanted),
	):
		if days:
			shown = ", ".join(f"{names[day]} ({frappe.utils.formatdate(day)})" for day in sorted(days)[:3])
			more = len(days) - 3
			said.append(label.format(shown + (" " + _("and {0} more").format(more) if more > 0 else "")))
	if said:
		tell.holidays_changed("; ".join(said), doc.name)
	return doc.name


def _access(record: str | None = None) -> dict:
	"""Workspace > Access: every level of each app, its User and Manager and
	the workspace's own between; or one level, as a form (one/access.py)."""
	from onedesk.one import access

	if record and record.startswith("level:"):
		return _level_page(record.split(":", 1)[1])
	if record and record.startswith("profile:"):
		return _profile_page(record.split(":", 1)[1])
	if record and record.startswith("group:"):
		return _group_page(record.split(":", 1)[1])
	rows = []
	for name, icon, _used, _managed in APPS:
		for tier in access.tiers(name):
			rows.append(
				{
					"key": access.key_of(name, tier),
					"name": tier,
					"own": int(tier not in access.BASE),
					"app": name,
					"icon": icon,
					"people": len(access.people_at(name, tier)),
				}
			)
	return {
		"apps": [{"name": name, "icon": icon} for name, icon, _used, _managed in APPS],
		"levels": rows,
		"profiles": access.profiles(),
		"groups": access.groups(),
	}


def _profile_page(name: str) -> dict:
	"""One profile as a form: its name and a level per app, as a person's page
	sets them."""
	from onedesk.one import access

	said = access.profile(name)
	own = all_levels()
	fields = [{"fieldname": "title", "fieldtype": "Data", "label": _("Name"), "reqd": 1}] + [
		{"fieldname": f"app_{icon}", "fieldtype": "Select", "label": app, "options": levels_of(app, own), "description": str(APP_SAID[app])}
		for app, icon, _used, _managed in APPS
	]
	return {
		"profile": said,
		"apps": [{"name": app, "icon": icon} for app, icon, _used, _managed in APPS],
		"fields": fields,
		"values": {"title": name, **{f"app_{icon}": said["levels"].get(app, "None") for app, icon, _used, _managed in APPS}},
		"opened": opened_of(frappe.get_doc("Role Profile", name)),
	}


def _group_page(name: str) -> dict:
	"""One group as a form: its name and who is in it, in frappe's own
	multi-pick of its members."""
	doc = frappe.get_doc("User Group", name)
	return {
		"group": {"name": doc.name, "members": len(doc.user_group_members)},
		"fields": [
			{"fieldname": "title", "fieldtype": "Data", "label": _("Name"), "reqd": 1},
			{"fieldname": "members", "fieldtype": "Table MultiSelect", "label": _("Members"), "options": "User Group Member"},
		],
		"values": {"title": doc.name, "members": [{"user": one.user} for one in doc.user_group_members]},
		"opened": opened_of(doc),
	}


def _level_page(key: str) -> dict:
	"""One level as a form: its name, and what it may do on each kind of
	record, in frappe's table, one tick per right."""
	from onedesk.one import access

	said = access.level(key)
	options = sorted(
		({"value": one, "label": _(one)} for one in set(access.kinds(said["app"])) - abilities_doctypes()),
		key=lambda one: one["label"],
	)
	table = {
		"fieldname": "rows",
		"fieldtype": "Table",
		"label": "",
		"fields": [
			{"fieldname": "doctype", "fieldtype": "Autocomplete", "label": _("Record Type"), "options": options, "in_list_view": 1, "reqd": 1, "columns": 2},
			*[
				{"fieldname": right, "fieldtype": "Check", "label": _(access.SAID[right]), "in_list_view": 1, "columns": 1}
				for right in access.RIGHTS
			],
		],
	}
	table["data"] = [dict(one) for one in said["rows"]]
	people = frappe.get_all("User", filters={"name": ["in", said["people"] or [""]]}, fields=["name", "full_name", "user_image"])
	fields = [table, *_ability_fields(said["app"], said["abilities"])]
	if said["own"]:
		fields.insert(0, {"fieldname": "title", "fieldtype": "Data", "label": _("Name"), "reqd": 1})
	carrier = said["name"] if said["own"] else None
	return {
		"level": {**said, "people": people, "icon": next(icon for app, icon, _u, _m in APPS if app == said["app"])},
		"fields": fields,
		"values": {
			"title": said["name"],
			"rows": said["rows"],
			**{f"ability_{one['key']}": one["value"] for one in said["abilities"]},
		},
		"abilities": [
			{"fieldname": f"ability_{one['key']}", "group": one["group"]} for one in said["abilities"]
		],
		"matrix": int(bool(options or said["rows"])),
		"opened": [{"doctype": "Role", "name": carrier, "modified": str(frappe.db.get_value("Role", carrier, "modified"))}] if carrier else [],
	}


def abilities_doctypes() -> set:
	from onedesk.one import abilities

	return abilities.doctypes()


def _ability_fields(app: str, held: list[dict]) -> list[dict]:
	"""A level's abilities as fields: a switch, or a choice of scope from the
	least the level can have (User's) up."""
	from onedesk.one import abilities

	declared = abilities.of_app(app)
	if not declared:
		return []
	names = getattr(declared, "SCOPE_LABELS", {})
	fields = []
	for one in held:
		field = {"fieldname": f"ability_{one['key']}", "label": one["label"], "description": str(one.get("about") or "")}
		if one["kind"] == "switch":
			fields.append({**field, "fieldtype": "Switch", "read_only": int(bool(one["least"]))})
			continue
		order = abilities.SCOPES
		said = {**names, **({"none": one["none"]} if one.get("none") else {})}
		fields.append(
			{
				**field,
				"fieldtype": "Select",
				"options": [
					{"value": scope, "label": str(said.get(scope) or scope)}
					for scope in order[order.index(one["least"]) :]
				],
			}
		)
	return fields


def _save_access(record: str | None, values: dict) -> str:
	"""A level's name and what it may do, a profile or a group, saved as
	one/access.py says it may be."""
	from onedesk.one import access

	kind, _sep, name = (record or "").partition(":")
	if kind == "level":
		said = access.level(name)
		rows = values["rows"] if "rows" in values else said["rows"]
		held = {
			one["key"]: values.get(f"ability_{one['key']}", one["value"]) for one in said["abilities"]
		}
		return "level:" + access.save_level(name, values.get("title") or name, rows, held if held else None)
	if kind == "profile":
		levels = access.profile(name)["levels"]
		levels.update({app: values[f"app_{icon}"] for app, icon, _used, _managed in APPS if values.get(f"app_{icon}")})
		return "profile:" + access.save_profile(name, values.get("title") or name, levels)
	if kind == "group":
		doc = frappe.get_doc("User Group", name)
		members = [one.get("user") for one in values["members"]] if "members" in values else [one.user for one in doc.user_group_members]
		return "group:" + access.save_group(name, values.get("title") or name, [one for one in members if one])
	frappe.throw(_("There is nothing to save here."))


def _numbering() -> dict:
	"""Every kind of record the administrator may renumber (one/numbering.py)."""
	from onedesk.one import numbering

	return {"rows": numbering.doctypes()}


def _approvals() -> dict:
	"""Every approval, and how many steps it has (one/approvals.py)."""
	from onedesk.one import approvals

	return {"rows": approvals.approvals()}


def _printing() -> dict:
	"""The workspace's letter heads and its own print formats (one/printing.py)."""
	from onedesk.one import printing

	company = _company()
	heads = printing.letter_heads()
	doc = {"company": company.name if company else None}
	for one in heads:
		one["drawn_top"], one["drawn_foot"] = (_drawn(one.get(key), doc) for key in ("content", "footer"))
	return {
		"letter_heads": heads,
		"formats": printing.formats(),
		"company_logo": company.company_logo if company else None,
	}


def _drawn(template: str | None, doc: dict) -> str:
	if not template or "{" not in template:
		return template or ""
	try:
		return frappe.utils.jinja.render_template(template, {"doc": frappe._dict(doc)})
	except Exception:
		return ""


def _notification_types(record: str | None = None) -> dict:
	"""Every notification One sends, by app, and the workspace's own rules; or
	the type or rule that is open (`rule:` and its name, or `rule:new`)."""
	if record and record.startswith("rule:"):
		return _rule(record[5:])
	if record:
		return _notification_type(record)
	from onedesk.one import notify, rules

	declared = notify.declared()
	rows = frappe.get_all(
		"Notification Type",
		fields=["name", "enabled", "one_rule", *notify.FIELDS],
		order_by="one_app asc, name asc",
	)
	apps: dict[str, list] = {}
	for row in rows:
		if row.one_rule:
			continue
		one = declared.get(row.name) or {}
		apps.setdefault(row.one_app or "", []).append(
			{
				"name": row.name,
				"label": _(row.name),
				"about": _(row.one_about) if row.one_about else None,
				"to": notify.to(row.name),
				"enabled": row.enabled,
				"edited": bool(row.one_default_subject)
				and (row.one_subject != row.one_default_subject or row.one_message != row.one_default_message),
				"outside": row.one_outside,
				"required": bool(one.get("required")),
				"always": bool(one.get("always_mailed")),
				"ours": bool(one),
				"upstream": notify.upstream(one),
				"mailed_by": one["app"] if one.get("mailed_by") else "",
				"email": row.one_allow_email if one else 1,
				"email_default": row.one_email_default,
				"push": row.one_allow_push if one else 0,
				"push_default": row.one_push_default,
			}
		)
	made = frappe.get_all(
		"Notification",
		filters={"one_rule": 1},
		fields=["name", "enabled", "document_type", "event", "date_changed", "days_in_advance", "value_changed"],
		order_by="name asc",
	)
	return {
		"rules": [{"name": one.name, "enabled": one.enabled, "said": rules.said(one)} for one in made],
		"apps": [
			{"app": app, "mark": _mark(app), "types": types}
			for app, types in sorted(apps.items(), key=lambda one: (not one[0], one[0]))
		],
	}


def _notification_type(name: str) -> dict:
	from onedesk.one import notify

	if not frappe.db.exists("Notification Type", name):
		frappe.throw(_("There is no notification type {0}.").format(name))
	doc = frappe.get_doc("Notification Type", name)
	one = notify.declared().get(name) or {}
	fields = fields_of("Notification Type", NOTIFICATION_TYPE)
	for field in fields:
		if field["fieldname"] == "one_message":
			field.update({"wrap": 1, "min_lines": 3, "max_lines": 12})
		if field["fieldname"] == "enabled":
			field["label"] = _("Send This")
			fixed = one.get("required") or (
				one.get("mailed_by") and not (one.get("switch") or one.get("notification"))
			)
			field["read_only"] = 1 if fixed else 0
	if one.get("mailed_by"):
		fields = [field for field in fields if field["fieldname"] == "enabled"]
	elif notify.upstream(one):
		fields = [field for field in fields if field["fieldname"] not in ("one_subject", "one_message")]
	return {
		"type": {
			"name": doc.name,
			"label": _(doc.name),
			"app": doc.one_app,
			"mark": _mark(doc.one_app),
			"about": _(doc.one_about) if doc.one_about else None,
			"to": notify.to(name),
			"ours": bool(one),
			"outside": doc.one_outside,
			"required": bool(one.get("required")),
			"always": bool(one.get("always_mailed")),
			"upstream": notify.upstream(one),
			"mailed_by": one["app"] if one.get("mailed_by") else "",
			"rule": one.get("rule") or "",
			"switch": bool(one.get("switch")),
			"notification": bool(one.get("notification")),
			"slots": notify.slots(name),
			"default_subject": doc.one_default_subject,
			"default_message": doc.one_default_message,
		},
		"fields": fields if one else [one for one in fields if one["fieldname"] == "enabled"],
		"values": {field: doc.get(field) for field in NOTIFICATION_TYPE},
		"opened": opened_of(doc),
	}


def _save_notification_type(name: str | None, values: dict) -> str | None:
	if name and name.startswith("rule:"):
		return f"rule:{_save_rule(name[5:], values)}"
	if not name or not frappe.db.exists("Notification Type", name):
		frappe.throw(_("There is nothing to save here."))
	doc = as_opened(frappe.get_doc("Notification Type", name))
	doc.update({field: values[field] for field in NOTIFICATION_TYPE if field in values})
	doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def preview_notification(
	name: Annotated[str, "The notification type."],
	subject: Annotated[str | None, "Its subject as it is being written."] = None,
	message: Annotated[str | None, "Its message as it is being written."] = None,
) -> dict:
	"""How a text being written reads, with each slot shown where it goes, and
	what is wrong with it if anything is. Rendered as notify renders it."""
	from markupsafe import Markup, escape

	from onedesk.one import notify

	roles.require()
	shown = {slot: Markup('<span class="os-slot">{0}</span>').format(escape(slot)) for slot in notify.slots(name)}
	out = {}
	for key, text in (("subject", subject), ("message", message)):
		wrong = notify.check(name, text)
		out[key] = None if wrong else notify._sandbox().from_string(text or "").render(shown)
		out[f"{key}_wrong"] = wrong
	return out


RULE = (
	"enabled",
	"document_type",
	"event",
	"date_changed",
	"days_in_advance",
	"value_changed",
	"filters",
	"subject",
	"message",
	"send_to_all_assignees",
)

RULE_CHANNELS = ("one_allow_email", "one_allow_push")


def _rule(name: str) -> dict:
	"""A rule of the workspace's, as a form: what it watches, when it fires,
	who is told, what it says, and the channels people may add."""
	from onedesk.one import rules

	new = name == "new"
	if not new and not frappe.db.exists("Notification", {"name": name, "one_rule": 1}):
		frappe.throw(_("There is no rule {0}.").format(name))
	doc = rules.blank() if new else rules.get(name)
	if new:
		doc.update({"enabled": 1, "event": "New", "channel": "System Notification", "message": ""})
	kind = (
		frappe.db.get_value("Notification Type", doc.name, RULE_CHANNELS, as_dict=True) if not new else None
	)
	fields = fields_of("Notification", RULE)
	said = {
		"enabled": (_("Send This"), None),
		"document_type": (_("Record Type"), _("Only record types you can open.")),
		"event": (_("When"), None),
		"date_changed": (_("The Date"), None),
		"days_in_advance": (_("Days"), None),
		"value_changed": (_("The Field"), None),
		"subject": (_("Subject"), _("One line. {{ doc.field }} puts a field of the record in.")),
		"message": (_("Message"), _("The notification detail and the email body. Optional.")),
		"send_to_all_assignees": (_("Assignees"), None),
	}
	for field in fields:
		label, description = said.get(field["fieldname"], (None, None))
		if label:
			field["label"] = str(label)
		field["description"] = str(description) if description else None
		name_of = field["fieldname"]
		if name_of == "event":
			field["options"] = [{"value": one, "label": _(one)} for one in rules.EVENTS]
		if name_of in ("date_changed", "days_in_advance"):
			field["depends_on"] = (
				"eval:doc.document_type && ['Days After', 'Days Before'].includes(doc.event)"
			)
		if name_of == "value_changed":
			field["depends_on"] = "eval:doc.document_type && doc.event === 'Value Change'"
		if name_of == "filters":
			field["hidden"] = 1
		if name_of == "message":
			field.update({"wrap": 1, "min_lines": 3, "max_lines": 12})
	roles_all = [
		one
		for one in frappe.get_all(
			"Role", filters={"disabled": 0, "desk_access": 1}, pluck="name", order_by="name asc"
		)
		if one not in ("Administrator", "Guest")
	]
	fields += [
		{
			"fieldname": "rule_name",
			"fieldtype": "Data",
			"label": str(_("Name")),
			"reqd": 1,
			"read_only": 0 if new else 1,
			"description": str(_("How people will know it when they choose how to get it.")),
		},
		{
			"fieldname": "roles",
			"fieldtype": "MultiSelectList",
			"label": str(_("People With the Role")),
			"options": [{"value": one, "label": _(one), "description": ""} for one in roles_all],
		},
		{
			"fieldname": "person_field",
			"fieldtype": "Select",
			"label": str(_("The Person on the Record")),
			"options": [],
		},
		*[
			{"fieldname": one, "fieldtype": "Check", "label": label}
			for one, label in (
				("one_allow_email", str(_("Email Allowed"))),
				("one_allow_push", str(_("Push Allowed"))),
			)
		],
	]
	values = {one: doc.get(one) for one in RULE}
	values.update(
		{
			"rule_name": "" if new else doc.name,
			"roles": [row.receiver_by_role for row in doc.recipients or [] if row.receiver_by_role],
			"person_field": next(
				(
					row.receiver_by_document_field
					for row in doc.recipients or []
					if row.receiver_by_document_field
				),
				"",
			),
			"one_allow_email": kind.one_allow_email if kind else 1,
			"one_allow_push": kind.one_allow_push if kind else 1,
		}
	)
	return {
		"rule": {
			"name": "" if new else doc.name,
			"new": new,
			"said": rules.said(doc) if doc.document_type else "",
		},
		"fields": fields,
		"values": values,
		"options": rules.fields_of(doc.document_type) if doc.document_type else None,
		"opened": [] if new else opened_of(doc),
	}


def _save_rule(name: str, values: dict) -> str:
	"""Make or change a rule. Returns its name."""
	from onedesk.one import rules

	new = name == "new"
	if new:
		doc = rules.blank()
		doc.name = (values.get("rule_name") or "").strip()
		if not doc.name:
			frappe.throw(_("Give the rule a name."))
		if frappe.db.exists("Notification", doc.name) or frappe.db.exists("Notification Type", doc.name):
			frappe.throw(_("There is already a notification called {0}.").format(doc.name))
	else:
		if not frappe.db.exists("Notification", {"name": name, "one_rule": 1}):
			frappe.throw(_("There is no rule {0}.").format(name))
		doc = as_opened(rules.get(name))
	doc.update({one: values[one] for one in RULE if one in values})
	doc.update({"one_rule": 1, "channel": "System Notification", "condition_type": "Filters"})
	roles_wanted = (
		frappe.parse_json(values.get("roles"))
		if isinstance(values.get("roles"), str)
		else values.get("roles")
	)
	rows = [{"receiver_by_role": one} for one in roles_wanted or [] if one]
	if values.get("person_field"):
		rows.append({"receiver_by_document_field": values["person_field"]})
	doc.set("recipients", rows)
	if new:
		doc.insert(ignore_permissions=True, set_name=doc.name)
	else:
		doc.save(ignore_permissions=True)
	kind = frappe.get_doc("Notification Type", doc.name)
	kind.update({one: frappe.utils.cint(values.get(one)) for one in RULE_CHANNELS if one in values})
	# A rule has no module to say who starts with a channel on: everybody
	# does, where it is allowed, until they turn it off.
	kind.one_email_default, kind.one_push_default = kind.one_allow_email, kind.one_allow_push
	kind.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["POST"])
def delete_rule(name: Annotated[str, "The rule."]) -> dict:
	"""Stop a rule for good, and its notification type with it."""
	roles.require()
	if not frappe.db.exists("Notification", {"name": name, "one_rule": 1}):
		frappe.throw(_("There is no rule {0}.").format(name))
	frappe.delete_doc("Notification", name, ignore_permissions=True)
	frappe.db.commit()
	return load("notification_types")
