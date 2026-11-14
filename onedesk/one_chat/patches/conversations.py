"""Each conversation people had in OneAI's panel becomes a conversation
with Una in OneChat, which the panel now reads: its turns as messages, in
the order they were said, and the AI Chat kept as its transcript."""

import json

import frappe

from onedesk.one_chat import agents, channels


def execute():
	from onedesk.one_ai import drawn
	from onedesk.one_chat import transcript

	held = set(frappe.get_all("Chat Channel", filters={"ai_chat": ("is", "set")}, pluck="ai_chat"))
	for name in frappe.get_all("AI Chat", pluck="name", order_by="creation asc"):
		if name in held:
			continue
		doc = frappe.get_doc("AI Chat", name)
		if not frappe.db.get_value("User", doc.owner, "enabled"):
			continue
		frappe.set_user(doc.owner)
		try:
			channel = channels.make(doc.title or name, channels.AGENT, [], agent=agents.UNA)
			frappe.db.set_value("Chat Channel", channel.name, {"ai_chat": doc.name, "owner": doc.owner, "last_message_on": doc.last_said_on or doc.modified}, update_modified=False)
			for one in drawn.shown(transcript.turns_of(doc)):
				parts = {key: one.get(key) for key in ("looked", "remembered", "cards") if one.get(key)}
				message = frappe.get_doc(
					{
						"doctype": "Chat Message",
						"channel": channel.name,
						"sender": doc.owner if one["role"] == "you" else "",
						"agent": agents.UNA if one["role"] == "model" else "",
						"text": one.get("text") or "",
						"ai_chat": doc.name,
						"asks": agents.UNA if one["role"] == "you" else "",
						"parts": json.dumps(parts, default=str) if parts else None,
					}
				)
				message.insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
