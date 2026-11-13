"""What's New: each module's versions, from its updates/, and the
newest each person has seen (docs/READY.md, Versions and What's New). A
version names the Help pages it changed (`docs`), and each page lists the
versions that changed it.
"""

from functools import lru_cache

import frappe
from frappe import _
from frappe.utils import md_to_html

from onedesk.one import media, ready, registry
from onedesk.one_admin import site

SEEN = "one_seen_version_{}"


def offered(module: str) -> bool:
	"""Whether the reader may see a module's versions, Help and tour: all of
	them, but OneAdmin's for its operators alone."""
	return not ready.MODULES.get(module, {}).get("operators") or site.operates()


def _known(module: str) -> None:
	if module not in ready.MODULES or not offered(module):
		frappe.throw(_("{0} has no versions.").format(module))


def seen(module: str) -> str | None:
	return frappe.defaults.get_user_default(SEEN.format(ready.MODULES[module]["folder"]))


def off(module: str, hidden: set) -> bool:
	"""Whether a module is an app this workspace has turned off, or its
	plan leaves out: its rail row is among `hidden` (one/apps.py)."""
	try:
		sidebar = registry.by_name(module).sidebar
	except KeyError:
		return False
	return bool(sidebar) and sidebar in hidden


@lru_cache
def titles(module: str) -> tuple[tuple[str, str], ...]:
	"""A module's Help pages by id and title, which Ctrl+K finds: read once
	a process, as the files change only with a release."""
	return tuple((page["id"], page["title"]) for page in ready.help_pages(module))


def for_boot() -> dict:
	"""Each module's version, whether the reader has seen it, the Help page
	its ControlCenter is explained on (settings, else overview), and its
	pages' titles; an app turned off, or one AccessCenter puts the reader at
	no level in, is marked `off`, so HelpCenter, UpdateCenter and Ctrl+K
	leave it out."""
	from onedesk.one import apps, rail

	hidden = set(apps.hidden()) | rail.unreached()
	out = {}
	for module in ready.MODULES:
		version = ready.current(module) if offered(module) else None
		if version:
			pages = [page for page, _icon in ready.MODULES[module].get("help", ())]
			told = next((page for page in ("settings", "overview") if page in pages), "")
			out[module] = {"version": version, "unseen": int(seen(module) != version), "help": told, "pages": titles(module)}
			if off(module, hidden):
				out[module]["off"] = 1
	return out


@frappe.whitelist()
def whats_new(module: str) -> dict:
	"""Every version of a module, newest first, each marked new if the reader
	has not seen it; opening them marks them seen."""
	_known(module)
	was = seen(module)
	before = ready.number(was) if was else (0, 0, 0)
	titles = {page["id"]: page["title"] for page in ready.help_pages(module)}
	entries = []
	for one in ready.shown(module):
		entries.append(
			{
				"version": one["version"],
				"date": one["date"],
				"kind": one["kind"],
				"title": one["title"],
				"html": md_to_html(media.pictured(module, one["body"], one["path"])),
				"new": int(ready.number(one["version"]) > before),
				"docs": [{"id": page, "title": titles[page]} for page in one["docs"] if page in titles],
			}
		)
	if entries:
		frappe.defaults.set_user_default(SEEN.format(ready.MODULES[module]["folder"]), entries[0]["version"])
	return {"module": module, "versions": [*coming(module), *entries]}


NOTES = "one_coming_notes"


def _notes() -> dict:
	"""The index every admin site publishes to the shared bucket, kept an
	hour; nothing when it can't be read."""
	held = frappe.cache.get_value(NOTES)
	if held is None:
		import requests

		try:
			answered = requests.get(f"{media.base()}/notes/index.json", timeout=5)
			held = answered.json() if answered.ok else {}
		except (requests.RequestException, ValueError):
			held = {}
		frappe.cache.set_value(NOTES, held, expires_in_sec=3600)
	return held


def coming(module: str) -> list[dict]:
	"""A module's versions newer than this workspace runs, from the shared
	index: what the next update brings."""
	now = ready.number(ready.current(module) or "0.0.0")
	return [
		{**one, "coming": 1, "new": 0, "docs": []}
		for one in _notes().get(module) or []
		if isinstance(one, dict) and one.get("version") and ready.number(one["version"]) > now
	]


def _filled(module: str, body: str) -> str:
	"""A page's words with what the module ships put in: `{roles}` is what
	each of its roles starts with (one/rights.py `defaults_table`)."""
	if "{roles}" in body:
		from onedesk.one import rights

		body = body.replace("{roles}", rights.defaults_table(module))
	return body


@frappe.whitelist()
def help_pages(module: str) -> dict:
	"""A module's help, page by page, in reading order, as people read it in
	its Help (docs/READY.md, Docs and Help)."""
	_known(module)
	changed = {}
	for one in ready.shown(module):
		for page in one["docs"]:
			changed.setdefault(page, []).append({"version": one["version"], "title": one["title"], "date": one["date"]})
	return {
		"module": module,
		"version": ready.current(module),
		"pages": [
			{
				"id": page["id"],
				"icon": page["icon"],
				"title": page["title"],
				"html": md_to_html(_filled(module, media.pictured(module, page["body"], page["path"]))),
				"changed": changed.get(page["id"], []),
			}
			for page in ready.help_pages(module)
		],
	}
