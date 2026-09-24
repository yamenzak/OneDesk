"""Mail in OneCloud: every attachment, in a folder per mailbox.

OneCloud's **Mail** holds one folder for each mailbox the reader holds, and in
each the files that came or went with its messages, newest first. Nothing is
stored for these folders. They are worked out from the Files attached to the
mailbox's Communications whenever they are opened, the way a record's folder
is, so a mailbox's folder is exactly its attachments and is seen by exactly
its holders.

A file here answers to its message (one_mail/access.py). Copying one to My
Files makes a new row on the same object, as any copy in OneCloud does, and
that copy is the reader's own.
"""

import frappe
from frappe import _

from onedesk.one_mail import holders

#: The node ids: `@mail`, and `@mail/<mailbox>`.
MAIL = "@mail"

#: How many files a mailbox's folder lists.
MOST = 500


def node_of(account: str) -> str:
	return f"{MAIL}/{account}"


def account_of(node_id: str) -> str | None:
	return node_id[len(MAIL) + 1 :] if node_id.startswith(MAIL + "/") else None


def _held() -> list[str]:
	return frappe.get_all("User Email", filters={"parent": frappe.session.user}, pluck="email_account")


def mailboxes() -> list[dict]:
	"""The folders under Mail: the reader's mailboxes, as holders.mailboxes
	orders them."""
	from onedesk.one_storage import namespace as ns

	return [
		ns.virtual(
			node_of(box["name"]),
			_("Workspace") if box["workspace"] else box["email"],
			icon="mail",
			mailbox=box["name"],
		)
		for box in holders.mailboxes()
	]


def files(account: str, search: str | None = None) -> list[dict]:
	"""A mailbox's attachments, newest first."""
	from onedesk.one_storage import namespace as ns

	if account not in _held():
		return []
	F = frappe.qb.DocType("File")
	C = frappe.qb.DocType("Communication")
	query = (
		frappe.qb.from_(F)
		.join(C)
		.on((F.attached_to_doctype == "Communication") & (F.attached_to_name == C.name))
		.where(C.email_account == account)
		.where(F.is_folder == 0)
		.select(*[F[field] for field in ns.FIELDS], C.subject.as_("message"))
		.orderby(F.creation, order=frappe.qb.desc)
		.limit(MOST)
	)
	if search:
		query = query.where(F.file_name.like(f"%{search}%"))
	return [{**ns.node(one), "where": one.message or ""} for one in query.run(as_dict=True)]


def trail(node_id: str) -> list[dict]:
	out = [{"id": "@root", "name": _("OneCloud")}, {"id": MAIL, "name": _("Mail")}]
	account = account_of(node_id)
	if account:
		out.append(
			{"id": node_id, "name": frappe.db.get_value("Email Account", account, "email_id") or account}
		)
	return out
