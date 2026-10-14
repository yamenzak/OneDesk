"""A payment to or from somebody is titled by their name (paid.titled). The
payments made before were titled by the party's ID, which for an employee is
HR-EMP-00013."""

import frappe


def execute():
	for one in frappe.get_all(
		"Payment Entry",
		filters={"payment_type": ["in", ["Receive", "Pay"]], "party_name": ["is", "set"]},
		fields=["name", "title", "party", "party_name"],
	):
		if one.title == one.party and one.party_name != one.party:
			frappe.db.set_value("Payment Entry", one.name, "title", one.party_name, update_modified=False)
