"""Sharing outside: a link, and the page somebody without an account sees.

A link is a `Cloud Link` row on a File: who may open it (anyone with the link,
or only the people invited by email), what they may do (view, download, and
for a folder upload), until when, and with what password. The link itself is
`/s/<token>`; the row keeps the token encrypted and is found by its hash, so
the table alone opens nothing.

**Opening one is proving something once.** Anyone-links with no password open
straight away. A password, or for an invitation a six-digit code sent to the
address invited, is asked once; the answer is a cookie sealed with the site's
key that names the link, the address and when it runs out, so nothing about a
guest is kept on the server and a cookie from one link opens no other.

**What a guest reaches is the link's file, or what is inside its folder**, now:
something added to a shared folder later is there, something deleted or moved
out is not. `_within` is the whole of that rule and every guest verb asks it.

**Who may make a link** is whoever may change the thing (`namespace.may`
write): its owner, a Workspace Administrator, an editor it was shared with,
or for a record's file whoever may change the record.
"""

import hashlib
import hmac
import random
import time
from urllib.parse import quote, unquote

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_datetime, get_fullname, get_url, now_datetime
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.utils import redirect

from onedesk.one_storage import api, store
from onedesk.one_storage import namespace as ns
from onedesk.one_storage.doctype.cloud_link.cloud_link import hashed

#: How long an unlocked link stays unlocked in one browser.
OPEN_FOR = 12 * 60 * 60

#: How long an emailed code is good for.
CODE_LIFE = 10 * 60

ANYONE, INVITED = "Anyone with the link", "Invited people"


def url_of(token: str) -> str:
	return get_url(f"/s/{token}")


# ------------------------------------------------------------ the owner's side


def _mine(node: str) -> dict:
	item = api._item(node)
	if item.one_home_of:
		frappe.throw(_("Share the folders in My Files, not My Files itself."))
	if not ns.may(item, "write"):
		frappe.throw(_("You may not share {0}.").format(item.file_name), frappe.PermissionError)
	return item


def _describe(link) -> dict:
	return {
		"name": link.name,
		"url": url_of(link.get_password("token")),
		"audience": link.audience,
		"invitees": [one.email for one in link.invitees],
		"allow_download": link.allow_download,
		"allow_upload": link.allow_upload,
		"expires_on": link.expires_on,
		"has_password": bool(link.password),
		"opened": link.opened,
		"expired": bool(link.expires_on and get_datetime(link.expires_on) < now_datetime()),
		"owner": get_fullname(link.owner),
	}


@frappe.whitelist()
@frappe.read_only()
def links(node: str) -> list[dict]:
	"""The links on a file or folder, for whoever may make them."""
	item = api._item(node)
	if not ns.may(item, "write"):
		return []
	names = frappe.get_all("Cloud Link", filters={"file": item.name, "disabled": 0}, pluck="name", order_by="creation desc")
	return [_describe(frappe.get_doc("Cloud Link", name)) for name in names]


@frappe.whitelist(methods=["POST"])
def make(
	node: str,
	audience: str = ANYONE,
	invitees: str | list | None = None,
	allow_download: int = 1,
	allow_upload: int = 0,
	expires_on: str | None = None,
	password: str | None = None,
) -> dict:
	item = _mine(node)
	invitees = frappe.parse_json(invitees) if isinstance(invitees, str) else (invitees or [])
	if audience == INVITED and not can_mail():
		frappe.throw(_("An invitation is sent by email, and this workspace has no outgoing email account yet."))
	link = frappe.get_doc(
		{
			"doctype": "Cloud Link",
			"file": item.name,
			"audience": audience if audience in (ANYONE, INVITED) else ANYONE,
			"invitees": [{"email": email} for email in invitees],
			"allow_download": cint(allow_download),
			"allow_upload": cint(allow_upload),
			"expires_on": expires_on or None,
			# An invitation is proved by the code sent to the address; a
			# password on top would be a second thing to pass on.
			"password": password if audience != INVITED else None,
		}
	)
	link.insert(ignore_permissions=True)
	if link.audience == INVITED:
		_invite(link, [one.email for one in link.invitees], link.flags.token)
	return _describe(link)


@frappe.whitelist(methods=["POST"])
def drop(name: str) -> None:
	link = frappe.get_doc("Cloud Link", name)
	_mine(link.file)
	link.db_set("disabled", 1)


def can_mail() -> bool:
	from frappe.email.doctype.email_account.email_account import EmailAccount

	return bool(EmailAccount.find_outgoing())


def _invite(link, emails: list, token: str) -> None:
	who = get_fullname(frappe.session.user)
	for email in emails:
		frappe.sendmail(
			recipients=[email],
			subject=_("{0} shared {1} with you").format(who, link.file_name),
			message="<br><br>".join(
				(
					_("{0} shared {1} with you.").format(frappe.bold(who), frappe.bold(link.file_name)),
					f'<a href="{url_of(token)}">{_("Open it")}</a>',
					_("You will be asked for a code, which is sent to this address."),
				)
			),
			now=False,
		)


def forget_file(doc, method=None) -> None:
	"""on_trash of File: its links go with it."""
	for name in frappe.get_all("Cloud Link", filters={"file": doc.name}, pluck="name"):
		frappe.delete_doc("Cloud Link", name, ignore_permissions=True, force=True)


# ------------------------------------------------------------ the guest's side


def live(token: str | None):
	"""The link a token names, if it still opens anything, or None."""
	if not token or len(token) > 64:
		return None
	name = frappe.db.get_value("Cloud Link", {"token_hash": hashed(token), "disabled": 0}, "name")
	if not name:
		return None
	link = frappe.get_doc("Cloud Link", name)
	if link.expires_on and get_datetime(link.expires_on) < now_datetime():
		return None
	item = ns.row(link.file)
	if not item or item.one_deleted or _binned(item.folder):
		return None
	return link


def _binned(folder: str | None) -> bool:
	above = ns.chain(folder)
	return bool(above and frappe.db.exists("File", {"name": ["in", above], "one_deleted": 1}))


def needs(link) -> str | None:
	"""What a link asks before it opens: "password", "email", or nothing."""
	if link.audience == INVITED:
		return "email"
	if link.password:
		return "password"
	return None


def _cookie(link) -> str:
	return f"oc_{link.token_hash[:16]}"


def _key() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def seal(token_hash: str, email: str, until: int, key: bytes) -> str:
	"""A cookie value naming the link, the address and the time it runs out,
	that only this site could have made. Pure."""
	body = f"{until}|{email}"
	mac = hmac.new(key, f"{token_hash}|{body}".encode(), hashlib.sha256).hexdigest()
	return f"{body}|{mac}"


def unseal(token_hash: str, value: str | None, key: bytes, now: float) -> str | None:
	"""The address a cookie was sealed for ("" for a password), or None if it
	is not one of ours, is for another link, or has run out. Pure."""
	try:
		until, email, mac = (value or "").rsplit("|", 2)
	except ValueError:
		return None
	good = seal(token_hash, email, int(until) if until.isdigit() else 0, key).rsplit("|", 1)[1]
	if not hmac.compare_digest(good, mac) or int(until) < now:
		return None
	return email


def opened_as(link) -> str | None:
	"""Who has opened this link in this browser: an address, "" for anybody,
	or None if it has not been opened yet."""
	if not needs(link):
		return ""
	# Frappe's cookie manager quotes what it sets, and the request gives it
	# back as it was sent.
	value = unquote(frappe.request.cookies.get(_cookie(link)) or "") if frappe.request else None
	email = unseal(link.token_hash, value, _key(), time.time())
	if email is None:
		return None
	if link.audience == INVITED and email not in {one.email for one in link.invitees}:
		return None
	return email


def _let_in(link, email: str = "") -> None:
	until = int(time.time()) + OPEN_FOR
	frappe.local.cookie_manager.set_cookie(
		_cookie(link), seal(link.token_hash, email, until, _key()), max_age=OPEN_FOR, httponly=True
	)


def _back(token: str, said: str | None = None, folder: str | None = None):
	query = []
	if folder:
		query.append(f"in={quote(folder, safe='')}")
	if said:
		query.append(f"said={said}")
	return redirect(f"/s/{token}" + (f"?{'&'.join(query)}" if query else ""), 303)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=10 * 60)
def unlock(token: str, password: str | None = None):
	link = live(token)
	if not link:
		return _back(token)
	from frappe.utils.password import get_decrypted_password

	kept = get_decrypted_password("Cloud Link", link.name, "password", raise_exception=False)
	if not kept or not hmac.compare_digest(kept.encode(), (password or "").encode()):
		return _back(token, "wrong")
	_let_in(link)
	return _back(token)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=10 * 60)
def ask_code(token: str, email: str | None = None):
	"""Send a code to an invited address. The answer is the same whether it
	was invited or not, so the page does not tell a stranger who was."""
	link = live(token)
	if not link:
		return _back(token)
	email = (email or "").strip().lower()
	if email in {one.email for one in link.invitees}:
		code = f"{random.SystemRandom().randrange(10**6):06d}"
		frappe.cache.set_value(f"onestorage:code:{link.name}:{email}", code, expires_in_sec=CODE_LIFE)
		try:
			frappe.sendmail(
				recipients=[email],
				subject=_("Your code for {0}").format(link.file_name),
				message=_("Your code is {0}. It works for ten minutes.").format(frappe.bold(code)),
				delayed=False,
			)
		except Exception:
			# The page says the same thing either way; the owner finds out
			# from the error log rather than the guest from a stack trace.
			frappe.log_error(title=f"OneCloud could not send a code for {link.name}")
	frappe.local.cookie_manager.set_cookie("oc_email", email, max_age=CODE_LIFE, httponly=True)
	return _back(token, "sent")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=10 * 60)
def enter_code(token: str, code: str | None = None):
	link = live(token)
	if not link:
		return _back(token)
	email = unquote(frappe.request.cookies.get("oc_email") or "").strip().lower()
	key = f"onestorage:code:{link.name}:{email}"
	kept = frappe.cache.get_value(key)
	if not kept or not hmac.compare_digest(str(kept), (code or "").strip()):
		return _back(token, "wrong_code")
	frappe.cache.delete_value(key)
	_let_in(link, email)
	for one in link.invitees:
		if one.email == email and not one.opened_on:
			frappe.db.set_value("Cloud Link Invitee", one.name, "opened_on", now_datetime())
	return _back(token)


def _within(link, name: str | None) -> dict:
	"""The link's own item, or something inside its folder, now; or NotFound."""
	item = ns.row(name or link.file)
	if not item or item.one_deleted:
		raise NotFound
	if item.name == link.file:
		return item
	above = ns.chain(item.folder)
	if link.file not in above or _binned(item.folder):
		raise NotFound
	return item


def contents(link, folder: str) -> list[dict]:
	"""What a guest sees in a folder: its folders and files, not the files
	attached to records that Frappe filed there."""
	found = frappe.get_all(
		"File",
		filters={"folder": folder, "one_deleted": 0},
		fields=ns.FIELDS,
		order_by="is_folder desc, file_name asc",
		limit=2000,
	)
	return [ns.node(one) for one in found if one.is_folder or not (one.attached_to_doctype and one.attached_to_name)]


@frappe.whitelist(allow_guest=True, methods=["GET", "HEAD"])
def get(token: str, item: str | None = None, download: int = 0):
	"""A file through a link: redirected to R2, or sent from the disk."""
	link = live(token)
	if not link or opened_as(link) is None:
		raise NotFound
	found = _within(link, item)
	if found.is_folder:
		raise NotFound
	if cint(download) and not link.allow_download:
		raise Forbidden
	if store.is_stored(found.file_url):
		return redirect(store.signed(store.key_of(found.file_url), filename=found.file_name, inline=not cint(download)), 302)
	doc = frappe.get_doc("File", found.name)
	frappe.local.response.filename = found.file_name
	frappe.local.response.filecontent = doc.get_content()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "attachment" if cint(download) else "inline"


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60 * 60)
def put(token: str, folder: str | None = None):
	"""Files sent into a folder through a link that takes them. They belong
	to whoever made the link, who is told."""
	link = live(token)
	if not link or opened_as(link) is None or not link.allow_upload:
		raise Forbidden
	into = _within(link, folder)
	if not into.is_folder:
		raise NotFound
	sent = [one for one in frappe.request.files.getlist("file") if one and one.filename]
	names = []
	for one in sent[:50]:
		doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": ns.unique_name(api._clean(one.filename) or "file", api._taken(into.name)),
				"folder": into.name,
				"is_private": 1,
				"content": one.stream.read(),
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		frappe.db.set_value("File", doc.name, "owner", link.owner, update_modified=False)
		names.append(doc.file_name)
	if names:
		_tell_owner(link, into, names)
	return _back(token, f"sent_{len(names)}", into.name if into.name != link.file else None)


def _tell_owner(link, into: dict, names: list) -> None:
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	enqueue_create_notification(
		link.owner,
		{
			"type": "Alert",
			"document_type": "File",
			"document_name": into.name,
			"subject": _("{0} files arrived in {1} through your link").format(len(names), frappe.bold(into.file_name))
			if len(names) > 1
			else _("{0} arrived in {1} through your link").format(frappe.bold(names[0]), frappe.bold(into.file_name)),
			"link": f"/desk/onecloud?node={quote(into.name, safe='')}",
		},
	)


def seen(link) -> None:
	frappe.db.set_value(
		"Cloud Link", link.name, {"opened": cint(link.opened) + 1, "last_opened": now_datetime()}, update_modified=False
	)
