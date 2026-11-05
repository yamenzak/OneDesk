"""Review stamps in the bottom bar, on a dev site only (developer_mode or
one_dev): Island on a page an island still draws, and Passed on a screen
the final passthrough finished, with its day. A screen is named as frappe
routes to it (`Form/Customer`, `List/Customer`, `onemail`); it is added in
the commit that finishes its pass and taken out by a change that undoes it.
"""

import re

PASSED: dict[str, dict] = {
	# "Form/Customer": {"on": "2026-11-02", "pass": "Final passthrough"},
	"Form/Stock Entry": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"List/Batch": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"Form/Batch": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"inventory": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"List/Item": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"stock-on-hand": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"List/Stock Entry": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"Form/Stock Reconciliation": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"List/Serial No": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"Form/Warehouse": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"query-report/Stock Balance": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"query-report/Stock Ledger": {"on": "2026-11-05", "pass": "OneInventory, stock"},
	"to-order": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"List/Material Request": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"List/Request for Quotation": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"Form/Request for Quotation": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"Form/Supplier Quotation": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"Form/Purchase Order": {"on": "2026-11-05", "pass": "OneInventory, buying"},
	"Form/Quality Inspection": {"on": "2026-11-05", "pass": "OneInventory, quality"},
	"Form/Non Conformance": {"on": "2026-11-05", "pass": "OneQuality, first walk"},
	"Form/Quality Goal": {"on": "2026-11-05", "pass": "OneQuality, first walk"},
	"List/Quality Action": {"on": "2026-11-05", "pass": "OneQuality, first walk"},
	"List/Asset": {"on": "2026-11-05", "pass": "OneInventory, assets"},
	"Form/Asset": {"on": "2026-11-05", "pass": "OneInventory, assets"},
	"Form/Asset Maintenance Log": {"on": "2026-11-05", "pass": "OneInventory, assets"},
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
