"""Telemetry bookkeeping does not belong on somebody's screen.

HRMS's refused first-time milestone leaves "HR Telemetry Milestone ... already
exists" on the request; this takes that message off, and nothing else.
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
