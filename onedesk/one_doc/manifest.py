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
	pitch=_lt("{one_doc} writes the company's documents, such as a scope of works, a letter or the minutes of a meeting. People write in the same document at once and comment in the margin. Each document is a file in {one_cloud}, sent as Word or PDF."),
	brings=(
		_lt("Writing together, with comments in the margin"),
		_lt("Templates and the history of every change"),
		_lt("Word and PDF, printed or sent"),
		_lt("A document kept on its record"),
	),
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
