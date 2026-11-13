"""What OneChat's screen calls (frontend/src/chat): the reader's
conversations, one conversation's messages and threads, sending, reacting,
and an agent's cards. Every call reads only conversations the reader is in
(channels.py)."""

import frappe
from frappe import _
from frappe.utils import cint

from onedesk.one_chat import agents, answers, cards, channels, messages

PAGE = 50


@frappe.whitelist(methods=["GET"])
def start() -> dict:
	"""The reader, the agents they may talk to and their conversations."""
	from onedesk.one import rights

	return {
		"me": frappe.session.user,
		"agents": agents.listed(),
		"channels": conversations(),
		"may_make": rights.held("Chat Channel", "chat_channels"),
	}


@frappe.whitelist(methods=["GET"])
def conversations() -> list[dict]:
	"""Every conversation the reader is in, newest first, with what is unread."""
	me = frappe.session.user
	held = frappe.get_all(
		"Chat Channel Member",
		filters={"parenttype": "Chat Channel", "user": me},
		fields=["parent", "last_read"],
		limit_page_length=0,
	)
	if not held:
		return []
	read = {one.parent: one.last_read for one in held}
	rows = frappe.get_all(
		"Chat Channel",
		filters={"name": ["in", list(read)]},
		fields=["name", "title", "kind", "private", "agent", "about", "last_message_on"],
		order_by="last_message_on desc",
		limit_page_length=0,
	)
	others = _others([one.name for one in rows if one.kind == channels.DIRECT], me)
	return [
		{
			**row,
			"last_message_on": str(row.last_message_on) if row.last_message_on else None,
			"with": others.get(row.name),
			"unread": _unread(row.name, read.get(row.name), me),
		}
		for row in rows
	]


def _others(names: list[str], me: str) -> dict[str, dict]:
	if not names:
		return {}
	found = frappe.get_all(
		"Chat Channel Member",
		filters={"parenttype": "Chat Channel", "parent": ["in", names], "user": ["!=", me]},
		fields=["parent", "user"],
	)
	return {one.parent: {"user": one.user, "name": frappe.utils.get_fullname(one.user), "image": frappe.db.get_value("User", one.user, "user_image")} for one in found}


def _unread(channel: str, since, me: str) -> int:
	filters = {"channel": channel, "thread": ("is", "not set"), "sender": ["!=", me]}
	if since:
		filters["creation"] = [">", since]
	return frappe.db.count("Chat Message", filters)


@frappe.whitelist(methods=["GET"])
def channel(channel: str, before: str | None = None, thread: str | None = None) -> dict:
	"""One conversation's messages, oldest first, a page at a time; or one
	thread's: its first message and every reply."""
	doc = channels.opened(channel)
	filters = {"channel": doc.name, "thread": thread or ("is", "not set")}
	if before:
		filters["creation"] = ["<", before]
	names = frappe.get_all("Chat Message", filters=filters, pluck="name", order_by="creation desc", limit=PAGE)
	said = [messages.shaped(frappe.get_doc("Chat Message", name)) for name in reversed(names)]
	if thread and not before:
		said.insert(0, messages.shaped(frappe.get_doc("Chat Message", thread)))
	return {
		"name": doc.name,
		"title": doc.title,
		"kind": doc.kind,
		"private": doc.private,
		"about": doc.about,
		"agent": doc.agent,
		"members": [{"user": one.user, "agent": one.agent, "name": agents.name_of(one.agent) if one.agent else frappe.utils.get_fullname(one.user)} for one in doc.members],
		"messages": said,
		"more": len(names) == PAGE,
		"cards": {name: cards.card(name) for name in {one["action"] for one in said if one["action"]}},
	}


@frappe.whitelist(methods=["POST"])
def seen(channel: str) -> dict:
	"""The reader has read everything in a conversation until now."""
	channels.opened(channel)
	channels.read(channel)
	return {"seen": channel}


@frappe.whitelist(methods=["POST"])
def send(channel: str, text: str = "", thread: str | None = None, files=None, page=None, field=None) -> dict:
	"""Say something; an agent asked or mentioned starts answering."""
	doc = channels.opened(channel)
	text = (text or "").strip()
	attached = messages.readable_files(frappe.parse_json(files) if isinstance(files, str) else (files or []), frappe.session.user)
	if not text and not attached:
		frappe.throw(_("Write a message or add a file."))
	root = frappe.db.get_value("Chat Message", thread, ["channel", "thread"], as_dict=True) if thread else None
	if thread and (not root or root.channel != doc.name or root.thread):
		frappe.throw(_("Replies go under a message in this conversation."))
	people, named = messages.mentions_in(text, doc)
	agent = doc.agent if doc.kind == channels.AGENT else (named[0] if named else None)
	held = answers.ready(doc, thread) if agent else None
	mentions = [{"user": user} for user in people] + [{"agent": one} for one in named]
	message = messages.post(doc, text, thread=thread, files=attached, mentions=mentions)
	messages.notify(message, doc, people)
	run = answers.ask(message, doc, agent, held, page=page, field=field) if agent else None
	return {"message": messages.shaped(message), "run": run, "agent": agent}


@frappe.whitelist(methods=["POST"])
def react(message: str, emoji: str) -> dict:
	return messages.react(message, emoji)


@frappe.whitelist(methods=["POST"])
def make(title: str, private: int = 0, about: str = "", people=None) -> dict:
	"""A new channel, with the people asked into it."""
	from onedesk.one import rights

	if not rights.held("Chat Channel", "chat_channels"):
		frappe.throw(_("Your role doesn't allow making channels."), frappe.PermissionError)
	if not (title or "").strip():
		frappe.throw(_("{0} is required.").format(_("Title")))
	people = frappe.parse_json(people) if isinstance(people, str) else (people or [])
	people = [one for one in people if frappe.db.get_value("User", one, "enabled") and not agents.of_user(one)]
	return {"name": channels.make(title, channels.CHANNEL, people, private=bool(cint(private)), about=about).name}


@frappe.whitelist(methods=["POST"])
def direct(user: str) -> dict:
	return {"name": channels.direct(user).name}


@frappe.whitelist(methods=["POST"])
def talk(agent: str) -> dict:
	"""The reader's latest conversation with an agent, or a new one."""
	held = channels.last_with(agent, frappe.session.user)
	return {"name": held or channels.with_agent(agent).name}


@frappe.whitelist(methods=["GET"])
def browse() -> list[dict]:
	"""The channels the reader may join: every one that is not private."""
	me = frappe.session.user
	rows = frappe.get_all(
		"Chat Channel",
		filters={"kind": channels.CHANNEL, "private": 0},
		fields=["name", "title", "about"],
		order_by="title asc",
		limit_page_length=0,
	)
	inside = set(frappe.get_all("Chat Channel Member", filters={"parenttype": "Chat Channel", "user": me}, pluck="parent"))
	return [{**row, "member": row.name in inside, "members": frappe.db.count("Chat Channel Member", {"parent": row.name, "parenttype": "Chat Channel"})} for row in rows]


@frappe.whitelist(methods=["POST"])
def join(channel: str) -> dict:
	return {"name": channels.join(channel).name}


@frappe.whitelist(methods=["POST"])
def add(channel: str, people) -> dict:
	people = frappe.parse_json(people) if isinstance(people, str) else (people or [])
	return {"members": len(channels.add(channel, people).members)}


@frappe.whitelist(methods=["POST"])
def leave(channel: str) -> dict:
	channels.leave(channel)
	return {"left": channel}


@frappe.whitelist(methods=["POST"])
def approve(action: str) -> dict:
	return cards.approve(action)


@frappe.whitelist(methods=["POST"])
def dismiss(action: str) -> dict:
	return cards.dismiss(action)


@frappe.whitelist(methods=["POST"])
def change(action: str, values) -> dict:
	return cards.change(action, values)
