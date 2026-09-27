"""What a workspace may use: its plan, and the add-ons on it.

The limits are a sum and copied onto `Tenant` when the workspace signs up
(signup.py) and whenever its plan or an add-on changes, and only then: an
offering is a price list the operator edits, and re-pricing a plan must not
change what a customer already bought. Everything that enforces a limit
reads the copy:

* **seats**, pushed to the workspace in `hello`, where People refuses a seat
  past it;
* **storage**, refused at upload by `storage.put_url`;
* **database**, which is Frappe Cloud's to enforce: the site is moved to the
  smallest Frappe Cloud plan whose database limit covers it (`move`). A move
  that press refuses or cannot be asked is left pending on the tenant and
  tried again nightly, because the customer has paid for the room either way;
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
	"""Write the limits onto the tenant, and move its site for the database."""
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
	move(tenant.name)
	return held


def press_plan_for(database_gb: int | None) -> str | None:
	"""The cheapest Frappe Cloud plan whose database limit covers this many
	GB, or None when the list cannot be read. Press states the limit in MB."""
	from onedesk.one_admin import faults, press

	try:
		offered = press.plans() or []
	except faults.Refused:
		return None
	wanted = (database_gb or 0) * 1024
	fits = [
		one
		for one in offered
		if not one.get("max_database_usage") or cint(one.get("max_database_usage")) >= wanted
	]
	fits.sort(key=lambda one: float(one.get("price_usd") or one.get("price") or 0))
	return fits[0].get("name") if fits else None


def move(slug: str) -> str | None:
	"""Put the tenant's site on the Frappe Cloud plan its database limit
	needs. Returns the plan asked for, or None when nothing was asked."""
	from onedesk.one_admin import faults, press

	tenant = frappe.get_doc("Tenant", slug)
	if not tenant.site:
		return None
	wanted = press_plan_for(round(cint(tenant.database_limit) / GB) or None)
	if not wanted or wanted == tenant.press_plan:
		return None
	try:
		press.call("press.api.site.change_plan", name=tenant.site, plan=wanted)
	except faults.Refused as refused:
		_event(slug, "Plan Change Pending", f"asked for {wanted}: {refused}")
		return None
	frappe.db.set_value("Tenant", slug, "press_plan", wanted, update_modified=False)
	_event(slug, "Plan Changed", f"database limit {cint(tenant.database_limit) // GB} GB on {wanted}")
	return wanted


def nightly() -> None:
	"""Move any site whose last move was refused or could not be asked."""
	if not site.is_admin():
		return
	for slug in frappe.get_all("Tenant", filters={"status": ["in", ("Live", "Overdue")]}, pluck="name"):
		try:
			move(slug)
		except Exception:
			frappe.log_error(title=f"Moving {slug} to its plan")
		frappe.db.commit()


def _event(slug: str, kind: str, detail: str) -> None:
	frappe.get_doc({"doctype": "Tenant Event", "tenant": slug, "kind": kind, "detail": detail}).insert(
		ignore_permissions=True
	)


def _doc(tenant):
	return frappe.get_doc("Tenant", tenant) if isinstance(tenant, str) else tenant
