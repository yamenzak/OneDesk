"""What's New: each module's versions, from its docs/changelog/, and the
newest each person has seen (docs/READY.md, Versions and What's New).

The words are written in English only, for the people using the module, so
they are shown as written. A picture beside an entry is sent inside it.
"""

import base64
import mimetypes
import re

import frappe
from frappe import _
from frappe.utils import md_to_html

from onedesk.one import ready

SEEN = "one_seen_version_{}"
PICTURE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _known(module: str) -> None:
	if module not in ready.MODULES:
		frappe.throw(_("{0} has no versions.").format(module))


def seen(module: str) -> str | None:
	return frappe.defaults.get_user_default(SEEN.format(ready.MODULES[module]["folder"]))


def for_boot() -> dict:
	"""Each module's version, and whether the reader has seen it."""
	out = {}
	for module in ready.MODULES:
		version = ready.current(module)
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
				"html": md_to_html(_pictured(one)),
				"new": int(ready.number(one["version"]) > before),
				"docs": [{"id": page, "title": titles[page]} for page in one["docs"] if page in titles],
			}
		)
	if entries:
		frappe.defaults.set_user_default(SEEN.format(ready.MODULES[module]["folder"]), entries[0]["version"])
	return {"module": module, "versions": entries}


def _pictured(one: dict) -> str:
	"""A version's or a help page's words with each picture beside it sent
	inside them."""

	def inline(found: re.Match) -> str:
		path = (one["path"].parent / found.group(2)).resolve()
		if not path.is_relative_to(one["path"].parent.resolve()) or not path.exists():
			return found.group(1)
		kind = mimetypes.guess_type(path.name)[0] or "image/png"
		return f"![{found.group(1)}](data:{kind};base64,{base64.b64encode(path.read_bytes()).decode()})"

	return PICTURE.sub(inline, one["body"])


def _filled(module: str, body: str) -> str:
	"""A page's words with what the module ships put in: `{roles}` is what
	each of its roles starts with (one/abilities.py `defaults_table`)."""
	if "{roles}" in body:
		from onedesk.one import abilities

		body = body.replace("{roles}", abilities.defaults_table(module))
	return body


@frappe.whitelist()
def help_pages(module: str) -> dict:
	"""A module's help, page by page, in reading order, as people read it in
	its Help (docs/READY.md, Docs and Help)."""
	_known(module)
	return {
		"module": module,
		"version": ready.current(module),
		"pages": [
			{"id": page["id"], "icon": page["icon"], "title": page["title"], "html": md_to_html(_filled(module, _pictured(page)))}
			for page in ready.help_pages(module)
		],
	}
