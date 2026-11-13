"""AccountCenter (docs/ONE.md): your own account, and the workspace's.

Two groups, Yours for everybody and Workspace for its administrators. Nothing
new is stored: each section reads and writes the records that already hold
it, as Settings did before it."""

from typing import Annotated

import frappe
from frappe import _, _lt

from onedesk.one import roles, sections
from onedesk.one.access import all_levels
from onedesk.one.people import (
	APP_SAID,
	APPS,
	LEVELS,
	NOT_PEOPLE,
	app_level,
	apps_said,
	level_of,
	levels_of,
	listed,
	one_of_the_people,
	roles_held,
	seats_used,
	set_access,
)

SECTIONS = [
	("profile", _lt("Profile"), "user", "yours"),
	("personal", _lt("Personal Details"), "contact-round", "yours"),
	("work", _lt("Work"), "briefcase-business", "yours"),
	("documents", _lt("Documents"), "id-card", "yours"),
	("signin", _lt("Sign-in"), "key-round", "yours"),
	("people", _lt("People"), "users", "workspace"),
	("devices", _lt("Devices"), "monitor-smartphone", "workspace"),
	("plan", _lt("Plan and Credits"), "credit-card", "workspace"),
	("domains", _lt("Domains"), "globe", "workspace"),
]

ON_A_RECORD = ("people",)

# Profile's parts, each its own section, drawn from one load and saved
# through one saver: a part only sends the fields it shows. All but Profile
# are an employee's.
PROFILE_PARTS = ("profile", "personal", "work", "documents")
EMPLOYEE_PARTS = ("personal", "work", "documents")


def _sees_plan() -> bool:
	"""Whether somebody may read Plan and Credits: an administrator, or a
	role given it in AccessCenter (abilities.py, `plan`)."""
	from onedesk.one import rights

	return roles.administers() or rights.may("Workspace Account", "account_plan")


def _may_open(section: str) -> bool:
	group = next((group for key, _label, _icon, group in SECTIONS if key == section), "")
	return group == "yours" or roles.administers() or (section == "plan" and _sees_plan())


@frappe.whitelist()
@frappe.read_only()
def sections_of() -> dict:
	"""The sections this person may open, and who they are."""
	employee = bool(_employee())
	return {
		"sections": [
			{"key": key, "label": str(label), "icon": icon, "group": group}
			for key, label, icon, group in SECTIONS
			if _may_open(key) and (employee or key not in EMPLOYEE_PARTS)
		],
		"admin": roles.administers(),
		"user": frappe.session.user,
	}


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section."],
	record: Annotated[str | None, "The one record the section is open on, where it lists several."] = None,
) -> dict:
	loaders = {
		**{part: _profile for part in PROFILE_PARTS},
		"signin": _signin,
		"people": _people,
		"plan": _plan,
		"domains": _domains,
		"devices": _devices,
	}
	if section not in loaders:
		frappe.throw(_("There is no such section."))
	if not _may_open(section):
		roles.require()
	return loaders[section](record) if section in ON_A_RECORD else loaders[section]()


@frappe.whitelist(methods=["POST"])
def save(
	section: Annotated[str, "Which section."],
	values: Annotated[str | dict, "What was changed."],
	opened: Annotated[str | list | None, "The records as the centre loaded them: doctype, name and modified."] = None,
	record: Annotated[str | None, "The one record the section is open on, where it lists several."] = None,
) -> dict:
	values = frappe.parse_json(values) or {}
	frappe.flags.one_opened = {f"{one['doctype']}:{one['name']}": one["modified"] for one in frappe.parse_json(opened) or []}
	savers = {**{part: _save_profile for part in PROFILE_PARTS}, "people": _save_person}
	if section not in savers:
		frappe.throw(_("There is nothing to save here."))
	if section not in PROFILE_PARTS:
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


PROFILE = ("first_name", "middle_name", "last_name", "gender", "birth_date", "mobile_no", "location", "bio", "language", "time_zone", "user_image")


EMPLOYEE_OWN = (
	"personal_email",
	"prefered_contact_email",
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
	"education": _lt("education"),
	"external_work_history": _lt("past work"),
	"one_documents": _lt("documents"),
}

# The identity documents HR keeps on the Employee (one_hr's Employee
# Document), which the person adds and renews from their profile too.
DOCUMENTS = ("document_type", "number", "issued_on", "expires_on", "attachment")

# The person's own CV on their Employee, edited as two tables: each table's
# columns, and the label it is drawn under.
HISTORY = {
	"education": ("Employee Education", ("qualification", "school_univ", "level", "year_of_passing")),
	"external_work_history": ("Employee External Work History", ("company_name", "designation", "total_experience")),
}


EMERGENCY = ("person_to_be_contacted", "relation", "emergency_phone_number")


SHARED = {"gender": "gender", "birth_date": "date_of_birth", "mobile_no": "cell_number", "user_image": "image"}


AT_WORK = (
	"name",
	"designation",
	"department",
	"reports_to",
	"branch",
	"employment_type",
	"date_of_joining",
	"contract_end_date",
	"notice_number_of_days",
	"company_email",
)


TITLES = {"Employee": "employee_name", "Department": "department_name"}


BANK = ("bank_name", "iban", "bank_ac_no")


def _profile() -> dict:
	user = frappe.get_doc("User", frappe.session.user)
	said = {
		"fields": sections.fields("User", PROFILE),
		"values": {name: user.get(name) for name in PROFILE},
		"email": user.email,
		"full_name": user.full_name,
		"employee": None,
	}
	employee = _employee()
	said["opened"] = sections.opened(user, employee)
	from onedesk.one import privacy

	said["privacy"] = privacy.state()
	if employee:
		said["values"].update({mine: employee.get(theirs) or said["values"].get(mine) for mine, theirs in SHARED.items()})
		said["values"].update({name: employee.get(name) for name in EMPLOYEE_OWN})
		said["values"].update({name: _history_rows(employee, name) for name in HISTORY})
		said["values"]["one_documents"] = _document_rows(employee)
		said["employee"] = {
			"name": employee.name,
			"fields": sections.fields("Employee", EMPLOYEE_OWN)
			+ [{**_history_field(name), "data": said["values"][name]} for name in HISTORY]
			+ [{**_documents_field(employee), "data": said["values"]["one_documents"]}],
			"work": _facts(employee, AT_WORK),
			"bank": [{**one, "value": _masked(one["value"])} if one["fieldname"] != "bank_name" else one for one in _facts(employee, BANK)],
		}
	return said


def _history_field(name: str) -> dict:
	"""One of the CV tables as the page draws it: its own columns, labelled as
	ERPNext labels them, under the heading the page gives it rather than a
	label of its own."""
	child, columns = HISTORY[name]
	meta = frappe.get_meta(child)
	width = 10 // len(columns)
	return {
		"fieldname": name,
		"fieldtype": "Table",
		"label": "",
		"description": None,
		"fields": [
			{
				"fieldname": one,
				"fieldtype": "Data" if meta.get_field(one).fieldtype in ("Small Text", "Text") else meta.get_field(one).fieldtype,
				"label": _(meta.get_field(one).label),
				"options": meta.get_field(one).options,
				"in_list_view": 1,
				"columns": width,
			}
			for one in columns
		],
	}


def _history_rows(employee, name: str) -> list[dict]:
	columns = HISTORY[name][1]
	return [{one: row.get(one) for one in columns} for row in employee.get(name) or []]


def _document_rows(employee) -> list[dict]:
	return [{"name": row.name, **{one: row.get(one) for one in DOCUMENTS}} for row in employee.get("one_documents") or []]


def _documents_field(employee) -> dict:
	"""The identity documents as a table the person edits: its kinds those of
	the workspace's countries and every country's (one_hr/papers.py), and
	above it which have run out."""
	from onedesk.one_hr import papers

	meta = frappe.get_meta("Employee Document")
	today = frappe.utils.getdate()
	gone = [
		_("{0} on {1}").format(_(row.document_type), frappe.utils.formatdate(row.expires_on))
		for row in employee.get("one_documents") or []
		if row.expires_on and frappe.utils.getdate(row.expires_on) < today
	]
	columns = {"document_type": 3, "number": 2, "issued_on": 2, "expires_on": 2, "attachment": 1}
	return {
		"fieldname": "one_documents",
		"fieldtype": "Table",
		"label": "",
		"description": _("Expired: {0}.").format(", ".join(gone)) if gone else None,
		"fields": [
			{
				"fieldname": one,
				"fieldtype": "Select" if one == "document_type" else meta.get_field(one).fieldtype,
				"label": _(meta.get_field(one).label),
				"options": "\n".join(["", *papers.offered()]) if one == "document_type" else meta.get_field(one).options,
				"in_list_view": 1,
				"columns": width,
				"reqd": 1 if one in ("document_type", "number") else 0,
			}
			for one, width in columns.items()
		],
	}


def _keep_documents(employee, rows: list) -> None:
	"""The person's documents as they left them: a row they kept is changed
	in place, so what HR set on it (where it was issued) stays; a new one is
	added; one they removed goes."""
	held = {row.name: row for row in employee.get("one_documents") or []}
	kept = []
	for one in rows or []:
		if not any(one.get(field) for field in DOCUMENTS):
			continue
		row = held.get(one.get("name"))
		if row:
			row.update({field: one.get(field) for field in DOCUMENTS})
			kept.append(row)
		else:
			kept.append(employee.append("one_documents", {field: one.get(field) for field in DOCUMENTS}))
	employee.set("one_documents", kept)


def _file_scans(employee) -> None:
	"""Each scan the person put on a document row moved into their Employee's
	room in OneCloud, beside their other papers, rather than left loose. Only
	files they uploaded themselves and nothing has claimed yet: a URL typed
	into the row cannot pull in somebody else's file."""
	urls = [row.attachment for row in employee.get("one_documents") or [] if row.attachment]
	if not urls:
		return
	for name in frappe.get_all(
		"File",
		filters={"file_url": ["in", urls], "owner": frappe.session.user, "attached_to_name": ["is", "not set"], "is_folder": 0},
		pluck="name",
	):
		frappe.db.set_value("File", name, {"attached_to_doctype": "Employee", "attached_to_name": employee.name, "folder": "Home/Attachments"})


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
	"""Both records, each as it was opened, saved here rather than one by the
	other (sync.py), so neither is changed under the other's check."""
	from onedesk.account_center import sync

	frappe.flags[sync.FLAG] = True
	try:
		_save_both(values, sync)
	finally:
		frappe.flags[sync.FLAG] = False


def _save_both(values: dict, sync) -> None:
	user = sections.as_opened(frappe.get_doc("User", frappe.session.user))
	user.update({name: values[name] for name in PROFILE if name in values})
	user.save(ignore_permissions=True)
	employee = _employee()
	if not employee:
		return
	changes = {name: values[name] for name in EMPLOYEE_OWN if name in values}
	was = {name: employee.get(name) for name in TOLD_HR if name not in HISTORY}
	was.update({name: _history_rows(employee, name) for name in HISTORY})
	was["one_documents"] = _now(employee, "one_documents")
	sections.as_opened(employee).update(changes)
	sync.to_employee(user, employee, [one for one in sync.PAIRS if one in values])
	for name, (_child, columns) in HISTORY.items():
		if name in values:
			employee.set(name, [{one: row.get(one) for one in columns} for row in values[name] or [] if any(row.get(one) for one in columns)])
	if "one_documents" in values:
		_keep_documents(employee, values["one_documents"])
	if any(employee.get(name) for name in EMERGENCY) and not (
		employee.person_to_be_contacted and employee.emergency_phone_number
	):
		frappe.throw(_("An emergency contact needs a name and a phone number, so HR can call them."))
	employee.save(ignore_permissions=True)
	_file_scans(employee)
	_tell_hr(employee, was)


def _tell_hr(employee, was: dict) -> None:
	"""HR learns when a person changes where they live or who to call, once
	per save, saying what changed. Not the person themselves, if they are HR."""
	said = list(
		dict.fromkeys(
			str(label)
			for name, label in TOLD_HR.items()
			if (was.get(name) or "") != _now(employee, name)
		)
	)
	if not said:
		return
	from onedesk.one_hr import tell as hr

	hr.employee_details_changed(employee, said)


def _now(employee, name: str):
	if name in HISTORY:
		return _history_rows(employee, name) or ""
	if name == "one_documents":
		return [{key: str(value) if value else value for key, value in row.items()} for row in _document_rows(employee)] or ""
	return employee.get(name) or ""


def _signin() -> dict:
	from onedesk.account_center import signin

	said = signin.facts()
	return {**said, "warnings": signin.warnings(said), "administers": roles.administers()}


@frappe.whitelist(methods=["POST"])
def sign_out_elsewhere() -> int:
	"""Every other session of this person ends; this one stays."""
	from frappe.sessions import clear_sessions

	clear_sessions(frappe.session.user, keep_current=True)
	return 1


def _people(record: str | None = None) -> dict:
	"""Everybody on the workspace; or the one person the section is open on."""
	from onedesk.account_center import signin

	if record:
		return _person_page(record)
	users = frappe.get_all(
		"User",
		filters={"user_type": "System User", "name": ["not in", NOT_PEOPLE]},
		fields=["name", "full_name", "enabled", "last_active", "user_image"],
		order_by="enabled desc, full_name asc",
		limit=500,
	)
	held = roles_held([one.name for one in users])
	employees = dict(
		frappe.get_all("Employee", filters={"user_id": ["in", [one.name for one in users] or [""]]}, fields=["user_id", "name"], as_list=True)
	)
	account = frappe.get_single("Workspace Account")
	own = all_levels()
	return {
		"apps": [{"name": name, "icon": icon, "levels": levels_of(name, own)} for name, icon, _used, _managed in APPS],
		"levels": [{"value": one, "label": _(one)} for one in LEVELS],
		"people": [
			{
				**one,
				"admin": roles.ADMINISTRATOR in held.get(one.name, set()),
				"access": listed(held.get(one.name, set()), own),
				"employee": employees.get(one.name),
				"way_in": signin.way_in(one.name),
			}
			for one in users
		],
		"seats": account.seats or 0,
		"used": sum(1 for one in users if one.enabled),
		"me": frappe.session.user,
	}


def _person_page(user: str) -> dict:
	"""One person as an administrator sees them, as a form: a Select per app
	and the Administrator switch, saved against the User as it was loaded;
	where they are signed in and their last sign-ins (account_center/signin.py), and the
	records they are held to (one/access.py)."""
	from onedesk.one import access
	from onedesk.account_center import signin

	doc = one_of_the_people(user)
	held = {one.role for one in doc.roles}
	own = all_levels()
	fields = [
		{"fieldname": f"app_{icon}", "fieldtype": "Select", "label": name, "options": levels_of(name, own), "description": str(APP_SAID[name])}
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
			"way_in": signin.way_in(doc.name),
			"me": me,
			"holds": access.record_access(doc.name),
			"kinds": access.kinds_held(),
		},
		"profiles": {one["name"]: one["levels"] for one in access.profiles()},
		"apps": [{"name": name, "icon": icon, "levels": levels_of(name, own)} for name, icon, _used, _managed in APPS],
		"fields": fields,
		"values": {
			**{f"app_{icon}": app_level(name, held, used, managed, own.get(name, ())) for name, icon, used, managed in APPS},
			"admin": 1 if roles.ADMINISTRATOR in held else 0,
			"profile": doc.get("one_profile") or "",
		},
		"opened": sections.opened(doc),
	}


def _save_person(record: str, values: dict) -> None:
	"""What a person may use. A profile picked sets every app at once; an app
	changed by hand takes them off the profile they were on."""
	from onedesk.one import access as profiles

	doc = sections.as_opened(one_of_the_people(record))
	chosen = {name: values.get(f"app_{icon}") for name, icon, _used, _managed in APPS if values.get(f"app_{icon}")}
	admin = frappe.utils.cint(values.get("admin")) if "admin" in values else int(roles.ADMINISTRATOR in {one.role for one in doc.roles})
	if values.get("profile") and values["profile"] != doc.get("one_profile"):
		set_access(doc, profiles.profile(values["profile"])["levels"], admin)
		frappe.db.set_value("User", doc.name, "one_profile", values["profile"], update_modified=False)
		return
	set_access(doc, chosen, admin)
	on = values.get("profile", doc.get("one_profile"))
	if on and any(level != profiles.profile(on)["levels"].get(name) for name, level in chosen.items()):
		on = None
	if (on or None) != (doc.get("one_profile") or None):
		frappe.db.set_value("User", doc.name, "one_profile", on or None, update_modified=False)


@frappe.whitelist(methods=["POST"])
def reset_two_factor(user: Annotated[str, "The person."]) -> dict:
	"""A person's authenticator forgotten, for a lost or new phone
	(signin.forget_two_factor)."""
	roles.require()
	from onedesk.account_center import signin

	doc = one_of_the_people(user)
	signin.forget_two_factor(doc.name)
	return _person_page(doc.name)


@frappe.whitelist(methods=["POST"])
def sign_out_everywhere(user: Annotated[str, "The person."]) -> dict:
	"""Every session a person has, ended: frappe's own, so the Activity Log
	records it. Your own are ended on your Sign-in page."""
	roles.require()
	from frappe.sessions import clear_sessions

	doc = one_of_the_people(user)
	if doc.name == frappe.session.user:
		frappe.throw(_("Sign yourself out from your own Sign-in page."))
	clear_sessions(user=doc.name, force=True)
	return _person_page(doc.name)


@frappe.whitelist(methods=["POST"])
def send_reset(user: Annotated[str, "The person."]) -> None:
	"""Frappe's own password reset mail, sent to the person."""
	roles.require()
	doc = one_of_the_people(user)
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
	from onedesk.account_center import invite as invitation

	wanted = frappe.parse_json(access) or {}
	if any(level != "None" for level in wanted.values()):
		set_access(frappe.get_doc("User", user.name), wanted, 0, told=False)
	invitation.send(user.name, apps_said(wanted))
	return _people()


@frappe.whitelist(methods=["POST"])
def invite_again(user: Annotated[str, "The person."]) -> None:
	"""A new invitation for somebody who has not joined yet; the old link stops."""
	from onedesk.account_center import invite as invitation

	roles.require()
	doc = one_of_the_people(user)
	if doc.last_login:
		frappe.throw(_("{0} has already joined. Send a password reset instead.").format(doc.full_name))
	held = {one.role for one in doc.roles}
	own = all_levels()
	invitation.send(
		doc.name, apps_said({name: level_of(held, used, managed, own.get(name, ())) for name, _icon, used, managed in APPS})
	)


STALE = 60 * 60


def _plan() -> dict:
	"""The workspace's account, as the administrator last said it: asked again
	first when that was over an hour ago, so a pack just paid for shows."""
	from onedesk.one import account
	from onedesk.account_center import closing, heads

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
				"database_limit", "credits_balance", "credits_held", "credits_month", "credits_expiring", "credits_limit", "credits_spent",
				"credits_expires_on", "last_heard", "update_at", "update_weekday", "update_hour",
			)
		},
		"used": seats_used(),
		"state": heads.account_state(held),
		"said": heads.account_said(held),
		"storage": {"used": heads.size(held.storage_bytes), "limit": heads.size(held.storage_limit)},
		"database": {"used": heads.size(held.database_bytes), "limit": heads.size(held.database_limit)},
		"add_ons": [{"offering": one.offering, "label": one.label, "quantity": one.quantity, "amount": one.amount} for one in held.add_ons],
		"linked": account.configured(),
		"admin": roles.administers(),
		"ledger": account.ledger() if account.configured() else None,
		"ledger_days": account.LEDGER_DAYS,
		# An AccountCenter Manager reads the plan; only an administrator is told
		# about the download and who may close it, and anybody that it closes.
		"closing": closing.state()
		if roles.administers()
		else {"closing_on": str(held.closing_on) if held.closing_on else None, "deleted_on": str(held.deleted_on) if held.deleted_on else None},
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
		"linked": account.configured(),
	}


def _devices() -> dict:
	"""The company's machines and every passkey on somebody's own. See
	account_center/devices.py."""
	from onedesk.account_center import devices

	return devices.for_settings()
