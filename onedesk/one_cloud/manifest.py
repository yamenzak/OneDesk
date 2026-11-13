"""OneCloud's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, _lt

APP = App(
	id="one_cloud",
	name="OneCloud",
	kind="app",
	module="One Cloud",
	line=_lt("Keep the company's files in one place and share them with anyone, inside or out."),
	mark="onecloud",
	owns=("One Sheet", "One Doc"),
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
