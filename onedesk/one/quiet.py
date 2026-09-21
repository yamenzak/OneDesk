"""Telemetry bookkeeping does not belong on somebody's screen.

HRMS counts first-time milestones by inserting a row and letting the unique
index refuse the second attempt:

    with savepoint(catch=Exception):
        frappe.get_doc({"doctype": MILESTONE_DOCTYPE, "event": event}).insert(...)

The savepoint rolls the row back, but the message the failure left behind does
not roll back with it — `frappe.local.message_log` is a list on the request, not
part of the transaction. So from the second leave application onwards, every
person who approves one is told **"HR Telemetry Milestone first_leave_applied
already exists"**, and the same on expense claims, attendance requests, shift
requests, job offers, appraisals, interviews, payroll entries and salary slips.

It is the same shape as the "Duplicate Name" that used to land on top of every
clock-in, which `one_hr/clock.py` handles inside its own endpoint. This is the
general case: hooked on `"*"` for the two events HRMS attaches its telemetry to,
and matching only that doctype's own name, so nothing anybody meant to say is
touched.
"""

import frappe

#: The only thing swept. Matched on the doctype's name rather than on the
#: sentence, because the sentence is translated and the name is not.
MILESTONE = "HR Telemetry Milestone"


def milestone(doc=None, method=None) -> None:
	if not frappe.local.message_log:
		return
	frappe.local.message_log = [
		said for said in frappe.local.message_log if MILESTONE not in str(said)
	]
