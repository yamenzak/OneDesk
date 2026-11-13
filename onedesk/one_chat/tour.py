"""OneChat's tour (one/tours.py, docs/READY.md mechanism 10), of its one
screen; each step points at a `data-tour` mark in frontend/src/chat."""

from frappe import _lt

CHAT = [
	{
		"target": "onechat-list",
		"side": "right",
		"title": _lt("Conversations"),
		"text": _lt("Channels, direct messages and your conversations with agents, with what you have not read in bold."),
	},
	{
		"target": "onechat-agents",
		"side": "right",
		"title": _lt("Agents", context="AI"),
		"text": _lt("Una and the agent of each app you use, ready to answer."),
	},
]

TOURS = [{"key": "chat", "at": "onechat", "steps": CHAT}]
