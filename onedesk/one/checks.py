"""One's part of the integration suite (one_demo/check.py runs it): its
roles, and the Recycle Bin's Everyone's Deletions."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import check


@check
def one_manager_sees_what_anybody_deleted():
	"""One's roles are made from its abilities.py (rights.settle) and its User
	role is everybody's. Nadia sees only what she deleted herself; given One
	Manager, which holds Everyone's Deletions, she sees what others deleted
	too, and still can't empty the bin for good."""
	from onedesk.one import recycle

	assert frappe.db.exists("Role", "One User") and frappe.db.exists("Role", "One Manager")
	assert "One User" in frappe.get_roles("nadia@one.test")
	others = frappe.db.get_value("Deleted Document", {"owner": ("not in", ("nadia@one.test", "Administrator", "Guest"))}, "name")
	assert others, "the demo has nothing deleted by anybody but Nadia"
	with as_user("nadia@one.test"):
		assert "nadia@one.test" in (recycle.query() or "") and not recycle._everyone("nadia@one.test")
	user = frappe.get_doc("User", "nadia@one.test")
	user.add_roles("One Manager")
	try:
		with as_user("nadia@one.test"):
			assert recycle._everyone("nadia@one.test"), "One Manager does not hold Everyone's Deletions"
			doc = frappe.get_doc("Deleted Document", others)
			assert recycle.has_permission(doc, "read", "nadia@one.test") or doc.deleted_doctype not in recycle._kinds("nadia@one.test")
			assert not recycle.has_permission(doc, "delete", "nadia@one.test"), "only an administrator empties the bin"
	finally:
		user.remove_roles("One Manager")
