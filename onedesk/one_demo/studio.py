"""OneStudio: the company's vans as a record type of its own, kept in
OneInventory, and two extensions, one on the screen that is on and has run
into an error in somebody's browser, one on the server kept off. Each made
as the owner's approved card makes it."""

from unittest import mock

import frappe

from onedesk.one_demo.base import as_user, tag
from onedesk.one_demo.people import OWNER

VAN = "Company Van"

#: label, fieldtype, options
FIELDS = (
	("Plate", "Data", None),
	("Make", "Data", None),
	("Driver", "Link", "Employee"),
	("Mileage", "Int", None),
	("Next Service", "Date", None),
)

#: plate, make, driver's name, mileage
VANS = (
	("D 41257", "Toyota Hiace", "Tariq Haidar", 84200),
	("D 77310", "Nissan Urvan", "Nadia Khoury", 23950),
)

#: title, runs, record, view or event, explanation, code
EXTENSIONS = (
	(
		"Say When a Customer Has No Mobile",
		"On Screen",
		"Customer",
		"Form",
		"Shows a note on a customer's form when no mobile number is kept for them.",
		"frappe.ui.form.on('Customer', {\n\trefresh(frm) {\n\t\tif (!frm.doc.mobile_no) frm.dashboard.set_headline(__('No mobile number yet.'));\n\t}\n});\n",
	),
	(
		"A Lead Needs a Mobile Number",
		"On Server",
		"Lead",
		"Before Save",
		"Refuses to save a lead with neither a mobile number nor an email address.",
		"if not doc.mobile_no and not doc.email_id:\n\tfrappe.throw('Give the lead a mobile number or an email address.')\n",
	),
)


def run(password=None):
	from onedesk.one_ai import proposals
	from onedesk.one_studio import ai, extensions, record_types, review

	with as_user(OWNER):
		if not frappe.db.exists(record_types.RECORD_TYPE, {"record_doctype": VAN}):
			card = ai.design_record_type(
				VAN,
				"OneInventory",
				"A van the company owns, who drives it and when it is next serviced.",
				[
					{"label": label, "fieldtype": kind, **({"options": options} if options else {}), "in_list_view": 1}
					for label, kind, options in FIELDS
				],
				"Keep our vans, who drives each one and when it is next serviced.",
			)
			proposals.apply(card["proposal"])
		for plate, make, driver, mileage in VANS:
			if frappe.db.exists(VAN, {"plate": plate}):
				continue
			tag(
				frappe.get_doc(
					{
						"doctype": VAN,
						"plate": plate,
						"make": make,
						"driver": frappe.db.get_value("Employee", {"employee_name": driver}),
						"mileage": mileage,
					}
				).insert()
			)
		# The second reading is a model's. The demo is built without one, so
		# it reads as passed, as it did for these when they were written.
		passed = {"verdict": "Pass", "why": "Does what it says and nothing more."}
		with mock.patch.object(review, "ask", return_value=passed):
			for title, runs, record, when, explanation, code in EXTENSIONS:
				if frappe.db.exists(extensions.EXTENSION, {"title": title}):
					continue
				on_screen = runs == extensions.ON_SCREEN
				kept = extensions.write(
					title=title,
					runs=runs,
					doctype=record,
					explanation=explanation,
					code=code,
					asked=explanation,
					view=when if on_screen else None,
					event=None if on_screen else when,
				)
				if on_screen:
					ai.turn_on({"extension": kept["extension"], "state": extensions.reviewed_as(frappe.get_doc(extensions.EXTENSION, kept["extension"]))})
	screen = frappe.db.get_value(extensions.EXTENSION, {"title": EXTENSIONS[0][0]})
	with as_user("omar@one.test"):
		customer = frappe.get_all("Customer", pluck="name", limit=1)[0]
		extensions.tripped(screen, "Cannot read properties of undefined (reading 'set_headline')", "at refresh (extension.js:3)", customer)
