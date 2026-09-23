"""Every project the reader may see, as the tree it is: each under its parent,
with its own figures. A parent's line is its own; the whole tree's add-up is on
the parent's page (tree.totals), where it is one number rather than a column to
read twice."""

import frappe
from frappe import _

from onedesk.one_hr.lifecycle import BOARDING
from onedesk.one_project import tree


def execute(filters=None):
	filters = filters or {}
	where = {} if filters.get("closed") else {"status": ["not in", ["Completed", "Cancelled"]]}
	# An onboarding or an exit is HR's checklist, not a piece of work (one_hr/lifecycle.py).
	where["project_type"] = ["!=", BOARDING]
	rows = frappe.get_list(
		"Project",
		filters=where,
		fields=["name", "project_name", tree.PARENT, "customer", "status", "one_health", "one_manager", "percent_complete",
			"expected_end_date", "estimated_costing", "total_costing_amount", "total_billed_amount", "gross_margin"],
		limit=0,
	)
	return columns(), ordered(rows)


def ordered(rows: list[dict]) -> list[dict]:
	"""Each project after its parent, indented by depth. A project whose parent
	the reader cannot see starts a tree of its own. Pure."""
	names = {row["name"] for row in rows}
	down = {}
	for row in rows:
		parent = row.get(tree.PARENT)
		down.setdefault(parent if parent in names else None, []).append(row)
	out = []

	def walk(parent, depth):
		for row in sorted(down.get(parent, []), key=lambda one: (one.get("project_name") or one["name"]).lower()):
			out.append({**row, "project": row["name"], "parent": row.get(tree.PARENT) if row.get(tree.PARENT) in names else None, "indent": depth})
			walk(row["name"], depth + 1)

	walk(None, 0)
	return out


def columns() -> list[dict]:
	return [
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 280},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 160},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "one_health", "label": _("Health"), "fieldtype": "Data", "width": 100},
		{"fieldname": "one_manager", "label": _("Project Manager"), "fieldtype": "Link", "options": "User", "width": 160},
		{"fieldname": "percent_complete", "label": _("% Completed"), "fieldtype": "Percent", "width": 110},
		{"fieldname": "expected_end_date", "label": _("Expected End Date"), "fieldtype": "Date", "width": 130},
		{"fieldname": "estimated_costing", "label": _("Estimated Cost"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_costing_amount", "label": _("Total Costing Amount"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "total_billed_amount", "label": _("Total Billed Amount"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "gross_margin", "label": _("Gross Margin"), "fieldtype": "Currency", "width": 130},
	]
