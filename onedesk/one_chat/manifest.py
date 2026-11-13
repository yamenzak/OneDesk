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
		("who-can-do-what", "shield"),
	),
	hooks={
		"one_ai_chat_kept": ("agent.kept",),
	},
)
