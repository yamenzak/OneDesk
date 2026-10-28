import frappe
from frappe.utils import add_days


def execute():
	"""Every announcement has a Show Until, one posted without one running a
	week from when it was posted, and a Status, Showing or Ended, by it."""
	from onedesk.one.announcements import FRESH_DAYS, ended

	for one in frappe.get_all("Note", filters={"public": 1, "expire_notification_on": ["is", "not set"]}, fields=["name", "creation"]):
		frappe.db.set_value("Note", one.name, "expire_notification_on", add_days(one.creation, FRESH_DAYS), update_modified=False)
	frappe.db.set_value("Note", {"public": 1}, "one_status", "Showing", update_modified=False)
	ended()
