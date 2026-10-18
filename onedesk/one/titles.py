"""A page is called what the rail called it.

The rail's own labels, read from the Sidebar rows, are handed to the browser,
and a report's, dashboard's or list's heading is set from them.
"""

import frappe

RENAMES = ("Report", "Dashboard", "DocType")


def for_boot() -> dict[str, dict[str, str]]:
	"""{kind: {name: label}} for every row in a One rail that disagrees, and
	`Crumb`, what a list's crumb says.

	A doctype is renamed only when it is ours and the rails call it one thing:
	`Tenant` is Workspaces. erpnext's are left their own names, since one of
	them is often two rows (Sales Invoice is Invoices and Credit Notes), and
	its name is what its own screens and messages call it."""
	found: dict[str, dict[str, str]] = {kind: {} for kind in RENAMES}
	called: dict[str, set[str]] = {}

	for sidebar in frappe.get_all("Sidebar", filters={"app": "onedesk"}, pluck="name"):
		for row in frappe.get_all(
			"Sidebar Item",
			filters={"parent": sidebar, "parenttype": "Sidebar"},
			fields=["label", "link_to", "link_type"],
			ignore_permissions=True,
		):
			if row.link_type not in RENAMES or not row.link_to:
				continue
			if row.link_type == "DocType":
				called.setdefault(row.link_to, set()).add(row.label)
			elif row.label != row.link_to:
				found[row.link_type][row.link_to] = row.label

	ours = _ours(list(called))
	for doctype, labels in called.items():
		if doctype in ours and len(labels) == 1 and doctype not in labels:
			found["DocType"][doctype] = next(iter(labels))
	found["Crumb"] = {
		doctype: next(iter(labels))
		for doctype, labels in called.items()
		if len(labels) == 1 and doctype not in labels
	}

	return {kind: names for kind, names in found.items() if names}


def _ours(doctypes: list[str]) -> set[str]:
	"""Which of these doctypes this app owns."""
	if not doctypes:
		return set()
	modules = frappe.get_all("Module Def", filters={"app_name": "onedesk"}, pluck="name")
	return set(
		frappe.get_all("DocType", filters={"name": ["in", doctypes], "module": ["in", modules]}, pluck="name")
	)
