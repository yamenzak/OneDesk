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
	pitch=_lt("{one_sheet} is the company's spreadsheet, with formulas, charts, pivot tables and notes. A workbook is kept in {one_cloud} and opened by anybody it is shared with. Excel and CSV files open in it and are saved from it."),
	brings=(
		_lt("Formulas, charts and pivot tables"),
		_lt("Excel and CSV in and out"),
		_lt("Templates and the history of every change"),
		_lt("A record's table as a sheet"),
	),
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
