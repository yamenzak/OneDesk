"""The side panel (public/js/one_ai/panel), as a conversation with an agent:
Una, or the agent of the app the reader is in. Each of the panel's
conversations is an Agent conversation of OneChat, kept as Chat Messages
like any other, and opens in OneChat too; the agent answers through
answers.py, and what it looked up and suggested rides on its message
(`parts`), drawn by the panel as it always was."""

import frappe
from frappe import _

from onedesk.one_chat import agents, api, channels, messages


@frappe.whitelist(methods=["GET"])
def conversations(limit: int = 20) -> list[dict]:
	"""The reader's conversations with agents, most recent first."""
	rows = frappe.get_all(
		"Chat Channel",
		filters={"kind": channels.AGENT, "owner": frappe.session.user},
		fields=["name", "title", "agent", "ai_chat", "last_message_on"],
		order_by="last_message_on desc",
		limit_page_length=int(limit),
	)
	titles = _titles([one.ai_chat for one in rows if one.ai_chat])
	return [
		{
			"name": one.name,
			"title": titles.get(one.ai_chat) or one.title,
			"agent": one.agent,
			"agent_name": agents.name_of(one.agent),
			"last_said_on": str(one.last_message_on) if one.last_message_on else None,
		}
		for one in rows
	]


def _titles(chats: list[str]) -> dict[str, str]:
	if not chats:
		return {}
	return dict(frappe.get_all("AI Chat", filters={"name": ["in", chats]}, fields=["name", "title"], as_list=True))


@frappe.whitelist(methods=["GET"])
def agent_for(page=None) -> dict:
	"""Who a new conversation on this page is with."""
	return agents.shown(agents.for_page(page))


@frappe.whitelist(methods=["GET"])
def opened(channel: str) -> dict:
	"""One conversation as the panel draws it."""
	doc = channels.opened(channel)
	if doc.kind != channels.AGENT:
		frappe.throw(_("This conversation isn't with an agent."))
	names = frappe.get_all("Chat Message", filters={"channel": doc.name, "thread": ("is", "not set")}, pluck="name", order_by="creation asc", limit_page_length=0)
	said = [_said(frappe.get_doc("Chat Message", name)) for name in names]
	running = None
	if doc.ai_chat:
		running = frappe.cache.get_value(f"one_ai_busy:{doc.ai_chat}")
	return {
		"name": doc.name,
		"title": (_titles([doc.ai_chat]).get(doc.ai_chat) if doc.ai_chat else None) or doc.title,
		"agent": agents.shown(doc.agent),
		"ai_chat": doc.ai_chat,
		"said": said,
		"spent": frappe.db.get_value("AI Chat", doc.ai_chat, "spent") or 0.0 if doc.ai_chat else 0.0,
		"running": running,
	}


def _said(message) -> dict:
	"""A message in the shape the panel draws a turn in. Pure but for the
	files' lookup."""
	parts = messages.shaped(message)["parts"] or {}
	return {
		"name": message.name,
		"role": "model" if message.agent else "you",
		"text": message.text or "",
		"files": [{"name": one["file_name"], "url": one["file_url"]} for one in messages.files_of(message)] + list(parts.get("files") or []),
		"looked": parts.get("looked") or [],
		"remembered": parts.get("remembered") or [],
		"cards": parts.get("cards") or [],
		"action": message.action,
	}


@frappe.whitelist(methods=["POST"])
def start(agent: str | None = None, page=None, title: str = "") -> dict:
	"""A new conversation with an agent, made when the first thing is said
	or a file is added."""
	doc = channels.with_agent(agent or agents.for_page(page), title=title or _("New conversation"))
	return {"name": doc.name, "title": doc.title, "agent": agents.shown(doc.agent), "said": [], "spent": 0.0}


@frappe.whitelist(methods=["POST"])
def say(text: str, channel: str | None = None, agent: str | None = None, page=None, files=None, field=None) -> dict:
	"""Say one thing to the agent, and start its answer."""
	if not channel:
		channel = start(agent, page, title=(text or "").strip()[: channels.TITLE])["name"]
	sent = api.send(channel, text, files=files, page=page, field=field)
	return {**opened(channel), "run": sent["run"]}


@frappe.whitelist(methods=["POST"])
def rename(channel: str, title: str) -> dict:
	doc = channels.opened(channel)
	title = (title or "").strip()[: channels.TITLE] or doc.title
	doc.db_set("title", title, update_modified=False)
	if doc.ai_chat:
		from onedesk.one_ai import chat

		chat.rename(doc.ai_chat, title)
	return {"name": doc.name, "title": title}


@frappe.whitelist(methods=["GET"])
def actions(names) -> list[dict]:
	"""The door's cards a conversation holds, as they stand now."""
	from onedesk.one_chat import cards

	names = frappe.parse_json(names) if isinstance(names, str) else (names or [])
	shown = []
	for name in names[:20]:
		cards.reach(name)
		shown.append(cards.card(name))
	return shown
