"""What OneProject adds to the agreements: OneAI reads a project when somebody
asks about it, as they see it, and a task it suggests is added only when they
approve it. See one_project/agent.py and trust_center/AGENTS.md."""

from onedesk.trust_center.registry import clause

M = "OneProject"

clause(
	document="ai",
	section="modules",
	key="oneproject-asks",
	module=M,
	body="""
		In OneProject, when you ask OneAI about a project, it reads the project as you see it on its page.
		That is its figures and tasks, and its money with the customer and with suppliers: orders, invoices,
		payments, retention and budgets. It also reads the time each person logged on it, its people, the outside
		contacts named on it with their role, email and phone, and the team's updates. It reads the same of
		the sub-projects you may see. Asked who has too much on, it reads the week as Workload shows it to
		you. A task, a milestone, time on your own timesheet or a cost type's budget it suggests is added only
		when you approve it. So is a reminder to a customer, a member, a contact, a new project or a change to
		a project's status.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="oneproject-workload",
	module=M,
	body="""
		Workload shows, to whoever works in OneProject, each person on a project's team with their hours
		for a week, the open work planned for them and their hours free. A holiday or a day of approved
		leave takes the day out of their hours. It shows the hours, never why they are fewer.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="oneproject-contacts",
	module=M,
	body="""
		A project can name people outside the company who work on it, such as the customer's
		representative, a consultant or a subcontractor. It keeps their role and a note, and shows their
		email and phone from the Address Book to whoever may read the project. Taking them off the project
		removes them from it. Their contact stays in the Address Book.
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
		Some projects count time by attendance on site. On such a project, a day you checked in at its site,
		or whose shift named it, is written as a timesheet on it: the day and the hours, nothing about where
		else you were. It is seen by whoever may read the project's
		time, and costs or bills the day as any timesheet does.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="oneproject-time",
	module=M,
	body="""
		A project's Time view shows, to whoever may read the project, the hours each person logged on it:
		the day, the activity, the task and whether it is billed. What those hours cost and bill, and so
		what each person's time comes to, is shown only to those who may see timesheet rates.
	""",
)
