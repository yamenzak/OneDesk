"""The workspace's people and what each may use: the apps, the level a
person holds in each (None, User, a level of the workspace's own, or
Manager), who counts as a person at all, and the seats they take. People
and AccessCenter set it; everything else reads it."""

import frappe
from frappe import _, _lt

from onedesk.one import registry, roles, tell
from onedesk.one.access import all_levels, companion

APPS = [(app.name, app.mark, app.roles.user, app.roles.manager) for app in registry.apps() if app.roles.user]
"""The apps a person is given a level in, with the roles each level means,
from each app's manifest (onedesk/one/registry)."""


def with_roles() -> list[tuple]:
	"""People's apps, then each module everybody uses that has a role above
	its User role (`EVERYONE`, one/rights.py), such as One and OneAI. Its User
	role is everybody's, so its only level to give is Manager, given in
	AccessCenter rather than on People."""
	from onedesk.one import rights

	said = list(APPS)
	ours = {name for name, *_rest in APPS}
	for declared in rights.modules():
		everyone = getattr(declared, "EVERYONE", None)
		managed = tuple(one for one in getattr(declared, "DEFAULTS", {}) if one != everyone)
		if everyone and managed and declared.APP not in ours:
			said.append((declared.APP, declared.APP.lower(), (everyone,), managed))
	return said


# Apps everybody uses: no None, and User is not worth saying on the list
# of people (one/rights.py `always`).
ALWAYS = (registry.name("one_mail"),)


APP_SAID = {
	**{app.name: _lt(app.line) for app in registry.apps() if app.line},
	"Reading": _lt("Mail and files read as they arrive, and filed on their record."),
}
"""What each app is for, in one line, from its manifest; Reading is OneAI's
own switch (one/apps.py) until P8.3 retires it."""


LEVELS = ("None", "User", "Manager")


NOT_PEOPLE = ("Administrator", "Guest", "oneai@one.invalid")


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


def app_level(app: str, held: set, used: tuple, managed: tuple, levels: tuple | list = ()) -> str:
	"""level_of, where an app everybody uses is at least User."""
	said = level_of(held, used, managed, levels)
	return "User" if said == "None" and app in ALWAYS else said


def listed(held: set, own: dict) -> dict:
	"""A person's role in each app, as the list of people shows it: User in
	an app everybody uses goes without saying."""
	said = {}
	for name, _icon, used, managed in APPS:
		level = app_level(name, held, used, managed, own.get(name, ()))
		if not (name in ALWAYS and level == "User"):
			said[name] = level
	return said


def levels_of(app: str, own: dict) -> list[dict]:
	"""What People offers for one app: None, User, the workspace's own roles
	between, and Manager. An app everybody uses has no None."""
	return [{"value": one, "label": _(one)} for one in ("None", "User") if not (one == "None" and app in ALWAYS)] + [
		{"value": one, "label": one} for one in own.get(app, [])
	] + [{"value": "Manager", "label": _("Manager")}]


def roles_held(users: list) -> dict:
	held = {}
	for row in frappe.get_all("Has Role", filters={"parenttype": "User", "parent": ["in", users or [""]]}, fields=["parent", "role"], limit=0):
		held.setdefault(row.parent, set()).add(row.role)
	return held


def one_of_the_people(user: str):
	roles.require()
	if user in NOT_PEOPLE or frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("That cannot be set."))
	return frappe.get_doc("User", user)


def set_access(doc, access: dict, admin: int, told: bool = True) -> None:
	"""What a person may use, as frappe's roles, in one save. They are told
	what changed, and every administrator is told of a new administrator. An
	app everybody uses is never None, and everybody keeps each module's own
	User role (one/rights.py `everyone`), whatever their level."""
	from onedesk.one import rights

	own = all_levels()
	if any(level not in LEVELS and level not in own.get(name, ()) for name, level in access.items()):
		frappe.throw(_("That cannot be set."))
	before = {one.role for one in doc.roles}
	ours = {roles.ADMINISTRATOR}
	wanted = set()
	for name, _icon, used, managed in with_roles():
		levels = own.get(name, ())
		alone = (companion(name),)
		ours |= set(used) | set(managed) | set(levels) | set(alone)
		level = access.get(name) or level_of(before, used, managed, levels)
		if name in ALWAYS and level == "None":
			level = "User"
		wanted |= roles_for(level, used, managed, levels, alone)
	wanted |= {role for declared in rights.modules() if (role := getattr(declared, "EVERYONE", None))}
	if admin:
		wanted.add(roles.ADMINISTRATOR)
	elif roles.ADMINISTRATOR in before:
		not_the_last_administrator(doc.name)
	after = (before - ours) | {role for role in wanted | {"Desk User"} if frappe.db.exists("Role", role)}
	if after != before:
		doc.set("roles", [{"role": role} for role in sorted(after)])
		doc.save(ignore_permissions=True)
		if told:
			told_of_access(doc, before, after)


def not_the_last_administrator(user: str) -> None:
	others = frappe.get_all("Has Role", filters={"role": roles.ADMINISTRATOR, "parenttype": "User", "parent": ["not in", (user, *NOT_PEOPLE)]}, pluck="parent")
	if not [one for one in others if frappe.db.get_value("User", one, "enabled")]:
		frappe.throw(_("A workspace needs at least one administrator."))


def told_of_access(doc, before: set, after: set) -> None:
	"""The person hears what they may now use; every other administrator
	hears of a new administrator, always by mail (one/notifications.py)."""
	said = []
	own = all_levels()
	for name, _icon, used, managed in with_roles():
		levels = own.get(name, ())
		was, now = app_level(name, before, used, managed, levels), app_level(name, after, used, managed, levels)
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


def apps_said(access: dict) -> list[str]:
	said = {"User": _("{0} as a user"), "Manager": _("{0} as a manager")}
	return [
		said[level].format(name) if level in said else _("{0} as {1}").format(name, level)
		for name, level in access.items()
		if level and level != "None"
	]


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
