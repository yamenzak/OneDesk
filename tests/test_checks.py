"""Whether an extension's code would work (one_studio/checks.py): the names it
uses read against the record's own fields, before OneAI's code is kept. Pure."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from onedesk.one_studio import checks

FIELDS = {
	"Customer": {"customer_name", "customer_type", "mobile_no", "territory", "email_id"},
	"Sales Invoice": {"customer", "grand_total", "status", "items"},
	"Sales Invoice Item": {"item_code", "qty", "rate"},
}


def fields(doctype):
	return FIELDS.get(doctype)


FORM = """frappe.ui.form.on("Customer", {
	refresh(frm) {
		frm.toggle_display(["territory", "email_id"], frm.doc.customer_type === "Company");
	},
	customer_type: function (frm) {
		frm.set_value("territory", "");
	},
	"mobile_no": (frm) => {},
});
frappe.ui.form.on("Sales Invoice Item", {
	qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
	},
	items_add(frm) {},
});"""


def test_server_code_naming_real_fields_passes():
	checks.on_server('if not doc.mobile_no:\n\tfrappe.throw(_("A number, please."))', "Customer", fields)
	checks.on_server(
		'paid = frappe.get_list("Sales Invoice", filters={"customer": doc.name, "docstatus": 1}, '
		'fields=["grand_total"])',
		"Customer",
		fields,
	)


@pytest.mark.parametrize(
	"code, says",
	[
		('if not doc.mobile:\n\tfrappe.throw(_("x"))', "Did you mean mobile_no"),
		('x = doc.get("teritory")', "Did you mean territory"),
		('n = frappe.get_list("Sales Invoice", filters={"cust": doc.name})', "Did you mean customer"),
		('t = frappe.db.get_value("Sales Invoice", "SINV-1", "total")', "Sales Invoice has no field total"),
	],
)
def test_server_code_naming_a_field_that_is_not_there_is_refused_with_the_nearest(code, says):
	with pytest.raises(checks.Refused, match=says):
		checks.on_server(code, "Customer", fields)


def test_a_kind_the_site_cannot_say_is_not_checked():
	checks.on_server('x = frappe.get_list("Unknown Kind", fields=["anything"])', "Customer", fields)


def test_a_form_naming_real_fields_and_events_passes():
	checks.on_screen(FORM, "Customer", "Form", fields)


@pytest.mark.parametrize(
	"wrong, right, says",
	[
		("refresh(frm)", "refesh(frm)", "handles refesh on Customer, which frappe never calls"),
		("frm.doc.customer_type", "frm.doc.type", "uses frm.doc.type"),
		('"email_id"]', '"email"]', "Did you mean email_id"),
		('set_value("territory"', 'set_value("teritory"', "Did you mean territory"),
		("qty(frm, cdt, cdn)", "quantity(frm, cdt, cdn)", "handles quantity on Sales Invoice Item"),
	],
)
def test_a_form_naming_what_is_not_there_is_refused(wrong, right, says):
	with pytest.raises(checks.Refused, match=says):
		checks.on_screen(FORM.replace(wrong, right), "Customer", "Form", fields)


def test_strings_and_comments_are_not_read_as_handlers():
	code = """frappe.ui.form.on("Customer", {
	// territory_note: not a handler
	refresh(frm) {
		frm.set_intro("label: nothing", "blue");
	},
});"""
	checks.on_screen(code, "Customer", "Form", fields)


def test_code_longer_than_one_change_is_refused():
	checks.length("x = 1\n" * checks.LONGEST)
	with pytest.raises(checks.Refused, match="Write the shortest code"):
		checks.length("x = 1\n" * (checks.LONGEST + 1))
