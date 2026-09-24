"""Where OneAI reads what arrives, and on whose behalf.

Three switches: a OneCloud folder (and every folder inside it), a OneMail
mailbox, and Intake Settings' "Read Files Attached to Records". Each is turned
on by a person and remembers who, because OneAI may only do there what that
person may do (docs/INTAKE.md §4.3). A person's My Files and own mailbox are
theirs to turn on, not an administrator's.
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
		frappe.throw(_("There is no folder {0} you may open.").format(folder))
	covering, person = of_folder(folder)
	return {
		"on": bool(covering),
		"here": covering == folder,
		"from": frappe.db.get_value("File", covering, "file_name") if covering and covering != folder else None,
		"for": person,
		"may": _may_switch(item),
	}


@frappe.whitelist(methods=["POST"])
def set_folder(folder: str, on: int) -> dict:
	"""Turn reading on or off for a folder and everything inside it."""
	item = ns.row(folder)
	if not item or not item.get("is_folder") or not _may_switch(item):
		frappe.throw(_("Only somebody who may change {0} can say whether OneAI reads it.").format(
			(item or {}).get("file_name") or folder
		), frappe.PermissionError)
	on = int(on or 0)
	frappe.db.set_value(
		"File", folder, {"one_intake": on, "one_intake_for": frappe.session.user if on else None}, update_modified=False
	)
	return folder_state(folder)


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

	actions.require(account)
	on = int(on or 0)
	frappe.db.set_value(
		"Email Account",
		account,
		{"one_intake": on, "one_intake_for": frappe.session.user if on else None},
		update_modified=False,
	)
	return mailbox_state(account)
