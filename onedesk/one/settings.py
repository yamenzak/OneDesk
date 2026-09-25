"""Settings: one place for everything a person or a workspace sets.

Before this a workspace manager had no single place to go. The account was a
bare form, Intake Settings sat in its own sidebar, mailboxes were in OneMail,
holidays in OneCalendar's Setup, people in frappe's User list, and a person's
own settings were frappe's My Settings. **Settings** (the avatar menu, and One's
sidebar) is one page with the sections down the side:

- **You**, for everybody: profile, notifications, mail, calendar, sign-in, and
  what OneAI remembers about you.
- **Workspace**, for its administrators only: general, people, plan and
  credits, domains, OneAI, Intake and holidays.

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
	("general", _lt("General"), "building-2", "workspace"),
	("people", _lt("People"), "users", "workspace"),
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
PROFILE = ("first_name", "last_name", "mobile_no", "language", "time_zone", "user_image")

NOTIFY = (
	"enabled",
	"enable_email_notifications",
	"enable_email_mention",
	"enable_email_assignment",
	"enable_email_share",
	"enable_email_event_reminders",
	"enable_email_threads_on_assigned_document",
)

INTAKE = ("records", "most_pages", "floor", "audit", "keep_in_place", "quiet_minutes", "household", "submit_einvoices")

SYSTEM = ("date_format", "time_format", "number_format", "first_day_of_the_week")


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
def load(section: Annotated[str, "Which section."]) -> dict:
	loaders = {
		"profile": _profile,
		"notifications": _notifications,
		"mail": _mail,
		"calendar": _calendar,
		"signin": _signin,
		"memory": _memory,
		"general": _general,
		"people": _people,
		"plan": _plan,
		"domains": _domains,
		"oneai": _oneai,
		"intake": _intake,
		"holidays": _holidays,
	}
	if section not in loaders:
		frappe.throw(_("There is no such section."))
	if _group(section) == "workspace":
		roles.require()
	return loaders[section]()


@frappe.whitelist(methods=["POST"])
def save(section: Annotated[str, "Which section."], values: Annotated[str | dict, "What was changed."]) -> dict:
	values = frappe.parse_json(values) or {}
	savers = {
		"profile": _save_profile,
		"notifications": _save_notifications,
		"general": _save_general,
		"intake": _save_intake,
		"holidays": _save_holidays,
	}
	if section not in savers:
		frappe.throw(_("There is nothing to save here."))
	if _group(section) == "workspace":
		roles.require()
	savers[section](values)
	frappe.db.commit()
	return load(section)


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
	return {
		"fields": _fields("User", PROFILE),
		"values": {name: user.get(name) for name in PROFILE},
		"email": user.email,
		"full_name": user.full_name,
	}


def _save_profile(values: dict) -> None:
	user = frappe.get_doc("User", frappe.session.user)
	user.update({name: values[name] for name in PROFILE if name in values})
	# Oneself, and only these fields: frappe's own rule for My Settings.
	user.save(ignore_permissions=True)


def _notifications() -> dict:
	from frappe.desk.doctype.notification_settings.notification_settings import create_notification_settings

	if not frappe.db.exists("Notification Settings", frappe.session.user):
		create_notification_settings(frappe.session.user)
	doc = frappe.get_doc("Notification Settings", frappe.session.user)
	return {"fields": _fields("Notification Settings", NOTIFY), "values": {name: doc.get(name) for name in NOTIFY}}


def _save_notifications(values: dict) -> None:
	doc = frappe.get_doc("Notification Settings", frappe.session.user)
	doc.update({name: values[name] for name in NOTIFY if name in values})
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
