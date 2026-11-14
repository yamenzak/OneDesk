"""OneChat's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, _lt

APP = App(
	id="one_chat",
	name="OneChat",
	kind="app",
	module="One Chat",
	ui="bespoke",
	regions=(
		Region("page", "onechat", "channels, direct messages and the agents (Chat Channel, Chat Message)"),
	),
	line=_lt("Talk to your team and to the agents, in channels, direct messages and threads."),
	pitch=_lt("{one_chat} is where the team talks, in channels by department or project and in direct messages. Each app's agent is there too, to be asked and to report what it did. A conversation is read only by the people in it."),
	brings=(
		_lt("Channels and direct messages"),
		_lt("Threads, mentions and reactions"),
		_lt("The agents of your apps"),
		_lt("Files from {one_cloud} or your computer"),
	),
	media=("conversation.webp", "agents.webp", "new-channel.webp"),
	credits=("ai",),
	mark="onechat",
	rail=35,
	sidebar="OneChat",
	screens="chat",
	names=("one_chat", "onechat"),
	help=(
		("overview", "info"),
		("channels", "hash"),
		("messages", "message-circle"),
		("agents", "bot"),
		("website-chats", "globe"),
		("who-can-do-what", "shield"),
	),
	hooks={
		"one_ai_waiting": ("cards.waiting",),
	},
	makes=(
		"Issue",
		"Lead",
		"Task",
	),
)
