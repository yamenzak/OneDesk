"""What OneFactory lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on
Manufacturing Settings, declared in permission_type/ beside this file. A
workspace administrator may do it without."""

from frappe import _lt

APP = "OneFactory"

# Not everybody's: People gives it to whoever uses OneFactory.
USER = "Manufacturing User"

DOCTYPE = "Manufacturing Settings"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "costs",
		"group": WORKSPACE,
		"label": _lt("See What Making Costs"),
		"kind": "switch",
		"all": "factory_costs",
		"about": _lt("See a bill of materials' cost per unit and its Costing tab."),
	},
]

# Nothing of OneFactory's is given on one record.
SHARED = ()

# ERPNext's own roles and what each starts with, written once on migrate
# (rights.settle): the workshop runs the floor, its manager sees the cost.
DEFAULTS = {
	"Manufacturing User": {},
	"Manufacturing Manager": {"costs": 1},
}
