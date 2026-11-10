"""Which modules are ready for live, and where each one's files are
(docs/READY.md). Pure, so the guards read it without a site.

A module's files are its folder, its static files under
`public/js/<folder>/`, `public/css/<folder>/` and `public/images/<folder>/`, and its screens under
`frontend/src/<screens>/`. OUTSIDE lists what still
sits elsewhere until it moves in; it only shrinks.
"""

import hashlib
import re
from pathlib import Path


def _lt(text: str) -> str:
	"""Marks a word the interface shows; the renderer says it in the reader's
	language. Plain here, so this file reads without frappe."""
	return text

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent

# One is declared ready for production once every module is. Until then the
# agreements change freely (docs/READY.md, Before production).
PRODUCTION = False

MODULES = {
	"OneMail": {
		"folder": "one_mail",
		"screens": "mail",
		"names": ("one_mail", "onemail"),
		"ready": True,
		# The points a guard can't settle, each as a person last looked at it
		# (HAND).
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "ef82a0f5117c", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "52a0c1d96fdb", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "52a0c1d96fdb", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "0e158460772b", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "52a0c1d96fdb", "by": "Claude, for Yamen"},
		},
		# Its help pages in reading order, each with its icon (docs/).
		"help": (
			("overview", "info"),
			("your-addresses", "at-sign"),
			("reading-and-writing", "mail"),
			("working-as-a-team", "users"),
			("connecting-a-mailbox", "plug"),
			("rules-and-out-of-office", "workflow"),
			("mail-on-records", "link"),
			("attachments-and-pictures", "paperclip"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneLegal": {
		"folder": "one_legal",
		"screens": "legal",
		"names": ("one_legal", "onelegal"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-09", "commit": "c07da170d8d0", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-09", "commit": "c07da170d8d0", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-09", "commit": "c07da170d8d0", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-09", "commit": "c07da170d8d0", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-09", "commit": "c07da170d8d0", "by": "Claude, for Yamen"},
		},
		# A module whose screen is a centre other modules open has no window,
		# so no foot or settings of its own; it says why (docs/READY.md, A
		# module with no window).
		"windowless": "TrustCenter is a dialog every module's foot opens, so OneLegal has no window, foot or settings of its own.",
		"help": (
			("overview", "info"),
			("agreeing", "file-check"),
			("optional-services", "toggle-right"),
			("changes", "history"),
			("who-can-do-what", "shield"),
		),
	},
	"OneAccount": {
		"folder": "one_account",
		"screens": "account",
		"names": ("one_account", "oneaccount"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-09", "commit": "ad363dde9810", "by": "Claude, for Yamen"},
		},
		"windowless": "AccountCenter is a dialog the avatar's menu and links open, so OneAccount has no window, foot or settings of its own.",
		"help": (
			("overview", "info"),
			("your-account", "user"),
			("people-and-devices", "users"),
			("plan-and-credits", "credit-card"),
			("who-can-do-what", "shield"),
		),
	},
	"OneCalendar": {
		"folder": "one_calendar",
		"screens": "calendar",
		"names": ("one_calendar", "onecalendar"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("calendars", "layers"),
			("events", "calendar-plus"),
			("deadlines", "alarm-clock"),
			("record-calendars", "folder-open"),
			("calendar-link", "link"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneTask": {
		"folder": "one_task",
		"screens": "task",
		"names": ("one_task", "onetask"),
		"ready": True,
		"companies": ("Task",),
		"interface": {
			"Task": {
				"fields": {"parent_task": "corner-left-up"},
				"cards": ({"key": "task.due"}, {"key": "task.steps"}, {"key": "task.waits"}, {"key": "task.logged"}),
				"states": {"order": ("Open", "Working", "Pending Review", "Overdue", "Completed"), "hide": ("Template", "Cancelled")},
			},
		},
		"checked": {
			"copy": {"on": "2026-11-06", "commit": "18161bb9ffa6", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-06", "commit": "18161bb9ffa6", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-06", "commit": "18161bb9ffa6", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-06", "commit": "18161bb9ffa6", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-06", "commit": "18161bb9ffa6", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("my-tasks", "list-checks"),
			("all-tasks", "circle-check"),
			("a-task", "file-text"),
			("timing", "timer"),
			("repeats-kinds-delays", "repeat"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneProject": {
		"folder": "one_project",
		"screens": "project",
		"names": ("one_project", "oneproject"),
		"ready": True,
		"companies": ("Project", "Timesheet"),
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("projects", "folder-kanban"),
			("starting-a-project", "plus"),
			("a-projects-page", "layout-dashboard"),
			("tasks-and-schedule", "list-checks"),
			("time", "timer"),
			("billing", "receipt"),
			("costs-and-budget", "wallet"),
			("subcontracts", "hard-hat"),
			("sub-projects", "git-branch"),
			("the-team", "users"),
			("the-customer", "globe"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
		"interface": {
			"Project": {
				"cards": ({"key": "project.done"}, {"key": "project.cost"}, {"key": "project.billed"}, {"key": "project.margin"}),
				"links": (
					{"label": _lt("Customer"), "icon": "building-2", "open": "customer"},
					{"label": _lt("Sales Order"), "icon": "file-text", "open": "sales_order"},
				),
				"states": {"field": "status", "order": ("Open", "On hold", "Completed"), "hide": ("Cancelled",)},
			},
			"Project Template": {
				"cards": ({"key": "template.tasks"}, {"key": "template.days"}, {"key": "template.used"}),
				"states": {"field": "project_type"},
			},
			"Timesheet": {
				"cards": ({"key": "timesheet.progress"}, {"key": "timesheet.worth"}),
				"states": {"order": ("Draft", "Submitted", "Partially Billed", "Billed", "Payslip"), "hide": ("Completed", "Cancelled")},
			},
		},
	},
	"OneInventory": {
		"folder": "one_inventory",
		"screens": "inventory",
		"names": ("one_inventory", "oneinventory"),
		"ready": True,
		"companies": (
			"Asset",
			"Asset Capitalization",
			"Asset Maintenance",
			"Asset Maintenance Team",
			"Asset Movement",
			"Asset Repair",
			"Asset Value Adjustment",
			"Blanket Order",
			"Delivery Note",
			"Delivery Trip",
			"Item Default",
			"Item Standard Cost",
			"Landed Cost Voucher",
			"Material Request",
			"Pick List",
			"Purchase Order",
			"Purchase Receipt",
			"Putaway Rule",
			"Quality Inspection",
			"Request for Quotation",
			"Serial No",
			"Serial and Batch Bundle",
			"Stock Closing Entry",
			"Stock Entry",
			"Stock Reconciliation",
			"Stock Reservation Entry",
			"Supplier Quotation",
			"Warehouse",
		),
		"checked": {
			"copy": {"on": "2026-11-06", "commit": "8184e878afdc", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-06", "commit": "8184e878afdc", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-06", "commit": "8184e878afdc", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-06", "commit": "8184e878afdc", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-06", "commit": "8184e878afdc", "by": "Claude, for Yamen"},
		},
		"interface": {
			"Item": {
				"fields": {"item_code": "hash"},
				"cards": ({"key": "item.on_hand", "title": _lt("On Hand")}, {"key": "item.free", "title": _lt("Free to Sell")}, {"key": "item.on_order", "title": _lt("On Order")}, {"key": "item.worth"}),
				"states": {
					"kinds": (
						{"label": _lt("Kept in Stock"), "filters": (("is_stock_item", "=", 1), ("has_variants", "=", 0))},
						{"label": _lt("Made Here"), "filters": (("default_bom", "is", "set"),)},
						{"label": _lt("Services"), "filters": (("is_stock_item", "=", 0), ("is_fixed_asset", "=", 0))},
						{"label": _lt("Equipment"), "filters": (("is_fixed_asset", "=", 1),)},
						{"label": _lt("Sizes or Colours"), "filters": (("has_variants", "=", 1),)},
					),
				},
			},
			"Purchase Receipt": {
				"cards": ({"key": "receipt.order"}, {"key": "receipt.worth"}, {"key": "receipt.rejected"}, {"key": "project.of"}),
				"track": "receipt.progress",
				"states": {"order": ("To Bill", "Partly Billed", "Completed", "Return", "Return Issued", "Closed", "Draft"), "hide": ("Cancelled",)},
			},
			"Delivery Note": {
				"cards": ({"key": "delivery.order"}, {"key": "delivery.total"}, {"key": "delivery.trip"}, {"key": "project.of"}),
				"track": "delivery.progress",
				"states": {"order": ("To Bill", "Partially Billed", "Completed", "Return", "Return Issued", "Closed", "Draft"), "hide": ("Cancelled",)},
			},
			"Delivery Trip": {
				"cards": ({"key": "trip.stops"}, {"key": "vehicle"}, {"key": "departure_time"}),
				"states": {"order": ("Scheduled", "In Transit", "Completed", "Draft"), "hide": ("Cancelled",)},
			},
			"Pick List": {
				"cards": ({"key": "pick.done"}, {"key": "customer_name"}, {"key": "parent_warehouse"}),
				"states": {"order": ("Open", "Partly Delivered", "Partially Transferred", "Completed", "Draft"), "hide": ("Cancelled",)},
			},
			"Shipment": {"states": {"order": ("Submitted", "Booked", "Completed", "Draft"), "hide": ("Cancelled",)}},
			"Asset": {
				"cards": ({"key": "asset.worth_now"}, {"key": "asset.cost"}, {"key": "asset.next_service", "title": _lt("Next Service")}, {"key": "asset.next_depreciation"}),
				"states": {
					"order": ("Submitted", "Partially Depreciated", "In Maintenance", "Out of Order", "Fully Depreciated", "Sold", "Scrapped", "Capitalized", "Work In Progress", "Draft"),
					"hide": ("Cancelled",),
				},
			},
			"Asset Maintenance Log": {
				"cards": ({"key": "service.due"}, {"key": "assign_to_name"}, {"key": "service.last"}),
				"states": {"field": "maintenance_status", "order": ("Overdue", "Planned", "Completed"), "hide": ("Cancelled",)},
			},
			"Asset Maintenance": {
				"cards": ({"key": "schedule.next"}, {"key": "service.asset"}, {"key": "maintenance_team"}),
				"states": {"field": "maintenance_team"},
			},
			"Asset Repair": {
				"cards": ({"key": "repair.out"}, {"key": "repair.cost"}),
				"states": {"field": "repair_status", "order": ("Pending", "Completed"), "hide": ("Cancelled",)},
			},
			"Asset Movement": {
				"fields": {"purpose": "arrow-left-right"},
				"cards": ({"key": "handover.what"}, {"key": "handover.from"}, {"key": "handover.to"}, {"key": "transaction_date"}),
				"states": {"field": "purpose", "order": ("Issue", "Receipt", "Transfer", "Transfer and Issue")},
			},
			"Asset Value Adjustment": {
				"cards": ({"key": "repair.asset"}, {"key": "current_asset_value"}, {"key": "new_asset_value"}, {"key": "adjustment.change"}),
				"states": {"field": "asset_category"},
			},
			"Quality Inspection": {
				"cards": ({"key": "inspection.readings"}, {"key": "inspection.of"}, {"key": "item_name"}, {"key": "inspection.by"}),
				"states": {"order": ("Accepted", "Rejected"), "hide": ("Cancelled",)},
			},
			"Material Request": {
				"cards": ({"key": "request.asked_by"}, {"key": "project.of"}),
				"track": "material.progress",
				"states": {
					"order": ("Pending", "Partially Ordered", "Ordered", "Partially Received", "Received", "Issued", "Transferred", "Stopped", "Draft"),
					"hide": ("Cancelled",),
				},
			},
			"Request for Quotation": {
				"cards": ({"key": "rfq.answered"}, {"key": "rfq.cheapest"}, {"key": "rfq.request"}, {"key": "project.of"}),
				"states": {"hide": ("Submitted", "Cancelled")},
			},
			"Supplier Quotation": {
				"cards": ({"key": "quote.cheapest"}, {"key": "quote.valid"}, {"key": "quote.request"}, {"key": "quote.ordered"}),
				"states": {"order": ("Submitted", "Partially Ordered", "Ordered", "Expired", "Draft"), "hide": ("Cancelled",)},
			},
			"Purchase Order": {
				"cards": ({"key": "order.total"}, {"key": "project.of"}, {"key": "order.blanket"}),
				"track": "order.progress",
				"states": {
					"order": ("To Receive and Bill", "To Receive", "To Bill", "To Pay", "On Hold", "Completed", "Closed", "Delivered", "Draft"),
					"hide": ("Cancelled",),
				},
			},
			"Stock Entry": {
				"cards": (
					{"key": "move.from", "title": _lt("Source Warehouse")},
					{"key": "move.to", "title": _lt("Target Warehouse")},
					{"key": "move.value"},
					{"key": "project.of"},
				),
				"states": {
					"field": "stock_entry_type",
					"order": ("Material Receipt", "Material Issue", "Material Transfer", "Manufacture", "Repack"),
				},
			},
			"Stock Reconciliation": {
				"cards": (
					{"key": "count.where"},
					{"key": "count.items"},
					{"key": "difference_amount"},
				),
				"states": {"field": "purpose", "order": ("Stock Reconciliation", "Opening Stock")},
			},
			"Batch": {
				"cards": (
					{"key": "batch.left"},
					{"key": "batch.expires"},
					{"key": "batch.came_from"},
					{"key": "batch.went"},
				),
				"states": {"field": "item"},
			},
			"Serial No": {
				"states": {"field": "status", "order": ("Active", "Delivered", "Consumed", "Inactive", "Expired")},
			},
			"Warehouse": {
				"cards": (
					{"key": "warehouse.items"},
					{"key": "warehouse.worth"},
					{"key": "warehouse.low"},
					{"key": "warehouse.last"},
				),
				"states": {"field": "warehouse_type"},
			},
		},
		"help": (
			("overview", "info"),
			("getting-ready", "list-checks"),
			("items", "package"),
			("an-items-page", "layout-dashboard"),
			("stock", "warehouse"),
			("buying", "shopping-cart"),
			("receiving-and-delivering", "truck"),
			("batches-and-quality", "layers"),
			("equipment", "wrench"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneFactory": {
		"folder": "one_factory",
		"screens": "factory",
		"names": ("one_factory", "onefactory"),
		"ready": False,
		"companies": (
			"BOM",
			"BOM Creator",
			"Job Card",
			"Master Production Schedule",
			"Plant Floor",
			"Production Plan",
			"Production Plan Schedule",
			"Sales Forecast",
			"Subcontracting Order",
			"Subcontracting Receipt",
			"Work Order",
		),
		"interface": {
			"Work Order": {
				"cards": ({"key": "work.for"}, {"key": "project.of"}),
				"track": "work.progress",
				"links": (
					{"label": _lt("Job Card"), "icon": "list-checks", "list": "Job Card", "with": {"work_order": "name"}, "when": (("status", "!=", "Draft"),)},
					{"label": _lt("Stock Entry"), "icon": "warehouse", "list": "Stock Entry", "with": {"work_order": "name"}, "when": (("status", "!=", "Draft"),)},
					{"label": _lt("Sales Order"), "icon": "receipt", "open": "sales_order"},
				),
				"states": {"order": ("Not Started", "In Process", "Completed", "Stopped", "Closed", "Draft"), "hide": ("Cancelled",)},
			},
			"Job Card": {
				"cards": ({"key": "card.order"}, {"key": "workstation"}, {"key": "card.done"}, {"key": "card.time"}),
				"states": {"order": ("Open", "Work In Progress", "On Hold", "Material Transferred", "Completed"), "hide": ("Cancelled",)},
			},
			"BOM": {
				"cards": ({"key": "bom.cost"}, {"key": "bom.steps"}, {"key": "bom.orders"}),
				"links": (
					{"label": _lt("Work Order"), "icon": "factory", "new": "Work Order", "with": {"production_item": "item", "bom_no": "name"}, "when": (("is_active", "=", 1),)},
					{"label": _lt("Work Order"), "icon": "factory", "list": "Work Order", "with": {"bom_no": "name"}},
				),
				"states": {
					"kinds": (
						{"label": _lt("Default"), "filters": (("is_default", "=", 1),)},
						{"label": _lt("Active"), "filters": (("is_active", "=", 1),)},
						{"label": _lt("Inactive"), "filters": (("is_active", "=", 0),)},
					),
				},
			},
			"Production Plan": {
				"states": {"order": ("Not Started", "In Process", "Material Requested", "Completed", "Closed", "Draft"), "hide": ("Cancelled",)},
			},
			"Subcontracting Order": {
				"cards": ({"key": "project.of"}, {"key": "total"}),
				"track": "sub.progress",
				"links": (
					{"label": _lt("Purchase Order"), "icon": "receipt", "open": "purchase_order"},
				),
				"states": {"order": ("Open", "Partial Material Transferred", "Material Transferred", "Partially Received", "Completed", "Closed", "Draft"), "hide": ("Cancelled",)},
			},
			"Subcontracting Receipt": {
				"cards": ({"key": "sub.order"}, {"key": "supplier_name"}, {"key": "project.of"}, {"key": "total"}),
				"states": {"order": ("Completed", "Return", "Return Issued", "Closed", "Draft"), "hide": ("Cancelled",)},
			},
			"Workstation": {
				"tabs": {"details_tab": "hard-hat"},
				"states": {"order": ("Production", "Idle", "Setup", "Maintenance", "Problem", "Off")},
			},
			"Plant Floor": {
				"states": {"field": "warehouse"},
			},
		},
		"help": (
			("overview", "info"),
			("work-orders-and-the-floor", "hard-hat"),
			("bills-of-materials", "list-tree"),
			("work-sent-to-suppliers", "send"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneQuality": {
		"folder": "one_quality",
		"screens": "quality",
		"names": ("one_quality", "onequality"),
		"ready": False,
		"companies": ("Non Conformance", "Quality Action"),
		"interface": {
			"Non Conformance": {
				"fields": {"subject": "triangle-alert"},
				"cards": ({"key": "quality.nc_actions"}, {"key": "procedure"}, {"key": "quality.raised_by"}),
				"links": (
					{"label": _lt("Quality Action"), "icon": "wrench", "new": "Quality Action", "with": {"one_non_conformance": "name", "procedure": "procedure"}, "when": (("status", "=", "Open"),)},
					{"label": _lt("Quality Action"), "icon": "wrench", "list": "Quality Action", "with": {"one_non_conformance": "name"}},
				),
				"states": {"order": ("Open", "Resolved"), "hide": ("Cancelled",)},
			},
			"Quality Action": {
				"cards": ({"key": "quality.action_done"}, {"key": "quality.action_problem"}, {"key": "goal"}, {"key": "procedure"}),
				"states": {"order": ("Open", "Completed")},
			},
			"Quality Review": {
				"cards": ({"key": "quality.review_met"}, {"key": "procedure"}),
				"states": {"order": ("Open", "Failed", "Passed")},
			},
			"Quality Goal": {
				"cards": ({"key": "quality.goal_last"}, {"key": "procedure"}),
				"states": {"field": "frequency"},
			},
			"Quality Procedure": {
				"cards": ({"key": "quality.procedure_open"}, {"key": "process_owner_full_name"}),
				"states": {"field": "process_owner_full_name"},
			},
			"Quality Meeting": {"states": {"order": ("Open", "Closed")}},
			"Quality Feedback": { "states": {"field": "document_type"}},
		},
		"help": (
			("overview", "info"),
			("procedures-and-goals", "list-ordered"),
			("problems-and-actions", "triangle-alert"),
			("meetings-and-feedback", "users"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneBook": {
		"folder": "one_book",
		"screens": "books",
		"names": ("one_book", "onebook"),
		"ready": True,
		"companies": (
			"Account",
			"Account Closing Balance",
			"Accounting Dimension Filter",
			"Accounting Period",
			"Bank Account",
			"Bank Statement Import",
			"Bank Transaction",
			"Bank Transaction Rule",
			"Budget",
			"Cost Center",
			"Cost Center Allocation",
			"Dunning",
			"Dunning Type",
			"Email Digest",
			"Exchange Rate Revaluation",
			"Import Supplier Invoice",
			"Invoice Discounting",
			"Item Tax Template",
			"Journal Entry",
			"Journal Entry Template",
			"Ledger Merge",
			"Lower Deduction Certificate",
			"Loyalty Program",
			"Mode of Payment Account",
			"POS Closing Entry",
			"POS Invoice",
			"POS Opening Entry",
			"POS Profile",
			"Party Account",
			"Payment Entry",
			"Payment Gateway Account",
			"Payment Order",
			"Payment Request",
			"Period Closing Voucher",
			"Pricing Rule",
			"Process Deferred Accounting",
			"Process Payment Reconciliation",
			"Process Statement Of Accounts",
			"Promotional Scheme",
			"Purchase Invoice",
			"Purchase Taxes and Charges Template",
			"Repost Accounting Ledger",
			"Sales Invoice",
			"Sales Taxes and Charges Template",
			"Share Transfer",
			"Shareholder",
			"Shipping Rule",
			"Subscription",
			"Tax Rule",
			"Tax Withholding Account",
			"Unreconcile Payment",
		),
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "4d0fc1c94a14", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "4d0fc1c94a14", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "4d0fc1c94a14", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "4d0fc1c94a14", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "4d0fc1c94a14", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("home", "layout-dashboard"),
			("getting-ready", "list-checks"),
			("invoices", "receipt"),
			("payments", "banknote"),
			("the-bank", "landmark"),
			("journal-entries", "book-open"),
			("tax", "percent"),
			("closing", "lock"),
			("currencies", "coins"),
			("printing", "printer"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
		# How its record types are drawn: an icon for each tab and field, the
		# head's cards (at most four, by the key of a head row or chart in
		# heads.py) and the row whose steps are the track. See interface().
		"interface": {
			"Bank Account": {
				"cards": ({"key": "bank.balance"}, {"key": "bank.unmatched"}, {"key": "bank.last_line"}),
				"states": {
					"kinds": (
						{"label": _lt("Company Account"), "filters": (("is_company_account", "=", 1),)},
						{"label": _lt("Party Account"), "filters": (("is_company_account", "=", 0),)},
					),
				},
			},
			"Bank Transaction": {
				"cards": ({"key": "bank_account"}, {"key": "reference_number"}, {"key": "bank.line_match"}, {"key": "bank.line_reconcile"}),
				"states": {"order": ("Unreconciled", "Reconciled", "Pending", "Settled"), "hide": ("Cancelled",)},
			},
			"Journal Entry": {
				"cards": ({"key": "journal.reference"}, {"key": "cheque_no"}, {"key": "total_debit"}),
				"track": "journal.progress",
				"states": {"field": "voucher_type", "order": ("Journal Entry", "Bank Entry", "Cash Entry", "Credit Note", "Debit Note", "Opening Entry", "Depreciation Entry", "Exchange Rate Revaluation")},
			},
			"Payment Entry": {
				"cards": ({"key": "paid_amount"}, {"key": "mode_of_payment"}, {"key": "reference_no"}, {"key": "project.of"}),
				"track": "payment.progress",
				"states": {"field": "payment_type", "order": ("Receive", "Pay", "Internal Transfer")},
			},
			"Purchase Invoice": {
				"cards": (
					{"key": "invoice.outstanding"},
					{"key": "invoice.due"},
					{"key": "grand_total"},
					{"key": "invoice.party_billed", "title": _lt("Billed in 12 Months")},
				),
				"track": "invoice.progress",
				"states": {
					"field": "status",
					"order": ("Overdue", "Unpaid", "Partly Paid", "Paid", "Return", "Debit Note Issued", "Draft"),
					"hide": ("Cancelled",),
				},
			},
			"Sales Invoice": {
				"cards": (
					{"key": "invoice.outstanding"},
					{"key": "invoice.due"},
					{"key": "grand_total"},
					{"key": "invoice.party_billed", "title": _lt("Billed in 12 Months")},
				),
				"track": "invoice.progress",
				"states": {
					"field": "status",
					"order": ("Overdue", "Unpaid", "Partly Paid", "Paid", "Return", "Credit Note Issued", "Draft"),
					"hide": ("Cancelled",),
				},
			},
			"Supplier": {
				"cards": (
					{"key": "party.overdue"},
					{"key": "party.last_bill"},
					{"key": "Open Orders"},
					{"key": "party.billed", "title": _lt("Billed in 12 Months")},
				),
				"states": {"field": "supplier_type", "order": ("Company", "Individual", "Partnership")},
			},
		},
	},
	"OneCRM": {
		"folder": "one_crm",
		"screens": "crm",
		"names": ("one_crm", "onecrm"),
		"ready": True,
		"companies": (
			"Customer Credit Limit",
			"Installation Note",
			"Issue",
			"Lead",
			"Maintenance Schedule",
			"Maintenance Visit",
			"Opportunity",
			"Party Account",
			"Proforma Invoice",
			"Prospect",
			"Quotation",
			"Sales Order",
			"Subcontracting Inward Order",
			"Warranty Claim",
		),
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "e24156bb54b5", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("leads", "user-plus"),
			("next-step", "calendar-check"),
			("a-record-page", "layout-dashboard"),
			("home", "house"),
			("stages-and-pipeline", "kanban"),
			("quoting", "file-text"),
			("customers", "building-2"),
			("appointments-and-campaigns", "megaphone"),
			("support", "life-buoy"),
			("reports", "chart-bar"),
			("setup", "list-checks"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
		# How its record types are drawn. See OneBook's and interface().
		"interface": {
			"Customer": {
				"cards": (
					{"key": "party.overdue"},
					{"key": "party.last_bill"},
					{"key": "Open Orders"},
					{"key": "party.billed", "title": _lt("Billed in 12 Months")},
				),
				"states": {"field": "customer_type", "order": ("Company", "Individual", "Partnership")},
			},
			"Lead": {
				"tabs": {"activities_tab": "calendar-check"},
				"cards": ({"key": "crm.next_step"}, {"key": "crm.reply"}, {"key": "crm.contact"}, {"key": "crm.deals"}),
				"states": {"order": ("Lead", "Open", "Replied", "Interested", "Opportunity", "Quotation", "Converted"), "hide": ("Do Not Contact", "Lost Quotation")},
			},
			"Opportunity": {
				"tabs": {"activities_tab": "calendar-check"},
				"cards": ({"key": "crm.value"}, {"key": "crm.stage"}, {"key": "crm.next_step"}, {"key": "crm.closes"}),
				"states": {"order": ("Open", "Replied", "Quotation", "Converted", "Lost"), "hide": ("Closed",)},
			},
			"Quotation": {
				"cards": ({"key": "order.total"}, {"key": "crm.valid"}, {"key": "crm.deal_of"}, {"key": "project.of"}),
				"states": {"order": ("Draft", "Open", "Replied", "Partially Ordered", "Ordered", "Expired", "Lost"), "hide": ("Cancelled",)},
			},
			"Sales Order": {
				"tabs": {"payment_schedule_section": "calendar-clock"},
				"cards": ({"key": "order.total"}, {"key": "crm.deliver_by"}, {"key": "per_delivered"}, {"key": "per_billed"}),
				"states": {"order": ("Draft", "To Deliver and Bill", "To Bill", "To Deliver", "Completed"), "hide": ("Cancelled", "Closed")},
			},
			"Contract": {
				"cards": ({"key": "signed_on"}, {"key": "end_date"}, {"key": "project.of"}),
				"states": {"order": ("Unsigned", "Active", "Inactive")},
			},
			"Appointment": {
				"fields": {"customer_name": "user"},
				"cards": ({"key": "scheduled_time"}, {"key": "crm.met_with"}),
				"states": {"order": ("Open", "Unverified", "Closed")},
			},
			"Email Campaign": {
				"fields": {"email_campaign_for": "users"},
				"cards": ({"key": "start_date"}, {"key": "end_date"}, {"key": "recipient"}),
				"states": {"order": ("Scheduled", "In Progress", "Completed", "Unsubscribed")},
			},
			"Email Group": {
				"states": {
					"kinds": (
						{"label": _lt("With Subscribers"), "filters": (("total_subscribers", ">", 0),)},
						{"label": _lt("Empty"), "filters": (("total_subscribers", "=", 0),)},
					),
				},
			},
			"Issue": {
				"fields": {"subject": "message-circle-warning"},
				"states": {"order": ("Open", "Replied", "On Hold", "Resolved", "Closed")},
			},
			"Maintenance Schedule": {
				"cards": ({"key": "crm.next_visit"}, {"key": "crm.visits_made"}),
				"states": {"field": "status"},
			},
			"Prospect": {
				"tabs": {"activities_tab": "calendar-check"},
				"states": {"field": "industry"},
			},
			"Warranty Claim": {
				"cards": ({"key": "warranty_amc_status"}, {"key": "warranty_expiry_date"}, {"key": "resolution_date"}),
				"states": {"order": ("Open", "Work In Progress", "Closed", "Cancelled")},
			},
		},
	},
	"OneDisplay": {
		"folder": "one_display",
		"screens": "display",
		"names": ("one_display", "onedisplay"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("screens-and-pairing", "tv"),
			("templates", "layout-template"),
			("channels", "radio"),
			("slides", "images"),
			("widgets-and-sources", "layout-dashboard"),
			("sound", "speaker"),
			("queues", "list-ordered"),
			("boards", "layout-grid"),
			("alerts", "siren"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneHR": {
		"folder": "one_hr",
		"screens": "hr",
		"names": ("one_hr", "onehr"),
		"ready": True,
		"companies": (
			"Additional Salary",
			"Appointment Letter",
			"Appraisal",
			"Appraisal Cycle",
			"Arrear",
			"Attendance",
			"Attendance Request",
			"Department",
			"Employee",
			"Employee Advance",
			"Employee Benefit Application",
			"Employee Benefit Claim",
			"Employee Incentive",
			"Employee Onboarding",
			"Employee Onboarding Template",
			"Employee Other Income",
			"Employee Performance Feedback",
			"Employee Promotion",
			"Employee Separation",
			"Employee Separation Template",
			"Employee Tax Exemption Declaration",
			"Employee Tax Exemption Proof Submission",
			"Employee Transfer",
			"Exit Interview",
			"Expense Claim",
			"Full and Final Statement",
			"Goal",
			"Gratuity",
			"Income Tax Slab",
			"Job Offer",
			"Job Opening",
			"Job Requisition",
			"Leave Adjustment",
			"Leave Allocation",
			"Leave Application",
			"Leave Block List",
			"Leave Encashment",
			"Leave Period",
			"Leave Policy Assignment",
			"Overtime Slip",
			"Payroll Correction",
			"Payroll Entry",
			"Payroll Period",
			"Retention Bonus",
			"Salary Slip",
			"Salary Structure",
			"Salary Structure Assignment",
			"Salary Withholding",
			"Shift Assignment",
			"Shift Request",
			"Shift Schedule Assignment",
			"Staffing Plan",
			"Training Event",
			"Training Program",
			"Travel Request",
			"Vehicle",
		),
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "70b26c9333b3", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("employees", "id-card"),
			("clocking-in", "clock"),
			("attendance", "calendar-check"),
			("leave", "plane"),
			("pay", "banknote"),
			("tax-and-benefits", "percent"),
			("expenses", "receipt"),
			("hiring", "user-plus"),
			("growth", "trending-up"),
			("joining-and-leaving", "door-open"),
			("setup", "list-checks"),
			("notifications", "bell"),
			("printing", "printer"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
		# How its record types are drawn. See OneBook's and interface().
		"interface": {
			"Employee": {
				"tabs": {"basic_details_tab": "id-card"},
				"cards": ({"key": "employee.standing"}, {"key": "employee.leave"}, {"key": "employee.awaiting"}, {"key": "employee.checked"}),
				"states": {"order": ("Active", "Suspended", "Inactive", "Left")},
				"links": (
					{
						"label": _lt("Apply for Leave"),
						"icon": "plane-takeoff",
						"new": "Leave Application",
						"with": {"employee": "name"},
						"when": (("status", "=", "Active"),),
					},
					{
						"label": _lt("Claim an Expense"),
						"icon": "receipt",
						"new": "Expense Claim",
						"with": {"employee": "name"},
						"when": (("status", "=", "Active"),),
					},
					{
						"label": _lt("Assign a Salary Structure"),
						"icon": "wallet",
						"new": "Salary Structure Assignment",
						"with": {"employee": "name"},
						"when": (("status", "=", "Active"),),
					},
				),
			},
			"Leave Application": {
				"cards": ({"key": "total_leave_days"}, {"key": "leave.left"}, {"key": "leave_approver_name"}),
				"states": {"order": ("Open", "Approved", "Rejected"), "hide": ("Cancelled",)},
			},
			"Leave Allocation": {
				"cards": ({"key": "new_leaves_allocated"}, {"key": "total_leaves_allocated"}),
				"states": {"field": "leave_type"},
			},
			"Attendance": {
				"cards": ({"key": "working_hours"}, {"key": "shift"}, {"key": "in_time"}),
				"states": {"order": ("Present", "Work From Home", "Half Day", "On Leave", "Absent")},
			},
			"Expense Claim": {
				"cards": ({"key": "total_claimed_amount"}, {"key": "total_sanctioned_amount"}, {"key": "total_advance_amount"}, {"key": "project.of"}),
				"states": {"order": ("Draft", "Unpaid", "Partially Paid", "Paid", "Rejected"), "hide": ("Submitted", "Cancelled")},
			},
			"Employee Advance": {
				"fields": {"purpose": "target"},
				"cards": ({"key": "advance_amount"}, {"key": "paid_amount"}, {"key": "claimed_amount"}, {"key": "return_amount"}),
				"states": {"order": ("Draft", "Unpaid", "Paid", "Partially Paid", "Claimed", "Returned", "Partly Claimed and Returned"), "hide": ("Cancelled",)},
			},
			"Salary Slip": {
				"tabs": {"employee_and_payroll_tab": "user"},
				"cards": ({"key": "gross_pay"}, {"key": "total_deduction"}, {"key": "net_pay"}, {"key": "payment_days"}),
				"states": {"order": ("Draft", "Submitted", "Withheld"), "hide": ("Cancelled",)},
			},
			"Payroll Entry": {
				"cards": ({"key": "number_of_employees"}, {"key": "payroll_frequency"}),
				"states": {"order": ("Draft", "Queued", "Submitted", "Failed"), "hide": ("Cancelled",)},
			},
			"Job Applicant": {
				"cards": ({"key": "applicant.opening"}, {"key": "source"}, {"key": "applicant.rating"}),
				"states": {"order": ("Open", "Replied", "Shortlisted", "Hold", "Accepted", "Rejected")},
			},
			"Job Opening": {
				"states": {"order": ("Open", "Closed")},
			},
			"Interview": {
				"cards": ({"key": "scheduled_on"}, {"key": "interview.rating"}),
				"states": {"order": ("Pending", "Under Review", "Cleared", "Rejected"), "hide": ("Cancelled",)},
			},
			"Job Offer": {
				"states": {"order": ("Draft", "Ready to Send", "Awaiting Response", "Accepted", "Rejected"), "hide": ("Cancelled",)},
			},
			"Job Requisition": {
				"states": {"order": ("Pending", "Open & Approved", "On Hold", "Filled", "Rejected"), "hide": ("Cancelled",)},
			},
			"Appraisal": {
				"cards": ({"key": "final_score"}, {"key": "appraisal_cycle"}),
				"states": {"field": "appraisal_cycle"},
			},
			"Appraisal Cycle": {
				"states": {"order": ("Not Started", "In Progress", "Completed")},
			},
			"Goal": {
				"states": {"order": ("Pending", "In Progress", "Completed", "Closed", "Archived")},
			},
			"Shift Request": {
				"states": {"order": ("Draft", "Approved", "Rejected")},
			},
			"Attendance Request": {
				"states": {"field": "reason"},
			},
			"Employee Onboarding": {
				"states": {"field": "boarding_status", "order": ("Pending", "In Process", "Completed")},
			},
			"Employee Separation": {
				"states": {"field": "boarding_status", "order": ("Pending", "In Process", "Completed")},
			},
			"Gratuity": {
				"cards": ({"key": "amount"},),
				"states": {"order": ("Draft", "Unpaid", "Paid"), "hide": ("Submitted", "Cancelled")},
			},
			"Full and Final Statement": {
				"states": {"order": ("Unpaid", "Paid"), "hide": ("Cancelled",)},
			},
			"Employee Grievance": {
				"states": {"order": ("Open", "Investigated", "Resolved", "Invalid"), "hide": ("Cancelled",)},
			},
			"Training Event": {
				"states": {"field": "event_status", "order": ("Scheduled", "Completed"), "hide": ("Cancelled",)},
			},
		},
	},
	"OneSlide": {
		"folder": "one_slide",
		"screens": "slide",
		"names": ("one_slide", "oneslide"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
		},
		"windowless": "A presentation opens from OneCloud in an editor that fills the window, so OneSlide's foot and settings are OneCloud's.",
		"help": (
			("overview", "info"),
			("working-on-slides", "presentation"),
			("design-and-layers", "layers"),
			("history-and-pdf", "history"),
			("presenting-by-link", "link"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
		),
	},
	"OneWriter": {
		"folder": "one_doc",
		"screens": "writer",
		"names": ("one_doc", "onedoc"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
		},
		"windowless": "A document opens from OneCloud in an editor that fills the window, so OneWriter's foot and settings are OneCloud's.",
		"help": (
			("overview", "info"),
			("writing", "pencil"),
			("writing-together", "users"),
			("history-and-templates", "history"),
			("printing-and-word", "printer"),
			("on-a-record", "link"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
		),
	},
	"OneWorkbook": {
		"folder": "one_sheet",
		"screens": "sheet",
		"names": ("one_sheet", "onesheet"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
		},
		"windowless": "A workbook opens from OneCloud in an editor that fills the window, so OneWorkbook's foot and settings are OneCloud's.",
		"help": (
			("overview", "info"),
			("working-in-a-workbook", "sheet"),
			("excel-and-csv", "file-spreadsheet"),
			("history-and-templates", "history"),
			("printing", "printer"),
			("a-records-table", "table"),
			("branded-sheets", "palette"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
		),
	},
	"OnePortal": {
		"folder": "one_portal",
		"screens": "portal",
		# Its own frappe-ui app, built apart from the islands (frontend/portal).
		"app": "portal",
		"names": ("one_portal", "oneportal"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "5e04e24b45b0", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "globe"),
			("inviting", "user-plus"),
			("links", "link"),
			("what-they-see", "eye"),
			("who-can-do-what", "shield"),
		),
	},
	"OneInterface": {
		"folder": "one_interface",
		"screens": "interface",
		"names": ("one_interface", "oneinterface"),
		"ready": False,
		"windowless": "OneInterface is the window every other module is drawn in, so it has no window, foot or settings of its own.",
		# A module that is the frame the others are drawn in, rather than an
		# app somebody is given, ships no roles; it says why (docs/READY.md,
		# An engine module).
		"engine": "OneInterface draws every module's screens and keeps no records of its own, so nobody is given it and it ships no roles.",
		"help": (
			("overview", "app-window"),
			("records", "file-text"),
			("lists", "list"),
			("dialogs", "square-stack"),
			("looks-and-themes", "palette"),
		),
	},
	"One": {
		"folder": "one",
		"screens": "one",
		"names": ("one_control", "access_center", "notification_center", "role_matrix"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-10", "commit": "bc85304106b7", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-10", "commit": "bc85304106b7", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-10", "commit": "bc85304106b7", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-10", "commit": "bc85304106b7", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-10", "commit": "bc85304106b7", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("home", "house"),
			("address-book", "book-user"),
			("announcements", "megaphone"),
			("records", "file-text"),
			("recycle-bin", "trash-2"),
			("weather", "cloud-sun"),
			("news", "newspaper"),
			("notifications", "bell"),
			("shortcuts", "keyboard"),
			("access-and-the-audit-log", "shield-check"),
			("your-data", "folder-lock"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneAI": {
		"folder": "one_ai",
		"screens": "intake",
		"names": ("one_ai", "oneai"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-08", "commit": "87069d373334", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("asking-oneai", "sparkles"),
			("cards", "check-check"),
			("writing", "pencil"),
			("summaries", "notebook-text"),
			("reading", "inbox"),
			("finding", "search"),
			("remembers", "brain"),
			("web-search", "globe"),
			("tiers-and-credits", "coins"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneAdmin": {
		"folder": "one_admin",
		"screens": "admin",
		"names": ("one_admin", "oneadmin"),
		"operators": True,
		"engine": "OneAdmin runs only on the admin site, where its one role is set, so it ships no roles to a workspace.",
		"help": (
			("overview", "info"),
			("workspaces", "building"),
			("settings", "settings"),
		),
	},
}

# The fourteen points a module is held to before it is marked ready
# (docs/READY.md, The fourteen points), in that order: what each is called,
# and the guards that hold every module to it on every run.
READY = "tests/guards/test_ready.py::"
POINTS = {
	"home": {
		"title": "One home",
		"guards": (
			READY + "test_nothing_of_a_module_is_left_outside",
			READY + "test_nothing_outside_a_module_is_named_for_it",
			READY + "test_a_module_writes_only_agents_scratchpad_and_docs",
		),
	},
	"versioned": {
		"title": "Versioned",
		"guards": (
			READY + "test_every_change_to_a_module_is_a_version",
			READY + "test_versions_follow_one_another",
			READY + "test_a_version_is_written_for_the_people_using_it",
		),
	},
	"whats_new": {
		"title": "What's New in the app",
		"guards": (READY + "test_a_module_has_one_settings_dialog_and_one_foot",),
	},
	"documented": {
		"title": "Documented",
		"guards": (
			READY + "test_a_module_writes_only_agents_scratchpad_and_docs",
			READY + "test_every_help_page_is_listed_and_every_link_lands",
			READY + "test_a_help_page_names_no_code",
			READY + "test_a_help_page_is_headed_pictured_and_linked_soundly",
		),
	},
	"copy": {
		"title": "Copy",
		"guards": (
			"tests/guards/test_copy.py::test_a_heading_is_five_words_or_fewer",
			"tests/guards/test_copy.py::test_a_description_is_one_sentence",
			"tests/guards/test_copy.py::test_no_banned_word_is_shown",
		),
	},
	"roles": {
		"title": "Roles",
		"guards": (
			READY + "test_a_module_ships_its_roles",
			READY + "test_a_module_grants_through_abilities_alone",
			READY + "test_a_module_leaves_roles_and_notifications_to_their_centers",
		),
	},
	"oneai": {
		"title": "OneAI",
		"guards": (READY + "test_a_module_reaches_every_change_through_oneai_or_says_why_not",),
	},
	"demo": {
		"title": "Demo and tests",
		"guards": (
			"tests/guards/test_coverage.py::test_no_module_has_more_left_to_cover_than_it_had",
			"tests/guards/test_demo.py::test_every_step_is_built_and_written_down",
		),
	},
	"notifications": {
		"title": "Notifications",
		"guards": (
			READY + "test_a_module_says_how_and_from_whom_it_tells_people",
			"tests/guards/test_notifications.py::test_every_type_sent_is_declared",
			READY + "test_a_module_leaves_roles_and_notifications_to_their_centers",
		),
	},
	"interface": {"title": "OneInterface pass", "guards": ()},
	"setup": {"title": "Setup steps", "guards": (READY + "test_a_module_says_what_setting_it_up_takes",)},
	"tour": {"title": "Tour", "guards": (READY + "test_a_module_ships_a_tour_of_its_screen",)},
	"settings": {"title": "Settings", "guards": (READY + "test_a_module_has_one_settings_dialog_and_one_foot",)},
	"legal": {
		"title": "Legal",
		"guards": (
			READY + "test_a_change_to_what_a_module_agrees_on_is_said",
			"tests/guards/test_legal.py::test_every_modules_legal_file_is_assembled",
		),
	},
}

# The points a guard holds only in part, and what a person looks at: before
# a module is marked ready, and again after a version that adds to it.
HAND = {
	"copy": "every heading, description and message it shows reads as the copy rules say, in English, Arabic and German",
	"demo": "the demo company uses every part of it and nothing in the demo makes it look wrong",
	"notifications": "it tells people what they need, on the channels that make sense, only to the roles that should hear it",
	"interface": "each screen, as each role, on a desktop and a phone: tokens only, frappe's controls, live where data changes, and the reader's formats",
	"legal": "what it does with data, read against what its clauses, subprocessors and optional services say",
}

# Files named for a module, or in its places, that are not its own, and why.
# A path ending in / is a whole folder. A module's files leave them out, so
# its version moves only with what is its own.
_ENGINE = "an engine every module uses, kept in One's folder"
_RAN = "OnePortal's, a patch that has run, kept at the path frappe recorded it under"
SHARED = {
	"brand/onemail.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/oneadmin.svg": "every product's mark is drawn in brand/, into one sprite",
	"frontend/src/islands/oneadmin.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_billing.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_releases.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_server_part.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_servers.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_sessions.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_status.js": "the islands build takes its entries from one folder",
	"brand/oneinventory.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onefactory.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onequality.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onecrm.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onehr.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_crm/business-card.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/business-card.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-ar.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-ar.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-de.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-de.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/order-from-lead.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/order-from-lead.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/cv.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/cv.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/sick-note.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/sick-note.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/signed-contract.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/signed-contract.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt-doubted.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt-doubted.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt.json": "reading's samples sit with every module's, under tests/samples",
	"brand/onebook.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_inventory/coating-bill.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/coating-bill.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/delivery-note.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/delivery-note.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/supplier-quote.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/supplier-quote.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/bank-statement-2026-10-06.xml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/bank-statement.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/new-supplier-invoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/new-supplier-invoice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/payment-advice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/payment-advice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/supplier-einvoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/supplier-einvoice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/transport-contract.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/transport-contract.json": "reading's samples sit with every module's, under tests/samples",
	"brand/oneportal.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onecalendar.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onedisplay.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/oneslide.svg": "every product's mark is drawn in brand/, into one sprite",
	"docs/ONESLIDE.md": "the plan that made OneSlide and moved OneDisplay's slides into it, across both modules",
	"brand/onedoc.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onesheet.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_calendar/site-meeting.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_calendar/site-meeting.json": "reading's samples sit with every module's, under tests/samples",
	"brand/onetask.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_task/drawings-request.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_task/drawings-request.json": "reading's samples sit with every module's, under tests/samples",
	"brand/oneproject.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_project/extra-work-request.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/extra-work-request.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/scaffolding-bill.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/scaffolding-bill.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/site-log.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/site-log.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/subcontractor-timesheet.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/subcontractor-timesheet.json": "reading's samples sit with every module's, under tests/samples",
	"onedesk/templates/emails/one_mail.html": "the frame every mail One sends is laid in, OneMail's or not",
	"brand/oneai.svg": "every product's mark is drawn in brand/, into one sprite",
	"onedesk/public/images/oneai.svg": "the mark as an image, for the places that can't use the sprite",
	"onedesk/one_mail/docs/asking-oneai.md": "OneMail's own Help page on what OneAI does in mail",
	"onedesk/one_mail/docs/asking-oneai/reading.png": "the picture on OneMail's page on OneAI",
	"tests/samples/intake/one_ai/ignore-instructions.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/ignore-instructions.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/locked-invoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/locked-invoice.json": "reading's samples sit with every module's, under tests/samples",
	# The engines every module uses (docs/ONE.md, What One keeps).
	"onedesk/one/rights.py": _ENGINE + ": what a role may do in each module (docs/ROLES.md)",
	"onedesk/one/roles.py": _ENGINE + ": who administers the workspace",
	"onedesk/one/notify.py": _ENGINE + ": every notification goes through it",
	"onedesk/one/push.py": _ENGINE + ": every notification's push",
	"onedesk/one/doctype/push_device/": _ENGINE + ": the devices a push goes to",
	"onedesk/one/tell.py": _ENGINE + ": what every module tells people about the workspace goes through it",
	"onedesk/one/account.py": _ENGINE + ": every module asks the account through it",
	"onedesk/one/apps.py": _ENGINE + ": which apps the workspace has turned off, which every module asks",
	"onedesk/one/people.py": _ENGINE + ": the apps every person is given, which every module asks",
	"onedesk/one/head.py": _ENGINE + ": the record head every module's records wear",
	"onedesk/one/stages.py": _ENGINE + ": the record head's stages",
	"onedesk/one/figures.py": _ENGINE + ": the record head's figures",
	"onedesk/one/linked.py": _ENGINE + ": another record's fields edited on this one",
	"onedesk/one/tabs.py": _ENGINE + ": a record's tabs after its fields",
	"onedesk/one/homes.py": _ENGINE + ": where every module's record leads back to",
	"onedesk/one/doctype/record_head/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_band/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_chart/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_indicator/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_linked/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_sentence/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_verb/": _ENGINE + ": the record head",
	"onedesk/one/layer.py": _ENGINE + ": what a workspace may change about any module's forms",
	"onedesk/one/babel.py": _ENGINE + ": every module's standard records in the reader's language",
	"onedesk/one/doctype/workspace_customization/": _ENGINE + ": the workspace layer",
	"onedesk/one/boards.py": _ENGINE + ": the board every module's boards open in",
	"onedesk/one/sections.py": _ENGINE + ": what every centre's section is drawn from and saved to",
	"onedesk/one/print_format_field_template/": _ENGINE + ": the blocks every module's print formats are made of",
	"onedesk/one/ready.py": _ENGINE + ": the READY mechanisms (docs/READY.md)",
	"onedesk/one/versions.py": _ENGINE + ": the READY mechanisms, What's New",
	"onedesk/one/tours.py": _ENGINE + ": the READY mechanisms, tours",
	"onedesk/one/setup_steps.py": _ENGINE + ": the READY mechanisms, setup steps",
	"onedesk/one/setup_wizard.py": _ENGINE + ": the first run, which sets every module up",
	# What is in One's folder on its way to the module it belongs to.
	"onedesk/one/patches/portal_account_forms.py": _RAN,
	"onedesk/one/patches/portal_address_button.py": _RAN,
	"onedesk/one/patches/portal_own_by_record.py": _RAN,
	"onedesk/one/patches/portal_settle.py": _RAN,
	"onedesk/one/privacy.py": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/privacy_copy.py": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/privacy_public.py": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/custom/personal_data_deletion_request.json": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/custom/personal_data_download_request.json": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/webhooks.py": "OneStudio's Webhooks, to move into one_studio",
	"onedesk/one/patches/holiday_names.py": "OneHR's holidays, a patch that has run",
}


def shared(path: str) -> bool:
	"""Whether a path, from the repository's root, is in SHARED."""
	return path in SHARED or any(key.endswith("/") and path.startswith(key) for key in SHARED)


OUTSIDE = {
	"OneInterface": [],
	"OneCRM": [],
	"OneHR": [],
	"OneMail": [],
	"One": [],
	"OneAI": [],
	"OneLegal": [],
	"OneAccount": [],
	"OnePortal": [],
	"OneInventory": [],
	"OneBook": [],
	"OneDisplay": [],
	"OneSlide": [],
	"OneWriter": [],
	"OneWorkbook": [],
}


def files(module: str) -> list[Path]:
	"""Every file of a module: its folder, its static files, its screens, and
	what still sits outside."""
	found = []
	for root in places(module):
		if root.exists():
			found += [path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
	found = [path for path in found if not shared(str(path.relative_to(ROOT)))]
	found += [ROOT / one for one in OUTSIDE.get(module, [])]
	return sorted(found)


def places(module: str) -> list[Path]:
	"""Where a module's files may be: its folder, its static folders and its
	screens."""
	spec = MODULES[module]
	return [
		APP / spec["folder"],
		APP / "public" / "js" / spec["folder"],
		APP / "public" / "css" / spec["folder"],
		APP / "public" / "images" / spec["folder"],
		ROOT / "frontend" / "src" / spec["screens"],
	] + ([ROOT / "frontend" / spec["app"]] if spec.get("app") else [])


# What a version is taken over: what the module ships and its help pages,
# not what only we read or run (its notes, versions, tests, checks, demo, and
# the passover's stamps, which only a dev site shows).
UNSHIPPED = ("AGENTS.md", "SCRATCHPAD.md", "checks.py", "demo.py", "stamps.py")
KINDS = ("major", "minor", "fix")
HEAD = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def shipped(module: str) -> list[Path]:
	"""The files a module's version is taken over."""
	return [
		path
		for path in files(module)
		if path.name not in UNSHIPPED
		and "tests" not in path.parts
		and "changelog" not in path.parts
		and path.suffix not in (".pyc",)
	]


def fingerprint(module: str) -> str:
	"""Twelve hex characters over every shipped file's path and bytes, so it
	moves with any change to the module and nothing else."""
	digest = hashlib.sha256()
	for path in shipped(module):
		digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes() + b"\0")
	return digest.hexdigest()[:12]


def changelog(module: str) -> Path:
	return APP / MODULES[module]["folder"] / "docs" / "changelog"


def number(version: str) -> tuple[int, int, int]:
	major, minor, fix = (int(one) for one in version.split("."))
	return major, minor, fix


def versions(module: str) -> list[dict]:
	"""Every version of a module, newest first: its front matter (version,
	date, kind, title, fingerprint) and its words, read from
	docs/changelog/<version>.md."""
	found = []
	for path in changelog(module).glob("*.md"):
		text = path.read_text(encoding="utf-8")
		head = HEAD.match(text)
		if not head:
			raise ValueError(f"{path} has no front matter")
		said = dict(line.split(": ", 1) for line in head.group(1).splitlines())
		said["docs"] = [one.strip() for one in said.get("docs", "").split(",") if one.strip()]
		found.append({**said, "version": path.stem, "body": text[head.end() :].strip(), "path": path})
	return sorted(found, key=lambda one: number(one["version"]), reverse=True)


def legal(module: str) -> str:
	"""What a module agrees on, as a version of it records it
	(one_legal/assemble.py `stamp`)."""
	from onedesk.one_legal import assemble

	return assemble.stamp(module)


def current(module: str) -> str | None:
	"""A module's version: its newest changelog entry's."""
	found = versions(module)
	return found[0]["version"] if found else None


def help_pages(module: str) -> list[dict]:
	"""A module's help pages in reading order: id, icon, title (its first
	heading), the rest of its words, and where it is, which its pictures sit
	beside."""
	folder = APP / MODULES[module]["folder"] / "docs"
	found = []
	for page, icon in MODULES[module].get("help", ()):
		text = (folder / f"{page}.md").read_text(encoding="utf-8")
		title, _, body = text.partition("\n")
		found.append(
			{"id": page, "icon": icon, "title": title.lstrip("# ").strip(), "body": body.strip(), "path": folder / f"{page}.md"}
		)
	return found


def registry(module: str) -> list[dict]:
	"""Where a module stands on each point: the guards that hold it, and, for
	a point a person must look at, when they last did."""
	checked = MODULES[module].get("checked", {})
	return [
		{
			"point": key,
			"title": point["title"],
			"guards": point["guards"],
			"look": HAND.get(key),
			"checked": checked.get(key),
		}
		for key, point in POINTS.items()
	]


INTERFACE_KEYS = {"tabs", "fields", "cards", "track", "states", "links"}


def _states(said: dict | None) -> dict:
	"""The list's strip: the field it counts, its values in the order the
	strip shows them (the rest after, by count) and those it leaves out.
	Undeclared, the strip counts `status`, by count. A record type whose
	kinds are no one field's values names them as `kinds` instead, each a
	label and its filters ([field, operator, value]), counted in that order."""
	said = said or {}
	strange = set(said) - {"field", "order", "hide", "kinds"}
	if strange:
		raise ValueError(f"a strip declares {sorted(strange)}")
	kinds = []
	for one in said.get("kinds") or ():
		if set(one) != {"label", "filters"} or not one["filters"]:
			raise ValueError(f"a strip's kind says a label and its filters: {one}")
		kinds.append({"label": str(one["label"]), "filters": [list(rule) for rule in one["filters"]]})
	return {"field": said.get("field", "status"), "order": list(said.get("order") or ()), "hide": list(said.get("hide") or ()), "kinds": kinds}


LINK_KEYS = {"label", "icon", "new", "list", "open", "with", "when"}


def _link(said: dict) -> dict:
	"""A record's shortcut: a new record of `new`, the list of `list`, or
	the record this one's `open` field names, with `with` (the other type's
	field: this record's field) carried over, shown while every `when`
	([field, "=" | "!=" | "in", value]) holds."""
	strange = set(said) - LINK_KEYS
	if strange or not said.get("label") or sum(bool(said.get(one)) for one in ("new", "list", "open")) != 1:
		raise ValueError(f"a link must say a label and one of new, list or open: {said}")
	return {
		"label": str(said["label"]),
		"icon": said.get("icon") or "arrow-up-right",
		"new": said.get("new"),
		"list": said.get("list"),
		"open": said.get("open"),
		"with": dict(said.get("with") or {}),
		"when": [list(one) for one in said.get("when") or ()],
	}


def interface() -> dict:
	"""How each record type is drawn, as every module declares it under
	"interface": icons for its tabs and fields, at most four head cards, the
	row whose steps are its track and the states its list's strip counts. The renderer reads this and nothing
	else; a record type is declared by one module only."""
	found = {}
	for module, one in MODULES.items():
		for doctype, said in (one.get("interface") or {}).items():
			strange = set(said) - INTERFACE_KEYS
			if strange:
				raise ValueError(f"{module} declares {sorted(strange)} for {doctype}")
			if doctype in found:
				raise ValueError(f"{doctype} is declared by {found[doctype]['module']} and {module}")
			if len(said.get("cards") or ()) > 4:
				raise ValueError(f"{module} gives {doctype} more than four head cards")
			found[doctype] = {
				"module": module,
				"tabs": dict(said.get("tabs") or {}),
				"fields": dict(said.get("fields") or {}),
				"cards": [{**card, "title": str(card["title"])} if card.get("title") else dict(card) for card in said.get("cards") or ()],
				"track": said.get("track"),
				"states": _states(said.get("states")),
				"links": [_link(one) for one in said.get("links") or ()],
			}
	return found

