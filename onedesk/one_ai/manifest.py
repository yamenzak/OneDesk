"""OneAI's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Centre, Settle, _lt

APP = App(
	id="one_ai",
	name="OneAI",
	kind="app",
	module="One AI",
	ui="native",
	line=_lt("Ask about anything in the workspace, and have drafts, summaries and answers written for you."),
	pitch=_lt("{one_ai} is the assistant in every part of {one}. Ask it about your work in your own words and language, and it answers from your records and {one}'s guides. It suggests a change on a card, and nothing changes until you approve it."),
	brings=(
		_lt("Answers from your own records"),
		_lt("Drafts and summaries"),
		_lt("Mail and files read and filed"),
		_lt("Web search"),
	),
	media=("documents.webp", "read-a-receipt.gif", "suggestion.webp", "agents.webp"),
	credits=("ai",),
	mark="oneai",
	rail=150,
	sidebar="OneAI",
	screens="intake",
	names=("one_ai", "oneai"),
	help=(
		("overview", "info"),
		("asking-oneai", "sparkles"),
		("cards", "check-check"),
		("writing", "pencil"),
		("summaries", "notebook-text"),
		("reading", "inbox"),
		("finding", "search"),
		("remembers", "brain"),
		("web-search", "globe"),
		("tiers-and-credits", "coins"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": True,
	},
	parts=("reading",),
	hooks={
		"one_record_notices": ("heads.NOTICES",),
	},
	settle=(
		Settle("reading.search.index"),
		Settle("agents.users.ensure"),
	),
)

PARTS = (
	App(id="ai_center", line=_lt("The agents, what they may do and what they did."), name="AICenter", kind="centre", module="", mark="aicenter", centre=Centre("ai", "aicenter")),
)
