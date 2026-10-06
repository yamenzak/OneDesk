"""Who may do what in OneProject, where ERPNext's defaults do not fit.

ERPNext lets only a **System Manager** open **Projects Settings**, which the
rail links to: whether a timesheet may overlap another and whether a task's
dates are checked against its project's. A Projects Manager keeps them.

ERPNext keeps **Budget** to the books, so a project manager could not set a
project's budget by cost type. A Projects Manager now keeps the budgets of
projects, and only those (budget.py `kept_to_projects`): a budget against a
cost centre stays the books'.

The books read every **Project**, since they invoice its time and progress
(members.py sees to which ones).

A role that reads it already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`). Tasks and project templates are
one_task/access.py and templates.py.
"""

from onedesk.one import roles

GIVEN = {
	"Projects Settings": {"Projects Manager": ("read", "write")},
	"Budget": {"Projects Manager": (*roles.WORK, "cancel", "amend")},
	"Project": {"Accounts User": roles.USE, "Accounts Manager": roles.USE},
}


def settle() -> None:
	roles.give(GIVEN)
