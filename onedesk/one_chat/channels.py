"""Who is in a conversation, and so who reads it: its members alone, as
Raven's channels are (docs/ARC-AI.md, OneChat). A channel that is not
private can be found and joined by everybody; reading it still takes
joining. A direct conversation is two people's, an Agent conversation one
person's with one agent. A Room is a conversation with a visitor from the
website (widget.py): read by its members and by the members of the channel
it belongs to (`desk`), who answer it. No role reads around this, an
administrator's neither: what people say to each other is theirs."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from onedesk.one_chat import agents

CHANNEL, DIRECT, AGENT, ROOM = "Channel", "Direct", "Agent", "Room"

VISITOR = "Guest"
"""Who a visitor's message is from: they have no user of their own."""

TITLE = 80


def reads(members: list[str], user: str) -> bool:
	"""Whether a person reads a conversation with these members. Pure."""
	return bool(user) and user in members


def members_of(channel: str) -> list[str]:
	return frappe.get_all("Chat Channel Member", filters={"parent": channel, "parenttype": "Chat Channel"}, pluck="user")


def readers(channel) -> list[str]:
	"""Who reads a conversation: its members, and a room's channel's too."""
	if isinstance(channel, str):
		channel = frappe.db.get_value("Chat Channel", channel, ["name", "kind", "desk"], as_dict=True) or frappe._dict()
		inside = members_of(channel.name) if channel.name else []
	else:
		inside = [one.user for one in channel.get("members") or []]
	if channel.get("kind") == ROOM and channel.get("desk"):
		inside = [*inside, *members_of(channel.desk)]
	return inside


def has_permission(doc, ptype=None, user=None, debug=False) -> bool:
	"""Chat Channel: whoever reads it writes it; anybody may make one."""
	user = user or frappe.session.user
	if ptype == "create" or doc.is_new():
		return True
	return reads(readers(doc), user)


def _mine(user: str) -> str:
	return f"select parent from `tabChat Channel Member` where parenttype = 'Chat Channel' and user = {user}"


def query(user=None) -> str:
	user = frappe.db.escape(user or frappe.session.user)
	return f"(`tabChat Channel`.name in ({_mine(user)}) or (`tabChat Channel`.kind = 'Room' and `tabChat Channel`.desk in ({_mine(user)})))"


def message_permission(doc, ptype=None, user=None, debug=False) -> bool:
	"""Chat Message: whoever reads its conversation reads it; only who wrote
	it changes it."""
	user = user or frappe.session.user
	if not reads(readers(doc.channel), user):
		return False
	if ptype in (None, "read", "create", "select", "print"):
		return True
	return doc.sender == user


def message_query(user=None) -> str:
	user = frappe.db.escape(user or frappe.session.user)
	rooms = f"select name from `tabChat Channel` where kind = 'Room' and desk in ({_mine(user)})"
	return f"(`tabChat Message`.channel in ({_mine(user)}) or `tabChat Message`.channel in ({rooms}))"


def opened(channel: str):
	"""The conversation, when the reader is in it; otherwise a refusal that
	says nothing of what it holds."""
	if not channel or not frappe.db.exists("Chat Channel", channel):
		frappe.throw(_("This conversation doesn't exist."), frappe.DoesNotExistError)
	doc = frappe.get_doc("Chat Channel", channel)
	if not reads(readers(doc), frappe.session.user):
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


def website() -> str | None:
	"""The channel that answers website chats, if one does."""
	return frappe.db.get_value("Chat Channel", {"kind": CHANNEL, "website": 1}, "name")


def answer_website(channel: str, on: bool) -> None:
	"""Whether a channel answers website chats: one at a time, so turning it
	on for one turns it off for the one before. An administrator's call, since
	it puts a chat on the workspace's website."""
	from onedesk.one import roles

	doc = opened(channel)
	if not roles.administers():
		frappe.throw(_("Your role doesn't allow changing this."), frappe.PermissionError)
	if doc.kind != CHANNEL:
		frappe.throw(_("Only a channel can answer website chats."))
	if on:
		for one in frappe.get_all("Chat Channel", filters={"website": 1, "name": ["!=", doc.name]}, pluck="name"):
			frappe.db.set_value("Chat Channel", one, "website", 0)
	frappe.db.set_value("Chat Channel", doc.name, "website", 1 if on else 0)


def room(desk: str, name: str, email: str, key: str, page: str = ""):
	"""A new room with a visitor, for the people of the channel that answers
	it. Made for a guest, so nobody is its first member but them."""
	people = [one for one in members_of(desk) if one and not agents.of_user(one)]
	doc = frappe.new_doc("Chat Channel")
	doc.update(
		{
			"title": name[:TITLE],
			"kind": ROOM,
			"private": 1,
			"desk": desk,
			"visitor_name": name,
			"visitor_email": email,
			"visitor_key": key,
			"page": page,
			"last_message_on": now_datetime(),
		}
	)
	for user in people:
		doc.append("members", {"user": user})
	doc.insert(ignore_permissions=True)
	return doc


def forward(channel: str, to: str):
	"""A room handed to another channel, whose people join it."""
	doc = opened(channel)
	if doc.kind != ROOM:
		frappe.throw(_("Only a room can be forwarded."))
	target = opened(to)
	if target.kind != CHANNEL:
		frappe.throw(_("A room is forwarded to a channel."))
	held = {one.user for one in doc.members}
	for user in members_of(target.name):
		if user and user not in held and not agents.of_user(user):
			doc.append("members", {"user": user})
	doc.desk = target.name
	doc.save(ignore_permissions=True)
	return doc


def close(channel: str, closed: bool = True):
	"""A room closed, or opened again: closed, its visitor writes no more."""
	doc = opened(channel)
	if doc.kind != ROOM:
		frappe.throw(_("Only a room can be closed."))
	frappe.db.set_value("Chat Channel", doc.name, "closed", 1 if closed else 0)
	return doc
