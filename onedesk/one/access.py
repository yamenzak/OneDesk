"""Access: who sees and does what, past the app levels People sets.

Four things on top of People's None, User and Manager, each frappe's own:
levels, record access, profiles and groups.
"""

import frappe
from frappe import _
from frappe.permissions import setup_custom_perms

from onedesk.one import roles, tell
from onedesk.one_studio.customize import REFUSED_MODULES

RIGHTS = ("select", "read", "write", "create", "delete", "submit", "cancel", "export")

FOLLOW = ("amend", "report", "import", "print", "email", "share")

ALL_RIGHTS = RIGHTS + FOLLOW

SAID = {
	"select": "Pick",
	"read": "Read",
	"write": "Edit",
	"create": "Create",
	"delete": "Delete",
	"submit": "Submit",
	"cancel": "Cancel",
	"export": "Export",
}

NEEDS = {
	"write": {"read"},
	"create": {"read"},
	"delete": {"read"},
	"submit": {"read", "write"},
	"cancel": {"read", "write", "submit"},
	"amend": {"read", "write", "create", "submit", "cancel"},
	"export": {"read"},
	"report": {"read"},
	"import": {"read", "create"},
	"print": {"read"},
	"email": {"read"},
	"share": {"read"},
}

SUBMITTED = {"submit", "cancel", "amend"}
NOT_SINGLE = {"report", "import", "export"}

BASE = ("User", "Manager")

EVERYONE = ("All", "Desk User", "Guest")


def _apps() -> dict:
	"""{app: (used, managed)}, from People's own list."""
	from onedesk.one.people import APPS

	return {name: (tuple(used), tuple(managed)) for name, _icon, used, managed in APPS}


def _builders() -> dict:
	"""{app: (used, managed)} for every app whose roles AccessCenter builds:
	People's, and the modules everybody uses (people.with_roles)."""
	from onedesk.one.people import with_roles

	return {name: (tuple(used), tuple(managed)) for name, _icon, used, managed in with_roles()}


def companion(app: str) -> str:
	"""The role only an app's plain users hold. It carries what they may do
	and some other level of the app may not, since every level holds the
	app's User roles."""
	return f"{app} User"


def _companion(app: str) -> str:
	"""The companion role, made the first time it is needed and given to
	everybody who is then a plain user of the app."""
	name = companion(app)
	if not frappe.db.exists("Role", name):
		frappe.get_doc(
			{"doctype": "Role", "role_name": name, "desk_access": 1, "is_custom": 1, "one_app": app}
		).insert(ignore_permissions=True)
		for user in people_at(app, "User"):
			doc = frappe.get_doc("User", user)
			doc.flags.ignore_permissions = True
			doc.add_roles(name)
	return name


def levels_of(app: str) -> list[str]:
	"""The workspace's own levels of one app, by name."""
	return frappe.get_all(
		"Role",
		filters={"one_app": app, "disabled": 0, "name": ["!=", companion(app)]},
		pluck="name",
		order_by="name asc",
	)


def all_levels() -> dict:
	"""{app: [level, ...]} for every app, the empty ones too."""
	said = {app: [] for app in _apps()}
	for row in frappe.get_all(
		"Role",
		filters={"one_app": ["is", "set"], "disabled": 0},
		fields=["name", "one_app"],
		order_by="name asc",
	):
		if row.name != companion(row.one_app):
			said.setdefault(row.one_app, []).append(row.name)
	return said


def tiers(app: str) -> list[str]:
	"""Every level of an app, lowest first: User, the workspace's own, Manager."""
	return ["User", *levels_of(app), "Manager"]


def _holds(app: str, tier: str) -> set:
	"""The roles somebody at a level of an app holds."""
	used, managed = _builders()[app]
	if tier == "User":
		return set(used) | {companion(app)}
	if tier == "Manager":
		return set(used) | set(managed)
	return set(used) | {tier}


def _carriers(app: str, tier: str) -> tuple:
	"""The roles a level's own rights are written on, past what every level
	of the app shares, which the app's User roles carry."""
	return {"User": (companion(app),), "Manager": _builders()[app][1]}.get(tier, (tier,))


def _rights(doctype: str, held: set) -> set:
	"""What the given roles may do on a kind of record, at the first level, as
	frappe reads it (Custom DocPerm where the kind has any)."""
	return {
		right
		for perm in frappe.get_meta(doctype).permissions
		if perm.role in held and not (perm.permlevel or 0) and not perm.if_owner
		for right in ALL_RIGHTS
		if perm.get(right)
	}


def _close(doctype: str, rights: set) -> set:
	"""Rights made whole: what each needs added, and what the kind cannot have
	taken off."""
	meta = frappe.get_meta(doctype)
	said = set(rights)
	if not meta.is_submittable:
		said -= SUBMITTED
	if meta.issingle:
		said -= NOT_SINGLE
	for right in list(said):
		said |= NEEDS.get(right, set())
	return said


def _wanted(doctype: str, chosen: set, had: set) -> set:
	"""What a level is to have on a kind: the rights ticked and what they need,
	and frappe's others as they were, or as a new reader gets them, while what
	they need is still there."""
	shown = _close(doctype, chosen & set(RIGHTS))
	follow = had & set(FOLLOW)
	if "read" in shown and "read" not in had:
		follow |= {"report", "print", "email"}
	if "write" in shown and "write" not in had:
		follow.add("share")
	if "cancel" in shown and "cancel" not in had:
		follow.add("amend")
	return _close(doctype, shown | {one for one in follow if NEEDS[one] <= shown})


def kinds(app: str) -> list[str]:
	"""Every kind of record the app's own roles have a rule on, as it shipped
	or as the workspace changed it: what a level of the app may be given."""
	used, managed = _builders()[app]
	held = list(set(used) | set(managed))
	parents = set(frappe.get_all("DocPerm", filters={"role": ["in", held]}, pluck="parent"))
	parents |= set(frappe.get_all("Custom DocPerm", filters={"role": ["in", held]}, pluck="parent"))
	said = []
	for doctype in sorted(parents):
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		if meta.istable or meta.module in REFUSED_MODULES:
			continue
		said.append(doctype)
	return said


def _matrix(app: str, tier: str) -> set:
	"""The kinds a level's record matrix shows: the app's, and any the level
	was given, less those an app's abilities live on (one/rights.py)."""
	from onedesk.one import rights

	return (set(kinds(app)) | _written(_carriers(app, tier))) - rights.doctypes()


def ability_role(app: str, tier: str) -> str:
	"""The role a level's abilities are written on: the app's first User
	role, its first Manager role, or a level of the workspace's own itself.
	Every level holds the User roles, so User's abilities reach them all."""
	used, managed = _builders()[app]
	return {"User": used[0] if used else companion(app), "Manager": managed[0]}.get(tier, tier)


def abilities_of(app: str, tier: str) -> list[dict]:
	"""A level's abilities as its page shows them: each declared ability, what
	the level has of it with User's included, and the least it can be set to
	(User's own) for a level above User."""
	from onedesk.one import rights

	declared = rights.of_app(app)
	if not declared:
		return []
	mine = rights.of(app, ability_role(app, tier))
	base = rights.of(app, ability_role(app, "User")) if tier != "User" else {}
	order = rights.SCOPES
	said = []
	for one in declared.ABILITIES:
		key = one["key"]
		if one["kind"] == "switch":
			value = int(bool(mine.get(key)) or bool(base.get(key)))
			least = int(bool(base.get(key)))
		else:
			value = max(mine.get(key, "none"), base.get(key, "none"), key=order.index)
			least = base.get(key, "none")
		said.append(
			{
				**{name: str(text) if name in ("group", "label", "about", "none") else text for name, text in one.items()},
				"value": value,
				"least": least,
			}
		)
	return said


def save_abilities(app: str, tier: str, values: dict) -> bool:
	"""A level's abilities saved on its role; True when anything changed."""
	from onedesk.one import rights

	if not rights.of_app(app):
		return False
	return rights.save(app, ability_role(app, tier), values)


def _written(roles_: tuple | set) -> set:
	"""Every kind the given roles have a rule of the workspace's own on."""
	return set(frappe.get_all("Custom DocPerm", filters={"role": ["in", list(roles_)]}, pluck="parent"))


def _picks(doctype: str) -> set:
	"""The kinds a new or changed record must name: the links somebody fills in
	and cannot leave empty, on it and on its tables."""
	meta = frappe.get_meta(doctype)
	said = set()
	for one in [meta, *(frappe.get_meta(df.options) for df in meta.get_table_fields())]:
		for df in one.fields:
			if df.fieldtype == "Link" and df.reqd and df.options and not df.hidden and not df.read_only:
				said.add(df.options)
	return {
		one
		for one in said - {doctype}
		if frappe.db.exists("DocType", one)
		and not frappe.get_meta(one).istable
		and frappe.get_meta(one).module not in REFUSED_MODULES
	}


def _rename(tier: str, title: str | None) -> str:
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the role a name."))
	if ":" in title:
		frappe.throw(_("A role's name cannot have a colon in it."))
	if title != tier:
		if frappe.db.exists("Role", title):
			frappe.throw(_("There is already a role called {0}.").format(title))
		from frappe.model.rename_doc import rename_doc

		rename_doc("Role", tier, title, force=True, ignore_permissions=True, show_alert=False)
	return title


def app_of(level: str) -> str:
	app = frappe.db.get_value("Role", level, "one_app")
	if not app or app not in _builders() or level == companion(app):
		frappe.throw(_("{0} is not one of the workspace's roles.").format(level))
	return app


def tier_of(key: str) -> tuple[str, str]:
	"""(app, level) from how a route names a level: `OneCRM:User`, or a level
	of the workspace's own by its name."""
	app, sep, tier = key.partition(":")
	if sep:
		if app not in _builders() or tier not in BASE:
			frappe.throw(_("{0} is not one of the workspace's roles.").format(key))
		return app, tier
	return app_of(key), key


def key_of(app: str, tier: str) -> str:
	return f"{app}:{tier}" if tier in BASE else tier


def people_at(app: str, tier: str) -> list[str]:
	"""Everybody whose level of an app is this one."""
	from onedesk.one.people import NOT_PEOPLE, level_of

	used, managed = _builders()[app]
	own = levels_of(app)
	held = {}
	for row in frappe.get_all(
		"Has Role",
		filters={
			"role": ["in", list(set(used) | set(managed) | set(own))],
			"parenttype": "User",
			"parent": ["not in", NOT_PEOPLE],
		},
		fields=["parent", "role"],
	):
		held.setdefault(row.parent, set()).add(row.role)
	return sorted(user for user, roles_ in held.items() if level_of(roles_, used, managed, own) == tier)


def level(key: str) -> dict:
	"""One level: its app, what it may do on each kind of record, and who is at it."""
	roles.require()
	app, tier = tier_of(key)
	held = _holds(app, tier)
	rows = []
	for doctype in sorted(_matrix(app, tier)):
		has = _rights(doctype, held)
		if has & set(RIGHTS):
			rows.append({"doctype": doctype, **{right: int(right in has) for right in RIGHTS}})
	return {
		"key": key_of(app, tier),
		"name": tier,
		"app": app,
		"own": int(tier not in BASE),
		"rows": rows,
		"abilities": abilities_of(app, tier),
		"people": people_at(app, tier),
	}


def save_level(key: str, title: str | None, rows: list[dict], abilities: dict | None = None) -> str:
	"""A level's name, for one of the workspace's own, and everything it may do:
	`rows` are {doctype, right: 0/1, ...}, one per kind. What a right needs
	comes with it, and a kind somebody at the level may make or change gives
	them at least the kinds it must name to pick from."""
	roles.require()
	app, tier = tier_of(key)
	if tier not in BASE:
		tier = _rename(tier, title)
	held = _holds(app, tier)
	allowed = _matrix(app, tier)
	chosen = {}
	for row in rows or []:
		doctype = row.get("doctype")
		if not doctype:
			continue
		if doctype not in allowed:
			frappe.throw(_("{0} is not a record type {1} uses.").format(_(doctype), app))
		chosen[doctype] = {right for right in RIGHTS if frappe.utils.cint(row.get(right))}
	had = {doctype: _rights(doctype, held) for doctype in allowed}
	wanted = {
		doctype: _wanted(doctype, chosen.get(doctype, set()), had.get(doctype, set()))
		for doctype in allowed | set(chosen)
	}
	everyone = set(EVERYONE)
	picked = {}
	for doctype in sorted(wanted):
		if not {"write", "create"} & wanted[doctype]:
			continue
		for target in sorted(_picks(doctype)):
			if target in picked:
				picked[target].append(doctype)
				continue
			has = wanted[target] if target in wanted else _rights(target, held)
			if {"select", "read"} & (has | _rights(target, everyone)):
				continue
			wanted[target] = has | {"select"}
			picked[target] = [doctype]
	changed = [
		doctype for doctype in sorted(wanted) if wanted[doctype] != had.get(doctype, _rights(doctype, held))
	]
	_set(app, tier, {doctype: wanted[doctype] for doctype in changed})
	if abilities is not None and save_abilities(app, tier, abilities):
		changed.append("abilities")
	if changed:
		for user in people_at(app, tier):
			tell.access_changed(
				user, _("what {0} can do in {1}").format(_(tier) if tier in BASE else tier, app)
			)
	if picked:
		frappe.msgprint(
			_("So they can fill those in, they may also pick from {0}.").format(
				", ".join(
					_("{0} (for {1})").format(_(one), ", ".join(_(why) for why in whys[:2]))
					if len(whys) <= 2
					else _("{0} (for {1} and {2} more)").format(
						_(one), ", ".join(_(why) for why in whys[:2]), len(whys) - 2
					)
					for one, whys in picked.items()
				)
			)
		)
	return key_of(app, tier)


def _set(app: str, tier: str, wanted: dict) -> None:
	"""One level given exactly `wanted` on each of those kinds, every other
	level of the app keeping what it has: what all of them share is written
	on the app's User roles, and each one's own on its own roles."""
	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

	if not wanted:
		return
	_companion(app)
	used, _managed = _builders()[app]
	every = tiers(app)
	for doctype, rights in wanted.items():
		have = {one: _rights(doctype, _holds(app, one)) for one in every}
		have[tier] = set(rights)
		shared = set.intersection(*have.values())
		setup_custom_perms(doctype)
		_put(doctype, used, shared)
		for one in every:
			_put(doctype, _carriers(app, one), have[one] - shared)
		validate_permissions_for_doctype(doctype, alert=False)
		frappe.clear_cache(doctype=doctype)


def _put(doctype: str, carriers: tuple, rights: set) -> None:
	"""Roles made to hold `rights` between them on a kind, at the first level:
	each keeps what it had of them, and the first of them takes the rest."""
	had = {role: _rights(doctype, {role}) for role in carriers}
	now = {role: had[role] & rights for role in carriers}
	rest = rights - set().union(*now.values())
	if rest:
		first = next((role for role in carriers if now[role]), carriers[0])
		now[first] |= rest
	for role in carriers:
		said = _close(doctype, now[role])
		if said != had[role]:
			_row(doctype, role, said)


def _row(doctype: str, role: str, rights: set) -> None:
	"""A role's rule on a kind at the first level, made to say `rights`. With
	none left it goes, unless the role has a rule on the kind's guarded
	fields, which frappe keeps only over a first-level rule."""
	where = {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}
	name = frappe.db.get_value("Custom DocPerm", where)
	if not rights:
		if not name:
			return
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": [">", 0]}):
			frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True, force=True)
			return
		rights = {"select"}
	doc = (
		frappe.get_doc("Custom DocPerm", name)
		if name
		else frappe.get_doc(
			{"doctype": "Custom DocPerm", "parenttype": "DocType", "parentfield": "permissions", **where}
		)
	)
	for right in ALL_RIGHTS:
		doc.set(right, 1 if right in rights else 0)
	doc.save(ignore_permissions=True)


def new_level(app: str, title: str, start: str = "User") -> str:
	"""A level of one app that starts as one of its levels already is, to
	change on its page."""
	roles.require()
	if app not in _builders() or start not in tiers(app):
		frappe.throw(_("That cannot be set."))
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the role a name."))
	if ":" in title:
		frappe.throw(_("A role's name cannot have a colon in it."))
	if frappe.db.exists("Role", title):
		frappe.throw(_("There is already a role called {0}.").format(title))
	frappe.get_doc(
		{"doctype": "Role", "role_name": title, "desk_access": 1, "is_custom": 1, "one_app": app}
	).insert(ignore_permissions=True)
	held = _holds(app, start)
	wanted = {}
	for doctype in sorted(_matrix(app, start)):
		has = _rights(doctype, held)
		if has != _rights(doctype, _holds(app, title)):
			wanted[doctype] = has
	_set(app, title, wanted)
	_guarded(app, start, title)
	save_abilities(app, title, {one["key"]: one["value"] for one in abilities_of(app, start)})
	return title


def _guarded(app: str, start: str, level: str) -> None:
	"""A new level given the rules on guarded fields that the level it started
	from holds of its own, such as a manager's on pay."""
	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

	touched = set()
	for row in frappe.get_all(
		"Custom DocPerm",
		filters={"role": ["in", list(_carriers(app, start))], "permlevel": [">", 0]},
		fields=["parent", "permlevel", "if_owner", *ALL_RIGHTS],
	):
		where = {"parent": row.parent, "role": level, "permlevel": row.permlevel, "if_owner": row.if_owner}
		if frappe.db.exists("Custom DocPerm", where):
			continue
		frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				"parenttype": "DocType",
				"parentfield": "permissions",
				**where,
				**{right: row.get(right) for right in ALL_RIGHTS},
			}
		).insert(ignore_permissions=True)
		touched.add(row.parent)
	for doctype in touched:
		validate_permissions_for_doctype(doctype, alert=False)
		frappe.clear_cache(doctype=doctype)


def delete_level(name: str) -> None:
	roles.require()
	app_of(name)
	people = people_at(app_of(name), name)
	if people:
		frappe.throw(_("{0} people have this role. Give them another first.").format(len(people)))
	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

	touched = _written({name})
	for row in frappe.get_all("Custom DocPerm", filters={"role": name}, pluck="name"):
		frappe.delete_doc("Custom DocPerm", row, ignore_permissions=True, force=True)
	for doctype in touched:
		validate_permissions_for_doctype(doctype, alert=False)
		frappe.clear_cache(doctype=doctype)
	frappe.delete_doc("Role", name, ignore_permissions=True, force=True)


def for_doctype(doctype: str) -> list[dict]:
	"""What each level of each app may do on one kind of record, for the
	record's Settings > Access: User, the workspace's own levels, Manager."""
	roles.require()
	said = []
	for app in _apps():
		rows = [
			{
				"level": tier,
				"key": key_of(app, tier),
				"rights": sorted(_rights(doctype, _holds(app, tier)) & set(RIGHTS), key=RIGHTS.index),
				"own": int(tier not in BASE),
			}
			for tier in tiers(app)
		]
		if any(row["rights"] for row in rows):
			said.append({"app": app, "rows": rows})
	return said


def matrix_of(app: str) -> dict:
	"""A module's role builder (one/rights.py): its roles as columns, User,
	the workspace's own, Manager; its abilities as rows, in the module's
	groups; and what each role holds of each."""
	from onedesk.one import rights

	roles.require()
	declared = rights.of_app(app)
	if not declared or app not in _builders():
		frappe.throw(_("That cannot be set."))
	names = getattr(declared, "SCOPE_LABELS", {})
	columns, values, least = [], {}, {}
	for tier in tiers(app):
		key = key_of(app, tier)
		held = abilities_of(app, tier)
		columns.append({"key": key, "name": tier, "own": int(tier not in BASE), "people": len(people_at(app, tier))})
		values[key] = {one["key"]: one["value"] for one in held}
		least[key] = {one["key"]: one["least"] for one in held if tier != "User"}
	groups = []
	for one in declared.ABILITIES:
		group = str(one["group"])
		if not groups or groups[-1]["label"] != group:
			groups.append({"label": group, "rows": []})
		said = {**names, **({"none": one["none"]} if one.get("none") else {})}
		groups[-1]["rows"].append(
			{
				"key": one["key"],
				"label": str(one["label"]),
				"about": str(one.get("about") or ""),
				"kind": one["kind"],
				"options": [] if one["kind"] == "switch" else [
					{"value": scope, "label": str(said.get(scope) or scope)} for scope in rights.SCOPES
				],
			}
		)
	return {"app": app, "roles": columns, "groups": groups, "values": values, "least": least}


def set_ability(key: str, ability: str, value) -> dict:
	"""One cell of the role builder: what one role holds of one ability. A
	role above User never holds less than User does."""
	from onedesk.one import rights

	roles.require()
	app, tier = tier_of(key)
	one = rights.ability(app, ability)
	held = {row["key"]: row for row in abilities_of(app, tier)}
	if one["kind"] == "switch":
		value = frappe.utils.cint(value)
		too_little = value < held[ability]["least"]
	else:
		too_little = value not in rights.SCOPES or rights.SCOPES.index(value) < rights.SCOPES.index(held[ability]["least"])
	if too_little:
		frappe.throw(_("A role above User has everything User has."))
	save_abilities(app, tier, {**{name: row["value"] for name, row in held.items()}, ability: value})
	return matrix_of(app)


def rename_level(name: str, title: str) -> str:
	roles.require()
	app_of(name)
	return _rename(name, title)


@frappe.whitelist()
def ability_matrix(app: str) -> dict:
	return matrix_of(app)


@frappe.whitelist(methods=["POST"])
def change_ability(key: str, ability: str, value) -> dict:
	return set_ability(key, ability, value)


@frappe.whitelist(methods=["POST"])
def rename_role(name: str, title: str) -> str:
	return rename_level(name, title)


@frappe.whitelist(methods=["POST"])
def make_level(app: str, title: str, start: str = "User") -> str:
	return new_level(app, title, start)


@frappe.whitelist(methods=["POST"])
def remove_level(name: str) -> None:
	delete_level(name)


@frappe.whitelist()
def doctype_levels(doctype: str) -> list[dict]:
	"""For a record's Settings > Access."""
	return for_doctype(doctype)


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
	from onedesk.one.people import NOT_PEOPLE

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
	tell.access_changed(user, _("only the records of {0} {1}").format(_(allow), for_value))


@frappe.whitelist(methods=["POST"])
def let_go(name: str) -> None:
	"""One of a person's holds taken away."""
	doc = frappe.get_doc("User Permission", name)
	_person(doc.user)
	if doc.allow not in RECORD_KINDS:
		frappe.throw(_("That cannot be set."))
	doc.delete(ignore_permissions=True)
	tell.access_changed(
		doc.user, _("no longer only the records of {0} {1}").format(_(doc.allow), doc.for_value)
	)


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
	from onedesk.one.people import app_level

	return {app: app_level(app, held, used, managed, own.get(app, ())) for app, (used, managed) in _apps().items()}


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
	from onedesk.one.people import ALWAYS, LEVELS, roles_for

	roles.require()
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the profile a name."))
	own = all_levels()
	wanted = {"Desk User"}
	for app, (used, managed) in _apps().items():
		level = levels.get(app) or "None"
		if app in ALWAYS and level == "None":
			level = "User"
		if level not in LEVELS and level not in own.get(app, ()):
			frappe.throw(_("That cannot be set."))
		wanted |= roles_for(level, used, managed, own.get(app, ()), (companion(app),))
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
	doc.unlock()
	for user in frappe.get_all("User", filters={"one_profile": doc.name}, pluck="name"):
		put_on(user, doc.name)
	return doc.name


def put_on(user: str, name: str | None) -> None:
	"""A person set to a profile's levels, or taken off one. Their
	administrator switch and every role outside the apps are kept."""
	from onedesk.one.people import set_access

	doc = frappe.get_doc("User", user)
	if name:
		levels = profile(name)["levels"]
		set_access(doc, levels, 1 if roles.ADMINISTRATOR in {one.role for one in doc.roles} else 0)
	frappe.db.set_value("User", user, "one_profile", name or None, update_modified=False)


@frappe.whitelist(methods=["POST"])
def new_profile(title: str) -> str:
	return save_profile(None, title, {})


@frappe.whitelist(methods=["POST"])
def remove_profile(name: str) -> None:
	roles.require()
	frappe.db.set_value("User", {"one_profile": name}, "one_profile", None, update_modified=False)
	frappe.delete_doc("Role Profile", name, ignore_permissions=True, force=True)


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
	from onedesk.one.people import NOT_PEOPLE

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
		frappe.throw(_("Add at least one person to the group."))
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


ADMINISTRATOR = {
	"Note": ("read", "write", "create", "delete"),
	"Workflow": ("read", "write", "create", "delete"),
	"Workflow State": ("read", "write", "create"),
	"Workflow Action Master": ("read", "write", "create"),
	"Version": ("read", "report"),
	"Activity Log": ("read", "report"),
	"Access Log": ("read", "report"),
	"Automation Flow": ("read", "write", "create", "delete"),
	"Email Template": ("read", "write", "create", "delete"),
	"Document Naming Rule": ("read", "write", "create", "delete"),
	"Notification Type": ("read", "write"),
	"Notification": ("read", "write", "create", "delete"),
	"Print Format": ("read", "write", "create", "delete", "print"),
	"Letter Head": ("read", "write", "create", "delete"),
	"Print Format Snippet": ("read", "write", "create", "delete"),
	"Print Format Field Template": ("read",),
	"Print Settings": ("read",),
	"Personal Data Deletion Request": ("read", "report"),
	"Personal Data Download Request": ("read", "report"),
	"Transaction Deletion Record": ("read",),
	"Deleted Document": ("read", "delete"),
	"Report": ("read", "write", "create", "delete"),
	"Auto Email Report": ("read", "write", "create", "delete"),
	"Dashboard": ("read", "write", "create", "delete"),
	"Dashboard Chart": ("read", "write", "create", "delete"),
	"Number Card": ("read", "write", "create", "delete"),
	"Webhook": ("read", "write", "create", "delete"),
	"Webhook Request Log": ("read", "report"),
	"Web Form": ("read", "write", "create", "delete"),
	"Email Domain": ("read",),
	"Dashboard Chart Source": ("read",),
	"Workflow Transition Tasks": ("read", "write", "create"),
}

PAGES = ("workflow-builder", "print-format-builder", "setup-wizard")

NOTE_LEVELS = {1: ("read", "write"), 2: ("read",)}

MASTER = ("read", "write", "create", "delete")

LISTS_GIVEN = "onedesk_masters_given"

DESK = "Desk User"


def settle() -> None:
	"""after_sync and after_migrate: what One's roles are given on frappe's doctypes."""
	roles.grant(ADMINISTRATOR)
	for page in PAGES:
		roles.open_page(page)
	_note_levels()
	_lists()
	_everybody("Report", "create")
	_own_reports()
	_everybody("Deleted Document", "read")
	_no_copies_in_the_sidebar()
	_no_google()


def _note_levels() -> None:
	"""The administrator's rights on a Note's higher levels, once each."""
	from frappe.permissions import add_permission, update_permission_property

	for level, ptypes in NOTE_LEVELS.items():
		if frappe.db.exists("Custom DocPerm", {"parent": "Note", "role": roles.ADMINISTRATOR, "permlevel": level}):
			continue
		add_permission("Note", roles.ADMINISTRATOR, level)
		for ptype in ptypes:
			update_permission_property("Note", roles.ADMINISTRATOR, level, ptype, 1, validate=False)


def _lists() -> None:
	"""The administrator keeps every module's lists (one/lists.py), and an
	app's managers its own. erpnext keeps several for a role of its own
	(Customer Group for its Sales Master Manager), so One's managers are
	given them once each."""
	from onedesk.one.lists import kinds_of
	from onedesk.one.people import APPS

	kinds = kinds_of()
	roles.grant({doctype: MASTER for _module, doctype, _label, _one in kinds if frappe.db.exists("DocType", doctype)})
	managers = {label: roles_ for label, _code, _users, roles_ in APPS}
	roles.raise_once(
		{doctype: dict.fromkeys(managers.get(module, ()), MASTER) for module, doctype, _label, _one in kinds},
		LISTS_GIVEN,
	)


def _everybody(doctype: str, ptype: str) -> None:
	"""One right for every desk user, once: Save As on a report (frappe lets a
	Desk User read one and not make one), and reading their own deletions,
	narrowed by one/recycle.py's `query` and `has_permission`."""
	from frappe.permissions import add_permission, update_permission_property

	where = {"parent": doctype, "role": DESK, "permlevel": 0, "if_owner": 0}
	if frappe.db.get_value("Custom DocPerm", where, ptype):
		return
	setup_custom_perms(doctype)
	if not frappe.db.exists("Custom DocPerm", where):
		add_permission(doctype, DESK, 0)
	update_permission_property(doctype, DESK, 0, ptype, 1, validate=False)


def _own_reports() -> None:
	"""A desk user saves a report and may change and delete it again, their
	own only, since frappe gives a Desk User none of that. Written once."""
	where = {"parent": "Report", "role": DESK, "permlevel": 0, "if_owner": 1}
	if frappe.db.exists("Custom DocPerm", where):
		return
	setup_custom_perms("Report")
	rights = dict.fromkeys(("read", "write", "delete"), 1)
	frappe.get_doc({"doctype": "Custom DocPerm", **where, **rights}).insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Report")


def _no_copies_in_the_sidebar() -> None:
	"""frappe lets everybody read their own copy requests, which put Data
	Copies in every person's sidebar. The person sees theirs on their profile."""
	download = "Personal Data Download Request"
	setup_custom_perms(download)
	for name in frappe.get_all("Custom DocPerm", filters={"parent": download, "role": "All"}, pluck="name"):
		frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True)
		frappe.clear_cache(doctype=download)


GOOGLE = ("Google Calendar", "Google Contacts")


def _no_google() -> None:
	"""frappe's Google Calendar and Google Contacts sync, which One does not
	offer: no desk user opens either, and their fields are hidden on Event
	and Contact. A calendar reaches Google through its own link
	(one_calendar/feed.py)."""
	for doctype in GOOGLE:
		setup_custom_perms(doctype)
		for name in frappe.get_all("Custom DocPerm", filters={"parent": doctype, "role": DESK}, pluck="name"):
			frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True)
			frappe.clear_cache(doctype=doctype)
