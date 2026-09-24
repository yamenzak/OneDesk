"""Putting files into OneCloud: straight from the browser to R2.

A file dropped on the explorer never passes through this server. `begin` asks
admin for a URL the browser may PUT each file to and hands back a ticket per
file; the browser sends the bytes to R2 itself, showing its own progress, and
then calls `done` with the ticket, which checks the object arrived and writes
the File row. A gigabyte of video costs this server two small requests.

**The ticket is the whole of the trust.** It is held in the cache for an hour,
names who asked, where to and under which key, and `done` believes nothing
else the browser says except the path inside a dropped folder. A ticket is
used once.

**A key per upload, not per content.** Frappe's own files are keyed by their
MD5 so ten copies are one object (`store.key_for`); a browser cannot hash a
large file cheaply before sending it, so an upload gets a random key under
`files/private/u/`. Copies made inside OneCloud still share their object.

Without an account (a bench of one's own) there is nothing to sign, and `here`
takes the file as an ordinary form post instead, through the same `_place`.
"""

import json
import mimetypes
import os

import frappe
import requests
from frappe import _

from onedesk.one_storage import api, store
from onedesk.one_storage import namespace as ns

#: How long a ticket is good for, from `begin`.
TICKET_LIFE = 60 * 60

#: How many files one `begin` signs for.
AT_ONCE = 200


def _extension(name: str) -> str:
	return "".join(ch for ch in os.path.splitext(name)[1].lower() if ch.isalnum() or ch == ".")[:12]


def split_path(path: str | None) -> list[str]:
	"""A dropped file's folders, from `a/b/c.txt`: ["a", "b"]. Pure."""
	parts = [api._clean(part) for part in (path or "").replace("\\", "/").split("/")]
	return [part for part in parts[:-1] if part and part not in (".", "..")][: ns.DEEPEST]


@frappe.whitelist(methods=["POST"])
def begin(node: str, files: str | list) -> dict:
	"""Tickets for putting `files` ([{name, size}]) into `node`."""
	files = json.loads(files) if isinstance(files, str) else files
	if not files or len(files) > AT_ONCE:
		frappe.throw(_("Send between one and {0} files at a time.").format(AT_ONCE))
	where = api._target(node)
	# Names already in the folder, so the browser can ask once whether to
	# replace them (keeping what they held as versions) or keep both.
	existing = []
	if where[0] == "folder":
		asked = {api._clean(one.get("name")) for one in files if "/" not in (one.get("path") or "")}
		existing = sorted(asked & set(frappe.get_all("File", filters={"folder": where[1], "is_folder": 0, "one_deleted": 0}, pluck="file_name")))
	if not store.enabled() or where[0] == "mount":
		# A server is written to through the workspace, which holds its keys.
		return {"direct": False, "existing": existing}
	from onedesk.one import account

	tickets = []
	for one in files:
		name = api._clean(one.get("name")) or "file"
		size = int(one.get("size") or 0)
		key = f"files/private/u/{frappe.generate_hash(length=24)}{_extension(name)}"
		signed = account.put_url(key, size)
		token = frappe.generate_hash(length=32)
		frappe.cache.set_value(
			_held(token),
			{"user": frappe.session.user, "node": node, "key": key, "name": name, "size": size},
			expires_in_sec=TICKET_LIFE,
		)
		tickets.append({"token": token, "url": signed["url"], "type": mimetypes.guess_type(name)[0] or ""})
	return {"direct": True, "tickets": tickets, "existing": existing}


def _held(token: str) -> str:
	return f"onestorage:upload:{token}"


@frappe.whitelist(methods=["POST"])
def done(token: str, path: str | None = None, replace: int = 0, version_of: str | None = None) -> dict:
	"""The browser's PUT finished: check the object is there, and file it."""
	held = frappe.cache.get_value(_held(token))
	if not held or held.get("user") != frappe.session.user:
		frappe.throw(_("That upload has expired. Try it again."))
	frappe.cache.delete_value(_held(token))
	arrived = requests.get(store.signed(held["key"]), headers={"Range": "bytes=0-0"}, timeout=store.PATIENCE)
	if arrived.status_code not in (200, 206):
		frappe.throw(_("{0} did not arrive. Try it again.").format(held["name"]))
	return _place(
		held["node"],
		path,
		{"file_url": store.url_for(held["key"]), "file_size": held["size"], "file_name": held["name"]},
		replace=int(replace),
		version_of=version_of,
	)


@frappe.whitelist(methods=["POST"])
def here(node: str, path: str | None = None, replace: int = 0, version_of: str | None = None) -> dict:
	"""A file sent to this server as a form post, where there is no account
	to send it to R2 with (or the browser could not reach R2)."""
	sent = frappe.request.files.get("file")
	if not sent:
		frappe.throw(_("No file was sent."))
	content = sent.stream.read()
	from onedesk.one_storage import mounts

	if mounts.is_mount(node):
		return mounts.write(node, api._clean(sent.filename) or "file", content)
	return _place(node, path, {"file_name": api._clean(sent.filename) or "file", "content": content}, replace=int(replace), version_of=version_of)


def _place(node: str, path: str | None, fields: dict, replace: int = 0, version_of: str | None = None) -> dict:
	"""The File row for something just put into `node`, making the folders
	of a dropped folder on the way. With `replace`, a file of the same name
	already there takes the new content and keeps the old as a version."""
	from onedesk.one_storage import history

	where = api._target(node)
	fields = {"doctype": "File", "is_private": 1, **fields}
	if where[0] == "record":
		taken = set(
			frappe.get_all(
				"File",
				filters={"attached_to_doctype": where[1], "attached_to_name": where[2]},
				pluck="file_name",
			)
		)
		fields.update(attached_to_doctype=where[1], attached_to_name=where[2])
	else:
		folder = where[1]
		for part in split_path(path):
			folder = _folder(folder, part)
		taken = api._taken(folder)
		fields["folder"] = folder
	same = None
	if version_of:
		same = version_of
		api._need(api._item(same), "write")
	elif replace and where[0] == "folder":
		same = frappe.db.get_value(
			"File", {"folder": fields["folder"], "file_name": fields["file_name"], "is_folder": 0, "one_deleted": 0}, "name"
		)
		if same:
			api._need(ns.row(same), "write")
	fields["file_name"] = ns.unique_name(fields["file_name"], taken)
	doc = frappe.get_doc(fields)
	doc.flags.ignore_permissions = True
	if "file_url" in fields:
		doc.flags.copy_from_existing_file = True
	doc.insert()
	name = history.replace(ns.row(same), doc.name) if same else doc.name
	if (mimetypes.guess_type(doc.file_name)[0] or "").startswith("image/") and store.is_stored(doc.file_url):
		frappe.enqueue(thumbnail, name=name, enqueue_after_commit=True)
	history.seen(name)
	return ns.node(ns.row(name))


def _folder(parent: str, name: str) -> str:
	"""The folder called `name` in `parent`, made if it is not there."""
	found = frappe.db.get_value(
		"File", {"folder": parent, "is_folder": 1, "file_name": name, "one_deleted": 0}, "name"
	)
	if found:
		return found
	doc = frappe.get_doc({"doctype": "File", "is_folder": 1, "file_name": name, "folder": parent})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def thumbnail(name: str) -> None:
	"""A stored image's small copy, made once it is in."""
	doc = frappe.get_doc("File", name)
	url = doc.make_thumbnail()
	if url:
		frappe.db.set_value("File", name, "thumbnail_url", url, update_modified=False)
