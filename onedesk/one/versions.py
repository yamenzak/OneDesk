"""What's New: each module's versions, from its docs/changelog/, and the
newest each person has seen (docs/READY.md, Versions and What's New). A
version names the Help pages it changed (`docs`), and each page lists the
versions that changed it.
"""

import frappe
from frappe import _
from frappe.utils import md_to_html

from onedesk.one import media, ready
from onedesk.one_admin import site

SEEN = "one_seen_version_{}"


def offered(module: str) -> bool:
	"""Whether the reader may see a module's versions, Help and tour: all of
	them, but OneAdmin's for its operators alone."""
	return not ready.MODULES[module].get("operators") or site.operates()


def _known(module: str) -> None:
	if module not in ready.MODULES or not offered(module):
		frappe.throw(_("{0} has no versions.").format(module))


def seen(module: str) -> str | None:
	return frappe.defaults.get_user_default(SEEN.format(ready.MODULES[module]["folder"]))


def for_boot() -> dict:
	"""Each module's version, and whether the reader has seen it."""
	out = {}
	for module in ready.MODULES:
		version = ready.current(module) if offered(module) else None
		if version:
			out[module] = {"version": version, "unseen": int(seen(module) != version)}
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
	for one in ready.versions(module):
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
	for one in ready.versions(module):
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
