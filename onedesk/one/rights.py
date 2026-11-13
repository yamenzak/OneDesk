"""What a role may do in a module beyond its records (docs/ROLES.md).

A module declares its abilities in `<module>/access.py`, named by the
`one_abilities` hook. Each is one of frappe's Permission Types on a doctype,
or two for one with a scope (their own, or every one). A role holds them on
Custom DocPerm, a person holds them on one record through a DocShare, and
frappe.has_permission answers both.
"""

import frappe
from frappe import _

from onedesk.one import roles

SCOPES = ("none", "own", "all")


def modules() -> list:
	"""Every module that declares abilities, as its `access` module."""
	return [frappe.get_module(path) for path in frappe.get_hooks("one_abilities")]


def of_app(app: str):
	"""The `access` module of one app, or None."""
	return next((one for one in modules() if one.APP == app), None)


def ability(app: str, key: str) -> dict:
	declared = of_app(app)
	found = next((one for one in (declared.ABILITIES if declared else []) if one["key"] == key), None)
	if not found:
		frappe.throw(_("{0} has no such ability.").format(app))
	return found


def ptypes(app: str) -> list[str]:
	"""Every permission type an app's abilities stand on."""
	declared = of_app(app)
	return [one[side] for one in (declared.ABILITIES if declared else []) for side in ("all", "own") if one.get(side)]


def doctypes() -> set[str]:
	"""The doctypes abilities live on, which the record matrix leaves out."""
	return {one.DOCTYPE for one in modules()}


def _row(doctype: str, role: str) -> dict | None:
	return frappe.db.get_value(
		"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}, "*", as_dict=True
	)


def of(app: str, role: str) -> dict:
	"""What a role holds of an app's abilities: a scope ("none", "own",
	"all") for one with a scope, 0 or 1 for a switch."""
	declared = of_app(app)
	if not declared:
		return {}
	row = _row(declared.DOCTYPE, role) or {}
	said = {}
	for one in declared.ABILITIES:
		if one["kind"] == "switch":
			said[one["key"]] = int(bool(row.get(one["all"])))
		else:
			said[one["key"]] = "all" if row.get(one["all"]) else "own" if row.get(one["own"]) else "none"
	return said


def save(app: str, role: str, values: dict) -> bool:
	"""A role given exactly `values` of an app's abilities, on its Custom
	DocPerm row for the doctype they live on. Frappe wants a basic right on
	every row, so a new row carries Select, and not Read, which Custom DocPerm
	would otherwise default to. True when anything changed."""
	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype
	from frappe.permissions import setup_custom_perms

	declared = of_app(app)
	if not declared:
		return False
	wanted = {}
	for one in declared.ABILITIES:
		value = values.get(one["key"], 0 if one["kind"] == "switch" else "none")
		if one["kind"] == "switch":
			wanted[one["all"]] = int(bool(frappe.utils.cint(value)))
		else:
			if value not in SCOPES:
				frappe.throw(_("That cannot be set."))
			wanted[one["all"]] = int(value == "all")
			wanted[one["own"]] = int(value == "own")
	setup_custom_perms(declared.DOCTYPE)
	row = _row(declared.DOCTYPE, role)
	if row and all(int(row.get(ptype) or 0) == on for ptype, on in wanted.items()):
		return False
	if not row and not any(wanted.values()):
		return False
	where = {"parent": declared.DOCTYPE, "role": role, "permlevel": 0, "if_owner": 0}
	doc = (
		frappe.get_doc("Custom DocPerm", row.name)
		if row
		else frappe.get_doc({"doctype": "Custom DocPerm", "parenttype": "DocType", "parentfield": "permissions", **where, "select": 1, "read": 0})
	)
	doc.update(wanted)
	doc.save(ignore_permissions=True)
	validate_permissions_for_doctype(declared.DOCTYPE, alert=False)
	frappe.clear_cache(doctype=declared.DOCTYPE)
	return True


def may(doctype: str, ptype: str, name: str | None = None, user: str | None = None) -> bool:
	"""Whether somebody may do one thing: on one record when `name` is given,
	through their roles or a share of it; on every record otherwise, through
	their roles alone. A workspace administrator may do everything."""
	user = user or frappe.session.user
	if user == "Administrator" or roles.administers(user):
		return True
	if name:
		return bool(frappe.has_permission(doctype, ptype, doc=name, user=user))
	return held(doctype, ptype, user)


def can(doctype: str, ptype: str = "read") -> bool:
	"""Whether the reader may `ptype` some record of `doctype`, as frappe
	answers it (roles, user permissions, shares), with no administrator's
	shortcut: what a Home, a story or a tab shows only to who may read it."""
	return bool(frappe.has_permission(doctype, ptype))


def held(doctype: str, ptype: str, user: str | None = None) -> bool:
	"""Whether somebody's roles give them `ptype` on every record of `doctype`,
	shares aside."""
	from frappe.permissions import get_role_permissions

	user = user or frappe.session.user
	if user == "Administrator" or roles.administers(user):
		return True
	return bool(get_role_permissions(frappe.get_meta(doctype), user=user).get(ptype))


def people_with(doctype: str, ptype: str, name: str | None = None) -> list[str]:
	"""Everybody turned on who may do `ptype`: on one record through a share
	of it too, else on every record. Who hears that something waits for
	them."""
	held_by = {
		row.role
		for row in frappe.get_all(
			"Custom DocPerm", filters={"parent": doctype, ptype: 1, "permlevel": 0}, fields=["role"]
		)
	} | {roles.ADMINISTRATOR}
	people = set(
		frappe.get_all(
			"Has Role",
			filters={"role": ["in", list(held_by)], "parenttype": "User", "parent": ["not in", ("Administrator", "Guest")]},
			pluck="parent",
		)
	)
	if name:
		people |= set(
			frappe.get_all("DocShare", filters={"share_doctype": doctype, "share_name": name, ptype: 1}, pluck="user")
		)
	return frappe.get_all("User", filters={"name": ["in", list(people) or [""]], "enabled": 1}, pluck="name")


def grants(app: str, name: str) -> dict:
	"""{user: [ability, ...]} that people were given on one record."""
	declared = of_app(app)
	keys = {one["all"]: one["key"] for one in declared.ABILITIES if one["key"] in declared.SHARED}
	said = {}
	for row in frappe.get_all(
		"DocShare",
		filters={"share_doctype": declared.DOCTYPE, "share_name": name, "everyone": 0},
		fields=["user", *keys],
	):
		said[row.user] = [key for ptype, key in keys.items() if row.get(ptype)]
	return said


def grant(app: str, name: str, user: str, keys: list[str]) -> list[str]:
	"""Somebody given exactly `keys` of an app's abilities on one record, as a
	share of it; with none, the share goes."""
	import frappe.share

	declared = of_app(app)
	allowed = {one["key"]: one["all"] for one in declared.ABILITIES if one["key"] in declared.SHARED}
	if any(key not in allowed for key in keys):
		frappe.throw(_("That cannot be set."))
	if not keys:
		frappe.share.remove(declared.DOCTYPE, name, user, flags={"ignore_share_permission": True, "ignore_permissions": True})
		return []
	frappe.share.add_docshare(
		declared.DOCTYPE,
		name,
		user,
		read=1,
		flags={"ignore_share_permission": True},
		**{ptype: int(key in keys) for key, ptype in allowed.items()},
	)
	return list(keys)


def share(doctype: str, name: str, user: str, *, write: int = 0, share: int = 0) -> None:
	"""Somebody given frappe's own read, and write or share if said, on one
	record, as a share frappe answers: the grant of a module whose people
	are given those bits alone, such as a file, a folder or a library in
	OneCloud."""
	import frappe.share

	frappe.share.add_docshare(doctype, name, user, read=1, write=write, share=share, flags={"ignore_share_permission": True})


def unshare(doctype: str, name: str, user: str, *, flags: dict) -> None:
	"""Somebody's share of one record taken away, with the flags its caller
	has already checked for."""
	import frappe.share

	frappe.share.remove(doctype, name, user, flags=flags)


def settle(*_args) -> None:
	"""after_migrate: each module's own roles, made from its `access.py`
	(its DEFAULTS name them, docs/READY.md mechanism 7), and given their
	default abilities once. A role that has a row on the doctype already
	keeps what the workspace made of it."""
	for declared in modules():
		for role, values in declared.DEFAULTS.items():
			made(role, declared.APP if role == getattr(declared, "EVERYONE", None) else None)
			row = _row(declared.DOCTYPE, role)
			if not row:
				save(declared.APP, role, values)
			else:
				_arrived(declared, role, values, row)


def made(role: str, app: str | None = None) -> None:
	"""A module's role, made once. Also before a module's doctypes are synced,
	when their permissions name a role that has to be there first."""
	if frappe.db.exists("Role", role):
		return
	values = {"doctype": "Role", "role_name": role, "desk_access": 1, "is_custom": 0}
	if app and frappe.db.has_column("Role", "one_app"):
		values["one_app"] = app
	frappe.get_doc(values).insert(ignore_permissions=True)


SETTLED = "one_abilities_settled_{}_{}"


def _arrived(declared, role: str, values: dict, row: dict) -> None:
	"""An ability an update brings is given to a role with its default, once,
	when the role's row is older than the ability; what the workspace makes
	of it afterwards is kept, as everything else is."""
	import json

	told = SETTLED.format(frappe.scrub(declared.APP), frappe.scrub(role))
	settled = set(json.loads(frappe.db.get_default(told) or "[]"))
	given = {}
	for one in declared.ABILITIES:
		if one["key"] in settled:
			continue
		settled.add(one["key"])
		since = frappe.db.get_value("Permission Type", {"doc_type": declared.DOCTYPE, "perm_type": one["all"]}, "creation")
		if since and since > row.creation and values.get(one["key"]) not in (None, 0, "none"):
			given[one["key"]] = values[one["key"]]
	if given:
		save(declared.APP, role, {**of(declared.APP, role), **given})
	frappe.db.set_default(told, json.dumps(sorted(settled)))


def defaults_table(app: str) -> str:
	"""What each of a module's roles starts with, as a Markdown table for its
	Help (`{roles}` on a page, one/versions.py), so the page can't say other
	than the module ships. In English, as Help is."""
	declared = of_app(app)
	if not declared:
		return ""
	was = getattr(frappe.local, "lang", None)
	frappe.local.lang = "en"
	try:
		roles = list(declared.DEFAULTS)
		# As the Roles matrix names them: the role everyone holds is User, the
		# module's other is Manager; ERPNext's roles go by their own names.
		everyone = getattr(declared, "EVERYONE", None)
		named = [str(_(role) if not everyone else _("User") if role == everyone else _("Manager")) for role in roles]
		rows = [f"| {_('Ability')} | " + " | ".join(named) + " |", "| --- |" + " --- |" * len(roles)]
		for one in declared.ABILITIES:
			cells = []
			for role in roles:
				value = declared.DEFAULTS[role].get(one["key"], 0 if one["kind"] == "switch" else "none")
				if one["kind"] == "switch":
					cells.append(str(_("On") if value else _("Off")))
				else:
					label = one.get(value) if value == "none" and one.get("none") else declared.SCOPE_LABELS[value]
					cells.append(str(label))
			rows.append(f"| **{one['label']}** | " + " | ".join(cells) + " |")
		return "\n".join(rows)
	finally:
		frappe.local.lang = was


def everyone(*_args) -> None:
	"""after_migrate: every person holds the User role of each module
	everybody uses, however they were made."""
	for declared in modules():
		role = getattr(declared, "EVERYONE", None)
		if not role or not frappe.db.exists("Role", role):
			continue
		has = set(frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"))
		for user in frappe.get_all(
			"User", filters={"user_type": "System User", "name": ["not in", ("Administrator", "Guest")]}, pluck="name"
		):
			if user not in has:
				doc = frappe.get_doc("User", user)
				doc.flags.ignore_permissions = True
				doc.add_roles(role)


def always() -> set[str]:
	"""The apps everybody uses, which have no None."""
	return {declared.APP for declared in modules() if getattr(declared, "EVERYONE", None)}
