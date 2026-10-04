"""A project run by Administrator is run by nobody (members.py `nobody`):
the field defaulted to whoever made the project, and a script made some."""

import frappe


def execute():
	frappe.db.sql(
		"update `tabProject` set one_manager = null where one_manager in ('Administrator', 'Guest')"
	)
