"""OneQuality's keys (docs/READY.md, mechanism 19), on its Home: a letter
for each record it starts. Pure."""

from onedesk.one.registry.model import _lt


SHORTCUTS = [
	{"key": "report_problem", "label": _lt("Report a Problem"), "keys": ["KeyN"], "where": "onequality"},
	{"key": "new_action", "label": _lt("New Quality Action"), "keys": ["KeyA"], "where": "onequality"},
]
