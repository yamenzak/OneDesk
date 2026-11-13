"""Who is in a conversation, and so who reads it: its members alone, as
Raven's channels are (docs/ARC-AI.md, OneChat). A channel that is not
private can be found and joined by everybody; reading it still takes
joining. A direct conversation is two people's, an Agent conversation one
person's with one agent. No role reads around this, an administrator's
neither: what people say to each other is theirs."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from onedesk.one_chat import agents

CHANNEL, DIRECT, AGENT = "Channel", "Direct", "Agent"

TITLE = 80


def reads(members: list[str], user: str) -> bool:
	"""Whether a person reads a conversation with these members. Pure."""
	return bool(user) and user in members


def members_of(channel: str) -> list[str]:
	return frappe.get_all("Chat Channel Member", filters={"parent": channel, "parenttype": "Chat Channel"}, pluck="user")


def has_permission(doc, ptype=None, user=None, debug=False) -> bool:
	"""Chat Channel: a member reads and writes it; anybody may make one."""
	user = user or frappe.session.user
	if ptype == "create" or doc.is_new():
		return True
	return reads([one.user for one in doc.get("members") or []], user)


def query(user=None) -> str:
	user = frappe.db.escape(user or frappe.session.user)
	return (
		"`tabChat Channel`.name in (select parent from `tabChat Channel Member` "
		f"where parenttype = 'Chat Channel' and user = {user})"
	)


def message_permission(doc, ptype=None, user=None, debug=False) -> bool:
	"""Chat Message: whoever reads its conversation reads it; only who wrote
	it changes it."""
	user = user or frappe.session.user
	if not reads(members_of(doc.channel), user):
		return False
	if ptype in (None, "read", "create", "select", "print"):
		return True
	return doc.sender == user


def message_query(user=None) -> str:
	user = frappe.db.escape(user or frappe.session.user)
	return (
		"`tabChat Message`.channel in (select parent from `tabChat Channel Member` "
		f"where parenttype = 'Chat Channel' and user = {user})"
	)


def opened(channel: str):
	"""The conversation, when the reader is in it; otherwise a refusal that
	says nothing of what it holds."""
	if not channel or not frappe.db.exists("Chat Channel", channel):
		frappe.throw(_("This conversation doesn't exist."), frappe.DoesNotExistError)
	doc = frappe.get_doc("Chat Channel", channel)
	if not reads([one.user for one in doc.members], frappe.session.user):
		frappe.throw(_("You aren't a member of this conversation."), frappe.PermissionError)
	return doc


def make(title: str, kind: str, people: list[str], private: bool = False, about: str = "", agent: str = "", key: str | None = None):
	"""A new conversation with its members: the person making it first."""
	me = frappe.session.user
	doc = frappe.new_doc("Chat Channel")
	doc.update(
		{
			"title": (title or "").strip()[:TITLE],
			"kind": kind,
			"private": 1 if private or kind != CHANNEL else 0,
			"about": about,
			"agent": agent,
			"direct_key": key,
			"last_message_on": now_datetime(),
		}
	)
	for user in dict.fromkeys([me, *people]):
		doc.append("members", {"user": user})
	if agent:
		doc.append("members", {"user": agents.user_of(agent), "agent": agent})
	doc.insert(ignore_permissions=True)
	return doc


def direct_key(one: str, other: str) -> str:
	"""The one conversation two people share. Pure."""
	return "\n".join(sorted({one, other}))


def direct(user: str):
	"""The direct conversation between the reader and a person, made the
	first time."""
	me = frappe.session.user
	if user == me or not frappe.db.get_value("User", user, "enabled") or agents.of_user(user):
		frappe.throw(_("{0} can't be messaged.").format(user))
	key = direct_key(me, user)
	held = frappe.db.get_value("Chat Channel", {"direct_key": key}, "name")
	if held:
		return frappe.get_doc("Chat Channel", held)
	return make(frappe.utils.get_fullname(user), DIRECT, [user], key=key)


def with_agent(agent: str, user: str | None = None, title: str = ""):
	"""A new conversation between a person and an agent."""
	if not agents.reaches(agent, user):
		frappe.throw(_("Your role doesn't allow talking to {0}.").format(agents.name_of(agent)), frappe.PermissionError)
	return make(title or agents.name_of(agent), AGENT, [], agent=agent)


def last_with(agent: str, user: str) -> str | None:
	"""The person's latest conversation with an agent, if any."""
	held = frappe.get_all(
		"Chat Channel",
		filters={"kind": AGENT, "agent": agent, "owner": user},
		pluck="name",
		order_by="last_message_on desc",
		limit=1,
	)
	return held[0] if held else None


def join(channel: str):
	doc = frappe.get_doc("Chat Channel", channel)
	if doc.kind != CHANNEL or doc.private:
		frappe.throw(_("Only a member can add you to this conversation."), frappe.PermissionError)
	if frappe.session.user not in [one.user for one in doc.members]:
		doc.append("members", {"user": frappe.session.user})
		doc.save(ignore_permissions=True)
	return doc


def add(channel: str, people: list[str]):
	doc = opened(channel)
	if doc.kind != CHANNEL:
		frappe.throw(_("People can be added to a channel only."))
	held = {one.user for one in doc.members}
	for user in people:
		if user not in held and frappe.db.get_value("User", user, "enabled") and not agents.of_user(user):
			doc.append("members", {"user": user})
	doc.save(ignore_permissions=True)
	return doc


def leave(channel: str) -> None:
	doc = opened(channel)
	if doc.kind != CHANNEL:
		frappe.throw(_("Only a channel can be left."))
	doc.members = [one for one in doc.members if one.user != frappe.session.user]
	doc.save(ignore_permissions=True)


def read(channel: str) -> None:
	"""The reader has seen everything in it until now."""
	frappe.db.set_value(
		"Chat Channel Member",
		{"parent": channel, "parenttype": "Chat Channel", "user": frappe.session.user},
		"last_read",
		now_datetime(),
		update_modified=False,
	)
