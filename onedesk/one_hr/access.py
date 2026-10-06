"""Who may do what in OneHR, where HRMS's defaults do not fit."""

from onedesk.one import roles

USER, MANAGER = "HR User", "HR Manager"

GIVEN = {
	doctype: {USER: roles.WORK, MANAGER: roles.MANAGE}
	for doctype in ("Travel Request", "Employee Advance", "Vehicle Log")
} | {"Purpose of Travel": {USER: roles.USE, MANAGER: roles.MANAGE}}


def settle() -> None:
	roles.give(GIVEN)
