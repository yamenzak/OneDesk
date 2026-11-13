"""One's own keys (docs/READY.md, mechanism 19): the centres and the shell,
the same in every app. Letters go with Alt and Shift: Alt alone and a
letter is frappe's, for the button whose letter is underlined. Pure."""

from onedesk.one.registry.model import _lt


SHORTCUTS = [
	{"key": "shortcuts", "label": _lt("See and Change Shortcuts"), "keys": ["shift+Slash"], "where": "anywhere", "frappe": "shift+/"},
	{"key": "home", "label": _lt("Go Home"), "keys": ["alt+shift+KeyH"], "where": "anywhere"},
	{"key": "notifications", "label": _lt("Open Notifications"), "keys": ["alt+shift+KeyN"], "where": "anywhere"},
	{"key": "theme", "label": _lt("Change Appearance"), "keys": ["mod+shift+KeyG"], "where": "anywhere", "frappe": "shift+ctrl+g"},
]
