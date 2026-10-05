"""What OneProject adds to the agreements: OneAI reads a project when somebody
asks about it, as they see it, and a task it suggests is added only when they
approve it. See one_project/ai.py and one_legal/README.md."""

from onedesk.one_legal.registry import clause

M = "OneProject"

clause(
	document="ai",
	section="modules",
	key="oneproject-asks",
	module=M,
	body="""
		In OneProject, when you ask OneAI about a project, it reads the project as you see it on its page:
		its figures, its money with the customer and with suppliers (orders, invoices, payments, retention
		and budgets), its tasks, its people and the team's updates, with those of its sub-projects you may
		see. A task it suggests for a project is added only when you approve it.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="oneproject-featured",
	module=M,
	body="""
		Photos and videos put in a project's Featured Media folder in OneCloud are there to show the project:
		on its page, on its customer's portal and wherever your organisation chooses to show it. Anyone with
		the link to one of them can open it, so put nothing there that is not meant to be seen. Taken out of
		the folder, a file is the project's again and needs a sign-in to open.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="oneproject-days-on-site",
	module=M,
	body="""
		On a project whose time is counted by attendance on site, your attendance for a day you checked in at
		the project's site, or your shift that day named it, is written as a timesheet on that project: the
		day and the hours, nothing about where else you were. It is seen by whoever may read the project's
		time, and costs or bills the day as any timesheet does.
	""",
)
