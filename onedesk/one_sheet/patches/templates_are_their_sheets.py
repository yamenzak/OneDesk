"""A template saved from a record's table workbook kept that table's sheet,
its header and the formulas under it, and was offered only for that table.
A template is its own sheets now: the table's sheet goes, and what said
which table it was for is cleared."""

import json

import frappe

from onedesk.one_sheet import api, storage, table


def execute():
	for one in frappe.get_all(api.WORKBOOK, filters={"is_template": 1, "bound_sheet": ["is", "set"]}, fields=["name", "bound_sheet", "sheets_data"]):
		data = json.loads(storage.decode_sheets_data(one.sheets_data) or "{}")
		kept = table.without(data, one.bound_sheet)
		frappe.db.set_value(
			api.WORKBOOK,
			one.name,
			{"sheets_data": storage.encode_sheets_data(json.dumps(kept, default=str)), "bound_sheet": None, "bound_columns": None},
			update_modified=False,
		)
