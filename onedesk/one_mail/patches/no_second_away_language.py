"""An out-of-office reply has no second language: whoever wants one writes it
in the message."""

import frappe


def execute():
	frappe.delete_doc_if_exists("Custom Field", "Email Account-one_away_also")
