"""How OneWorkbook and OneWriter save over the office file they edit in
place without losing what nobody chose to lose: read-only for macros and
older formats, Save Over Original or Save as Copy for a file with parts the
editor drops (fidelity.py), and a note on One's own record of what a save
from the drive or OneOS left out. AGENTS.md, Under the hood, Nothing lost
silently."""

import json
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import get_fullname, now_datetime

from onedesk.one_storage import fidelity, lease
from onedesk.one_storage import namespace as ns

OVER, COPY = "over", "copy"


def listed(raw) -> list:
	if isinstance(raw, list):
		return raw
	try:
		return json.loads(raw or "[]") or []
	except ValueError:
		return []


def opened(doctype: str, name: str, found: list[str]) -> None:
	"""What the file just read in has that the editor drops."""
	frappe.db.set_value(doctype, name, {"would_lose": json.dumps(found), "held_back": None}, update_modified=False)


def state(doctype: str, name: str, item: dict, may_write: bool) -> dict:
	"""What an editor opens with: whether the reader may change it here, the
	line saying why not, the line saying what saving over the file drops,
	and what a save from the drive left out."""
	held = frappe.db.get_value(doctype, name, ["source_kind", "would_lose", "outside_dropped"], as_dict=True) or frappe._dict()
	found = listed(held.would_lose) if held.source_kind else []
	alone = lease.blocking(item["name"])
	why = lease.told(alone) if alone else _read_only(held, item)
	write = bool(may_write) and not why
	return {
		"can_write": write,
		"notice": why if may_write or alone else None,
		"loses": fidelity.dropping(item["file_name"], found) if write and found else None,
		"dropped": dropped(held.outside_dropped),
	}


def dropped(raw) -> str | None:
	said = raw if isinstance(raw, dict) else json.loads(raw) if raw else None
	if not said or not said.get("what"):
		return None
	line = (
		_("{0} saved this in OneOS on {1}. Its {2} could not be kept. What it held before is in Version History.")
		if said.get("in") == lease.ONEOS
		else _("{0} saved this from the drive on {1}. Its {2} could not be kept. What it held before is in Version History.")
	)
	return line.format(get_fullname(said.get("by")), frappe.utils.format_datetime(said.get("on"), "d MMM, HH:mm"), fidelity.named(said["what"]))


@contextmanager
def through(kind: str):
	"""A save coming in through the alone lease its writer holds, OneOS or
	a lock on the drive, which the lease does not refuse."""
	was = frappe.flags.one_lease_through
	frappe.flags.one_lease_through = kind
	try:
		yield
	finally:
		frappe.flags.one_lease_through = was


def before(usual: str) -> str:
	"""The name of the version kept before an outside save: `usual`, or
	that it came from OneOS."""
	return _("Before a OneOS save") if frappe.flags.one_lease_through == lease.ONEOS else usual


def _let_through(alone: dict | None) -> bool:
	return bool(alone and alone["mine"] and alone["kind"] == frappe.flags.one_lease_through)


def check(doctype: str, name: str, item: dict) -> None:
	"""A save from the editor refused while somebody has the file alone, or
	while it opens read-only."""
	found = frappe.db.get_value(doctype, name, ["source_kind", "would_lose"], as_dict=True) or frappe._dict()
	alone = lease.blocking(item["name"])
	if alone and not _let_through(alone):
		frappe.throw(lease.told(alone), frappe.PermissionError)
	why = _read_only(found, item)
	if why:
		frappe.throw(why, frappe.PermissionError)


def _read_only(held: dict, item: dict) -> str | None:
	"""The line saying why a file edited in place opens read-only."""
	why = held.source_kind and fidelity.read_only(item["file_name"], listed(held.would_lose))
	return fidelity.why_read_only(item["file_name"], why) if why else None


def write_back(doctype: str, name: str, item: dict, content, choice: str = "", edited: bool = True) -> dict:
	"""The editor's content as the File's, when nothing would be lost or the
	reader chose: `held` with the line to show when saving over waits for a
	choice (and, when something was `edited`, the changes marked as waiting),
	`copy` with the new File when they chose a copy. `content` is the bytes,
	or what makes them, called only once they are written."""
	from onedesk.one_storage import history

	check(doctype, name, item)
	found = listed(frappe.db.get_value(doctype, name, "would_lose"))
	if found and choice not in (OVER, COPY):
		if edited and not frappe.db.get_value(doctype, name, "held_back"):
			frappe.db.set_value(doctype, name, "held_back", now_datetime(), update_modified=False)
		return {"held": fidelity.dropping(item["file_name"], found)}
	if callable(content):
		content = content()
	if not content:
		frappe.throw(_("No file was uploaded."))
	if choice == COPY:
		made = _beside(item, content)
		frappe.db.set_value(doctype, name, {"file": made.name, "title": made.file_name, "would_lose": "[]", "held_back": None}, update_modified=False)
		history.seen(made.name)
		return {"copy": ns.node(ns.row(made.name)), "file": made.name}
	made = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": item["file_name"],
			"content": content,
			"is_private": item.get("is_private", 1),
			"folder": item.get("folder") or None,
		}
	)
	made.flags.ignore_permissions = True
	made.insert()
	frappe.flags.one_writing_back = True
	try:
		history.replace(ns.row(item["name"]), made.name, sitting=lease.sitting(item["name"], "editor"))
	finally:
		frappe.flags.one_writing_back = False
	frappe.db.set_value(doctype, name, {"would_lose": "[]", "held_back": None}, update_modified=False)
	return {"file": item["name"], "size": frappe.db.get_value("File", item["name"], "file_size")}


def _beside(item: dict, content: bytes, name: str | None = None):
	"""A new File next to `item`: in its folder, on its record, or in My
	Files where the reader may not add there."""
	from onedesk.one_storage import api

	wanted = name or item["file_name"]
	fields = {"doctype": "File", "is_private": item.get("is_private", 1), **({"content": content} if isinstance(content, bytes) else {"file_url": content})}
	if item.get("attached_to_doctype") and item.get("attached_to_name"):
		fields.update(attached_to_doctype=item["attached_to_doctype"], attached_to_name=item["attached_to_name"], folder=item.get("folder"))
		taken = set(frappe.get_all("File", filters={"attached_to_doctype": item["attached_to_doctype"], "attached_to_name": item["attached_to_name"]}, pluck="file_name"))
	else:
		folder = ns.row(item["folder"]) if item.get("folder") else None
		fields["folder"] = item["folder"] if folder and ns.may(folder, "add") else ns.home()
		taken = api._taken(fields["folder"])
	fields["file_name"] = ns.unique_name(wanted, taken)
	made = frappe.get_doc(fields)
	made.flags.ignore_permissions = True
	made.insert()
	return made


def set_aside(doctype: str, name: str, url: str) -> bool:
	"""A new version of the file arrived while the editor's changes waited
	for a choice: the workbook or document leaves the file, kept as a copy
	of One's own beside it named for whoever made the changes. True when it
	did."""
	held = frappe.db.get_value(doctype, name, ["file", "held_back", "modified_by"], as_dict=True)
	if not held or not held.held_back or not held.file:
		return False
	item = ns.row(held.file)
	stem = item["file_name"].rsplit(".", 1)[0] if "." in item["file_name"] else item["file_name"]
	first = (get_fullname(held.modified_by) or "").split(" ")[0] or held.modified_by
	made = _beside(item, url + name, _("{0} ({1}'s copy)").format(stem, first))
	frappe.db.set_value(doctype, name, {"file": made.name, "title": made.file_name, "source_kind": None, "would_lose": None, "held_back": None}, update_modified=False)
	from onedesk.one_storage import history

	history.note(made.name, _("kept the changes not saved to {0}").format(item["file_name"]))
	return True


def outside(doctype: str, name: str, found: list[str]) -> None:
	"""What a save from the drive or OneOS into One's own record left out."""
	said = {"what": found, "by": frappe.session.user, "on": str(now_datetime()), "in": frappe.flags.one_lease_through} if found else None
	frappe.db.set_value(doctype, name, "outside_dropped", json.dumps(said) if said else None, update_modified=False)


def dismiss(doctype: str, name: str) -> None:
	frappe.db.set_value(doctype, name, "outside_dropped", None, update_modified=False)
