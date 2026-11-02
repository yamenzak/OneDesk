"""ShortcutCenter (docs/READY.md, mechanism 19): what each key does where.
Every module declares its own in its shortcuts.py; what a person moves is
kept as their own default, `one_shortcuts`. One's README, Under the hood,
says how a key is written."""

import importlib
import json
import re

import frappe
from frappe import _

from onedesk.one import ready

KEPT = "one_shortcuts"

# Where a shortcut works, by what the window says the view is (data-one-view),
# and its words. A module's own screen is named by its page, and reads "In"
# and the module.
WHERE = {
	"anywhere": ("Anywhere", None),
	"lists": ("In a List", ("list", "report", "image", "map", "gantt", "kanban", "board", "dashboard", "calendar")),
	"record": ("In a Record", ("form",)),
	"calendar": ("In a Calendar", ("calendar",)),
}

MODIFIERS = ("mod", "alt", "shift")
KEY = re.compile(r"^(?:(?:mod|alt|shift)\+)*(?:mouse:(?:back|forward|middle)|[A-Z][A-Za-z0-9]+)$")

# What a browser or the system keeps, which no page can be given.
RESERVED = {
	"Tab",
	"shift+Tab",
	"mod+KeyW",
	"mod+KeyT",
	"mod+KeyN",
	"mod+KeyQ",
	"mod+Tab",
	"mod+shift+KeyT",
	"mod+shift+KeyN",
	"mod+shift+KeyW",
	"mouse:middle",
}


def _modules():
	for module, spec in ready.MODULES.items():
		path = f"onedesk.{spec['folder']}.shortcuts"
		try:
			found = importlib.import_module(path)
		except ModuleNotFoundError as e:
			if e.name != path:
				raise
			continue
		yield module, spec["folder"], found


def declared() -> list[dict]:
	"""Every shortcut every module ships, as declared."""
	out = []
	for module, folder, found in _modules():
		for one in getattr(found, "SHORTCUTS", ()):
			out.append({**one, "id": f"{folder}.{one['key']}", "module": module})
	return out


def where_label(where: str, module: str) -> str:
	if where in WHERE:
		return _(WHERE[where][0])
	return _("In {0}").format(module)


def kinds(where: str):
	"""The views a shortcut works in: None for anywhere, else the window's
	kinds, or a module's page by its name."""
	if where in WHERE:
		return WHERE[where][1]
	return (f"page:{where}",)


def yours() -> dict:
	try:
		said = json.loads(frappe.defaults.get_user_default(KEPT) or "{}")
	except ValueError:
		said = {}
	return said if isinstance(said, dict) else {}


def for_boot() -> dict:
	"""Every shortcut with its words, where it works and the keys it ships
	with, and the keys the reader moved."""
	return {
		"shortcuts": [
			{
				"id": one["id"],
				"module": one["module"],
				"label": _(one["label"]),
				"where": one["where"],
				"where_label": where_label(one["where"], one["module"]),
				"kinds": kinds(one["where"]),
				"keys": list(one["keys"]),
				"typing": int(bool(one.get("typing"))),
				"dialogs": int(bool(one.get("dialogs"))),
				"frappe": one.get("frappe"),
			}
			for one in declared()
		],
		"yours": yours(),
		"reserved": sorted(RESERVED),
	}


def _check(keys: list[str]) -> list[str]:
	if not isinstance(keys, list):
		frappe.throw(_("Keys must be a list."))
	for key in keys:
		if not isinstance(key, str) or not KEY.match(key):
			frappe.throw(_("{0} is not a key.").format(key))
		if key in RESERVED:
			frappe.throw(_("{0} belongs to your browser, so it can't be a shortcut.").format(key))
	return keys


@frappe.whitelist(methods=["POST"])
def save(id: str, keys: str | list) -> dict:
	"""The reader's keys for one shortcut; the keys it ships with again when
	they are the same."""
	keys = _check(json.loads(keys) if isinstance(keys, str) else keys)
	shipped = {one["id"]: list(one["keys"]) for one in declared()}
	if id not in shipped:
		frappe.throw(_("There is no such shortcut."))
	said = yours()
	if keys == shipped[id]:
		said.pop(id, None)
	else:
		said[id] = keys
	frappe.defaults.set_user_default(KEPT, json.dumps(said, sort_keys=True))
	return said


@frappe.whitelist(methods=["POST"])
def reset(id: str | None = None) -> dict:
	"""One shortcut, or every one, back to the keys it ships with."""
	said = yours()
	if id:
		said.pop(id, None)
	else:
		said = {}
	frappe.defaults.set_user_default(KEPT, json.dumps(said, sort_keys=True))
	return said
