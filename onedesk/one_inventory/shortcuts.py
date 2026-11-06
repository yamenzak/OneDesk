"""OneInventory's keys (docs/READY.md, mechanism 19), on its own screens:
Stock Summary and Reorder. Pure."""


def _lt(text: str) -> str:
	return text


SHORTCUTS = [
	{"key": "find_stock", "label": _lt("Search Items"), "keys": ["Slash"], "where": "stock-on-hand"},
	{"key": "find_order", "label": _lt("Search"), "keys": ["Slash"], "where": "to-order"},
	{"key": "order", "label": _lt("Draft Purchase Orders"), "keys": ["KeyO"], "where": "to-order"},
]
