"""A channel that showed one queue becomes a channel with a widget collection
holding a queue board and a ticker, and a screen that was a kiosk shows a
kiosk channel of its own (one_display/AGENTS.md, stage 4)."""

import json

import frappe


def execute():
	if not frappe.db.has_column("Display Channel", "queue"):
		return
	for old in frappe.db.sql(
		"select name, queue, headline, ticker from `tabDisplay Channel` where ifnull(queue, '') != ''", as_dict=True
	):
		source = _source(old.queue)
		widgets = [
			{
				"widget_type": "Queue Board",
				"source": source,
				"x": 0,
				"y": 0,
				"w": 100,
				"h": 92 if old.ticker else 100,
				"settings": json.dumps({"heading": old.headline} if old.headline else {}),
			}
		]
		if old.ticker:
			widgets.append({"widget_type": "Ticker", "x": 0, "y": 92, "w": 100, "h": 8, "settings": json.dumps({"text": old.ticker})})
		frappe.db.set_value("Display Channel", old.name, "widget_collection", _collection(old.name, widgets))
		if frappe.db.has_column("Display Screen", "mode"):
			kiosks = frappe.db.sql(
				"select name from `tabDisplay Screen` where channel=%s and mode='Kiosk'", old.name, pluck="name"
			)
			if kiosks:
				kiosk = _collection(f"{old.name} Kiosk", [{"widget_type": "Kiosk", "source": source, "x": 0, "y": 0, "w": 100, "h": 100}])
				channel = f"{old.name} Kiosk"
				if not frappe.db.exists("Display Channel", channel):
					frappe.get_doc({"doctype": "Display Channel", "channel_name": channel, "widget_collection": kiosk}).insert(
						ignore_permissions=True
					)
				for screen in kiosks:
					frappe.db.set_value("Display Screen", screen, "channel", channel, update_modified=False)


def _source(queue: str) -> str:
	name = f"{queue} Queue"
	if not frappe.db.exists("Display Source", name):
		frappe.get_doc({"doctype": "Display Source", "source_name": name, "kind": "Queue", "queue": queue}).insert(
			ignore_permissions=True
		)
	return name


def _collection(name: str, widgets: list[dict]) -> str:
	if not frappe.db.exists("Widget Collection", name):
		frappe.get_doc({"doctype": "Widget Collection", "collection_name": name, "widgets": widgets}).insert(
			ignore_permissions=True
		)
	return name
