"""A record's tabs after its fields: Mail, Files, Activity.

Each is declared by the module that draws it, under `one_record_tabs` in
hooks.py, and nothing is written to any doctype.
"""

import frappe
from frappe import _lt

#: What a declaration may say.
KEYS = {"name", "label", "order", "doctypes", "leaves_out"}

#: One's own: comments, mail, changes, assignments and shares, last, drawn by
#: frappe's own footer moved into it (record_activity.js).
TABS = [{"name": "activity", "label": _lt("Activity"), "order": 90}]


def declared() -> list[dict]:
	"""Every module's tabs, in the order they are drawn."""
	found = {}
	for path in frappe.get_hooks("one_record_tabs") or []:
		for tab in frappe.get_attr(path):
			strange = set(tab) - KEYS
			if strange or not tab.get("name") or not tab.get("label"):
				raise ValueError(f"{path}: a record tab says {sorted(strange) or 'no name or label'}")
			if tab["name"] in found:
				raise ValueError(f"{path}: two record tabs are called {tab['name']}")
			found[tab["name"]] = tab
	return sorted(found.values(), key=lambda tab: (tab.get("order") or 50, tab["name"]))


def for_boot() -> list[dict]:
	"""The tabs as the desk draws them, their labels in the reader's words."""
	return [
		{
			"name": tab["name"],
			"label": str(tab["label"]),
			"doctypes": list(tab["doctypes"]) if tab.get("doctypes") else None,
			"leaves_out": list(tab.get("leaves_out") or []),
		}
		for tab in declared()
	]
