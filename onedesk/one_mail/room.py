"""Mail when the workspace's storage is full: the message always arrives.

An attachment refused for room is written down on its message
(`one_unsaved`), and `again`, every hour, saves what now fits."""

import json
from urllib.parse import unquote

import frappe
from frappe.email.receive import Email

from onedesk.one_mail import tell

MOST = 50

TOLD = "one_mail:storage_full_told"


def kept(doc, missing: list[dict]) -> None:
	"""Write down the attachments a message could not keep, and say so."""
	held = unsaved(doc.name)
	names = {one["file_name"] for one in held}
	held += [one for one in missing if one["file_name"] not in names]
	doc.one_unsaved = json.dumps(held)
	frappe.db.set_value("Communication", doc.name, "one_unsaved", doc.one_unsaved, update_modified=False)
	tell.attachments_not_saved(doc)


def unsaved(name: str) -> list[dict]:
	try:
		return json.loads(frappe.db.get_value("Communication", name, "one_unsaved") or "[]") or []
	except ValueError:
		return []


def again() -> int:
	"""Save what fits of every attachment that arrived while storage was full.
	Stops at the first one still refused: the rest would be refused too."""
	from onedesk.one_cloud import store

	saved = 0
	for name in frappe.get_all(
		"Communication", filters={"one_unsaved": ["is", "set"]}, pluck="name", order_by="creation asc", limit=MOST
	):
		wanted = {one["file_name"] for one in unsaved(name)}
		if not wanted:
			continue
		try:
			found = _attachments(frappe.get_doc("Communication", name))
		except Exception:
			frappe.log_error(title=f"OneMail could not take {name} again for its attachments")
			continue
		left = []
		for attachment in found:
			file_name = unquote(attachment["fname"])
			if file_name not in wanted:
				continue
			try:
				_save(name, file_name, attachment["fcontent"])
				saved += 1
			except store.NoRoom:
				left.append({"file_name": file_name, "size": len(attachment["fcontent"] or b"")})
		frappe.db.set_value(
			"Communication", name, "one_unsaved", json.dumps(left) if left else None, update_modified=False
		)
		frappe.db.commit()
		if left:
			break
	if saved:
		frappe.cache.delete_value(TOLD)
	return saved


def _save(communication: str, file_name: str, content: bytes) -> None:
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": "Communication",
			"attached_to_name": communication,
			"is_private": 1,
			"content": content,
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value("Communication", communication, "has_attachment", 1, update_modified=False)


def _attachments(doc) -> list[dict]:
	"""The message's attachments as it arrived: its original in R2 for an
	address on the mail domain, or the server's copy for a connected one."""
	return Email(_original(doc)).attachments


def _original(doc) -> bytes:
	import requests

	from onedesk.one import account

	if doc.get("one_raw_key"):
		url = account.ask("onedesk.one_admin.proxy.storage_get", key=doc.one_raw_key)["url"]
		answer = requests.get(url, timeout=60)
		answer.raise_for_status()
		return answer.content
	from onedesk.one_mail import imap

	with imap.Session(frappe.get_doc("Email Account", doc.email_account)) as session:
		session.select(doc.one_folder, readonly=True)
		row = session.fetch([int(doc.uid)], "(UID FLAGS BODY.PEEK[])").get(int(doc.uid))
	if not row or row.get("body") is None:
		raise LookupError(f"uid {doc.uid} is no longer in {doc.one_folder}")
	return row["body"]
