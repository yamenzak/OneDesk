"""A maintenance visit is titled with the visit and the customer
(one_calendar/events.py `maintenance_visit`). The visits booked before are
titled once."""

import frappe


def execute():
	from onedesk.one_calendar.events import maintenance_visit

	booked = frappe.get_all("Event Participants", filters={"reference_doctype": "Maintenance Schedule", "parenttype": "Event"}, pluck="parent")
	for name in set(booked):
		doc = frappe.get_doc("Event", name)
		if maintenance_visit(doc):
			frappe.db.set_value("Event", name, {"subject": doc.subject, "description": doc.description}, update_modified=False)
