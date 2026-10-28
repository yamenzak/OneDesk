"""Contact's Portal column (one_portal/gate.py) filled in for every portal
login there already is, which OnePortal's People list is filtered on."""

import frappe

from onedesk.one_portal import gate


def execute():
	for user in frappe.get_all("User", filters={"user_type": "Website User"}, pluck="name"):
		gate.mark(user)
