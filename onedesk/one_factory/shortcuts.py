"""OneFactory's keys (docs/READY.md, mechanism 19), on its Home: a letter
for each record it starts. Pure."""


def _lt(text: str) -> str:
	return text


SHORTCUTS = [
	{"key": "new_work_order", "label": _lt("New Work Order"), "keys": ["KeyN"], "where": "onefactory"},
	{"key": "new_bom", "label": _lt("New BOM"), "keys": ["KeyB"], "where": "onefactory"},
]
