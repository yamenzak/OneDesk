"""OneAI's key (docs/READY.md, mechanism 19): asking, from anywhere. Pure."""


def _lt(text: str) -> str:
	return text


SHORTCUTS = [
	{"key": "ask", "label": _lt("Ask OneAI"), "keys": ["alt+shift+KeyA"], "where": "anywhere"},
]
