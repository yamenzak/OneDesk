"""OneCloud's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, Settle, _lt

APP = App(
	id="one_cloud",
	name="OneCloud",
	kind="app",
	module="One Cloud",
	ui="bespoke",
	regions=(
		Region("page", "onecloud", "the files (File)"),
	),
	line=_lt("Keep the company's files in one place and share them with anyone, inside or out."),
	pitch=_lt("{one_cloud} keeps the company's files in one place: your own, your team's, and every file attached to a record. It works like the file explorer on your computer. Files are shared with the team, or by link with anyone outside."),
	brings=(
		_lt("Your files, shared folders and every record's attachments"),
		_lt("Sharing with the team and by link"),
		_lt("Versions and activity on every file"),
		_lt("Files a browser can't open, edited in {oneos}"),
	),
	media=("company.webp", "open-a-folder.gif", "a-file.webp", "records.webp"),
	credits=("oneos", "office"),
	mark="onecloud",
	rail=20,
	sidebar="OneCloud",
	screens="cloud",
	names=("one_cloud", "onecloud"),
	help=(
		("overview", "info"),
		("using-the-explorer", "folder-open"),
		("opening-files", "file"),
		("editing-in-oneos", "monitor"),
		("files-on-records", "paperclip"),
		("sharing-with-the-team", "users"),
		("sharing-outside", "link"),
		("libraries", "library"),
		("versions-and-activity", "history"),
		("asking-for-files", "inbox"),
		("drive-on-your-computer", "hard-drive"),
		("servers-as-folders", "server"),
		("asking-oneai", "sparkles"),
		("storage", "database"),
		("who-can-do-what", "shield"),
	),
	no_roles="Who may open a file in OneCloud is who it is shared with, or who may open its record, so OneCloud ships no roles.",
	hooks={
		"one_record_tabs": ("namespace.TABS",),
	},
	settle=(
		Settle("store.unlimit"),
	),
)

PARTS = (
	App(id="oneos", name="OneOS", kind="engine", module=""),
)
