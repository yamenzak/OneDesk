import frappe


def execute():
	"""Announcements run along the top bar, so none also pops up at sign-in."""
	frappe.db.set_value("Note", {"notify_on_login": 1}, {"notify_on_login": 0, "notify_on_every_login": 0}, update_modified=False)
