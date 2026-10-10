"""Timesheets made before One filled their title are named by it, so
ERPNext's Profit on Billed Hours says whose time each one is
(one_hr/timesheet.py `title`)."""

import frappe


def execute():
	frappe.db.sql(
		"""update `tabTimesheet` t join `tabEmployee` e on e.name = t.employee
		set t.title = e.employee_name where ifnull(t.title, '') = ''"""
	)
	frappe.db.sql(
		"""update `tabTimesheet` t join `tabUser` u on u.name = t.owner
		set t.title = u.full_name where ifnull(t.title, '') = '' and ifnull(t.employee, '') = ''"""
	)
