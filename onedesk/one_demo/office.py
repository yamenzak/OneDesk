"""Office files in the company's files, so Open in OneOS has something real
to open: Samir's handover letter to Khalid and the Bayview tower review in
the Projects library, Omar's proposal to Crescent Schools and this year's
price list, Huda's budget, and Karim's stock export. For Riyadh, Samir
files Ahmed's site report and the Al Olaya costing in riyals. Each is written here
when the demo is built, by the person whose work it is, and shared the way
OneCloud shares a file."""

import csv
import io

import frappe
from frappe.utils import formatdate

from onedesk.one_demo.base import COMPANY, CURRENCY, as_user, today, wh
from onedesk.one_demo.branch import BRANCH, SUPERVISOR
from onedesk.one_demo.masters import ITEMS
from onedesk.one_demo.storage import LIBRARY, PM

SALES = "omar@one.test"
BOOKS = "huda@one.test"
STORES = "karim@one.test"
OWNER = "wsadmin@one.test"

LETTER = "Handover letter to Khalid Mansour.docx"
PROPOSAL = "Crescent Schools window replacement proposal.docx"
REVIEW = "Bayview Tower project review.pptx"
STOCK = "Stock on hand.csv"
REPORT = "Al Olaya Towers site report.docx"
COSTING = "Al Olaya Towers costing.xlsx"
VAT = 0.05
SHARES = ("Margin", "VAT rate")
CENTS = ("Prices",)


def budget_name() -> str:
	return f"Budget {today().year}.xlsx"


def prices_name() -> str:
	return f"Price list {today().year}.xlsx"


def files() -> list[dict]:
	"""Each file: who made it, whether it sits in the Projects library or
	their own files, its folder and name, what writes it, and who it is
	shared with, to read or to change."""
	made = [
		{"owner": PM, "library": True, "folder": "Mansour Villa", "name": LETTER, "make": _letter, "shared": {}},
		{"owner": PM, "library": True, "folder": "Bayview Tower", "name": REVIEW, "make": _review, "shared": {"karim@one.test": 0}},
		{"owner": SALES, "library": False, "folder": "Proposals", "name": PROPOSAL, "make": _proposal, "shared": {PM: 1, "rania@one.test": 0}},
		{"owner": SALES, "library": False, "folder": "Price lists", "name": prices_name(), "make": _prices, "shared": {PM: 0, STORES: 0}},
		{"owner": BOOKS, "library": False, "folder": "Budgets", "name": budget_name(), "make": _budget, "shared": {OWNER: 1, PM: 0}},
		{"owner": STORES, "library": False, "folder": "Exports", "name": STOCK, "make": _stock, "shared": {"yousef@one.test": 0, BOOKS: 0}},
	]
	if frappe.db.exists("Company", BRANCH):
		made += [
			{"owner": PM, "library": True, "folder": "Al Olaya Towers", "name": REPORT, "make": _report, "shared": {}},
			{"owner": PM, "library": True, "folder": "Al Olaya Towers", "name": COSTING, "make": _costing, "shared": {BOOKS: 0}},
		]
	return made


def found(one: dict) -> str | None:
	return frappe.db.get_value("File", {"owner": one["owner"], "file_name": one["name"], "is_folder": 0, "one_deleted": 0})


def run(password=None):
	from onedesk.one_storage import share, upload
	from onedesk.one_storage import namespace as ns

	library = frappe.db.get_value("File", {"one_library": 1, "file_name": LIBRARY})
	for one in files():
		if found(one):
			continue
		with as_user(one["owner"]):
			where = library if one["library"] and library else ns.home(one["owner"])
			node = upload._place(where, f"{one['folder']}/{one['name']}", {"file_name": one["name"], "content": one["make"]()})["id"]
			for edit in (0, 1):
				people = [user for user, may in one["shared"].items() if may == edit and frappe.db.exists("User", user)]
				if people:
					share.share([node], people, edit)


def _word(blocks: list) -> bytes:
	from docx import Document

	doc = Document()
	for kind, said in blocks:
		if kind == "table":
			table = doc.add_table(rows=0, cols=len(said[0]))
			table.style = "Light Grid Accent 1"
			for row in said:
				cells = table.add_row().cells
				for cell, value in zip(cells, row):
					cell.text = str(value)
		elif kind == "points":
			for point in said:
				doc.add_paragraph(point, style="List Bullet")
		elif kind == "title":
			doc.add_heading(said, 0)
		elif kind == "heading":
			doc.add_heading(said, 1)
		else:
			doc.add_paragraph(said)
	out = io.BytesIO()
	doc.save(out)
	return out.getvalue()


def _excel(sheets: dict, widths: dict | None = None) -> bytes:
	from openpyxl import Workbook
	from openpyxl.styles import Font

	book = Workbook()
	book.remove(book.active)
	for title, rows in sheets.items():
		sheet = book.create_sheet(title)
		for row in rows:
			sheet.append(row)
			for cell in sheet[sheet.max_row]:
				if any(one in SHARES for one in row):
					cell.number_format = "0.0%"
				elif isinstance(cell.value, int) or (isinstance(cell.value, str) and cell.value.startswith("=")):
					cell.number_format = "#,##0.00" if title in CENTS else "#,##0"
		for cell in sheet[1]:
			cell.font = Font(bold=True)
		for column, width in (widths or {}).get(title, {}).items():
			sheet.column_dimensions[column].width = width
	out = io.BytesIO()
	book.save(out)
	return out.getvalue()


def _money(value: float, currency: str = CURRENCY) -> str:
	return f"{currency} {value:,.0f}"


def _company() -> dict:
	return frappe.db.get_value("Company", COMPANY, ["phone_no", "email", "website"], as_dict=True) or {}


def _letter() -> bytes:
	reach = _company()
	return _word(
		[
			("title", COMPANY),
			("text", " · ".join(filter(None, ("Dubai", reach.get("phone_no"), reach.get("email"))))),
			("text", formatdate(today(), "d MMMM yyyy")),
			("text", "Mr Khalid Mansour\nMansour & Sons\nAl Barsha, Dubai"),
			("heading", "Handover of your villa's windows and doors"),
			("text", "Dear Mr Mansour,"),
			(
				"text",
				"The casement windows and sliding doors on the ground floor are in, and the balustrade glass for the "
				"terraces arrives from Gulf Glass next week. We are on course to hand the villa over to you in December.",
			),
			("text", "Before the handover we would like to walk the house with you. On the day we will:"),
			(
				"points",
				[
					"open and close every window and door with you, and fix anything that sticks",
					"go through the snag list Rania keeps and agree what is left",
					"give you the keys for the multipoint locks and the care guide for the frames",
				],
			),
			(
				"text",
				"Your two-year warranty starts on the day of handover. The ten per cent held back on each invoice is "
				"due to us four months after it, once the defects period has passed.",
			),
			("text", "Please let me know a morning that suits you."),
			("text", "Yours sincerely,"),
			("text", "Samir Aoun\nProjects Manager"),
		]
	)


def _proposal() -> bytes:
	price = {one[0]: one[6] for one in ITEMS}
	lines = (("WIN-CS12", "Casement Window 1200", 48), ("SVC-INST", "Installation (hours)", 160))
	rows = [("Item", "Description", "Qty", "Rate", "Amount")]
	total = 0
	for code, said, qty in lines:
		total += qty * price[code]
		rows.append((code, said, qty, f"{price[code]:,.0f}", f"{qty * price[code]:,.0f}"))
	rows.append(("", "", "", "Total", f"{total:,.0f}"))
	rows.append(("", "", "", "VAT 5%", f"{total * VAT:,.0f}"))
	rows.append(("", "", "", "Total with VAT", f"{total * (1 + VAT):,.0f}"))
	return _word(
		[
			("title", "Window replacement, east wing"),
			("text", f"A proposal for Crescent Schools, Sharjah · {formatdate(today(), 'd MMMM yyyy')}"),
			("heading", "Why"),
			(
				"text",
				"Rania's survey of the east wing found the original sliding windows warped, their seals gone and "
				"several latches broken. Classrooms on the south side lose their cooling through the gaps.",
			),
			("heading", "What we propose"),
			(
				"points",
				[
					"Replace the 48 sliding windows of the east wing with casement windows in double glazed units",
					"Fit restrictors on every window above the ground floor",
					"Take the old frames away and make good the openings",
				],
			),
			("heading", "Price"),
			("table", rows),
			("text", f"All figures in {CURRENCY}."),
			("heading", "Programme"),
			("text", "Three weeks on site during the summer holidays, one floor a week, so no classroom is lost in term time."),
			("heading", "Terms"),
			("text", "Thirty per cent on order, the rest as each floor is handed over. This proposal is valid for thirty days."),
			("text", "Omar Farouk\nSales Manager, Sahara Glass & Aluminium"),
		]
	)


def _prices() -> bytes:
	rows = [["Code", "Item", "Unit", f"Price ({CURRENCY})", "VAT", "Price with VAT"]]
	for code, name, _group, uom, _kind, _buy, sell, _reorder in ITEMS:
		if sell:
			at = len(rows) + 1
			rows.append([code, name, uom, sell, f"=D{at}*Notes!$B$2", f"=D{at}+E{at}"])
	notes = [["Note", "Value"], ["VAT rate", VAT], ["Valid from", f"1 January {today().year}"], ["Prices", "Ex works Dubai, before delivery"]]
	return _excel({"Prices": rows, "Notes": notes}, {"Prices": {"B": 30, "D": 14, "F": 16}, "Notes": {"A": 14, "B": 32}})


def _budget() -> bytes:
	quarters = ("Q1", "Q2", "Q3", "Q4")
	income = (("Projects", (1200000, 1450000, 1300000, 1650000)), ("Maintenance contracts", (90000, 90000, 95000, 95000)), ("Design fees", (40000, 55000, 45000, 60000)))
	costs = (("Materials", (620000, 760000, 680000, 860000)), ("Subcontractors", (180000, 220000, 200000, 250000)), ("Site labour", (210000, 230000, 220000, 240000)))
	overheads = (("Office rent", 15000), ("Utilities", 3500), ("Salaries, office", 48000), ("Vehicles", 6000), ("Insurance", 2500), ("Software", 1500))
	rows = [["Line", *quarters, "Year"]]

	def line(label, values):
		at = len(rows) + 1
		rows.append([label, *values, f"=SUM(B{at}:E{at})"])
		return at

	first = line(*income[0])
	for one in income[1:]:
		last = line(*one)
	revenue = len(rows) + 1
	rows.append(["Revenue", *(f"=SUM({c}{first}:{c}{last})" for c in "BCDE"), f"=SUM(F{first}:F{last})"])
	first = line(*costs[0])
	for one in costs[1:]:
		last = line(*one)
	upper = len(rows) + 1
	rows.append(["Overheads", *(f"=Overheads!$D${len(overheads) + 2}" for _ in quarters), "=SUM(B{0}:E{0})".format(upper)])
	spent = len(rows) + 1
	rows.append(["Costs", *(f"=SUM({c}{first}:{c}{upper})" for c in "BCDEF")])
	rows.append(["Profit", *(f"={c}{revenue}-{c}{spent}" for c in "BCDEF")])
	rows.append(["Margin", *(f"=IF({c}{revenue}=0,0,({c}{revenue}-{c}{spent})/{c}{revenue})" for c in "BCDEF")])
	held = [["Overhead", "Monthly", "Months", "Quarter"]]
	for label, monthly in overheads:
		at = len(held) + 1
		held.append([label, monthly, 3, f"=B{at}*C{at}"])
	held.append(["Each quarter", "", "", f"=SUM(D2:D{len(held)})"])
	return _excel({"Budget": rows, "Overheads": held}, {"Budget": {"A": 24, **dict.fromkeys("BCDEF", 14)}, "Overheads": {"A": 20}})


def _review() -> bytes:
	from pptx import Presentation

	project = frappe.db.get_value("Project", {"project_name": "Bayview Tower Curtain Wall"}, ["percent_complete", "expected_end_date"], as_dict=True) or {}
	done = round(project.get("percent_complete") or 0)
	ends = formatdate(project.get("expected_end_date"), "MMMM yyyy") if project.get("expected_end_date") else "next year"
	slides = (
		("Bayview Tower curtain wall", f"Project review · {formatdate(today(), 'MMMM yyyy')}\nSamir Aoun, Projects Manager"),
		("Where we are", [f"{done}% of the work done", "Podium units going in, levels 1 to 10 on brackets", f"Handover planned for {ends}"]),
		("Budget", [f"Materials {_money(900000)}", f"Subcontracts {_money(300000)}", f"Labour {_money(180000)}", f"Equipment {_money(60000)}"]),
		("What could hold us up", ["Double glazed units from Gulf Glass, ordered late once already", "Crane time shared with the main contractor", "Wind on the upper levels in March"]),
		("Next four weeks", ["Finish the podium units and seal the perimeter", "Nadia's shop drawings for levels 11 to 24", "Bayview's next progress claim"]),
	)
	deck = Presentation()
	for at, (title, said) in enumerate(slides):
		slide = deck.slides.add_slide(deck.slide_layouts[0 if at == 0 else 1])
		slide.shapes.title.text = title
		body = slide.placeholders[1].text_frame
		points = said if isinstance(said, list) else said.split("\n")
		body.text = points[0]
		for point in points[1:]:
			body.add_paragraph().text = point
	out = io.BytesIO()
	deck.save(out)
	return out.getvalue()


def _stock() -> bytes:
	warehouses = frappe.get_all("Warehouse", filters={"company": COMPANY, "is_group": 0}, pluck="name")
	held = frappe.get_all(
		"Bin",
		filters={"warehouse": ["in", warehouses or [wh("Stores")]], "actual_qty": [">", 0]},
		fields=["item_code", "warehouse", "actual_qty", "stock_uom", "valuation_rate", "stock_value"],
		order_by="item_code asc, warehouse asc",
	)
	names = dict(frappe.get_all("Item", filters={"name": ["in", [row.item_code for row in held] or [""]]}, fields=["name", "item_name"], as_list=True))
	out = io.StringIO()
	writer = csv.writer(out)
	writer.writerow(("Item code", "Item", "Warehouse", "Quantity", "Unit", f"Valuation rate ({CURRENCY})", f"Value ({CURRENCY})"))
	for row in held:
		writer.writerow((row.item_code, names.get(row.item_code, ""), row.warehouse, f"{row.actual_qty:g}", row.stock_uom, f"{row.valuation_rate:.2f}", f"{row.stock_value:.2f}"))
	return out.getvalue().encode()


def _report() -> bytes:
	first, last, _email = SUPERVISOR
	return _word(
		[
			("title", "Al Olaya Towers site report"),
			("text", f"{BRANCH}, Riyadh · week ending {formatdate(today(), 'd MMMM yyyy')} · {first} {last}, site supervisor"),
			("heading", "Done this week"),
			("points", ["Survey of the tower's openings finished and signed off", "Brackets fixed on the first two floors", "Twelve casement windows delivered from our stores"]),
			("heading", "Next week"),
			("points", ["Fit the first windows on level 1", "Seal the brackets on level 2", "Walk level 1 with the main contractor"]),
			("heading", "Hold-ups"),
			("text", "Crane time is short on Sundays, when the main contractor lifts its steel. We have asked for Monday mornings instead."),
			("heading", "Safety"),
			("text", "No incidents. Two new fixers were inducted on Wednesday."),
		]
	)


def _costing() -> bytes:
	rows = [
		["Line", "Qty", "Unit", "Rate (SAR)", "Amount (SAR)"],
		["Casement windows sold", 60, "Nos", 1150, "=B2*D2"],
		["Aluminium profile", 360, "Meter", 26.5, "=B3*D3"],
		["Double glazed units", 72, "Square Meter", 155, "=B4*D4"],
		["Concealed hinges", 120, "Nos", 35, "=B5*D5"],
		["Structural silicone", 48, "Nos", 29, "=B6*D6"],
		["Fixing crew", 18, "Day", 900, "=B7*D7"],
		["", "", "", "Costs", "=SUM(E3:E7)"],
		["", "", "", "Profit", "=E2-E8"],
		["", "", "", "Margin", "=IF(E2=0,0,E9/E2)"],
	]
	return _excel({"Costing": rows}, {"Costing": {"A": 24, "D": 12, "E": 14}})
