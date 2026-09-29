"""A page is called what the rail called it.

Every report and dashboard the rail points at belongs to erpnext or hrms, and
its heading is its record's name — "Employee Hours Utilization Based On
Timesheet" against a rail row reading "Hours Utilization", "Employees working on
a holiday" against "Working on a Holiday". Five reports and five dashboards
disagreed with the row somebody had just clicked.

Renaming theirs is not available: the name is the record's identity, and a
standard Report is rewritten from its app's JSON on every migrate. Forking ten
of them to change a string is worse than the string.

So the rail's own labels are handed to the browser and the heading is set from
them. **Read from the Sidebar rows rather than typed into a list**: a second copy
of those labels is a copy that will disagree with the first the week somebody
renames a row.
"""

import frappe

#: What the rail can rename. A workspace's heading is the workspace's own
#: title. All three are read in `public/js/reports.js`, at their own seams: a
#: report's heading comes from `QueryReport.set_breadcrumbs`, a dashboard's
#: from the crumb the dashboard page adds, which honours a `label` the page
#: never passes, and a list's from its title and its crumb.
RENAMES = ("Report", "Dashboard", "DocType")


def for_boot() -> dict[str, dict[str, str]]:
	"""{kind: {name: label}} for every row in a One rail that disagrees.

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

	return {kind: names for kind, names in found.items() if names}


def _ours(doctypes: list[str]) -> set[str]:
	"""Which of these doctypes this app owns."""
	if not doctypes:
		return set()
	modules = frappe.get_all("Module Def", filters={"app_name": "onedesk"}, pluck="name")
	return set(
		frappe.get_all("DocType", filters={"name": ["in", doctypes], "module": ["in", modules]}, pluck="name")
	)
