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
