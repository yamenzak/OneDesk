"""What OneDisplay's screen keeper does on its own (agent.py WATCH): a
screen that said it may stop working, as a ToDo for whoever manages the
screens. It answers actions, which the agents' door takes
(one_ai/agents/work.py)."""

import frappe
from frappe import _
from frappe.utils import today


def at_risk() -> list:
	"""Each paired screen, not turned off, that said it may stop working
	soon (screens.py _risks), as a ToDo on the screen with its reasons for
	the first person who manages OneDisplay, once a day and only while no
	ToDo on it is open."""
	from onedesk.one_ai.agents import door
	from onedesk.one_ai.reading.act import Action

	day = today()
	owner = door.approver("one_display")
	out = []
	for row in frappe.get_all("Display Screen", filters={"status": "Paired", "dark": 0, "at_risk": 1}, fields=["name", "screen_name", "risk"]):
		if frappe.db.exists("ToDo", {"reference_type": "Display Screen", "reference_name": row.name, "status": "Open"}):
			continue
		said = _("{0} may stop working soon.").format(row.screen_name or row.name)
		values = {"description": "\n".join([said, *(row.risk or "").splitlines()]), "reference_type": "Display Screen", "reference_name": row.name, "date": day, "priority": "Medium", "allocated_to": owner}
		out.append(Action("Create", "ToDo", values={key: value for key, value in values.items() if value}, key=f"one_display|risk|{row.name}|{day}", why=said))
	return out
