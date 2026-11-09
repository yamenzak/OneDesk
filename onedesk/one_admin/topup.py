"""Buying credits, and the ones a plan promises every month.

Both write one `Credit Ledger Entry` through `ledger.grant`, with an
idempotency key. Packs rather than amounts; a plan's monthly credit does not
roll over.
"""

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, getdate, today

from onedesk.one_admin import ledger, price_list, site, stripe
from onedesk.one_admin.faults import Again, Refused

GRANTED_ON = ("Live", "Overdue")
MOST_PACKS = 10


def packs() -> list[dict]:
	"""The credit packs on sale, cheapest first."""
	return frappe.get_all(
		"Offering",
		filters={"kind": "Credit Pack", "enabled": 1},
		fields=["name", "label", "description", "currency", "amount", "credits"],
		order_by="amount asc",
	)


def buy(tenant: str, pack: str) -> dict:
	"""A checkout for this workspace to pay for this pack in its own page."""
	site.require_admin()
	sold = frappe.db.get_value(
		"Offering", pack, ["name", "kind", "enabled", "credits"], as_dict=True
	)
	if not sold or sold.kind != "Credit Pack" or not sold.enabled:
		raise Refused(f"{pack} is not a credit pack on sale")
	return {"checkout": stripe.checkout_for_credits(tenant, sold.name), "credits": sold.credits}


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
		expires_on=add_days(today(), price_list.PACK_CREDITS_LAST_DAYS),
	)


def wants_a_pack(on: bool, status: str, balance: float, below: int, bought: int, cap: int) -> bool:
	"""Whether a workspace buys a pack now. Pure."""
	return bool(on) and status == "Live" and bool(below) and balance < below and bought < cap


def after_spend(tenant: str) -> None:
	"""Credits were spent: a pack is queued if the workspace asked for that
	and its balance has fallen under its line."""
	held = frappe.db.get_value("Tenant", tenant, ["auto_topup", "status", "auto_topup_below", "auto_topup_cap"], as_dict=True)
	if held and held.auto_topup and wants_a_pack(True, held.status, ledger.balance(tenant), held.auto_topup_below, ledger.packs_charged_this_month(tenant), held.auto_topup_cap):
		frappe.enqueue("onedesk.one_admin.topup.charge", tenant=tenant, job_id=f"one_auto_topup_{tenant}", deduplicate=True, enqueue_after_commit=True)


def charge(tenant: str) -> str | None:
	"""One pack charged to the saved card and granted. A card that cannot
	pay turns auto top-up off and tells the owner."""
	doc = frappe.get_doc("Tenant", tenant)
	bought = ledger.packs_charged_this_month(tenant)
	if not wants_a_pack(doc.auto_topup, doc.status, ledger.balance(tenant), doc.auto_topup_below, bought, doc.auto_topup_cap):
		return None
	month = today()[:7]
	try:
		paid = stripe.charge_saved_card(doc, doc.auto_topup_pack, f"{tenant}:{month}:{bought + 1}")
	except Again:
		raise
	except Refused:
		frappe.log_error(title=f"Auto top-up of {tenant}")
		paid = None
	if not paid:
		doc.db_set("auto_topup", 0)
		from onedesk.one_admin import tell

		tell.topup_failed(doc)
		return None
	sold = frappe.db.get_value("Offering", doc.auto_topup_pack, ["credits", "label"], as_dict=True)
	return ledger.grant(tenant, sold.credits, "Purchase", reference=paid, key=f"stripe:{paid}", why=sold.label, expires_on=add_days(today(), price_list.PACK_CREDITS_LAST_DAYS))


def settings(tenant) -> dict:
	"""What the account screen shows."""
	return {"enabled": tenant.auto_topup, "pack": tenant.auto_topup_pack, "below": tenant.auto_topup_below, "cap": tenant.auto_topup_cap, "packs": packs(), "card": bool(tenant.stripe_customer)}


def keep_settings(tenant, enabled: int, pack: str, below: int, cap: int) -> dict:
	"""An administrator's choice, checked."""
	if enabled:
		if not frappe.db.exists("Offering", {"name": pack, "kind": "Credit Pack", "enabled": 1}):
			raise Refused(f"{pack} is not a credit pack on sale")
		if not tenant.stripe_customer:
			frappe.throw(frappe._("Add a card first."))
		if below < 1 or not 1 <= cap <= MOST_PACKS:
			frappe.throw(frappe._("Monthly Pack Limit must be between 1 and {0}, and Minimum Balance above 0.").format(MOST_PACKS))
	frappe.db.set_value("Tenant", tenant.name, {"auto_topup": enabled, "auto_topup_pack": pack or None, "auto_topup_below": below, "auto_topup_cap": cap})
	return {"enabled": enabled}


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
