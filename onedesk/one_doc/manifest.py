"""OneDoc's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App

APP = App(
	id="one_doc",
	name="OneDoc",
	kind="app",
	module="One Doc",
	mark="onedoc",
	screens="doc",
	names=("one_doc", "onedoc"),
	help=(
		("overview", "info"),
		("writing", "pencil"),
		("writing-together", "users"),
		("history-and-templates", "history"),
		("printing-and-word", "printer"),
		("on-a-record", "link"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
	),
	windowless="A document opens from OneCloud in an editor that fills the window, so OneDoc's foot and settings are OneCloud's.",
	ready={
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-13", "commit": "a3569d8d8e65", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-13", "commit": "a3569d8d8e65", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-13", "commit": "a3569d8d8e65", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-13", "commit": "a3569d8d8e65", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-13", "commit": "a3569d8d8e65", "by": "Claude, for Yamen"},
		},
	},
)
