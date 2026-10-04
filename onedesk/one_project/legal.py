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
		its figures, its tasks, its people and the team's updates, with those of its sub-projects you may
		see. A task it suggests for a project is added only when you approve it.
	""",
)
