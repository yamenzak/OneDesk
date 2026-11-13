"""What OneSheet adds to the agreements: what OneAI is sent when it is
asked about the workbook that is open. A workbook is a file in OneCloud, so
what OneCloud's agreements say of a file holds for it. See
one_sheet/AGENTS.md and one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause

M = "OneSheet"

clause(
	document="ai",
	section="modules",
	key="onesheet-asks",
	module=M,
	body="""
		In OneSheet, OneAI can answer about the workbook you have open. It is sent the workbook's name, the
		names of its sheets, and the cells you selected with what they hold. For a workbook on a record's
		table, it is also sent which record and which table. It reads other cells, or another workbook, only
		to answer you, and only one you may open. A workbook it makes, and the cells, formats and notes it
		writes, are cards, and nothing changes until you approve them.
	""",
)
