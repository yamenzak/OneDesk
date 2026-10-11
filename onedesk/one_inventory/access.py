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

#: How a supplier is scored, and each month's score.
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
			STOCK_MANAGER: roles.MANAGE,
			"Purchase Manager": roles.MANAGE,
			"Item Manager": roles.MANAGE,
		},
		# Freight and duty come in on a forwarder's bill, which the accountant
		# keeps. ERPNext gives landed costs to the stock manager alone.
		"Landed Cost Voucher": {STOCK_USER: roles.USE, "Accounts Manager": roles.WORK},
		# Every order, receipt, delivery, movement and invoice form reads one
		# setting of it on opening, and ERPNext lets only the stock manager
		# and the sales user read it.
		"Stock Settings": {
			role: ("read",)
			for role in (STOCK_USER, "Purchase User", "Accounts User", "Projects User", "Manufacturing User")
		},
		# A price agreed with a supplier or a customer for a year. ERPNext
		# gives it to the System Manager alone, the operator's role.
		"Blanket Order": {
			STOCK_USER: roles.USE,
			"Purchase User": roles.WORK,
			"Purchase Manager": roles.MANAGE,
			"Sales User": roles.WORK,
			"Sales Manager": roles.MANAGE,
		},
	}
	# Scoring suppliers by delivery and quality, System Manager's alone in
	# ERPNext too. The buyer reads the scores and the buying manager sets
	# them up.
	| {doctype: {"Purchase User": roles.USE, "Purchase Manager": roles.MANAGE} for doctype in SCORING}
)


#: For roles that read already: once, so a change in Access stands.
RAISED = {"Supplier": {"Purchase User": ("read", "write", "create"), "Purchase Manager": roles.MANAGE}}


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
