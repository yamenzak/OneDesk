"""OneCRM's keys (docs/READY.md, mechanism 19), on its Home: a letter for
each thing it starts. Pure."""


def _lt(text: str) -> str:
	return text


SHORTCUTS = [
	{"key": "new_lead", "label": _lt("New Lead"), "keys": ["KeyL"], "where": "onecrm"},
	{"key": "new_opportunity", "label": _lt("New Opportunity"), "keys": ["KeyO"], "where": "onecrm"},
	{"key": "new_quotation", "label": _lt("New Quotation"), "keys": ["KeyQ"], "where": "onecrm"},
]
