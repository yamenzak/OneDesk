"""A person's own address sends as well as receives now, unless a workspace
administrator turns that off in OneMail's settings (holders.set_personal_sends).
Addresses made while they only received are brought in line."""

import frappe


def execute():
	if frappe.db.get_default("one_mail_personal_sends") == "0":
		return
	for name in frappe.get_all("Email Account", filters={"one_hosted": 1, "one_shared": 0, "enable_outgoing": 0}, pluck="name"):
		frappe.db.set_value("Email Account", name, "enable_outgoing", 1, update_modified=False)
