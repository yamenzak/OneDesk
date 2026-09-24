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
from frappe import _

from onedesk.one import roles

ROOT, MY, SHARED, COMPANY, RECORDS, BIN = "@root", "@my", "@shared", "@company", "@records", "@bin"
HOME, ATTACHMENTS = "Home", "Home/Attachments"

#: Frappe's own bookkeeping, which has files but no folder anybody wants.
UNLISTED = frozenset(
	("Prepared Report", "Data Import", "Data Export", "Access Log", "Error Log", "Deleted Document", "Version")
)

#: How deep a folder chain is walked before it is taken to be a loop.
DEEPEST = 64

FIELDS = [
	"name", "file_name", "is_folder", "folder", "file_url", "file_size", "is_private", "owner",
	"modified", "creation", "attached_to_doctype", "attached_to_name", "one_home_of", "one_deleted",
	"one_deleted_by", "one_deleted_on", "thumbnail_url", "file_type",
]  # fmt: skip


# ------------------------------------------------------------------ ids


def parse(node: str) -> tuple:
	"""What a node id names: (kind, *parts). Pure."""
	node = node or ROOT
	if node == ROOT or node in (MY, SHARED, COMPANY, BIN, RECORDS):
		return (node,)
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


def space(item: dict) -> tuple:
	"""Whose part of the tree a File is in: ("record", doctype, name),
	("home", person), ("attachments",) or ("company",)."""
	if item.get("attached_to_doctype") and item.get("attached_to_name") and not item.get("is_folder"):
		return ("record", item["attached_to_doctype"], item["attached_to_name"])
	if item.get("one_home_of"):
		return ("home", item["one_home_of"])
	for folder in ancestors(item["name"]):
		if folder == ATTACHMENTS:
			return ("attachments",)
		person = frappe.db.get_value("File", folder, "one_home_of")
		if person:
			return ("home", person)
	return ("company",)


# ------------------------------------------------------------- permission


def inside(folder: str) -> tuple:
	"""The space of whatever is put in `folder`, worked out once for a whole
	listing rather than once per file."""
	if folder == HOME:
		return ("company",)
	if folder == ATTACHMENTS:
		return ("attachments",)
	person = frappe.db.get_value("File", folder, "one_home_of")
	if person:
		return ("home", person)
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
	if item.get("owner") == user:
		return True
	# Somebody signed in to a portal — a customer, a supplier — sees the files
	# of records they may read and their own, and nothing of the staff's.
	if not _staff(user):
		return False
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
	}


def virtual(node_id: str, name: str, **more) -> dict:
	return {"id": node_id, "name": name, "folder": True, "virtual": True, **more}


def roots() -> list[dict]:
	return [
		virtual(MY, _("My Files"), icon="folder-heart"),
		virtual(SHARED, _("Shared with Me"), icon="users"),
		virtual(COMPANY, _("Company"), icon="building-2"),
		virtual(RECORDS, _("Records"), icon="database"),
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
		return []
	if kind[0] == BIN:
		return binned()
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
		found = [one for one in found if not one.one_home_of and one.name != ATTACHMENTS]
	if search:
		found = [one for one in found if search.lower() in (one.file_name or "").lower()]
	where = inside(folder)
	return [node(one) for one in found if may(one, where=where)]


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
	return [node(one) for one in found]


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
	if kind[0] in (MY, SHARED, COMPANY, BIN):
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
	chain = [item["name"], *ancestors(item["name"])]
	crumbs = []
	for name in chain:
		one = row(name)
		if not one:
			break
		if one.one_home_of:
			crumbs.append({"id": MY if one.one_home_of == frappe.session.user else name, "name": _("My Files")})
			break
		if name == HOME:
			crumbs.append({"id": COMPANY, "name": _("Company")})
			break
		crumbs.append({"id": name, "name": one.file_name})
	return top + list(reversed(crumbs))
