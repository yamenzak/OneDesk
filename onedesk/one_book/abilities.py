"""What OneBook lets a role do beyond its records (one/rights.py,
docs/ROLES.md): each ability is one of frappe's Permission Types on Accounts
Settings, declared in permission_type/ beside this file. A workspace
administrator may do them without."""

from frappe import _lt

APP = "OneBook"

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
