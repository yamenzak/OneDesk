"""Who sees and changes an automation: whoever its trigger's app says, as
its own screens said before (Trigger.keeps `allowed` and `query`)."""

import frappe

from onedesk.one.automation import kinds


def allowed(doc, ptype=None, user=None, debug=False) -> bool:
	"""Automation has_permission: the trigger's own answer."""
	if not doc.trigger:
		return True
	return bool(kinds.trigger(doc.trigger).keeper("allowed")(doc, ptype, user))


def query(user=None) -> str:
	"""Automation's query conditions: each trigger's own, on its rows."""
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	said = []
	for one in kinds.triggers():
		own = one.keeper("query")(user)
		said.append(f"(`tabAutomation`.`trigger` = {frappe.db.escape(one.key)}" + (f" and {own})" if own else ")"))
	return "(" + " or ".join(said) + ")" if said else "1=0"
