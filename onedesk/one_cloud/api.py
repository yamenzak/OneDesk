"""The verbs of OneCloud: what the explorer, WebDAV and a mount all call.

Every one takes node ids (namespace.py), asks `namespace.may` first, and does
the work as the framework with that answer in hand."""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

from onedesk.one_cloud import live, mounts
from onedesk.one_cloud import namespace as ns

KEPT_DAYS = 30


def _item(node_id: str) -> dict:
	item = ns.row(node_id)
	if not item:
		frappe.throw(_("This item no longer exists."), frappe.DoesNotExistError)
	return item


def _need(item: dict, ptype: str) -> None:
	if not ns.may(item, ptype):
		frappe.throw(_("You can't change {0}.").format(item.get("file_name")), frappe.PermissionError)


def _target(node_id: str) -> tuple:
	"""Where things put into `node_id` go: ("folder", File name),
	("record", doctype, name) or ("mount", node id)."""
	if mounts.is_mount(node_id):
		return ("mount", node_id)
	kind = ns.parse(node_id)
	if kind[0] == "featured":
		if not frappe.has_permission("Project", "write", kind[1]):
			frappe.throw(_("You can't add files to {0}.").format(kind[1]), frappe.PermissionError)
		return ("record", "Project", kind[1], "featured")
	if kind[0] == "own":
		kind = (ns.RECORDS, "Project", kind[1])
	if kind[0] == ns.RECORDS and len(kind) == 3:
		if not ns.may_add(kind[1], kind[2]):
			frappe.throw(_("You can't add files to {0}.").format(kind[2]), frappe.PermissionError)
		return ("record", kind[1], kind[2])
	folder = ns.folder_of(node_id)
	if not folder:
		frappe.throw(_("You can't add items here."))
	if not ns.may(_item(folder), "add"):
		frappe.throw(_("You can't add to this folder."), frappe.PermissionError)
	return ("folder", folder)


def _taken(folder: str, but: str | None = None) -> set:
	"""The names already used in a folder, leaving out `but` itself."""
	filters = {"folder": folder}
	if but:
		filters["name"] = ["!=", but]
	return set(frappe.get_all("File", filters=filters, pluck="file_name"))


def _searched(node: str, search: str, everywhere: int) -> list[dict]:
	"""What is called that, then what has it written inside (one_ai/reading/search.py)."""
	from onedesk.one_ai.reading import search as inside

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
			frappe.throw(_("This item no longer exists."), frappe.DoesNotExistError)
	can_add = False
	if kind[0] in (ns.MY, ns.COMPANY, "file"):
		can_add = ns.may(_item(ns.folder_of(node)), "add")
	elif kind[0] == ns.RECORDS and len(kind) == 3:
		can_add = ns.may_add(kind[1], kind[2])
	elif kind[0] == "own":
		can_add = bool(frappe.has_permission("Project", "write", kind[1]))
	elif kind[0] == "featured":
		can_add = bool(frappe.has_permission("Project", "write", kind[1]))
	elif kind[0] == "mount":
		can_add = True
	from onedesk.one_cloud import opening, oneos

	items = _searched(node, search, int(everywhere or 0)) if search else ns.children(node)
	opening.editing(items)
	return {
		"node": node,
		"trail": ns.trail(node),
		"watch": live.watch(node, bool(search)),
		"items": items,
		"oneos": oneos.offered(),
		"can_add": can_add,
		"can_make_folder": can_add and kind[0] not in (ns.RECORDS, "featured", "own"),
		"can_make_library": kind[0] == ns.LIBRARIES and ns._staff(frappe.session.user),
		"can_make_mount": kind[0] == ns.MOUNTS and ns._staff(frappe.session.user),
	}


@frappe.whitelist()
@frappe.read_only()
def folders(node: str = ns.ROOT) -> list[dict]:
	"""The navigation pane: only what can be opened."""
	return [one for one in ns.children(node) if one.get("folder")]


@frappe.whitelist(methods=["GET"])
@frappe.read_only()
def capacity() -> list[dict]:
	"""How full the workspace is, for the bars at the foot of OneCloud's rail:
	files and database against the plan. A limit of nothing draws a size with
	no bar. Where each number comes from is in AGENTS.md, Under the hood."""
	from frappe.utils import cint

	from onedesk.one import account
	from onedesk.account_center import heads

	held = frappe.get_single("Workspace Account")
	linked = account.configured()
	if linked:
		files = cint(held.storage_bytes)
	else:
		files = cint(frappe.db.sql("select coalesce(sum(file_size), 0) from `tabFile` where is_folder = 0")[0][0])
	rows = (
		("storage", _("Storage"), files, cint(held.storage_limit) if linked else 0),
		("database", _("Database"), account.database_bytes(), cint(held.database_limit) if linked else 0),
	)
	return [
		{
			"key": key,
			"label": label,
			"used": used,
			"limit": limit,
			"said": _("{0} of {1}").format(heads.size(used), heads.size(limit)) if limit else _("{0} used").format(heads.size(used)),
			"near": bool(limit) and used >= limit * account.NEARLY_FULL,
			"over": bool(limit) and used > limit,
		}
		for key, label, used, limit in rows
	]


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
		frappe.throw(_("Records can't contain folders."))
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
		frappe.throw(_("Name is required."))
	if name == item.file_name:
		return ns.node(item)
	name = ns.unique_name(name, _taken(item.folder, but=node) if item.folder else set())
	frappe.db.set_value("File", node, "file_name", name)
	live.announce(item)
	if item.is_folder:
		node = _rename_folder(node)
	_note(node, _("renamed it from {0}").format(item.file_name))
	return ns.node(ns.row(node))


READ_AT_MOST = 2 * 1024 * 1024


def _content(item) -> bytes:
	from onedesk.one_cloud import store

	if store.is_stored(item.file_url):
		return store.get(store.key_of(item.file_url))
	content = frappe.get_doc("File", item.name).get_content()
	return content.encode() if isinstance(content, str) else content or b""


@frappe.whitelist()
def content(node: str) -> None:
	"""A file's bytes from our own address, for what reads a file in the page
	(the viewer's PDF reader, the picture editor), since a stored file's
	address leads off to the store, which a page may not read."""
	item = _item(node)
	_need(item, "read")
	if item.is_folder:
		frappe.throw(_("A folder has no content."))
	frappe.local.response.filename = item.file_name
	frappe.local.response.filecontent = _content(item)
	frappe.local.response.type = "binary"


@frappe.whitelist()
def text(node: str) -> dict:
	"""A text file's words, for the viewer: its first 2 MB, read where it is
	kept, since a stored file's address leads off to the store, which a page
	may not read."""
	item = _item(node)
	_need(item, "read")
	if item.is_folder:
		frappe.throw(_("A folder has no text."))
	content = _content(item)
	return {"text": content[:READ_AT_MOST].decode("utf-8", errors="replace"), "cut": len(content) > READ_AT_MOST}


COLORS = ("red", "amber", "green", "cyan", "blue", "violet", "pink")


@frappe.whitelist(methods=["POST"])
def color(nodes: str | list, color: str | None = None) -> list[str]:
	"""Folders drawn in a colour, or in none: for everybody who sees them, by
	whoever may change them."""
	if color and color not in COLORS:
		frappe.throw(_("Choose one of the colors offered."))
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	done = []
	for node in nodes:
		if mounts.is_mount(node):
			continue
		item = _item(node)
		if not item.is_folder:
			continue
		_need(item, "write")
		frappe.db.set_value("File", node, "one_color", color or None, update_modified=False)
		live.announce(item)
		done.append(node)
	return done


def _note(name: str, what: str) -> None:
	from onedesk.one_cloud import history

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
		if _refeature(item, where):
			moved.append(node_id)
			continue
		if where[0] == "record" or attached:
			moved += copy([node_id], target)
			continue
		_need(item, "write")
		if item.one_home_of:
			frappe.throw(_("My Files cannot be moved."))
		if _leaves_its_owner(item, where[1]):
			frappe.throw(_("{0} is in someone else's files. Copy it instead.").format(item.file_name))
		if item.folder == where[1]:
			continue
		if item.is_folder and ns.would_loop(node_id, ns.ancestors(where[1]), where[1]):
			frappe.throw(_("A folder can't be moved into itself."))
		name = ns.unique_name(item.file_name, _taken(where[1]))
		if name != item.file_name:
			frappe.db.set_value("File", node_id, "file_name", name)
		frappe.db.set_value("File", node_id, "folder", where[1])
		live.announce(item, folders=[where[1]])
		moved.append(_rename_folder(node_id) if item.is_folder else node_id)
		_note(moved[-1], _("moved it from {0}").format(frappe.db.get_value("File", item.folder, "file_name") or item.folder))
	return moved


def _refeature(item: dict, where: tuple) -> bool:
	"""A project's own file moved between its folder and its Featured Media
	is the same file, marked or not: nothing is copied. Whether it was."""
	if where[0] != "record" or where[1] != "Project" or item.attached_to_doctype != "Project":
		return False
	if item.attached_to_name != where[2]:
		return False
	from onedesk.one_project import media

	on = len(where) > 3
	if bool(item.get("one_featured")) != on:
		_need(item, "write")
		media.feature(item.name, on)
	return True


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
			frappe.throw(_("You can't open {0}.").format(item.file_name), frappe.PermissionError)
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
			frappe.throw(_("You can't open {0}.").format(item.file_name), frappe.PermissionError)
		if not doctype:
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
	from onedesk.one_cloud import upload

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
				frappe.throw(_("You can't open {0}.").format(item.file_name), frappe.PermissionError)
			if item.is_folder:
				frappe.throw(_("Folders can't be copied to or from a server. Copy the files in {0} instead.").format(item.file_name))
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
			frappe.throw(_("Records can't contain folders."))
		if ns.would_loop(item.name, ns.ancestors(where[1]), where[1]):
			frappe.throw(_("A folder can't be moved into itself."))
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
		"is_private": 1 if item.get("one_featured") else item.is_private,
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
		if len(where) > 3:
			from onedesk.one_project import media

			media.check(item.file_name)
			fields.update(one_featured=1, is_private=0)
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
		_tell_holders(item)
		binned += 1
	return {"binned": binned, "removed": removed}


def _tell_holders(item) -> None:
	"""Whoever has a file open when it goes to the Recycle Bin hears so."""
	if item.is_folder:
		return
	from onedesk.one_cloud import lease, tell

	others = [user for user in lease.in_it(item.name) if user != frappe.session.user]
	if others:
		tell.deleted_while_open(others, item)


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
		_note(back[-1], _("restored it from the Recycle Bin"))
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
	(one_ai/reading/keep.py)."""
	from onedesk.one_ai.reading import keep

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
