"""OneAI's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, _lt

APP = App(
	id="one_ai",
	name="OneAI",
	kind="app",
	module="One AI",
	line=_lt("Ask about anything in the workspace, and have drafts, summaries and answers written for you."),
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
	),
)
