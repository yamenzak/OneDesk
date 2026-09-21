"""Settling something the clock proposed.

`healing.networks` and `healing.zones` write a `Clock Network` or a `Clock
Place` as Proposed on the first corroborated sighting and promote it to
Confirmed once enough employees agree. The two states a person decides between
are the same on both doctypes, so the verbs are here rather than twice.

Status is read only on those records. It was a dropdown, which made rejecting
a proposal look like picking a value from a list, and let somebody set a
rejected address back to Confirmed without saying why. A rejection is final in
the sense that matters: `healing._learn` matches a Rejected row like any other
and never promotes it again.
"""

import frappe
from frappe import _

#: The doctypes the learner writes. Nothing else may be settled through here.
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
