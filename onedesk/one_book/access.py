"""Who may do what in OneBook, where ERPNext's defaults do not fit.

ERPNext lets only a **System Manager** open three of the tools the rail
links to, and keeps the purchase tax templates from accounts:

- **Bank** (Bank Reconciliation Tool) and **Bank Statement Import**: matching
  the bank's lines to payments is an accountant's daily work, so an Accounts
  User may do it and import a statement, and an Accounts Manager too.
- **Opening Invoices** (Opening Invoice Creation Tool): what customers and
  suppliers owed on the day the books start, entered once, by an Accounts
  Manager.
- **Purchase Tax Templates**: ERPNext gives them to buying. The VAT a bill
  carries is the books' decision, so an Accounts Manager keeps them and an
  Accounts User reads them.

A role that reads one already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`).
"""

from onedesk.one import roles

USER, MANAGER = "Accounts User", "Accounts Manager"

GIVEN = {
	"Bank Reconciliation Tool": {USER: ("read", "write"), MANAGER: ("read", "write")},
	"Bank Statement Import": {USER: roles.WORK, MANAGER: roles.MANAGE},
	"Opening Invoice Creation Tool": {MANAGER: ("read", "write")},
	"Purchase Taxes and Charges Template": {USER: roles.USE, MANAGER: roles.MANAGE},
}


def settle() -> None:
	roles.give(GIVEN)
