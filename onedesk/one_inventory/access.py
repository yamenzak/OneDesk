"""Who may do what in OneInventory: its one ability, a Permission Type on
Stock Settings (one/rights.py, docs/ROLES.md), and the grants where
ERPNext's defaults do not fit. A role that reads one already keeps what it
has (one/roles.py `give`); a workspace administrator may do the ability.
"""

from frappe import _lt

from onedesk.one import roles

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


STOCK_USER, STOCK_MANAGER = "Stock User", "Stock Manager"

REGISTER = ("Asset", "Asset Category", "Asset Value Adjustment", "Asset Capitalization")

UPKEEP = (
	"Asset Maintenance",
	"Asset Maintenance Log",
	"Asset Maintenance Team",
	"Asset Repair",
	"Quality Inspection",
)

SCORING = (
	"Supplier Scorecard",
	"Supplier Scorecard Period",
	"Supplier Scorecard Criteria",
	"Supplier Scorecard Standing",
	"Supplier Scorecard Variable",
)


GIVEN = (
	{doctype: {STOCK_USER: roles.USE, STOCK_MANAGER: roles.MANAGE} for doctype in REGISTER}
	| {doctype: {STOCK_USER: roles.WORK, STOCK_MANAGER: roles.MANAGE} for doctype in UPKEEP}
	| {
		"Item Price": {
			STOCK_USER: roles.USE,
			"Purchase User": roles.USE,
			"Sales User": roles.USE,
			STOCK_MANAGER: roles.MANAGE,
			"Purchase Manager": roles.MANAGE,
			"Sales Manager": roles.MANAGE,
			"Item Manager": roles.MANAGE,
		},
		"Landed Cost Voucher": {STOCK_USER: roles.USE, "Accounts Manager": roles.WORK},
		"Stock Settings": {
			role: ("read",)
			for role in (STOCK_USER, "Purchase User", "Accounts User", "Projects User", "Manufacturing User")
		},
		"Blanket Order": {
			STOCK_USER: roles.USE,
			"Purchase User": roles.WORK,
			"Purchase Manager": roles.MANAGE,
			"Sales User": roles.WORK,
			"Sales Manager": roles.MANAGE,
		},
	}
	| {doctype: {"Purchase User": roles.USE, "Purchase Manager": roles.MANAGE} for doctype in SCORING}
)

GIVEN["Item Lead Time"] = {
	"Stock User": roles.WORK,
	"Purchase User": roles.WORK,
	"Manufacturing User": roles.WORK,
	"Stock Manager": roles.MANAGE,
	"Purchase Manager": roles.MANAGE,
	"Manufacturing Manager": roles.MANAGE,
}
GIVEN["UOM Conversion Factor"] = {STOCK_USER: roles.USE, STOCK_MANAGER: roles.MANAGE, "Item Manager": roles.MANAGE}
GIVEN["Delivery Settings"] = {"Stock Manager": ("read", "write")}
GIVEN["Shipment Parcel Template"] = {"Stock User": roles.USE, "Stock Manager": roles.MANAGE}
GIVEN["Driver"] = {STOCK_USER: ("read",)}

for doctype in ("Asset", "Asset Movement"):
	GIVEN.setdefault(doctype, {}).update({"HR User": ("read",), "HR Manager": ("read",)})


RAISED = {"Supplier": {"Purchase User": ("read", "write", "create"), "Purchase Manager": roles.MANAGE}}


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
