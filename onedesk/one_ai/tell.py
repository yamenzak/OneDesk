"""Telling people about OneAI (notifications/one/oneai_changed.md)."""

import frappe

from onedesk.one import notify


def action_changed(others: list, label: str, changed: list) -> None:
	"""An action's model or added instructions changed, told to the other administrators."""
	notify.notify(
		"OneAI Changed",
		others,
		link="/desk/workspace-settings?section=oneai",
		by=frappe.utils.get_fullname(),
		action=frappe._(label),
		what=frappe._(" and ").join(changed),
	)
