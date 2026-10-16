"""Who may do what in OneHR, where HRMS's defaults do not fit."""

from onedesk.one import roles

USER, MANAGER = "HR User", "HR Manager"

GIVEN = {
	doctype: {USER: roles.WORK, MANAGER: roles.MANAGE}
	for doctype in ("Travel Request", "Employee Advance", "Vehicle Log")
} | {one: {USER: roles.USE, MANAGER: roles.MANAGE} for one in ("Purpose of Travel", "Vehicle Service Item")}

#: For a role that reads already: once, so a change in Access stands. HRMS
#: lets HR make an End of Service (Gratuity), a joining or a leaving checklist
#: and nobody submit it, and only submitting gives each step to its person.
RAISED = {
	doctype: {USER: roles.WORK, MANAGER: roles.MANAGE}
	for doctype in ("Gratuity", "Employee Onboarding", "Employee Separation")
}


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
