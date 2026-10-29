"""How far each project has got and how its tasks stand: ERPNext's Project
Summary without the HR checklists, which are Projects too. See the module's
README, Under the hood."""

import frappe
from erpnext.projects.report.project_summary import project_summary as upstream
from frappe.utils import today

from onedesk.one_hr.lifecycle import BOARDING

REPEATED = ("project_name", "project_type")

OFFERED = ("status", "priority", "is_active")


def execute(filters=None):
	filters = {key: value for key, value in (filters or {}).items() if key in OFFERED and value not in (None, "")}
	filters["project_type"] = ["!=", BOARDING]
	columns, data, message, chart, summary = upstream.execute(filters)
	if data:
		late(data)
		chart, summary = upstream.get_chart_data(data), upstream.get_report_summary(data)
	for one in summary or []:
		if one.get("datatype") == "Percent":
			one["value"] = round(one["value"] or 0)
	for row in data:
		row["percent_complete"] = round(row.get("percent_complete") or 0)
	for one in columns:
		if one["fieldname"] == "percent_complete":
			one.update(fieldtype="Percent", width=110)
	return [one for one in columns if one["fieldname"] not in REPEATED], data, message, chart, summary


# Overdue by end date, as My Tasks counts: erpnext's Overdue status waits on a nightly job.
def late(projects):
	counts = frappe.get_list(
		"Task",
		filters={
			"project": ["in", [project.name for project in projects]],
			"exp_end_date": ["<", today()],
			"status": ["not in", ("Completed", "Cancelled", "Template")],
		},
		fields=["project", {"COUNT": "*", "as": "count"}],
		group_by="project",
	)
	by = {row.project: row.count for row in counts}
	for project in projects:
		project["overdue_tasks"] = by.get(project.name, 0)
