"""The website's chat (public/js/one_chat/widget.js): a visitor's room, read
with a key only their browser holds, every call limited per network address.
AGENTS.md, Rooms and the website, says what a visitor reads and why."""

import re

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, now_datetime, sha256_hash

from onedesk.one_chat import automations, channels, messages

AN_HOUR = 60 * 60
A_DAY = 24 * AN_HOUR
OPENS_AN_HOUR = 5
"""Chats one network address may start in an hour."""
OPENS_A_DAY = 20
SAYS_AN_HOUR = 60
"""Messages one network address may send in an hour."""
READS_AN_HOUR = 1200
"""How often one network address may look for new messages in an hour: every
three seconds while a chat is open."""
MOST_SAID = 2000
MOST_NAME = 80
SHOWN = 50
OPENED = "Website Chat"
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+$")


def key_of(token: str) -> str:
	"""What is kept of a visitor's key. Pure."""
	return sha256_hash(token or "")


def checked(name: str, email: str, text: str) -> tuple[str, str, str]:
	"""A visitor's name, address and first message, trimmed, or a refusal
	that says what to change. Pure but for the words."""
	name, email, text = (name or "").strip()[:MOST_NAME], (email or "").strip().lower(), (text or "").strip()
	if not name:
		frappe.throw(_("{0} is required.").format(_("Name")))
	if not EMAIL.match(email):
		frappe.throw(_("Enter a valid email address."))
	if not text:
		frappe.throw(_("Write a message."))
	return name, email, text[:MOST_SAID]


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=READS_AN_HOUR, seconds=AN_HOUR, endpoint="onedesk.one_chat.widget.offered")
def offered() -> dict:
	"""Whether the website has a chat, and its heading and line: the
	website's name and the answering channel's description."""
	desk = channels.website()
	if not desk or not _open():
		return {"on": 0}
	about = frappe.db.get_value("Chat Channel", desk, "about") or ""
	return {"on": 1, "title": _title(), "about": about}


def _open() -> bool:
	"""Whether OneChat is on in the workspace."""
	from onedesk.one import apps, registry

	return registry.get("one_chat").sidebar not in apps.hidden()


def _title() -> str:
	"""The workspace's name, as Branding sets it."""
	return frappe.db.get_single_value("System Settings", "app_name") or ""


def _room_of(token: str):
	"""The visitor's room, or a refusal that says nothing of any other."""
	name = frappe.db.get_value("Chat Channel", {"visitor_key": key_of(token), "kind": channels.ROOM}, "name") if token else None
	if not name:
		frappe.throw(_("This chat has ended."), frappe.DoesNotExistError)
	return frappe.get_doc("Chat Channel", name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=OPENS_AN_HOUR, seconds=AN_HOUR, endpoint="onedesk.one_chat.widget.start:hour")
@rate_limit(limit=OPENS_A_DAY, seconds=A_DAY, endpoint="onedesk.one_chat.widget.start:day")
def start(name: str, email: str, text: str, page: str | None = None) -> dict:
	"""A visitor starts a chat: a room for the channel that answers the
	website, their first message in it, and its people told. Answers the key
	the visitor's browser keeps, which nothing here can give back."""
	desk = channels.website()
	if not desk or not _open():
		frappe.throw(_("Chat isn't available right now."))
	name, email, text = checked(name, email, text)
	token = frappe.generate_hash(length=32)
	room = channels.room(desk, name, email, key_of(token), (page or "")[:140])
	message = _said(room, text)
	_opened(room, message)
	return {"token": token}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=SAYS_AN_HOUR, seconds=AN_HOUR, endpoint="onedesk.one_chat.widget.send")
def send(token: str, text: str) -> dict:
	"""A visitor's next message in their room, while it is open."""
	room = _room_of(token)
	if room.closed:
		frappe.throw(_("This chat has ended."))
	text = (text or "").strip()[:MOST_SAID]
	if not text:
		frappe.throw(_("Write a message."))
	return {"message": shown(messages.shaped(_said(room, text)), room)}


def _said(room, text: str):
	"""A visitor's message, posted as nobody but the room's visitor, and the
	channel's automations started on it."""
	message = messages.post(room, text, sender=channels.VISITOR)
	automations.fire(message, room)
	return message


def _opened(room, message) -> None:
	"""The room's people told that a visitor started a chat."""
	from onedesk.one import notify as hub

	people = [one.user for one in room.members if one.user]
	if people:
		hub.notify(
			OPENED,
			people,
			link=f"/app/onechat?channel={room.name}",
			sender="Administrator",
			who=room.visitor_name,
			text=messages.short(message.text),
		)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=READS_AN_HOUR, seconds=AN_HOUR, endpoint="onedesk.one_chat.widget.said")
def said(token: str, after: str | None = None) -> dict:
	"""What the visitor reads of their room since `after`, oldest first."""
	room = _room_of(token)
	filters = {"channel": room.name, "thread": ("is", "not set"), "action": ("is", "not set")}
	if after:
		filters["creation"] = [">", after]
	rows = frappe.get_all(
		"Chat Message",
		filters=filters,
		fields=["name", "sender", "agent", "text", "creation"],
		order_by="creation desc",
		limit=SHOWN,
	)
	return {"messages": [shown(one, room) for one in reversed(rows)], "closed": cint(room.closed), "now": str(now_datetime())}


def shown(one, room) -> dict:
	"""One message as the visitor reads it: its words, when, and who wrote
	it, themselves, an agent by its name or a person by their first name."""
	from onedesk.one_chat import agents

	mine = one.get("sender") == channels.VISITOR
	if mine:
		who = room.visitor_name
	elif one.get("agent"):
		who = agents.name_of(one["agent"])
	else:
		who = (frappe.utils.get_fullname(one.get("sender")) or "").split(" ")[0]
	return {"name": one.get("name"), "text": one.get("text") or "", "mine": int(mine), "who": who, "at": str(one.get("creation"))}
