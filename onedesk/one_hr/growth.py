"""Two things the appraisal machinery expects somebody to do by hand.

**A cycle nobody set to In Progress is invisible to its own summary.** An
Appraisal Cycle is born `Not Started`, and the only thing in HRMS that ever
changes that is `complete_cycle`, which sets `Completed`. Nothing sets
`In Progress`. But the summary the cycle screen shows is looked up by it:

	if not cycle_name:
		cycle_name = frappe.get_value(
			"Appraisal Cycle", {"status": "In Progress"}, order_by="start_date desc"
		)

So "employees without feedback" is counted against no cycle at all until
somebody notices the dropdown and changes it. Creating appraisals for a cycle is
the moment it starts, so that is where the status moves.

**An appraisal has no period, so its duplicate check has nothing to compare.**
`validate_duplicate` looks for another appraisal for the same person either in
the same cycle *or* over an overlapping period:

	(Appraisal.appraisal_cycle == self.appraisal_cycle)
	| ((Appraisal.start_date.between(self.start_date, self.end_date)) | ...)

Nothing in HRMS ever fills `start_date` or `end_date` on an Appraisal — not
`create_appraisals_for_cycle`, not the form script — so every comparison in the
second half is against NULL, which is never true. Only the cycle branch ever
fires, and two appraisals for one person in two different cycles covering the
same months go through. The cycle knows the dates, so the appraisal takes them.

**A promotion says who and when and nothing about what changed.** The new
designation lives in a `promotion_details` row, which is a child table and so
cannot be a list column and cannot be searched. `one_becomes` is that row's
`new` value, kept on the document, so the list can say `Engineer → Senior
Engineer` and a filter can find every promotion into one grade.
"""

import frappe

#: The only property whose change is worth saying on the list. Grade and
#: department changes travel with it; the designation is the one people mean.
PROMOTED_TO = "Designation"


def cycle_under_way(doc, method=None) -> None:
	"""An appraisal exists, so its cycle has started."""
	if not doc.appraisal_cycle:
		return
	if frappe.db.get_value("Appraisal Cycle", doc.appraisal_cycle, "status") != "Not Started":
		return
	frappe.db.set_value("Appraisal Cycle", doc.appraisal_cycle, "status", "In Progress")


def appraisal_period(doc, method=None) -> None:
	"""The cycle's dates, on the appraisal, before its own duplicate check reads them."""
	if not doc.appraisal_cycle or (doc.start_date and doc.end_date):
		return
	cycle = frappe.db.get_value(
		"Appraisal Cycle", doc.appraisal_cycle, ["start_date", "end_date"], as_dict=True
	)
	if not cycle:
		return
	doc.start_date = doc.start_date or cycle.start_date
	doc.end_date = doc.end_date or cycle.end_date


def promotion(doc, method=None) -> None:
	"""Carry the new designation up onto the document."""
	doc.one_becomes = ""
	for row in doc.promotion_details or []:
		if row.property == PROMOTED_TO and row.new:
			doc.one_becomes = row.new
			return
