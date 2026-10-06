"""Who may do what in OneInventory, where ERPNext's defaults do not fit.

A role that reads one already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`).
"""

from onedesk.one import roles

STOCK_USER, STOCK_MANAGER = "Stock User", "Stock Manager"

#: Seen by stock, run by its manager.
REGISTER = ("Asset", "Asset Category", "Asset Value Adjustment", "Asset Capitalization")

#: The upkeep, done by stock.
UPKEEP = (
	"Asset Maintenance",
	"Asset Maintenance Log",
	"Asset Maintenance Team",
	"Asset Repair",
	"Quality Inspection",
)

GIVEN = (
	{doctype: {STOCK_USER: roles.USE, STOCK_MANAGER: roles.MANAGE} for doctype in REGISTER}
	| {doctype: {STOCK_USER: roles.WORK, STOCK_MANAGER: roles.MANAGE} for doctype in UPKEEP}
	| {
		"Item Price": {
			STOCK_USER: roles.USE,
			"Purchase User": roles.USE,
			STOCK_MANAGER: roles.MANAGE,
			"Purchase Manager": roles.MANAGE,
			"Item Manager": roles.MANAGE,
		}
	}
)


#: For roles that read already: once, so a change in Access stands.
RAISED = {"Supplier": {"Purchase User": ("read", "write", "create"), "Purchase Manager": roles.MANAGE}}


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
