"""Where OneAI reads what arrives, and on whose behalf.

Three switches: a OneCloud folder, a OneMail mailbox, and Intake Settings'
"Read Files Attached to Records", each remembering who turned it on.
"""

import frappe
from frappe import _

from onedesk.one_storage import namespace as ns


def of_folder(folder: str | None) -> tuple[str | None, str | None]:
	"""(the folder whose switch covers this one, on whose behalf), or Nones."""
	for at in ns.chain(folder):
		held = frappe.db.get_value("File", at, ["one_intake", "one_intake_for"], as_dict=True)
		if held and held.one_intake:
			return at, held.one_intake_for
	return None, None


def of_mailbox(account: str | None) -> str | None:
	"""On whose behalf a mailbox is read, when it is."""
	if not account:
		return None
	held = frappe.db.get_value("Email Account", account, ["one_intake", "one_intake_for"], as_dict=True)
	return held.one_intake_for if held and held.one_intake else None


def of_file(doc) -> str | None:
	"""On whose behalf a new file is read by a model, or None when no switch
	covers it."""
	if doc.attached_to_doctype and doc.attached_to_name:
		if doc.attached_to_doctype == "Communication":
			account = frappe.db.get_value("Communication", doc.attached_to_name, "email_account")
			return of_mailbox(account)
		return doc.owner if frappe.db.get_single_value("Intake Settings", "records") else None
	return of_folder(doc.folder)[1]


@frappe.whitelist()
def folder_state(folder: str) -> dict:
	item = ns.row(folder)
	if not item or not item.get("is_folder") or not ns.may(item):
		frappe.throw(_("Folder {0} not found").format(folder))
	covering, person = of_folder(folder)
	return {
		"on": bool(covering),
		"here": covering == folder,
		"from": frappe.db.get_value("File", covering, "file_name")
		if covering and covering != folder
		else None,
		"for": person,
		"may": _may_switch(item),
	}


@frappe.whitelist(methods=["POST"])
def read_now(file: str) -> None:
	"""Read one file with OneAI, as the person asking, when no folder of it is
	read. Whoever may open the file may ask; a message's attachment is read
	with its mailbox, and a folder is switched on instead."""
	item = ns.row(file)
	if not item or item.get("is_folder") or item.get("one_deleted") or not ns.may(item):
		frappe.throw(_("File {0} not found").format(file), frappe.PermissionError)
	if item.get("attached_to_doctype") == "Communication":
		frappe.throw(_("A message's attachments are read with its mailbox."))
	from onedesk.one_intake import pipeline

	pipeline.later("read_file", f"file:{item['name']}", name=item["name"], person=frappe.session.user)


@frappe.whitelist(methods=["POST"])
def set_folder(folder: str, on: int) -> dict:
	"""Turn reading on or off for a folder and everything inside it."""
	item = ns.row(folder)
	on = int(on or 0)
	stopping = not on and _administers()
	if not item or not item.get("is_folder") or not (stopping or _may_switch(item)):
		frappe.throw(
			_("Only someone who can edit {0} can change this.").format(
				(item or {}).get("file_name") or folder
			),
			frappe.PermissionError,
		)
	frappe.db.set_value(
		"File",
		folder,
		{"one_intake": on, "one_intake_for": frappe.session.user if on else None},
		update_modified=False,
	)
	return folder_state(folder)


def file_switched(doc, method=None) -> None:
	"""File validate: a folder's switch holds however the folder is changed
	(a bulk edit, an import, frappe.client.set_value). Only whoever may throw
	it does, and it reads for that person and nobody else."""
	if doc.is_new() or not (doc.has_value_changed("one_intake") or doc.has_value_changed("one_intake_for")):
		return
	if doc.flags.ignore_permissions:
		return
	item = doc.as_dict()
	if doc.one_intake:
		if not doc.is_folder or not _may_switch(item):
			frappe.throw(_("Only someone who can edit {0} can change this.").format(doc.file_name), frappe.PermissionError)
		doc.one_intake_for = frappe.session.user
	elif not (_administers() or _may_switch(item)):
		frappe.throw(_("Only someone who can edit {0} can change this.").format(doc.file_name), frappe.PermissionError)
	else:
		doc.one_intake_for = None


def mailbox_switched(doc, method=None) -> None:
	"""Email Account validate: the same for a mailbox. It reads for whoever
	turned it on, and a holder of the mailbox turns it on."""
	if doc.is_new() or not (doc.has_value_changed("one_intake") or doc.has_value_changed("one_intake_for")):
		return
	if doc.flags.ignore_permissions:
		return
	from onedesk.one_mail import actions

	if doc.one_intake:
		actions.require(doc.name)
		doc.one_intake_for = frappe.session.user
		doc.create_contact = 0
	else:
		if not _administers():
			actions.require(doc.name)
		doc.one_intake_for = None


def _may_switch(item: dict) -> bool:
	"""A folder's switch is its owner's to throw: My Files only by its person,
	anything else by whoever may change the folder itself. Attachments and
	Libraries hold other things' files, and have no switch."""
	if item["name"] in (ns.ATTACHMENTS, ns.LIBRARY_ROOT):
		return False
	if item.get("one_home_of"):
		return item["one_home_of"] == frappe.session.user
	return ns.may(item, "write")


@frappe.whitelist()
def mailbox_state(account: str) -> dict:
	from onedesk.one_mail import actions

	actions.require(account)
	held = frappe.db.get_value("Email Account", account, ["one_intake", "one_intake_for"], as_dict=True)
	return {"on": bool(held.one_intake), "for": held.one_intake_for}


@frappe.whitelist(methods=["POST"])
def set_mailbox(account: str, on: int) -> dict:
	"""Turn reading on or off for a mailbox. Any of its holders may."""
	from onedesk.one_mail import actions

	on = int(on or 0)
	if on or not _administers():
		actions.require(account)
	values = {"one_intake": on, "one_intake_for": frappe.session.user if on else None}
	if on:
		values["create_contact"] = 0
	frappe.db.set_value("Email Account", account, values, update_modified=False)
	held = frappe.db.get_value("Email Account", account, ["one_intake", "one_intake_for"], as_dict=True)
	return {"on": bool(held.one_intake), "for": held.one_intake_for}


def overview() -> dict:
	"""Every mailbox, and every folder OneAI reads, for OneIntake Settings."""
	from onedesk.one_mail import actions

	name = frappe.utils.get_fullname
	mailboxes = [
		{
			"name": one.name,
			"email": one.email_id or one.name,
			"on": bool(one.one_intake),
			"for": name(one.one_intake_for) if one.one_intake_for else None,
			"mine": actions.holds(one.name),
		}
		for one in frappe.get_all(
			"Email Account",
			fields=["name", "email_id", "one_intake", "one_intake_for"],
			order_by="email_id asc",
		)
	]
	folders = [
		{"name": one.name, "path": one.name, "for": name(one.one_intake_for) if one.one_intake_for else None}
		for one in frappe.get_all(
			"File",
			filters={"is_folder": 1, "one_intake": 1},
			fields=["name", "one_intake_for"],
			order_by="name asc",
		)
	]
	return {"mailboxes": mailboxes, "folders": folders}


def _administers() -> bool:
	from onedesk.one.roles import administers

	return administers()
