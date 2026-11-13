"""OneDeck's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle

APP = App(
	id="one_deck",
	name="OneDeck",
	kind="app",
	module="One Deck",
	mark="onedeck",
	screens="slide",
	names=("one_deck", "onedeck"),
	help=(
		("overview", "info"),
		("working-on-slides", "presentation"),
		("design-and-layers", "layers"),
		("history-and-pdf", "history"),
		("presenting-by-link", "link"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
	),
	windowless="A presentation opens from OneCloud in an editor that fills the window, so OneDeck's foot and settings are OneCloud's.",
	ready={
		"ready": True,
	},
	settle=(
		Settle("setup.themes"),
		Settle("decks.sync"),
	),
)
