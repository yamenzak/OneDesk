"""How an agent answers in a conversation, today: through OneAI's chat loop
as it stands (one_ai/chat.py say, then answer in the background), as the
person who asked, with no model call of OneChat's own. The loop keeps its
transcript in an AI Chat, one per person and conversation (or thread); the
person's message names it, and when the loop keeps its answer the
`one_ai_chat_kept` hook (kept, below) posts what the agent said into the
conversation, in the asker's thread. Una and an app's agent answer the same
way until P8.3 gives each agent its own tools (docs/ARC-AI.md)."""

import json

import frappe
from frappe import _

from onedesk.one_chat import agents, channels, messages


def transcript(channel: str, thread: str | None, user: str) -> str | None:
	"""The AI Chat this person's questions in a conversation or thread go on."""
	held = frappe.get_all(
		"Chat Message",
		filters={"channel": channel, "thread": thread or ("is", "not set"), "sender": user, "ai_chat": ("is", "set")},
		pluck="ai_chat",
		order_by="creation desc",
		limit=1,
	)
	if held:
		return held[0]
	if not thread:
		return frappe.db.get_value("Chat Channel", {"name": channel, "kind": channels.AGENT, "owner": user}, "ai_chat")
	return None


def ready(channel, thread: str | None) -> str | None:
	"""Refuses before anything is posted when the agent is still answering
	this person here; answers the transcript to go on."""
	from onedesk.one import apps, registry
	from onedesk.one_ai import chat

	if not apps.ai_on():
		frappe.throw(_("{0} is turned off for this workspace.").format(registry.name("one_ai")))
	held = transcript(channel.name, thread, frappe.session.user)
	if held and chat._running(held):
		frappe.throw(_("Still answering the last question."), title=_("Not yet"))
	return held


def ask(message, channel, agent: str, held: str | None, page=None, field=None) -> str:
	"""Start the agent's answer to a message; answers the run to follow."""
	from onedesk.one_ai import chat

	urls = [one["file_url"] for one in messages.files_of(message)]
	started = chat.say(message.text or "", chat=held, page=page, files=urls, field=field)
	message.db_set({"ai_chat": started["name"], "asks": agent}, update_modified=False)
	if channel.kind == channels.AGENT and not channel.ai_chat:
		frappe.db.set_value("Chat Channel", channel.name, "ai_chat", started["name"], update_modified=False)
	return started["run"]


def answered(turns: list[dict]) -> list[dict]:
	"""What the loop said since the person's last question, as the panel
	reads it (chat.shown). Pure but for shown's lookups."""
	from onedesk.one_ai import chat

	said = chat.shown(turns)
	last = max((at for at, one in enumerate(said) if one["role"] == "you"), default=-1)
	return [one for one in said[last + 1 :] if one["role"] == "model"]


def kept(doc, turns: list[dict]) -> None:
	"""one_ai_chat_kept: the agent's answer, posted where it was asked."""
	asked = frappe.get_all(
		"Chat Message",
		filters={"ai_chat": doc.name, "asks": ("is", "set")},
		fields=["name", "channel", "thread", "asks"],
		order_by="creation desc",
		limit=1,
	)
	if not asked:
		return
	asked = asked[0]
	channel = frappe.get_doc("Chat Channel", asked.channel)
	thread = asked.thread or (asked.name if channel.kind == channels.CHANNEL else None)
	for one in answered(turns):
		parts = {key: one.get(key) for key in ("looked", "remembered", "cards", "files") if one.get(key)}
		messages.post(
			channel,
			one.get("text") or "",
			thread=thread,
			sender=agents.user_of(asked.asks) or "",
			agent=asked.asks,
			ai_chat=doc.name,
			parts=json.dumps(parts, default=str) if parts else None,
		)
	if channel.kind == channels.AGENT and doc.title and doc.title != channel.title:
		frappe.db.set_value("Chat Channel", channel.name, "title", doc.title[: channels.TITLE], update_modified=False)
