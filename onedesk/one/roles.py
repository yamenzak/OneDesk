"""Who administers a workspace, and who manages its mail.

Workspace Administrator in place of System Manager, which nobody on a
workspace is ever given; Mail Manager for the workspace's mailboxes alone
(one_mail/README.md).
"""

import frappe

ADMINISTRATOR = "Workspace Administrator"

MAIL_MANAGER = "Mail Manager"


def ensure(*_args) -> None:
	"""The role exists on every site, workspace or admin alike. Mail Manager
	is a fixture (fixtures/role.json)."""
	if frappe.db.exists("Role", ADMINISTRATOR):
		return
	frappe.get_doc(
		{"doctype": "Role", "role_name": ADMINISTRATOR, "desk_access": 1, "is_custom": 0}
	).insert(ignore_permissions=True)


def manages_mail(user: str | None = None) -> bool:
	"""Whether somebody manages the workspace's mailboxes: a Mail Manager or
	an administrator."""
	held = frappe.get_roles(user)
	return ADMINISTRATOR in held or MAIL_MANAGER in held


def administers(user: str | None = None) -> bool:
	return ADMINISTRATOR in frappe.get_roles(user)


def administrators() -> list[str]:
	"""Everybody who administers this workspace and is turned on: who hears
	about the workspace itself (its account, a new administrator)."""
	held = frappe.get_all(
		"Has Role",
		filters={
			"role": ADMINISTRATOR,
			"parenttype": "User",
			"parent": ["not in", ("Administrator", "Guest")],
		},
		pluck="parent",
		distinct=True,
	)
	return frappe.get_all("User", filters={"name": ["in", held or [""]], "enabled": 1}, pluck="name")


def mail_managers() -> list[str]:
	"""Everybody turned on who manages the workspace's mail: who hears of a
	rule waiting for approval."""
	held = frappe.get_all(
		"Has Role",
		filters={
			"role": ["in", (ADMINISTRATOR, MAIL_MANAGER)],
			"parenttype": "User",
			"parent": ["not in", ("Administrator", "Guest")],
		},
		pluck="parent",
		distinct=True,
	)
	return frappe.get_all("User", filters={"name": ["in", held or [""]], "enabled": 1}, pluck="name")


def require_mail() -> None:
	"""Refuse anyone who doesn't manage the workspace's mail."""
	if not manages_mail():
		frappe.throw(frappe._("Only a Mail Manager or an administrator can do this."), frappe.PermissionError)


def require() -> None:
	"""Refuse anyone who does not administer this workspace."""
	if not administers():
		frappe.throw(
			frappe._("Only an administrator of this workspace can do this."),
			frappe.PermissionError,
		)


def grant(grants: dict) -> None:
	"""What the role is given on frappe's doctypes, {doctype: (ptype, ...)},
	written once per doctype: a doctype with a Custom DocPerm row for the role
	has been decided by the workspace, which may have changed it since."""
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	for doctype, ptypes in grants.items():
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": ADMINISTRATOR}):
			continue
		setup_custom_perms(doctype)
		add_permission(doctype, ADMINISTRATOR, 0)
		for ptype in ptypes:
			update_permission_property(doctype, ADMINISTRATOR, 0, ptype, 1, validate=False)


USE = ("read", "report", "print")
WORK = (*USE, "write", "create", "submit")
MANAGE = (*WORK, "delete", "cancel", "amend", "export", "share")

SUBMITTING = ("submit", "cancel", "amend")


def give(grants: dict) -> None:
	"""What a space's own roles are given, {doctype: {role: (ptype, ...)}}:
	a role that reads there already, by erpnext's rules or the workspace's,
	keeps what it has, and one that does not is given these. A kind or role
	the site does not have is skipped, and so is submitting where nothing is."""
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	for doctype, by_role in grants.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		submits = frappe.get_meta(doctype).is_submittable
		for role, ptypes in by_role.items():
			if not frappe.db.exists("Role", role):
				continue
			where = {"parent": doctype, "role": role, "permlevel": 0, "read": 1}
			if frappe.db.exists("Custom DocPerm", where) or (
				not frappe.db.exists("Custom DocPerm", {"parent": doctype})
				and frappe.db.exists("DocPerm", where)
			):
				continue
			setup_custom_perms(doctype)
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				add_permission(doctype, role, 0)
			for ptype in ptypes:
				if ptype in SUBMITTING and not submits:
					continue
				update_permission_property(doctype, role, 0, ptype, 1, validate=False)


def raise_once(grants: dict, kept: str = "onedesk_roles_raised") -> None:
	"""More for a role that has some already, {doctype: {role: (ptype, ...)}}:
	where erpnext keeps adding a record for a role of its own nobody in One
	holds. Each kind and role is given once, and kept in the default `kept`,
	so a change made later in Access stands."""
	import json

	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	given = set(json.loads(frappe.db.get_default(kept) or "[]"))
	for doctype, by_role in grants.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		submits = frappe.get_meta(doctype).is_submittable
		for role, ptypes in by_role.items():
			key = f"{doctype}|{role}"
			if key in given or not frappe.db.exists("Role", role):
				continue
			setup_custom_perms(doctype)
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				add_permission(doctype, role, 0)
			for ptype in ptypes:
				if ptype in SUBMITTING and not submits:
					continue
				update_permission_property(doctype, role, 0, ptype, 1, validate=False)
			given.add(key)
	frappe.db.set_default(kept, json.dumps(sorted(given)))


def open_page(page: str) -> None:
	"""A frappe page opened to the role, through frappe's Custom Role. A Custom
	Role replaces the page's roles, so it keeps the page's own too."""
	_open("page", page)


def open_report(report: str, *given: str) -> None:
	"""A report opened to `given` as well as to its own roles, the same way."""
	_open("report", report, given)


def _open(field: str, name: str, given: tuple = ()) -> None:
	parent = frappe.db.get_value("Custom Role", {field: name})
	custom = frappe.get_doc("Custom Role", parent) if parent else frappe.new_doc("Custom Role")
	if not parent:
		custom.set(field, name)
		if field == "report":
			custom.ref_doctype = frappe.db.get_value("Report", name, "ref_doctype")
	held = {row.role for row in custom.roles}
	before = len(held)
	own = frappe.get_all("Has Role", filters={"parenttype": field.title(), "parent": name}, pluck="role")
	for role in (*own, ADMINISTRATOR, *given):
		if role not in held and frappe.db.exists("Role", role):
			custom.append("roles", {"role": role})
			held.add(role)
	if not parent or len(held) != before:
		custom.save(ignore_permissions=True)
