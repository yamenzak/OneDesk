"""Who may resolve a non conformance: OneQuality's Resolve Non Conformances
(access.py)."""

import frappe
from frappe import _

from onedesk.one import rights


def held(user: str | None = None) -> bool:
	return rights.may("Non Conformance", "quality_resolve", user=user)


def guard(doc, method=None) -> None:
	"""Non Conformance validate: setting it to Resolved takes the ability."""
	if doc.status != "Resolved" or (not doc.is_new() and doc.get_db_value("status") == "Resolved"):
		return
	if not held():
		frappe.throw(_("Your role doesn't allow resolving a non conformance."), frappe.PermissionError)
