"""A file's past, and a person's: versions, Recent, Starred and activity."""

import json
import time

import frappe
from frappe import _
from frappe.utils import get_fullname, now_datetime

from onedesk.one_cloud import api, store
from onedesk.one_cloud import namespace as ns

RECENT = 50
SITTING_SECONDS = 10 * 60


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


def merges(last: dict | None, url: str, by: str, sitting: str | None, now: float) -> bool:
	"""Whether a save takes the place of the saver's last version rather
	than adding one: the file still holds what the same person saved last in
	the same sitting, under ten minutes ago. The version from before the
	sitting stays. Pure."""
	return bool(
		sitting
		and last
		and last.get("sitting") == sitting
		and last.get("by") == by
		and last.get("url") == url
		and now - float(last.get("on") or 0) < SITTING_SECONDS
	)


def _sitting_key(name: str) -> str:
	return f"onecloud_sitting:{name}"


def replace(item: dict, new: str, sitting: str | None = None) -> str:
	"""Point `item` at the content of the File `new`, keeping what it held as
	a version, and take `new`'s row away without touching the content. An
	empty file is not kept: a drive writes one first and its content after.
	Saves in one `sitting` (the editor, a OneOS session, the drive) by one
	person, each under ten minutes after the last, are one version."""
	fresh = frappe.db.get_value(
		"File", new, ["file_url", "file_size", "content_hash", "thumbnail_url"], as_dict=True
	)
	merged = merges(frappe.cache.get_value(_sitting_key(item.name)), item.file_url, frappe.session.user, sitting, time.time())
	if merged and fresh.file_url != item.file_url:
		_let_go_of(item)
	elif not merged and item.file_size:
		keep(item)
	frappe.db.set_value("File", item.name, {**fresh, "modified": now_datetime(), "modified_by": frappe.session.user})
	frappe.db.delete("File", new)
	if sitting:
		frappe.cache.set_value(
			_sitting_key(item.name),
			{"sitting": sitting, "by": frappe.session.user, "url": fresh.file_url, "on": time.time()},
			expires_in_sec=SITTING_SECONDS,
		)
	from onedesk.one_doc import word
	from onedesk.one_sheet import api as sheets
	from onedesk.one_cloud import live

	sheets.file_replaced(item.name)
	word.file_replaced(item.name)

	live.announce(item)
	if not merged:
		note(item.name, _("uploaded a new version"))
	return item.name


def _let_go_of(item: dict) -> None:
	"""The content a merged save takes the place of, deleted from storage
	once nothing else names it."""
	url = item.file_url
	if store.is_stored(url) and not store._named_elsewhere(item.name, url):
		key = store.key_of(url)
		frappe.db.after_commit.add(lambda: store._drop([key]))


@frappe.whitelist()
@frappe.read_only()
def versions(node: str) -> list[dict]:
	item = api._item(node)
	if not ns.may(item):
		frappe.throw(_("This item no longer exists."), frappe.DoesNotExistError)
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
	from onedesk.one_cloud import lease

	item = api._item(node)
	api._need(item, "write")
	old = frappe.get_doc("Cloud File Version", version)
	if old.file != item.name:
		frappe.throw(_("This version doesn't belong to {0}.").format(item.file_name))
	held = lease.blocking(item.name)
	if held:
		frappe.throw(lease.told(held))
	keep(item)
	frappe.cache.delete_value(_sitting_key(item.name))
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
	from onedesk.one_cloud import live

	live.announce(item)
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


def _recent_key(user: str) -> str:
	return f"onecloud:recent:{user}"


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
		frappe.throw(_("This item no longer exists."), frappe.DoesNotExistError)
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
