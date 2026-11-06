"""Review stamps in the bottom bar, on a dev site only (developer_mode or
one_dev): Island on a page an island still draws, and Passed on a screen
the final passthrough finished, with its day. A screen is named as frappe
routes to it (`Form/Customer`, `List/Customer`, `onemail`); it is added in
the commit that finishes its pass and taken out by a change that undoes it.
"""

import re

PASSED: dict[str, dict] = {
	"Form/Sales Invoice": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"List/Sales Invoice": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"Form/Purchase Invoice": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"List/Purchase Invoice": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"Form/Payment Entry": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"List/Payment Entry": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"Form/Journal Entry": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"List/Journal Entry": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"Form/Bank Transaction": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"List/Bank Transaction": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"Form/Bank Account": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"List/Bank Account": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"Form/Supplier": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"List/Supplier": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"books": {"on": "2026-11-06", "pass": "OneBook, closing"},
	"Form/Maintenance Schedule": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"List/Maintenance Schedule": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"Form/Warranty Claim": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"List/Warranty Claim": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"Form/Email Group": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"Form/Email Campaign": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"List/Email Campaign": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"Form/Appointment": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"List/Appointment": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"Form/Customer": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"List/Purchase Order": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"Form/Material Request": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	# "Form/Customer": {"on": "2026-11-02", "pass": "Final passthrough"},
	"Form/Stock Entry": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"List/Batch": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"Form/Batch": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"inventory": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"List/Item": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"List/Lead": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"Form/Lead": {"on": "2026-11-06", "pass": "OneCRM, November"},
	"List/Opportunity": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"Form/Opportunity": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"List/Prospect": {"on": "2026-11-06", "pass": "OneCRM, November"},
	"List/Quotation": {"on": "2026-11-06", "pass": "OneCRM, November"},
	"Form/Quotation": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"List/Sales Order": {"on": "2026-11-06", "pass": "OneCRM, November"},
	"Form/Sales Order": {"on": "2026-11-06", "pass": "OneCRM, November"},
	"Form/Contract": {"on": "2026-11-06", "pass": "OneCRM, November"},
	"List/Issue": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"List/Maintenance Visit": {"on": "2026-11-06", "pass": "OneCRM, November"},
	"onecrm": {"on": "2026-11-06", "pass": "OneCRM, closing"},
	"Form/Project Template": {"on": "2026-11-06", "pass": "Project to its form"},
	"Form/Project": {"on": "2026-11-06", "pass": "Project to its form"},
	"Form/Item": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"stock-on-hand": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"List/Stock Entry": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"Form/Stock Reconciliation": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"List/Serial No": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"Form/Warehouse": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"query-report/Stock Balance": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"query-report/Stock Ledger": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"to-order": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"List/Material Request": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"List/Request for Quotation": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"Form/Request for Quotation": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"Form/Supplier Quotation": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"Form/Purchase Order": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"Form/Quality Inspection": {"on": "2026-11-05", "pass": "OneInventory, quality"},
	"Form/Non Conformance": {"on": "2026-11-05", "pass": "OneQuality, first walk"},
	"Form/Quality Goal": {"on": "2026-11-05", "pass": "OneQuality, first walk"},
	"List/Quality Action": {"on": "2026-11-05", "pass": "OneQuality, first walk"},
	"List/Asset": {"on": "2026-11-05", "pass": "OneInventory, assets"},
	"Form/Asset": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"Form/Asset Maintenance Log": {"on": "2026-11-06", "pass": "OneInventory, closing"},
	"List/Delivery Note": {"on": "2026-11-05", "pass": "OneInventory, shipping"},
	"Form/Delivery Note": {"on": "2026-11-05", "pass": "OneInventory, shipping"},
	"Form/Purchase Receipt": {"on": "2026-11-05", "pass": "OneInventory, shipping"},
	"Form/Delivery Trip": {"on": "2026-11-05", "pass": "OneInventory, shipping"},
}

SCREEN = re.compile(r"^((Form|List|Tree|Report|query-report|print)/[^/]+|[a-z0-9-]+)$")


def dev() -> bool:
	from onedesk.one import dev

	return dev.site()


def for_boot() -> dict:
	"""What the stamps need, on a dev site; nothing anywhere else."""
	if not dev():
		return {}
	return {"dev": 1, "passed": PASSED}
