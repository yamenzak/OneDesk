"""A passkey is its person's rather than its employee's, so an administrator
or anybody else without an employee record can have one. Every row made so
far was an employee's; their login is filled in from it. And passkey sign-in
is on, since it is now the way in that the login page leads with."""

import frappe


def execute():
	frappe.db.sql(
		"""update `tabClock Device` d join `tabEmployee` e on e.name = d.employee
		set d.user = e.user_id
		where ifnull(d.user, '') = '' and ifnull(e.user_id, '') != ''"""
	)
	if frappe.get_meta("System Settings").has_field("one_login_with_passkey"):
		frappe.db.set_single_value("System Settings", "one_login_with_passkey", 1)
