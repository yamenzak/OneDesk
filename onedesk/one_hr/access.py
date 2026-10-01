"""Who may do what in OneHR, where HRMS's defaults do not fit.

HRMS gives four of the Expenses group's kinds to roles nobody is given in
One: a **Travel Request** and its **Purpose of Travel** to the System Manager,
an **Employee Advance** to the employee and an Expense Approver, and a
**Vehicle Log** to a Fleet Manager. So the people officer the rail is for
could open none of them. An HR User now handles them, and an HR Manager runs
them; the purposes of travel are the HR Manager's list.

The employee's own requests are unchanged: HRMS's Employee and Employee Self
Service rules still decide what they see of their own. A role that reads one
already, by HRMS's rules or the workspace's, keeps what it has (one/roles.py
`give`).
"""

from onedesk.one import roles

USER, MANAGER = "HR User", "HR Manager"

GIVEN = {
	doctype: {USER: roles.WORK, MANAGER: roles.MANAGE}
	for doctype in ("Travel Request", "Employee Advance", "Vehicle Log")
} | {"Purpose of Travel": {USER: roles.USE, MANAGER: roles.MANAGE}}


def settle() -> None:
	roles.give(GIVEN)
