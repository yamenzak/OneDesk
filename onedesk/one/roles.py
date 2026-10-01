"""Who administers a workspace.

Nobody on a workspace is ever given System Manager — not the person who signed
up, not whoever they hand the keys to. System Manager is the whole desk: every
doctype, every setting, the scheduler, the users. What somebody running their
own workspace needs is much narrower — which model an action runs on and what
it is told, the workspace's address, buying credits — and a role that grants
exactly that is one that can be handed out without handing out the site.

It is called Workspace Administrator because frappe already ships a role named
Workspace Manager, and that one is about editing the desk's sidebar pages.

Administrator the user holds every role, so nothing here locks the bench's own
account out of anything.
"""

import frappe

ADMINISTRATOR = "Workspace Administrator"


def ensure(*_args) -> None:
	"""The role exists on every site, workspace or admin alike."""
	if frappe.db.exists("Role", ADMINISTRATOR):
		return
	frappe.get_doc(
		{"doctype": "Role", "role_name": ADMINISTRATOR, "desk_access": 1, "is_custom": 0}
	).insert(ignore_permissions=True)


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


#: What a space's roles are given where erpnext gives only its System
#: Manager (give): to look, to do the work, to run it.
USE = ("read", "report", "print")
WORK = (*USE, "write", "create", "submit")
MANAGE = (*WORK, "delete", "cancel", "amend", "export")

#: Rights only a submittable kind has.
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


def open_page(page: str) -> None:
	"""A frappe page opened to the role, through frappe's Custom Role. A Custom
	Role replaces the page's roles, so it keeps the page's own too."""
	name = frappe.db.get_value("Custom Role", {"page": page})
	custom = frappe.get_doc("Custom Role", name) if name else frappe.new_doc("Custom Role")
	if not name:
		custom.page = page
	held = {row.role for row in custom.roles}
	own = frappe.get_all("Has Role", filters={"parenttype": "Page", "parent": page}, pluck="role")
	for role in (*own, ADMINISTRATOR):
		if role not in held:
			custom.append("roles", {"role": role})
	if not name or len(custom.roles) != len(held):
		custom.save(ignore_permissions=True)
