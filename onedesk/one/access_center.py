"""AccessCenter (docs/READY.md, mechanism 14): who may do what in each module
that declares its abilities (`one_abilities`, one/abilities.py). Its roles
are the matrix one/access.py builds; its people are People's levels of the
app; what one person was given on one record is the module's shares. Only a
workspace administrator reads or changes any of it."""

import frappe
from frappe import _

from onedesk.one import abilities, access, roles


def _app(app: str):
	"""The `abilities` module of an app AccessCenter shows, or a refusal."""
	from onedesk.one.settings import APPS

	declared = abilities.of_app(app)
	if not declared or app not in {name for name, *_rest in APPS}:
		frappe.throw(_("{0} has no roles to set.").format(app))
	return declared


@frappe.whitelist()
def modules() -> list[str]:
	"""The modules AccessCenter has a part for, in People's order."""
	from onedesk.one.settings import APPS

	roles.require()
	declared = {one.APP for one in abilities.modules()}
	return [name for name, *_rest in APPS if name in declared]


@frappe.whitelist()
def people(app: str) -> dict:
	"""Everybody on the workspace and their role in one app, with the roles
	the app offers: None (unless everybody uses it), User, the workspace's
	own, Manager."""
	from onedesk.one import settings

	roles.require()
	_app(app)
	used, managed = next((u, m) for name, _icon, u, m in settings.APPS if name == app)
	own = access.levels_of(app)
	users = frappe.get_all(
		"User",
		filters={"user_type": "System User", "enabled": 1, "name": ["not in", settings.NOT_PEOPLE]},
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
		limit=500,
	)
	held = settings._held([one.name for one in users])
	return {
		"levels": settings._levels(app, {app: own}),
		"people": [
			{
				"user": one.name,
				"name": one.full_name or one.name,
				"image": one.user_image,
				"level": settings.app_level(app, held.get(one.name, set()), used, managed, own),
			}
			for one in users
		],
	}


@frappe.whitelist(methods=["POST"])
def put(app: str, user: str, level: str) -> str:
	"""One person's role in one app, as People sets it; a person on a
	profile that says otherwise comes off it."""
	from onedesk.one import settings

	_app(app)
	doc = settings._one_of_the_people(user)
	admin = int(roles.ADMINISTRATOR in {one.role for one in doc.roles})
	settings._set_access(doc, {app: level}, admin)
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
	what: each of the module's shares that carries one of its abilities."""
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
	the share away (abilities.grant)."""
	roles.require()
	_app(app)
	return abilities.grant(app, record, user, list(frappe.parse_json(keys) or []))
