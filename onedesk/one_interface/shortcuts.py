"""The window's keys (docs/READY.md, mechanism 19): moving about, and what
every list, record and calendar has, whichever app it is in. The ones frappe
already had (Ctrl+K, Ctrl+S, Ctrl+B, Ctrl+P, Ctrl+/) keep their keys, and
`frappe` names the one of frappe's each replaces, which then stays quiet. Letters
go with Alt and Shift: Alt alone and a letter is frappe's, for the button
whose letter is underlined. Pure."""

from onedesk.one.registry.model import _lt


SHORTCUTS = [
	# Anywhere
	{"key": "search", "label": _lt("Search"), "keys": ["mod+KeyK"], "where": "anywhere", "typing": True, "frappe": "ctrl+k"},
	{"key": "back", "label": _lt("Back"), "keys": ["alt+ArrowLeft"], "where": "anywhere"},
	{"key": "forward", "label": _lt("Forward"), "keys": ["alt+ArrowRight"], "where": "anywhere"},
	{"key": "up", "label": _lt("Up One Level"), "keys": ["alt+ArrowUp"], "where": "anywhere"},
	{"key": "refresh", "label": _lt("Refresh"), "keys": ["alt+shift+KeyR"], "where": "anywhere"},
	{"key": "details", "label": _lt("Show or Hide Details"), "keys": ["alt+shift+KeyI"], "where": "anywhere"},
	{"key": "sidebar", "label": _lt("Show or Hide the Sidebar"), "keys": ["mod+Slash"], "where": "anywhere", "frappe": "ctrl+/"},
	# A list
	{"key": "new", "label": _lt("New"), "keys": ["mod+KeyB"], "where": "lists", "frappe": "ctrl+b"},
	{"key": "find", "label": _lt("Search This List"), "keys": ["Slash"], "where": "lists"},
	# A record
	{"key": "save", "label": _lt("Save"), "keys": ["mod+KeyS"], "where": "record", "typing": True, "dialogs": True, "frappe": "ctrl+s"},
	{"key": "new_record", "label": _lt("New"), "keys": ["mod+KeyB"], "where": "record", "frappe": "ctrl+b"},
	{"key": "print", "label": _lt("Print"), "keys": ["mod+KeyP"], "where": "record", "frappe": "ctrl+p"},
	{"key": "previous", "label": _lt("Previous Record"), "keys": ["mod+shift+Comma"], "where": "record", "frappe": "shift+ctrl+<"},
	{"key": "next", "label": _lt("Next Record"), "keys": ["mod+shift+Period"], "where": "record", "frappe": "shift+ctrl+>"},
	# A calendar
	{"key": "today", "label": _lt("Today"), "keys": ["KeyT"], "where": "calendar"},
	{"key": "later", "label": _lt("Next Period"), "keys": ["KeyJ"], "where": "calendar"},
	{"key": "earlier", "label": _lt("Previous Period"), "keys": ["KeyK"], "where": "calendar"},
	{"key": "month", "label": _lt("Month"), "keys": ["KeyM"], "where": "calendar"},
	{"key": "week", "label": _lt("Week"), "keys": ["KeyW"], "where": "calendar"},
	{"key": "day", "label": _lt("Day"), "keys": ["KeyD"], "where": "calendar"},
]
