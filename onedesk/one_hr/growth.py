"""Two things the appraisal machinery expects somebody to do by hand."""

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
