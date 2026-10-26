"""AccessCenter (docs/READY.md, mechanism 14): who may do what in each module
that declares its abilities (`one_abilities`, one/rights.py). Its roles
are the matrix one/access.py builds; its people are People's levels of the
app; what one person was given on one record is the module's shares. Only a
workspace administrator reads or changes any of it."""

from typing import Annotated

import frappe
from frappe import _

from onedesk.one import access, rights, roles
from onedesk.one.access import all_levels
from onedesk.one.people import APP_SAID, APPS, levels_of
from onedesk.one.sections import opened as opened_of


def _app(app: str):
	"""The `abilities` module of an app AccessCenter shows, or a refusal."""
	from onedesk.one.people import APPS

	declared = rights.of_app(app)
	if not declared or app not in {name for name, *_rest in APPS}:
		frappe.throw(_("{0} has no roles to set.").format(app))
	return declared


@frappe.whitelist()
def modules() -> list[str]:
	"""The modules AccessCenter has a part for, in People's order."""
	from onedesk.one.people import APPS

	roles.require()
	declared = {one.APP for one in rights.modules()}
	return [name for name, *_rest in APPS if name in declared]


@frappe.whitelist()
def people(app: str) -> dict:
	"""Everybody on the workspace and their role in one app, with the roles
	the app offers: None (unless everybody uses it), User, the workspace's
	own, Manager."""
	from onedesk.one import people

	roles.require()
	_app(app)
	used, managed = next((u, m) for name, _icon, u, m in people.APPS if name == app)
	own = access.levels_of(app)
	users = frappe.get_all(
		"User",
		filters={"user_type": "System User", "enabled": 1, "name": ["not in", people.NOT_PEOPLE]},
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
		limit=500,
	)
	held = people.roles_held([one.name for one in users])
	return {
		"levels": people.levels_of(app, {app: own}),
		"people": [
			{
				"user": one.name,
				"name": one.full_name or one.name,
				"image": one.user_image,
				"level": people.app_level(app, held.get(one.name, set()), used, managed, own),
			}
			for one in users
		],
	}


@frappe.whitelist(methods=["POST"])
def put(app: str, user: str, level: str) -> str:
	"""One person's role in one app, as People sets it; a person on a
	profile that says otherwise comes off it."""
	from onedesk.one import people

	_app(app)
	doc = people.one_of_the_people(user)
	admin = int(roles.ADMINISTRATOR in {one.role for one in doc.roles})
	people.set_access(doc, {app: level}, admin)
	on = doc.get("one_profile")
	if on and access.profile(on)["levels"].get(app) != level:
		frappe.db.set_value("User", doc.name, "one_profile", None, update_modified=False)
	return level


def _title(declared, name: str) -> str:
	"""What a record is called where AccessCenter lists it: the field its
	module names (`TITLE`), else its doctype's title field, else its name."""
	field = getattr(declared, "TITLE", None) or frappe.get_meta(declared.DOCTYPE).get_title_field()
	return frappe.db.get_value(declared.DOCTYPE, name, field) or name


@frappe.whitelist()
def records(app: str) -> dict:
	"""Every person given more than their role on one record of the app, and
	what: each of the module's shares that carries one of its rights."""
	roles.require()
	declared = _app(app)
	shared = [one for one in declared.ABILITIES if one["key"] in declared.SHARED]
	ptypes = {one["all"]: one["key"] for one in shared}
	rows = frappe.get_all(
		"DocShare",
		filters={"share_doctype": declared.DOCTYPE, "everyone": 0},
		fields=["user", "share_name", *ptypes],
		order_by="share_name asc",
	)
	names = {row.user for row in rows}
	full = dict(frappe.get_all("User", filters={"name": ["in", list(names) or [""]]}, fields=["name", "full_name"], as_list=True))
	grants = []
	for row in rows:
		given = [key for ptype, key in ptypes.items() if row.get(ptype)]
		if given:
			grants.append(
				{
					"record": row.share_name,
					"title": _title(declared, row.share_name),
					"user": row.user,
					"name": full.get(row.user) or row.user,
					"given": given,
				}
			)
	return {
		"abilities": [{"key": one["key"], "label": str(one["label"])} for one in shared],
		"grants": grants,
	}


@frappe.whitelist(methods=["POST"])
def give(app: str, record: str, user: str, keys: str | list) -> list[str]:
	"""What one person may do on one record beyond their role; none takes
	the share away (rights.grant)."""
	roles.require()
	_app(app)
	return rights.grant(app, record, user, list(frappe.parse_json(keys) or []))


# The workspace's own roles, profiles and groups, for the apps that don't
# declare abilities: a CenterSection (center_section.js) loads them here
# and saves them back, a role, profile or group as the record it is open on.
@frappe.whitelist()
def load(
	section: Annotated[str, "Which section: access."],
	record: Annotated[str | None, "level:<key>, profile:<name>, group:<name>, or nothing for the lists."] = None,
) -> dict:
	roles.require()
	if section != "access":
		frappe.throw(_("There is no such section."))
	return _access(record)


@frappe.whitelist(methods=["POST"])
def save(
	section: Annotated[str, "Which section: access."],
	values: Annotated[str | dict, "What was changed."],
	opened: Annotated[str | list | None, "The records as the page loaded them: doctype, name and modified."] = None,
	record: Annotated[str | None, "The role, profile or group it is open on."] = None,
) -> dict:
	roles.require()
	if section != "access":
		frappe.throw(_("There is nothing to save here."))
	frappe.flags.one_opened = {f"{one['doctype']}:{one['name']}": one["modified"] for one in frappe.parse_json(opened) or []}
	record = _save_access(record, frappe.parse_json(values) or {}) or record
	frappe.db.commit()
	return {**_access(record), "record": record}


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
	from onedesk.one import rights

	return rights.doctypes()


def _ability_fields(app: str, held: list[dict]) -> list[dict]:
	"""A level's abilities as fields: a switch, or a choice of scope from the
	least the level can have (User's) up."""
	from onedesk.one import rights

	declared = rights.of_app(app)
	if not declared:
		return []
	names = getattr(declared, "SCOPE_LABELS", {})
	fields = []
	for one in held:
		field = {"fieldname": f"ability_{one['key']}", "label": one["label"], "description": str(one.get("about") or "")}
		if one["kind"] == "switch":
			fields.append({**field, "fieldtype": "Switch", "read_only": int(bool(one["least"]))})
			continue
		order = rights.SCOPES
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
