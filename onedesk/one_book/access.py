"""Who may do what in OneBook: its abilities, Permission Types on Accounts
Settings (one/rights.py, docs/ROLES.md), and the grants where ERPNext's
defaults do not fit. A role that reads one already keeps what it has
(one/roles.py `give`); a workspace administrator may do every ability.
"""

from frappe import _lt

from onedesk.one import registry, roles

APP = registry.name("one_book")

# Not everybody's: People gives it to whoever uses OneBook.
USER = "Accounts User"

DOCTYPE = "Accounts Settings"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "lock",
		"group": WORKSPACE,
		"label": _lt("Lock the Books"),
		"kind": "switch",
		"all": "books_lock",
		"about": _lt("Lock the accounts up to a day, so nothing on or before it can change."),
	},
	{
		"key": "fix",
		"group": WORKSPACE,
		"label": _lt("Fix What the Check Finds"),
		"kind": "switch",
		"all": "books_fix",
		"about": _lt("Make the changes Books Check offers, such as adding the next year or a bank account."),
	},
]

# Nothing of OneBook's is given on one record.
SHARED = ()

# ERPNext's own roles and what each starts with, written once on migrate
# (rights.settle).
DEFAULTS = {
	"Accounts User": {},
	"Accounts Manager": {"lock": 1, "fix": 1},
}


MANAGER = "Accounts Manager"

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
