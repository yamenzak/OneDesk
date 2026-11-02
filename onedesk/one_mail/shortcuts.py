"""OneMail's keys (docs/READY.md, mechanism 19), as Gmail has them, in the
mailbox's own screen. Pure."""


def _lt(text: str) -> str:
	return text


SHORTCUTS = [
	{"key": "next", "label": _lt("Next Conversation"), "keys": ["KeyJ", "ArrowDown"], "where": "onemail"},
	{"key": "previous", "label": _lt("Previous Conversation"), "keys": ["KeyK", "ArrowUp"], "where": "onemail"},
	{"key": "compose", "label": _lt("New Email"), "keys": ["KeyC"], "where": "onemail"},
	{"key": "reply", "label": _lt("Reply"), "keys": ["KeyR"], "where": "onemail"},
	{"key": "reply_all", "label": _lt("Reply All"), "keys": ["KeyA"], "where": "onemail"},
	{"key": "forward", "label": _lt("Forward"), "keys": ["KeyF"], "where": "onemail"},
	{"key": "archive", "label": _lt("Archive"), "keys": ["KeyE"], "where": "onemail"},
	{"key": "delete", "label": _lt("Delete"), "keys": ["shift+Digit3", "Delete"], "where": "onemail"},
	{"key": "star", "label": _lt("Star or Unstar"), "keys": ["KeyS"], "where": "onemail"},
	{"key": "unread", "label": _lt("Mark as Unread"), "keys": ["KeyU"], "where": "onemail"},
	{"key": "search", "label": _lt("Search Mail"), "keys": ["Slash"], "where": "onemail"},
]
