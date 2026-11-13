"""A costing workbook in the company's files: the rates behind the Bayview
tower quotation, worked out in a grid, with a second sheet for labour. Shared
with Karim, so two people can work on it at once."""

import json

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_sheet import api, storage

OWNER = "wsadmin@one.test"
CHECKER = "karim@one.test"
NAME = "bayview-costing"
TITLE = "Bayview tower costing"

MATERIALS = [
	["Item", "Qty", "Unit", "Rate", "Amount"],
	["Curtain wall glazing", "420", "m2", "385", "=B2*D2"],
	["Aluminium mullions", "1260", "m", "42", "=B3*D3"],
	["Structural silicone", "310", "tube", "18.5", "=B4*D4"],
	["Brackets and anchors", "980", "pc", "6.75", "=B5*D5"],
	["", "", "", "Materials", "=SUM(E2:E5)"],
	["", "", "", "Labour", "=Labour!D5"],
	["", "", "", "Total", "=E6+E7"],
]

LABOUR = [
	["Crew", "Days", "Day rate", "Amount"],
	["Installers (6)", "45", "1650", "=B2*C2"],
	["Crane and operator", "12", "2400", "=B3*C3"],
	["Site supervision", "45", "450", "=B4*C4"],
	["", "", "Labour", "=SUM(D2:D4)"],
]


def _packed(rows: list[list[str]]) -> dict:
	return {"rows": {str(at): [one or None for one in row] for at, row in enumerate(rows)}}


def run(password=None):
	if not frappe.db.exists(api.WORKBOOK, NAME):
		_make()
	file = frappe.db.get_value(api.WORKBOOK, NAME, "file")
	if frappe.db.exists("User", CHECKER) and not frappe.db.exists("DocShare", {"share_doctype": "File", "share_name": file, "user": CHECKER}):
		frappe.share.add_docshare("File", file, CHECKER, read=1, write=1, notify=0, flags={"ignore_share_permission": True})


def _make():
	from onedesk.one_cloud import namespace as ns

	content = {"sheet": {"v": 2, "current": "Materials", "sheets": {"Materials": _packed(MATERIALS), "Labour": _packed(LABOUR)}}}
	with as_user(OWNER):
		book = frappe.get_doc({"doctype": api.WORKBOOK, "title": TITLE, "sheets_data": storage.encode_sheets_data(json.dumps(content))})
		book.flags.ignore_permissions = True
		book.insert(set_name=NAME)
		file = frappe.get_doc({"doctype": "File", "file_url": api.URL + NAME, "is_private": 1, "folder": ns.HOME, "file_name": TITLE})
		file.flags.ignore_permissions = True
		file.insert()
		book.db_set("file", file.name)
