"""ERPNext's Manufacturing dashboard, which the rail's Overview opens,
corrected where it says something untrue, after every sync and migrate: a
month's work orders counted from the first of the month, not ERPNext's
rolling figure with a percentage nobody reads, and the downtime chart over
the last month."""

import json

import frappe

THIS_MONTH = ["creation", "Timespan", "this month"]

CARDS = {
	"Monthly Total Work Order": {
		"show_percentage_stats": 0,
		"filters_json": [["Work Order", "docstatus", "=", 1], ["Work Order", *THIS_MONTH]],
	},
	"Monthly Completed Work Order": {
		"show_percentage_stats": 0,
		"filters_json": [
			["Work Order", "status", "=", "Completed"],
			["Work Order", "docstatus", "=", 1],
			["Work Order", *THIS_MONTH],
		],
	},
}

CHARTS = {
	"Last Month Downtime Analysis": {
		"filters_json": {},
		"dynamic_filters_json": {
			"from_date": "frappe.datetime.add_months(frappe.datetime.nowdate(), -1)",
			"to_date": "frappe.datetime.nowdate()",
		},
	},
}


def settle() -> None:
	for name, said in CARDS.items():
		_set("Number Card", name, said)
	for name, said in CHARTS.items():
		_set("Dashboard Chart", name, said)


def _set(doctype: str, name: str, said: dict) -> None:
	if not frappe.db.exists(doctype, name):
		return
	values = {key: json.dumps(value) if isinstance(value, list | dict) else value for key, value in said.items()}
	frappe.db.set_value(doctype, name, values, update_modified=False)
