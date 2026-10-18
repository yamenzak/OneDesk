"""What a workspace may use: its plan, and the add-ons on it.

The limits are a sum, copied onto `Tenant` at signup and whenever its plan or
an add-on changes, and only then; everything that enforces a limit reads the
copy. A zero on the plan is no limit.
"""

import frappe
from frappe.utils import cint

from onedesk.one_admin import site

GB = 1000 * 1000 * 1000

LIMITED = ("seats", "storage_gb", "database_gb", "credits_a_month")


def limits(tenant) -> dict:
	"""The plan's quota plus every add-on times how many, per resource. None
	for a resource the plan leaves unlimited."""
	tenant = _doc(tenant)
	plan = (
		frappe.db.get_value("Offering", tenant.offering, list(LIMITED), as_dict=True)
		if tenant.offering
		else None
	) or frappe._dict()
	held = {one: cint(plan.get(one)) or (0 if one == "credits_a_month" else None) for one in LIMITED}
	for row in tenant.get("add_ons") or []:
		adds = frappe.db.get_value("Offering", row.offering, list(LIMITED), as_dict=True) or {}
		for one in LIMITED:
			if held[one] is not None and adds.get(one):
				held[one] += cint(adds.get(one)) * max(1, cint(row.quantity))
	return held


def apply(tenant) -> dict:
	"""Write the limits onto the tenant."""
	site.require_admin()
	tenant = _doc(tenant)
	held = limits(tenant)
	frappe.db.set_value(
		"Tenant",
		tenant.name,
		{
			"seats": held["seats"] or 0,
			"storage_limit": (held["storage_gb"] or 0) * GB,
			"database_limit": (held["database_gb"] or 0) * GB,
			"credits_a_month": held["credits_a_month"] or 0,
		},
		update_modified=False,
	)
	return held


def _doc(tenant):
	return frappe.get_doc("Tenant", tenant) if isinstance(tenant, str) else tenant


def held_on_servers() -> dict:
	"""How many workspaces each server holds: every one placed on it that is
	not archived or dropped, since those have no site any more."""
	from collections import Counter

	return Counter(
		frappe.get_all(
			"Tenant",
			filters={"server": ["is", "set"], "status": ["not in", ("Archived", "Dropped")]},
			pluck="server",
		)
	)
