"""What will fail the first time somebody invoices, is paid or pays, with the
fix beside it. The checks are one_book/ready.py's."""

from frappe import _

from onedesk.one_book import ready


def execute(filters=None):
	return columns(), ready.checks()


def columns() -> list[dict]:
	return [
		{"fieldname": "check", "label": _("Check"), "fieldtype": "Data", "width": 300},
		{"fieldname": "state", "label": _("State"), "fieldtype": "Data", "width": 110},
		{"fieldname": "says", "label": _("What It Means"), "fieldtype": "Data", "width": 520},
		{"fieldname": "fix", "label": _("Fix"), "fieldtype": "Data", "width": 150},
	]
