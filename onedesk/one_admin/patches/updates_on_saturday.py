import frappe


def execute():
	"""A workspace made before update windows updates on Saturday at 01:00."""
	frappe.db.sql("update `tabTenant` set update_weekday = 5, update_hour = 1 where update_weekday = 0 and update_hour = 0")
