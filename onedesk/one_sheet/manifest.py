"""OneSheet's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App

APP = App(
	id="one_sheet",
	name="OneSheet",
	kind="app",
	module="One Sheet",
	mark="onesheet",
	screens="sheet",
	names=("one_sheet", "onesheet"),
	help=(
		("overview", "info"),
		("working-in-a-workbook", "sheet"),
		("excel-and-csv", "file-spreadsheet"),
		("history-and-templates", "history"),
		("printing", "printer"),
		("a-records-table", "table"),
		("branded-sheets", "palette"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
	),
	windowless="A workbook opens from OneCloud in an editor that fills the window, so OneSheet's foot and settings are OneCloud's.",
	ready={
		"ready": True,
	},
)
