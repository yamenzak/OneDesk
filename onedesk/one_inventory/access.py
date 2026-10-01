"""Who may do what in OneInventory, where ERPNext's defaults do not fit.

ERPNext gives a company's assets to accounts, quality and manufacturing, and
its item prices to two master roles nobody in a small business holds. In One
assets and prices are OneInventory's (README), so its own roles have them:

- **Assets**, their categories, maintenance, repairs, value adjustments and
  capitalization: a Stock Manager runs them; a Stock User reads the register
  and does the upkeep (maintenance, its log and teams, repairs).
- **Item Prices**: whoever manages items, stock or buying keeps them; the
  people who use stock and buying read them.
- **Quality Inspections**: a Stock User records one, a Stock Manager runs them.

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


def settle() -> None:
	roles.give(GIVEN)
