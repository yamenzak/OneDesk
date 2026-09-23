"""The pipeline: deals by stage, on the desk's own Kanban.

The desk's Kanban reads and writes its column field on the server whatever the
field's type; only its New Board dialog insists on a Select. So the board is
made here rather than from that dialog, on `sales_stage` as it is, with one
column per Sales Stage in position order. A stage added, renamed or removed
changes the board, which is why the columns are derived rather than a fixture.

Dragging a deal saves it, so a move runs `stages.before_validate` like any
other: the probability follows and Won converts. A Lost stage is an archived
column, so nothing can be dropped on it: losing a deal asks why, and a drop
cannot, so the server refused it and the board left the card where it fell.
"""

import json
from typing import Annotated

import frappe
from frappe.utils import flt

from onedesk.one_crm import stages

BOARD = "Pipeline"

#: What each column's dot says: Won green, the rest still open.
INDICATOR = {"Won": "Green"}

#: What a card shows under the deal's name.
CARD = ["opportunity_amount", "one_next_step", "one_next_on"]


def sync(doc=None, method=None, *args) -> None:
	"""One column per stage, in position order, keeping each column's cards."""
	board = (
		frappe.get_doc("Kanban Board", BOARD)
		if frappe.db.exists("Kanban Board", BOARD)
		else frappe.new_doc("Kanban Board")
	)
	kept = {row.column_name: row.order for row in board.get("columns") or []}
	board.update(
		{
			"kanban_board_name": BOARD,
			"reference_doctype": "Opportunity",
			"field_name": "sales_stage",
			"private": 0,
			"show_labels": 0,
			"fields": json.dumps(CARD),
		}
	)
	board.set("columns", [])
	for stage in stages.stages():
		board.append(
			"columns",
			{
				"column_name": stage.name,
				"status": "Archived" if stage.one_outcome == "Lost" else "Active",
				"indicator": INDICATOR.get(stage.one_outcome, "Blue"),
				"order": kept.get(stage.name) or "[]",
			},
		)
	board.flags.ignore_permissions = True
	board.save()


@frappe.whitelist()
@frappe.read_only()
def worth(filters: Annotated[str | list | None, "The board's filters, as the list sends them."] = None) -> dict:
	"""Each stage's value and weighted value, in the company's currency, for the
	deals the reader can see through the same filters as the board."""
	rows = frappe.get_list(
		"Opportunity",
		filters=frappe.parse_json(filters) if filters else None,
		fields=["sales_stage", "base_opportunity_amount", "base_total", "probability"],
		limit=0,
	)
	return {
		"currency": frappe.db.get_default("currency"),
		"stages": totals(rows),
	}


def totals(rows) -> dict:
	"""Value and weighted value per stage. Pure.

	A deal's value is what was typed, or its items' total when nothing was:
	ERPNext keeps the two apart and a board that reads only one shows a deal
	priced by its items as worth nothing.
	"""
	out = {}
	for row in rows:
		value = flt(row.get("base_opportunity_amount")) or flt(row.get("base_total"))
		stage = out.setdefault(row.get("sales_stage"), {"value": 0.0, "weighted": 0.0})
		stage["value"] += value
		stage["weighted"] += value * flt(row.get("probability")) / 100
	return out
