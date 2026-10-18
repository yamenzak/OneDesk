"""How far each project has got and how its tasks stand: ERPNext's Project
Summary without the HR checklists, which are Projects too. See the module's
README, Under the hood."""

from erpnext.projects.report.project_summary import project_summary as upstream

from onedesk.one_hr.lifecycle import BOARDING

REPEATED = ("project_name", "project_type")

OFFERED = ("status", "priority", "is_active")


def execute(filters=None):
	filters = {key: value for key, value in (filters or {}).items() if key in OFFERED and value not in (None, "")}
	filters["project_type"] = ["!=", BOARDING]
	columns, data, message, chart, summary = upstream.execute(filters)
	for one in summary or []:
		if one.get("datatype") == "Percent":
			one["value"] = round(one["value"] or 0)
	for row in data:
		row["percent_complete"] = round(row.get("percent_complete") or 0)
	for one in columns:
		if one["fieldname"] == "percent_complete":
			one.update(fieldtype="Percent", width=110)
	return [one for one in columns if one["fieldname"] not in REPEATED], data, message, chart, summary
