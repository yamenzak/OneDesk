"""A rule's OneAI reply is sent as it is now: there is no Review Before
Sending (rules.answer). A rule whose OneAI reply asked for review was
written to be checked, so it is switched off rather than left to start
sending unchecked; its owner switches it back on."""

import frappe


def execute():
	from onedesk.one.automation import flow

	for name, steps in frappe.get_all("Mail Rule", fields=["name", "steps"], as_list=True):
		said = frappe.parse_json(steps) if steps else []
		reviewed = [one for one in flow.actions_in(said) if one.get("type") == "reply" and one.pop("review", None)]
		if not reviewed and "review" not in (steps or ""):
			continue
		for one in flow.actions_in(said):
			one.pop("review", None)
		values = {"steps": frappe.as_json(said, indent=None)}
		if any(one.get("with") == "OneAI" for one in reviewed):
			values["enabled"] = 0
		frappe.db.set_value("Mail Rule", name, values, update_modified=False)
