"""OneFactory's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Roles, _lt

APP = App(
	id="one_factory",
	name="OneFactory",
	kind="app",
	module="One Factory",
	line=_lt("Plan what you make, run it on the shop floor, and send work out to suppliers."),
	mark="onefactory",
	owns=("Manufacturing", "Subcontracting"),
	rail=60,
	sidebar="OneFactory",
	roles=Roles(user=("Manufacturing User",), manager=("Manufacturing Manager",)),
	screens="factory",
	names=("one_factory", "onefactory"),
	help=(
		("overview", "info"),
		("work-orders-and-the-floor", "hard-hat"),
		("bills-of-materials", "list-tree"),
		("work-sent-to-suppliers", "send"),
		("notifications", "bell"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": False,
	},
	companies=(
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
	interface={
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
)
