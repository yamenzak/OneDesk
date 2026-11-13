"""OneHR's keys (docs/READY.md, mechanism 19), on its Home: a letter for
each request it starts. Pure."""

from onedesk.one.registry.model import _lt


SHORTCUTS = [
	{"key": "request_leave", "label": _lt("Request Leave"), "keys": ["KeyL"], "where": "onehr"},
	{"key": "claim_expense", "label": _lt("Claim an Expense"), "keys": ["KeyE"], "where": "onehr"},
	{"key": "new_employee", "label": _lt("New Employee"), "keys": ["KeyN"], "where": "onehr"},
]
