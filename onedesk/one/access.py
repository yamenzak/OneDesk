"""Access: who sees and does what, past the app levels People sets.
docs/DESK-COVERAGE.md, P2.

People gives each person None, User or Manager on each app that is somebody's
job (one/settings.py APPS), and those are erpnext's own roles. Access adds four
things, each frappe's own:

- **Levels.** A Role the workspace makes for one app (`Role.one_app`), between
  its User and its Manager. A person at a level holds the app's User roles and
  the level, and the level carries only what it adds, as Custom DocPerm rows:
  on a kind of record the app's own roles work with, and never a right none of
  them has there, so a level cannot reach past the app's Manager, another app
  or frappe's own records.
- **Record access.** frappe's User Permission: a person sees only the records
  of a territory, a department or a customer group they are given.
- **Profiles.** frappe's Role Profile, a named set of app levels, applied
  through settings._set_access rather than by frappe's own sync, which would
  take away roles other parts of One give (HR's Employee). `User.one_profile`
  remembers whose profile it is, and a profile changed is applied again to
  everybody on it.
- **Groups.** frappe's User Group, which frappe's assign dialog already takes.

Writing Custom DocPerm copies a kind's standard permissions first, as frappe's
Role Permissions Manager does, after which an app update to that kind's
standard permissions no longer reaches it.
"""

import frappe
from frappe import _
from frappe.permissions import setup_custom_perms

from onedesk.one import roles
from onedesk.one.customize import REFUSED_MODULES

#: The rights a level may add, as the level page offers them.
RIGHTS = ("read", "write", "create", "delete", "submit", "cancel", "export")

#: How each right is said on screen.
SAID = {
	"read": "Read",
	"write": "Edit",
	"create": "Create",
	"delete": "Delete",
	"submit": "Submit",
	"cancel": "Cancel",
	"export": "Export",
}


def _apps() -> dict:
	"""{app: (used, managed)}, from People's own list."""
	from onedesk.one.settings import APPS

	return {name: (tuple(used), tuple(managed)) for name, _icon, used, managed in APPS}


def levels_of(app: str) -> list[str]:
	"""The workspace's own levels of one app, by name."""
	return frappe.get_all("Role", filters={"one_app": app, "disabled": 0}, pluck="name", order_by="name asc")


def all_levels() -> dict:
	"""{app: [level, ...]} for every app, the empty ones too."""
	said = {app: [] for app in _apps()}
	for row in frappe.get_all(
		"Role",
		filters={"one_app": ["is", "set"], "disabled": 0},
		fields=["name", "one_app"],
		order_by="name asc",
	):
		said.setdefault(row.one_app, []).append(row.name)
	return said


def _rights(doctype: str, held: set) -> set:
	"""What the given roles may do on a kind of record, at the first level, as
	frappe reads it (Custom DocPerm where the kind has any)."""
	return {
		right
		for perm in frappe.get_meta(doctype).permissions
		if perm.role in held and not (perm.permlevel or 0) and not perm.if_owner
		for right in RIGHTS
		if perm.get(right)
	}


def kinds(app: str) -> dict:
	"""{doctype: the most a level of the app may do there}: every kind of
	record the app's own roles may read, and what its User and Manager may do
	on it between them."""
	used, managed = _apps()[app]
	held = set(used) | set(managed)
	parents = set(
		frappe.get_all("DocPerm", filters={"role": ["in", list(held)], "permlevel": 0}, pluck="parent")
	)
	parents |= set(
		frappe.get_all("Custom DocPerm", filters={"role": ["in", list(held)], "permlevel": 0}, pluck="parent")
	)
	said = {}
	for doctype in sorted(parents):
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		if meta.istable or meta.module in REFUSED_MODULES:
			continue
		most = _rights(doctype, held)
		if "read" in most:
			said[doctype] = most
	return said


def app_of(level: str) -> str:
	app = frappe.db.get_value("Role", level, "one_app")
	if not app or app not in _apps():
		frappe.throw(_("{0} is not one of the workspace's levels.").format(level))
	return app


def level(name: str) -> dict:
	"""One level: its app, what it adds on each kind of record, and who is at it."""
	roles.require()
	app = app_of(name)
	used, _managed = _apps()[app]
	rows = []
	for perm in frappe.get_all(
		"Custom DocPerm",
		filters={"role": name, "permlevel": 0},
		fields=["parent", *RIGHTS],
		order_by="parent asc",
	):
		rows.append({"doctype": perm.parent, **{right: perm.get(right) or 0 for right in RIGHTS}})
	return {
		"name": name,
		"app": app,
		"rows": rows,
		"people": held_by(name),
		"user_has": {row["doctype"]: sorted(_rights(row["doctype"], set(used))) for row in rows},
	}


def held_by(level: str) -> list[str]:
	return frappe.get_all(
		"Has Role",
		filters={"role": level, "parenttype": "User", "parent": ["not in", ("Administrator", "Guest")]},
		pluck="parent",
	)


def save_level(name: str | None, app: str, title: str, rows: list[dict]) -> str:
	"""A level made or changed: `rows` are {doctype, right: 0/1, ...}, the
	whole of what it adds. Each right is one the app's own roles have on that
	kind; anything past them is refused."""
	roles.require()
	if app not in _apps():
		frappe.throw(_("That cannot be set."))
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the level a name."))
	allowed = kinds(app)
	wanted = {}
	for row in rows or []:
		doctype = row.get("doctype")
		if not doctype:
			continue
		if doctype not in allowed:
			frappe.throw(_("{0} is not a kind of record {1} works with.").format(_(doctype), app))
		chosen = {right for right in RIGHTS if frappe.utils.cint(row.get(right))}
		past = chosen - allowed[doctype]
		if past:
			frappe.throw(
				_("{0}'s own roles may not {1} a {2}, so a level of it may not either.").format(
					app, ", ".join(_(SAID[one]).lower() for one in sorted(past, key=RIGHTS.index)), _(doctype)
				)
			)
		if chosen:
			wanted[doctype] = chosen | ({"read"} if chosen else set())
	if name:
		if app_of(name) != app:
			frappe.throw(_("A level stays with its app."))
		if title != name:
			frappe.rename_doc("Role", name, title, force=True)
			name = title
	else:
		if frappe.db.exists("Role", title):
			frappe.throw(_("There is already a role called {0}.").format(title))
		frappe.get_doc(
			{"doctype": "Role", "role_name": title, "desk_access": 1, "is_custom": 1, "one_app": app}
		).insert(ignore_permissions=True)
		name = title
	had = {row["doctype"]: {r for r in RIGHTS if row.get(r)} for row in level(name)["rows"]}
	_write(name, wanted)
	if had != wanted:
		for user in held_by(name):
			_told(user, _("what the level {0} adds in {1}").format(name, app))
	return name


def _write(level: str, wanted: dict) -> None:
	"""The level's Custom DocPerm rows made to say exactly `wanted`."""
	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

	had = frappe.get_all("Custom DocPerm", filters={"role": level, "permlevel": 0}, fields=["name", "parent"])
	touched = {row.parent for row in had} | set(wanted)
	for row in had:
		if row.parent not in wanted:
			frappe.delete_doc("Custom DocPerm", row.name, ignore_permissions=True, force=True)
	for doctype, rights in wanted.items():
		setup_custom_perms(doctype)
		name = frappe.db.get_value(
			"Custom DocPerm", {"parent": doctype, "role": level, "permlevel": 0, "if_owner": 0}
		)
		doc = (
			frappe.get_doc("Custom DocPerm", name)
			if name
			else frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": doctype,
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": level,
					"permlevel": 0,
				}
			)
		)
		for right in RIGHTS:
			doc.set(right, 1 if right in rights else 0)
		doc.save(ignore_permissions=True)
	for doctype in touched:
		validate_permissions_for_doctype(doctype, alert=False)
		frappe.clear_cache(doctype=doctype)


def delete_level(name: str) -> None:
	roles.require()
	app_of(name)
	people = held_by(name)
	if people:
		frappe.throw(_("{0} people are at this level. Move them to another first.").format(len(people)))
	_write(name, {})
	frappe.delete_doc("Role", name, ignore_permissions=True, force=True)


def for_doctype(doctype: str) -> list[dict]:
	"""What each app's levels may do on one kind of record, for the record's
	Settings > Access: User, the workspace's own levels, Manager."""
	roles.require()
	said = []
	for app, (used, managed) in _apps().items():
		user = _rights(doctype, set(used))
		manager = _rights(doctype, set(used) | set(managed))
		if not manager:
			continue
		rows = [{"level": "User", "rights": sorted(user, key=RIGHTS.index), "own": 0}]
		for one in levels_of(app):
			rows.append(
				{"level": one, "rights": sorted(user | _rights(doctype, {one}), key=RIGHTS.index), "own": 1}
			)
		rows.append({"level": "Manager", "rights": sorted(manager, key=RIGHTS.index), "own": 0})
		said.append({"app": app, "rows": rows})
	return said


@frappe.whitelist(methods=["POST"])
def new_level(app: str, title: str) -> str:
	"""A level of one app that adds nothing yet, to fill in on its page."""
	return save_level(None, app, title, [])


@frappe.whitelist(methods=["POST"])
def remove_level(name: str) -> None:
	delete_level(name)


@frappe.whitelist()
def doctype_levels(doctype: str) -> list[dict]:
	"""For a record's Settings > Access."""
	return for_doctype(doctype)


# ------------------------------------------------------------------ record access

#: The kinds of record a person can be held to, as frappe's User Permission
#: holds them: everything linked to one of these is then theirs only.
RECORD_KINDS = (
	"Territory",
	"Customer Group",
	"Customer",
	"Supplier",
	"Department",
	"Branch",
	"Project",
	"Warehouse",
)


def _person(user: str) -> None:
	from onedesk.one.settings import NOT_PEOPLE

	roles.require()
	if user in NOT_PEOPLE or frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("That cannot be set."))


def record_access(user: str) -> list[dict]:
	"""What a person is held to, of the kinds Access holds people to: each
	record, and where it applies. What HR and erpnext hold them to themselves
	(their own employee record) is theirs, and not shown."""
	return frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": ["in", RECORD_KINDS]},
		fields=["name", "allow", "for_value", "apply_to_all_doctypes", "applicable_for"],
		order_by="allow asc, for_value asc",
	)


def kinds_held() -> list[dict]:
	"""What the add window offers: the kinds this workspace has."""
	return [{"value": one, "label": _(one)} for one in RECORD_KINDS if frappe.db.exists("DocType", one)]


@frappe.whitelist(methods=["POST"])
def hold(user: str, allow: str, for_value: str, applicable_for: str | None = None) -> None:
	"""Hold a person to one record of a kind: they see only what is linked to
	it, everywhere or on one kind of record. They are told."""
	_person(user)
	if allow not in RECORD_KINDS:
		frappe.throw(
			_(
				"A person can be held to a territory, a customer group, a customer, a supplier, a department, a branch, a project or a warehouse."
			)
		)
	if not frappe.db.exists(allow, for_value):
		frappe.throw(_("There is no {0} {1}.").format(_(allow), for_value))
	if applicable_for and (
		not frappe.db.exists("DocType", applicable_for)
		or frappe.get_meta(applicable_for).module in REFUSED_MODULES
	):
		frappe.throw(_("That cannot be set."))
	if frappe.db.exists(
		"User Permission",
		{"user": user, "allow": allow, "for_value": for_value, "applicable_for": applicable_for or None},
	):
		return
	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": allow,
			"for_value": for_value,
			"apply_to_all_doctypes": 0 if applicable_for else 1,
			"applicable_for": applicable_for or None,
		}
	).insert(ignore_permissions=True)
	_told(user, _("only the records of {0} {1}").format(_(allow), for_value))


@frappe.whitelist(methods=["POST"])
def let_go(name: str) -> None:
	"""One of a person's holds taken away."""
	doc = frappe.get_doc("User Permission", name)
	_person(doc.user)
	if doc.allow not in RECORD_KINDS:
		frappe.throw(_("That cannot be set."))
	doc.delete(ignore_permissions=True)
	_told(doc.user, _("no longer only the records of {0} {1}").format(_(doc.allow), doc.for_value))


def _told(user: str, change: str) -> None:
	from onedesk.one import notify

	notify.notify("Access Changed", user, link="/desk", changes=change, by=frappe.utils.get_fullname())


# ------------------------------------------------------------------ profiles


def profiles() -> list[dict]:
	"""Every profile, the levels it sets, and how many people are on it."""
	said = []
	own = all_levels()
	for name in frappe.get_all("Role Profile", pluck="name", order_by="name asc"):
		held = set(
			frappe.get_all("Has Role", filters={"parent": name, "parenttype": "Role Profile"}, pluck="role")
		)
		said.append(
			{
				"name": name,
				"levels": _levels_in(held, own),
				"people": frappe.db.count("User", {"one_profile": name}),
			}
		)
	return said


def _levels_in(held: set, own: dict) -> dict:
	from onedesk.one.settings import level_of

	return {app: level_of(held, used, managed, own.get(app, ())) for app, (used, managed) in _apps().items()}


def profile(name: str) -> dict:
	roles.require()
	held = set(
		frappe.get_all("Has Role", filters={"parent": name, "parenttype": "Role Profile"}, pluck="role")
	)
	return {
		"name": name,
		"levels": _levels_in(held, all_levels()),
		"people": frappe.get_all("User", filters={"one_profile": name}, fields=["name", "full_name"]),
	}


def save_profile(name: str | None, title: str, levels: dict) -> str:
	"""A profile made or changed, as the levels it sets, and set again on
	everybody on it, keeping what else they hold."""
	from onedesk.one.settings import LEVELS, roles_for

	roles.require()
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the profile a name."))
	own = all_levels()
	wanted = {"Desk User"}
	for app, (used, managed) in _apps().items():
		level = levels.get(app) or "None"
		if level not in LEVELS and level not in own.get(app, ()):
			frappe.throw(_("That cannot be set."))
		wanted |= roles_for(level, used, managed, own.get(app, ()))
	if name and title != name:
		frappe.rename_doc("Role Profile", name, title, force=True)
		frappe.db.set_value("Role Profile", title, "role_profile", title, update_modified=False)
		frappe.db.set_value("User", {"one_profile": name}, "one_profile", title, update_modified=False)
		name = title
	if not name:
		if frappe.db.exists("Role Profile", title):
			frappe.throw(_("There is already a profile called {0}.").format(title))
		doc = frappe.new_doc("Role Profile")
		doc.role_profile = title
	else:
		doc = frappe.get_doc("Role Profile", name)
	doc.set("roles", [{"role": one} for one in sorted(wanted) if frappe.db.exists("Role", one)])
	doc.save(ignore_permissions=True)
	# frappe queues its own sync of the profile's members on every save and
	# locks the profile until a worker runs it. One's profiles have none of
	# frappe's members (they are applied here), so the lock only refuses the
	# next save.
	doc.unlock()
	for user in frappe.get_all("User", filters={"one_profile": doc.name}, pluck="name"):
		put_on(user, doc.name)
	return doc.name


def put_on(user: str, name: str | None) -> None:
	"""A person set to a profile's levels, or taken off one. Their
	administrator switch and every role outside the apps are kept."""
	from onedesk.one.settings import _set_access

	doc = frappe.get_doc("User", user)
	if name:
		levels = profile(name)["levels"]
		_set_access(doc, levels, 1 if roles.ADMINISTRATOR in {one.role for one in doc.roles} else 0)
	frappe.db.set_value("User", user, "one_profile", name or None, update_modified=False)


@frappe.whitelist(methods=["POST"])
def new_profile(title: str) -> str:
	return save_profile(None, title, {})


@frappe.whitelist(methods=["POST"])
def remove_profile(name: str) -> None:
	roles.require()
	frappe.db.set_value("User", {"one_profile": name}, "one_profile", None, update_modified=False)
	frappe.delete_doc("Role Profile", name, ignore_permissions=True, force=True)


# ------------------------------------------------------------------ groups


def groups() -> list[dict]:
	return [
		{
			"name": name,
			"members": frappe.db.count("User Group Member", {"parent": name, "parenttype": "User Group"}),
		}
		for name in frappe.get_all("User Group", pluck="name", order_by="name asc")
	]


def save_group(name: str | None, title: str, members: list[str]) -> str:
	"""A group made or changed: its name and who is in it, people of the
	workspace only."""
	from onedesk.one.settings import NOT_PEOPLE

	roles.require()
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the group a name."))
	people = set(
		frappe.get_all(
			"User", filters={"user_type": "System User", "name": ["not in", NOT_PEOPLE]}, pluck="name"
		)
	)
	if not members:
		frappe.throw(_("A group needs somebody in it."))
	if set(members) - people:
		frappe.throw(_("A group holds people of the workspace."))
	if name and title != name:
		frappe.rename_doc("User Group", name, title, force=True)
		name = title
	if name:
		doc = frappe.get_doc("User Group", name)
	else:
		if frappe.db.exists("User Group", title):
			frappe.throw(_("There is already a group called {0}.").format(title))
		doc = frappe.new_doc("User Group")
		doc.name = title
	doc.set("user_group_members", [{"user": one} for one in dict.fromkeys(members)])
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["POST"])
def new_group(title: str, members: str | list) -> str:
	"""A group, with the people it starts with: frappe's group has at least one."""
	members = frappe.parse_json(members) if isinstance(members, str) else members
	return save_group(
		None, title, [one.get("user") if isinstance(one, dict) else one for one in members or []]
	)


@frappe.whitelist(methods=["POST"])
def remove_group(name: str) -> None:
	roles.require()
	frappe.delete_doc("User Group", name, ignore_permissions=True, force=True)
