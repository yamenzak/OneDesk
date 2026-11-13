"""OneDoc, OneSheet and OneDeck turned off (one/apps.py): nothing new of
their kind is made anywhere, by New, a template, a copy, an import or OneAI,
and everything made in them still opens, read-only, and still leaves as its
Word, Excel or PowerPoint file. A file never becomes unreadable. AGENTS.md,
Under the hood, An editor turned off."""

import frappe
from frappe import _
from frappe.utils.caching import request_cache

from onedesk.one import registry

APPS = {"Writer Document": "one_doc", "Workbook": "one_sheet", "Presentation": "one_deck"}
KINDS = {"document": "Writer Document", "workbook": "Workbook", "presentation": "Presentation"}


def off_among(hidden) -> set[str]:
	"""The record types whose editor's rail row is among `hidden`. Pure but
	for the registry."""
	rows = set(hidden or ())
	return {doctype for doctype, app in APPS.items() if registry.get(app).sidebar in rows}


@request_cache
def off() -> frozenset:
	from onedesk.one import apps

	return frozenset(off_among(apps.hidden()))


def on(doctype: str) -> bool:
	return doctype not in off()


def kinds_off() -> set[str]:
	"""The editors' kinds ("document", "workbook", "presentation") turned off."""
	return {kind for kind, doctype in KINDS.items() if doctype in off()}


def ways(found: dict, gone: set[str]) -> dict | None:
	"""What Edit offers on an office file, less what would make one of the
	kinds `gone`: an editor turned off neither opens a file nor makes one.
	Pure."""
	kept = {way: kind if kind not in gone else None for way, kind in (found or {}).items()}
	return kept if any(kept.values()) else None


def read_only(doctype: str) -> str | None:
	"""The line an editor opens with while its app is turned off."""
	if doctype not in APPS or on(doctype):
		return None
	return _("{0} is turned off for this workspace, so this opens read-only.").format(registry.name(APPS[doctype]))


def refused(doctype: str) -> str:
	return _("{0} is turned off for this workspace, so nothing new can be made in it.").format(registry.name(APPS[doctype]))


def refuse_change(doctype: str) -> None:
	"""A save, an upload or a setting refused while the editor is off."""
	why = read_only(doctype)
	if why:
		frappe.throw(why, frappe.PermissionError)


def making(doc) -> None:
	"""Each editor's record type's before_insert: refused while its app is
	off, but for what installing and migrating set up (OneDeck's themes)."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if not on(doc.doctype):
		frappe.throw(refused(doc.doctype), frappe.PermissionError)


def boot(bootinfo) -> None:
	"""Which editors are on, by kind, for OneCloud's New and the editors."""
	gone = kinds_off()
	bootinfo["one_editors"] = {kind: kind not in gone for kind in KINDS}
