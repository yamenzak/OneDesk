"""What OneChat tells people, read by onedesk/notifications/__init__.py
beside the other modules' files (docs/READY.md, mechanism 8): a mention, a
direct message, and what a channel's automation says to tell. A message in a channel that mentions nobody tells nobody;
it is marked unread in the conversation's list instead. Pure."""

from onedesk.one import registry

ALL = {"bell": True, "email": True, "push": True}

TYPES = [
	{
		"name": "Mention in a Conversation",
		"app": registry.name("one_chat"),
		"about": "When somebody mentions you in a channel or a thread.",
		"to": "Each person mentioned who is in the conversation, but the sender",
		"channels": ALL,
		"push_default": True,
		"sender": "workspace",
		"subject": "{who} mentioned you in {conversation}",
		"message": "{text}",
	},
	{
		"name": "Direct Message",
		"app": registry.name("one_chat"),
		"about": "When somebody sends you a direct message.",
		"to": "The other person in the conversation",
		"channels": ALL,
		"push_default": True,
		"sender": "workspace",
		"subject": "{who} sent you a message",
		"message": "{text}",
	},
	{
		"name": "Chat Automation Notice",
		"app": registry.name("one_chat"),
		"about": "When a channel's automation says to tell you that a message it watches for was posted.",
		"to": "Whoever the automation names, while they are in the channel",
		"channels": ALL,
		"button": "Open Conversation",
		"email_default": False,
		"push_default": True,
		"sender": "workspace",
		"subject": "{who} wrote in {conversation}",
		"message": "{text}<br>The automation {automation} told you.",
	},
]
