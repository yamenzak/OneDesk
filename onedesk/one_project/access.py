"""Who may do what in OneProject, where ERPNext's defaults do not fit.

ERPNext lets only a **System Manager** open **Projects Settings**, which the
rail links to: whether a timesheet may overlap another and whether a task's
dates are checked against its project's. A Projects Manager keeps them.

A role that reads it already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`). Tasks and project templates are
one_task/access.py and templates.py.
"""

from onedesk.one import roles

GIVEN = {"Projects Settings": {"Projects Manager": ("read", "write")}}


def settle() -> None:
	roles.give(GIVEN)
