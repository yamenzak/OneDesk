"""What OneChat adds to the agreements: the messages people write to each
other and to the agents, kept in the workspace and read by a conversation's
members alone (channels.py), and what goes to OneAI when an agent is asked
(answers.py), what a website visitor writes in a chat (widget.py), and
what an agent an automation lets answer is sent (automations.py). See
trust_center/AGENTS.md."""

from onedesk.one import registry
from onedesk.trust_center.registry import clause

M = registry.name("one_chat")

clause(
	document="privacy",
	section="modules",
	key="chat-messages",
	module=M,
	body=f"""
		{M} keeps in your workspace the messages people write, the files they add to them and their reactions.
		A conversation is read only by its members, the people in it and the agents asked into it. A workspace
		administrator cannot read a conversation they are not a member of. A channel that is not private can be
		found and joined by anybody in the workspace. A person mentioned, or sent a direct message, is told by a
		notification, and by email or push if they chose it.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onechat-agents",
	module=M,
	body=f"""
		In {M}, a message to an agent, or one that mentions an agent, is a question to {registry.name("one_ai")}.
		It is sent with that person's earlier questions and answers there, and answered as any question is.
		The agent's answer is kept as a message in the conversation. A message that asks no agent is sent only where a
		channel's automation lets an agent answer it.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="chat-website",
	module=M,
	body=f"""
		If your organisation has a channel answer website chats, a visitor to its website can write to it from a
		chat on each page. {M} keeps in your workspace the visitor's name, email address, the page they wrote from
		and their messages, as a conversation of your organisation's. The people of that channel read it.
		The visitor's browser keeps a random key that opens only that conversation, and only a fingerprint of the
		key is kept. With it the visitor reads the replies in that conversation, never its threads, a card or
		anything else in the workspace. Starting a chat and writing in one are limited for each network address.
		Your organisation is responsible for what it does with what visitors write.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onechat-automations",
	module=M,
	body=f"""
		A channel's automation in {M} can let an agent answer messages, a website visitor's too. The agent is sent
		the automation's instructions and the words of that conversation, and nothing else. It looks up no record
		to answer. Its answer is kept as a message in the conversation, where a visitor reads it.
	""",
)
