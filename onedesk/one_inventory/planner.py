"""What OneInventory's storekeeper makes of what OneAI read (docs/ARC-AI.md,
The agents): a delivery note as a draft Purchase Receipt, a delivery nobody
ordered as a task to check it, and a supplier's offer as a Supplier
Quotation. Pure: each answers actions, which the agents' door takes."""

from onedesk.one_ai.reading.act import Action as _Action
from onedesk.one_ai.reading.money import Action, _real
from onedesk.one_project.intake import task_in


def goods(reading: dict, ctx: dict) -> list[Action]:
	"""A supplier's delivery note, as a draft Purchase Receipt against the
	order it delivers, for what the note says came. A line that matches no
	item makes it a proposal."""
	if not _real(reading, ctx) or reading.get("kind") != "Delivery Note" or not ctx.get("purchase_order"):
		return []
	items = ctx.get("items") or {}
	source = reading.get("lines") or []
	delivered = {}
	for index, one in enumerate(source):
		if items.get(index):
			delivered[items[index]] = delivered.get(items[index], 0) + float(one.get("qty") or 0)
	missing = any(not items.get(index) for index in range(len(source)))
	values = {"order": ctx["purchase_order"], "supplier_delivery_note": reading.get("number"), "delivered": delivered}
	return [Action("Create", "Purchase Receipt", values={key: value for key, value in values.items() if value}, key="books|receipt", flow="onedesk.one_ai.reading.planning.receipt_from_order", propose=missing, why=ctx["said"]["unmatched"] if missing else "", propose_on_error=True)]


def unordered(reading: dict, ctx: dict) -> list[Action]:
	"""A delivery from a known supplier that no order of ours asked for: a
	task to check it before anybody signs for it or pays."""
	if not _real(reading, ctx) or reading.get("kind") != "Delivery Note" or ctx.get("purchase_order") or not ctx.get("supplier") or reading.get("change") not in (None, "", "New"):
		return []
	values = {
		"subject": ctx["said"]["unordered"].format(ctx["supplier"]),
		"description": ctx["said"]["see_document"],
		"exp_end_date": ctx["today"],
		"one_about_doctype": "Supplier",
		"one_about": ctx["supplier"],
		"assign_to": ctx.get("person"),
		"project": task_in(ctx.get("project"), ctx["today"]),
	}
	return [_Action("Create", "Task", values=values, key="task|unordered", flow="onedesk.one_ai.reading.planning.make_task", sure=True)]


def _each(line: dict) -> float:
	"""A line's price for one: its unit price, or its amount over how many."""
	if line.get("unit_price") is not None:
		return float(line["unit_price"])
	return float(line.get("amount") or 0) / (float(line.get("qty") or 1) or 1)


def quotation(reading: dict, ctx: dict) -> list[Action]:
	"""A supplier's offer, as a Supplier Quotation when every line is an item,
	dated the day the supplier gave it, so one read after it ran out is kept too."""
	if not _real(reading, ctx) or reading.get("kind") != "Offer" or not ctx.get("supplier"):
		return []
	items = ctx.get("items") or {}
	source = reading.get("lines") or []
	if not source or len(items) < len(source):
		return []
	rows = [{"item_code": items[index], "qty": float(one.get("qty") or 1), "rate": _each(one)} for index, one in enumerate(source)]
	valid = next((str(one["date"]) for one in reading.get("dates") or [] if one.get("what") == "Valid Until" and one.get("date")), None)
	values = {"supplier": ctx["supplier"], "transaction_date": reading.get("issued_on") or ctx["today"], "valid_till": valid, "items": rows}
	return [Action("Create", "Supplier Quotation", values={k: v for k, v in values.items() if v}, key="books|quotation", propose_on_error=True)]
