"""A workspace changing what it pays for: its plan, and the add-ons on it.

Everything here is asked by the workspace through the proxy and answered by
the calculator (plans.py), so the customer and the operator see the same
arithmetic: what the workspace has now, what each plan with the cheapest
add-ons on top would cost for what it needs, and taking one of those.

**Taking an option sets the whole shape.** An option is a plan and the
add-ons that bring it up to a need, so taking it makes the subscription
exactly that: the plan swapped if it differs, each add-on set to its count,
and add-ons the option does not have taken off. Stripe prorates each change
and charges the difference now; a declined card refuses the change before
anything here is written (stripe.PRORATED).

**Nothing goes below what is used.** A smaller plan, or an add-on taken
off, that would leave the workspace over its seats, its storage or its
database is refused with what to clear first, because the alternative is a
workspace that cannot save anything the moment the change lands.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from onedesk.one_admin import offerings, plans, quota, site, stripe
from onedesk.one_admin.faults import Refused

GB = quota.GB


def offered(tenant: str, seats_used: int = 0) -> dict:
	"""What the workspace has, and what it could have instead."""
	site.require_admin()
	held = frappe.get_doc("Tenant", tenant)
	ladder, sold, _costs = offerings.listed()
	return {
		"currency": offerings.currency(),
		"plan": held.offering,
		"add_ons": {row.offering: cint(row.quantity) for row in held.add_ons},
		"monthly": monthly(held),
		"used": _used(held, seats_used),
		"plans": [_offer(one) for one in sorted(ladder, key=lambda one: one.price)],
		"add_ons_sold": [_offer(one) for one in sold if one.kind == "Add-on"],
	}


def quote(tenant: str, needs: dict, seats_used: int = 0) -> dict:
	"""Every way to have `needs` in all, cheapest first, and what it costs
	against what the workspace pays now."""
	site.require_admin()
	held = frappe.get_doc("Tenant", tenant)
	ladder, sold, _costs = offerings.listed()
	used = _used(held, seats_used)
	# Never quote less than what is already used: a need below it is a need
	# nobody can have without deleting something first.
	wanted = {one: max(flt(needs.get(one)), used.get(one) or 0) for one in plans.RESOURCES}
	now = monthly(held)
	return {
		"now": now,
		"currency": offerings.currency(),
		"options": [
			{
				"plan": option.plan.key,
				"label": option.plan.label,
				"extras": [{"offering": one.key, "label": one.label, "count": count, "price": one.price} for one, count in option.extras],
				"monthly": option.monthly,
				"change": round(option.monthly - now, 2),
				"current": option.plan.key == held.offering and _same(held, option),
			}
			for option in plans.quote(wanted, ladder, [one for one in sold if one.kind == "Add-on"])
			if not option.unmet
		],
	}


def take(tenant: str, plan: str, extras: dict, seats_used: int = 0) -> dict:
	"""Make the subscription this plan with exactly these add-ons."""
	site.require_admin()
	held = frappe.get_doc("Tenant", tenant)
	extras = {key: cint(count) for key, count in (extras or {}).items() if cint(count) > 0}
	_check_sold(plan, extras)
	_check_room(held, plan, extras, seats_used)
	if not held.stripe_subscription:
		raise Refused(_("This workspace has no subscription to change. Ask us to set one up."))

	was = held.offering
	# Each change is written as Stripe accepts it, so a card declined half way
	# leaves this record saying what Stripe now bills, not what was asked.
	try:
		if plan != held.offering:
			old_price = frappe.db.get_value("Offering", held.offering, "stripe_price") if held.offering else None
			stripe.swap_plan(held.stripe_subscription, old_price, stripe.price_for(plan))
			held.offering = plan

		rows = {row.offering: row for row in held.add_ons}
		for key in sorted(set(rows) | set(extras)):
			row = rows.get(key)
			want = extras.get(key, 0)
			if row and cint(row.quantity) == want:
				continue
			item = stripe.set_item(
				held.stripe_subscription,
				row.stripe_item if row else None,
				stripe.price_for(key) if want else None,
				want,
			)
			if want:
				if not row:
					row = held.append("add_ons", {"offering": key})
				row.quantity, row.stripe_item = want, item
			elif row:
				held.remove(row)
	finally:
		held.flags.ignore_links = True
		held.save(ignore_permissions=True)
		limits = quota.apply(held)
	_log(held.name, "Plan Changed" if plan != was else "Add-on Changed", plan, extras)
	return {
		"plan": plan,
		"add_ons": extras,
		"limits": limits,
		"monthly": monthly(frappe.get_doc("Tenant", held.name)),
		"currency": offerings.currency(),
	}


def set_add_on(tenant: str, offering: str, quantity: int, seats_used: int = 0) -> dict:
	"""One add-on to this many, the rest as they are."""
	held = frappe.get_doc("Tenant", tenant)
	extras = {row.offering: cint(row.quantity) for row in held.add_ons}
	extras[offering] = cint(quantity)
	return take(tenant, held.offering, extras, seats_used)


def monthly(held) -> float:
	"""What the workspace pays a month: its plan and its add-ons."""
	price = flt(frappe.db.get_value("Offering", held.offering, "amount")) if held.offering else 0
	for row in held.add_ons:
		price += flt(frappe.db.get_value("Offering", row.offering, "amount")) * max(1, cint(row.quantity))
	return round(price, 2)


def _used(held, seats_used: int) -> dict:
	return {
		"seats": cint(seats_used),
		"storage_gb": flt(held.storage_bytes) / GB,
		"database_gb": flt(held.database_bytes) / GB,
		"credits_a_month": 0,
	}


def _check_sold(plan: str, extras: dict) -> None:
	on_sale = frappe.db.get_value("Offering", plan, ["kind", "enabled"], as_dict=True)
	if not on_sale or on_sale.kind != "Plan" or not on_sale.enabled:
		raise Refused(_("{0} is not a plan on sale.").format(plan))
	for key in extras:
		one = frappe.db.get_value("Offering", key, ["kind", "enabled"], as_dict=True)
		if not one or one.kind != "Add-on" or not one.enabled:
			raise Refused(_("{0} is not an add-on on sale.").format(key))


def _check_room(held, plan: str, extras: dict, seats_used: int) -> None:
	"""Refuse a shape that leaves the workspace over what it already uses."""
	shape = frappe._dict(offering=plan, add_ons=[frappe._dict(offering=key, quantity=count) for key, count in extras.items()])
	after = quota.limits(shape)
	used = _used(held, seats_used)
	over = []
	if after["seats"] is not None and used["seats"] > after["seats"]:
		over.append(_("{0} people have seats and it allows {1}. Turn somebody off first.").format(used["seats"], after["seats"]))
	if after["storage_gb"] is not None and used["storage_gb"] > after["storage_gb"]:
		over.append(_("Files take {0} GB and it allows {1} GB.").format(round(used["storage_gb"], 1), after["storage_gb"]))
	if after["database_gb"] is not None and used["database_gb"] > after["database_gb"]:
		over.append(_("The database takes {0} GB and it allows {1} GB.").format(round(used["database_gb"], 1), after["database_gb"]))
	if over:
		raise Refused(" ".join(over))


def _same(held, option) -> bool:
	have = {row.offering: cint(row.quantity) for row in held.add_ons}
	return have == {one.key: count for one, count in option.extras}


def _offer(one) -> dict:
	return {
		"key": one.key,
		"label": one.label,
		"price": one.price,
		**{resource: (None if one.quota(resource) == plans.INF else one.quota(resource)) for resource in plans.RESOURCES},
	}


def _log(slug: str, kind: str, plan: str, extras: dict) -> None:
	detail = plan + (" with " + ", ".join(f"{count} × {key}" for key, count in extras.items()) if extras else "")
	frappe.get_doc({"doctype": "Tenant Event", "tenant": slug, "kind": kind, "detail": detail}).insert(
		ignore_permissions=True
	)


# ------------------------------------------------------------------ invoices


def invoices(tenant: str) -> dict:
	"""The workspace's Stripe invoices, newest first, as its own screen lists
	them, and who they are from."""
	site.require_admin()
	customer = frappe.db.get_value("Tenant", tenant, "stripe_customer")
	if not customer:
		return {"invoices": [], "seller": seller()}
	found = stripe.fetch("invoices", {"customer": customer, "limit": 24}).get("data") or []
	return {"invoices": [_said(one) for one in found if one.get("status") != "draft"], "seller": seller()}


def invoice(tenant: str, invoice_id: str) -> dict:
	"""One of the workspace's invoices with its lines, for its own books.
	Refused when it is another customer's."""
	site.require_admin()
	held = stripe.fetch(f"invoices/{invoice_id}")
	if held.get("customer") != frappe.db.get_value("Tenant", tenant, "stripe_customer"):
		raise Refused(_("That is not one of this workspace's invoices."))
	said = _said(held)
	said["lines"] = [
		{
			"description": line.get("description") or "",
			"quantity": max(1, int(line.get("quantity") or 1)),
			"amount": flt(line.get("amount")) / 100,
			"offering": ((line.get("price") or {}).get("metadata") or {}).get("offering"),
		}
		for line in (held.get("lines") or {}).get("data") or []
	]
	said["seller"] = seller()
	return said


def portal(tenant: str, back: str) -> str:
	"""Stripe's billing portal for the workspace: its card, its billing
	address, its receipts. Stripe draws it; we only open it."""
	site.require_admin()
	customer = frappe.db.get_value("Tenant", tenant, "stripe_customer")
	if not customer:
		raise Refused(_("This workspace has no billing account yet."))
	return stripe.portal(customer, back)


def seller() -> dict:
	"""Who the invoices are from, as a workspace's books name a supplier: the
	admin site's company, with what OneIntake recognises it by."""
	from onedesk.one_admin import books

	held = frappe.db.get_value(
		"Company", books.company(), ["company_name", "tax_id", "website", "email", "phone_no"], as_dict=True
	) or {}
	return {key: value for key, value in held.items() if value}


def _said(one: dict) -> dict:
	return {
		"id": one.get("id"),
		"number": one.get("number") or one.get("id"),
		"created": one.get("created"),
		"currency": (one.get("currency") or "usd").upper(),
		"total": flt(one.get("total")) / 100,
		"paid": flt(one.get("amount_paid")) / 100,
		"status": one.get("status"),
		"page": one.get("hosted_invoice_url"),
		"pdf": one.get("invoice_pdf"),
	}
