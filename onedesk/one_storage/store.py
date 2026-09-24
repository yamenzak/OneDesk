"""Where a File's bytes are: R2, through admin's signed URLs.

Frappe writes new content through the `write_file` hook and deletes it through
`delete_file_data_content`, and reads everything else straight off the disk.
So `write` puts new content in R2 and gives the File a URL of ours, `delete`
drops the object when the last File naming it goes, and `file.CloudFile` reads
it back. A workspace not linked to an account (a bench of one's own, the test
site) keeps using the disk: `enabled` is the switch, and it is the account's
configuration, not a setting anybody on the workspace can change.

**A key is the content, not the file.** `files/<private|public>/<md5><ext>` is
Frappe's own de-duplication (`content_hash`) carried into R2: the same PDF
attached to ten records is ten File rows and one object.

**A URL of ours, never R2's.** A stored file's URL is
`/api/method/onedesk.one_storage.store.fetch?key=…`. Frappe counts any
`/api/method/` URL as remote (`URL_PREFIXES`), so its disk checks pass it by,
and `fetch` checks the reader may open the file before redirecting to a URL
admin signed for a quarter of an hour. A signed URL in a saved page is dead
in fifteen minutes; ours is good for as long as the file is.
"""

import mimetypes
import os
import re
from urllib.parse import parse_qs, quote, urlparse

import frappe
import requests
from frappe import _
from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect

FETCH = "/api/method/onedesk.one_storage.store.fetch"

#: How long to wait on R2 for one object, either way.
PATIENCE = 120

#: The largest file anything in a workspace takes: what R2 accepts in one
#: PUT. Size is not what a tenant is limited by — their storage is, and
#: admin refuses a put there is no room for — so every size limit Frappe has
#: is set to this. See `unlimit`, and one_admin/steps.py push_config.
LARGEST = 5 * 1024**3

#: How long a URL admin signed is reused for; admin signs them for fifteen
#: minutes, so a reused one always has five left.
REUSE = 10 * 60


def enabled() -> bool:
	"""Whether new files go to R2: the workspace is linked to an account, and
	the bench has not been told to keep them on disk."""
	from onedesk.one import account

	return account.configured() and not frappe.conf.get("onestorage_on_disk")


def is_stored(file_url: str | None) -> bool:
	return bool(file_url) and file_url.startswith(FETCH)


def key_of(file_url: str) -> str | None:
	"""The key in a stored file's URL. Pure."""
	if not is_stored(file_url):
		return None
	found = parse_qs(urlparse(file_url).query).get("key")
	return found[0] if found else None


def key_for(content_hash: str, file_name: str | None, is_private) -> str:
	"""Where content goes: by what it is, and whether it is private. Pure."""
	extension = re.sub(r"[^a-z0-9.]", "", os.path.splitext(file_name or "")[1].lower())[:12]
	return f"files/{'private' if int(is_private or 0) else 'public'}/{content_hash}{extension}"


def url_for(key: str) -> str:
	return f"{FETCH}?key={quote(key, safe='/')}"


def put(key: str, content: bytes) -> None:
	from onedesk.one import account

	signed = account.put_url(key, len(content))
	kind = mimetypes.guess_type(key)[0] or "application/octet-stream"
	answer = requests.put(signed["url"], data=content, headers={"Content-Type": kind}, timeout=PATIENCE)
	answer.raise_for_status()


def get(key: str) -> bytes:
	answer = requests.get(signed(key), timeout=PATIENCE)
	answer.raise_for_status()
	return answer.content


def signed(key: str, filename: str | None = None, inline: bool = True) -> str:
	"""A URL admin signed for this object, reused while it has time left."""
	from onedesk.one import account

	cache = f"onestorage:signed:{key}:{filename or ''}:{int(inline)}"
	held = frappe.cache.get_value(cache)
	if held:
		return held
	url = account.get_url(key, filename=filename, inline=inline)["url"]
	frappe.cache.set_value(cache, url, expires_in_sec=REUSE)
	return url


def unlimit() -> None:
	"""after_install and after_migrate: the attach button's size limit
	(System Settings, in MB) raised to LARGEST. The limit on every other
	request is the site's config, which admin writes when it builds the site."""
	wanted = LARGEST // (1024 * 1024)
	if int(frappe.db.get_single_value("System Settings", "max_file_size") or 0) < wanted:
		frappe.db.set_single_value("System Settings", "max_file_size", wanted)


# ---------------------------------------------------------------- the hooks


def write(doc):
	"""write_file: new content to R2, or to disk where there is no account."""
	if not enabled():
		return doc.save_file_on_filesystem()
	content = doc._content if isinstance(doc._content, bytes) else doc._content.encode()
	key = key_for(doc.content_hash, doc.file_name, doc.is_private)
	put(key, content)
	doc.file_url = url_for(key)
	return {"file_name": doc.file_name, "file_url": doc.file_url}


def delete(doc, only_thumbnail=False) -> None:
	"""delete_file_data_content: drop the object once nothing names it, and
	only once the delete is committed — a rolled-back delete keeps its file."""
	if not is_stored(doc.file_url):
		doc.delete_file_from_filesystem(only_thumbnail=only_thumbnail)
		return
	gone = []
	if not only_thumbnail and not _named_elsewhere(doc.name, doc.file_url):
		gone.append(key_of(doc.file_url))
	if is_stored(doc.thumbnail_url) and not _named_elsewhere(doc.name, doc.thumbnail_url, "thumbnail_url"):
		gone.append(key_of(doc.thumbnail_url))
	if gone:
		frappe.db.after_commit.add(lambda: _drop(gone))


def _named_elsewhere(name: str, url: str, field: str = "file_url") -> bool:
	"""Whether another File, or a version of any file, still names this."""
	return bool(
		frappe.db.exists("File", {field: url, "name": ["!=", name]})
		or (field == "file_url" and frappe.db.exists("Cloud File Version", {"file_url": url}))
	)


def _drop(keys: list) -> None:
	from onedesk.one import account

	for key in keys:
		try:
			account.drop(key)
		except Exception:
			frappe.log_error(title=f"OneCloud could not delete {key}")


# ------------------------------------------------------------ the one door


@frappe.whitelist(allow_guest=True, methods=["GET", "HEAD"])
def fetch(key: str, download: int = 0):
	"""A stored file, for whoever may open it: a redirect to R2.

	Any File naming the object will do, since they are the same bytes: a public
	one opens for anybody, a private one for whoever OneCloud says may read it
	(namespace.may), which is Frappe's own rule and then some. A reader who
	may not is told there is nothing here rather than that they may not — the
	difference would say the file exists.
	"""
	rows = frappe.get_all(
		"File",
		filters={"file_url": url_for(key)},
		fields=["name", "file_name", "is_private"],
		order_by="is_private asc",
		limit=50,
	)
	thumbnail = not rows
	if thumbnail:
		rows = frappe.get_all(
			"File", filters={"thumbnail_url": url_for(key)}, fields=["name", "file_name", "is_private"], limit=50
		)
	from onedesk.one_storage import history, namespace

	for row in rows:
		if not row.is_private or namespace.may(namespace.row(row.name)):
			if not thumbnail and not int(download):
				history.seen(row.name)
			return redirect(signed(key, filename=row.file_name, inline=not int(download)), 302)
	# An old version opens for whoever may open the file it was a version of.
	for version in frappe.get_all("Cloud File Version", filters={"file_url": url_for(key)}, fields=["file", "version"], limit=20):
		item = namespace.row(version.file)
		if item and namespace.may(item):
			return redirect(signed(key, filename=item.file_name, inline=not int(download)), 302)
	raise NotFound(_("There is no such file."))


# ------------------------------------------------------ files on the disk


def on_disk() -> list:
	"""File rows whose content is still on this server's disk."""
	return frappe.get_all(
		"File",
		filters={"is_folder": 0},
		or_filters=[["file_url", "like", "/files/%"], ["file_url", "like", "/private/files/%"]],
		pluck="name",
		order_by="creation asc",
	)


def move(limit: int = 500) -> dict:
	"""Copy files on the disk to R2 and point their rows at it.

	The copy on disk stays. A public file's URL may be written into a web page,
	a letter head or an email template that no File row knows about, and those
	keep working because the old path still answers; what changes is every row
	and every attach field that names it.
	"""
	from onedesk.one_storage.file import CloudFile

	moved, failed = 0, []
	urls: dict = {}
	for name in on_disk()[:limit]:
		doc: CloudFile = frappe.get_doc("File", name)
		old = doc.file_url
		try:
			if old not in urls:
				content = doc.get_content()
				content = content if isinstance(content, bytes) else content.encode()
				from frappe.core.doctype.file.utils import get_content_hash

				key = key_for(doc.content_hash or get_content_hash(content), doc.file_name, doc.is_private)
				put(key, content)
				urls[old] = url_for(key)
			repoint(doc, urls[old])
			moved += 1
		except Exception:
			failed.append(name)
			frappe.log_error(title=f"OneCloud could not move {name}")
	frappe.db.commit()
	return {"moved": moved, "failed": failed, "left": max(len(on_disk()), 0)}


def repoint(doc, url: str) -> None:
	"""A File, and the field it was attached through, at its new URL."""
	old = doc.file_url
	frappe.db.set_value("File", doc.name, "file_url", url, update_modified=False)
	if doc.attached_to_doctype and doc.attached_to_name and doc.attached_to_field:
		try:
			if frappe.db.get_value(doc.attached_to_doctype, doc.attached_to_name, doc.attached_to_field) == old:
				frappe.db.set_value(
					doc.attached_to_doctype, doc.attached_to_name, doc.attached_to_field, url, update_modified=False
				)
		except Exception:
			frappe.log_error(title=f"OneCloud could not repoint {doc.attached_to_doctype} {doc.attached_to_name}")
