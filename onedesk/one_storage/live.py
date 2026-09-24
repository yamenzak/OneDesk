"""OneCloud, live: an open folder redraws when somebody else changes it.

A list view does this by joining its doctype's socket room and redrawing on
Frappe's `list_update`. The explorer cannot share that event: the list view
calls `frappe.realtime.off("list_update")` before binding its own handler,
which unbinds every other listener, so opening any list would silence
OneCloud. And a good part of what OneCloud does never reaches it anyway —
binning, restoring, moving and a new version are `db.set_value`, which
publishes nothing.

So OneCloud has its own event, `onecloud_change`, in the same place: the
File doctype's room, which the explorer joins the way a list view does.
What changed is said as keys, not names. Every desk user may join that room,
and a folder's id is its path — `Home/alice@x.com/Salaries` — so the keys
are an HMAC of the folder, or of the record a file is attached to, under the
site's encryption key. A listing says which keys it is watching (`watch`),
and the explorer re-asks for the listing when one of them is heard. The
re-asking goes through `may` like any listing, so an event tells nobody
anything about a file they may not open.

Views that are not one folder — Recent, Shared with Me, the Recycle Bin,
Requests, a search — watch everything (`ANY`) and redraw on any change,
at most once a second or so (the explorer waits for a pause).

Several changes in one request are one message, sent after the commit, so
nobody re-reads a folder before the change is in it.
"""

import hashlib
import hmac

import frappe
from frappe.realtime import get_doctype_room
from frappe.utils.password import get_encryption_key

EVENT = "onecloud_change"

#: A listing that redraws on any change.
ANY = "*"


def key(text: str) -> str:
	"""What a folder or record is called on the wire. Pure, given the site."""
	return hmac.new(get_encryption_key().encode(), text.encode(), hashlib.sha256).hexdigest()[:16]


def record_key(doctype: str, name: str) -> str:
	return key(f"record:{doctype}/{name}")


def keys_of(item) -> set:
	"""Where a File (a row or a Document) shows: its folder, and the record
	it is attached to."""
	out = set()
	folder, doctype, name = item.get("folder"), item.get("attached_to_doctype"), item.get("attached_to_name")
	if folder:
		out.add(key(folder))
	if doctype and name:
		out.add(record_key(doctype, name))
	return out


def announce(*items, folders: tuple | list = ()) -> None:
	"""Say that these Files (rows, or names) changed, and these folders with
	them; sent once, after the commit."""
	keys = set()
	for item in items:
		if isinstance(item, str):
			item = frappe.db.get_value(
				"File", item, ["folder", "attached_to_doctype", "attached_to_name"], as_dict=True
			) or {}
		keys |= keys_of(item or {})
	keys |= {key(folder) for folder in folders if folder}
	if not keys:
		return
	held = getattr(frappe.local, "onecloud_live", None)
	if held is None:
		held = set()
		frappe.local.onecloud_live = held
		frappe.db.after_commit.add(_send)
		frappe.db.after_rollback.add(_drop)
	held |= keys


def _send() -> None:
	held = getattr(frappe.local, "onecloud_live", None) or set()
	frappe.local.onecloud_live = None
	if held:
		frappe.publish_realtime(EVENT, {"keys": sorted(held)}, room=get_doctype_room("File"))


def _drop() -> None:
	frappe.local.onecloud_live = None


def changed(doc, method=None) -> None:
	"""File on_update and on_trash: whatever Frappe itself saved or deleted —
	an upload, a copy, a new folder, an attachment from any form."""
	before = doc.get_doc_before_save() if method == "on_update" else None
	announce(doc, folders=[before.folder] if before and before.folder != doc.folder else [])


def watch(node: str, searching: bool = False):
	"""The keys a listing of `node` redraws on."""
	from onedesk.one_storage import namespace as ns

	if searching:
		return ANY
	kind = ns.parse(node)
	if kind[0] == "mount":
		return []  # a server is read live, and tells us nothing
	if kind[0] == ns.RECORDS and len(kind) == 3:
		return [record_key(kind[1], kind[2])]
	if kind[0] in (ns.MY, ns.COMPANY, "file"):
		return [key(ns.folder_of(node))]
	return ANY
