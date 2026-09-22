"""Which site this is, and the one switch that decides.

The same app ships to every site. A site is the **admin site** when its
`site_config.json` carries `"one_admin": 1`, and a tenant workspace otherwise.

It is a site config key rather than a role, a setting or a fixture, and that is
the whole point: all three of those are editable from a desk by somebody holding
System Manager, and a tenant administrator holds System Manager on their own
workspace. `site_config.json` is a file on the bench that no request can write.
So the question "may this site provision workspaces and hold the ledger that
bills people" has an answer the people being billed cannot change.

**Hiding is Frappe's own permission machinery, not a layer over it.** Every
doctype in the One Admin module grants exactly one role, `One Operator`, and
grants it to nobody else — not System Manager, not Administrator by DocPerm.
So a tenant site carries the tables and refuses every route a person has to
them. Measured on the dev site as a System Manager who is not Administrator:
`frappe.client.get` and `get_value` raise `PermissionError`, the desk's own
form load raises it, `get_list` never gets as far as a query, and the doctype
is absent from `can_read`, which is what the awesomebar and the report builder
offer from.

The exact claim is "no route a request has", not "no route". `frappe.get_doc`
called from bench Python reads it, because `get_doc` checks permission on write
and not on read — the check lives at the API layer. That is not a hole here:
running Python on the bench means holding the bench, and a tenant holds a
workspace. It is worth being exact about, though, because the day somebody
writes a whitelisted helper that calls `get_doc` on one of these and returns
it, the permission is not there to save them. Anything reading an operator
doctype for a caller starts with `require_admin()`.

`apply()` keeps that true in both directions on every migrate. On the admin site
the role exists. On a tenant site it is removed from everyone who somehow has
it, which is the case that matters: a site restored from an admin backup, or a
workspace that was the admin site during development.
"""

import frappe

#: The key, and the only one. Read through `frappe.conf` rather than
#: `frappe.local.conf` so it resolves the same in a request, a worker and a
#: bench console.
FLAG = "one_admin"

#: The role every One Admin doctype grants, and the only role any of them
#: grants. `tests/test_admin_flag.py` holds that.
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
		raise frappe.PermissionError(frappe._("This site does not administer workspaces."))


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
