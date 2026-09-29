"""A model's place on the list, for the rows written before it had one."""

import frappe

from onedesk.one_admin.doctype.ai_model.ai_model import rank


def execute():
	for one in frappe.get_all("AI Model", fields=["name", "offered", "status"]):
		frappe.db.set_value("AI Model", one.name, "rank", rank(one), update_modified=False)
