"""OneDeck's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, Settle, _lt

APP = App(
	id="one_deck",
	name="OneDeck",
	kind="app",
	module="One Deck",
	ui="bespoke",
	regions=(
		Region("page", "presentation", "a presentation from OneCloud, in OneDeck's editor (Presentation)"),
	),
	line=_lt("Make presentations together, present them by link, and send them as PowerPoint or PDF."),
	mark="onedeck",
	rail=26,
	sidebar="OneDeck",
	needs=("one_cloud",),
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
	windowless="Its rail row lists its presentations in OneCloud's explorer and each opens in an editor that fills the window, so OneDeck's settings are OneCloud's.",
	ready={
		"ready": True,
	},
	settle=(
		Settle("setup.themes"),
		Settle("decks.sync"),
	),
)
