"""One tree of files, and who may do what in it.

The explorer, WebDAV and mounts all read this module and nothing else, so a
rule here is a rule everywhere. A node is named by an id:

- `@root` — the top: My Files, Shared with Me, Company, Records, Recycle Bin.
- `@my`, `@company` — stored folders under other names: the reader's own
  folder (`home`) and Frappe's own Home, less everybody's own folders and
  Frappe's Attachments folder.
- `@shared` — what other people have shared with the reader (stage 4).
- `@records`, `@records/<DocType>`, `@records/<DocType>/<name>` — derived:
  the doctypes the reader may read that have files, the records of one, and
  the files attached to one. Nothing is stored for them; they are worked out
  from `attached_to_*` whenever they are opened, so a record's folder is
  always exactly its attachments and is seen by exactly who may read it.
- `@mail`, `@mail/<mailbox>` — derived, like records: the reader's mailboxes,
  and the files that came or went with a mailbox's messages
  (one_mail/cloud.py). A message's files are here and not under Records.
- `@bin` — what the reader deleted, for thirty days.
- anything else — a File, by its name.

**Who may do what** is `may`, and nothing else decides it. A file attached to
a record answers to the record. Otherwise: its owner may do anything; somebody
signed in to a portal gets nothing more; a person's own folder and everything
in it is theirs; the Company folder is
everybody's to read and add to, and its items are their owner's or a
Workspace Administrator's to change. Sharing (stage 4) and libraries
(stage 6) add to this function and to nowhere else.
"""

import frappe
from frappe import _, _lt

from onedesk.one import roles

ROOT, MY, SHARED, COMPANY, RECORDS, BIN = "@root", "@my", "@shared", "@company", "@records", "@bin"

#: Every record's Files tab: OneCloud on the record's own room, drawn by
#: record_files.js. File itself has no room. See one/tabs.py.
TABS = [{"name": "files", "label": _lt("Files"), "order": 80, "leaves_out": ("File",)}]
LIBRARIES, RECENT, STARRED, MOUNTS, REQUESTS = "@libraries", "@recent", "@starred", "@mounts", "@requests"
MAIL = "@mail"
HOME, ATTACHMENTS, LIBRARY_ROOT = "Home", "Home/Attachments", "Home/Libraries"

#: A library member's role, as the DocShare that carries it: (write, share).
ROLES = {"Reader": (0, 0), "Member": (1, 0), "Owner": (1, 1)}

#: Frappe's own bookkeeping, which has files but no folder anybody wants.
#: A message's files are under Mail, by mailbox, rather than Records.
UNLISTED = frozenset(
	(
		"Prepared Report", "Data Import", "Data Export", "Access Log", "Error Log", "Deleted Document", "Version",
		"Communication",
	)
)  # fmt: skip

#: How deep a folder chain is walked before it is taken to be a loop.
DEEPEST = 64

FIELDS = [
	"name", "file_name", "is_folder", "folder", "file_url", "file_size", "is_private", "owner",
	"modified", "creation", "attached_to_doctype", "attached_to_name", "one_home_of", "one_deleted",
	"one_deleted_by", "one_deleted_on", "thumbnail_url", "file_type", "one_library", "_liked_by",
	"one_intake",
]  # fmt: skip


# ------------------------------------------------------------------ ids


def parse(node: str) -> tuple:
	"""What a node id names: (kind, *parts). Pure."""
	node = node or ROOT
	if node == ROOT or node in (MY, SHARED, COMPANY, BIN, RECORDS, LIBRARIES, RECENT, STARRED, MOUNTS, REQUESTS, MAIL):
		return (node,)
	if node.startswith(MAIL + "/"):
		return (MAIL, node[len(MAIL) + 1 :])
	if node.startswith("@request/"):
		return ("request", node)
	if node.startswith("@mount/"):
		return ("mount", node)
	if node.startswith(RECORDS + "/"):
		rest = node[len(RECORDS) + 1 :]
		doctype, _sep, name = rest.partition("/")
		return (RECORDS, doctype, name) if name else (RECORDS, doctype)
	return ("file", node)


def record_node(doctype: str, name: str | None = None) -> str:
	return f"{RECORDS}/{doctype}/{name}" if name else f"{RECORDS}/{doctype}"


def unique_name(wanted: str, taken: set) -> str:
	"""`wanted`, or `wanted (2)`, `(3)`… before its extension, the way an
	explorer keeps both. Pure."""
	if wanted not in taken:
		return wanted
	stem, dot, extension = wanted.rpartition(".")
	if not dot or not stem:
		stem, extension = wanted, ""
	n = 2
	while True:
		candidate = f"{stem} ({n}){'.' + extension if extension else ''}"
		if candidate not in taken:
			return candidate
		n += 1


def would_loop(moving: str, ancestors_of_target: list, target: str) -> bool:
	"""Whether putting `moving` into `target` puts a folder inside itself.
	Pure over the target's chain of parents."""
	return moving == target or moving in ancestors_of_target


# ------------------------------------------------------------ the folders


def home(user: str | None = None, create: bool = True) -> str | None:
	"""The File that is a person's My Files, made the first time it is asked for."""
	user = user or frappe.session.user
	found = frappe.db.get_value("File", {"one_home_of": user, "is_folder": 1}, "name")
	if found or not create or user == "Guest":
		return found
	taken = set(frappe.get_all("File", filters={"folder": HOME}, pluck="file_name"))
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"is_folder": 1,
			"file_name": unique_name(user, taken),
			"folder": HOME,
			"one_home_of": user,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def row(name: str) -> dict | None:
	found = frappe.get_all("File", filters={"name": name}, fields=FIELDS, limit=1)
	return found[0] if found else None


def ancestors(name: str) -> list[str]:
	"""A File's folders, nearest first."""
	chain, at = [], frappe.db.get_value("File", name, "folder")
	while at and len(chain) < DEEPEST:
		chain.append(at)
		at = frappe.db.get_value("File", at, "folder")
	return chain


def chain(folder: str | None) -> list[str]:
	"""A folder and the folders above it, nearest first; asked once a request
	per folder, since every file in a listing has the same one."""
	if not folder:
		return []
	held = _request("onecloud_chains")
	if folder not in held:
		held[folder] = [folder, *ancestors(folder)]
	return held[folder]


def grants(user: str | None = None) -> dict:
	"""What has been shared with `user`: {File name: "read" or "write"}. One
	query a request; `forget` clears it after a share changes."""
	user = user or frappe.session.user
	held = _request("onecloud_grants")
	if user not in held:
		rows = frappe.get_all(
			"DocShare",
			filters={"share_doctype": "File", "user": user, "read": 1},
			fields=["share_name", "write"],
		)
		held[user] = {one.share_name: "write" if one.write else "read" for one in rows}
	return held[user]


def _request(key: str) -> dict:
	"""A dict that lasts as long as this request does."""
	held = getattr(frappe.local, key, None)
	if held is None:
		held = {}
		setattr(frappe.local, key, held)
	return held


def forget() -> None:
	setattr(frappe.local, "onecloud_grants", {})
	setattr(frappe.local, "onecloud_chains", {})


def granted(item: dict, user: str) -> str | None:
	"""The most `user` has been given on this item, by a share on it or on any
	folder it is in: "write", "read" or None. Pure given `grants` and `chain`."""
	held = grants(user)
	if not held:
		return None
	best = None
	for name in [item["name"], *chain(item.get("folder"))]:
		right = held.get(name)
		if right == "write":
			return "write"
		best = best or right
	return best


def space(item: dict) -> tuple:
	"""Whose part of the tree a File is in: ("record", doctype, name),
	("home", person), ("library", folder), ("attachments",) or ("company",)."""
	if item.get("attached_to_doctype") and item.get("attached_to_name") and not item.get("is_folder"):
		return ("record", item["attached_to_doctype"], item["attached_to_name"])
	if item.get("one_home_of"):
		return ("home", item["one_home_of"])
	if item.get("one_library"):
		return ("library", item["name"])
	for folder in ancestors(item["name"]):
		if folder == ATTACHMENTS:
			return ("attachments",)
		found = frappe.db.get_value("File", folder, ["one_home_of", "one_library"], as_dict=True) or {}
		if found.get("one_home_of"):
			return ("home", found["one_home_of"])
		if found.get("one_library"):
			return ("library", folder)
	return ("company",)


# ------------------------------------------------------------- permission


def inside(folder: str) -> tuple:
	"""The space of whatever is put in `folder`, worked out once for a whole
	listing rather than once per file."""
	if folder == HOME:
		return ("company",)
	if folder == ATTACHMENTS:
		return ("attachments",)
	if folder == LIBRARY_ROOT:
		return ("libraries",)
	found = frappe.db.get_value("File", folder, ["one_home_of", "one_library"], as_dict=True) or {}
	if found.get("one_home_of"):
		return ("home", found["one_home_of"])
	if found.get("one_library"):
		return ("library", folder)
	return space({"name": folder, "is_folder": 1})


def may(item: dict, ptype: str = "read", user: str | None = None, where: tuple | None = None) -> bool:
	"""Whether `user` may `ptype` ("read", "write" or "add") this File. "add"
	is putting something into a folder; "write" is renaming, moving and
	deleting the item itself. `where` is the item's space when the caller
	already knows it."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if user == "Guest":
		return ptype == "read" and not item.get("is_private") and not item.get("is_folder")
	if item.get("attached_to_doctype") and item.get("attached_to_name") and not item.get("is_folder"):
		where = ("record", item["attached_to_doctype"], item["attached_to_name"])
	elif item.get("one_home_of"):
		where = ("home", item["one_home_of"])
	where = where or space(item)
	if where[0] == "record":
		return frappe.has_permission(where[1], "write" if ptype != "read" else "read", where[2], user=user)
	if where[0] in ("library", "libraries"):
		return _library_may(item, ptype, user, where)
	if item.get("owner") == user:
		return True
	# Somebody signed in to a portal — a customer, a supplier — sees the files
	# of records they may read and their own, and nothing of the staff's.
	if not _staff(user):
		return False
	# Shared with them, on the item or on a folder it is in.
	right = granted(item, user)
	if right == "write" or (right and ptype == "read"):
		return True
	if where[0] == "home":
		return where[1] == user
	if where[0] == "attachments":
		return False
	# The company folder: everybody's to read and add to; an item is changed by
	# whoever made it, or a Workspace Administrator.
	if ptype == "read":
		return item.get("is_folder") or not item.get("is_private") or _frappe_may(item, user)
	if ptype == "add":
		return bool(item.get("is_folder"))
	return roles.ADMINISTRATOR in frappe.get_roles(user)


def _library_may(item: dict, ptype: str, user: str, where: tuple) -> bool:
	"""A library is its members': readers read, members change what is in it,
	owners also rename it and say who is in it. Having made a file there is
	nothing once you are no longer a member. A Workspace Administrator may do
	anything, so that a library whose owners have all left is not lost."""
	if roles.ADMINISTRATOR in frappe.get_roles(user):
		return True
	if where[0] == "libraries" or not _staff(user):
		return False
	if item.get("one_library") and ptype == "write":
		return role_in(item["name"], user) == "Owner"
	right = granted(item, user)
	return right == "write" or (right == "read" and ptype == "read")


def role_in(library: str, user: str | None = None) -> str | None:
	"""A person's role in a library: "Owner", "Member", "Reader" or None."""
	user = user or frappe.session.user
	found = frappe.db.get_value(
		"DocShare", {"share_doctype": "File", "share_name": library, "user": user}, ["write", "share"], as_dict=True
	)
	if not found:
		return None
	return "Owner" if found.share else "Member" if found.write else "Reader"


def library_root() -> str:
	"""The folder libraries are kept in, made the first time it is needed.
	It is under Home like Attachments, and hidden from Company like it."""
	if not frappe.db.exists("File", LIBRARY_ROOT):
		doc = frappe.get_doc({"doctype": "File", "is_folder": 1, "file_name": "Libraries", "folder": HOME})
		doc.flags.ignore_permissions = True
		doc.insert()
	return LIBRARY_ROOT


def libraries(user: str | None = None) -> list[dict]:
	"""The libraries the reader is in — every one, for an administrator."""
	user = user or frappe.session.user
	filters = {"one_library": 1, "one_deleted": 0}
	if roles.ADMINISTRATOR not in frappe.get_roles(user) and user != "Administrator":
		mine = frappe.get_all(
			"DocShare", filters={"share_doctype": "File", "user": user, "read": 1}, pluck="share_name"
		)
		filters["name"] = ["in", mine or [""]]
	found = frappe.get_all("File", filters=filters, fields=FIELDS, order_by="file_name asc")
	return [{**node(one), "role": role_in(one.name, user)} for one in found]


def _staff(user: str) -> bool:
	return frappe.get_cached_value("User", user, "user_type") == "System User"


def _frappe_may(item: dict, user: str) -> bool:
	"""Frappe's own rule for a file, which is where a direct share lives."""
	from frappe.core.doctype.file.file import has_permission

	return has_permission(frappe._dict(item), "read", user=user)


# --------------------------------------------------------------- listing


def node(item: dict) -> dict:
	"""What the explorer draws for a File."""
	return {
		"id": item["name"],
		"name": _("My Files") if item.get("one_home_of") else item["file_name"],
		"folder": bool(item.get("is_folder")),
		"size": item.get("file_size") or 0,
		"modified": item.get("modified"),
		"owner": item.get("owner"),
		"url": item.get("file_url"),
		"thumbnail": item.get("thumbnail_url"),
		"private": bool(item.get("is_private")),
		"record": [item["attached_to_doctype"], item["attached_to_name"]]
		if item.get("attached_to_doctype") and item.get("attached_to_name")
		else None,
		"deleted": item.get("one_deleted_on"),
		"shared": bool(item.get("shared")),
		"starred": frappe.session.user in (item.get("_liked_by") or ""),
		**({"library": True, "icon": "library-big"} if item.get("one_library") else {}),
		**({"intake": True} if item.get("one_intake") else {}),
	}


def virtual(node_id: str, name: str, **more) -> dict:
	return {"id": node_id, "name": name, "folder": True, "virtual": True, **more}


def roots() -> list[dict]:
	return [
		virtual(MY, _("My Files"), icon="folder-heart"),
		virtual(RECENT, _("Recent"), icon="clock"),
		virtual(STARRED, _("Starred"), icon="star"),
		virtual(SHARED, _("Shared with Me"), icon="users"),
		virtual(LIBRARIES, _("Libraries"), icon="library-big"),
		virtual(COMPANY, _("Company"), icon="building-2"),
		virtual(RECORDS, _("Records"), icon="database"),
		virtual(MAIL, _("Mail"), icon="mail"),
		virtual(MOUNTS, _("Network"), icon="network"),
		virtual(REQUESTS, _("Requests"), icon="inbox"),
		virtual(BIN, _("Recycle Bin"), icon="trash-2"),
	]


def folder_of(node_id: str) -> str | None:
	"""The stored folder a node puts new things into, where it has one."""
	kind = parse(node_id)
	if kind[0] == MY:
		return home()
	if kind[0] == COMPANY:
		return HOME
	if kind[0] == "file":
		return node_id
	return None


def children(node_id: str, search: str | None = None) -> list[dict]:
	"""What is in a node, as the reader may see it: folders first."""
	kind = parse(node_id)
	if kind[0] == ROOT:
		return roots()
	if kind[0] == SHARED:
		return shared_with_me()
	if kind[0] == LIBRARIES:
		return libraries()
	if kind[0] in (RECENT, STARRED):
		from onedesk.one_storage import history

		return history.recent() if kind[0] == RECENT else history.starred()
	if kind[0] in (REQUESTS, "request"):
		from onedesk.one_storage import file_requests

		return file_requests.visible() if kind[0] == REQUESTS else file_requests.children(node_id)
	if kind[0] in (MOUNTS, "mount"):
		from onedesk.one_storage import mounts

		return mounts.visible() if kind[0] == MOUNTS else mounts.children(node_id)
	if kind[0] == BIN:
		return binned()
	if kind[0] == MAIL:
		from onedesk.one_mail import cloud

		return cloud.mailboxes() if len(kind) == 1 else cloud.files(kind[1], search)
	if kind[0] == RECORDS:
		if len(kind) == 1:
			return record_doctypes()
		if len(kind) == 2:
			return records(kind[1], search)
		return attachments(kind[1], kind[2])
	folder = folder_of(node_id)
	filters = {"folder": folder, "one_deleted": 0}
	found = frappe.get_all("File", filters=filters, fields=FIELDS, order_by="is_folder desc, file_name asc", limit=5000)
	# A file attached to a record lives in Records, whatever folder Frappe
	# filed it in.
	found = [one for one in found if one.is_folder or not (one.attached_to_doctype and one.attached_to_name)]
	if kind[0] == COMPANY:
		found = [one for one in found if not one.one_home_of and one.name not in (ATTACHMENTS, LIBRARY_ROOT)]
	if search:
		found = [one for one in found if search.lower() in (one.file_name or "").lower()]
	where = inside(folder)
	return [node(one) for one in mark_shared([one for one in found if may(one, where=where)])]


def mark_shared(items: list) -> list:
	"""Set `shared` on the items somebody has been given, in one query."""
	names = [one.name for one in items]
	shared = set(
		frappe.get_all("DocShare", filters={"share_doctype": "File", "share_name": ["in", names]}, pluck="share_name")
	) if names else set()
	for one in items:
		one.shared = one.name in shared
	return items


def shared_with_me(user: str | None = None) -> list[dict]:
	"""What other people have shared with the reader: only the top of each
	shared branch, since what is inside a shared folder comes with it."""
	from frappe.utils import get_fullname

	user = user or frappe.session.user
	held = grants(user)
	if not held:
		return []
	found = frappe.get_all(
		"File", filters={"name": ["in", list(held)], "one_deleted": 0}, fields=FIELDS, order_by="is_folder desc, file_name asc"
	)
	# A library one is a member of is under Libraries, not here.
	found = [one for one in found if one.owner != user and not one.one_library]
	names = {one.name for one in found}
	out = []
	for one in found:
		above = chain(one.folder)
		if names & set(above):
			continue
		if above and frappe.db.exists("File", {"name": ["in", above], "one_deleted": 1}):
			continue
		one.shared = True
		out.append({**node(one), "where": get_fullname(one.owner)})
	return out


def below(folder: str, most: int = 5000) -> list[str]:
	"""A folder and every live folder under it. From Home that is the Company
	tree only: the homes and Attachments under it are somebody else's."""
	out, edge = [folder], [folder]
	while edge and len(out) < most:
		rows = frappe.get_all(
			"File",
			filters={"folder": ["in", edge], "is_folder": 1, "one_deleted": 0},
			fields=["name", "one_home_of"],
		)
		edge = [
			one.name
			for one in rows
			if not (folder == HOME and (one.one_home_of or one.name in (ATTACHMENTS, LIBRARY_ROOT)))
		]
		out += edge
	return out


def search(node_id: str, text: str, most: int = 500) -> list[dict]:
	"""What is called `text` anywhere under a node, the way an explorer's
	search box looks through every folder below the one it is in."""
	kind = parse(node_id)
	if kind[0] == ROOT:
		return everywhere(text, most)
	if kind[0] not in (MY, COMPANY, "file"):
		return children(node_id, text)
	starts = [folder_of(node_id)]
	out = []
	for start in starts:
		inner = below(start)
		labels = {
			one.name: _("Company") if one.name == HOME else _("My Files") if one.one_home_of else one.file_name
			for one in frappe.get_all("File", filters={"name": ["in", inner]}, fields=["name", "file_name", "one_home_of"])
		}
		found = frappe.get_all(
			"File",
			filters={"folder": ["in", inner], "one_deleted": 0, "file_name": ["like", f"%{text}%"]},
			fields=FIELDS,
			order_by="is_folder desc, file_name asc",
			limit=most,
		)
		where = inside(start)
		for one in found:
			if start == HOME and (one.one_home_of or one.name in (ATTACHMENTS, LIBRARY_ROOT)):
				continue
			if not one.is_folder and one.attached_to_doctype and one.attached_to_name:
				continue
			if may(one, where=where):
				out.append({**node(one), "where": labels.get(one.folder), "parent": one.folder})
	return out[:most]


def everywhere(text: str, most: int = 200) -> list[dict]:
	"""Everything called `text` that the reader may open, wherever it is: My
	Files, Company, what is shared with them, their libraries, and the files
	of the records they may read. Servers on the Network are not searched;
	they are read live and one slow server would hold up every search."""
	text = (text or "").strip()
	if not text:
		return []
	like = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
	found = frappe.get_all(
		"File",
		filters={"one_deleted": 0, "file_name": ["like", like], "name": ["not in", [HOME, ATTACHMENTS, LIBRARY_ROOT]]},
		fields=FIELDS,
		order_by="modified desc",
		limit=most * 10,
	)
	folders = _folders()
	user = frappe.session.user
	out = []
	for one in found:
		if one.one_home_of or one.attached_to_doctype in UNLISTED:
			continue
		if one.one_library:
			where = ("library", one.name)
		elif one.attached_to_doctype and one.attached_to_name and not one.is_folder:
			where = ("record", one.attached_to_doctype, one.attached_to_name)
		else:
			where = placed(one.folder, folders)
			if not where:  # in a folder in the Recycle Bin
				continue
		if not may(one, where=where):
			continue
		out.append({**node(one), "where": _where_label(one, folders, user), "parent": _parent_of(one)})
		if len(out) >= most:
			break
	return out


def _folders() -> dict:
	"""Every folder, once a request: a search walks up from each file it
	finds, and asking the database once per step would be thousands."""
	held = _request("onecloud_folders")
	if not held:
		for one in frappe.get_all(
			"File", filters={"is_folder": 1}, fields=["name", "folder", "file_name", "one_home_of", "one_library", "one_deleted"]
		):
			held[one.name] = one
	return held


def placed(folder: str | None, folders: dict) -> tuple | None:
	"""The space of what is in `folder`, as `space` says it, read from
	`folders` without asking the database; None when a folder above it is
	in the Recycle Bin. Pure."""
	at, steps = folder, 0
	while at and steps <= DEEPEST + 2:
		found = folders.get(at)
		if not found:
			break
		if found.get("one_deleted"):
			return None
		if at == ATTACHMENTS:
			return ("attachments",)
		if at == HOME:
			return ("company",)
		if found.get("one_home_of"):
			return ("home", found["one_home_of"])
		if found.get("one_library"):
			return ("library", at)
		at, steps = found.get("folder"), steps + 1
	return ("company",)


def _where_label(item: dict, folders: dict, user: str) -> str:
	"""Where a search result is, in a word or two."""
	if item.get("attached_to_doctype") and item.get("attached_to_name") and not item.get("is_folder"):
		doctype = item["attached_to_doctype"]
		return f"{_(doctype)} {item['attached_to_name']}"
	parent = folders.get(item.get("folder")) or {}
	if item.get("folder") == HOME:
		return _("Company")
	if item.get("folder") == LIBRARY_ROOT:
		return _("Libraries")
	if parent.get("one_home_of"):
		return _("My Files") if parent["one_home_of"] == user else _("Shared with Me")
	return parent.get("file_name") or ""


def _parent_of(item: dict) -> str:
	"""The node a search result's "Open file location" goes to."""
	if item.get("attached_to_doctype") and item.get("attached_to_name") and not item.get("is_folder"):
		return record_node(item["attached_to_doctype"], item["attached_to_name"])
	if item.get("folder") == LIBRARY_ROOT:
		return LIBRARIES
	if item.get("folder") == HOME:
		return COMPANY
	return item.get("folder") or ROOT


def record_doctypes() -> list[dict]:
	counted = frappe.db.sql(
		"""select attached_to_doctype, count(*) from `tabFile`
		where is_folder = 0 and ifnull(attached_to_doctype, '') != '' and ifnull(attached_to_name, '') != ''
		group by attached_to_doctype order by attached_to_doctype"""
	)
	return [
		virtual(record_node(doctype), _(doctype), count=count, doctype=doctype)
		for doctype, count in counted
		if doctype not in UNLISTED and frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, "read")
	]


def records(doctype: str, search: str | None = None, most: int = 500) -> list[dict]:
	"""The records of a doctype that have files, newest file first, that the
	reader may read, each named by its title where it has one."""
	names = frappe.db.sql_list(
		"""select attached_to_name from `tabFile`
		where attached_to_doctype = %s and is_folder = 0 and ifnull(attached_to_name, '') != ''
		group by attached_to_name order by max(creation) desc limit 2000""",
		doctype,
	)
	if not names:
		return []
	meta = frappe.get_meta(doctype)
	title = meta.title_field if meta.title_field and meta.has_field(meta.title_field) else None
	fields = ["name", title] if title else ["name"]
	readable = {
		one.name: one
		for one in frappe.get_list(doctype, filters={"name": ["in", names]}, fields=fields, limit=len(names))
	}
	out = []
	for name in names:
		if name not in readable:
			continue
		label = str(name)
		if title and readable[name].get(title) and str(readable[name].get(title)) != str(name):
			label = f"{name} · {readable[name].get(title)}"
		if search and search.lower() not in label.lower():
			continue
		out.append(virtual(record_node(doctype, name), label, record=[doctype, name]))
		if len(out) >= most:
			break
	return out


def attachments(doctype: str, name: str) -> list[dict]:
	if not frappe.has_permission(doctype, "read", name):
		return []
	found = frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": name, "is_folder": 0},
		fields=FIELDS,
		order_by="file_name asc",
	)
	out = [node(one) for one in found]
	# Files that belong here as well as where they are kept (one_intake's File
	# Link). A link never grants read: only those the reader may open.
	linked = frappe.get_all("File Link", filters={"for_doctype": doctype, "for_name": name}, pluck="file")
	held = {one.name for one in found}
	if linked:
		for one in frappe.get_all("File", filters={"name": ["in", linked], "is_folder": 0}, fields=FIELDS, order_by="file_name asc"):
			if one.name not in held and may(one):
				out.append({**node(one), "linked": True})
	return out


def binned(user: str | None = None) -> list[dict]:
	"""What the reader deleted and may still restore: only the top of each
	deleted branch, since what is inside a deleted folder comes back with it."""
	user = user or frappe.session.user
	found = frappe.get_all(
		"File",
		filters={"one_deleted": 1},
		or_filters={"owner": user, "one_deleted_by": user},
		fields=FIELDS,
		order_by="one_deleted_on desc",
	)
	deleted = set(frappe.get_all("File", filters={"one_deleted": 1}, pluck="name"))
	return [node(one) for one in found if one.folder not in deleted]


# ------------------------------------------------------------ the path


def trail(node_id: str) -> list[dict]:
	"""The address bar: from the top to this node, each a place to go back to."""
	kind = parse(node_id)
	top = [{"id": ROOT, "name": _("OneCloud")}]
	if kind[0] == ROOT:
		return top
	if kind[0] == "mount":
		from onedesk.one_storage import mounts

		return mounts.trail(node_id)
	if kind[0] == MAIL:
		from onedesk.one_mail import cloud

		return cloud.trail(node_id)
	if kind[0] == "request":
		from onedesk.one_storage import file_requests

		return file_requests.trail(node_id)
	if kind[0] in (MY, SHARED, COMPANY, BIN, LIBRARIES, RECENT, STARRED, MOUNTS, REQUESTS):
		return top + [{"id": node_id, "name": next(r["name"] for r in roots() if r["id"] == node_id)}]
	if kind[0] == RECORDS:
		out = top + [{"id": RECORDS, "name": _("Records")}]
		if len(kind) > 1:
			out.append({"id": record_node(kind[1]), "name": _(kind[1])})
		if len(kind) > 2:
			out.append({"id": node_id, "name": kind[2]})
		return out
	item = row(node_id)
	if not item:
		return top
	path = [item["name"], *ancestors(item["name"])]
	crumbs = []
	for name in path:
		one = row(name)
		if not one:
			break
		if one.one_home_of == frappe.session.user:
			crumbs.append({"id": MY, "name": _("My Files")})
			break
		if one.one_library:
			crumbs += [{"id": name, "name": one.file_name}, {"id": LIBRARIES, "name": _("Libraries")}]
			break
		if one.one_home_of:
			# Somebody else's: reached through what they shared, so the trail
			# starts at the highest folder shared with the reader.
			held = grants()
			at = max((i for i, crumb in enumerate(crumbs) if crumb["id"] in held), default=None)
			if at is not None:
				crumbs = [*crumbs[: at + 1], {"id": SHARED, "name": _("Shared with Me")}]
			else:
				from frappe.utils import get_fullname

				crumbs.append({"id": name, "name": get_fullname(one.one_home_of)})
			break
		if name == HOME:
			crumbs.append({"id": COMPANY, "name": _("Company")})
			break
		crumbs.append({"id": name, "name": one.file_name})
	return top + list(reversed(crumbs))
