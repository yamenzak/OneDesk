"""A conversation as a team works it (Mail Conversation): who has it,
through frappe's own Assign To; whether it is done; notes the team writes
on it; who is writing a reply now;
when a snoozed one comes back; and whom to tell when nobody has answered.
Notes are frappe's comments on the row.
A conversation's row is made the first time somebody does one of these.
Only the mailbox's holders read or change it (has_permission)."""

import frappe
from frappe import _
from frappe.utils import get_datetime, get_fullname, now_datetime

from onedesk.one_mail import actions, live

CONVERSATION = "Mail Conversation"
REPLYING = "onemail_replying"


def has_permission(doc, ptype=None, user=None) -> bool:
	"""A conversation opens for whoever holds its mailbox."""
	user = user or frappe.session.user
	return user == "Administrator" or bool(frappe.db.exists("User Email", {"parent": user, "email_account": doc.account}))


def _found(account: str, thread: str) -> str | None:
	return frappe.db.get_value(CONVERSATION, {"account": account, "thread": thread})


def _subject(account: str, thread: str) -> str:
	return frappe.db.get_value(
		"Communication", {"email_account": account, "one_thread": thread}, "subject", order_by="communication_date asc"
	) or frappe.db.get_value("Communication", thread, "subject") or ""


def conversation(account: str, thread: str):
	"""The conversation's row, made now if it has none."""
	actions.require(account)
	name = _found(account, thread)
	if name:
		return frappe.get_doc(CONVERSATION, name)
	doc = frappe.get_doc({"doctype": CONVERSATION, "account": account, "thread": thread, "subject": _subject(account, thread)[:140]})
	doc.flags.ignore_permissions = True
	return doc.insert()


def _holders(account: str) -> list[str]:
	return frappe.get_all("User Email", filters={"email_account": account}, pluck="parent", distinct=True)


def _assigned(doc) -> list[str]:
	return frappe.parse_json(doc.get("_assign") or "[]") or []


@frappe.whitelist()
def state(account: str, thread: str) -> dict:
	"""Who has the conversation, whether it is done, its notes, and who may
	be given it."""
	actions.require(account)
	name = _found(account, thread)
	doc = frappe.get_doc(CONVERSATION, name) if name else None
	notes = (
		frappe.get_all(
			"Comment",
			filters={"reference_doctype": CONVERSATION, "reference_name": name, "comment_type": "Comment"},
			fields=["name", "owner", "content", "creation"],
			order_by="creation asc",
		)
		if name
		else []
	)
	people = [one for one in _holders(account) if frappe.db.get_value("User", one, "enabled") and one != "Administrator"]
	return {
		"name": name,
		"status": doc.status if doc else "Open",
		"assigned": [{"user": one, "name": get_fullname(one)} for one in (_assigned(doc) if doc else [])],
		"snoozed_until": doc.snoozed_until if doc else None,
		"remind_at": doc.remind_at if doc and doc.remind_by == frappe.session.user else None,
		"notes": [{**one, "by": get_fullname(one.owner)} for one in notes],
		"people": [{"user": one, "name": get_fullname(one)} for one in sorted(people, key=get_fullname)],
		"shared": bool(frappe.db.get_value("Email Account", account, "one_shared")),
	}


@frappe.whitelist(methods=["POST"])
def assign(account: str, thread: str, user: str | None = None) -> dict:
	"""Give the conversation to one holder of the mailbox, or to nobody. They
	are told as frappe tells anybody given a record."""
	from frappe.desk.form import assign_to

	doc = conversation(account, thread)
	if user and user not in _holders(account):
		frappe.throw(_("{0} doesn't use this mailbox.").format(get_fullname(user)))
	for one in _assigned(doc):
		if one != user:
			assign_to.remove(CONVERSATION, doc.name, one)
	if user and user not in _assigned(frappe.get_doc(CONVERSATION, doc.name)):
		assign_to.add({"assign_to": [user], "doctype": CONVERSATION, "name": doc.name, "description": doc.subject or _("A conversation")})
	live.changed(account)
	return state(account, thread)


@frappe.whitelist(methods=["POST"])
def done(account: str, thread: str, done: int = 1) -> dict:
	"""Mark the conversation done, which closes its assignment, or open it
	again. A new message from outside opens it again on its own."""
	from frappe.desk.form import assign_to

	doc = conversation(account, thread)
	doc.status = "Done" if frappe.utils.cint(done) else "Open"
	doc.flags.ignore_permissions = True
	doc.save()
	if doc.status == "Done":
		assign_to.close_all_assignments(CONVERSATION, doc.name, ignore_permissions=True)
	live.changed(account)
	return state(account, thread)


@frappe.whitelist(methods=["POST"])
def note(account: str, thread: str, content: str) -> dict:
	"""A note for the team, never sent: frappe's comment on the
	conversation's row."""
	from frappe.desk.form.utils import add_comment

	if not (content or "").strip():
		frappe.throw(_("Write a note first."))
	doc = conversation(account, thread)
	add_comment(CONVERSATION, doc.name, content, frappe.session.user, get_fullname(frappe.session.user))
	live.changed(account)
	return state(account, thread)


@frappe.whitelist(methods=["POST"])
def replying(account: str, thread: str, on: int = 1) -> None:
	"""Tell the mailbox's other holders that the reader is writing a reply
	in this conversation, or has stopped."""
	actions.require(account)
	said = {"account": account, "thread": thread, "user": frappe.session.user, "name": get_fullname(frappe.session.user), "on": frappe.utils.cint(on)}
	for user in _holders(account):
		if user != frappe.session.user:
			frappe.publish_realtime(REPLYING, said, user=user)


@frappe.whitelist(methods=["POST"])
def snooze(account: str, thread: str, until: str | None = None) -> dict:
	"""Out of the inbox until then, or back now."""
	doc = conversation(account, thread)
	if until and get_datetime(until) <= now_datetime():
		frappe.throw(_("Choose a time still to come."))
	doc.snoozed_until = until or None
	doc.snoozed_by = frappe.session.user if until else None
	doc.flags.ignore_permissions = True
	doc.save()
	live.changed(account)
	return state(account, thread)


@frappe.whitelist(methods=["POST"])
def remind(account: str, thread: str, at: str | None = None) -> dict:
	"""Tell the reader then if nobody has replied, or forget it."""
	doc = conversation(account, thread)
	if at and get_datetime(at) <= now_datetime():
		frappe.throw(_("Choose a time still to come."))
	doc.remind_at = at or None
	doc.remind_by = frappe.session.user if at else None
	doc.flags.ignore_permissions = True
	doc.save()
	return state(account, thread)


def place(account: str, thread: str) -> str:
	"""Where a conversation opens in OneMail."""
	from urllib.parse import urlencode

	return "/desk/onemail?" + urlencode({"box": account, "thread": thread})


@frappe.whitelist()
def opened(name: str) -> str:
	"""Where a conversation's row opens: in OneMail, as its assignment's and
	its notification's link lead."""
	doc = frappe.get_doc(CONVERSATION, name)
	if not has_permission(doc):
		raise frappe.PermissionError
	return place(doc.account, doc.thread)


def arrived(doc, method=None) -> None:
	"""Communication after_insert: a message from outside opens its
	conversation again, ends its snooze and its reminder."""
	if doc.communication_medium != "Email" or not doc.email_account or doc.sent_or_received != "Received":
		return
	name = _found(doc.email_account, doc.one_thread or doc.name)
	if not name:
		return
	frappe.db.set_value(CONVERSATION, name, {"status": "Open", "snoozed_until": None, "remind_at": None, "remind_by": None})


def due() -> None:
	"""Every few minutes: snoozed conversations whose time has come are back
	in their inbox, unread; a reminder whose time has come with no reply is
	told to whoever asked."""
	from onedesk.one_mail import tell

	now = now_datetime()
	for one in frappe.get_all(CONVERSATION, filters={"snoozed_until": ["<=", now]}, fields=["name", "account", "thread"]):
		frappe.db.set_value(CONVERSATION, one.name, {"snoozed_until": None, "snoozed_by": None})
		newest = frappe.db.get_value(
			"Communication", {"email_account": one.account, "one_thread": one.thread}, "name", order_by="communication_date desc"
		) or one.thread
		if frappe.db.exists("Communication", newest):
			frappe.db.set_value("Communication", newest, "seen", 0, update_modified=False)
		live.changed(one.account)
	for one in frappe.get_all(
		CONVERSATION, filters={"remind_at": ["<=", now]}, fields=["name", "account", "thread", "subject", "remind_by"]
	):
		frappe.db.set_value(CONVERSATION, one.name, {"remind_at": None, "remind_by": None})
		tell.no_reply(one, place(one.account, one.thread))
