"""Settling something the clock proposed."""

import frappe
from frappe import _

LEARNED = ("Clock Network", "Clock Place")


def _settle(doctype: str, name: str, status: str) -> None:
	if doctype not in LEARNED:
		frappe.throw(_("{0} is not something the clock proposes.").format(doctype))
	frappe.has_permission(doctype, "write", doc=name, throw=True)

	frappe.db.set_value(doctype, name, "status", status)
	frappe.get_doc(doctype, name).add_comment("Comment", _("Marked {0}.").format(_(status)))


@frappe.whitelist(methods=["POST"])
def confirm(doctype: str, name: str) -> None:
	"""Allow check-ins from it, ahead of the threshold agreeing."""
	_settle(doctype, name, "Confirmed")


@frappe.whitelist(methods=["POST"])
def reject(doctype: str, name: str) -> None:
	"""Refuse it, and stop the learner offering it again."""
	_settle(doctype, name, "Rejected")
