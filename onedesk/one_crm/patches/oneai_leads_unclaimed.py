"""A lead OneAI made while reading mail was its own, so nobody saw it to take
and Lead Owner Efficiency counted OneAI as a salesperson. Like a lead from the
website, it is everybody's to take (`capture.before_insert`)."""

import frappe

from onedesk.one.notify import ONEAI


def execute():
	frappe.db.set_value("Lead", {"lead_owner": ONEAI}, "lead_owner", None, update_modified=False)
