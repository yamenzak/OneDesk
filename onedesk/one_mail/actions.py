"""What a person does to mail: read, star, move, delete, and folders.

For a connected mailbox the server is the truth, so each change is made there
first, and here only once the server has taken it. A phone reading the same
mailbox sees it at once, and the next sync finds nothing to undo. For a hosted
mailbox, on the mail domain, there is no server: its folders and flags live
only here.

Read and starred state belongs to the mailbox, not to the person: two people
holding sales@ see one inbox, as the server does.

Only somebody who holds a mailbox, through a `User Email` row, may change
anything in it. Being a workspace administrator is not enough: somebody's own
mailbox is theirs.

Delete moves to the mailbox's Trash. Deleting from Trash removes the message
from the server for good. The Communication goes too, unless it is linked to
a record (a contact does not count, since Frappe links those by itself): then
it stays on the record's timeline and only leaves the mailbox.
"""

import json

import frappe
from frappe import _

from onedesk.one_mail import imap, live

#: Folders every hosted mailbox has, as (path, kind).
STANDARD = (
	("INBOX", "Inbox"),
	("Sent", "Sent"),
	("Drafts", "Drafts"),
	("Junk", "Junk"),
	("Trash", "Trash"),
	("Archive", "Archive"),
)

#: Kinds a person may not rename or delete.
FIXED = ("Inbox", "Sent", "Drafts", "Junk", "Trash", "Archive")


# ------------------------------------------------------------------ who


def holds(account: str, user: str | None = None) -> bool:
	"""Holding a mailbox is a User Email row for it, as Frappe's own
	Communication permission reads it (holders.py)."""
	return bool(
		frappe.db.exists("User Email", {"parent": user or frappe.session.user, "email_account": account})
	)


def require(account: str) -> None:
	# A mailbox's own rules act for it (rules.py), whoever the job runs as.
	if frappe.flags.one_mail_rules:
		return
	if not holds(account):
		raise frappe.PermissionError(_("You do not hold the mailbox {0}.").format(account))


# ------------------------------------------------------------------ helpers


def _names(names) -> list[str]:
	if isinstance(names, str):
		names = json.loads(names) if names.startswith("[") else [names]
	return list(dict.fromkeys(names or []))


def _rows(names) -> list[dict]:
	rows = frappe.get_all(
		"Communication",
		filters={"name": ["in", _names(names)], "communication_medium": "Email"},
		fields=["name", "email_account", "one_folder", "uid", "reference_doctype", "reference_name"],
	)
	for account in {row.email_account for row in rows}:
		if not account:
			frappe.throw(_("A message that belongs to no mailbox cannot be changed here."))
		require(account)
	return rows


def _grouped(rows) -> dict[tuple[str, str], list[dict]]:
	out: dict[tuple[str, str], list[dict]] = {}
	for row in rows:
		out.setdefault((row.email_account, row.one_folder), []).append(row)
	return out


def _connected(account: str) -> bool:
	return bool(frappe.db.get_value("Email Account", account, "one_connected"))


def _uids(rows) -> list[int]:
	return [int(row.uid) for row in rows if row.uid]


def _set(rows, values: dict) -> None:
	for row in rows:
		frappe.db.set_value("Communication", row.name, values, update_modified=False)


def recount(account: str, path: str | None) -> None:
	"""A folder's unread count, after a change here."""
	folder = frappe.db.get_value("Mail Folder", {"account": account, "path": path}, "name") if path else None
	if folder:
		unread = frappe.db.count("Communication", {"email_account": account, "one_folder": path, "seen": 0})
		frappe.db.set_value("Mail Folder", folder, "unread", unread, update_modified=False)
	live.changed(account)


def folder_of(account: str, kind: str) -> str | None:
	"""The path of a mailbox's folder of this kind."""
	return frappe.db.get_value("Mail Folder", {"account": account, "kind": kind, "hidden": 0}, "path")


def standard(account: str) -> None:
	"""A hosted mailbox's folders, made if missing."""
	for path, kind in STANDARD:
		if not frappe.db.exists("Mail Folder", {"account": account, "path": path}):
			frappe.get_doc(
				{
					"doctype": "Mail Folder",
					"account": account,
					"path": path,
					"label": path.title(),
					"kind": kind,
					"delimiter": "/",
				}
			).insert(ignore_permissions=True)


# ------------------------------------------------------------------ flags


def _flag(names, field: str, flag: str, on: int) -> int:
	rows = _rows(names)
	on = int(bool(int(on)))
	for (account, path), group in _grouped(rows).items():
		if _connected(account) and path and _uids(group):
			with imap.Session(frappe.get_doc("Email Account", account)) as session:
				session.select(path, readonly=False)
				session.store(_uids(group), "+FLAGS.SILENT" if on else "-FLAGS.SILENT", flag)
		_set(group, {field: on})
		recount(account, path)
	return len(rows)


@frappe.whitelist(methods=["POST"])
def mark(names, seen: int = 1) -> int:
	"""Mark messages read, or unread."""
	return _flag(names, "seen", "\\Seen", seen)


@frappe.whitelist(methods=["POST"])
def star(names, flagged: int = 1) -> int:
	"""Star messages, or take the star off."""
	return _flag(names, "one_flagged", "\\Flagged", flagged)


# ------------------------------------------------------------------ moving


@frappe.whitelist(methods=["POST"])
def move(names, folder: str) -> int:
	"""Move messages into a folder of the same mailbox."""
	target = frappe.get_doc("Mail Folder", folder)
	rows = _rows(names)
	for (account, path), group in _grouped(rows).items():
		if account != target.account:
			frappe.throw(_("A message can only move to a folder of its own mailbox."))
		if path == target.path:
			continue
		_move(account, path, group, target.path)
	return len(rows)


def _move(account: str, path: str | None, group: list, to: str) -> None:
	now = {}
	if _connected(account) and path and _uids(group):
		with imap.Session(frappe.get_doc("Email Account", account)) as session:
			session.select(path, readonly=False)
			now = session.move(_uids(group), to)
	for row in group:
		# Without COPYUID the new uid is unknown; the next sync reads the target
		# folder and finds the message by its Message-ID.
		frappe.db.set_value(
			"Communication",
			row.name,
			{"one_folder": to, "uid": now.get(int(row.uid or 0), 0)},
			update_modified=False,
		)
	recount(account, path)
	recount(account, to)


@frappe.whitelist(methods=["POST"])
def delete(names) -> int:
	"""Into Trash; out of Trash for good."""
	rows = _rows(names)
	for (account, path), group in _grouped(rows).items():
		trash = folder_of(account, "Trash")
		if trash and path != trash:
			_move(account, path, group, trash)
			continue
		if _connected(account) and path and _uids(group):
			with imap.Session(frappe.get_doc("Email Account", account)) as session:
				session.select(path, readonly=False)
				session.expunge(_uids(group))
		for row in group:
			if linked(row):
				frappe.db.set_value(
					"Communication", row.name, {"one_folder": None, "uid": 0}, update_modified=False
				)
			else:
				frappe.delete_doc("Communication", row.name, ignore_permissions=True, force=True)
		recount(account, path)
	return len(rows)


def linked(row) -> bool:
	"""Whether a message is on a record's timeline. Frappe links every message
	to the contacts it names by itself; those links are not somebody's
	choice and do not keep a message."""
	return bool(row.reference_name) or bool(
		frappe.db.exists(
			"Communication Link", {"parent": row.name, "link_doctype": ["not in", ("Contact", "Address")]}
		)
	)


# ------------------------------------------------------------------ folders


def _path(account: str, label: str, parent: str | None) -> tuple[str, str]:
	label = (label or "").strip()
	if not label or len(label) > 100:
		frappe.throw(_("A folder needs a name of up to 100 characters."))
	delimiter = "/"
	if parent:
		delimiter = frappe.db.get_value("Mail Folder", parent, "delimiter") or "/"
	else:
		delimiter = (
			frappe.db.get_value("Mail Folder", {"account": account, "delimiter": ["is", "set"]}, "delimiter")
			or "/"
		)
	if delimiter in label:
		frappe.throw(_("A folder's name cannot hold {0}.").format(delimiter))
	parent_path = frappe.db.get_value("Mail Folder", parent, "path") if parent else None
	path = imap.encode(label)
	return (f"{parent_path}{delimiter}{path}" if parent_path else path), delimiter


@frappe.whitelist(methods=["POST"])
def create_folder(account: str, label: str, parent: str | None = None) -> str:
	require(account)
	path, delimiter = _path(account, label, parent)
	if frappe.db.exists("Mail Folder", {"account": account, "path": path}):
		frappe.throw(_("There is already a folder called {0}.").format(label))
	if _connected(account):
		with imap.Session(frappe.get_doc("Email Account", account)) as session:
			session.create(path)
	doc = frappe.get_doc(
		{
			"doctype": "Mail Folder",
			"account": account,
			"path": path,
			"label": label.strip(),
			"kind": "Other",
			"delimiter": delimiter,
		}
	)
	doc.insert(ignore_permissions=True)
	live.changed(account)
	return doc.name


def _own(folder: str):
	doc = frappe.get_doc("Mail Folder", folder)
	require(doc.account)
	if doc.kind in FIXED:
		frappe.throw(
			_("{0} is one of the mailbox's own folders and stays as it is.").format(doc.label or doc.path)
		)
	return doc


@frappe.whitelist(methods=["POST"])
def rename_folder(folder: str, label: str) -> str:
	doc = _own(folder)
	parent = doc.path.rsplit(doc.delimiter, 1)[0] if doc.delimiter and doc.delimiter in doc.path else None
	path = imap.encode(label.strip())
	path = f"{parent}{doc.delimiter}{path}" if parent else path
	if path == doc.path:
		return doc.name
	if _connected(doc.account):
		with imap.Session(frappe.get_doc("Email Account", doc.account)) as session:
			session.rename(doc.path, path)
	# The folder and everything under it now have new paths.
	old = doc.path
	for row in [{"name": doc.name, "path": old}, *_under(doc)]:
		moved = path + row["path"][len(old) :]
		frappe.db.set_value("Mail Folder", row["name"], "path", moved, update_modified=False)
		frappe.db.set_value(
			"Communication",
			{"email_account": doc.account, "one_folder": row["path"]},
			"one_folder",
			moved,
			update_modified=False,
		)
	frappe.db.set_value("Mail Folder", doc.name, "label", label.strip(), update_modified=False)
	live.changed(doc.account)
	return doc.name


def _under(doc) -> list[dict]:
	"""The folders inside this one, deepest first."""
	if not doc.delimiter:
		return []
	rows = frappe.get_all(
		"Mail Folder",
		filters={"account": doc.account, "path": ["like", f"{doc.path}{doc.delimiter}%"]},
		fields=["name", "path"],
	)
	return sorted(rows, key=lambda row: -len(row["path"]))


@frappe.whitelist(methods=["POST"])
def delete_folder(folder: str) -> None:
	"""Its messages go to Trash first, and its folders with it."""
	doc = _own(folder)
	for row in [*_under(doc), {"name": doc.name, "path": doc.path}]:
		inside = frappe.get_all(
			"Communication", filters={"email_account": doc.account, "one_folder": row["path"]}, pluck="name"
		)
		if inside:
			delete(inside)
		if _connected(doc.account):
			with imap.Session(frappe.get_doc("Email Account", doc.account)) as session:
				session.delete(row["path"])
		frappe.delete_doc("Mail Folder", row["name"], ignore_permissions=True, force=True)
	live.changed(doc.account)
