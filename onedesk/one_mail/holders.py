"""Who holds which mailbox, which of them may send from it, and which one is
the workspace's.

To hold a mailbox is to have a `User Email` row for it, which lets them read
it; the row's `one_sends` says whether they may send from it too. A
workspace administrator chooses both for the workspace's mailbox and every
shared one, in OneMail's settings (Workspace Mailboxes)."""

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


def sending_rows(user: str | None = None) -> dict:
	"""The mailboxes `user` holds, and whether each holding lets them send."""
	return {
		row.email_account: row.one_sends is None or bool(row.one_sends)
		for row in frappe.get_all(
			"User Email", filters={"parent": user or frappe.session.user}, fields=["email_account", "one_sends"]
		)
	}


def may_send(account: str, user: str | None = None) -> bool:
	"""Whether `user` may send from `account`: it sends, they hold it, and
	their holding lets them."""
	if not frappe.db.get_value("Email Account", account, "enable_outgoing"):
		return False
	return bool(sending_rows(user).get(account))


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
	rows = sending_rows()
	held = list(rows)
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
				"sends": int(bool(account.enable_outgoing and rows.get(account.name))),
				"error": account.one_error,
				"intake": account.one_intake,
				"receives_only": int(bool(account.one_hosted and not account.enable_outgoing)),
				"may_sign": int(may_sign(account.name)) if account.enable_outgoing and rows.get(account.name) else 0,
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
def shared() -> dict:
	"""The workspace's mailboxes, who reads and who sends from each, and
	whether people may send from their own address: OneMail's settings,
	for an administrator."""
	_admin()
	accounts = frappe.get_all(
		"Email Account",
		filters={"one_shared": 1},
		fields=["name", "email_id", "one_hosted", "one_connected", "enable_outgoing"],
		order_by="email_id asc",
	)
	ours = workspace()
	names = dict(frappe.get_all("User", filters={"user_type": "System User"}, fields=["name", "full_name"], as_list=True))
	for account in accounts:
		account["people"] = [
			{"user": row.parent, "name": names.get(row.parent) or row.parent, "sends": int(row.one_sends is None or bool(row.one_sends))}
			for row in frappe.get_all(
				"User Email",
				filters={"email_account": account.name},
				fields=["parent", "one_sends"],
				order_by="parent asc",
			)
		]
		account["workspace"] = int(account.name == ours)
	accounts.sort(key=lambda one: -one["workspace"])
	return {
		"mailboxes": accounts,
		"personal_sends": int(addresses.personal_sends()),
		"allowed_domains": addresses.allowed_domains(),
		"mail_domain": addresses.domain(),
		"slug": addresses.slug(),
	}


@frappe.whitelist(methods=["POST"])
def set_access(account: str, people) -> list[dict]:
	"""Exactly these people hold one of the workspace's mailboxes, each
	reading it and, where `sends`, sending from it: [{user, sends}]."""
	_admin()
	if not frappe.db.get_value("Email Account", account, "one_shared"):
		frappe.throw(_("{0} is a personal mailbox and can't be shared.").format(account))
	rows = json.loads(people) if isinstance(people, str) else people or []
	wanted = {row["user"]: int(bool(row.get("sends"))) for row in rows if row.get("user")}
	for user in wanted:
		if not frappe.db.get_value("User", {"name": user, "enabled": 1, "user_type": "System User"}):
			frappe.throw(_("{0} isn't in this workspace.").format(user))
	now = set(frappe.get_all("User Email", filters={"email_account": account}, pluck="parent"))
	for user in set(wanted) - now:
		addresses.hold(account, user)
	for user in now - set(wanted):
		frappe.db.delete("User Email", {"parent": user, "email_account": account})
	for user, sends in wanted.items():
		frappe.db.set_value("User Email", {"parent": user, "email_account": account}, "one_sends", sends, update_modified=False)
	from onedesk.one_mail import tell

	tell.mailbox_shared(account, sorted(set(wanted) - now))
	frappe.publish_realtime("one_mailbox", after_commit=True)
	return [{"user": user, "sends": sends} for user, sends in sorted(wanted.items())]


@frappe.whitelist(methods=["POST"])
def grant(account: str, user: str, sends: int = 1) -> None:
	"""One person reads one of the workspace's mailboxes, and with `sends`
	sends from it too; given again, only `sends` changes."""
	rows = {row["user"]: row["sends"] for row in _people(account)}
	rows[user] = int(bool(int(sends)))
	set_access(account, [{"user": one, "sends": on} for one, on in rows.items()])


@frappe.whitelist(methods=["POST"])
def revoke(account: str, user: str) -> None:
	"""One person no longer reads one of the workspace's mailboxes."""
	set_access(account, [row for row in _people(account) if row["user"] != user])


def _people(account: str) -> list[dict]:
	return [
		{"user": row.parent, "sends": int(row.one_sends is None or bool(row.one_sends))}
		for row in frappe.get_all("User Email", filters={"email_account": account}, fields=["parent", "one_sends"])
	]


@frappe.whitelist(methods=["POST"])
def set_personal_sends(on: int) -> int:
	"""Whether people may send from their own address. Every personal address
	follows at once, and so does each one made after."""
	_admin()
	on = int(bool(int(on)))
	frappe.db.set_default(addresses.PERSONAL_SENDS, str(on))
	for name in frappe.get_all("Email Account", filters={"one_hosted": 1, "one_shared": 0}, pluck="name"):
		frappe.db.set_value("Email Account", name, "enable_outgoing", on, update_modified=False)
	frappe.publish_realtime("one_mailbox", after_commit=True)
	return on


@frappe.whitelist(methods=["POST"])
def set_allowed_domains(domains) -> list[str]:
	"""The domains people may connect a personal mailbox at; an empty list
	lets them connect any. A shared mailbox, an administrator's, is not held
	to it."""
	_admin()
	rows = json.loads(domains) if isinstance(domains, str) else domains or []
	clean = []
	for one in rows:
		domain = addresses.domain_of(one)
		if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", domain):
			frappe.throw(_("{0} isn't a domain, such as gmail.com.").format(one))
		if domain not in clean:
			clean.append(domain)
	frappe.db.set_default(addresses.ALLOWED_DOMAINS, ",".join(clean))
	return clean


def sending(doc, method=None) -> None:
	"""Communication before_insert: a person sends only from a mailbox they
	may send from. Mail the workspace sends on its own (no person behind the
	request) is not theirs to refuse."""
	if doc.communication_medium != "Email" or doc.sent_or_received != "Sent":
		return
	user = frappe.session.user
	if user in ("Administrator", "Guest") or not getattr(frappe.local, "request", None) or frappe.flags.in_import:
		return
	account = doc.email_account
	if not account and doc.sender:
		from email.utils import parseaddr

		account = frappe.db.get_value("Email Account", {"email_id": parseaddr(doc.sender)[1]}, "name")
	if not account:
		return
	managed = frappe.db.get_value("Email Account", account, ["one_hosted", "one_connected"]) or (0, 0)
	if any(managed) and not may_send(account, user):
		frappe.throw(
			_("You can't send from {0}. A workspace administrator chooses who may, in OneMail's settings.").format(
				frappe.db.get_value("Email Account", account, "email_id")
			),
			frappe.PermissionError,
		)


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
