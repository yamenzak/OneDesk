"""OneAI's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, _lt

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
		"checked": {
			"copy": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
		},
	},
)
