"""Who may do what in OneFactory: its one ability, a Permission Type on
Manufacturing Settings (one/rights.py, docs/ROLES.md), and the grants where
ERPNext's defaults do not fit. A role that reads one already keeps what it
has (one/roles.py `give`); a workspace administrator may do the ability.
"""

from frappe import _lt

from onedesk.one import roles

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


GIVEN = {
	"Subcontracting BOM": {
		"Purchase User": roles.USE,
		"Manufacturing User": roles.USE,
		"Purchase Manager": roles.MANAGE,
		"Manufacturing Manager": roles.MANAGE,
	},
	"Subcontracting Order": {
		"Manufacturing User": roles.USE,
		"Manufacturing Manager": roles.USE,
	},
	"Subcontracting Receipt": {
		"Manufacturing User": roles.USE,
		"Manufacturing Manager": roles.USE,
	},
	"Plant Floor": {
		"Manufacturing User": roles.USE,
		"Manufacturing Manager": roles.MANAGE,
	},
}


def settle() -> None:
	roles.give(GIVEN)
