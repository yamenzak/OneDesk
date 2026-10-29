"""ERPNext's Stock, Buying, Manufacturing and Asset dashboards, which the
rail's Overview rows open, corrected where they say something untrue, after
every sync and migrate. What each correction is for is in AGENTS.md."""

import json

import erpnext
import frappe

THIS_MONTH = ["creation", "Timespan", "this month"]

CARDS = {
	"Total Active Items": {"show_percentage_stats": 0},
	"Total Warehouses": {"show_percentage_stats": 0},
	"Active Suppliers": {"show_percentage_stats": 0},
	"Total Assets": {"show_percentage_stats": 0},
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
	"Monthly Quality Inspection": {
		"show_percentage_stats": 0,
		"filters_json": [["Quality Inspection", "docstatus", "=", 1], ["Quality Inspection", *THIS_MONTH]],
	},
}

IN_MONEY = ("Total Stock Value", "Asset Value", "Annual Purchase")

YEAR = {
	"from_date": 'frappe.defaults.get_user_default("year_start_date")',
	"to_date": 'frappe.defaults.get_user_default("year_end_date")',
}

CHARTS = {
	"Asset Value Analytics": {
		"filters_json": {"status": "In Location", "filter_based_on": "--Select a period--", "group_by": "--Select a group--"},
		"dynamic_filters_json": {"company": 'frappe.defaults.get_user_default("Company")'},
	},
	"Quality Inspection Analysis": {"filters_json": {}, "dynamic_filters_json": YEAR},
	"Last Month Downtime Analysis": {
		"filters_json": {},
		"dynamic_filters_json": {
			"from_date": "frappe.datetime.add_months(frappe.datetime.nowdate(), -1)",
			"to_date": "frappe.datetime.nowdate()",
		},
	},
}


def settle() -> None:
	company = erpnext.get_default_company()
	currency = erpnext.get_company_currency(company) if company else None
	for name, said in CARDS.items():
		_set("Number Card", name, said)
	if currency:
		for name in IN_MONEY:
			_set("Number Card", name, {"currency": currency})
	for name, said in CHARTS.items():
		_set("Dashboard Chart", name, said)


def _set(doctype: str, name: str, said: dict) -> None:
	if not frappe.db.exists(doctype, name):
		return
	values = {key: json.dumps(value) if isinstance(value, list | dict) else value for key, value in said.items()}
	frappe.db.set_value(doctype, name, values, update_modified=False)
