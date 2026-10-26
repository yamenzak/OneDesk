"""What OneTask adds to the agreements: OneAI reads a person's tasks when they
ask, and a task or a change it suggests is made only when they approve it. See
one_task/ai.py and one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause

M = "OneTask"

clause(
	document="ai",
	section="modules",
	key="onetask-asks",
	module=M,
	body="""
		In OneTask, when you ask OneAI about your work, it reads your tasks as you see them on My Tasks, and
		a task as you see it on its page: what it waits on, its checklist and sub-tasks, and the hours each
		person logged on it that you may see. A task it suggests, or the steps it suggests for one, are added
		only when you approve them, and a colleague it names is given the task then. A change it suggests to
		a task, such as marking it done or moving the day it is due, is made only when you approve it.
	""",
)
