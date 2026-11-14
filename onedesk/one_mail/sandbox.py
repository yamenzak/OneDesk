"""A mail's link or attachment seen safely before anybody opens it: the link
in a throwaway browser, the file read from its bytes, both in One's office
Worker away from the workspace, with nothing of the reader's session. An
Office file is offered first as a clean PDF; a program never. AGENTS.md,
Stage 12, has the whole of it."""

import base64
import hashlib

import frappe
from frappe import _

from onedesk.one_admin import faults
from onedesk.one_mail import actions, risk

LOOKED_FOR = 10 * 60
CHECKED_FOR = 30 * 24 * 60 * 60
MOST_LINK = 2048
MOST_CHECKED = 25 * 1024 * 1024
NEVER = ("program", "double", "archive")
UNCHECKED = {
	"encrypted": lambda name: _("{0} has a password, so what it holds couldn't be checked.").format(name),
	"too_deep": lambda name: _("{0} holds archives inside archives, too deep to check.").format(name),
	"too_big": lambda name: _("{0} is too big to check.").format(name),
	"too_many": lambda name: _("{0} holds too many files to check.").format(name),
	"unopened": lambda name: _("{0} is a kind of archive that can't be checked.").format(name),
	"unreadable": lambda name: _("{0} couldn't be read, so it wasn't checked.").format(name),
	"service": lambda name: _("{0} couldn't be checked right now. Try again later.").format(name),
}


def _message(name: str):
	row = frappe.db.get_value("Communication", name, ["name", "email_account", "content"], as_dict=True)
	if not row or not row.email_account:
		frappe.throw(_("This message no longer exists."), frappe.DoesNotExistError)
	actions.require(row.email_account)
	return row


def links_of(content: str | None) -> set[str]:
	"""The web addresses a message's links open. Pure."""
	return {target.strip() for target, _words in risk.links(content, content) if target.strip().lower().startswith(("http://", "https://"))}


def looked(url: str, said: dict) -> dict:
	"""What a link's look shows the reader: where it ends, on which site,
	how many times it was sent on, whether it asks for a password, its
	picture, and what went wrong if anything did. Pure."""
	final = said.get("final_url") or url
	hops = [one for one in said.get("redirects") or [] if one != final]
	failed = said.get("failed")
	return {
		"url": url,
		"final_url": final,
		"site": risk.host_of(final),
		"moved": risk.host_of(final) != risk.host_of(url),
		"redirects": len(hops),
		"title": (said.get("title") or "").strip()[:200],
		"asks_password": bool(said.get("asks_password")),
		"picture": f"data:image/jpeg;base64,{said['picture']}" if said.get("picture") else None,
		"failed": failed,
		"warning": {
			"download": _("This link downloads a file instead of opening a page."),
			"slow": _("The page took too long to open. The picture shows how far it got."),
			"unreachable": _("The page couldn't be reached."),
		}.get(failed),
	}


def _refused(raised: Exception) -> str:
	if isinstance(raised, faults.Refused) and (raised.said == "NotEnough" or "NotEnough" in (raised.detail or "")):
		return _("The workspace has no credits left for this.")
	return _("The link couldn't be previewed right now. Try again later.")


@frappe.whitelist(methods=["POST"])
def link(message: str, url: str) -> dict:
	"""A link of a message, opened in a throwaway browser away from the
	workspace, before the reader opens it: where it ends, its redirects,
	whether it asks for a password and a picture of the page. Only a link
	the message holds, and only for somebody who holds its mailbox."""
	row = _message(message)
	url = (url or "").strip()
	if len(url) > MOST_LINK or url not in links_of(row.content):
		frappe.throw(_("This link isn't in the message."))
	key = f"one_mail_looked:{hashlib.sha256(url.encode()).hexdigest()}"
	kept = frappe.cache.get_value(key)
	if kept:
		return kept
	from onedesk.one import account

	try:
		said = account.ask("onedesk.one_admin.proxy.guard_link", url=url)
	except faults.Refused as raised:
		return {"url": url, "failed": "service", "warning": _refused(raised)}
	shown = looked(url, said or {})
	frappe.cache.set_value(key, shown, expires_in_sec=LOOKED_FOR)
	return shown


def verdict(name: str, found: dict, by_name: dict | None = None) -> dict:
	"""What a checked attachment offers the reader, from what its name says
	(risk.of_file) and what its bytes were found to be: `never` for a
	program or an archive holding one, `clean` for an Office file, which is
	offered as a clean copy first, `unchecked` when it couldn't be read, and
	`checked` otherwise. Pure."""
	reasons = []
	if by_name and by_name.get("why") in NEVER:
		return {"state": "never", "reasons": [risk.words(by_name)], "inside": [], "clean": False}
	program = found.get("program")
	if program:
		held = {"why": "archive", "file": name, "holds": program.rsplit("/", 1)[-1]} if program != name else {"why": "program", "file": name}
		return {"state": "never", "reasons": [risk.words(held)], "inside": found.get("inside") or [], "clean": False}
	if found.get("macros"):
		reasons.append(risk.words({"why": "macro", "file": found["macros"]}))
	if found.get("mismatch"):
		reasons.append(_("{0} isn't the kind of file its name says.").format(name))
	if found.get("scripts"):
		reasons.append(_("{0} has scripts that run when it's opened.").format(name))
	if found.get("page"):
		reasons.append(_("{0} is a web page, which can ask for a password.").format(name))
	unchecked = found.get("unchecked")
	if unchecked:
		reasons.insert(0, UNCHECKED.get(unchecked, UNCHECKED["unreadable"])(name))
	state = "unchecked" if unchecked else "clean" if found.get("office") else "checked"
	return {"state": state, "reasons": reasons, "inside": (found.get("inside") or [])[:100], "clean": state == "clean"}


def _attachment(message: str, file: str):
	row = frappe.db.get_value(
		"File",
		{"name": file, "attached_to_doctype": "Communication", "attached_to_name": message},
		["name", "file_name", "file_url", "file_size", "content_hash", "is_folder", "one_preview_of"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("This attachment no longer exists."), frappe.DoesNotExistError)
	return row


def _found(item) -> dict:
	from onedesk.one import account
	from onedesk.one_cloud import api

	if (item.file_size or 0) > MOST_CHECKED:
		return {"unchecked": "too_big"}
	key = f"one_mail_checked:{item.content_hash or item.name}"
	kept = frappe.cache.get_value(key)
	if kept:
		return kept
	try:
		found = account.ask(
			"onedesk.one_admin.proxy.guard_file",
			name=item.file_name,
			data=base64.b64encode(api._content(item)).decode(),
			programs=sorted(risk.PROGRAMS),
		)
	except faults.Refused:
		return {"unchecked": "service"}
	frappe.cache.set_value(key, found or {}, expires_in_sec=CHECKED_FOR)
	return found or {}


def _clean_copy(item, found: dict) -> bool:
	from onedesk.one_cloud import office

	if item.content_hash and item.one_preview_of == item.content_hash:
		return True
	stem = item.file_name.rsplit(".", 1)[0] if "." in item.file_name else item.file_name
	named = item.file_name if office.converts(item.file_name) else f"{stem}.{found.get('ending') or 'docx'}"
	try:
		office._pdf(frappe._dict({**item, "file_name": named, "is_folder": 0}))
	except (faults.Refused, frappe.ValidationError):
		frappe.clear_last_message()
		return False
	return True


@frappe.whitelist(methods=["POST"])
def check(message: str, file: str) -> dict:
	"""An attachment checked before anybody opens it, away from the
	workspace: what it really is, what an archive holds, and whether it
	carries a program or macros. An Office file gets a clean copy, a PDF,
	offered first. Only for somebody who holds the message's mailbox."""
	_message(message)
	item = _attachment(message, file)
	by_name = risk.of_file(item.file_name, None)
	found = {} if by_name and by_name.get("why") in NEVER else _found(item)
	said = verdict(item.file_name, found, by_name)
	if said["clean"] and not _clean_copy(item, found):
		said = {**said, "state": "checked", "clean": False, "reasons": [*said["reasons"], _("Could not make a clean copy. Only the original can be opened.")]}
	return {**said, "name": item.file_name, "file": item.name, "original": item.file_url if said["state"] != "never" else None}


@frappe.whitelist()
def clean(message: str, file: str) -> None:
	"""An attachment's clean copy, the PDF its check made, to read in the
	browser."""
	from onedesk.one_cloud import office

	_message(message)
	item = _attachment(message, file)
	made = frappe.cache.get_value(f"one_cloud_office:{item.content_hash or item.name}") or office._kept(item.name, item.content_hash)
	if not made:
		frappe.throw(_("This attachment has no clean copy yet."), frappe.DoesNotExistError)
	frappe.local.response.filename = (item.file_name.rsplit(".", 1)[0] if "." in item.file_name else item.file_name) + ".pdf"
	frappe.local.response.filecontent = made
	frappe.local.response.type = "binary"
