"""Buying credits, and the ones a plan promises every month.

Both write one `Credit Ledger Entry` through `ledger.grant`, with an
idempotency key. Packs rather than amounts; a plan's monthly credit does not
roll over.
"""

import frappe
from frappe.utils import get_first_day, get_last_day, getdate

from onedesk.one_admin import ledger, site, stripe
from onedesk.one_admin.faults import Refused

GRANTED_ON = ("Live", "Overdue")


def packs() -> list[dict]:
	"""The credit packs on sale, cheapest first."""
	return frappe.get_all(
		"Offering",
		filters={"kind": "Credit Pack", "enabled": 1},
		fields=["name", "label", "description", "currency", "amount", "credits"],
		order_by="amount asc",
	)


def buy(tenant: str, pack: str) -> dict:
	"""Somewhere for this workspace to pay for this pack."""
	site.require_admin()
	sold = frappe.db.get_value(
		"Offering", pack, ["name", "kind", "enabled", "credits"], as_dict=True
	)
	if not sold or sold.kind != "Credit Pack" or not sold.enabled:
		raise Refused(f"{pack} is not a credit pack on sale")
	return {"pay_at": stripe.checkout_for_credits(tenant, sold.name), "credits": sold.credits}


def bought(session: dict) -> str | None:
	"""A completed checkout that was a pack. Writes the grant, once.

	Called from the webhook, which Stripe delivers more than once by design. The
	key is the session's own id, so the second delivery finds the first
	delivery's entry and returns it rather than granting again.
	"""
	site.require_admin()
	meta = session.get("metadata") or {}
	tenant, pack = meta.get("tenant"), meta.get("pack")
	if not tenant or not pack:
		return None

	credits = frappe.db.get_value("Offering", pack, "credits")
	if not credits:
		raise Refused(f"{pack} grants no credits")
	return ledger.grant(
		tenant,
		credits,
		"Purchase",
		reference=session.get("id"),
		key=f"stripe:{session.get('id')}",
		why=frappe.db.get_value("Offering", pack, "label"),
	)


def monthly() -> None:
	"""The credit every plan promises, granted once a month and never twice.

	Run nightly rather than on the first of the month, so a workspace built on
	the twelfth has its credit that night instead of waiting nineteen days. The
	key carries the month, which is what makes running it every night harmless.
	"""
	for row in frappe.get_all(
		"Tenant", filters={"status": ["in", GRANTED_ON]}, fields=["name", "offering"]
	):
		if not row.offering:
			continue
		try:
			allowance(row.name, row.offering)
		except Exception:
			frappe.log_error(f"monthly credits: {row.name}")


def allowance(tenant: str, offering: str, on=None) -> str | None:
	"""One workspace's credit for the month that `on` falls in: the plan's,
	and any monthly credits added to it (quota.py)."""
	credits = frappe.db.get_value("Tenant", tenant, "credits_a_month") or frappe.db.get_value(
		"Offering", offering, "credits_a_month"
	)
	if not credits:
		return None

	day = getdate(on)
	return ledger.grant(
		tenant,
		credits,
		"Plan",
		reference=offering,
		expires_on=get_last_day(day),
		key=f"plan:{tenant}:{get_first_day(day):%Y-%m}",
		why=frappe._("Monthly credit for {0}").format(frappe.utils.formatdate(day, "MMMM yyyy")),
	)
