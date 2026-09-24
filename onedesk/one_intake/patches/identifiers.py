"""Every existing record's identifiers, read once in the background."""

import frappe


def execute():
	frappe.enqueue("onedesk.one_intake.identity.remember_all", queue="long", enqueue_after_commit=True)
