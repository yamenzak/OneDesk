"""OneSheet's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, _lt

APP = App(
	id="one_sheet",
	name="OneSheet",
	kind="app",
	module="One Sheet",
	ui="bespoke",
	regions=(
		Region("page", "workbook", "a workbook from OneCloud, in OneSheet's editor (Workbook)"),
	),
	line=_lt("Work on spreadsheets together, with formulas and charts, and send them as Excel."),
	mark="onesheet",
	rail=24,
	sidebar="OneSheet",
	needs=("one_cloud",),
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
	windowless="Its rail row lists its workbooks in OneCloud's explorer and each opens in an editor that fills the window, so OneSheet's settings are OneCloud's.",
	ready={
		"ready": True,
	},
)
