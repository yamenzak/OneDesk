"""How far each project has got and how its tasks stand: ERPNext's Project
Summary without the HR checklists, which are Projects too. See the module's
README, Under the hood."""

from erpnext.projects.report.project_summary import project_summary as upstream

from onedesk.one_hr.lifecycle import BOARDING

#: Their columns that say again what the Project column says.
REPEATED = ("project_name", "project_type")


def execute(filters=None):
	filters = {key: value for key, value in (filters or {}).items() if value not in (None, "")}
	filters.pop("company", None)
	filters["project_type"] = ["!=", BOARDING]
	columns, data, message, chart, summary = upstream.execute(filters)
	for one in summary or []:
		if one.get("datatype") == "Percent":
			one["value"] = round(one["value"] or 0)
	# Their Completion is a bare "33.33"; it reads as a share, to a whole one.
	for row in data:
		row["percent_complete"] = round(row.get("percent_complete") or 0)
	for one in columns:
		if one["fieldname"] == "percent_complete":
			one.update(fieldtype="Percent", width=110)
	return [one for one in columns if one["fieldname"] not in REPEATED], data, message, chart, summary
