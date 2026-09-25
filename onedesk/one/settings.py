"""Settings: one place for everything a person or a workspace sets.

Before this a workspace manager had no single place to go. The account was a
bare form, Intake Settings sat in its own sidebar, mailboxes were in OneMail,
holidays in OneCalendar's Setup, people in frappe's User list, and a person's
own settings were frappe's My Settings. Now every section is an entry in One's
own sidebar, so the page itself is one wide column, in two groups:

- **You**, for everybody: profile, notifications, mail, calendar, sign-in, and
  what OneAI remembers about you.
- **Workspace**, for its administrators only: general, people, plan and
  credits, domains, OneAI, Intake and holidays. These open a second page,
  `workspace-settings`, whose only role is Workspace Administrator, so frappe
  hides the entries from everybody else.

Nothing new is stored. Each section reads and writes the records that already
hold it — User, Notification Settings, Company, System Settings, Workspace
Account, AI Action Setting, Intake Settings, Holiday List — and the verbs that
already exist are called as they are (a mailbox is connected in OneMail, a
domain through the account). A workspace section asks `roles.require()`
first, so a person who is not an administrator cannot reach it by calling it.
"""

from typing import Annotated

import frappe
from frappe import _, _lt

from onedesk.one import roles

#: (key, label, icon, group). The icons are Lucide, from frappe's sprite.
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
	("notification_types", _lt("Notifications"), "bell-ring", "workspace"),
	("plan", _lt("Plan and Credits"), "credit-card", "workspace"),
	("domains", _lt("Domains"), "globe", "workspace"),
	("oneai", _lt("OneAI"), "sparkles", "workspace"),
	("intake", _lt("Intake"), "inbox", "workspace"),
	("holidays", _lt("Holidays"), "calendar-days", "workspace"),
]

#: What a person may reach in each app, as frappe's own roles: using it, and
#: managing it. Everybody on the desk has One, OneCloud, OneMail, OneTask and
#: OneCalendar; these are the apps whose records are somebody's job.
APPS = [
	("OneCRM", "onecrm", ("Sales User",), ("Sales Manager",)),
	("OneBook", "onebook", ("Accounts User",), ("Accounts Manager",)),
	("OneInventory", "oneinventory", ("Stock User", "Purchase User"), ("Stock Manager", "Purchase Manager", "Item Manager")),
	("OneProject", "oneproject", ("Projects User",), ("Projects Manager",)),
	("OneHR", "onehr", ("HR User",), ("HR Manager",)),
]

LEVELS = ("None", "User", "Manager")

#: Who is never listed among the people: the bench's own account, the guest,
#: and the user OneAI writes as.
NOT_PEOPLE = ("Administrator", "Guest", "oneai@one.invalid")

#: What a person may change about themselves here.
PROFILE = ("first_name", "last_name", "gender", "birth_date", "mobile_no", "location", "bio", "language", "time_zone", "user_image")

#: What a person keeps up to date on their own employee record: how to reach
#: them, who to call, and two facts HR asks for. Their pay and their job are
#: HR's to change, so those are shown and not asked.
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

#: Said on both records. The employee's copy is the one HR reads, and erpnext
#: copies it onto the login on every save of the employee, so a change here
#: goes to the employee first or the next save would undo it.
SHARED = {"gender": "gender", "birth_date": "date_of_birth", "mobile_no": "cell_number", "user_image": "image"}

#: What the page shows of a person's job, as HR set it.
AT_WORK = ("name", "designation", "department", "reports_to", "branch", "employment_type", "date_of_joining", "company_email")

#: What a linked record is called on screen, where its id is not its name. A
#: department's id carries the company's abbreviation, which one company does
#: not need.
TITLES = {"Employee": "employee_name", "Department": "department_name"}

#: Where their pay goes, shown with all but the last four hidden.
BANK = ("bank_name", "iban", "bank_ac_no")

#: A person's own switches on Notification Settings. Which types they are
#: mailed is the rest of the section, one tick each (`_notifications`); frappe
#: hides its older per-kind checkboxes, which no longer decide anything.
NOTIFY = (
	"enabled",
	"enable_email_notifications",
	"enable_email_event_reminders",
	"enable_email_threads_on_assigned_document",
)

#: Frappe's labels for those, as a person would say them.
NOTIFY_SAID = {
	"enabled": (_lt("Notifications"), _lt("Off, nothing reaches your bell or your inbox.")),
	"enable_email_notifications": (_lt("Also by Email"), _lt("Off, nothing is mailed to you, whatever is ticked below.")),
	"enable_email_event_reminders": (_lt("Event Reminders"), _lt("A mail before an event of yours starts.")),
	"enable_email_threads_on_assigned_document": (
		_lt("Mail About What Is Assigned to You"),
		_lt("The mails on a record you were given to do, as they arrive."),
	),
}

INTAKE = ("records", "most_pages", "floor", "audit", "keep_in_place", "quiet_minutes", "household", "submit_einvoices")

SYSTEM = ("date_format", "time_format", "number_format", "first_day_of_the_week")

#: Sections that list several records and open on one of them.
ON_A_RECORD = ("notification_types",)

#: What an administrator sets on a notification type: whether it is sent, its
#: text, and the channels people may choose for it.
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
		"plan": _plan,
		"domains": _domains,
		"oneai": _oneai,
		"intake": _intake,
		"holidays": _holidays,
		"notification_types": _notification_types,
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
	# What the page loaded, so a record changed since is refused the way a
	# desk form refuses it, rather than overwritten.
	frappe.flags.one_opened = {f"{one['doctype']}:{one['name']}": one["modified"] for one in frappe.parse_json(opened) or []}
	savers = {
		"profile": _save_profile,
		"notifications": _save_notifications,
		"general": _save_general,
		"intake": _save_intake,
		"holidays": _save_holidays,
		"notification_types": _save_notification_type,
	}
	if section not in savers:
		frappe.throw(_("There is nothing to save here."))
	if _group(section) == "workspace":
		roles.require()
	if section in ON_A_RECORD:
		# A new record comes back under its own name.
		record = savers[section](record, values) or record
	else:
		savers[section](values)
	frappe.db.commit()
	return load(section, record)


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
				"label": _(field.label),
				"options": field.options,
				"description": _(field.description) if field.description else None,
			}
		)
	return out


# ------------------------------------------------------------------ you


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
	# Oneself, and only these fields: frappe's own rule for My Settings.
	user.save(ignore_permissions=True)
	employee = _employee()
	if not employee:
		return
	# The login first: saving the employee copies its fields onto the login,
	# which would find a login changed underneath it the other way round.
	changes = {name: values[name] for name in EMPLOYEE_OWN if name in values}
	changes.update({theirs: values[mine] for mine, theirs in SHARED.items() if mine in values})
	_as_opened(employee).update(changes)
	# Their own record, and only these fields.
	employee.save(ignore_permissions=True)


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
		field.update({"label": str(label), "description": str(description)})
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
				"options": f'<div class="os-kind-name">{esc(one["label"])}</div>'
				f'<div class="os-quiet">{esc(_said_of(one))}</div>',
				"depends_on": "eval:doc.enabled",
			},
			{
				"fieldname": email,
				"fieldtype": "Check",
				"label": str(_("Email")),
				"read_only": 0 if one["allowed"] else 1,
				"depends_on": "eval:doc.enabled",
			},
			{
				"fieldname": pushing,
				"fieldtype": "Check",
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
		# Product names are names; the workspace's own rules are "Rules", in the reader's words.
		"groups": [{"app": _(app) if app else str(_("Across One")), "rows": rows} for app, rows in groups.items()],
		"push": push.devices(),
		"opened": _opened(doc),
	}


def _said_of(one: dict) -> str:
	"""What a kind is, and why a tick cannot be changed when it cannot."""
	said = [one["about"]]
	if one.get("always"):
		said.append(_("Its mail is always sent, so you can answer it by replying."))
	elif not one["allowed"]:
		said.append(_("It is not mailed in this workspace."))
	if not one["push"]:
		said.append(_("It is not pushed in this workspace."))
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
		kept = [row.notification_type for row in doc.get(field) or [] if row.notification_type not in chosen]
		doc.set(field, [{"notification_type": name} for name in kept + [name for name, on in chosen.items() if on]])
	doc.save(ignore_permissions=True)


def _mail() -> dict:
	from onedesk.one_mail import holders

	return {"mailboxes": holders.mailboxes()}


def _calendar() -> dict:
	return {"has_feed": bool(frappe.db.exists("Calendar Feed", frappe.session.user))}


def _signin() -> dict:
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
	passkey = None
	if employee:
		from onedesk.one_hr import passkey as keys

		passkey = bool(keys.held_by(employee))
	sessions = frappe.db.count("Sessions", {"user": frappe.session.user}) if frappe.db.table_exists("Sessions") else None
	return {"employee": employee, "passkey": passkey, "sessions": sessions}


@frappe.whitelist(methods=["POST"])
def sign_out_elsewhere() -> int:
	"""Every other session of this person ends; this one stays."""
	from frappe.sessions import clear_sessions

	clear_sessions(frappe.session.user, keep_current=True)
	return 1


def _memory() -> dict:
	rows = frappe.get_all(
		"AI Memory",
		filters={"owner": frappe.session.user},
		fields=["name", "fact", "about_doctype", "about_name", "creation"],
		order_by="creation desc",
		limit=200,
	)
	return {"facts": rows}


@frappe.whitelist(methods=["POST"])
def forget(name: Annotated[str, "The AI Memory to forget."]) -> dict:
	"""One thing OneAI remembers about the reader, forgotten."""
	doc = frappe.get_doc("AI Memory", name)
	doc.check_permission("delete")
	doc.delete()
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
			# The reader's own row, or the organisation's, which everybody in it
			# is bound by and so may see.
			ignore_permissions=True,
		)
		if not rows:
			return None
		row = rows[0]
		return {
			"version": row.version,
			# Asked again only for a new revision; a new hash is shown, not asked.
			"owed": not gate.agreed(row.version, assemble.version_of(key)),
			"on": frappe.utils.formatdate(row.accepted_on),
			"by": frappe.utils.get_fullname(row.user) if party == gate.WORKSPACE else None,
		}

	documents = []
	for key, one in DOCUMENTS.items():
		version = assemble.version_of(key)
		parties = gate.AUDIENCE.get(one["audience"], ())
		# Through a name, not `_(one["title"])`: the extractor would take the
		# key for the text. The titles are extracted from one_legal/gate.SHOWN.
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


# ------------------------------------------------------------------ the workspace


def _company():
	name = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	return frappe.get_doc("Company", name) if name else None


def _general() -> dict:
	company = _company()
	system = frappe.get_single("System Settings")
	account = frappe.get_single("Workspace Account")
	return {
		"name": account.workspace_name,
		"company": company.company_name if company else None,
		"country": company.country if company else system.country,
		"currency": company.default_currency if company else None,
		"fields": _fields("Company", ("company_logo",)) + _fields("System Settings", ("language", "time_zone", *SYSTEM)),
		"values": {
			"company_logo": company.company_logo if company else None,
			"language": system.language,
			"time_zone": system.time_zone,
			**{name: system.get(name) for name in SYSTEM},
		},
	}


def _save_general(values: dict) -> None:
	company = _company()
	if company and "company_logo" in values:
		company.company_logo = values["company_logo"]
		company.save(ignore_permissions=True)
	system = frappe.get_single("System Settings")
	system.update({name: values[name] for name in ("language", "time_zone", *SYSTEM) if name in values})
	system.save(ignore_permissions=True)


def level_of(held: set, used: tuple, managed: tuple) -> str:
	"""None, User or Manager, from the roles a person holds. Pure."""
	if held & set(managed):
		return "Manager"
	if held & set(used):
		return "User"
	return "None"


def roles_for(level: str, used: tuple, managed: tuple) -> set:
	"""The roles a level means: a manager uses the app as well. Pure."""
	return {"None": set(), "User": set(used), "Manager": set(used) | set(managed)}[level]


def _people() -> dict:
	users = frappe.get_all(
		"User",
		filters={"user_type": "System User", "name": ["not in", NOT_PEOPLE]},
		fields=["name", "full_name", "enabled", "last_active", "user_image"],
		order_by="enabled desc, full_name asc",
		limit=500,
	)
	held = {}
	for row in frappe.get_all("Has Role", filters={"parenttype": "User", "parent": ["in", [one.name for one in users]]}, fields=["parent", "role"], limit=0):
		held.setdefault(row.parent, set()).add(row.role)
	account = frappe.get_single("Workspace Account")
	return {
		"apps": [{"name": name, "icon": icon} for name, icon, _used, _managed in APPS],
		"levels": [{"value": one, "label": _(one)} for one in LEVELS],
		"people": [
			{
				**one,
				"admin": roles.ADMINISTRATOR in held.get(one.name, set()),
				"access": {name: level_of(held.get(one.name, set()), used, managed) for name, _icon, used, managed in APPS},
			}
			for one in users
		],
		"seats": account.seats or 0,
		"used": sum(1 for one in users if one.enabled),
	}


@frappe.whitelist(methods=["POST"])
def set_access(
	user: Annotated[str, "The person."],
	app: Annotated[str, "OneCRM, OneBook, OneInventory, OneProject or OneHR."],
	level: Annotated[str, "None, User or Manager."],
) -> dict:
	"""What a person may do in one app, as frappe's roles."""
	roles.require()
	found = next((one for one in APPS if one[0] == app), None)
	if not found or level not in LEVELS or user in NOT_PEOPLE:
		frappe.throw(_("That cannot be set."))
	_name, _icon, used, managed = found
	doc = frappe.get_doc("User", user)
	want = roles_for(level, used, managed)
	doc.remove_roles(*[role for role in set(used) | set(managed) if role not in want])
	doc.add_roles(*[role for role in want if frappe.db.exists("Role", role)])
	return _people()


@frappe.whitelist(methods=["POST"])
def set_admin(user: Annotated[str, "The person."], on: Annotated[int, "1 to make them an administrator."]) -> dict:
	"""Whether a person administers the workspace. Nobody removes the last."""
	roles.require()
	if user in NOT_PEOPLE:
		frappe.throw(_("That cannot be set."))
	doc = frappe.get_doc("User", user)
	if int(on):
		doc.add_roles(roles.ADMINISTRATOR)
	else:
		others = frappe.get_all("Has Role", filters={"role": roles.ADMINISTRATOR, "parenttype": "User", "parent": ["not in", (user, *NOT_PEOPLE)]}, pluck="parent")
		if not [one for one in others if frappe.db.get_value("User", one, "enabled")]:
			frappe.throw(_("A workspace needs at least one administrator."))
		doc.remove_roles(roles.ADMINISTRATOR)
	return _people()


@frappe.whitelist(methods=["POST"])
def set_enabled(user: Annotated[str, "The person."], on: Annotated[int, "1 to let them sign in."]) -> dict:
	"""A person may sign in, or not. Their records stay either way."""
	roles.require()
	if user in NOT_PEOPLE or user == frappe.session.user:
		frappe.throw(_("You cannot turn yourself off."))
	if int(on):
		_seat_left()
	frappe.db.set_value("User", user, "enabled", int(on))
	return _people()


@frappe.whitelist(methods=["POST"])
def invite(
	email: Annotated[str, "Their address."],
	first_name: Annotated[str, "Their first name."],
	last_name: Annotated[str | None, "Their last name."] = None,
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
	_seat_left()
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"user_type": "System User",
			"send_welcome_email": 1,
			"roles": [{"role": "Desk User"}],
		}
	)
	user.insert(ignore_permissions=True)
	return _people()


def _seat_left() -> None:
	seats = frappe.get_single("Workspace Account").seats or 0
	used = frappe.db.count("User", {"user_type": "System User", "enabled": 1, "name": ["not in", NOT_PEOPLE]})
	if seats and used >= seats:
		frappe.throw(_("All {0} seats are taken. Turn somebody off, or add seats to the plan.").format(seats))


def _plan() -> dict:
	account = frappe.get_single("Workspace Account").as_dict()
	used = frappe.db.count("User", {"user_type": "System User", "enabled": 1, "name": ["not in", NOT_PEOPLE]})
	from onedesk.one_intake import digest

	return {"account": account, "used": used, "month": digest.said(digest.this_month())}


def _domains() -> dict:
	"""What the account last said, without a round trip: Check Again asks."""
	rows = frappe.get_single("Workspace Account").domains
	return {"domains": [{"domain": one.domain, "status": one.status, "primary": one.primary, "provided": one.given} for one in rows]}


def _oneai() -> dict:
	chosen = {one.action: one for one in frappe.get_all("AI Action Setting", fields=["name", "action", "model", "extra"])}
	actions = frappe.get_all("AI Action", filters={"enabled": 1}, fields=["name", "label", "about", "capability"], order_by="label asc")
	return {
		"actions": [
			{**one, "label": _(one.label), "about": _(one.about) if one.about else None, "model": (chosen.get(one.name) or {}).get("model"), "setting": (chosen.get(one.name) or {}).get("name")}
			for one in actions
		],
		"knowledge": frappe.db.count("AI Knowledge", {"enabled": 1}),
	}


def _intake() -> dict:
	from onedesk.one_intake import digest

	doc = frappe.get_single("Intake Settings")
	return {"fields": _fields("Intake Settings", INTAKE), "values": {name: doc.get(name) for name in INTAKE}, "month": digest.said(digest.this_month())}


def _save_intake(values: dict) -> None:
	doc = frappe.get_single("Intake Settings")
	doc.update({name: values[name] for name in INTAKE if name in values})
	doc.save(ignore_permissions=True)


def _holidays() -> dict:
	company = _company()
	chosen = company.default_holiday_list if company else None
	coming = (
		frappe.get_all(
			"Holiday",
			filters={"parent": chosen, "holiday_date": [">=", frappe.utils.today()], "weekly_off": 0},
			fields=["holiday_date", "description"],
			order_by="holiday_date asc",
			limit=8,
		)
		if chosen
		else []
	)
	return {
		"lists": frappe.get_all("Holiday List", pluck="name", order_by="to_date desc"),
		"chosen": chosen,
		"coming": [{"date": one.holiday_date, "what": frappe.utils.strip_html_tags(one.description or "")} for one in coming],
	}


def _save_holidays(values: dict) -> None:
	company = _company()
	if company and values.get("holiday_list") and frappe.db.exists("Holiday List", values["holiday_list"]):
		company.default_holiday_list = values["holiday_list"]
		company.save(ignore_permissions=True)


# ------------------------------------------------------------------ notifications


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
				"enabled": row.enabled,
				"edited": bool(row.one_default_subject)
				and (row.one_subject != row.one_default_subject or row.one_message != row.one_default_message),
				"outside": row.one_outside,
				"required": bool(one.get("required")),
				"always": bool(one.get("always_mailed")),
				"ours": bool(one),
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
	# Ours by app, then frappe's own, which every app shares.
	return {
		"rules": [{"name": one.name, "enabled": one.enabled, "said": rules.said(one)} for one in made],
		"apps": [{"app": app, "types": types} for app, types in sorted(apps.items(), key=lambda one: (not one[0], one[0]))],
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
			# A few lines, wrapped, rather than a code editor's thirty.
			field.update({"wrap": 1, "min_lines": 3, "max_lines": 12})
		if field["fieldname"] == "enabled":
			field["label"] = _("Send This")
			field["read_only"] = 1 if one.get("required") else 0
	return {
		"type": {
			"name": doc.name,
			"label": _(doc.name),
			"app": doc.one_app,
			"about": _(doc.one_about) if doc.one_about else None,
			"ours": bool(one),
			"outside": doc.one_outside,
			"required": bool(one.get("required")),
			"always": bool(one.get("always_mailed")),
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


# ------------------------------------------------------------------ rules

#: What a rule form sets on the Notification itself.
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

#: What it sets on the rule's notification type: the channels people may add.
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
		# Frappe's Notification starts with a sample message; a rule starts empty.
		doc.update({"enabled": 1, "event": "New", "channel": "System Notification", "message": ""})
	kind = (
		frappe.db.get_value("Notification Type", doc.name, RULE_CHANNELS, as_dict=True) if not new else None
	)
	fields = _fields("Notification", RULE)
	said = {
		"enabled": (_("Send This"), None),
		"document_type": (_("Kind of Record"), _("Only kinds you can open yourself.")),
		"event": (_("When"), None),
		"date_changed": (_("The Date"), None),
		"days_in_advance": (_("Days"), None),
		"value_changed": (_("The Field"), None),
		"subject": (_("Subject"), _("One line. {{ doc.field }} puts a field of the record in.")),
		"message": (_("Message"), _("The detail under the bell, and the body of the mail. It may be empty.")),
		"send_to_all_assignees": (_("Whoever It Is Assigned To"), None),
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
