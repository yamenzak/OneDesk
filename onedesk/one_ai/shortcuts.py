"""OneAI's key (docs/READY.md, mechanism 19): asking, from anywhere. Pure."""

from onedesk.one.registry.model import _lt


SHORTCUTS = [
	{"key": "ask", "label": _lt("Ask OneAI"), "keys": ["alt+shift+KeyA"], "where": "anywhere"},
]
