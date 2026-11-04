"""A screen already quiet when OneDisplay began keeping who was told on the
screen itself was told before, in the cache: it is marked told, so the
change does not tell everybody again."""

import frappe
from frappe.utils import add_to_date, now_datetime

from onedesk.one_display.tell import SILENT


def execute():
	since = add_to_date(now_datetime(), minutes=-SILENT)
	for screen in frappe.get_all(
		"Display Screen", filters=[["status", "=", "Paired"], ["last_seen", "is", "set"], ["last_seen", "<", since]], fields=["name", "last_seen"]
	):
		frappe.db.set_value("Display Screen", screen.name, "offline_told", screen.last_seen, update_modified=False)
