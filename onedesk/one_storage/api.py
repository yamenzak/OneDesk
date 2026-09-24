"""The verbs of OneCloud: what the explorer, WebDAV and a mount all call.

Every one takes node ids (namespace.py), asks `namespace.may` first, and does
the work as the framework with that answer in hand — so File's own
permissions, written for attachments, do not decide who may rename a folder
in somebody's My Files.

**Moving across is copying.** Within the stored folders a move is a move.
Between a record and a folder it is a copy, the way an explorer copies
between two drives: dragging an invoice's PDF into My Files must not take it
off the invoice, and dropping a file on a record attaches a copy to it. A
copy is a new File row naming the same object, so no bytes move either way.

**Deleting is into the Recycle Bin** for anything in a folder, for thirty
days, then gone (`purge_old`). Deleting a record's file removes the
attachment, as it does on the record's own page.
"""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

from onedesk.one_storage import live, mounts
from onedesk.one_storage import namespace as ns

#: How long the Recycle Bin keeps things.
KEPT_DAYS = 30


def _item(node_id: str) -> dict:
	item = ns.row(node_id)
	if not item:
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	return item


def _need(item: dict, ptype: str) -> None:
	if not ns.may(item, ptype):
		frappe.throw(_("You may not change {0}.").format(item.get("file_name")), frappe.PermissionError)


def _target(node_id: str) -> tuple:
	"""Where things put into `node_id` go: ("folder", File name),
	("record", doctype, name) or ("mount", node id)."""
	if mounts.is_mount(node_id):
		return ("mount", node_id)
	kind = ns.parse(node_id)
	if kind[0] == ns.RECORDS and len(kind) == 3:
		if not frappe.has_permission(kind[1], "write", kind[2]):
			frappe.throw(_("You may not add files to {0}.").format(kind[2]), frappe.PermissionError)
		return ("record", kind[1], kind[2])
	folder = ns.folder_of(node_id)
	if not folder:
		frappe.throw(_("Nothing can be put here."))
	if not ns.may(_item(folder), "add"):
		frappe.throw(_("You may not add to this folder."), frappe.PermissionError)
	return ("folder", folder)


def _taken(folder: str, but: str | None = None) -> set:
	"""The names already used in a folder, leaving out `but` itself."""
	filters = {"folder": folder}
	if but:
		filters["name"] = ["!=", but]
	return set(frappe.get_all("File", filters=filters, pluck="file_name"))


def _searched(node: str, search: str, everywhere: int) -> list[dict]:
	"""What is called that, then what has it written inside (one_intake/search.py)."""
	from onedesk.one_intake import search as inside

	by_name = ns.everywhere(search) if everywhere else ns.search(node, search)
	kind = ns.parse(node)
	if not everywhere and kind[0] not in (ns.MY, ns.COMPANY, "file", ns.ROOT):
		return by_name
	under = None if everywhere or kind[0] == ns.ROOT else ns.below(ns.folder_of(node))
	named = {one["id"] for one in by_name}
	return by_name + [one for one in inside.in_files(search, under) if one["id"] not in named]


@frappe.whitelist()
@frappe.read_only()
def listing(node: str = ns.ROOT, search: str | None = None, everywhere: int = 0) -> dict:
	"""A node's contents, its trail, and what the reader may do there. With
	`search`, what is called that under the node, or with `everywhere`
	anywhere the reader may look."""
	kind = ns.parse(node)
	if kind[0] == "file":
		item = _item(node)
		if not item.is_folder or not ns.may(item):
			frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	can_add = False
	if kind[0] in (ns.MY, ns.COMPANY, "file"):
		can_add = ns.may(_item(ns.folder_of(node)), "add")
	elif kind[0] == ns.RECORDS and len(kind) == 3:
		can_add = bool(frappe.has_permission(kind[1], "write", kind[2]))
	elif kind[0] == "mount":
		# The server decides; a refusal comes back as its own words.
		can_add = True
	return {
		"node": node,
		"trail": ns.trail(node),
		"watch": live.watch(node, bool(search)),
		"items": _searched(node, search, int(everywhere or 0)) if search else ns.children(node),
		"can_add": can_add,
		"can_make_folder": can_add and kind[0] != ns.RECORDS,
		"can_make_library": kind[0] == ns.LIBRARIES and ns._staff(frappe.session.user),
		"can_make_mount": kind[0] == ns.MOUNTS and ns._staff(frappe.session.user),
	}


@frappe.whitelist()
@frappe.read_only()
def folders(node: str = ns.ROOT) -> list[dict]:
	"""The navigation pane: only what can be opened."""
	return [one for one in ns.children(node) if one.get("folder")]


@frappe.whitelist()
@frappe.read_only()
def resolve(path: str) -> str:
	"""The node a typed path names — `My Files/Projects/2026` — walking the
	same listings the explorer draws, so it finds nothing the reader could not
	have clicked their way to."""
	node = ns.ROOT
	for part in [one.strip() for one in (path or "").replace("\\", "/").split("/") if one.strip()]:
		wanted = part.lower()
		found = next(
			(
				one
				for one in ns.children(node)
				if one.get("folder")
				and wanted in (one["name"].lower(), one["id"].rsplit("/", 1)[-1].lower(), (one.get("doctype") or "").lower())
			),
			None,
		)
		if not found:
			frappe.throw(_("There is no {0} here.").format(part), frappe.DoesNotExistError)
		node = found["id"]
	return node


@frappe.whitelist(methods=["POST"])
def make_folder(parent: str, name: str) -> dict:
	if mounts.is_mount(parent):
		return mounts.make_folder(parent, _clean(name) or _("New folder"))
	where = _target(parent)
	if where[0] != "folder":
		frappe.throw(_("A record holds files, not folders."))
	name = _clean(name) or _("New folder")
	doc = frappe.get_doc(
		{"doctype": "File", "is_folder": 1, "file_name": ns.unique_name(name, _taken(where[1])), "folder": where[1]}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return ns.node(ns.row(doc.name))


@frappe.whitelist(methods=["POST"])
def rename(node: str, name: str) -> dict:
	if mounts.is_mount(node):
		return mounts.rename(node, _clean(name))
	item = _item(node)
	_need(item, "write")
	if item.one_home_of:
		frappe.throw(_("My Files cannot be renamed."))
	name = _clean(name)
	if not name:
		frappe.throw(_("Give it a name."))
	if name == item.file_name:
		return ns.node(item)
	name = ns.unique_name(name, _taken(item.folder, but=node) if item.folder else set())
	frappe.db.set_value("File", node, "file_name", name)
	live.announce(item)
	if item.is_folder:
		node = _rename_folder(node)
	_note(node, _("renamed it from {0}").format(item.file_name))
	return ns.node(ns.row(node))


def _note(name: str, what: str) -> None:
	from onedesk.one_storage import history

	history.note(name, what)


def _rename_folder(name: str) -> str:
	"""A folder's id is its path, so a new name or place is a new id."""
	from frappe.model.rename_doc import rename_doc

	doc = frappe.get_doc("File", name)
	wanted = doc.get_name_based_on_parent_folder()
	if wanted and wanted != name and not frappe.db.exists("File", wanted):
		return rename_doc("File", name, wanted, ignore_permissions=True, show_alert=False)
	return name


@frappe.whitelist(methods=["POST"])
def move(nodes: str | list, target: str) -> list[str]:
	"""Into a folder; onto a record, or out of one, it copies."""
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	across = _across(nodes, target, move=True)
	if across is not None:
		return across
	where = _target(target)
	moved = []
	for node_id in nodes:
		item = _item(node_id)
		attached = bool(item.attached_to_doctype and item.attached_to_name)
		if where[0] == "record" or attached:
			moved += copy([node_id], target)
			continue
		_need(item, "write")
		if item.one_home_of:
			frappe.throw(_("My Files cannot be moved."))
		if _leaves_its_owner(item, where[1]):
			frappe.throw(_("{0} is in somebody else's files. Copy it instead.").format(item.file_name))
		if item.folder == where[1]:
			continue
		if item.is_folder and ns.would_loop(node_id, ns.ancestors(where[1]), where[1]):
			frappe.throw(_("A folder cannot go inside itself."))
		name = ns.unique_name(item.file_name, _taken(where[1]))
		if name != item.file_name:
			frappe.db.set_value("File", node_id, "file_name", name)
		frappe.db.set_value("File", node_id, "folder", where[1])
		live.announce(item, folders=[where[1]])
		moved.append(_rename_folder(node_id) if item.is_folder else node_id)
		_note(moved[-1], _("moved it from {0}").format(frappe.db.get_value("File", item.folder, "file_name") or item.folder))
	return moved


def _leaves_its_owner(item: dict, folder: str) -> bool:
	"""Whether moving `item` into `folder` would carry it out of somebody
	else's files: what was shared with you, you may reorganise inside the
	folder it was shared in, and copy out, but not take."""
	user = frappe.session.user
	source = ns.space(item)
	return user != "Administrator" and source[0] == "home" and source[1] != user and ns.inside(folder) != source


@frappe.whitelist(methods=["POST"])
def copy(nodes: str | list, target: str) -> list[str]:
	"""New rows naming the same objects: no bytes are copied."""
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	across = _across(nodes, target, move=False)
	if across is not None:
		return across
	where = _target(target)
	made = []
	for node_id in nodes:
		item = _item(node_id)
		if not ns.may(item):
			frappe.throw(_("You may not open {0}.").format(item.file_name), frappe.PermissionError)
		made.append(_copy(item, where))
	return made


@frappe.whitelist(methods=["POST"])
def attach(nodes: str | list, doctype: str | None = None, docname: str | None = None, fieldname: str | None = None) -> list[dict]:
	"""Files chosen from OneCloud in Frappe's upload dialog: what its Library
	did — a new File row on the same object, attached as `upload_file` would
	attach an upload — but allowed by `namespace.may` rather than by Frappe's
	File permission, which knows nothing of a shared folder."""
	from frappe.handler import check_write_permission

	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	check_write_permission(doctype, docname)
	made = []
	for node_id in nodes:
		item = _item(node_id)
		if item.is_folder:
			frappe.throw(_("{0} is a folder. Choose the files in it.").format(item.file_name))
		if not ns.may(item):
			frappe.throw(_("You may not open {0}.").format(item.file_name), frappe.PermissionError)
		if not doctype:
			# Nothing to attach it to: a new message in OneMail, whose sending
			# copies it onto the message. A row of its own would only be a stray
			# copy in My Files.
			made.append(frappe.get_doc("File", item.name).as_dict())
			continue
		doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": item.file_name,
				"file_url": item.file_url,
				"is_private": item.is_private,
				"file_size": item.file_size,
				"content_hash": frappe.db.get_value("File", item.name, "content_hash"),
				"attached_to_doctype": doctype,
				"attached_to_name": docname,
				"attached_to_field": fieldname,
			}
		)
		doc.flags.ignore_permissions = True
		doc.flags.copy_from_existing_file = True
		doc.insert()
		made.append(doc.as_dict())
	return made


def _across(nodes: list, target: str, move: bool) -> list[str] | None:
	"""Moves and copies that touch a server, or None for those that do not.
	Within one server a move is the server's own rename; anything else
	carries the bytes over, the way a copy between two drives does."""
	if not any(mounts.is_mount(one) for one in [*nodes, target]):
		return None
	from onedesk.one_storage import upload

	done = []
	for node in nodes:
		if move and mounts.is_mount(node) and mounts.is_mount(target) and mounts.split(node)[0] == mounts.split(target)[0]:
			done.append(mounts.move_within(node, target))
			continue
		if mounts.is_mount(node):
			name, content = mounts.read(node)
		else:
			item = _item(node)
			if not ns.may(item):
				frappe.throw(_("You may not open {0}.").format(item.file_name), frappe.PermissionError)
			if item.is_folder:
				frappe.throw(_("Copy the files in {0}, not the folder, to or from a server.").format(item.file_name))
			content = frappe.get_doc("File", item.name).get_content()
			name, content = item.file_name, content if isinstance(content, bytes) else content.encode()
		if mounts.is_mount(target):
			done.append(mounts.write(target, name, content)["id"])
		else:
			done.append(upload._place(target, None, {"file_name": name, "content": content})["id"])
	return done


def _copy(item: dict, where: tuple) -> str:
	if item.is_folder:
		if where[0] == "record":
			frappe.throw(_("A record holds files, not folders."))
		if ns.would_loop(item.name, ns.ancestors(where[1]), where[1]):
			frappe.throw(_("A folder cannot go inside itself."))
		folder = frappe.get_doc(
			{
				"doctype": "File",
				"is_folder": 1,
				"file_name": ns.unique_name(item.file_name, _taken(where[1])),
				"folder": where[1],
			}
		)
		folder.flags.ignore_permissions = True
		folder.insert()
		for child in frappe.get_all("File", filters={"folder": item.name, "one_deleted": 0}, fields=ns.FIELDS):
			_copy(child, ("folder", folder.name))
		return folder.name
	fields = {
		"doctype": "File",
		"file_url": item.file_url,
		"is_private": item.is_private,
		"file_size": item.file_size,
		"content_hash": frappe.db.get_value("File", item.name, "content_hash"),
	}
	if where[0] == "record":
		taken = set(
			frappe.get_all(
				"File",
				filters={"attached_to_doctype": where[1], "attached_to_name": where[2]},
				pluck="file_name",
			)
		)
		fields.update(
			file_name=ns.unique_name(item.file_name, taken),
			attached_to_doctype=where[1],
			attached_to_name=where[2],
		)
	else:
		fields.update(file_name=ns.unique_name(item.file_name, _taken(where[1])), folder=where[1])
	doc = frappe.get_doc(fields)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


@frappe.whitelist(methods=["POST"])
def delete(nodes: str | list) -> dict:
	"""Folders and their files to the Recycle Bin; a record's file off the
	record; a server's file off the server."""
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	remote = [one for one in nodes if mounts.is_mount(one)]
	nodes = [one for one in nodes if not mounts.is_mount(one)]
	binned, removed = 0, mounts.delete(remote) if remote else 0
	for node_id in nodes:
		item = _item(node_id)
		_need(item, "write")
		if item.one_home_of or node_id in (ns.HOME, ns.ATTACHMENTS):
			frappe.throw(_("{0} cannot be deleted.").format(item.file_name))
		if item.attached_to_doctype and item.attached_to_name:
			frappe.delete_doc("File", node_id, ignore_permissions=True)
			removed += 1
			continue
		frappe.db.set_value(
			"File",
			node_id,
			{"one_deleted": 1, "one_deleted_on": now_datetime(), "one_deleted_by": frappe.session.user},
		)
		live.announce(item)
		binned += 1
	return {"binned": binned, "removed": removed}


@frappe.whitelist(methods=["POST"])
def restore(nodes: str | list) -> list[str]:
	"""Back where it was, or to My Files if that is gone too."""
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	back = []
	for node_id in nodes:
		item = _item(node_id)
		if not item.one_deleted or not _deleted_by_reader(item):
			continue
		folder = item.folder
		if not folder or not frappe.db.exists("File", folder) or frappe.db.get_value("File", folder, "one_deleted"):
			folder = ns.home()
		name = ns.unique_name(item.file_name, _taken(folder, but=node_id))
		frappe.db.set_value(
			"File",
			node_id,
			{"one_deleted": 0, "one_deleted_on": None, "one_deleted_by": None, "folder": folder, "file_name": name},
		)
		live.announce(item, folders=[folder])
		back.append(_rename_folder(node_id) if item.is_folder and folder != item.folder else node_id)
		_note(back[-1], _("put it back from the Recycle Bin"))
	return back


def _deleted_by_reader(item: dict) -> bool:
	user = frappe.session.user
	return user == "Administrator" or user in (item.owner, item.one_deleted_by)


@frappe.whitelist(methods=["POST"])
def purge(nodes: str | list) -> int:
	"""Gone for good: out of the Recycle Bin, and the objects with it once
	nothing names them."""
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	gone = 0
	for node_id in nodes:
		item = _item(node_id)
		if not item.one_deleted or not _deleted_by_reader(item):
			continue
		gone += _erase(node_id)
	return gone


@frappe.whitelist(methods=["POST"])
def empty_bin() -> int:
	return purge([one["id"] for one in ns.binned()])


def _erase(name: str) -> int:
	"""A File and everything in it, deepest first. A document the law says
	must still be kept stays in the Recycle Bin, and so does its folder
	(one_intake/keep.py)."""
	from onedesk.one_intake import keep

	gone = 0
	for child in frappe.get_all("File", filters={"folder": name}, pluck="name"):
		gone += _erase(child)
	if frappe.db.exists("File", {"folder": name}) or keep.held(frappe.get_doc("File", name)):
		return gone
	frappe.delete_doc("File", name, ignore_permissions=True, force=True)
	return gone + 1


def purge_old() -> None:
	"""Daily: what has been in the Recycle Bin longer than it keeps things."""
	cutoff = add_days(now_datetime(), -KEPT_DAYS)
	for name in frappe.get_all(
		"File", filters={"one_deleted": 1, "one_deleted_on": ["<", cutoff]}, pluck="name", order_by="one_deleted_on asc"
	):
		if frappe.db.exists("File", name):
			try:
				_erase(name)
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				frappe.log_error(title=f"OneCloud could not empty {name} from the Recycle Bin")


def _clean(name: str | None) -> str:
	"""A name as a folder or file may have one: no slashes, trimmed. Pure."""
	return " ".join((name or "").replace("/", " ").replace("\\", " ").split())[:140]
