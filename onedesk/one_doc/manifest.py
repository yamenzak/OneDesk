"""OneDoc's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, _lt

APP = App(
	id="one_doc",
	name="OneDoc",
	kind="app",
	module="One Doc",
	ui="bespoke",
	regions=(
		Region("page", "document", "a document from OneCloud, in OneDoc's editor (Writer Document)"),
	),
	line=_lt("Write documents together, from a template or a blank page, and send them as Word or PDF."),
	mark="onedoc",
	rail=22,
	sidebar="OneDoc",
	needs=("one_cloud",),
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
	windowless="Its rail row lists its documents in OneCloud's explorer and each opens in an editor that fills the window, so OneDoc's settings are OneCloud's.",
	ready={
		"ready": True,
	},
)
