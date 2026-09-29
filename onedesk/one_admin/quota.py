"""What a workspace may use: its plan, and the add-ons on it.

The limits are a sum and copied onto `Tenant` when the workspace signs up
(signup.py) and whenever its plan or an add-on changes, and only then: an
offering is a price list the operator edits, and re-pricing a plan must not
change what a customer already bought. Everything that enforces a limit
reads the copy:

* **seats**, pushed to the workspace in `hello`, where People refuses a seat
  past it;
* **storage**, refused at upload by `storage.put_url`;
* **database**, measured by the workspace itself and sent in `hello`, where
  it is shown and warned about. The sites are on our own Frappe Cloud
  servers, where a site is unlimited and carries no Frappe Cloud plan, so
  there is nothing to move it to: the limit is ours to watch, and Home says
  when a workspace is past it;
* **credits a month**, granted by `topup.monthly`.

A zero on the plan is no limit, as Offering says; an add-on on an unlimited
plan changes nothing.
"""

import frappe
from frappe.utils import cint

from onedesk.one_admin import site

GB = 1000 * 1000 * 1000

#: What a plan and an add-on can carry, as Offering fields.
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
