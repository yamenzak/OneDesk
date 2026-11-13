"""OneBook's keys (docs/READY.md, mechanism 19), on its Home: a letter for
each paper it starts. Pure."""

from onedesk.one.registry.model import _lt


SHORTCUTS = [
	{"key": "new_invoice", "label": _lt("New Sales Invoice"), "keys": ["KeyI"], "where": "books"},
	{"key": "new_bill", "label": _lt("New Purchase Invoice"), "keys": ["KeyB"], "where": "books"},
	{"key": "new_payment", "label": _lt("New Payment Entry"), "keys": ["KeyP"], "where": "books"},
	{"key": "new_journal", "label": _lt("New Journal Entry"), "keys": ["KeyJ"], "where": "books"},
]
