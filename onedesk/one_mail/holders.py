"""Who holds which mailbox, and which one is the workspace's.

To hold a mailbox is to have a `User Email` row for it. That is Frappe's own
notion, and Frappe's Communication permission already reads it, so a message
is visible to exactly the people who hold its mailbox. Nothing here adds a
second list.

A mailbox is either somebody's own (their address on the mail domain, or one
they connected) or the workspace's (`one_shared`): the workspace's address,
and addresses such as sales@ a workspace administrator connected for the
workspace. Only the workspace's mailboxes have their holders chosen by an
administrator. Somebody's own Gmail is theirs; an administrator does not see
into it.

The workspace's mailbox is its address on the mail domain until an
administrator puts a connected one in its place, for receiving, sending or
both. The address on the mail domain keeps receiving either way, so nothing
sent to it is lost.
"""

import json

import frappe
from frappe import _

from onedesk.one_mail import addresses

#: The default holding the account that is the workspace's mailbox, when it is
#: not the address on the mail domain.
WORKSPACE = "one_mail_workspace"

#: How folders are listed: the usual ones first, in the order mail clients use.
ORDER = ("Inbox", "Drafts", "Sent", "Archive", "Junk", "Trash", "Other")


def _admin() -> None:
	from onedesk.one import roles

	frappe.only_for(roles.ADMINISTRATOR)


def workspace() -> str | None:
	"""The workspace's mailbox."""
	chosen = frappe.db.get_default(WORKSPACE)
	if chosen and frappe.db.exists("Email Account", chosen):
		return chosen
	return addresses.ensure_workspace()


def ordered(folders: list[dict]) -> list[dict]:
	"""The usual folders first, then the rest by path. Pure."""
	return sorted(
		folders, key=lambda one: (ORDER.index(one.get("kind") or "Other"), (one.get("path") or "").lower())
	)


@frappe.whitelist()
def mailboxes() -> list[dict]:
	"""The reader's mailboxes, with their folders: the workspace's first, then
	the other shared ones, then their own."""
	held = frappe.get_all("User Email", filters={"parent": frappe.session.user}, pluck="email_account")
	if not held:
		return []
	ours = workspace()
	accounts = frappe.get_all(
		"Email Account",
		filters={"name": ["in", held]},
		fields=[
			"name",
			"email_id",
			"one_hosted",
			"one_connected",
			"one_shared",
			"enable_outgoing",
			"one_error",
		],
	)
	folders: dict[str, list] = {}
	for row in frappe.get_all(
		"Mail Folder",
		filters={"account": ["in", held], "hidden": 0},
		fields=["name", "account", "path", "label", "kind", "unread", "total", "delimiter"],
	):
		folders.setdefault(row.account, []).append(row)
	out = []
	for account in accounts:
		listed = ordered(folders.get(account.name, []))
		out.append(
			{
				"name": account.name,
				"email": account.email_id,
				"hosted": account.one_hosted,
				"connected": account.one_connected,
				"shared": account.one_shared,
				"workspace": int(account.name == ours),
				"sends": account.enable_outgoing,
				"error": account.one_error,
				"unread": sum(one.unread or 0 for one in listed if one.kind in ("Inbox", "Other")),
				"folders": listed,
			}
		)
	return sorted(out, key=lambda one: (-one["workspace"], -one["shared"], one["email"]))


@frappe.whitelist()
def shared() -> list[dict]:
	"""The workspace's mailboxes and who holds each, for an administrator."""
	_admin()
	accounts = frappe.get_all(
		"Email Account",
		filters={"one_shared": 1},
		fields=["name", "email_id", "one_hosted", "enable_outgoing"],
	)
	ours = workspace()
	for account in accounts:
		account["holders"] = frappe.get_all(
			"User Email", filters={"email_account": account.name}, pluck="parent"
		)
		account["workspace"] = int(account.name == ours)
	return accounts


@frappe.whitelist(methods=["POST"])
def set_holders(account: str, users) -> list[str]:
	"""Exactly these people hold one of the workspace's mailboxes."""
	_admin()
	if not frappe.db.get_value("Email Account", account, "one_shared"):
		frappe.throw(
			_("Only the workspace's mailboxes are shared out. {0} belongs to one person.").format(account)
		)
	wanted = set(json.loads(users) if isinstance(users, str) else users or [])
	for user in wanted:
		if not frappe.db.get_value("User", {"name": user, "enabled": 1, "user_type": "System User"}):
			frappe.throw(_("{0} is not somebody who works here.").format(user))
	now = set(frappe.get_all("User Email", filters={"email_account": account}, pluck="parent"))
	for user in wanted - now:
		addresses.hold(account, user)
	for user in now - wanted:
		frappe.db.delete("User Email", {"parent": user, "email_account": account})
	return sorted(wanted)


@frappe.whitelist(methods=["POST"])
def replace(account: str, sends: int = 1) -> str:
	"""A connected mailbox of the workspace's becomes the workspace's mailbox,
	and, with `sends`, what the workspace sends from."""
	_admin()
	doc = frappe.get_doc("Email Account", account)
	if not (doc.one_shared and doc.one_connected):
		frappe.throw(_("Only a mailbox connected for the workspace can be the workspace's."))
	if int(sends):
		if not doc.enable_outgoing:
			frappe.throw(
				_("{0} was connected without sending, so it cannot send for the workspace.").format(
					doc.email_id
				)
			)
		doc.default_outgoing = 1
		doc.flags.ignore_permissions = True
		doc.save()
	frappe.db.set_default(WORKSPACE, account)
	return account


@frappe.whitelist(methods=["POST"])
def restore() -> str | None:
	"""The workspace's address on the mail domain is its mailbox again, for
	receiving and sending."""
	_admin()
	frappe.db.set_default(WORKSPACE, None)
	own = addresses.ensure_workspace()
	if own:
		doc = frappe.get_doc("Email Account", own)
		doc.default_outgoing = 1
		doc.flags.ignore_permissions = True
		doc.save()
	return own
