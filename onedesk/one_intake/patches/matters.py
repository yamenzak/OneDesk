"""Readings understood before matters existed start a matter each, name their
party, and count as acted on: they were filed then, or came before filing did."""

import frappe


def execute():
	frappe.db.sql(
		"""update `tabReading` set matter = name, `change` = 'New', matter_state = 'Open',
		acted_on = coalesce(understood_on, modified)
		where state = 'Understood' and ifnull(matter, '') = ''"""
	)
	from onedesk.one_intake import filing

	for name in frappe.get_all("Reading", filters={"state": "Understood", "party_name": ["is", "not set"]}, pluck="name"):
		rows = frappe.get_all("Reading Party", filters={"parent": name}, fields=["role", "matched_doctype", "matched_name", "score", "ours"])
		belongs = filing.records([dict(row) for row in rows])
		if belongs:
			frappe.db.set_value("Reading", name, {"party_doctype": belongs[0][0], "party_name": belongs[0][1]}, update_modified=False)
