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

#: What the rail can rename. A doctype's heading is its own and is already
#: right, and a workspace's is the workspace's own title. Dashboards disagree
#: too — five of them — but their view draws its heading somewhere else and
#: nothing here reads a map it cannot use.
RENAMES = ("Report",)


def for_boot() -> dict[str, dict[str, str]]:
	"""{"Report": {name: label}} for every row in a One rail that disagrees."""
	found: dict[str, dict[str, str]] = {kind: {} for kind in RENAMES}

	for sidebar in frappe.get_all("Sidebar", filters={"app": "onedesk"}, pluck="name"):
		for row in frappe.get_all(
			"Sidebar Item",
			filters={"parent": sidebar, "parenttype": "Sidebar"},
			fields=["label", "link_to", "link_type"],
			ignore_permissions=True,
		):
			if row.link_type in RENAMES and row.link_to and row.label != row.link_to:
				found[row.link_type][row.link_to] = row.label

	return {kind: names for kind, names in found.items() if names}
