"""A file opened in OneOS, the desktop in the browser that OneAdmin runs and
bills (one_admin/oneos.py): the lease (lease.py) taken alone, never while
somebody may write in it live, and two addresses sealed with the site's key
for the container, one to download the file and one to save it. A
workbook, document or presentation of One's own goes as the office file the
drive serves and each save comes back into it. AGENTS.md, Under the hood,
OneOS."""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import get_fullname, get_url, now_datetime
from werkzeug.exceptions import Conflict, Forbidden, NotFound
from werkzeug.utils import redirect

from onedesk.one_admin import faults
from onedesk.one_cloud import api, lease, office, opening, saving, store
from onedesk.one_cloud import namespace as ns

OPENS = office.OFFICE | {"csv"}
LEASE_SECONDS = 2 * 60
LONGEST = 8 * 60 * 60
MOST_BYTES = 200 * 1024 * 1024
DOWNLOAD, UPLOAD = "file", "save"
TOLD = ("Idle", "Time Limit", "No Credits", "Not Answering", "Stopped by Operator")


def opens(name: str) -> bool:
	"""Whether a file is one OneOS opens: Word, Excel, PowerPoint,
	OpenDocument and CSV. Pure."""
	return "." in (name or "") and name.rsplit(".", 1)[-1].lower() in OPENS


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
	return get_url(f"/api/method/onedesk.one_cloud.oneos.{what}?{query}")


def offered() -> dict | None:
	"""What an hour of OneOS costs this workspace in credits, as OneAdmin
	last said, or None while it is not offered: not set up, or a trial."""
	held = frappe.db.get_value("Workspace Account", None, ["oneos_on", "oneos_credits_an_hour"], as_dict=True)
	if not held or not frappe.utils.cint(held.oneos_on):
		return None
	return {"credits_an_hour": frappe.utils.flt(held.oneos_credits_an_hour, 2)}


def holder(item: dict, now=None) -> dict | None:
	"""Who has a file open in OneOS, for its row: their name, and whether it
	is the reader."""
	held = lease.held_alone(item, now=now)
	return {"by": held["by"], "mine": held["mine"]} if held and held["kind"] == lease.ONEOS else None


def _openable(node: str) -> dict:
	item = api._item(node)
	api._need(item, "read")
	own = opening.own_of(item)
	if item.is_folder or not (own or opens(item.file_name)):
		frappe.throw(_("{0} can't be opened in OneOS.").format(item.file_name))
	why = own and opening.kept_inside(*own)
	if why:
		frappe.throw(why, title=_("OneOS Not Started"))
	return item


def _named(item: dict) -> str:
	own = opening.own_of(item)
	return opening.office_name(item, own[0]) if own else item.file_name


@frappe.whitelist(methods=["POST"])
def start(node: str, copy: int = 0) -> dict:
	"""Open a file in OneOS: the lease taken, the session started in
	OneAdmin and the address to open in a new tab. Somebody else's lease, or
	somebody in it in OneSheet or OneDoc, or a file the reader may not
	change, answers with `held` instead, and `copy` opens a copy of it."""
	item = _openable(node)
	if not offered():
		frappe.throw(_("OneOS isn't offered to this workspace."), title=_("OneOS Not Started"))
	if int(copy or 0):
		item = _copied(item)
	if not ns.may(item, "write"):
		return {"held": {"by": None, "mine": False, "where": "OneOS", "readonly": True}}
	taken = lease.take(item.name, lease.ONEOS, frappe.session.user, LEASE_SECONDS)
	if taken.get("held"):
		return taken
	expires = int(time.time()) + LONGEST
	from onedesk.one import account

	try:
		said = account.ask(
			"onedesk.one_admin.proxy.oneos_start",
			file=item.name,
			file_name=_named(item),
			user=frappe.session.user,
			file_url=_address(DOWNLOAD, item.name, taken["lock"], expires),
			save_url=_address(UPLOAD, item.name, taken["lock"], expires),
			again=taken.get("session"),
		)
	except faults.Refused as refused:
		lease.release(item.name, taken["lock"])
		frappe.db.commit()
		frappe.throw(_plainly(refused), title=_("OneOS Not Started"))
	lease.started(item.name, said["session"])
	from onedesk.one_cloud import history, live as changes

	history.seen(item.name)
	if not taken.get("session"):
		history.note(item.name, _("opened it in OneOS"))
	changes.announce(item)
	return {"url": said["url"], "node": item.name, "name": _named(item)}


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


@frappe.whitelist(methods=["POST"])
def close(node: str) -> None:
	"""The reader's own OneOS session on a file closed: the container saves
	and stops, and the lease goes."""
	item = api._item(node)
	held = lease.alone_of(item.name)
	if not held.one_lease_user or held.one_lease_kind != lease.ONEOS:
		return
	if held.one_lease_user != frappe.session.user and not ns.may(item, "write"):
		frappe.throw(_("{0} is open in OneOS by {1}.").format(item.file_name, get_fullname(held.one_lease_user)), frappe.PermissionError)
	if held.one_lease_session:
		from onedesk.one import account

		try:
			account.ask("onedesk.one_admin.proxy.oneos_stop", session=held.one_lease_session)
		except faults.Refused:
			frappe.log_error(title="Closing a OneOS session")
	lease.release(item.name, held.one_lease_lock)
	from onedesk.one_cloud import live as changes

	changes.announce(item)


def _sealed(what: str, f: str, k: str, e: str, s: str) -> dict:
	if not unsealed(what, f, k, e, s, _key(), time.time()):
		raise Forbidden
	item = ns.row(f)
	if not item or item.one_deleted:
		raise NotFound
	if frappe.db.get_value("File", f, "one_lease_lock") not in (None, "", k):
		raise Conflict
	return item


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=120, seconds=60 * 60)
def file(f: str, k: str, e: str, s: str):
	"""The file a session opens, for its container: redirected to a signed
	R2 address, or sent from the disk."""
	item = _sealed(DOWNLOAD, f, k, e, s)
	own = opening.own_of(item)
	if own:
		frappe.local.response.filename = opening.office_name(item, own[0])
		made = _as(item, lambda: opening.exported(*own))
		frappe.cache.set_value(f"onecloud_oneos_saved:{k}", hashlib.md5(made).hexdigest(), expires_in_sec=LONGEST)
		frappe.local.response.filecontent = made
		frappe.local.response.type = "download"
		frappe.local.response.display_content_as = "attachment"
		return
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
	own = opening.own_of(item)
	if own:
		return _into_own(item, own, content, k)
	if hashlib.md5(content).hexdigest() == frappe.db.get_value("File", item.name, "content_hash"):
		return {"saved": False}

	def kept():
		api._need(item, "write")
		_version(item, content, k)

	_as(item, kept)
	return {"saved": True}


def _as(item: dict, then):
	"""`then`, as the person who opened the file in OneOS."""
	was = frappe.session.user
	frappe.set_user(frappe.db.get_value("File", item.name, "one_lease_user") or item.owner)
	try:
		return then()
	finally:
		frappe.set_user(was)


def _into_own(item: dict, own: tuple[str, str], content: bytes, lock: str) -> dict:
	"""A save from OneOS read back into One's own, as a save from the drive
	is (dav.write_own): once for each content a session sends."""
	held = f"onecloud_oneos_saved:{lock}"
	sent = hashlib.md5(content).hexdigest()
	if frappe.cache.get_value(held) == sent:
		return {"saved": False}
	from onedesk.one_cloud import dav

	def kept():
		api._need(item, "write")
		with saving.through(lease.ONEOS):
			dav.write_own({own[0]: own[1]}, content)

	_as(item, kept)
	frappe.cache.set_value(held, sent, expires_in_sec=LONGEST)
	return {"saved": True}


def _version(item: dict, content: bytes, lock: str) -> None:
	from onedesk.one_cloud import history

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
	history.replace(ns.row(item.name), doc.name, sitting=lock)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def stopped(session: str) -> dict:
	"""OneAdmin says a session stopped. Like account.wake it takes nothing on
	trust: the workspace asks OneAdmin with its own token and acts on that."""
	name = frappe.db.get_value("File", {"one_lease_session": session}, "name") if session else None
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
	for row in frappe.get_all("File", filters={"one_lease_user": ["is", "set"], "one_lease_kind": lease.ONEOS}, pluck="name"):
		try:
			_look(row, now)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"OneOS lease on {row}")


def _look(name: str, now=None) -> None:
	from onedesk.one import account

	now = now or now_datetime()
	held = frappe.db.get_value("File", name, ["file_name", *lease.FIELDS], as_dict=True)
	if not held or not held.one_lease_user or held.one_lease_kind != lease.ONEOS:
		return
	if not held.one_lease_session:
		if lease.lapsed(held.one_lease_until, now):
			lease.release(name, held.one_lease_lock)
		return
	try:
		said = account.ask("onedesk.one_admin.proxy.oneos_state", session=held.one_lease_session)
	except faults.Refused:
		said = None
	if said is None:
		if lease.lapsed(held.one_lease_until, now):
			_ended(name, held, None)
		return
	if said.get("state") in ("Starting", "Running"):
		lease.extend(name, held.one_lease_lock, LEASE_SECONDS)
		warned = f"onecloud_oneos_warned:{held.one_lease_session}"
		if not said.get("warn"):
			frappe.cache.delete_value(warned)
		elif not frappe.cache.get_value(warned):
			frappe.cache.set_value(warned, 1, expires_in_sec=30 * 60)
			frappe.publish_realtime("onecloud_oneos", {"file": name, "name": held.file_name, "warn": True}, user=held.one_lease_user, after_commit=True)
		return
	_ended(name, held, said.get("stop_reason"))


def _ended(name: str, held: dict, why: str | None) -> None:
	"""A session is over: the lease goes, and its person hears why when it was
	not their own doing."""
	from onedesk.one_cloud import live as changes
	from onedesk.one_cloud import tell

	lease.release(name, held.one_lease_lock)
	changes.announce(name)
	why = why or "Not Answering"
	frappe.publish_realtime(
		"onecloud_oneos",
		{"file": name, "name": held.file_name, "why": why},
		user=held.one_lease_user,
		after_commit=True,
	)
	if why in TOLD:
		tell.oneos_closed(held.one_lease_user, name, held.file_name)
