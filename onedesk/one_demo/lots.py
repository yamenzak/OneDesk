"""Lots with a shelf life: Weatherproof Silicone Sealant keeps twelve months
from the day it was made. Two lots were bought from Emirates Sealants &
Fixings, one in January that runs out of date within the month and is still
partly in the Stores, and one in August. Some of the old lot went to the
Mansour villa, so a lot's page says where it came from and where it went.
And pieces kept by number: six smart locks from Euro Hardware Trading, each
with its own serial number and a two-year warranty."""

import frappe
from frappe.utils import add_days

from onedesk.one_demo.base import COMPANY, ago, ahead, as_user, dated, on, save, today, wh

ITEM = "SIL-WP"
SUPPLIER = "Emirates Sealants & Fixings"
BUYER = "karim@one.test"

LOTS = (
	("SIL-WP-A1", ago(341), ahead(24), on(1, 12), 120, 38),
	("SIL-WP-B2", ago(55), ahead(310), ago(48), 80, 39.5),
)

SENT = 70

LOCK = "HW-SMART"
LOCKS = ("Euro Hardware Trading", [f"SL-{n:04d}" for n in range(1, 7)], ago(30), 105)


def run(password=None):
	if not frappe.db.get_single_value("Stock Settings", "enable_serial_and_batch_no_for_item"):
		settings = frappe.get_doc("Stock Settings")
		settings.enable_serial_and_batch_no_for_item = 1
		settings.save()
	_item()
	for lot in LOTS:
		_lot(*lot)
	_sent()
	_locks()


def _item():
	if frappe.db.exists("Item", ITEM):
		return
	with as_user(BUYER):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": ITEM,
				"item_name": "Weatherproof Silicone Sealant",
				"item_group": "Consumable",
				"stock_uom": "Nos",
				"description": "<p>Neutral cure weatherproof silicone, 300 ml cartridge, grey.</p>",
				"is_stock_item": 1,
				"is_purchase_item": 1,
				"has_batch_no": 1,
				"has_expiry_date": 1,
				"shelf_life_in_days": 365,
				"item_defaults": [{"company": COMPANY, "default_warehouse": wh("Stores")}],
			}
		).insert()


def _lot(batch, made, expires, received, qty, rate):
	if frappe.db.exists("Batch", {"batch_id": batch, "item": ITEM}):
		return
	with as_user(BUYER):
		lot = frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_id": batch,
				"item": ITEM,
				"manufacturing_date": made,
				"expiry_date": expires,
				"supplier": SUPPLIER,
			}
		).insert()
		receipt = frappe.new_doc("Purchase Receipt")
		receipt.supplier = SUPPLIER
		receipt.company = COMPANY
		dated(receipt, received)
		receipt.append(
			"items",
			{
				"item_code": ITEM,
				"qty": qty,
				"rate": rate,
				"warehouse": wh("Stores"),
				"use_serial_batch_fields": 1,
				"batch_no": lot.name,
			},
		)
		save(receipt, submit=True)


def _sent():
	"""The old lot's cartridges taken to the Mansour villa's site."""
	old = frappe.db.get_value("Batch", {"batch_id": LOTS[0][0], "item": ITEM})
	if not old or frappe.db.exists("Serial and Batch Entry", {"batch_no": old, "qty": ["<", 0], "docstatus": 1}):
		return
	site = wh("Mansour Villa Site")
	if not frappe.db.exists("Warehouse", site):
		return
	with as_user(BUYER):
		move = frappe.new_doc("Stock Entry")
		move.stock_entry_type = "Material Transfer"
		move.company = COMPANY
		dated(move, min(add_days(LOTS[0][3], 60), today()))
		move.append(
			"items",
			{
				"item_code": ITEM,
				"qty": SENT,
				"s_warehouse": wh("Stores"),
				"t_warehouse": site,
				"use_serial_batch_fields": 1,
				"batch_no": old,
			},
		)
		save(move, submit=True)


def _locks():
	"""Six smart locks, each with its serial number, received into the Stores."""
	supplier, numbers, received, rate = LOCKS
	if frappe.db.exists("Serial No", numbers[0]) or not frappe.db.exists("Supplier", supplier):
		return
	with as_user(BUYER):
		if not frappe.db.exists("Item", LOCK):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": LOCK,
					"item_name": "Smart Lock 500",
					"item_group": "Hardware" if frappe.db.exists("Item Group", "Hardware") else "Raw Material",
					"stock_uom": "Nos",
					"description": "<p>Keypad and fingerprint lock for aluminium doors.</p>",
					"is_stock_item": 1,
					"is_purchase_item": 1,
					"has_serial_no": 1,
					"serial_no_series": "SL-.####",
					"warranty_period": 730,
					"item_defaults": [{"company": COMPANY, "default_warehouse": wh("Stores")}],
				}
			).insert()
		receipt = frappe.new_doc("Purchase Receipt")
		receipt.supplier = supplier
		receipt.company = COMPANY
		receipt.currency = "EUR"
		dated(receipt, received)
		receipt.append(
			"items",
			{
				"item_code": LOCK,
				"qty": len(numbers),
				"rate": rate,
				"warehouse": wh("Stores"),
				"use_serial_batch_fields": 1,
				"serial_no": "\n".join(numbers),
			},
		)
		save(receipt, submit=True)
