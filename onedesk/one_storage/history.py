"""A file's past, and a person's: versions, Recent, Starred and activity.

**A version is the object a file used to name.** Objects are never
overwritten (a key is its content, or a random one for an upload), so
replacing a file is pointing its row at a new object and writing down the old
one in `Cloud File Version`. The File keeps its name, so its shares, its
links and its place in every folder stay as they were; restoring an old
version is the same move the other way, with what was current written down
first. `store.delete` counts a version as naming its object, so a version's
bytes go only when the file itself does (`forget`).

**Recent** is what the reader opened or put somewhere, newest first, kept in
the cache as a short list per person: it is a convenience, and losing it
loses nothing. **Starred** is Frappe's own `_liked_by` on File, read and
written directly so that starring a file does not comment on it or tell its
owner. **Activity** is Info comments on the File, written by the verbs that
change something, and read back with the versions.
"""

import json

import frappe
from frappe import _
from frappe.utils import get_fullname, now_datetime

from onedesk.one_storage import api, store
from onedesk.one_storage import namespace as ns

#: How many files Recent remembers.
RECENT = 50


# --------------------------------------------------------------- versions


def keep(item: dict) -> None:
	"""Write down what `item` holds now, before it holds something else."""
	number = (frappe.db.count("Cloud File Version", {"file": item.name}) or 0) + 1
	frappe.get_doc(
		{
			"doctype": "Cloud File Version",
			"file": item.name,
			"version": number,
			"file_url": item.file_url,
			"file_size": item.file_size,
			"content_hash": frappe.db.get_value("File", item.name, "content_hash"),
			"made_by": frappe.db.get_value("File", item.name, "modified_by"),
			"made_on": item.modified,
		}
	).insert(ignore_permissions=True)


def replace(item: dict, new: str) -> str:
	"""Point `item` at the content of the File `new`, keeping what it held as
	a version, and take `new`'s row away without touching the content."""
	keep(item)
	fresh = frappe.db.get_value(
		"File", new, ["file_url", "file_size", "content_hash", "thumbnail_url"], as_dict=True
	)
	frappe.db.set_value("File", item.name, {**fresh, "modified": now_datetime(), "modified_by": frappe.session.user})
	frappe.db.delete("File", new)
	note(item.name, _("uploaded a new version"))
	return item.name


@frappe.whitelist()
@frappe.read_only()
def versions(node: str) -> list[dict]:
	item = api._item(node)
	if not ns.may(item):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	rows = frappe.get_all(
		"Cloud File Version",
		filters={"file": item.name},
		fields=["name", "version", "file_url", "file_size", "made_by", "made_on"],
		order_by="version desc",
	)
	return [
		{
			"name": one.name,
			"version": one.version,
			"size": one.file_size,
			"by": get_fullname(one.made_by) if one.made_by else "",
			"on": one.made_on,
			"url": one.file_url,
		}
		for one in rows
	]


@frappe.whitelist(methods=["POST"])
def restore(node: str, version: str) -> None:
	"""Make an old version current again; what was current becomes a version."""
	item = api._item(node)
	api._need(item, "write")
	old = frappe.get_doc("Cloud File Version", version)
	if old.file != item.name:
		frappe.throw(_("That version is not one of {0}'s.").format(item.file_name))
	keep(item)
	frappe.db.set_value(
		"File",
		item.name,
		{
			"file_url": old.file_url,
			"file_size": old.file_size,
			"content_hash": old.content_hash,
			"thumbnail_url": None,
			"modified": now_datetime(),
			"modified_by": frappe.session.user,
		},
	)
	note(item.name, _("restored version {0}").format(old.version))


def forget(doc, method=None) -> None:
	"""on_trash of File: its versions go, and their objects when nothing else
	names them."""
	rows = frappe.get_all("Cloud File Version", filters={"file": doc.name}, fields=["name", "file_url"])
	if not rows:
		return
	frappe.db.delete("Cloud File Version", {"file": doc.name})
	gone = [
		store.key_of(one.file_url)
		for one in rows
		if store.is_stored(one.file_url) and not store._named_elsewhere(doc.name, one.file_url)
	]
	if gone:
		frappe.db.after_commit.add(lambda: store._drop(gone))


# ------------------------------------------------------------ recent, starred


def _recent_key(user: str) -> str:
	return f"onestorage:recent:{user}"


def seen(name: str, user: str | None = None) -> None:
	"""Put a file at the top of somebody's Recent."""
	user = user or frappe.session.user
	if user == "Guest":
		return
	key = _recent_key(user)
	try:
		frappe.cache.lrem(frappe.cache.make_key(key), 0, name)
		frappe.cache.lpush(key, name)
		frappe.cache.ltrim(key, 0, RECENT - 1)
	except Exception:
		pass


def recent(user: str | None = None) -> list[dict]:
	user = user or frappe.session.user
	try:
		names = [one.decode() if isinstance(one, bytes) else one for one in frappe.cache.lrange(_recent_key(user), 0, RECENT - 1)]
	except Exception:
		names = []
	if not names:
		return []
	rows = {one.name: one for one in frappe.get_all("File", filters={"name": ["in", names], "one_deleted": 0}, fields=ns.FIELDS)}
	return [
		{**ns.node(rows[name]), "where": _folder_name(rows[name].folder)}
		for name in names
		if name in rows and ns.may(rows[name], user=user)
	]


def starred_by(item: dict, user: str | None = None) -> bool:
	return (user or frappe.session.user) in json.loads(item.get("_liked_by") or "[]")


def starred(user: str | None = None) -> list[dict]:
	user = user or frappe.session.user
	found = frappe.get_all(
		"File",
		filters={"_liked_by": ["like", f'%"{user}"%'], "one_deleted": 0},
		fields=ns.FIELDS,
		order_by="is_folder desc, file_name asc",
		limit=500,
	)
	return [
		{**ns.node(one), "where": _folder_name(one.folder)} for one in found if starred_by(one, user) and ns.may(one, user=user)
	]


@frappe.whitelist(methods=["POST"])
def star(nodes: str | list, on: int = 1) -> None:
	"""Star or unstar. Frappe's own like would comment on the file and tell its
	owner; a star is nobody's business but the reader's."""
	nodes = frappe.parse_json(nodes) if isinstance(nodes, str) else nodes
	user = frappe.session.user
	for node_id in nodes:
		item = api._item(node_id)
		if not ns.may(item):
			continue
		liked = [one for one in json.loads(frappe.db.get_value("File", item.name, "_liked_by") or "[]") if one != user]
		if int(on):
			liked.append(user)
		frappe.db.set_value("File", item.name, "_liked_by", json.dumps(liked), update_modified=False)


def _folder_name(folder: str | None) -> str:
	if not folder:
		return ""
	found = frappe.db.get_value("File", folder, ["file_name", "one_home_of"], as_dict=True)
	if not found:
		return ""
	if found.one_home_of:
		return _("My Files") if found.one_home_of == frappe.session.user else get_fullname(found.one_home_of)
	return _("Company") if folder == ns.HOME else found.file_name


# --------------------------------------------------------------- activity


def note(name: str, what: str) -> None:
	"""One line of a file's activity: who did what, now."""
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "File",
			"reference_name": name,
			"content": what,
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
@frappe.read_only()
def activity(node: str) -> dict:
	"""What the preview pane shows under a file: its versions, what was done
	to it, and whether the reader starred it."""
	item = api._item(node)
	if not ns.may(item):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	done = frappe.get_all(
		"Comment",
		filters={"reference_doctype": "File", "reference_name": item.name, "comment_type": "Info"},
		fields=["owner", "content", "creation"],
		order_by="creation desc",
		limit=20,
	)
	return {
		"starred": starred_by(item),
		"versions": versions(node) if not item.is_folder else [],
		"done": [
			{"who": get_fullname(one.owner), "what": one.content, "when": one.creation}
			for one in done
		]
		+ [{"who": get_fullname(item.owner), "what": _("created it"), "when": item.creation}],
	}
