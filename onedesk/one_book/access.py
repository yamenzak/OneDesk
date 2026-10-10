"""Who may do what in OneBook, where ERPNext's defaults do not fit.

A role that reads one already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`).
"""

from onedesk.one import roles

USER, MANAGER = "Accounts User", "Accounts Manager"

GIVEN = {
	"Bank": {USER: roles.USE, MANAGER: (*roles.USE, "write", "create")},
	"Bank Reconciliation Tool": {USER: ("read", "write"), MANAGER: ("read", "write")},
	"Bank Statement Import": {USER: roles.WORK, MANAGER: roles.MANAGE},
	"Opening Invoice Creation Tool": {MANAGER: ("read", "write")},
	"Purchase Taxes and Charges Template": {USER: roles.USE, MANAGER: roles.MANAGE},
	# The books pay a leaver's End of Service, which HRMS shows HR alone.
	"Gratuity": {USER: roles.USE, MANAGER: roles.USE},
}


#: For a role that reads already: once, so a change in Access stands.
RAISED = {"Supplier": {MANAGER: ("read", "write", "create")}}


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
