"""A project's plan: what depends on what, and what moves when a date slips.

**A dependency says which project it is in.** ERPNext moves a task's dependants
later when its date slips (`reschedule_dependent_tasks`), and finds them by the
project on each Task Depends On row — a read-only field nothing in ERPNext ever
writes, so the slip never found anything. The row takes the task's project.
"""


def before_validate(doc, method=None) -> None:
	"""Task before_validate: each dependency row names the task's project."""
	for row in doc.get("depends_on") or []:
		if not row.project:
			row.project = doc.project
