"""An offering's `gives` line and `sort_key`, for the price list written
before them. Written straight to the row: saving would re-sync its Item and,
on a changed price, drop its Stripe price, neither of which is wanted here."""

import frappe

from onedesk.one_admin.doctype.offering.offering import RANK, gives


def execute():
	for name in frappe.get_all("Offering", pluck="name"):
		held = frappe.get_doc("Offering", name)
		frappe.db.set_value(
			"Offering",
			name,
			{"gives": gives(held), "sort_key": RANK.get(held.kind, 9) * 1_000_000 + (held.amount or 0)},
			update_modified=False,
		)
