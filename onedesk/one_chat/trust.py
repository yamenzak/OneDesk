"""What OneChat adds to the agreements: the messages people write to each
other and to the agents, kept in the workspace and read by a conversation's
members alone (channels.py), and what goes to OneAI when an agent is asked
(answers.py). See trust_center/AGENTS.md."""

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
		The agent's answer is kept as a message in the conversation. Messages that ask no agent are never sent.
	""",
)
