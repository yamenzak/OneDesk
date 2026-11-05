"""What OneInventory lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on Stock
Settings, declared in permission_type/ beside this file. A workspace
administrator may do it without."""

from frappe import _lt

APP = "OneInventory"

# Not everybody's: People gives it to whoever uses OneInventory.
USER = "Stock User"

DOCTYPE = "Stock Settings"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "fix",
		"group": WORKSPACE,
		"label": _lt("Fix What the Check Finds"),
		"kind": "switch",
		"all": "inventory_fix",
		"about": _lt("Make the changes Inventory Check offers, such as turning on batches or naming the home warehouse."),
	},
]

# Nothing of OneInventory's is given on one record.
SHARED = ()

# ERPNext's own roles and what each starts with, written once on migrate
# (rights.settle); the books' manager could fix the check before, and still does.
DEFAULTS = {
	"Stock User": {},
	"Stock Manager": {"fix": 1},
	"Accounts Manager": {"fix": 1},
}
