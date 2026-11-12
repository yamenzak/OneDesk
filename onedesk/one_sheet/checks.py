"""OneWorkbook's part of the integration suite (one_demo/check.py runs it):
a workbook made, saved, versioned, copied and printed in OneCloud; an Excel
or CSV file edited in place and a workbook read as Excel on the drive; a
record's table edited as a sheet; templates; and OneAI's cards on a
workbook, with nothing sent to a model."""

import json

import frappe
from frappe.utils import flt

from onedesk.one_demo.base import COMPANY, as_user
from onedesk.one_demo.check import check
from onedesk.one_demo.people import OWNER


@check
def onecloud_holds_a_workbook_with_its_history():
	"""Layla makes a workbook in her files from OneCloud, saves it twice with
	an edit to B2, renames it, and finds both saves in its history and B2's
	before and after. Rania can't open it. A copy of the first version is a
	workbook of its own; restoring that version brings 100 back; deleting
	the File takes the workbook and its history with it."""
	from onedesk.one_sheet import ai as sheet_ai
	from onedesk.one_sheet import api, live, versions

	def held(value):
		return json.dumps({"sheet": {"v": 2, "current": "Sheet1", "sheets": {"Sheet1": {"rows": {"1": [None, value]}}}}})

	with as_user(OWNER):
		made = api.make("@my", "Glazing rates")
		book = made["workbook"]
		assert made["name"] == "Glazing rates" and api.workbook_of(made["url"]) == book
		assert api.get_sheet(book)["can_write"]
		api.save_sheet("Glazing rates", held("100"), book, json.dumps([{"op_type": "setCell", "sub_sheet": "Sheet1", "cell_refs": ["B2"], "before": {"B2": None}, "after": {"B2": "100"}}]), "r1")
		assert api.save_sheet("Glazing rates", held("100"), book, "", "r1")["head_seq"] == 2, "a save sent twice is kept once"
		frappe.db.set_value(versions.VERSION, {"workbook": book}, "creation", frappe.utils.add_to_date(None, minutes=-5))
		api.save_sheet("Glazing rates 2026", held("120"), book, json.dumps([{"op_type": "setCell", "sub_sheet": "Sheet1", "cell_refs": ["B2"], "before": {"B2": "100"}, "after": {"B2": "120"}}]), "r2")
		assert frappe.db.get_value("File", made["id"], "file_name") == "Glazing rates 2026"
		assert api.rename_sheet(book, "Glazing rates")["title"] == "Glazing rates"
		told = versions.timeline(book)["buckets"]["earlier"]["items"]
		assert len(told) == 2 and told[0]["seq"] > told[1]["seq"], told
		assert [(one["before"], one["after"]) for one in versions.ops_for_cell(book, "B2", "Sheet1")] == [("100", "120"), (None, "100")]
		first = told[-1]["id"]
		assert '"100"' in versions.state_at(first)["sheets_data"]
		assert versions.label_snapshot(first, "Before the discount")["pinned"]
		assert versions.timeline(book)["buckets"]["pinned"]["items"][0]["label"] == "Before the discount"
		copy = versions.make_copy(first, "Glazing rates, first")
		assert '"100"' in api.get_sheet(copy)["sheets_data"]
		versions.restore(first)
		assert '"100"' in api.get_sheet(book)["sheets_data"]
		assert api.get_link_preview("https://example.com") == {"url": "https://example.com"}
		api.download(book)
		assert frappe.local.response["location"] == f"/desk/workbook/{book}"
		admitted = live.admit("workbook", book)
		assert admitted["ok"] and admitted["write"] and admitted["who"]["user"] == OWNER, admitted
		told = sheet_ai.page({"page": "workbook", "record": book, "selection": {"page": "workbook", "workbook": book, "sheet": "Sheet1", "range": "B2:B2", "active": "B2"}})
		assert "Sheet1 with B2:B2 selected" in told and '"B2": "100"' in told, "OneAI is told the workbook and what is selected"
	with as_user("rania@one.test"):
		try:
			api.get_sheet(book)
			raise AssertionError("Rania opened Layla's workbook")
		except frappe.PermissionError:
			pass
		assert live.admit("workbook", book) == {"ok": False}, "nor joins its room"
		assert live.admit("file", book) == {"ok": False}
	for one in (made["id"], frappe.db.get_value(api.WORKBOOK, copy, "file")):
		frappe.delete_doc("File", one, ignore_permissions=True, force=True)
	assert not frappe.db.exists(api.WORKBOOK, book) and not frappe.db.exists(versions.VERSION, {"workbook": book})


@check
def a_table_keeps_its_formulas():
	"""Layla types a formula under a quotation's items that reads a Costing
	sheet; drawing the table again after a change on the form keeps it. She
	saves the workbook as a template: it keeps the Costing sheet and leaves
	the table out, and it starts a plain workbook like any other template.
	Karim keeps no template until he is a Manager. All of it is undone
	afterwards."""
	from onedesk.one_sheet import api, storage, table, templates

	def first_sheet(book):
		held = table._held(book)
		return table.stored(json.loads(storage.decode_sheets_data(held.sheets_data)), held.bound_sheet)

	quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
	frappe.db.savepoint("template_check")
	try:
		with as_user(OWNER):
			book = table.open_table("Quotation", quote, "items")
			held = table._held(book)
			data = json.loads(storage.decode_sheets_data(held.sheets_data))
			rows = table.stored(data, held.bound_sheet)
			qty = rows["0"].index("Quantity")
			rows["1"][qty] = "=Costing!C4:C"
			data["sheet"]["sheets"]["Costing"] = {"rows": {"3": ["CW01", "Wall", "10"]}}
			frappe.db.set_value(api.WORKBOOK, book, "sheets_data", storage.encode_sheets_data(json.dumps(data)))
			child = frappe.get_doc("Quotation", quote).items[0]
			frappe.db.set_value(child.doctype, child.name, "qty", flt(child.qty) + 1)
			was = first_sheet(book)["0"][0]
			table.refresh(book)
			assert first_sheet(book)["0"][0] != was, "drawn again"
			assert first_sheet(book)["1"][qty] == "=Costing!C4:C", "and the formula stays"
			made = templates.save_as(book, "Glazing costing")
			kept = json.loads(storage.decode_sheets_data(frappe.db.get_value(api.WORKBOOK, made["name"], "sheets_data")))
			assert list(kept["sheet"]["sheets"]) == ["Costing"], "a template is its own sheets, not the record's table"
			assert templates.sheets_of(made["name"]) == [{"name": "Costing", "cells": {"A4": "CW01", "B4": "Wall", "C4": "10"}}]
			assert {"name": made["name"], "title": "Glazing costing"} in templates.listed()
			copy = api.make("@my", "Glazing for Bayview", made["name"])
			assert copy["workbook"] != book
		with as_user("karim@one.test"):
			his = api.make("@my", "Template check")["workbook"]
			assert not api.get_sheet(his)["can_template"], "a User keeps no company templates"
			try:
				templates.save_as(his, "Not a template")
				raise AssertionError("a User kept a company template")
			except frappe.PermissionError:
				frappe.clear_messages()
			karim = frappe.get_doc("User", "karim@one.test")
			karim.flags.ignore_permissions = True
			karim.add_roles("OneWorkbook Manager")
			assert api.get_sheet(his)["can_template"], "a Manager keeps them"
			assert not frappe.has_permission(api.WORKBOOK, "read"), "keeping templates opens no workbook the File doesn't"
			kept = templates.save_as(his, "His template")
			assert {"name": kept["name"], "title": "His template"} in templates.listed(), "a template OneCloud offers"
			try:
				api.get_sheet(book)
				raise AssertionError("a Manager opened a workbook its File doesn't give him")
			except frappe.PermissionError:
				frappe.clear_messages()
	finally:
		frappe.db.rollback(save_point="template_check")


@check
def oneai_makes_reads_and_writes_a_workbook():
	"""OneAI suggests a workbook with a formula and a bold header, and on
	approval it is made in OneCloud; it finds and reads it, writes a cell
	and a note as cards, and refuses a record's table sheet and a name that
	isn't a cell. All undone afterwards."""
	from onedesk.one_ai import proposals, tools
	from onedesk.one_sheet import ai

	frappe.db.savepoint("oneai_sheet_check")
	try:
		with as_user(OWNER):
			said = tools.run("draft_workbook", {"name": "Glass check", "sheets": [{"name": "Prices", "cells": {"A1": "Item", "B1": "Rate", "A2": "Clear 8mm", "B2": 60, "B3": "=B2*1.05"}, "looks": {"A1:B1": {"bold": True}}}]})
			assert not said["ran"] and said["answer"]["state"] == "Proposed", said
			book = proposals.apply(said["answer"]["proposal"])["record"]
			assert "at least one sheet" in ai.draft_workbook("Empty check", [])["error"]
			found = ai.my_workbooks("Glass check")
			assert [one["workbook"] for one in found] == [book] and found[0]["sheets"] == ["Prices"], found
			read = ai.read_workbook(book)
			assert read["cells"] == {"A1": "Item", "B1": "Rate", "A2": "Clear 8mm", "B2": 60, "B3": "=B2*1.05"}, read
			wrote = ai.write_cells(book, "Prices", {"B2": 65}, {"B2:B3": {"numberFormat": "number:us:2"}})
			proposals.apply(wrote["proposal"])
			note = ai.comment_on_cell(book, "Prices", "B2", "Up from 60 this month.")
			proposals.apply(note["proposal"])
			read = tools.run("read_workbook", {"workbook": book, "cells": "B2:B3"})["answer"]
			assert read["cells"] == {"B2": 65, "B3": "=B2*1.05"} and read["notes"] == {"B2": "Up from 60 this month."}, read
			assert "isn't a cell" in tools.run("write_cells", {"workbook": book, "sheet": "Prices", "cells": {"row 3": 1}})["answer"]["error"]
			quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
			from onedesk.one_sheet import table

			bound = table.open_table("Quotation", quote, "items")
			assert "record's table" in tools.run("write_cells", {"workbook": bound, "sheet": "Items", "cells": {"B2": "x"}})["answer"]["error"]
	finally:
		frappe.db.rollback(save_point="oneai_sheet_check")


@check
def a_spreadsheet_file_opens_and_saves_back_into_itself():
	"""A CSV in OneCloud opens as a workbook that reads it in the first time,
	what is done to it is written back into the same File, what it held
	before kept as a version, and a new version put in from outside is read
	in again. All undone afterwards."""
	import base64

	from onedesk.one_sheet import api
	from onedesk.one_storage import namespace as ns

	frappe.db.savepoint("file_sheet_check")
	try:
		with as_user(OWNER):
			made = frappe.get_doc({"doctype": "File", "file_name": "Prices check.csv", "content": b"Item,Rate\nGL,60\n", "is_private": 1, "folder": ns.HOME})
			made.insert()
			book = api.open_file(made.name)["workbook"]
			assert api.open_file(made.name)["workbook"] == book, "one file, one workbook"
			source = api.get_sheet(book)["source"]
			assert source == {"kind": "csv", "url": made.file_url, "fresh": True, "name": "Prices check.csv"}, source
			api.save_sheet("Prices check.csv", json.dumps({"sheet": {"v": 2, "current": "Sheet1", "sheets": {"Sheet1": {"rows": {"0": ["Item", "Rate"], "1": ["GL", "65"]}}}}}), book)
			assert not api.get_sheet(book)["source"]["fresh"], "read in once"
			api.write_back(book, base64.b64encode(b"Item,Rate\nGL,65\n").decode())
			now = frappe.get_doc("File", made.name)
			assert now.get_content() in (b"Item,Rate\nGL,65\n", "Item,Rate\nGL,65\n"), now.get_content()
			assert frappe.db.count("Cloud File Version", {"file": made.name}) == 1, "what it held is a version"
			api.file_replaced(made.name)
			assert api.get_sheet(book)["source"]["fresh"], "a version from outside is read in again"
			try:
				api.open_file(frappe.get_doc({"doctype": "File", "file_name": "notes check.txt", "content": b"x", "is_private": 1, "folder": ns.HOME}).insert().name)
				raise AssertionError("a text file opened as a workbook")
			except frappe.ValidationError:
				pass
	finally:
		frappe.db.rollback(save_point="file_sheet_check")


@check
def an_excel_file_is_never_saved_over_with_less():
	"""An Excel file with a chart opens in OneWorkbook saying
	what saving over it would drop, and is not saved over until somebody
	chooses; an .xlsm opens read-only and refuses a save. Saves by one person
	in one sitting are one version, the one from before the sitting kept. A
	workbook of One's own saved from Excel keeps itself as it was first and
	notes what was left out. All undone afterwards."""
	import io

	from openpyxl import Workbook, load_workbook
	from openpyxl.chart import BarChart, Reference
	from openpyxl.comments import Comment

	from onedesk.one_sheet import api, excel
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import history
	from onedesk.one_storage import namespace as ns

	def book(rate: int, rich: bool = True) -> bytes:
		made = Workbook()
		sheet = made.active
		sheet["A1"], sheet["B1"] = "GL", rate
		if rich:
			sheet["B1"].comment = Comment("From the supplier.", "Karim")
			chart = BarChart()
			chart.add_data(Reference(sheet, min_col=2, min_row=1, max_row=1))
			sheet.add_chart(chart, "D2")
		out = io.BytesIO()
		made.save(out)
		return out.getvalue()

	sheets = json.dumps({"sheet": {"v": 2, "current": "Sheet", "sheets": {"Sheet": {"rows": {"0": ["GL", "65"]}}}}})
	frappe.db.savepoint("sheet_lose_check")
	try:
		with as_user(OWNER):
			rich = frappe.get_doc({"doctype": "File", "file_name": "Rates check.xlsx", "content": book(60), "is_private": 1, "folder": ns.HOME})
			rich.insert()
			opened = api.open_file(rich.name)["workbook"]
			said = api.get_sheet(opened)
			assert said["can_write"] and "charts" in said["loses"] and "comments" not in said["loses"], said["loses"]
			api.save_sheet("Rates check.xlsx", sheets, opened)
			assert "held" in api.write_back(opened), "saving over waits for a choice"
			assert frappe.db.get_value("File", rich.name, "file_url") == rich.file_url
			copy = api.write_back(opened, "", "copy")
			assert copy["file"] != rich.name and frappe.db.get_value("File", rich.name, "file_url") == rich.file_url, "a copy leaves the file alone"
			plain = frappe.get_doc({"doctype": "File", "file_name": "Plain check.xlsx", "content": book(60, rich=False), "is_private": 1, "folder": ns.HOME})
			plain.insert()
			edited = api.open_file(plain.name)["workbook"]
			assert not api.get_sheet(edited)["loses"]
			for rate in (61, 62, 63):
				api.save_sheet("Plain check.xlsx", json.dumps({"sheet": {"v": 2, "current": "Sheet", "sheets": {"Sheet": {"rows": {"0": ["GL", str(rate)]}}}}}), edited)
				api.write_back(edited)
			assert load_workbook(io.BytesIO(cloud._content(frappe._dict(ns.row(plain.name)))))["Sheet"]["B1"].value == 63
			assert len(history.versions(plain.name)) == 1, "three saves in one sitting are one version"
			assert history.versions(plain.name)[0]["url"] == plain.file_url, "and the one kept is the file from before the sitting"
			macros = frappe.get_doc({"doctype": "File", "file_name": "Macros check.xlsm", "content": book(60, rich=False), "is_private": 1, "folder": ns.HOME})
			macros.insert()
			locked = api.open_file(macros.name)["workbook"]
			said = api.get_sheet(locked)
			assert not said["can_write"] and "macros" in said["notice"], said["notice"]
			try:
				api.save_sheet("Macros check.xlsm", sheets, locked)
				raise AssertionError("a workbook with macros was saved in OneWorkbook")
			except frappe.PermissionError:
				frappe.clear_last_message()
			own = api.make("@my", "Own rates check")["workbook"]
			api.save_sheet("Own rates check", sheets, own)
			excel.write(own, book(70))
			assert frappe.db.exists("Workbook Version", {"workbook": own, "label": "Before an Excel save"}), "kept as it was first"
			assert "comments" in (api.get_sheet(own)["dropped"] or ""), "and what Excel had that was left out is noted"
			api.dismiss_dropped(own)
			assert not api.get_sheet(own)["dropped"]
	finally:
		frappe.db.rollback(save_point="sheet_lose_check")


@check
def an_excel_file_keeps_its_look_when_saved_over():
	"""Huda's budget, with its bold header, number formats and widths, edited
	in OneWorkbook and saved over: the file has the edit and still has its
	look and its formulas. All undone afterwards."""
	import io

	from openpyxl import load_workbook

	from onedesk.one_demo import office as demo
	from onedesk.one_sheet import api, excel
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	budget = next(one for one in demo.files() if one["name"] == demo.budget_name())
	file = demo.found(budget)
	assert file, "the demo has Huda's budget"
	frappe.db.savepoint("sheet_look_check")
	try:
		with as_user(budget["owner"]):
			book = api.open_file(file)["workbook"]
			assert not api.get_sheet(book)["loses"], "saving over a styled file drops nothing"
			data = excel.read(book, cloud._content(frappe._dict(ns.row(file))))
			data["sheet"]["sheets"]["Budget"]["rows"]["1"][1] = 1250000
			api.save_sheet(budget["name"], json.dumps(data, default=str), book)
			assert "file" in api.write_back(book)
			sheet = load_workbook(io.BytesIO(cloud._content(frappe._dict(ns.row(file)))))["Budget"]
			assert sheet["B2"].value == 1250000, "the edit"
			assert sheet["A1"].font.bold and sheet["F1"].font.bold, "the bold header"
			assert sheet["B2"].number_format == "#,##0" and sheet["F2"].number_format == "#,##0", "the number formats"
			assert sheet["F2"].value == "=SUM(B2:E2)", "the formulas"
			assert sheet.column_dimensions["A"].width == 24, "the widths"
	finally:
		frappe.db.rollback(save_point="sheet_look_check")


@check
def a_sheet_prints_under_the_letter_head():
	"""A sheet prints as a PDF under the workspace's letter head, or another
	one chosen, or none, drawn as it is on screen and never from HTML the
	editor sends; kept, it lands beside the workbook in OneCloud. All undone
	afterwards."""
	from onedesk.one_sheet import api, paper

	frappe.db.savepoint("paper_check")
	try:
		with as_user(OWNER):
			book = api.make("@my", "Paper check")["workbook"]
			sheet = {"name": "Sheet1", "size": [2, 2], "cells": [[0, 0, "Item", {"bold": True}], [0, 1, "<script>x</script>", {}], [1, 0, "Glass", {}]], "head": 1}
			top = frappe.db.get_value("Letter Head", {"is_default": 1}, "content") or ""
			drawn = paper.page("Paper check", [sheet])
			assert top[:40] in drawn and "&lt;script&gt;" in drawn and "<script>" not in drawn, "under the letter head, text as text"
			other = frappe.get_doc({"doctype": "Letter Head", "letter_head_name": "Paper check head", "source": "HTML", "content": "<p>Paper check head</p>"})
			other.insert(ignore_permissions=True)
			assert next(one.name for one in paper.letter_heads()) == frappe.db.get_value("Letter Head", {"is_default": 1}), "the default first"
			assert "Paper check head" in paper.page("Paper check", [sheet], letter_head=other.name), "the letter head chosen"
			assert paper._record(book).company == COMPANY, "a head written for record prints finds the company"
			assert top[:40] not in paper.page("Paper check", [sheet], letter_head=paper.NO_HEAD), "or none"
			try:
				paper.page("Paper check", [sheet], letter_head="No such head")
				raise AssertionError("a letter head that isn't there printed")
			except frappe.ValidationError:
				pass
			paper.pdf(book, json.dumps([sheet]))
			assert frappe.local.response.filecontent[:4] == b"%PDF" and frappe.local.response.filename == "Paper check - Sheet1.pdf"
			kept = paper.pdf(book, json.dumps([sheet]), keep="cloud")
			item = frappe.db.get_value("File", kept["id"], ["folder", "file_name"], as_dict=True)
			assert item.folder == frappe.db.get_value("File", frappe.db.get_value("Workbook", book, "file"), "folder") and item.file_name.endswith(".pdf"), item
			try:
				paper.pdf(book, json.dumps([sheet]), keep="record")
				raise AssertionError("a workbook on no record kept a print on one")
			except frappe.ValidationError:
				pass
	finally:
		for key in ("filecontent", "filename", "type"):
			frappe.local.response.pop(key, None)
		frappe.db.rollback(save_point="paper_check")


@check
def a_workbook_left_open_waits_on_the_bar():
	"""A workbook left for another screen waits on the bar under its title;
	one that is gone, or that the reader may not open, isn't named. All
	undone afterwards."""
	from onedesk.one_sheet import api

	frappe.db.savepoint("bar_check")
	try:
		with as_user(OWNER):
			book = api.make("@my", "Bar check")["workbook"]
			assert api.titles(json.dumps([book, "no-such-book"])) == {book: "Bar check"}
		with as_user("Guest"):
			assert api.titles([book]) == {}, "a reader who can't open it isn't told its name"
	finally:
		frappe.db.rollback(save_point="bar_check")


@check
def a_workbook_is_an_excel_file_on_the_drive():
	"""On the network drive a workbook is "Name.xlsx": its formulas with the
	values the editor last worked out, a OneWorkbook-only formula as its
	value. Saved over from Excel, the values and formulas come back with a
	version kept, and the formula Excel only saw as a value keeps its
	formula. A record's workbook is not written from the drive. All undone
	afterwards."""
	import io

	from openpyxl import load_workbook

	from onedesk.one_sheet import api, excel, table
	from onedesk.one_storage import dav
	from onedesk.one_storage import namespace as ns

	frappe.db.savepoint("excel_check")
	try:
		with as_user(OWNER):
			made = api.make("@my", "Excel check")
			book = made["workbook"]
			rows = {"0": ["Item", "Qty", "Total"], "1": ["Glass", 3, "=B2*20"], "2": ["Sum", None, "=SUM(C2:C)"], "3": ["By", '=BRAND("name")']}
			data = {"sheet": {"v": 2, "current": "Sheet1", "sheets": {"Sheet1": {"rows": rows}}}, "values": {"Sheet1": {"C2": 60, "C3": 60, "B4": "Sahara"}}}
			api.save_sheet("Excel check", json.dumps(data), book)
			assert dav._as_file(ns.node(ns.row(made["id"])))["name"] == "Excel check.xlsx"
			sheet = load_workbook(io.BytesIO(excel.build(book))).active
			assert sheet["C2"].value == "=B2*20" and sheet["C3"].value == f"=SUM(C2:C{excel.LAST_ROW})" and sheet["B4"].value == "Sahara", "formulas, and ours as values"
			assert load_workbook(io.BytesIO(excel.build(book)), data_only=True).active["C2"].value == 60, "with what the editor worked out"
			file = frappe.get_doc("File", made["id"])
			assert file.get_content()[:2] == b"PK" and file.file_name == "Excel check.xlsx", "an attachment or a download is the Excel file"
			file.save()
			assert frappe.db.get_value("File", made["id"], "file_name") == "Excel check", "and the file keeps its name"
			sheet["B2"] = 5
			saved = io.BytesIO()
			sheet.parent.save(saved)
			before = frappe.db.count("Workbook Change", {"workbook": book})
			excel.write(book, saved.getvalue())
			back = excel._sheets(excel._data(book))["Sheet1"]["rows"]
			assert back["1"][1] == 5 and back["2"][2] == "=SUM(C2:C)" and back["3"][1] == '=BRAND("name")', back
			assert frappe.db.count("Workbook Change", {"workbook": book}) > before, "a version is kept"
			quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
			bound = table.open_table("Quotation", quote, "items")
			try:
				excel.write(bound, excel.build(bound))
				raise AssertionError("a record's workbook was written from the drive")
			except frappe.PermissionError:
				pass
	finally:
		frappe.db.rollback(save_point="excel_check")


@check
def a_record_table_opens_as_a_workbook():
	"""Layla opens a draft quotation's items in a workbook, raises a quantity
	and adds a line: the quotation saves itself and sends ids and figures
	back. A word for a number and an unknown item are refused; a sheet that
	missed a change on the form is refused and redrawn on opening; FIELD()
	reads the quotation; a copy is a plain workbook. All undone afterwards."""
	from unittest import mock

	from onedesk.one_sheet import api, storage, table

	def lines(book):
		held = table._held(book)
		rows = json.loads(storage.decode_sheets_data(held.sheets_data))["sheet"]["sheets"][held.bound_sheet]["rows"]
		return [[str(one) if one is not None else "" for one in rows[at]] for at in sorted(rows, key=int)]

	def sent(rows):
		return json.dumps({"sheet": "Items", "rows": rows})

	quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
	frappe.db.savepoint("table_check")
	try:
		with as_user(OWNER):
			book = table.open_table("Quotation", quote, "items")
			assert table.open_table("Quotation", quote, "items") == book, "one table, one workbook"
			opened = api.get_sheet(book)
			assert opened["table"] == {"sheet": "Items", "doctype": "Quotation", "name": quote, "field": "items", "label": "Items"}, opened["table"]
			assert json.loads(opened["sheets_data"])["view"]["Items"]["hiddenCols"] == [0]
			rows = lines(book)
			head = rows[0]
			qty, code = head.index("Quantity"), head.index("Item Code")
			first = frappe.get_doc("Quotation", quote).items[0]
			assert rows[1][0] == first.name and rows[0][0].startswith(table.MARK)
			rows[1][qty] = str(first.qty + 2)
			added = [""] * len(head)
			added[code], added[qty] = first.item_code, "3"
			rows.append(added)
			said = api.save_sheet("Items", json.dumps({"sheet": {"v": 2, "sheets": {}}}), book, "", "t1", sent(rows))["table"]
			assert said["ok"], said
			saved = frappe.get_doc("Quotation", quote)
			assert [one.qty for one in saved.items][:1] == [first.qty + 2] and saved.items[-1].qty == 3, saved.items
			assert said["cells"][f"A{len(rows)}"] == saved.items[-1].name, "the new line's id comes back"
			assert saved.items[-1].rate and saved.items[-1].amount == saved.items[-1].rate * 3, "the quotation worked it out"
			for at, value in said["cells"].items():
				line, column = int(at[1:]) - 1, ord(at[0]) - 65
				rows[line][column] = value
			assert api.save_sheet("Items", "{}", book, "", "t2", sent(rows))["table"] == {"ok": True, "cells": {}}, "nothing left to do"
			wrong = [list(one) for one in rows]
			wrong[1][qty] = "lots"
			refused = table.apply(book, sent(wrong))
			assert not refused["ok"] and "Quantity" in refused["message"], refused
			wrong[1][qty], wrong[1][code] = "1", "NO-SUCH-ITEM"
			refused = table.apply(book, sent(wrong))
			assert not refused["ok"] and "NO-SUCH-ITEM" in refused["message"] and refused["missing"] == {"Item": ["NO-SUCH-ITEM"]}, refused
			assert frappe.get_doc("Quotation", quote).items[0].qty == first.qty + 2, "a refused sheet changes nothing"
			try:
				table.make_missing(book, "Customer", '["NO-SUCH-ITEM"]')
				raise AssertionError("made a record of a type the table doesn't name")
			except frappe.ValidationError:
				pass
			assert table.make_missing(book, "Item", '["NO-SUCH-ITEM"]') == {"made": ["NO-SUCH-ITEM"], "failed": {}}
			assert frappe.db.get_value("Item", "NO-SUCH-ITEM", "item_group"), "made with what a new item starts with"
			for attempt in ("and the sheet goes in", first.item_code):
				said = table.apply(book, sent(wrong))
				assert said["ok"], (attempt, said)
				for at, value in said["cells"].items():
					wrong[int(at[1:]) - 1][ord(at[0]) - 65] = value
				wrong[1][code] = first.item_code
			rows = [list(one) for one in wrong]
			changed = frappe.get_doc("Quotation", quote)
			changed.items[0].qty = 5
			told = []
			with mock.patch("frappe.publish_realtime", side_effect=lambda event, message, **kw: told.append((event, message, kw.get("docname")))):
				changed.save()
			assert ("one_table_changed", {"workbook": book}, quote) in told, "the open workbook hears of it"
			stale = table.apply(book, sent(rows))
			assert not stale["ok"] and "changed on the record" in stale["message"], stale
			drawn = table.redrawn(book)
			assert drawn["sheet"] == "Items" and drawn["cells"][f"{chr(65 + qty)}2"] == "5", "drawn again in place"
			assert lines(book)[1][qty] == "5", "and kept"
			read = api.records(json.dumps([["Quotation", quote], ["Quotation", "NO-SUCH-QUOTE"]]))
			assert read["Quotation"][quote]["name"] == quote and "NO-SUCH-QUOTE" not in read["Quotation"], "FIELD() reads it"
			file = frappe.get_doc("File", frappe.db.get_value(api.WORKBOOK, book, "file"))
			copy = frappe.get_doc({"doctype": "File", "file_url": file.file_url, "file_name": "Items, a copy", "folder": "Home", "is_private": 1})
			copy.flags.ignore_permissions = True
			copy.insert()
			assert not frappe.db.get_value(api.WORKBOOK, api.workbook_of(copy.file_url), "bound_doctype"), "a copy is a plain workbook"
	finally:
		frappe.db.rollback(save_point="table_check")
