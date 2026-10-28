"""Start Again, in One's ControlCenter › Company: ERPNext's Transaction
Deletion Record, for a workspace that tried One with made-up records.

ERPNext asks for its System Manager at every step, the operator's role, so
the record is made and submitted as Administrator once the workspace
administrator is checked; its jobs then run as Administrator too. Who
started it is written on the record.
"""

import frappe
from frappe import _

from onedesk.one import roles

DOCTYPE = "Transaction Deletion Record"


def planned(company: str):
	"""The record saved with what it will delete. ERPNext's list leaves out
	what is in its ignored table, which its own validate fills, so customers,
	accounts and employees stay off the list."""
	doc = frappe.new_doc(DOCTYPE)
	doc.company = company
	doc.insert()
	doc.generate_to_delete_list()
	return doc


@frappe.whitelist(methods=["POST"])
def start() -> str:
	"""Every transaction of the company deleted, in the background."""
	roles.require()
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw(_("There is no company to start again."))
	who = frappe.session.user
	frappe.set_user("Administrator")
	try:
		doc = planned(company)
		doc.submit()
		doc.add_comment("Info", _("Started by {0} from Workspace Settings.").format(frappe.utils.get_fullname(who)))
	finally:
		frappe.set_user(who)
	return doc.name
