"""What OneAI does in OneCloud: knows the folder open and the file chosen,
reads a file's text, says who can see a file, and says what takes the space.

Everything is read as the reader, through the explorer's own rule
(`namespace.may`): a file OneAI may read is a file the reader may open. A
file's text goes to the model only when the reader asks about it, and
nothing of it is kept but the answer. Finding a file by what it says is
OneIntake's `find_documents`, which already checks each hit the same way.

Nothing here changes a file. Sharing, moving and deleting stay the
explorer's, where the reader sees what they are doing.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import cint, get_fullname

#: Characters of a file's text given to the model.
MOST_TEXT = 12000

#: Files listed when asked what takes the space.
MOST_LISTED = 15

SUGGESTIONS = {
	# In a folder, with nothing chosen.
	"page:onecloud": [
		{
			# The reader says what the file is about; searched by what it says.
			"label": _lt("Find a file…"),
			"ask": _lt("Find the file that "),
			"fill": True,
			"expects": "find_documents",
		},
		{
			"label": _lt("What is taking the space?"),
			"ask": _lt("What is taking the most space in my files, and what could I clear out?"),
			"expects": "largest_files",
		},
	],
	# With one file chosen (oneai.js names the section `file`).
	"page:onecloud/file": [
		{
			"label": _lt("Summarise this file"),
			"ask": _lt(
				"Summarise this file in a few lines. Who is it from or for, and does anything in it need doing?"
			),
			"expects": "open_file",
		},
		{
			"label": _lt("Who can see this?"),
			"ask": _lt("Who can see this file, and how?"),
			"expects": "who_can_see",
		},
		{
			"label": _lt("Find a file…"),
			"ask": _lt("Find the file that "),
			"fill": True,
			"expects": "find_documents",
		},
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on the OneCloud page: the folder open,
	and the file chosen, when the reader may open them."""
	if said.get("page") != "onecloud":
		return None
	from onedesk.one_storage import namespace as ns

	where = "The reader is in OneCloud, the workspace's files"
	folder = _named(said.get("folder") or "")
	if folder:
		where += f', in the folder "{folder}" (its id is {said.get("folder")})'
	chosen = ns.row(said.get("record") or "") if said.get("record") else None
	if chosen and not chosen.get("is_folder") and ns.may(chosen):
		where += f', with the file "{chosen.file_name}" chosen (its id is {chosen.name})'
	return (
		where + ". open_file reads a file's text; who_can_see says who can see a file and how; "
		"largest_files says what takes the space; find_documents finds a file by what is written in it. "
		"Nothing is changed from here: sharing, moving and deleting are done in the explorer. How OneCloud "
		"works is in its documentation (how_to)."
	)


def _named(node: str) -> str | None:
	"""A folder's name as the reader sees it, or None when they may not."""
	from onedesk.one_storage import namespace as ns

	if not node:
		return None
	if node.startswith("@"):
		return {
			ns.MY: "My Files",
			ns.SHARED: "Shared with Me",
			ns.COMPANY: "Company",
			ns.RECORDS: "Records",
			ns.BIN: "Recycle Bin",
		}.get(node, node.lstrip("@").replace("-", " ").title())
	item = ns.row(node)
	if not item or not ns.may(item):
		return None
	return "My Files" if item.get("one_home_of") else item.file_name


def _file(file: str):
	"""A file the reader may open, or the reason there is none."""
	from onedesk.one_storage import namespace as ns

	item = ns.row(file or "")
	if not item or item.get("one_deleted") or not ns.may(item):
		return None, {"error": "There is no such file the reader may open."}
	if item.get("is_folder"):
		return None, {"error": "That is a folder. Ask about a file in it."}
	return item, None


def open_file(
	file: Annotated[str, "The file's id, as the page names it."],
) -> dict:
	"""A file the reader may open: what it is, where it is, who owns it, and
	its text (what OneIntake read of it, or read now). Read it before
	summarising a file or answering a question about what it says."""
	from onedesk.one_intake import read

	item, refused = _file(file)
	if refused:
		return refused
	said = {
		"name": item.file_name,
		"size": cint(item.file_size),
		"modified": str(item.modified),
		"owner": get_fullname(item.owner),
		"record": [item.attached_to_doctype, item.attached_to_name] if item.get("attached_to_name") else None,
	}
	# Read once per content: a copy of a file is found by what it holds. The
	# reader may open the file (`_file`, the explorer's own rule), so what
	# OneIntake read of it is theirs to see: nobody may read a Reading row by
	# itself, which is why this is not `get_list`.
	hashed = frappe.db.get_value("File", item.name, "content_hash")
	reading = frappe.get_all(
		"Reading",
		filters={"source_doctype": "File", "source_name": item.name, "state": ["in", ("Read", "Understood")]},
		fields=["text", "kind", "summary"],
		order_by="modified desc",
		limit=1,
	) or (
		hashed
		and frappe.get_all(
			"Reading",
			filters={"key": hashed, "state": ["in", ("Read", "Understood")]},
			fields=["text", "kind", "summary"],
			limit=1,
		)
	)
	if reading and (reading[0].text or "").strip():
		said.update(
			{"kind": reading[0].kind, "summary": reading[0].summary, "text": reading[0].text[:MOST_TEXT]}
		)
		return said
	try:
		content = frappe.get_doc("File", item.name).get_content()
	except Exception:
		return {**said, "error": "The file could not be opened."}
	if isinstance(content, str):
		content = content.encode()
	text = read.read(item.file_name, content or b"")
	if text.needs in ("eyes", "ears"):
		return {
			**said,
			"text": None,
			"note": "It is a scan, a photo or a recording. Read with OneAI, on the file's menu, reads it.",
		}
	if text.needs:
		return {**said, "text": None, "note": "It is locked with a password."}
	said["text"] = (text.text or "")[:MOST_TEXT] or None
	return said


def who_can_see(
	file: Annotated[str, "The file's id, as the page names it."],
) -> dict:
	"""Who can see a file the reader may open: its owner, the people it is
	shared with (and whether they may change it), those it reaches through a
	folder above it, and the links on it that reach people outside."""
	from onedesk.one_storage import links, share

	item, refused = _file(file)
	if refused:
		return refused
	if item.get("attached_to_name"):
		return {
			"name": item.file_name,
			"record": [item.attached_to_doctype, item.attached_to_name],
			"rule": "A record's file is seen by whoever may open the record.",
		}
	people = share.people(item.name)
	return {
		"name": item.file_name,
		"owner": people["owner"]["name"],
		"shared_with": [{"name": one["name"], "may_change": one["edit"]} for one in people["people"]],
		"through_a_folder": [
			{"name": one["name"], "may_change": one["edit"], "folder": one["from"]}
			for one in people["inherited"]
		],
		# The link's address is a key; the model is told what it reaches, not the key.
		"links": [
			{
				"reaches": "only the people invited" if one["invitees"] else one["audience"],
				"invited": one["invitees"],
				"password": one["has_password"],
				"download": bool(one["allow_download"]),
				"expires": str(one["expires_on"]) if one["expires_on"] else None,
				"expired": one["expired"],
				"opened": one["opened"],
			}
			for one in links.links(item.name)
		],
	}


def largest_files() -> dict:
	"""The reader's own largest files, how much they take together, and how
	full the workspace's storage is. The files are the reader's own, not
	everybody's: what takes the space in their files is theirs to clear."""
	user = frappe.session.user
	# Only the reader's own files, by owner: nothing here reaches anybody else's.
	mine = frappe.get_all(
		"File",
		filters={"owner": user, "is_folder": 0, "one_deleted": 0},
		fields=["name", "file_name", "file_size", "modified", "folder"],
		order_by="file_size desc",
		limit=MOST_LISTED,
	)
	total = frappe.db.sql(
		"select coalesce(sum(file_size), 0) from `tabFile` where owner = %s and is_folder = 0 and ifnull(one_deleted, 0) = 0",
		user,
	)[0][0]
	binned = frappe.db.sql(
		"select coalesce(sum(file_size), 0) from `tabFile` where owner = %s and is_folder = 0 and one_deleted = 1",
		user,
	)[0][0]
	held = (
		frappe.get_single("Workspace Account") if frappe.db.exists("DocType", "Workspace Account") else None
	)
	return {
		"largest": [
			{
				"name": one.file_name,
				"id": one.name,
				"bytes": cint(one.file_size),
				"modified": str(one.modified),
			}
			for one in mine
		],
		"mine_bytes": cint(total),
		"in_recycle_bin_bytes": cint(binned),
		"workspace_used_bytes": cint(held.storage_bytes) if held else None,
		"workspace_limit_bytes": cint(held.storage_limit) if held else None,
		"note": "The Recycle Bin counts until it is emptied, or for thirty days.",
	}
