"""A file opened in OneOS, the desktop in the browser that OneAdmin runs and
bills (one_admin/oneos.py). The workspace keeps the lease: one person edits a
file in OneOS at a time, and the lease lapses two minutes after OneAdmin last
said the session runs. The container reaches the workspace only through two
addresses sealed with the site's key, one to download this file and one to
upload a new version of it, each good for the session's longest length."""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_to_date, get_datetime, get_fullname, get_url, now_datetime
from werkzeug.exceptions import Conflict, Forbidden, NotFound
from werkzeug.utils import redirect

from onedesk.one_admin import faults
from onedesk.one_storage import api, office, store
from onedesk.one_storage import namespace as ns

OPENS = office.OFFICE | {"csv"}
LEASE_SECONDS = 2 * 60
LONGEST = 8 * 60 * 60
MOST_BYTES = 200 * 1024 * 1024
DOWNLOAD, UPLOAD = "file", "save"
FIELDS = ("one_os_lease", "one_os_session", "one_os_user", "one_os_until")
TOLD = ("Idle", "Time Limit", "No Credits", "Not Answering", "Stopped by Operator")


def opens(name: str) -> bool:
	"""Whether a file is one OneOS opens: Word, Excel, PowerPoint,
	OpenDocument and CSV. Pure."""
	return "." in (name or "") and name.rsplit(".", 1)[-1].lower() in OPENS


def live(until, now) -> bool:
	"""Whether a lease still holds. Pure."""
	return bool(until) and get_datetime(until) > now


def seal(what: str, file: str, lease: str, expires: int, key: bytes) -> str:
	"""The seal on one of a session's two addresses. Pure."""
	return hmac.new(key, f"oneos|{what}|{file}|{lease}|{expires}".encode(), hashlib.sha256).hexdigest()


def unsealed(what: str, file: str, lease: str, expires: str, given: str, key: bytes, now: float) -> bool:
	"""Whether an address is one of ours, for this file, lease and use, and
	still in time. Pure."""
	if not (file and lease and expires and given) or not str(expires).isdigit() or int(expires) < now:
		return False
	return hmac.compare_digest(seal(what, file, lease, int(expires), key), given)


def _key() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def _address(what: str, file: str, lease: str, expires: int) -> str:
	query = urlencode({"f": file, "k": lease, "e": expires, "s": seal(what, file, lease, expires, _key())})
	return get_url(f"/api/method/onedesk.one_storage.oneos.{what}?{query}")


def holder(item: dict, now=None) -> dict | None:
	"""Who has a file open in OneOS, for its row: their name, and whether it
	is the reader."""
	if not item.get("one_os_user") or not live(item.get("one_os_until"), now or now_datetime()):
		return None
	return {"by": get_fullname(item["one_os_user"]), "mine": item["one_os_user"] == frappe.session.user}


def _openable(node: str) -> dict:
	item = api._item(node)
	api._need(item, "read")
	if item.is_folder or not opens(item.file_name) or ns._document(item) or ns._workbook(item) or ns._presentation(item):
		frappe.throw(_("{0} can't be opened in OneOS.").format(item.file_name))
	return item


@frappe.whitelist(methods=["POST"])
def start(node: str, copy: int = 0) -> dict:
	"""Open a file in OneOS: the lease taken, the session started in
	OneAdmin and the address to open in a new tab. Somebody else's lease, or
	a file the reader may not change, answers with `held` instead, and
	`copy` opens a copy of it."""
	item = _openable(node)
	if int(copy or 0):
		item = _copied(item)
	if not ns.may(item, "write"):
		return {"held": {"by": None, "readonly": True}}
	lease = _take(item.name)
	if lease.get("held"):
		return lease
	expires = int(time.time()) + LONGEST
	from onedesk.one import account

	try:
		said = account.ask(
			"onedesk.one_admin.proxy.oneos_start",
			file=item.name,
			file_name=item.file_name,
			user=frappe.session.user,
			file_url=_address(DOWNLOAD, item.name, lease["lease"], expires),
			save_url=_address(UPLOAD, item.name, lease["lease"], expires),
			again=lease.get("session"),
		)
	except faults.Refused as refused:
		_let_go(item.name, lease["lease"])
		frappe.db.commit()
		frappe.throw(_plainly(refused), title=_("OneOS Not Started"))
	frappe.db.set_value("File", item.name, "one_os_session", said["session"], update_modified=False)
	from onedesk.one_storage import history, live as changes

	history.seen(item.name)
	if not lease.get("session"):
		history.note(item.name, _("opened it in OneOS"))
	changes.announce(item)
	return {"url": said["url"], "node": item.name, "name": item.file_name}


def _plainly(refused: faults.Refused) -> str:
	detail = (refused.detail or "").strip()
	return detail if detail and not detail.startswith(("Traceback", "{", "<")) else _("OneOS could not be started. Try again in a few minutes.")


def _copied(item: dict) -> dict:
	"""A copy of the file beside it, or in My Files where the reader may not
	add to its folder."""
	folder = ns.row(item.folder) if item.folder else None
	target = item.folder if folder and ns.may(folder, "add") else ns.MY
	made = api.copy([item.name], target)
	return ns.row(made[0])


def _take(name: str) -> dict:
	"""The lease on a file for the reader: a new one, the reader's own still
	running (with its session, to open again), or who else holds it."""
	now = now_datetime()
	held = frappe.db.get_value("File", name, list(FIELDS), as_dict=True, for_update=True)
	if held.one_os_user and live(held.one_os_until, now):
		if held.one_os_user != frappe.session.user:
			return {"held": {"by": get_fullname(held.one_os_user), "readonly": False}}
		if held.one_os_session:
			frappe.db.set_value("File", name, "one_os_until", add_to_date(now, seconds=LEASE_SECONDS), update_modified=False)
			return {"lease": held.one_os_lease, "session": held.one_os_session}
	lease = frappe.generate_hash(length=20)
	frappe.db.set_value(
		"File",
		name,
		{"one_os_lease": lease, "one_os_session": None, "one_os_user": frappe.session.user, "one_os_until": add_to_date(now, seconds=LEASE_SECONDS)},
		update_modified=False,
	)
	return {"lease": lease}


def _let_go(name: str, lease: str | None = None) -> None:
	"""The lease released, if it is still the one named."""
	if lease and frappe.db.get_value("File", name, "one_os_lease") != lease:
		return
	frappe.db.set_value("File", name, dict.fromkeys(FIELDS), update_modified=False)


@frappe.whitelist(methods=["POST"])
def close(node: str) -> None:
	"""The reader's own OneOS session on a file closed: the container saves
	and stops, and the lease goes."""
	item = api._item(node)
	held = frappe.db.get_value("File", item.name, list(FIELDS), as_dict=True)
	if not held.one_os_user:
		return
	if held.one_os_user != frappe.session.user and not ns.may(item, "write"):
		frappe.throw(_("{0} is open in OneOS by {1}.").format(item.file_name, get_fullname(held.one_os_user)), frappe.PermissionError)
	if held.one_os_session:
		from onedesk.one import account

		try:
			account.ask("onedesk.one_admin.proxy.oneos_stop", session=held.one_os_session)
		except faults.Refused:
			frappe.log_error(title="Closing a OneOS session")
	_let_go(item.name, held.one_os_lease)
	from onedesk.one_storage import live as changes

	changes.announce(item)


def _sealed(what: str, f: str, k: str, e: str, s: str) -> dict:
	if not unsealed(what, f, k, e, s, _key(), time.time()):
		raise Forbidden
	item = ns.row(f)
	if not item or item.one_deleted:
		raise NotFound
	held = frappe.db.get_value("File", f, ["one_os_lease", "one_os_user"], as_dict=True)
	if held.one_os_lease and held.one_os_lease != k:
		raise Conflict
	return item


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=120, seconds=60 * 60)
def file(f: str, k: str, e: str, s: str):
	"""The file a session opens, for its container: redirected to a signed
	R2 address, or sent from the disk."""
	item = _sealed(DOWNLOAD, f, k, e, s)
	if store.is_stored(item.file_url):
		return redirect(store.signed(store.key_of(item.file_url), filename=item.file_name, inline=False), 302)
	frappe.local.response.filename = item.file_name
	frappe.local.response.filecontent = api._content(item)
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "attachment"


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=600, seconds=60 * 60)
def save(f: str, k: str, e: str, s: str) -> dict:
	"""A new version of the file, saved in OneOS: the request's body, or the
	first file in a form, written as the person who opened it."""
	item = _sealed(UPLOAD, f, k, e, s)
	sent = next(iter(frappe.request.files.values()), None) if frappe.request.files else None
	content = sent.stream.read(MOST_BYTES + 1) if sent else frappe.request.get_data()[: MOST_BYTES + 1]
	if not content:
		frappe.throw(_("No file was uploaded."))
	if len(content) > MOST_BYTES:
		frappe.throw(_("{0} is over {1} MB.").format(item.file_name, MOST_BYTES // 1024 // 1024))
	if hashlib.md5(content).hexdigest() == frappe.db.get_value("File", item.name, "content_hash"):
		return {"saved": False}
	was = frappe.session.user
	frappe.set_user(frappe.db.get_value("File", item.name, "one_os_user") or item.owner)
	try:
		api._need(item, "write")
		_version(item, content)
	finally:
		frappe.set_user(was)
	return {"saved": True}


def _version(item: dict, content: bytes) -> None:
	from onedesk.one_storage import history

	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": item.file_name,
			"is_private": item.is_private,
			"folder": item.folder or ns.HOME,
			"content": content,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	history.replace(ns.row(item.name), doc.name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def stopped(session: str) -> dict:
	"""OneAdmin says a session stopped. Like account.wake it takes nothing on
	trust: the workspace asks OneAdmin with its own token and acts on that."""
	name = frappe.db.get_value("File", {"one_os_session": session}, "name") if session else None
	if not name:
		return {"ok": True}
	was = frappe.session.user
	frappe.set_user("Administrator")
	try:
		_look(name)
	finally:
		frappe.set_user(was)
	return {"ok": True}


def tick() -> None:
	"""Every minute: each lease renewed while OneAdmin says its session runs,
	and let go when it stopped or two minutes after OneAdmin last answered."""
	from onedesk.one import account

	if not account.configured():
		return
	now = now_datetime()
	for row in frappe.get_all("File", filters={"one_os_user": ["is", "set"]}, fields=["name", "one_os_until"]):
		try:
			_look(row.name, now)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"OneOS lease on {row.name}")


def _look(name: str, now=None) -> None:
	from onedesk.one import account

	now = now or now_datetime()
	held = frappe.db.get_value("File", name, ["file_name", *FIELDS], as_dict=True)
	if not held or not held.one_os_user:
		return
	if not held.one_os_session:
		if not live(held.one_os_until, now):
			_let_go(name, held.one_os_lease)
		return
	try:
		said = account.ask("onedesk.one_admin.proxy.oneos_state", session=held.one_os_session)
	except faults.Refused:
		said = None
	if said is None:
		if not live(held.one_os_until, now):
			_ended(name, held, None)
		return
	if said.get("state") in ("Starting", "Running"):
		frappe.db.set_value("File", name, "one_os_until", add_to_date(now, seconds=LEASE_SECONDS), update_modified=False)
		warned = f"onecloud_oneos_warned:{held.one_os_session}"
		if not said.get("warn"):
			frappe.cache.delete_value(warned)
		elif not frappe.cache.get_value(warned):
			frappe.cache.set_value(warned, 1, expires_in_sec=30 * 60)
			frappe.publish_realtime("onecloud_oneos", {"file": name, "name": held.file_name, "warn": True}, user=held.one_os_user, after_commit=True)
		return
	_ended(name, held, said.get("stop_reason"))


def _ended(name: str, held: dict, why: str | None) -> None:
	"""A session is over: the lease goes, and its person hears why when it was
	not their own doing."""
	from onedesk.one_storage import live as changes
	from onedesk.one_storage import tell

	_let_go(name, held.one_os_lease)
	changes.announce(name)
	why = why or "Not Answering"
	frappe.publish_realtime(
		"onecloud_oneos",
		{"file": name, "name": held.file_name, "why": why},
		user=held.one_os_user,
		after_commit=True,
	)
	if why in TOLD:
		tell.oneos_closed(held.one_os_user, name, held.file_name)
