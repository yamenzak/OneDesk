"""OneCRM's keys (docs/READY.md, mechanism 19), on its Home: a letter for
each thing it starts. Pure."""

from onedesk.one.registry.model import _lt


SHORTCUTS = [
	{"key": "new_lead", "label": _lt("New Lead"), "keys": ["KeyL"], "where": "onecrm"},
	{"key": "new_opportunity", "label": _lt("New Opportunity"), "keys": ["KeyO"], "where": "onecrm"},
	{"key": "new_quotation", "label": _lt("New Quotation"), "keys": ["KeyQ"], "where": "onecrm"},
]
