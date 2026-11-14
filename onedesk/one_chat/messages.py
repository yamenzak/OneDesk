"""Writing a message: who it mentions and who is told, the thread it
replies in, the files it carries, and the live update to everybody in the
conversation. Live updates go to the conversation's room, which frappe's
socket.io lets only a reader join (doc_subscribe asks has_permission), and
a short note to each member's own room, so their list of conversations
marks it unread."""

import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from onedesk.one_chat import agents, channels

LIVE = "one_chat_message"
UNREAD = "one_chat_unread"
CHANGED = "one_chat_changed"

MENTIONED = "Mention in a Conversation"
DIRECT = "Direct Message"

SHOWN = 160
REACTIONS = 12


def post(channel, text: str = "", thread: str | None = None, files=(), sender: str | None = None, agent: str = "", **more):
	"""One message, written as whoever says it, with the conversation and its
	thread brought up to date and everybody in it told live."""
	doc = frappe.new_doc("Chat Message")
	doc.update(
		{
			"channel": channel.name,
			"thread": thread,
			"sender": sender if sender is not None else frappe.session.user,
			"agent": agent,
			"text": text,
			**more,
		}
	)
	for file in files:
		doc.append("files", {"file": file})
	doc.insert(ignore_permissions=True)
	now = now_datetime()
	frappe.db.set_value("Chat Channel", channel.name, "last_message_on", now, update_modified=False)
	if thread:
		frappe.db.set_value(
			"Chat Message",
			thread,
			{"replies": cint(frappe.db.get_value("Chat Message", thread, "replies")) + 1, "last_reply_on": now},
			update_modified=False,
		)
	live(doc)
	return doc


def live(doc, event: str = LIVE) -> None:
	said = shaped(doc)
	frappe.publish_realtime(event, said, doctype="Chat Channel", docname=doc.channel, after_commit=True)
	if event != LIVE:
		return
	for user in channels.members_of(doc.channel):
		if user and user != doc.sender:
			frappe.publish_realtime(UNREAD, {"channel": doc.channel, "thread": doc.thread}, user=user, after_commit=True)


def shaped(doc) -> dict:
	"""A message as the conversation draws it."""
	return {
		"name": doc.name,
		"channel": doc.channel,
		"thread": doc.thread,
		"sender": doc.sender,
		"agent": doc.agent,
		"automation": (frappe.db.get_value("Automation", doc.automation, "title") or doc.automation) if doc.automation else None,
		"text": doc.text or "",
		"creation": str(doc.creation),
		"replies": cint(doc.replies),
		"last_reply_on": str(doc.last_reply_on) if doc.last_reply_on else None,
		"reactions": reactions_of(doc.reactions),
		"files": files_of(doc),
		"action": doc.action,
		"parts": json.loads(doc.parts) if isinstance(doc.parts, str) and doc.parts else (doc.parts or None),
		"mentions": [one.user or one.agent for one in doc.get("mentions") or []],
	}


def files_of(doc) -> list[dict]:
	names = [one.file for one in doc.get("files") or []]
	if not names:
		return []
	found = frappe.get_all("File", filters={"name": ["in", names]}, fields=["name", "file_name", "file_url", "file_size"])
	return [{"name": one.name, "file_name": one.file_name, "file_url": one.file_url, "size": one.file_size} for one in found]


def readable_files(files: list[str], user: str) -> list[str]:
	"""The files of OneCloud a person may attach: those they may open."""
	kept = []
	for name in files or []:
		if frappe.db.exists("File", name) and frappe.has_permission("File", "read", doc=name, user=user):
			kept.append(name)
		else:
			frappe.throw(_("You don't have permission to share {0}.").format(name), frappe.PermissionError)
	return kept


def reactions_of(value) -> dict[str, list[str]]:
	if isinstance(value, str):
		value = json.loads(value or "{}") if value.strip() else {}
	return value if isinstance(value, dict) else {}


def reacted(reactions: dict, emoji: str, user: str) -> dict:
	"""The reactions with one person's emoji added, or taken off when they
	had it. Pure."""
	held = {key: list(users) for key, users in (reactions or {}).items()}
	people = held.get(emoji, [])
	if user in people:
		people = [one for one in people if one != user]
	else:
		people = [*people, user]
	if people:
		held[emoji] = people
	else:
		held.pop(emoji, None)
	return held


def told(kind: str, members: list[str], sender: str, mentioned: list[str]) -> dict[str, list[str]]:
	"""Who is told of a message, by notification: whoever it mentions in the
	conversation, and in a direct conversation the other person. Never the
	sender, never anybody outside it, never twice. Pure."""
	inside = [one for one in members if one and one != sender]
	named = [one for one in dict.fromkeys(mentioned) if one in inside]
	direct = [one for one in inside if one not in named] if kind == channels.DIRECT else []
	return {MENTIONED: named, DIRECT: direct}


def notify(doc, channel, mentioned: list[str]) -> None:
	from onedesk.one import notify as hub

	who = frappe.utils.get_fullname(doc.sender)
	said = short(doc.text) or _("Sent a file.")
	link = f"/app/onechat?channel={channel.name}" + (f"&thread={doc.thread or doc.name}" if doc.thread or channel.kind == channels.CHANNEL else "")
	for kind, users in told(channel.kind, channels.members_of(channel.name), doc.sender, mentioned).items():
		if users:
			hub.notify(kind, users, link=link, sender=doc.sender, who=who, conversation=channel.title, text=said)


def short(text: str | None) -> str:
	said = " ".join((text or "").split())
	return said if len(said) <= SHOWN else said[: SHOWN - 1] + "…"


def mentions_in(text: str, channel) -> tuple[list[str], list[str]]:
	"""The people in the conversation and the agents a message names after @."""
	people = {one.user: frappe.utils.get_fullname(one.user) for one in channel.members if one.user and not one.agent}
	reachable = {one["agent"]: one["handle"] for one in agents.listed()}
	return agents.mentioned(text, people), agents.mentioned(text, reachable)


def react(message: str, emoji: str) -> dict:
	doc = frappe.get_doc("Chat Message", message)
	channels.opened(doc.channel)
	emoji = (emoji or "").strip()[:REACTIONS]
	if not emoji:
		frappe.throw(_("Choose a reaction."))
	held = reacted(reactions_of(doc.reactions), emoji, frappe.session.user)
	doc.db_set("reactions", json.dumps(held), update_modified=False)
	doc.reactions = json.dumps(held)
	live(doc, CHANGED)
	return reactions_of(doc.reactions)
