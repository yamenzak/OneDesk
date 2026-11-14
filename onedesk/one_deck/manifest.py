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
	pitch=_lt("{one_deck} makes presentations, such as a tender pitch or a monthly review. Slides are made together, from a template, at any size. A presentation is shown by link and sent as PowerPoint or PDF."),
	brings=(
		_lt("Templates and slides of any size"),
		_lt("Presenting by link"),
		_lt("PowerPoint and PDF"),
		_lt("The history of every change"),
	),
	media=("presentation.webp", "go-through-the-slides.gif", "file-menu.webp"),
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
