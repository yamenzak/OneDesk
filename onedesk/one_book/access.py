"""Who may do what in OneBook, where ERPNext's defaults do not fit.

A role that reads one already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`).
"""

from onedesk.one import roles

USER, MANAGER = "Accounts User", "Accounts Manager"

GIVEN = {
	"Accounting Dimension": {USER: ("read",)},
	"Bank": {USER: roles.USE, MANAGER: (*roles.USE, "write", "create")},
	"Bank Reconciliation Tool": {USER: ("read", "write"), MANAGER: ("read", "write")},
	"Bank Statement Import": {USER: roles.WORK, MANAGER: roles.MANAGE},
	"Opening Invoice Creation Tool": {MANAGER: ("read", "write")},
	"Purchase Taxes and Charges Template": {USER: roles.USE, MANAGER: roles.MANAGE},
	"Gratuity": {USER: roles.USE, MANAGER: roles.USE},
	"Pegged Currencies": {MANAGER: ("read", "write")},
	"Repost Accounting Ledger": {MANAGER: roles.MANAGE},
	"Loyalty Program": {USER: roles.USE, MANAGER: roles.MANAGE},
	"Tax Withholding Group": {USER: roles.USE, MANAGER: roles.MANAGE},
	"Import Supplier Invoice": {USER: roles.WORK, MANAGER: roles.MANAGE},
	"Email Digest": {MANAGER: roles.MANAGE},
	"Plaid Settings": {MANAGER: ("read", "write")},
	"Code List": {USER: roles.USE, MANAGER: roles.MANAGE},
	"Common Code": {USER: roles.USE, MANAGER: roles.MANAGE},
}


RAISED = {"Supplier": {MANAGER: ("read", "write", "create")}}


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
