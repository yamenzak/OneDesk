"""Who may do what in OneInventory, where ERPNext's defaults do not fit.

A role that reads one already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`).
"""

from onedesk.one import roles

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

QUALITY = (
	"Quality Goal",
	"Quality Procedure",
	"Quality Review",
	"Quality Action",
	"Non Conformance",
	"Quality Meeting",
	"Quality Feedback",
)

GIVEN = (
	{doctype: {STOCK_USER: roles.USE, STOCK_MANAGER: roles.MANAGE} for doctype in REGISTER}
	| {doctype: {STOCK_USER: roles.WORK, STOCK_MANAGER: roles.MANAGE} for doctype in QUALITY}
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
GIVEN["Quality Feedback Template"] = {STOCK_USER: roles.USE, STOCK_MANAGER: roles.MANAGE}
GIVEN["UOM Conversion Factor"] = {STOCK_USER: roles.USE, STOCK_MANAGER: roles.MANAGE, "Item Manager": roles.MANAGE}
GIVEN["Delivery Settings"] = {"Stock Manager": ("read", "write")}
GIVEN["Shipment Parcel Template"] = {"Stock User": roles.USE, "Stock Manager": roles.MANAGE}
GIVEN["Driver"] = {STOCK_USER: ("read",)}

for doctype in ("Asset", "Asset Movement"):
	GIVEN.setdefault(doctype, {}).update({"HR User": ("read",), "HR Manager": ("read",)})


RAISED = {"Supplier": {"Purchase User": ("read", "write", "create"), "Purchase Manager": roles.MANAGE}}


def settle() -> None:
	roles.give(GIVEN)
	roles.open_report("Review", STOCK_USER, STOCK_MANAGER)
	roles.raise_once(RAISED)
