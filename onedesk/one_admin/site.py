"""Which site this is, and the one switch that decides.

A site is the admin site when its `site_config.json` carries `"one_admin": 1`,
and a tenant workspace otherwise. A file no request can write, so the people
being billed cannot change it.
"""

import frappe

FLAG = "one_admin"

OPERATOR = "One Operator"


def is_admin() -> bool:
	"""Whether this site is the admin site."""
	return bool(frappe.conf.get(FLAG))


def require_admin() -> None:
	"""Refuse on a tenant site.

	Every whitelisted method that provisions, prices or bills starts here. The
	message says what is wrong rather than what was asked for: a tenant site
	reaching one of these is a misconfiguration or a probe, and neither is
	helped by being told which endpoint exists.
	"""
	if not is_admin():
		raise frappe.PermissionError(frappe._("This site doesn't manage workspaces."))


def apply(*_args) -> None:
	"""Make the operator role match what kind of site this is."""
	if is_admin():
		_ensure_role()
		return
	_withdraw_role()


def _ensure_role() -> None:
	if frappe.db.exists("Role", OPERATOR):
		return
	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": OPERATOR,
			"desk_access": 1,
			"is_custom": 0,
		}
	).insert(ignore_permissions=True)


def _withdraw_role() -> None:
	"""Take it off anybody holding it on a site that is not the admin site.

	The role itself is left in place. Deleting it would cascade through every
	`Has Role` and every DocPerm that names it, and the doctypes here name it in
	their own shipped JSON — so a migrate would put it straight back and the
	delete would have achieved a slower migrate and nothing else.
	"""
	if not frappe.db.exists("Role", OPERATOR):
		return
	for name in frappe.get_all("Has Role", filters={"role": OPERATOR}, pluck="name"):
		frappe.delete_doc("Has Role", name, ignore_permissions=True, force=True)


def refuse_on_a_tenant(doc=None, ptype=None, user=None) -> bool:
	"""Opening one of these records, on a site that does not administer anything.

	Registered under `has_permission`; it is called only when there is a
	document, which is why it is not the whole answer (`nothing_on_a_tenant`).
	"""
	return is_admin()


def nothing_on_a_tenant(user=None, doctype=None) -> str:
	"""Listing one of these records, on a site that does not administer anything.

	Registered under `permission_query_conditions`, which is the seam every
	list, report, link search and `get_list` passes through. An empty string
	adds no condition; `1=0` is a condition nothing satisfies, so the query runs
	and answers nothing rather than raising — which is also what a list does for
	a doctype holding no rows, and a workspace site holds none of these anyway.
	"""
	return "" if is_admin() else "1=0"


MODULE = "One Admin"


def offer(bootinfo=None) -> None:
	"""`extend_bootinfo`: OneAdmin's rail and Home are offered to operators only.

	frappe gives every workspace to Workspace Manager, whatever roles it names, so
	the way to OneAdmin is taken out of what the desk is told.
	"""
	if is_admin() and OPERATOR in frappe.get_roles():
		return
	sidebars = bootinfo.get("module_sidebars")
	if isinstance(sidebars, dict):
		sidebars.pop(MODULE, None)
	for key in ("allowed_workspaces", "workspaces"):
		held = bootinfo.get(key)
		if isinstance(held, dict) and isinstance(held.get("pages"), list):
			held["pages"] = [page for page in held["pages"] if _named(page) != MODULE]
		elif isinstance(held, list):
			bootinfo[key] = [page for page in held if _named(page) != MODULE]


def _named(page) -> str | None:
	return page.get("name") if isinstance(page, dict) else page
