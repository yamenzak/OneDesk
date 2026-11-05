"""Who sees what making costs: OneFactory's See What Making Costs
(abilities.py). Without it a bill of materials' Costing tab and its cost per
unit at the top of the page are not shown."""

from onedesk.one import rights


def seen(user: str | None = None) -> bool:
	return rights.may("Manufacturing Settings", "factory_costs", user=user)


def onload(doc, method=None) -> None:
	"""BOM onload: tells the form to leave the Costing tab out."""
	if not seen():
		doc.set_onload("one_costs_hidden", 1)
