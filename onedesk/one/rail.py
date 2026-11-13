"""The rail is the person's (docs/run/RUN.md, P5.8 and P5.9; the whole of it
is in one_interface/AGENTS.md, The rail is the person's). An app AccessCenter
puts somebody at no level in leaves their boot; the workspace's order is the
site's Dock layer, a person's their own through frappe's save_user_dock;
folders and recent apps are One's layer in their user settings (One Rail),
naming apps by where they go, so a changed shipped Dock leaves them be.
"""

import frappe
from frappe import _

HOST = "onedesk"
SETTINGS = "One Rail"
ALWAYS_OPEN = ("settings",)
"""ControlCenter opens on each app's own settings from the tray and the foot,
whatever One's own row says."""


def nowhere(apps: list, held: set, own: dict, always: tuple) -> list[str]:
	"""The apps somebody holding `held` is at no level in: none of an app's
	User or Manager roles, nor one of the workspace's own levels of it (`own`,
	by app). An app everybody uses (`always`) is never one. `apps` is People's
	(name, mark, used, managed). Pure."""
	out = []
	for name, _mark, used, managed in apps:
		if name in always:
			continue
		if held & (set(used) | set(managed) | set(own.get(name, ()))):
			continue
		out.append(name)
	return out


def unreached(user: str | None = None) -> set[str]:
	"""The rail rows (Sidebar names) of the apps AccessCenter puts the reader
	at no level in."""
	from onedesk.one import registry
	from onedesk.one.access import all_levels
	from onedesk.one.people import ALWAYS, APPS

	held = set(frappe.get_roles(user))
	return {sidebar for name in nowhere(APPS, held, all_levels(), ALWAYS) if (sidebar := registry.by_name(name).sidebar)}


def opened(items: list) -> set[str]:
	"""The centres a rail's rows open (`/desk/one?center=...`). Pure."""
	from urllib.parse import parse_qs, urlparse

	out = set()
	for item in items or []:
		asked = parse_qs(urlparse(item.get("url") or "").query).get("center")
		if asked:
			out.add(asked[0])
	return out


def ordered(base: list[str], order: list[str]) -> list[str]:
	"""Every key of `order` in its order, and each key of `base` it does not
	name placed after the key before it in `base` (first, when none is): an
	app an upgrade adds lands where the shipped Dock puts it, inside an order
	somebody saved before it existed. Pure."""
	out = list(dict.fromkeys(order))
	placed = set(out)
	for at, key in enumerate(base):
		if key in placed:
			continue
		before = next((base[i] for i in range(at - 1, -1, -1) if base[i] in placed), None)
		out.insert(out.index(before) + 1 if before else 0, key)
		placed.add(key)
	return out


def folded(folders: list, keys: set) -> list[dict]:
	"""A person's folders, each with the apps of `keys` it names and none it
	names twice, an app in one folder only, and a folder with no app left
	out: what a rail an upgrade changed still draws. Pure."""
	out, taken = [], set()
	for folder in folders or []:
		if not isinstance(folder, dict) or not str(folder.get("name") or "").strip():
			continue
		apps = [key for key in dict.fromkeys(folder.get("apps") or []) if key in keys and key not in taken]
		if apps:
			taken.update(apps)
			out.append({"name": str(folder["name"]).strip(), "apps": apps})
	return out


def _key(entry: dict) -> str:
	from frappe.desk.doctype.dock.dock import dock_key

	return dock_key(entry)


def _own_order(dock: dict) -> None:
	"""A person's own order, with the rows it never named (an app the
	shipped Dock or the workspace added since) where the workspace's order
	puts them."""
	from frappe.desk.doctype.dock.dock import get_user_dock, resolve_app_dock

	mine = dock.get(HOST)
	if not mine or not get_user_dock(HOST):
		return
	site = resolve_app_dock(HOST, upto="site")
	held = {_key(entry): entry for entry in site}
	held.update({_key(entry): entry for entry in mine})
	dock[HOST] = [held[key] for key in ordered([_key(entry) for entry in site], [_key(entry) for entry in mine])]


def boot(bootinfo) -> None:
	"""`extend_bootinfo`, after One's sidebars are settled: the centres the
	reader's One rail opens, the person's own order with what was added
	since, and their folders and recent apps."""
	from frappe.model.utils.user_settings import get_user_settings

	from onedesk.one import registry

	sidebars = bootinfo.get("module_sidebars")
	if not isinstance(sidebars, dict):
		return
	rows = (sidebars.get(registry.get("one").sidebar) or {}).get("items") or []
	shown = opened(rows) | set(ALWAYS_OPEN)
	bootinfo["one_centres"] = [one for one in bootinfo.get("one_centres") or [] if one.get("key") in shown]
	if isinstance(bootinfo.get("dock"), dict):
		_own_order(bootinfo["dock"])
	held = frappe.parse_json(get_user_settings(SETTINGS)) or {}
	keys = {_key(entry) for entry in (bootinfo.get("dock") or {}).get(HOST) or []}
	bootinfo["one_rail"] = {
		"app": HOST,
		"folders": folded(held.get("folders"), keys),
		"recent": [key for key in held.get("recent") or [] if key in keys],
	}


def _shown_rail() -> list[dict]:
	"""The workspace's order of the apps on the rail: the site's layer over
	the shipped Dock, the apps it hides left out."""
	from frappe.desk.doctype.dock.dock import resolve_app_dock

	return [
		{"key": _key(entry), "title": entry.get("title") or entry.get("link_to"), "icon": entry.get("icon")}
		for entry in resolve_app_dock(HOST, upto="site", gated=False)
		if not entry.get("hidden") and entry.get("link_type") == "Sidebar"
	]


@frappe.whitelist()
def workspace() -> dict:
	"""SetupCenter's Order of Apps: the apps in the workspace's order."""
	from onedesk.one import roles

	roles.require()
	return {"apps": _shown_rail()}


@frappe.whitelist(methods=["POST"])
def save_workspace(order: str | list) -> dict:
	"""The workspace's order of the apps, for everybody who has not arranged
	their own; an empty order is the shipped one."""
	from onedesk.one import companions, roles

	roles.require()
	keys = frappe.parse_json(order) if isinstance(order, str) else order
	if not isinstance(keys, list) or any(not isinstance(key, str) for key in keys):
		frappe.throw(_("Could not save the order."))
	companions.layer(order=keys)
	return workspace()
