"""Who may do what in OneProject, where ERPNext's defaults do not fit."""

from onedesk.one import roles

GIVEN = {
	"Projects Settings": {"Projects Manager": ("read", "write")},
	"Budget": {"Projects Manager": (*roles.WORK, "cancel", "amend")},
	"Project": {"Accounts User": roles.USE, "Accounts Manager": roles.USE},
}


def settle() -> None:
	roles.give(GIVEN)
