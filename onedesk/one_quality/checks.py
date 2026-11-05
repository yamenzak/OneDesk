"""OneQuality's part of the integration suite (one_demo/check.py runs it):
procedures, goals, problems and their actions, as the people in quality
read them, and its one ability."""

import frappe

from onedesk.one_demo.check import _Told, check
from onedesk.one_demo.quality import PROCEDURE


@check
def onequality_a_problem_is_raised_told_and_resolved():
	"""Tariq, who uses OneQuality, reads the curtain wall's procedure and
	raises a non conformance against it; Karim, who manages quality, is told,
	and only he may set it to Resolved. Anybody may report a problem, as
	ERPNext lets every employee, but nobody outside quality resolves one or
	changes a procedure."""
	from onedesk.one_demo.base import as_user
	from onedesk.one_quality import resolve

	with as_user("tariq@one.test"):
		assert frappe.has_permission("Quality Procedure", "read", doc=PROCEDURE)
		assert frappe.has_permission("Quality Action", "write") and not resolve.held()
		with _Told() as told:
			raised = frappe.get_doc(
				{"doctype": "Non Conformance", "subject": "Cover caps fitted before the sealant cured", "procedure": PROCEDURE, "status": "Open"}
			).insert()
		managers = told.to("Non Conformance Raised")
		assert "karim@one.test" in managers and "tariq@one.test" not in managers and "Administrator" not in managers, managers
		raised.status = "Resolved"
		try:
			raised.save()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a quality user resolved a non conformance")
	with as_user("karim@one.test"):
		assert resolve.held()
		done = frappe.get_doc("Non Conformance", raised.name)
		done.status = "Resolved"
		done.save()
	with as_user("nadia@one.test"):
		assert frappe.has_permission("Non Conformance", "create"), "anybody may report a problem"
		assert not resolve.held() and not frappe.has_permission("Quality Procedure", "write")
