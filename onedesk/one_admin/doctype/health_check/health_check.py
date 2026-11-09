import frappe
from frappe.model.document import Document


class HealthCheck(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("Health Check", ["service", "checked_at"])
