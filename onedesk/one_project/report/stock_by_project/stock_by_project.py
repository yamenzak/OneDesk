"""What stock each project has had: ERPNext's Project wise Stock Tracking for
the projects the reader may open, without the HR checklists. See the
module's README, Under the hood."""

import frappe
from erpnext.projects.report.project_wise_stock_tracking import project_wise_stock_tracking as upstream

from onedesk.one_hr.lifecycle import BOARDING

KEPT = (0, 1, 2, 3, 5, 7, 8, 9, 10)


def execute(filters=None):
	columns, data = upstream.execute(filters)
	shown = set(
		frappe.get_list("Project", filters={"project_type": ["!=", BOARDING]}, pluck="name", limit_page_length=0)
	)
	rows = [row for row in data if row[0] in shown and any(row[1:4])]
	return [columns[i] for i in KEPT], [[row[i] for i in KEPT] for row in rows]
