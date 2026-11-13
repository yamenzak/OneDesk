"""OneSlide's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle

APP = App(
	id="one_slide",
	name="OneSlide",
	kind="app",
	module="One Slide",
	mark="oneslide",
	screens="slide",
	names=("one_slide", "oneslide"),
	help=(
		("overview", "info"),
		("working-on-slides", "presentation"),
		("design-and-layers", "layers"),
		("history-and-pdf", "history"),
		("presenting-by-link", "link"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
	),
	windowless="A presentation opens from OneCloud in an editor that fills the window, so OneSlide's foot and settings are OneCloud's.",
	ready={
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-12", "commit": "ec12a9996047", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-12", "commit": "ec12a9996047", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-12", "commit": "ec12a9996047", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-12", "commit": "ec12a9996047", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-12", "commit": "ec12a9996047", "by": "Claude, for Yamen"},
		},
	},
	settle=(
		Settle("setup.themes"),
		Settle("decks.sync"),
	),
)
