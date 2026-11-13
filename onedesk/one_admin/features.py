"""What a plan includes beyond its quotas (onedesk/one/registry/features.py),
carried as the quotas are: the price list's plan onto its Offering, the
Offering onto the Tenant when it buys it or changes plan, and the Tenant's
in `proxy.hello`'s answer. Everything that gates on one reads the Tenant's
copy, so a plan declared again never changes what a customer bought."""

import frappe

CHILD = "Plan Feature"
FIELD = "features"


def rows(ids) -> list[dict]:
	"""A Table field's rows for these ids. Pure."""
	return [{"feature": one} for one in ids]


def held(doctype: str, name: str) -> tuple[str, ...]:
	"""The ids an Offering or a Tenant has."""
	return tuple(
		frappe.get_all(CHILD, filters={"parenttype": doctype, "parent": name, "parentfield": FIELD}, pluck="feature", order_by="idx asc")
	)


def write(doctype: str, name: str, ids) -> None:
	"""Make an Offering's or a Tenant's features these, without saving it."""
	if held(doctype, name) == tuple(ids):
		return
	frappe.db.delete(CHILD, {"parenttype": doctype, "parent": name, "parentfield": FIELD})
	for at, one in enumerate(ids, 1):
		frappe.get_doc({"doctype": CHILD, "parenttype": doctype, "parent": name, "parentfield": FIELD, "idx": at, "feature": one}).db_insert()


def of_tenant(tenant) -> tuple[str, ...]:
	"""What a workspace's plan includes."""
	return held("Tenant", tenant if isinstance(tenant, str) else tenant.name)


def copy(tenant: str, offering: str | None) -> None:
	"""The Tenant takes its plan's features, as `quota.apply` takes its limits."""
	write("Tenant", tenant, held("Offering", offering) if offering else ())


def tenants_with(feature: str) -> list[str]:
	"""The Tenants whose plan includes a feature."""
	return sorted(set(frappe.get_all(CHILD, filters={"parenttype": "Tenant", "parentfield": FIELD, "feature": feature}, pluck="parent")))
