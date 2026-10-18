"""Settings: one place for everything a person or a workspace sets.

Two groups, You for everybody and Workspace for its administrators. Nothing new
is stored: each section reads and writes the records that already hold it.
"""

from typing import Annotated

import frappe
from frappe import _, _lt

from onedesk.one import roles, tell
from onedesk.one.access import all_levels, companion

SECTIONS = [
	("profile", _lt("Profile"), "user", "you"),
	("notifications", _lt("Notifications"), "bell", "you"),
	("mail", _lt("Mail"), "mail", "you"),
	("calendar", _lt("Calendar"), "calendar", "you"),
	("signin", _lt("Sign-in"), "key-round", "you"),
	("memory", _lt("What OneAI Remembers"), "brain", "you"),
	("agreements", _lt("Agreements"), "scale", "you"),
	("general", _lt("General"), "building-2", "workspace"),
	("people", _lt("People"), "users", "workspace"),
	("access", _lt("Access"), "shield-check", "workspace"),
	("devices", _lt("Devices"), "monitor-smartphone", "workspace"),
	("notification_types", _lt("Workspace Notifications"), "bell-ring", "workspace"),
	("numbering", _lt("Numbering"), "hash", "workspace"),
	("printing", _lt("Printing"), "printer", "workspace"),
	("mail_templates", _lt("Mail Templates"), "mails", "workspace"),
	("approvals", _lt("Approvals"), "route", "workspace"),
	("plan", _lt("Plan and Credits"), "credit-card", "workspace"),
	("domains", _lt("Domains"), "globe", "workspace"),
	("oneai", _lt("OneAI Actions"), "sparkles", "workspace"),
	("intake", _lt("OneIntake Settings"), "oneintake", "workspace"),
	("holidays", _lt("Holidays"), "calendar-days", "workspace"),
]

APPS = [
	("OneCRM", "onecrm", ("Sales User",), ("Sales Manager",)),
	("OneBook", "onebook", ("Accounts User",), ("Accounts Manager",)),
	(
		"OneInventory",
		"oneinventory",
		("Stock User", "Purchase User", "Manufacturing User"),
		("Stock Manager", "Purchase Manager", "Item Manager", "Manufacturing Manager"),
	),
	("OneProject", "oneproject", ("Projects User",), ("Projects Manager",)),
	("OneHR", "onehr", ("HR User",), ("HR Manager",)),
]

APP_SAID = {
	"OneCRM": _lt("Leads, deals, customers and quotes."),
	"OneBook": _lt("Invoices, bills, payments and the books."),
	"OneInventory": _lt("Items, stock, buying, making and assets."),
	"OneProject": _lt("Projects, tasks and timesheets."),
	"OneHR": _lt("Employees, leave, attendance and pay."),
}

LEVELS = ("None", "User", "Manager")

NOT_PEOPLE = ("Administrator", "Guest", "oneai@one.invalid")

PROFILE = ("first_name", "last_name", "gender", "birth_date", "mobile_no", "location", "bio", "language", "time_zone", "user_image")

EMPLOYEE_OWN = (
	"personal_email",
	"current_address",
	"permanent_address",
	"person_to_be_contacted",
	"relation",
	"emergency_phone_number",
	"marital_status",
	"blood_group",
)

TOLD_HR = {
	"current_address": _lt("current address"),
	"permanent_address": _lt("permanent address"),
	"person_to_be_contacted": _lt("emergency contact"),
	"relation": _lt("emergency contact"),
	"emergency_phone_number": _lt("emergency contact"),
}

EMERGENCY = ("person_to_be_contacted", "relation", "emergency_phone_number")

LABELS = {"mobile_no": _lt("Mobile"), "phone_no": _lt("Phone"), "city": _lt("City"), "state": _lt("State or Region")}

SHARED = {"gender": "gender", "birth_date": "date_of_birth", "mobile_no": "cell_number", "user_image": "image"}

AT_WORK = ("name", "designation", "department", "reports_to", "branch", "employment_type", "date_of_joining", "company_email")

TITLES = {"Employee": "employee_name", "Department": "department_name"}

BANK = ("bank_name", "iban", "bank_ac_no")

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

ON_A_RECORD = ("notification_types", "people", "holidays", "access")

NOTIFICATION_TYPE = (
	"enabled",
	"one_subject",
	"one_message",
	"one_allow_email",
	"one_email_default",
	"one_allow_push",
	"one_push_default",
)


@frappe.whitelist()
@frappe.read_only()
def sections() -> dict:
	"""The sections this person may open, and who they are."""
	admin = roles.administers()
	return {
		"sections": [
			{"key": key, "label": str(label), "icon": icon, "group": group}
			for key, label, icon, group in SECTIONS
			if group == "you" or admin
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
		"profile": _profile,
		"notifications": _notifications,
		"mail": _mail,
		"calendar": _calendar,
		"signin": _signin,
		"memory": _memory,
		"agreements": _agreements,
		"general": _general,
		"people": _people,
		"access": _access,
		"plan": _plan,
		"domains": _domains,
		"devices": _devices,
		"oneai": _oneai,
		"intake": _intake,
		"holidays": _holidays,
		"notification_types": _notification_types,
		"numbering": _numbering,
		"printing": _printing,
		"mail_templates": _mail_templates,
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
		"profile": _save_profile,
		"notifications": _save_notifications,
		"general": _save_general,
		"intake": _save_intake,
		"holidays": _save_holidays,
		"notification_types": _save_notification_type,
		"people": _save_person,
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


def _as_opened(doc):
	"""The record as the page loaded it, for frappe's own `check_if_latest`,
	which refuses the save if it has changed since, with frappe's own message
	(Document.check_if_latest). A record the page did not send is saved as
	it is."""
	modified = (frappe.flags.one_opened or {}).get(f"{doc.doctype}:{doc.name}")
	if modified:
		doc.modified = modified
	return doc


def _opened(*docs) -> list[dict]:
	"""What the page needs to save these back, and to hear when somebody else
	changes them: each record's doctype, name and modified."""
	return [{"doctype": doc.doctype, "name": doc.name, "modified": str(doc.modified)} for doc in docs if doc]


def _group(section: str) -> str:
	return next((group for key, _label, _icon, group in SECTIONS if key == section), "")


def _fields(doctype: str, names: tuple) -> list[dict]:
	"""A doctype's own fields, as the page draws them: its labels, options and
	descriptions rather than a second copy of them here."""
	meta = frappe.get_meta(doctype)
	out = []
	for name in names:
		field = meta.get_field(name)
		if not field:
			continue
		out.append(
			{
				"fieldname": field.fieldname,
				"fieldtype": field.fieldtype,
				"label": str(LABELS[name]) if name in LABELS else _(field.label),
				"options": field.options,
				"description": _(field.description) if field.description else None,
			}
		)
	return out


def _profile() -> dict:
	user = frappe.get_doc("User", frappe.session.user)
	said = {
		"fields": _fields("User", PROFILE),
		"values": {name: user.get(name) for name in PROFILE},
		"email": user.email,
		"full_name": user.full_name,
		"employee": None,
	}
	employee = _employee()
	said["opened"] = _opened(user, employee)
	from onedesk.one import privacy

	said["privacy"] = privacy.state()
	if employee:
		said["values"].update({mine: employee.get(theirs) or said["values"].get(mine) for mine, theirs in SHARED.items()})
		said["values"].update({name: employee.get(name) for name in EMPLOYEE_OWN})
		said["employee"] = {
			"fields": _fields("Employee", EMPLOYEE_OWN),
			"work": _facts(employee, AT_WORK),
			"bank": [{**one, "value": _masked(one["value"])} if one["fieldname"] != "bank_name" else one for one in _facts(employee, BANK)],
		}
	return said


def _employee():
	"""The person's own employee record, when they have one. Read past
	permissions: the only filter is the session's own user."""
	from onedesk.one_hr import own

	name = own.employee_of()
	return frappe.get_doc("Employee", name) if name else None


def _facts(doc, names: tuple) -> list[dict]:
	"""Fields of a record as label and value, for reading rather than editing.
	A link shows the record's title, not its id."""
	meta = frappe.get_meta(doc.doctype)
	out = []
	for name in names:
		value = doc.get(name)
		if not value:
			continue
		field = meta.get_field(name)
		label = _(field.label) if field else _("Employee ID")
		if field and field.fieldtype == "Link":
			value = frappe.db.get_value(field.options, value, TITLES.get(field.options) or frappe.get_meta(field.options).get_title_field()) or value
			value = _(value) if field.options in ("Designation", "Employment Type") else value
		elif field and field.fieldtype == "Date":
			value = frappe.utils.formatdate(value)
		out.append({"fieldname": name, "label": label, "value": value})
	return out


def _masked(value: str) -> str:
	"""All but the last four characters hidden. Pure."""
	value = (value or "").replace(" ", "")
	return "•••• " + value[-4:] if len(value) > 4 else value


def _save_profile(values: dict) -> None:
	user = _as_opened(frappe.get_doc("User", frappe.session.user))
	user.update({name: values[name] for name in PROFILE if name in values})
	user.save(ignore_permissions=True)
	employee = _employee()
	if not employee:
		return
	changes = {name: values[name] for name in EMPLOYEE_OWN if name in values}
	changes.update({theirs: values[mine] for mine, theirs in SHARED.items() if mine in values})
	was = {name: employee.get(name) for name in TOLD_HR}
	_as_opened(employee).update(changes)
	if any(employee.get(name) for name in EMERGENCY) and not (
		employee.person_to_be_contacted and employee.emergency_phone_number
	):
		frappe.throw(_("An emergency contact needs a name and a phone number, so HR can call them."))
	employee.save(ignore_permissions=True)
	_tell_hr(employee, was)


def _tell_hr(employee, was: dict) -> None:
	"""HR learns when a person changes where they live or who to call, once
	per save, saying what changed. Not the person themselves, if they are HR."""
	said = list(
		dict.fromkeys(
			str(label) for name, label in TOLD_HR.items() if (was.get(name) or "") != (employee.get(name) or "")
		)
	)
	if not said:
		return
	tell.employee_details_changed(employee, said)


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
	fields = _fields("Notification Settings", NOTIFY)
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
		"opened": _opened(doc),
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

	doc = _as_opened(frappe.get_doc("Notification Settings", frappe.session.user))
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


def _mail() -> dict:
	from onedesk.one_mail import holders

	return {"mailboxes": holders.mailboxes()}


def _calendar() -> dict:
	from onedesk.one_calendar import feed

	return {"link": feed.current(), "allowed": feed.allowed()}


def _signin() -> dict:
	from onedesk.one import signin

	return signin.facts()


@frappe.whitelist(methods=["POST"])
def sign_out_elsewhere() -> int:
	"""Every other session of this person ends; this one stays."""
	from frappe.sessions import clear_sessions

	clear_sessions(frappe.session.user, keep_current=True)
	return 1


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


def _agreements() -> dict:
	"""Every agreement: what the reader agreed to themselves, what the
	organisation agreed to and who agreed for it, and what is only published.
	Read from the rows OneLegal's own gate writes, never a second copy."""
	from onedesk.one_legal import assemble, gate
	from onedesk.one_legal.documents import DOCUMENTS

	def last(key: str, party: str) -> dict | None:
		filters = {"document": key, "party": party}
		if party == gate.USER:
			filters["user"] = frappe.session.user
		rows = frappe.get_all(
			"Legal Acceptance",
			filters=filters,
			fields=["version", "user", "accepted_on"],
			order_by="creation desc",
			limit=1,
			ignore_permissions=True,
		)
		if not rows:
			return None
		row = rows[0]
		return {
			"version": row.version,
			"owed": not gate.agreed(row.version, assemble.version_of(key)),
			"on": frappe.utils.formatdate(row.accepted_on),
			"by": frappe.utils.get_fullname(row.user) if party == gate.WORKSPACE else None,
		}

	documents = []
	for key, one in DOCUMENTS.items():
		version = assemble.version_of(key)
		parties = gate.AUDIENCE.get(one["audience"], ())
		title, summary = one["title"], one["summary"]
		documents.append(
			{
				"key": key,
				"title": _(title),
				"summary": _(summary),
				"version": version,
				"you": {"current": version, "owed": True, **(last(key, gate.USER) or {})}
				if gate.USER in parties
				else None,
				"organisation": {"current": version, "owed": True, **(last(key, gate.WORKSPACE) or {})}
				if gate.WORKSPACE in parties
				else None,
			}
		)
	return {"documents": documents, "admin": roles.administers()}


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
		_fields("Company", ("company_logo", *ON_DOCUMENTS))
		+ _fields("Address", ADDRESS)
		+ _zones(_switches(_fields("System Settings", ("language", "time_zone", *SYSTEM, *SIGNING_IN, *FOOTER))))
		+ _switches(_fields("Global Defaults", AMOUNTS))
	)
	return {
		"name": account.workspace_name,
		"company": company.company_name if company else None,
		"country": company.country if company else system.country,
		"currency": company.default_currency if company else None,
		"fields": [{**one, **_said_on_general(one["fieldname"], system)} for one in fields] + _signing_in_fields() + _sharing_fields(),
		"values": {
			"company_logo": company.company_logo if company else None,
			**{name: company.get(name) if company else None for name in ON_DOCUMENTS},
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
		"opened": _opened(company, system, address, defaults),
	}


AMOUNTS = ("hide_currency_symbol", "disable_rounded_total", "disable_in_words")

ON_DOCUMENTS = ("one_brand_colour", "phone_no", "email", "website", "tax_id")
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
		_as_opened(address)
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
	"hide_currency_symbol": _lt("Amounts are shown without AED, $ or another symbol."),
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
			for name in ("company_logo", *ON_DOCUMENTS)
			if name in values and (values[name] or None) != (company.get(name) or None)
		}
		if changed:
			_as_opened(company).update(changed)
			company.save(ignore_permissions=True)
		_save_company_address(company, values)
	_save_amounts(values)
	system = _as_opened(frappe.get_single("System Settings"))
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
		_as_opened(defaults).update(wanted)
		defaults.save(ignore_permissions=True)


def level_of(held: set, used: tuple, managed: tuple, levels: tuple | list = ()) -> str:
	"""None, User, one of the workspace's own levels of the app
	(one/access.py), or Manager, from the roles a person holds. Pure."""
	if held & set(managed):
		return "Manager"
	for one in levels:
		if one in held:
			return one
	if held & set(used):
		return "User"
	return "None"


def roles_for(level: str, used: tuple, managed: tuple, levels: tuple | list = (), alone: tuple | list = ()) -> set:
	"""The roles a level means: every level holds the app's User roles, a
	plain user also the app's companion role (`alone`, one/access.py), a
	manager the app's Manager roles, and a level of the workspace's own
	itself. Pure."""
	if level in levels:
		return set(used) | {level}
	return {"None": set(), "User": set(used) | set(alone), "Manager": set(used) | set(managed)}[level]


def _levels(app: str, own: dict) -> list[dict]:
	"""What People offers for one app: None, User, the workspace's own levels
	between, and Manager."""
	return [{"value": one, "label": _(one)} for one in ("None", "User")] + [
		{"value": one, "label": one} for one in own.get(app, [])
	] + [{"value": "Manager", "label": _("Manager")}]


def _people(record: str | None = None) -> dict:
	"""Everybody on the workspace; or the one person the section is open on."""
	if record:
		return _person_page(record)
	users = frappe.get_all(
		"User",
		filters={"user_type": "System User", "name": ["not in", NOT_PEOPLE]},
		fields=["name", "full_name", "enabled", "last_active", "user_image"],
		order_by="enabled desc, full_name asc",
		limit=500,
	)
	held = _held([one.name for one in users])
	employees = dict(
		frappe.get_all("Employee", filters={"user_id": ["in", [one.name for one in users] or [""]]}, fields=["user_id", "name"], as_list=True)
	)
	account = frappe.get_single("Workspace Account")
	own = all_levels()
	return {
		"apps": [{"name": name, "icon": icon, "levels": _levels(name, own)} for name, icon, _used, _managed in APPS],
		"levels": [{"value": one, "label": _(one)} for one in LEVELS],
		"people": [
			{
				**one,
				"admin": roles.ADMINISTRATOR in held.get(one.name, set()),
				"access": {
					name: level_of(held.get(one.name, set()), used, managed, own.get(name, ()))
					for name, _icon, used, managed in APPS
				},
				"employee": employees.get(one.name),
			}
			for one in users
		],
		"seats": account.seats or 0,
		"used": sum(1 for one in users if one.enabled),
		"me": frappe.session.user,
	}


def _held(users: list) -> dict:
	held = {}
	for row in frappe.get_all("Has Role", filters={"parenttype": "User", "parent": ["in", users or [""]]}, fields=["parent", "role"], limit=0):
		held.setdefault(row.parent, set()).add(row.role)
	return held


def _one_of_the_people(user: str):
	roles.require()
	if user in NOT_PEOPLE or frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("That cannot be set."))
	return frappe.get_doc("User", user)


def _person_page(user: str) -> dict:
	"""One person as an administrator sees them, as a form: a Select per app
	and the Administrator switch, saved against the User as it was loaded;
	where they are signed in and their last sign-ins (one/signin.py), and the
	records they are held to (one/access.py)."""
	from onedesk.one import access, signin

	doc = _one_of_the_people(user)
	held = {one.role for one in doc.roles}
	own = all_levels()
	fields = [
		{"fieldname": f"app_{icon}", "fieldtype": "Select", "label": name, "options": _levels(name, own), "description": str(APP_SAID[name])}
		for name, icon, _used, _managed in APPS
	]
	fields.insert(
		0,
		{
			"fieldname": "profile",
			"fieldtype": "Select",
			"label": _("Profile"),
			"options": [{"value": "", "label": _("None, set by hand")}] + [{"value": one["name"], "label": one["name"]} for one in access.profiles()],
			"description": _("Sets every app below. Changing an app by hand removes the profile."),
		},
	)
	fields.append(
		{
			"fieldname": "admin",
			"fieldtype": "Switch",
			"label": _("Administrator"),
			"description": _("Can manage people, the plan, domains and OneAI. Other administrators are notified."),
		}
	)
	me = doc.name == frappe.session.user
	return {
		"person": {
			"name": doc.name,
			"full_name": doc.full_name,
			"user_image": doc.user_image,
			"enabled": doc.enabled,
			"last_active": doc.last_active,
			"joined": bool(doc.last_login),
			"employee": frappe.db.get_value("Employee", {"user_id": doc.name}, "name"),
			"sessions": [] if me else signin.sessions(doc.name),
			"recent": signin.recent(doc.name),
			"me": me,
			"holds": access.record_access(doc.name),
			"kinds": access.kinds_held(),
		},
		"profiles": {one["name"]: one["levels"] for one in access.profiles()},
		"apps": [{"name": name, "icon": icon, "levels": _levels(name, own)} for name, icon, _used, _managed in APPS],
		"fields": fields,
		"values": {
			**{f"app_{icon}": level_of(held, used, managed, own.get(name, ())) for name, icon, used, managed in APPS},
			"admin": 1 if roles.ADMINISTRATOR in held else 0,
			"profile": doc.get("one_profile") or "",
		},
		"opened": _opened(doc),
	}


def _save_person(record: str, values: dict) -> None:
	"""What a person may use. A profile picked sets every app at once; an app
	changed by hand takes them off the profile they were on."""
	from onedesk.one import access as profiles

	doc = _as_opened(_one_of_the_people(record))
	chosen = {name: values.get(f"app_{icon}") for name, icon, _used, _managed in APPS if values.get(f"app_{icon}")}
	admin = frappe.utils.cint(values.get("admin")) if "admin" in values else int(roles.ADMINISTRATOR in {one.role for one in doc.roles})
	if values.get("profile") and values["profile"] != doc.get("one_profile"):
		_set_access(doc, profiles.profile(values["profile"])["levels"], admin)
		frappe.db.set_value("User", doc.name, "one_profile", values["profile"], update_modified=False)
		return
	_set_access(doc, chosen, admin)
	on = values.get("profile", doc.get("one_profile"))
	if on and any(level != profiles.profile(on)["levels"].get(name) for name, level in chosen.items()):
		on = None
	if (on or None) != (doc.get("one_profile") or None):
		frappe.db.set_value("User", doc.name, "one_profile", on or None, update_modified=False)


def _set_access(doc, access: dict, admin: int, told: bool = True) -> None:
	"""What a person may use, as frappe's roles, in one save. They are told
	what changed, and every administrator is told of a new administrator."""
	own = all_levels()
	if any(level not in LEVELS and level not in own.get(name, ()) for name, level in access.items()):
		frappe.throw(_("That cannot be set."))
	before = {one.role for one in doc.roles}
	ours = {roles.ADMINISTRATOR}
	wanted = set()
	for name, _icon, used, managed in APPS:
		levels = own.get(name, ())
		alone = (companion(name),)
		ours |= set(used) | set(managed) | set(levels) | set(alone)
		wanted |= roles_for(access.get(name) or level_of(before, used, managed, levels), used, managed, levels, alone)
	if admin:
		wanted.add(roles.ADMINISTRATOR)
	elif roles.ADMINISTRATOR in before:
		_not_the_last_administrator(doc.name)
	after = (before - ours) | {role for role in wanted | {"Desk User"} if frappe.db.exists("Role", role)}
	if after != before:
		doc.set("roles", [{"role": role} for role in sorted(after)])
		doc.save(ignore_permissions=True)
		if told:
			_told_of_access(doc, before, after)


def _not_the_last_administrator(user: str) -> None:
	others = frappe.get_all("Has Role", filters={"role": roles.ADMINISTRATOR, "parenttype": "User", "parent": ["not in", (user, *NOT_PEOPLE)]}, pluck="parent")
	if not [one for one in others if frappe.db.get_value("User", one, "enabled")]:
		frappe.throw(_("A workspace needs at least one administrator."))


def _told_of_access(doc, before: set, after: set) -> None:
	"""The person hears what they may now use; every other administrator
	hears of a new administrator, always by mail (notifications/one/)."""
	said = []
	own = all_levels()
	for name, _icon, used, managed in APPS:
		levels = own.get(name, ())
		was, now = level_of(before, used, managed, levels), level_of(after, used, managed, levels)
		if was != now:
			plain = {"None": _("no longer {0}"), "User": _("{0} as a user"), "Manager": _("{0} as a manager")}
			said.append(plain[now].format(name) if now in plain else _("{0} as {1}").format(name, now))
	if (roles.ADMINISTRATOR in after) != (roles.ADMINISTRATOR in before):
		said.append(_("administrator of the workspace") if roles.ADMINISTRATOR in after else _("no longer an administrator"))
	if said:
		tell.access_changed(doc.name, ", ".join(said))
	if roles.ADMINISTRATOR in after and roles.ADMINISTRATOR not in before:
		tell.administrator_added(doc)
	if roles.ADMINISTRATOR in before and roles.ADMINISTRATOR not in after:
		tell.administrator_removed(doc)


@frappe.whitelist(methods=["POST"])
def sign_out_everywhere(user: Annotated[str, "The person."]) -> dict:
	"""Every session a person has, ended: frappe's own, so the Activity Log
	records it. Your own are ended on your Sign-in page."""
	roles.require()
	from frappe.sessions import clear_sessions

	doc = _one_of_the_people(user)
	if doc.name == frappe.session.user:
		frappe.throw(_("Sign yourself out from your own Sign-in page."))
	clear_sessions(user=doc.name, force=True)
	return _person_page(doc.name)


@frappe.whitelist(methods=["POST"])
def send_reset(user: Annotated[str, "The person."]) -> None:
	"""Frappe's own password reset mail, sent to the person."""
	roles.require()
	doc = _one_of_the_people(user)
	if not doc.enabled:
		frappe.throw(_("Turn them on first."))
	doc._reset_password(send_email=True)


@frappe.whitelist(methods=["POST"])
def set_enabled(user: Annotated[str, "The person."], on: Annotated[int, "1 to let them sign in."]) -> dict:
	"""A person may sign in, or not. Their records stay either way."""
	roles.require()
	if user in NOT_PEOPLE or user == frappe.session.user:
		frappe.throw(_("You cannot turn yourself off."))
	doc = frappe.get_doc("User", user)
	doc.enabled = int(on)
	doc.flags.ignore_permissions = True
	doc.save()
	if not int(on):
		from frappe.sessions import clear_sessions

		clear_sessions(user=user, force=True)
	return _people()


@frappe.whitelist(methods=["POST"])
def invite(
	email: Annotated[str, "Their address."],
	first_name: Annotated[str, "Their first name."],
	last_name: Annotated[str | None, "Their last name."] = None,
	access: Annotated[str | dict | None, "Each app's level: None, User or Manager."] = None,
) -> dict:
	"""A new person on the workspace, sent frappe's welcome mail to set a
	password. They can use One, OneCloud, OneMail, OneTask and OneCalendar at
	once; the apps whose records are somebody's job are given in People."""
	roles.require()
	email = (email or "").strip().lower()
	if not frappe.utils.validate_email_address(email):
		frappe.throw(_("That is not an email address."))
	if frappe.db.exists("User", email):
		frappe.throw(_("{0} is already on the workspace.").format(email))
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": "Desk User"}],
		}
	)
	user.insert(ignore_permissions=True)
	from onedesk.one import invite as invitation

	wanted = frappe.parse_json(access) or {}
	if any(level != "None" for level in wanted.values()):
		_set_access(frappe.get_doc("User", user.name), wanted, 0, told=False)
	invitation.send(user.name, _apps_said(wanted))
	return _people()


def _apps_said(access: dict) -> list[str]:
	said = {"User": _("{0} as a user"), "Manager": _("{0} as a manager")}
	return [
		said[level].format(name) if level in said else _("{0} as {1}").format(name, level)
		for name, level in access.items()
		if level and level != "None"
	]


@frappe.whitelist(methods=["POST"])
def invite_again(user: Annotated[str, "The person."]) -> None:
	"""A new invitation for somebody who has not joined yet; the old link stops."""
	from onedesk.one import invite as invitation

	roles.require()
	doc = _one_of_the_people(user)
	if doc.last_login:
		frappe.throw(_("{0} has already joined. Send a password reset instead.").format(doc.full_name))
	held = {one.role for one in doc.roles}
	own = all_levels()
	invitation.send(
		doc.name, _apps_said({name: level_of(held, used, managed, own.get(name, ())) for name, _icon, used, managed in APPS})
	)


def seats_used() -> int:
	"""Everybody turned on who takes a seat."""
	return frappe.db.count("User", {"user_type": "System User", "enabled": 1, "name": ["not in", NOT_PEOPLE]})


def seated(doc, method=None) -> None:
	"""User validate: a person turned on takes a seat, and there are only as
	many as the plan has, however they are added or turned on (People, the
	User form, a bulk edit, an import)."""
	if doc.user_type != "System User" or not doc.enabled or doc.name in NOT_PEOPLE:
		return
	before = None if doc.is_new() else doc.get_doc_before_save()
	if before and before.enabled and before.user_type == "System User":
		return
	if not frappe.db.exists("DocType", "Workspace Account"):
		return
	seats = frappe.get_single("Workspace Account").seats or 0
	if seats and seats_used() >= seats:
		frappe.throw(_("All {0} seats are in use. Disable someone or add seats to the plan.").format(seats))


STALE = 60 * 60


def _plan() -> dict:
	"""The workspace's account, as the administrator last said it: asked again
	first when that was over an hour ago, so a pack just paid for shows."""
	from onedesk.one import account, closing, heads

	held = frappe.get_single("Workspace Account")
	heard = held.last_heard
	if account.configured() and (not heard or frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), heard) > STALE):
		account.refresh()
		frappe.db.commit()
		held = frappe.get_single("Workspace Account")
	return {
		"account": {
			key: held.get(key)
			for key in (
				"workspace_name", "billed_to", "plan", "plan_key", "monthly", "plan_currency", "seats", "storage_bytes", "storage_limit", "database_bytes",
				"database_limit", "credits_balance", "credits_held", "credits_month", "credits_expiring",
				"credits_expires_on", "last_heard",
			)
		},
		"used": seats_used(),
		"state": heads.account_state(held),
		"said": heads.account_said(held),
		"storage": {"used": heads.size(held.storage_bytes), "limit": heads.size(held.storage_limit)},
		"database": {"used": heads.size(held.database_bytes), "limit": heads.size(held.database_limit)},
		"add_ons": [{"offering": one.offering, "label": one.label, "quantity": one.quantity, "amount": one.amount} for one in held.add_ons],
		"ledger": account.ledger() if account.configured() else None,
		"ledger_days": account.LEDGER_DAYS,
		"closing": closing.state(),
	}


def _domains() -> dict:
	"""What the account last said, asked again first when that was over an
	hour ago or never said where a domain should point. Check Again asks."""
	from onedesk.one import account

	held = frappe.get_single("Workspace Account")
	heard = held.last_heard
	stale = not heard or frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), heard) > STALE
	if account.configured() and (stale or not held.dns_target):
		account.refresh()
		frappe.db.commit()
		held = frappe.get_single("Workspace Account")
	return {
		"domains": [
			{"domain": one.domain, "status": one.status, "problem": one.problem, "primary": one.primary, "given": one.given}
			for one in held.domains
		],
		"target": held.dns_target,
		"last_heard": held.last_heard,
	}


def _devices() -> dict:
	"""The company's machines and every passkey on somebody's own. See
	one/devices.py."""
	from onedesk.one import devices

	return devices.for_settings()


def _oneai() -> dict:
	"""Every action, what it runs on, what it used in the last thirty days, and
	the models it could run on instead, from the account's catalogue. The
	catalogue and the usage are the account's; either being unreachable leaves
	the list drawn from what this site knows."""
	from frappe.utils import add_days, today

	from onedesk.one import account

	chosen = {
		one.action: one
		for one in frappe.get_all(
			"AI Action Setting", fields=["name", "action", "model", "extra", "people_choose", "modified"]
		)
	}
	actions = frappe.get_all(
		"AI Action",
		filters={"enabled": 1},
		fields=["name", "label", "about", "capability", "product", "default_model"],
		order_by="product asc, label asc",
	)
	catalogue, used = {}, {}
	if account.configured():
		try:
			catalogue = account.ask(
				"onedesk.one_admin.proxy.ai_models_for", needs=sorted({one.capability for one in actions})
			) or {}
			said = account.ask("onedesk.one_admin.proxy.ai_usage", start=add_days(today(), -29), end=today()) or {}
			used = {one.get("action"): one for one in said.get("actions") or [] if one.get("action")}
		except Exception:
			frappe.log_error(title="OneAI Actions could not ask the account")
	rows = []
	for one in actions:
		held = chosen.get(one.name) or {}
		spent = used.get(one.name) or {}
		rows.append(
			{
				"name": one.name,
				"label": _(one.label),
				"about": _(one.about) if one.about else None,
				"capability": one.capability,
				"product": one.product or "OneAI",
				"default_model": one.default_model,
				"model": held.get("model"),
				"extra": held.get("extra"),
				"people_choose": bool(held.get("people_choose")),
				"setting": held.get("name"),
				"modified": str(held.get("modified")) if held.get("modified") else None,
				"credits": round(float(spent.get("credits") or 0), 2),
				"calls": int(spent.get("calls") or 0),
			}
		)
	from onedesk.one_ai import logos

	for offered in catalogue.values():
		for model in offered:
			model["logo"] = logos.url(model.get("logo_domain"))
	return {"actions": rows, "catalogue": catalogue}


def _intake() -> dict:
	"""OneIntake's settings, with the defaults written in where the record is
	empty (an empty floor is 70%, not nothing), and the month: what arrived,
	what OneAI handled, what needed a person, what was undone, and what waits
	now, for everybody."""
	from onedesk.one_intake import act, pipeline

	doc = frappe.get_single("Intake Settings")
	values = {name: doc.get(name) for name in INTAKE}
	values["most_pages"] = values["most_pages"] or pipeline.MOST_PAGES
	values["floor"] = values["floor"] or act.FLOOR
	fields = [
		{**one, "fieldtype": "Switch"} if one["fieldtype"] == "Check" else one
		for one in _fields("Intake Settings", INTAKE)
	]
	from onedesk.one_intake import switches

	opened = [doc]
	hr = _intake_hr()
	if hr:
		held = frappe.get_single("HR Settings")
		fields += [{**one, "fieldtype": "Switch"} for one in _fields("HR Settings", hr)]
		values.update({name: held.get(name) for name in hr})
		opened.append(held)
	return {
		"fields": fields,
		"values": values,
		"month": _intake_month(),
		"hr": list(hr),
		"marks": {app: _mark(app) for app in ("OneBook", "OneHR", "OneMail", "OneCloud")},
		**switches.overview(),
		"opened": _opened(*opened),
	}


INTAKE_HR = ("one_ai_screen", "one_ai_prepare", "one_ai_transcribe", "one_ai_grievances")


def _intake_hr() -> tuple:
	if not frappe.db.exists("DocType", "HR Settings"):
		return ()
	meta = frappe.get_meta("HR Settings")
	return tuple(name for name in INTAKE_HR if meta.get_field(name))


def _intake_month() -> dict:
	from frappe.utils import get_first_day, today

	from onedesk.one_intake import digest, inbox

	month = digest.this_month()
	start = get_first_day(today())
	waiting = frappe.db.sql(f"select count(*) from `tabReading` r where {inbox._box('waiting')}")[0][0]
	undone = frappe.db.count("Intake Action", {"level": "Undone", "modified": [">=", start]})
	return {**month, "waiting": int(waiting or 0), "undone": int(undone or 0)}


TOLD_OF = ("audit", "household", "submit_einvoices", "floor")


def _save_intake(values: dict) -> None:
	from onedesk.one_intake import act

	doc = _as_opened(frappe.get_single("Intake Settings"))

	def meant(name):
		value = frappe.utils.flt(doc.get(name))
		return (value or act.FLOOR) if name == "floor" else value

	was = {name: meant(name) for name in TOLD_OF}
	doc.update({name: values[name] for name in INTAKE if name in values})
	doc.save(ignore_permissions=True)
	hr = [name for name in _intake_hr() if name in values]
	if hr:
		held = _as_opened(frappe.get_single("HR Settings"))
		if any(frappe.utils.cint(held.get(name)) != frappe.utils.cint(values[name]) for name in hr):
			held.update({name: values[name] for name in hr})
			held.save(ignore_permissions=True)
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
		*_fields("Holiday List", ("country", "subdivision")),
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
		"opened": _opened(doc),
	}


def _save_holidays(record: str | None, values: dict) -> str:
	"""The list's day off, country and public holidays, saved against when the
	page loaded it. A new day off remakes the week's days off; the other
	administrators and the HR managers hear what changed."""
	from onedesk.one import holidays

	name = record or holidays.in_force()
	doc = _as_opened(frappe.get_doc("Holiday List", name))
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
		{"fieldname": f"app_{icon}", "fieldtype": "Select", "label": app, "options": _levels(app, own), "description": str(APP_SAID[app])}
		for app, icon, _used, _managed in APPS
	]
	return {
		"profile": said,
		"apps": [{"name": app, "icon": icon} for app, icon, _used, _managed in APPS],
		"fields": fields,
		"values": {"title": name, **{f"app_{icon}": said["levels"].get(app, "None") for app, icon, _used, _managed in APPS}},
		"opened": _opened(frappe.get_doc("Role Profile", name)),
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
		"opened": _opened(doc),
	}


def _level_page(key: str) -> dict:
	"""One level as a form: its name, and what it may do on each kind of
	record, in frappe's table, one tick per right."""
	from onedesk.one import access

	said = access.level(key)
	options = sorted(({"value": one, "label": _(one)} for one in access.kinds(said["app"])), key=lambda one: one["label"])
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
	fields = [table]
	if said["own"]:
		fields.insert(0, {"fieldname": "title", "fieldtype": "Data", "label": _("Name"), "reqd": 1})
	carrier = said["name"] if said["own"] else None
	return {
		"level": {**said, "people": people, "icon": next(icon for app, icon, _u, _m in APPS if app == said["app"])},
		"fields": fields,
		"values": {"title": said["name"], "rows": said["rows"]},
		"opened": [{"doctype": "Role", "name": carrier, "modified": str(frappe.db.get_value("Role", carrier, "modified"))}] if carrier else [],
	}


def _save_access(record: str | None, values: dict) -> str:
	"""A level's name and what it may do, a profile or a group, saved as
	one/access.py says it may be."""
	from onedesk.one import access

	kind, _sep, name = (record or "").partition(":")
	if kind == "level":
		rows = values["rows"] if "rows" in values else access.level(name)["rows"]
		return "level:" + access.save_level(name, values.get("title") or name, rows)
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


def _mail_templates() -> dict:
	"""Every mail template, and what each is the default for (one/mail_templates.py)."""
	from onedesk.one import mail_templates

	return {"rows": mail_templates.templates()}


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
	fields = _fields("Notification Type", NOTIFICATION_TYPE)
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
		"opened": _opened(doc),
	}


def _save_notification_type(name: str | None, values: dict) -> str | None:
	if name and name.startswith("rule:"):
		return f"rule:{_save_rule(name[5:], values)}"
	if not name or not frappe.db.exists("Notification Type", name):
		frappe.throw(_("There is nothing to save here."))
	doc = _as_opened(frappe.get_doc("Notification Type", name))
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

RULE_CHANNELS = ("one_allow_email", "one_email_default", "one_allow_push", "one_push_default")


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
	fields = _fields("Notification", RULE)
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
				("one_email_default", str(_("Email for New People"))),
				("one_allow_push", str(_("Push Allowed"))),
				("one_push_default", str(_("Push for New People"))),
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
			"one_email_default": kind.one_email_default if kind else 0,
			"one_allow_push": kind.one_allow_push if kind else 1,
			"one_push_default": kind.one_push_default if kind else 0,
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
		"opened": [] if new else _opened(doc),
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
		doc = _as_opened(rules.get(name))
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
