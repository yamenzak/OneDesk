"""Which site this is, and the one switch that decides.

The same app ships to every site. A site is the **admin site** when its
`site_config.json` carries `"one_admin": 1`, and a tenant workspace otherwise.

It is a site config key rather than a role, a setting or a fixture, and that is
the whole point: all three of those are editable from a desk by somebody holding
System Manager. Nobody on a workspace is given it (`one/roles.py`), but a rule
that holds only while nobody is ever given a role is a rule one mistake away
from not holding. `site_config.json` is a file on the bench that no request can write.
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

**The role is not on its own, though, and it should not be.** A role is a row,
and anybody who ever held System Manager on a workspace could grant themselves
`One Operator` between one migrate and the next, and the permission machinery
would let them in. Two hooks close that, and it takes
two because Frappe asks the question in two different places:

* `refuse_on_a_tenant` is the `has_permission` hook. Frappe calls it only when
  there is a document to judge, so it is what refuses opening a record.
* `nothing_on_a_tenant` is the `permission_query_conditions` hook. It is what
  every list, report and link search goes through, and on a workspace site it
  returns a condition nothing satisfies.

Measured, because the first on its own looked like enough and was not: with the
role granted by hand and the flag off, `has_permission("Tenant")` with no
document still answered True and `get_list` returned rows. The hook had only
ever fired for `One Admin Settings`, which is a Single and therefore always has
a document. A gate that covers the form and not the list is not a gate.

Both read `frappe.conf`, which is a file on the bench that no request can write.
So there are two kinds of gate and they fail differently: the role decides what
is *offered* — a rail, an awesomebar, a report builder — and the site config
decides what is *answered*.
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


def refuse_on_a_tenant(doc=None, ptype=None, user=None) -> bool:
	"""Opening one of these records, on a site that does not administer anything.

	Registered under `has_permission`. Frappe calls it after the role check has
	already passed and a False here refuses anyway, so a role somebody granted
	themselves on their own workspace buys nothing.

	It is called only when there is a document, which is why it is not the whole
	answer — see `nothing_on_a_tenant`.
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
