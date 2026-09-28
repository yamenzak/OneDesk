"""What OneTask adds to the agreements: OneAI reads a person's tasks when they
ask, and a task it suggests is added only when they approve it. See
one_task/ai.py and one_legal/README.md."""

from onedesk.one_legal.registry import clause

M = "OneTask"

clause(
	document="ai",
	section="modules",
	key="onetask-asks",
	module=M,
	body="""
		In OneTask, when you ask OneAI about your work, it reads your tasks as you see them on My Tasks. A
		task it suggests, or the steps it suggests for one, are added only when you approve them, and a
		colleague it names is given the task then.
	""",
)
