"""Who may do what in OneBook, where ERPNext's defaults do not fit.

ERPNext lets only a **System Manager** open three of the tools the rail
links to, or add a bank, and keeps the purchase tax templates from accounts:

- **Bank** (Bank Reconciliation Tool) and **Bank Statement Import**: matching
  the bank's lines to payments is an accountant's daily work, so an Accounts
  User may do it and import a statement, and an Accounts Manager too.
- **Opening Invoices** (Opening Invoice Creation Tool): what customers and
  suppliers owed on the day the books start, entered once, by an Accounts
  Manager.
- **Banks**: the list of banks a bank account picks from. ERPNext lets only
  a System Manager add one, so One's own Add Bank stopped for everybody; an
  Accounts Manager adds one here and an Accounts User reads them.
- **Purchase Tax Templates**: ERPNext gives them to buying. The VAT a bill
  carries is the books' decision, so an Accounts Manager keeps them and an
  Accounts User reads them.

- **Suppliers**: a bill often comes from a new supplier, so an Accounts
  Manager adds one too (`RAISED`).

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
}


#: For a role that reads already: once, so a change in Access stands.
RAISED = {"Supplier": {MANAGER: ("read", "write", "create")}}


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
