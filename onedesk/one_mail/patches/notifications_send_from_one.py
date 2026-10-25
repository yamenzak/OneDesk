"""Setting a shared mailbox as the workspace's, and restoring the workspace
address, used to make that mailbox frappe's `default_outgoing`, so every
notification went out from the customer's own address. The mailbox chosen
is now the workspace's Default Outgoing (holders.SENDS_FROM), and frappe's
default goes back to One's own sender where the workspace has one."""

import frappe


def execute():
	from onedesk.one_mail import holders

	ours = frappe.get_all(
		"Email Account",
		filters={"enable_outgoing": 1, "one_hosted": 0, "one_connected": 0},
		pluck="name",
	)
	if len(ours) != 1:
		return
	held = frappe.get_all(
		"Email Account", filters={"default_outgoing": 1, "name": ["!=", ours[0]]}, fields=["name", "one_shared"]
	)
	for one in held:
		if one.one_shared and not frappe.db.get_default(holders.SENDS_FROM):
			frappe.db.set_default(holders.SENDS_FROM, one.name)
		frappe.db.set_value("Email Account", one.name, "default_outgoing", 0, update_modified=False)
	if held:
		frappe.db.set_value("Email Account", ours[0], "default_outgoing", 1, update_modified=False)
