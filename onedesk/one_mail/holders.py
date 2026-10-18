"""Who holds which mailbox, and which one is the workspace's.

To hold a mailbox is to have a `User Email` row for it."""

import json
import re

import frappe
from frappe import _

from onedesk.one_mail import addresses

WORKSPACE = "one_mail_workspace"

ORDER = ("Inbox", "Drafts", "Sent", "Archive", "Junk", "Trash", "Other")


def _administers() -> bool:
	from onedesk.one import roles

	return roles.administers()


def _admin() -> None:
	from onedesk.one import roles

	frappe.only_for(roles.ADMINISTRATOR)


def workspace() -> str | None:
	"""The workspace's mailbox."""
	chosen = frappe.db.get_default(WORKSPACE)
	if chosen and frappe.db.exists("Email Account", chosen):
		return chosen
	return addresses.ensure_workspace()


def may_sign(account: str) -> bool:
	"""Whether the reader may change how a mailbox signs: a mailbox that
	sends, which they hold, and when it is the workspace's, which everybody
	sends under, only as a workspace administrator."""
	from onedesk.one import roles
	from onedesk.one_mail import actions

	sends, shared = frappe.db.get_value("Email Account", account, ["enable_outgoing", "one_shared"]) or (0, 0)
	return bool(sends) and actions.holds(account) and (not shared or roles.administers())


def first_line(html: str | None) -> str:
	"""A signature's first line of text, to show what a mailbox signs with.
	Pure."""
	from frappe.utils import strip_html

	text = re.sub(r"<\s*/?(br|p|div|li)\b[^>]*>", "\n", html or "", flags=re.I)
	return next((line.strip() for line in strip_html(text).splitlines() if line.strip()), "")


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
			"one_intake",
			"signature",
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
				"intake": account.one_intake,
				"receives_only": int(bool(account.one_hosted and not account.enable_outgoing)),
				"may_sign": int(may_sign(account.name)) if account.enable_outgoing else 0,
				"signed": first_line(account.signature),
				"may_reconnect": int(
					bool(account.one_connected) and (not account.one_shared or _administers())
				),
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
			_("{0} is a personal mailbox and can't be shared.").format(account)
		)
	wanted = set(json.loads(users) if isinstance(users, str) else users or [])
	for user in wanted:
		if not frappe.db.get_value("User", {"name": user, "enabled": 1, "user_type": "System User"}):
			frappe.throw(_("{0} isn't in this workspace.").format(user))
	now = set(frappe.get_all("User Email", filters={"email_account": account}, pluck="parent"))
	for user in wanted - now:
		addresses.hold(account, user)
	for user in now - wanted:
		frappe.db.delete("User Email", {"parent": user, "email_account": account})
	from onedesk.one_mail import tell

	tell.mailbox_shared(account, sorted(wanted - now))
	return sorted(wanted)


@frappe.whitelist(methods=["POST"])
def replace(account: str, sends: int = 1) -> str:
	"""A connected mailbox of the workspace's becomes the workspace's mailbox,
	and, with `sends`, what the workspace sends from."""
	_admin()
	doc = frappe.get_doc("Email Account", account)
	if not (doc.one_shared and doc.one_connected):
		frappe.throw(_("Only a shared mailbox can be the workspace mailbox."))
	if int(sends):
		if not doc.enable_outgoing:
			frappe.throw(
				_("{0} was connected without Enable Outgoing, so it can't send.").format(
					doc.email_id
				)
			)
		_sends_for_everybody(doc)
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
		_sends_for_everybody(frappe.get_doc("Email Account", own))
	return own


def _sends_for_everybody(doc) -> None:
	"""The mailbox the workspace sends from. frappe's own save takes the default
	off the one before by saving it as the reader, who may not write mailboxes,
	so it is taken off here first."""
	for other in frappe.get_all("Email Account", filters={"default_outgoing": 1, "name": ["!=", doc.name]}, pluck="name"):
		frappe.db.set_value("Email Account", other, "default_outgoing", 0, update_modified=False)
	doc.default_outgoing = 1
	doc.flags.ignore_permissions = True
	doc.save()


@frappe.whitelist()
def signature_of(account: str) -> str | None:
	"""A mailbox's signature: the address's, whoever writes from it."""
	from onedesk.one_mail import actions

	actions.require(account)
	return frappe.db.get_value("Email Account", account, "signature")


@frappe.whitelist(methods=["POST"])
def set_signature(account: str, signature: str | None = None) -> None:
	"""Change a mailbox's signature: whoever holds it, and for one of the
	workspace's, which everybody sends under, a workspace administrator."""
	from onedesk.one_mail import actions

	actions.require(account)
	if not frappe.db.get_value("Email Account", account, "enable_outgoing"):
		frappe.throw(_("{0} only receives mail, so it has no signature.").format(account))
	if not may_sign(account):
		frappe.throw(
			_("Only a Workspace Administrator can change the signature of {0}.").format(account),
			frappe.PermissionError,
		)
	frappe.db.set_value(
		"Email Account",
		account,
		{"signature": signature or None, "add_signature": int(bool((signature or "").strip()))},
		update_modified=False,
	)


def signed(doc, method=None) -> None:
	"""Email Account validate: a mailbox with a signature signs its mail, and
	one without signs nothing, however the signature was changed."""
	doc.add_signature = int(bool((doc.signature or "").strip()))


@frappe.whitelist()
def signature_for(email: str) -> str | None:
	"""The signature of the address the composer sends from, if the writer
	holds it. Email Account itself is not readable to them."""
	account = frappe.db.get_value(
		"Email Account", {"email_id": email, "add_signature": 1}, ["name", "signature"], as_dict=True
	)
	if not account or not frappe.db.exists(
		"User Email", {"parent": frappe.session.user, "email_account": account.name}
	):
		return None
	return account.signature
