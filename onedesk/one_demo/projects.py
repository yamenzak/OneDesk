"""OneProject, every way a project runs: fixed price, time and materials,
retainer and internal.
"""

import frappe
from frappe.utils import add_days, add_months, date_diff, flt, get_first_day, get_first_day_of_week, getdate

from onedesk.one_demo.base import (
	COMPANY,
	account,
	ago,
	ahead,
	as_user,
	dated,
	make,
	on,
	rated,
	save,
	tag,
	today,
	wh,
)
from onedesk.one_hr.hiring import AUTHOR
from onedesk.one_project import library

PM = "samir@one.test"
OWNER = "wsadmin@one.test"
ACCOUNTS_USER = "huda@one.test"
TEMPLATE = "Aluminium & Glazing"

PHASES = tuple(
	(phase["subject"], tuple((one["subject"], one["day"], one["days"]) for one in phase["tasks"]))
	for phase in library.read("aluminium_and_glazing")["tasks"]
)


def run(password=None):
	_accounts()
	_terms()
	with as_user(PM):
		_template()
		villa()
		tower()
		acme()
		balcony()
		partitions()
		showroom()
		survey()
		marina()
		facade_care()
		workshop()
	for project in frappe.get_all("Project", filters={"status": "Open"}, pluck="name"):
		_current(project)
	_estimates()
	_contacts()
	_behind()
	_own()
	_portal(password)


def villa():
	name = _project(
		"Mansour Villa Windows and Doors",
		kind="Fixed Price",
		client="Mansour & Sons",
		starts=on(2, 15),
		ends=ahead(55),
		template=TEMPLATE,
		team=("rania@one.test", "tariq@one.test", "yousef@one.test", "nadia@one.test"),
		notes="A four-bedroom villa in Al Barsha: casement windows, sliding doors and glass balustrades, handed over in December.",
	)
	if not name:
		return
	order = _contract(
		name,
		on(2, 12),
		[("WIN-CS12", 60, 2400), ("DR-SL24", 20, 6800), ("BAL-GL", 60, 1450), ("SVC-INST", 120, 180)],
		retention=10,
		retention_due=ahead(120),
		handover=50,
		tax="With Invoice",
	)
	_signed(name, on(2, 14), "Khalid Mansour")
	_budget(name, {"Materials": 140000, "Subcontracts": 60000, "Labour": 40000})
	frappe.db.set_value("Project", name, {"one_time_budget": 90000, "one_hours_planned": 1500})
	_progress(name, done_through=3, half_way=4)
	_current(name)
	_glass_late(name)
	_milestone_shares(name, (10, 20, 30, 30, 10))
	first = _bill_progress(order, on(4, 30), done=20)
	_pay(first, on(5, 20))
	second = _bill_progress(order, on(7, 31), lines={0: 70, 1: 40, 2: 30, 3: 20})
	_pay(second, on(8, 25), part=0.6)
	_bill_progress(order, ago(40), lines={0: 90, 1: 60, 2: 50, 3: 35})
	sub = _subcontract(name, "Precision Installers", 58000, on(6, 1), retention=5)
	bill = _bill_progress(sub, on(8, 15), done=40, doctype="Purchase Order")
	_pay(bill, on(9, 5))
	_issue(
		name,
		on(5, 18),
		(("ALU-6063", 420), ("GLS-DGU", 95), ("HW-HINGE", 120), ("HW-HANDLE", 60), ("SEAL-EPDM", 600)),
	)
	_issue(name, on(8, 4), (("ALU-6063", 380), ("GLS-DGU", 88), ("HW-LOCK", 18), ("SIL-CLR", 40)))
	_time(name, ("Arun", "Ravi", "Joseph"), "Fabrication", _begins(name, FACTORY), weeks=5, hours=28, phase=FACTORY)
	_time(name, ("Yousef", "Bilal"), "Installation", _begins(name, SITE), weeks=3, hours=32, phase=SITE)
	_time(name, ("Yousef", "Bilal"), "Installation", GLASS_IN, weeks=None, hours=32, phase=SITE)
	_time(name, ("Rania",), "Project Management", on(2, 20), weeks=None, hours=6, task=False)
	_extra_work(
		name, "Mansour & Sons", "Staircase balustrade", [("BAL-GL", 14, 1500), ("SVC-INST", 20, 180)], ago(30)
	)
	_signed(frappe.db.get_value("Project", {"one_parent": name, "project_name": "Staircase balustrade"}) or name)
	_update(name, "Frames for the ground floor are in. Glass for the first floor lands on Thursday.", ago(9), "rania@one.test")
	_update(name, "Balustrade drawings approved by Khalid. Starting the staircase next week.", ago(3), "tariq@one.test")
	_papers(name)
	frappe.db.set_value("Project", name, "one_health", "At Risk")


def tower():
	name = _project(
		"Bayview Tower Curtain Wall",
		kind="Fixed Price",
		client="Bayview Developments",
		starts=on(3, 1),
		ends=add_days(today(), 170),
		team=("rania@one.test", "tariq@one.test", "karim@one.test"),
		notes="Unitised curtain wall for a 24-storey residential tower in Business Bay, podium first.",
	)
	if not name:
		return
	order = _contract(
		name,
		on(2, 25),
		[("BAL-GL", 400, 1450), ("WIN-CS12", 300, 2400), ("SVC-INST", 1800, 180)],
		retention=5,
		retention_due=ahead(300),
		handover=50,
	)
	_signed(name)
	_advance("Bayview Developments", order, 180000, on(3, 10))
	_budget(name, {"Materials": 900000, "Subcontracts": 300000, "Labour": 180000, "Equipment": 60000})
	for part, starts, ends in (("Podium", on(3, 15), ahead(20)), ("Levels 1 to 10", on(6, 1), ahead(110))):
		sub = _project(
			f"Bayview Tower {part}",
			kind="Fixed Price",
			client="Bayview Developments",
			starts=starts,
			ends=ends,
			parent=name,
		)
		_tasks(
			sub,
			(
				("Shop drawings", 0, 15, "nadia@one.test", "Completed"),
				(
					"Brackets and embeds",
					15,
					20,
					"rania@one.test",
					"Completed" if part == "Podium" else "Working",
				),
				("Unit installation", 35, 60, "tariq@one.test", "Working" if part == "Podium" else "Open"),
				("Perimeter sealing", 95, 25, "rania@one.test", "Open"),
			),
			starts,
		)
	scaffold = _subcontract(name, "Rapid Scaffolding", 66000, on(4, 1))
	_signed(name, on(3, 28), "Omar Haddad", supplier="Rapid Scaffolding")
	_bill_progress(scaffold, on(7, 1), done=50, doctype="Purchase Order")
	_bill_progress(order, on(5, 31), done=8)
	late = _bill_progress(order, ago(75), done=15)
	frappe.db.set_value("Project", name, "one_health", "On Track")
	return late


def acme():
	if frappe.db.exists("Project", {"project_name": "Acme New York Lobby"}):
		return
	name = _project(
		"Acme New York Lobby",
		kind="Fixed Price",
		client="Acme Holdings",
		starts=ahead(20),
		ends=ahead(140),
		notes="Glass entrance and lobby screens for Acme's Manhattan office. Quoted, waiting on their board.",
	)
	quote = frappe.new_doc("Quotation")
	quote.update(
		{
			"quotation_to": "Customer",
			"party_name": "Acme Holdings",
			"opportunity": frappe.db.get_value("Opportunity", {"party_name": "Acme Holdings"}),
			"currency": "USD",
			"project": name,
			"valid_till": ahead(25),
		}
	)
	dated(quote, ago(6), "transaction_date")
	quote.append("items", {"item_code": "DR-SL24", "qty": 6, "rate": 2100})
	quote.append("items", {"item_code": "BAL-GL", "qty": 30, "rate": 420})
	quote.append("items", {"item_code": "SVC-INST", "qty": 90, "rate": 55})
	save(quote, submit=True)


def balcony():
	name = _project(
		"Rahman Balcony Enclosure",
		kind="Fixed Price",
		client="Aisha Rahman",
		starts=on(3, 2),
		ends=on(5, 30),
		team=("yousef@one.test",),
		notes="Frameless sliding enclosure for a 9 m balcony in Jumeirah Lake Towers.",
	)
	if not name:
		return
	order = _contract(name, on(2, 26), [("DR-SL24", 4, 6800), ("SVC-INST", 40, 180), ("SVC-SURV", 1, 7600)])
	_tasks(
		name,
		(
			("Measure the balcony", 0, 2, "rania@one.test", "Completed"),
			("Fabricate the sliding panels", 10, 20, "tariq@one.test", "Completed"),
			("Install and seal", 35, 6, "yousef@one.test", "Completed"),
			("Handover", 45, 1, "samir@one.test", "Completed"),
		),
		on(3, 2),
	)
	invoice = _bill_progress(order, on(5, 31), done=100)
	_pay(invoice, on(6, 12))
	from onedesk.one_project.status import change

	change(name, "Completed")


def partitions():
	name = _project(
		"Palm Interiors Office Partitions",
		kind="Fixed Price",
		client="Palm Interiors",
		starts=on(7, 1),
		ends=on(9, 30),
		notes="Glass partitions for a co-working floor. The client moved to another building.",
	)
	if not name:
		return
	_tasks(
		name,
		(
			("Site survey", 0, 2, "rania@one.test", "Completed"),
			("Partition layout", 3, 10, "nadia@one.test", "Cancelled"),
		),
		on(7, 1),
	)
	from onedesk.one_project.status import change

	change(name, "Cancelled", close=1)


def showroom():
	name = _project(
		"Nordlicht Showroom Design",
		kind="Time and Materials",
		client="Nordlicht GmbH",
		starts=on(4, 1),
		ends=ahead(45),
		markup=12,
		budget=90000,
		team=("nadia@one.test",),
		notes="Design and supervision of a glass-heavy showroom fit-out in Berlin, billed by the hour.",
	)
	if not name:
		return
	_tasks(
		name,
		(
			("Concept options", 0, 14, "nadia@one.test", "Completed"),
			("Design development", 14, 30, "nadia@one.test", "Completed"),
			("Technical drawings", 44, 40, "nadia@one.test", "Working"),
			("Site supervision visits", 84, 60, "samir@one.test", "Open"),
		),
		on(4, 1),
	)
	_time(name, ("Nadia",), "Design", on(4, 2), weeks=14, hours=22)
	_time(name, ("Samir",), "Site Survey", on(5, 4), weeks=3, hours=8)
	from onedesk.one_project.billing import invoice_time

	with as_user(ACCOUNTS_USER):
		draft = invoice_time(name, item="SVC-DES")
		_redate(draft, on(7, 15))
		save(draft, submit=True)
	_pay(frappe.get_doc("Sales Invoice", draft.name), on(8, 2))
	_time(name, ("Nadia",), "Design", on(7, 20), weeks=None, hours=18)
	_buy_for(
		name, "Euro Hardware Trading", (("HW-HANDLE", 40, 21), ("HW-LOCK", 12, 88)), on(6, 10), currency="EUR"
	)


def survey():
	name = _project(
		"Crescent Schools Window Survey",
		kind="Time and Materials",
		client="Crescent Schools",
		starts=ago(12),
		ends=ahead(10),
		team=("rania@one.test",),
	)
	if not name:
		return
	_tasks(
		name,
		(
			("Survey the east wing", 0, 3, "rania@one.test", "Completed"),
			("Survey the west wing", 5, 3, "rania@one.test", "Working"),
			("Write the condition report", 9, 5, "rania@one.test", "Open"),
		),
		ago(12),
	)
	_time(name, ("Rania",), "Site Survey", ago(11), weeks=2, hours=9)


def marina():
	name = _project(
		"Marina Hotels Glazing Care",
		kind="Retainer",
		client="Marina Hotels Group",
		starts=on(1, 1),
		ends=add_days(on(1, 1), 729),
		monthly_fee=12000,
		monthly_hours=40,
		team=("yousef@one.test", "tariq@one.test"),
		notes="Glazing inspection and repairs across three hotels, a visit a week and call-outs within 24 hours.",
	)
	if not name:
		return
	_retainer(
		name,
		1,
		months=today().month - 1,
		people=("Yousef", "Bilal"),
		hours=(9, 10, 11, 9, 12, 10, 15, 13, 9),
	)


def facade_care():
	name = _project(
		"Gulf Properties Facade Care",
		kind="Retainer",
		client="Gulf Properties REIT",
		starts=on(6, 1),
		ends=add_days(on(6, 1), 364),
		monthly_fee=8500,
		monthly_hours=24,
		team=("yousef@one.test",),
	)
	if not name:
		return
	_retainer(name, 6, months=today().month - 6, people=("Imran",), hours=(5, 6, 6, 7))


def workshop():
	name = _project(
		"Workshop CNC Upgrade",
		kind="Internal",
		starts=on(5, 1),
		ends=ahead(25),
		budget=600000,
		team=("tariq@one.test", "karim@one.test"),
		notes="A five-axis profile machining centre for the workshop, and the floor and power it needs.",
	)
	if not name:
		return
	_tasks(
		name,
		(
			("Choose the machine", 0, 20, "tariq@one.test", "Completed"),
			("Prepare the floor and power", 25, 30, "karim@one.test", "Completed"),
			("Install and commission", 60, 25, "tariq@one.test", "Working"),
			("Train the fabricators", 90, 10, "tariq@one.test", "Open"),
		),
		on(5, 1),
	)
	_time(name, ("Tariq",), "Project Management", on(5, 4), weeks=12, hours=4)


def _project(
	title, kind, starts, ends, client=None, template=None, team=(), notes=None, parent=None, **values
):
	if frappe.db.exists("Project", {"project_name": title}):
		return None
	from onedesk.one_project import kinds
	from onedesk.one_project import team as members

	name = kinds.make(
		{
			"title": title,
			"kind": kind,
			"client": client,
			"starts": str(starts),
			"ends": str(ends),
			"manager": PM,
			"template": template,
			"parent": parent,
			**dict(zip(("payment_terms", "terms"), AGREED.get(title, (None, None)), strict=True)),
			**values,
		}
	)
	tag(frappe.get_doc("Project", name))
	if notes:
		frappe.db.set_value("Project", name, "notes", notes)
	for user in team:
		members.add(name, user)
	return name


def _contract(project, date, lines, retention=0, retention_due=None, handover=0, tax=None):
	"""The customer's order for the work, made on the day it was signed and
	named the project's contract, as Add Contract does. Khalid's contract
	taxes each bill in full (`tax`); the rest are taxed as the workspace
	starts them, the retention when it's released."""
	from onedesk.one_book.currency import bill_in

	doc = frappe.get_doc("Project", project)
	if retention:
		frappe.db.set_value(
			"Project",
			project,
			{"one_retention": retention, "one_retention_due": retention_due, "one_retention_handover": handover},
		)
	order = frappe.new_doc("Sales Order")
	order.company = COMPANY
	bill_in(order, "Customer", doc.customer)
	order.update(
		{
			"customer": doc.customer,
			"project": project,
			"delivery_date": doc.expected_end_date,
			"one_retention": retention,
			"one_retention_due": retention_due if retention else None,
			"one_retention_handover": handover if retention else 0,
			"one_retention_tax": tax,
		}
	)
	dated(order, date, "transaction_date")
	for code, qty, rate in lines:
		order.append(
			"items",
			{
				"item_code": code,
				"qty": qty,
				"rate": rate,
				"delivery_date": doc.expected_end_date,
				"project": project,
			},
		)
	save(order, submit=True)
	doc.db_set("sales_order", order.name)
	return order.name


def _signed(project, date=None, signee=None, supplier=None):
	"""A contract drawn up as Draw Up Contract does it, by whoever keeps sales:
	with the customer, or with `supplier` from the subcontract template, signed
	and submitted on `date`, or not signed yet."""
	from onedesk.one_project.agreement import draw_up

	with as_user(OWNER):
		made = draw_up(project, party_type="Supplier", party=supplier, template=SUBCONTRACT) if supplier else draw_up(project)
		doc = frappe.get_doc("Contract", made)
		if date:
			doc.update({"is_signed": 1, "signee": signee, "signed_on": f"{date} 11:00:00"})
			doc.submit()
	return tag(doc)


def _bill_progress(order, date, done=None, lines=None, doctype="Sales Order"):
	"""Bill Progress, as the project page asks for it, by whoever keeps the
	books."""
	with as_user(ACCOUNTS_USER):
		return _billed(order, date, done, lines, doctype)


def _billed(order, date, done, lines, doctype):
	from onedesk.one_project.progress import bill_progress

	if lines is not None:
		rows = frappe.get_all(f"{doctype} Item", filters={"parent": order}, fields=["name"], order_by="idx")
		lines = {rows[i].name: share for i, share in lines.items()}
	invoice = bill_progress(order, doctype=doctype, done=done, lines=lines)
	_redate(invoice, date)
	if invoice.doctype == "Purchase Invoice":
		invoice.bill_no = f"INV-{order[-5:]}-{date.month}"
		invoice.bill_date = date
	return save(invoice, submit=True)


def _redate(invoice, date):
	"""An invoice dated in the past, due as its terms say from that day: its
	schedule was made today, so each of its own terms moves back with it.
	The retention keeps its dates, which follow the work, not the invoice."""
	from onedesk.one_project.retention import HELD

	dated(invoice, date)
	rows = invoice.get("payment_schedule") or []
	for row in rows:
		if row.payment_term not in HELD:
			row.due_date = add_days(date, max(0, date_diff(row.due_date, today())))
	invoice.due_date = max(getdate(row.due_date) for row in rows) if rows else None
	return invoice


def _pay(invoice, date, part=1.0):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	from onedesk.one_project.retention import HELD

	held = sum(flt(row.payment_amount) for row in invoice.get("payment_schedule") or [] if row.payment_term in HELD)
	with as_user(ACCOUNTS_USER):
		payment = get_payment_entry(invoice.doctype, invoice.name)
		dated(payment, date)
		payment.reference_no = f"TRF-{invoice.name.rsplit('-', 1)[-1]}"
		payment.reference_date = date
		if part < 1 or held:
			amount = flt((payment.paid_amount - held) * part, 2)
			payment.paid_amount = amount
			payment.received_amount = flt(
				amount * flt(payment.source_exchange_rate or 1) / flt(payment.target_exchange_rate or 1), 2
			)
			for ref in payment.references:
				ref.allocated_amount = min(ref.allocated_amount, amount)
		save(rated(payment), submit=True)


def _advance(customer, order, amount, date):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	with as_user(ACCOUNTS_USER):
		payment = get_payment_entry("Sales Order", order, party_amount=amount)
		dated(payment, date)
		payment.reference_no = f"ADV-{order[-5:]}"
		payment.reference_date = date
		save(payment, submit=True)


def _subcontract(project, supplier, amount, date, retention=0):
	order = frappe.new_doc("Purchase Order")
	order.update(
		{
			"supplier": supplier,
			"company": COMPANY,
			"project": project,
			"schedule_date": add_days(date, 60),
			"one_retention": retention,
			"one_retention_due": ahead(150) if retention else None,
		}
	)
	dated(order, date, "transaction_date")
	order.append(
		"items",
		{
			"item_code": "SVC-SUB",
			"qty": 1,
			"rate": amount,
			"schedule_date": add_days(date, 60),
			"project": project,
		},
	)
	return save(order, submit=True).name


SCHEDULE = (
	("W01", "Casement", 1200, 1500, 12),
	("W02", "Casement", 900, 1500, 18),
	("W03", "Fixed", 600, 2100, 30),
	("D01", "Sliding door", 2400, 2400, 14),
	("D02", "Sliding door", 3600, 2400, 6),
)


def _papers(project):
	"""What the villa keeps beside its money: the window schedule on its
	Files tab, a photo from site in its Featured Media, and a request for
	the next run of profile, each added as Samir adds them."""
	from onedesk.one_project import media
	from onedesk.one_storage import namespace, upload

	if not frappe.db.exists("File", {"attached_to_name": project, "file_name": "Window schedule.csv"}):
		rows = ["Mark,Type,Width,Height,Count", *(",".join(map(str, one)) for one in SCHEDULE)]
		upload._place(namespace.record_node("Project", project), None, {"file_name": "Window schedule.csv", "content": "\n".join(rows).encode()})
	if not media.featured(project):
		upload._place(media.node(project), None, {"file_name": "Ground floor frames.png", "content": _photo()})
	if not frappe.db.exists("Material Request Item", {"project": project}):
		request = frappe.new_doc("Material Request")
		request.update({"material_request_type": "Purchase", "company": COMPANY, "schedule_date": ahead(10)})
		for code, qty in (("ALU-6063", 300), ("GLS-DGU", 60)):
			request.append("items", {"item_code": code, "qty": qty, "schedule_date": ahead(10), "warehouse": wh("Stores"), "project": project})
		save(request, submit=True)


def _photo(sky=(176, 208, 232)) -> bytes:
	"""A picture of a glazed frame against the sky, drawn rather than shipped."""
	from io import BytesIO

	from PIL import Image, ImageDraw

	picture = Image.new("RGB", (960, 600), sky)
	draw = ImageDraw.Draw(picture)
	draw.rectangle((0, 460, 960, 600), fill=(214, 200, 176))
	for left in (140, 500):
		draw.rectangle((left, 120, left + 320, 460), outline=(70, 74, 80), width=18)
		draw.line((left + 160, 120, left + 160, 460), fill=(70, 74, 80), width=12)
		draw.rectangle((left + 18, 138, left + 150, 442), fill=(150, 190, 220))
		draw.rectangle((left + 170, 138, left + 302, 442), fill=(160, 198, 226))
	held = BytesIO()
	picture.save(held, "PNG")
	return held.getvalue()


def _buy_for(project, supplier, lines, date, currency=None):
	order = frappe.new_doc("Purchase Order")
	order.update(
		{"supplier": supplier, "company": COMPANY, "project": project, "schedule_date": add_days(date, 14)}
	)
	if currency:
		order.currency = currency
	dated(order, date, "transaction_date")
	for code, qty, rate in lines:
		order.append(
			"items",
			{
				"item_code": code,
				"qty": qty,
				"rate": rate,
				"schedule_date": add_days(date, 14),
				"project": project,
				"warehouse": wh("Stores"),
			},
		)
	save(order, submit=True)
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice

	with as_user(ACCOUNTS_USER):
		bill = make_purchase_invoice(order.name)
		_redate(bill, add_days(date, 12))
		bill.bill_no = f"EH-{order.name[-5:]}"
		bill.update_stock = 1
		return save(bill, submit=True)


def _issue(project, date, lines):
	entry = frappe.new_doc("Stock Entry")
	entry.stock_entry_type = "Material Issue"
	entry.purpose = "Material Issue"
	entry.company = COMPANY
	entry.project = project
	dated(entry, date)
	for code, qty in lines:
		entry.append(
			"items", {"item_code": code, "qty": qty, "s_warehouse": wh("Stores"), "project": project}
		)
	save(entry, submit=True)


def _budget(project, lines):
	from onedesk.one_project.budget import set_budget

	for kind, amount in lines.items():
		set_budget(project, account(COST_TYPES[kind]), amount, "Warn")


def _tasks(project, rows, starts):
	"""(subject, starts after days, lasts days, assigned to, status)"""
	made = []
	for subject, begin, lasts, who, status in rows:
		begins = add_days(starts, begin)
		values = {
			"doctype": "Task",
			"subject": subject,
			"project": project,
			"exp_start_date": begins,
			"exp_end_date": add_days(begins, lasts),
			"status": "Open" if status in ("Completed", "Cancelled") else status,
		}
		task = make(values)
		_assign(task.name, who)
		_finish(task.name, status, add_days(begins, lasts))
		made.append(task.name)
	_current(project)
	return made


def _current(project):
	"""An open project's work as it stands today: what's still to do is due
	from next week on, in the order it was planned, what's under way partly
	done, and not all of it the same priority. Done work keeps its dates."""
	if frappe.db.get_value("Project", project, "status") != "Open":
		return
	tasks = frappe.get_all(
		"Task",
		filters={"project": project, "status": ["in", ("Open", "Working", "Pending Review", "Overdue")]},
		fields=["name", "status", "exp_start_date", "exp_end_date", "progress"],
		order_by="exp_end_date asc, name asc",
	)
	ends = [getdate(one.exp_end_date) for one in tasks if one.exp_end_date]
	shift = max(0, date_diff(ahead(7), min(ends))) if ends else 0
	last = getdate(frappe.db.get_value("Project", project, "expected_end_date") or add_days(today(), 365))
	for i, task in enumerate(tasks):
		values = {"priority": ("Medium", "Low", "High", "Medium", "Low")[i % 5]}
		if shift and task.exp_end_date:
			end = min(getdate(add_days(task.exp_end_date, shift)), last)
			values["exp_end_date"] = end
			if task.status == "Open" and task.exp_start_date:
				values["exp_start_date"] = min(getdate(add_days(task.exp_start_date, shift)), end)
		if task.status == "Working" and not flt(task.progress):
			values["progress"] = (40, 65, 25, 80, 50)[i % 5]
		frappe.db.set_value("Task", task.name, values, update_modified=False)


FACTORY, SITE = "Factory Fabrication & Assembly", "Site Installation & Logistics"

GLASS_IN = on(8, 10)


def _begins(project, phase):
	"""The day a phase of the project begins, as its first task does."""
	group = frappe.db.get_value("Task", {"project": project, "subject": phase, "is_group": 1})
	return min(getdate(day) for day in frappe.get_all("Task", filters={"parent_task": group}, pluck="exp_start_date") if day)


def _glass_late(project):
	"""The villa's glass came late. Install glass has been under way since
	it reached site, and what comes after it is still to do, one after the
	other from next week on, each phase holding its own tasks and all of it
	inside the project's end, as ERPNext checks when a task is saved."""
	glass = frappe.db.get_value("Task", {"project": project, "subject": "Install glass"})
	if not glass:
		return
	frappe.db.set_value(
		"Task", glass, {"exp_start_date": GLASS_IN, "exp_end_date": ago(4), "status": "Working"}, update_modified=False
	)
	after = frappe.get_all(
		"Task",
		filters={"project": project, "is_group": 0, "status": ["not in", ("Completed", "Cancelled")], "name": ["!=", glass]},
		fields=["name", "parent_task", "exp_start_date", "exp_end_date"],
		order_by="lft asc",
	)
	if not after:
		return
	day = getdate(ahead(7))
	last = getdate(frappe.db.get_value("Project", project, "expected_end_date"))
	room = max(1, date_diff(last, day) // len(after))
	for one in after:
		planned = date_diff(one.exp_end_date, one.exp_start_date) if one.exp_start_date and one.exp_end_date else 2
		ends = min(add_days(day, max(0, min(planned, room - 1))), last)
		frappe.db.set_value(
			"Task", one.name, {"exp_start_date": day, "exp_end_date": ends, "status": "Open", "progress": 0}, update_modified=False
		)
		day = min(add_days(ends, 1), last)
	for phase in frappe.get_all("Task", filters={"project": project, "is_group": 1}, pluck="name"):
		dates = frappe.get_all("Task", filters={"parent_task": phase}, fields=["exp_start_date", "exp_end_date"])
		if not dates:
			continue
		frappe.db.set_value(
			"Task",
			phase,
			{
				"exp_start_date": min(getdate(one.exp_start_date) for one in dates if one.exp_start_date),
				"exp_end_date": max(getdate(one.exp_end_date) for one in dates if one.exp_end_date),
			},
			update_modified=False,
		)


def _portal(password=None):
	"""Khalid Mansour invited to the portal by Omar, so the villa can be seen
	as its customer sees it, and put on its team by Samir: he sees its files
	there, not its timesheets, since the villa is a fixed price."""
	from frappe.utils.password import update_password

	from onedesk.one import portal_invite
	from onedesk.one_project import team

	contact = frappe.db.get_value("Contact", {"email_id": "khalid@mansour.example"})
	if not contact:
		return
	with as_user("omar@one.test"):
		portal_invite.invite_contact(contact)
	user = frappe.db.get_value("Contact", contact, "user")
	if user and password:
		update_password(user, password)
	villa = frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	if user and villa:
		with as_user(PM):
			team.add(villa, user)
			team.show(villa, user, timesheets=0, files=1)


def _behind():
	"""Not everything is on time: a villa task is late, and Rania has more to
	do this week than she has hours, so Workload, the Overview and OneAI's
	"What is late?" have something true to say."""
	villa = frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	open_ = ("Open", "Working")
	late = frappe.get_all(
		"Task",
		filters={"project": villa, "status": ["in", open_], "is_group": 0},
		fields=["name", "exp_start_date"],
		order_by="exp_end_date asc",
		limit=1,
	)
	if late:
		frappe.db.set_value(
			"Task",
			late[0].name,
			{"exp_start_date": min(getdate(late[0].exp_start_date or ago(12)), getdate(ago(12))), "exp_end_date": ago(4), "status": "Working"},
			update_modified=False,
		)
	busy = frappe.get_all(
		"Task",
		filters={
			"_assign": ["like", '%"rania@one.test"%'],
			"status": ["in", open_],
			"is_group": 0,
			"name": ["not in", [one.name for one in late] or [""]],
		},
		fields=["name", "actual_time"],
		order_by="exp_end_date asc",
		limit=1,
	)
	if busy:
		starts = get_first_day_of_week(getdate(today()))
		frappe.db.set_value(
			"Task",
			busy[0].name,
			{
				"exp_start_date": starts,
				"exp_end_date": add_days(starts, 5),
				"expected_time": flt(busy[0].actual_time) + 60,
			},
			update_modified=False,
		)


def _progress(project, done_through, half_way):
	"""The template's phases: those before `done_through` done, the one at
	`half_way` half done with its next task under way, the rest still to
	come."""
	people = ("rania@one.test", "nadia@one.test", "karim@one.test", "tariq@one.test", "yousef@one.test")
	for i, (phase, tasks) in enumerate(PHASES, 1):
		for j, (subject, *_rest) in enumerate(tasks):
			task = frappe.db.get_value(
				"Task", {"project": project, "subject": subject}, ["name", "exp_end_date"], as_dict=True
			)
			if not task:
				continue
			_assign(task.name, people[(i + j) % len(people)])
			if i < done_through or ((i == done_through and j < len(tasks)) and i <= done_through):
				_finish(task.name, "Completed", task.exp_end_date)
			elif i == half_way and j < len(tasks) // 2:
				_finish(task.name, "Completed", task.exp_end_date)
			elif i == half_way and j == len(tasks) // 2:
				_finish(task.name, "Working", None)
		milestone = frappe.db.get_value("Task", {"project": project, "subject": phase})
		if milestone and i <= done_through:
			_finish(milestone, "Completed", None)


def _milestone_shares(project, shares):
	for (phase, _tasks), share in zip(PHASES, shares, strict=True):
		milestone = frappe.db.get_value("Task", {"project": project, "subject": phase})
		if milestone:
			doc = frappe.get_doc("Task", milestone)
			doc.is_milestone = 1
			doc.one_bill_share = share
			doc.save()


def _estimates():
	"""Each project task's hours, so Workload has load to show: a few hours a
	day for the days it runs, more on some than others, and on open work more
	than what's logged on it so far. A to-do about a bill plans no hours."""
	tasks = frappe.get_all(
		"Task",
		filters={"is_template": 0, "is_group": 0, "is_milestone": 0, "expected_time": 0, "project": ["is", "set"], "owner": ["!=", AUTHOR]},
		fields=["name", "status", "exp_start_date", "exp_end_date", "actual_time"],
		order_by="name",
	)
	for i, task in enumerate(tasks):
		days = date_diff(task.exp_end_date, task.exp_start_date) + 1 if task.exp_start_date and task.exp_end_date else 2
		hours = min(max(days, 1), 5) * (2, 3, 4, 6)[i % 4]
		if task.status not in ("Completed", "Cancelled"):
			hours += flt(task.actual_time)
		elif flt(task.actual_time):
			hours = round(flt(task.actual_time) * (1.1, 0.9, 1.05, 1.0)[i % 4], 1)
		frappe.db.set_value("Task", task.name, "expected_time", hours, update_modified=False)


def _contacts():
	"""Each customer's project names who speaks for the customer, and the
	villa its installers too (Team › Contacts)."""
	for project in frappe.get_all(
		"Project", filters={"customer": ["is", "set"], "one_parent": ["is", "not set"]}, fields=["name", "customer"]
	):
		doc = frappe.get_doc("Project", project.name)
		if doc.get("one_contacts"):
			continue
		person = frappe.db.get_value(
			"Dynamic Link", {"link_doctype": "Customer", "link_name": project.customer, "parenttype": "Contact"}, "parent"
		)
		if person:
			doc.append("one_contacts", {"role": "Client's Representative", "contact": person})
		if doc.project_name == "Mansour Villa Windows and Doors":
			doc.append("one_contacts", {"role": "Subcontractor", "supplier": "Precision Installers", "note": "Fits the windows and doors"})
		if doc.get("one_contacts"):
			doc.save()


OWN = {
	PM: [
		("Call Acme about the lobby drawings", -2, "High", []),
		("Check the crane booking for the tower podium", 0, "Medium", []),
		("Prepare the site visit for the marina", 5, "Medium", ["Print the drawings", "Book the car", "Send the agenda"]),
	],
	"rania@one.test": [
		("Renew the site safety card", 3, "Medium", []),
	],
	ACCOUNTS_USER: [
		("Send Samir the week's cash position", 4, "Medium", ["Match the bank", "List what is due this week"]),
	],
}

REPEATS = {(ACCOUNTS_USER, "Send Samir the week's cash position"): "Weekly"}


def _own():
	"""Each person's own to-dos, made by them, as My Tasks' quick add makes
	them: in no project, given to whoever made them (one_task/capture.py)."""
	for user, tasks in OWN.items():
		with as_user(user):
			for subject, days, priority, steps in tasks:
				name = frappe.db.get_value("Task", {"subject": subject, "owner": user})
				if not name:
					name = frappe.get_doc(
						{
							"doctype": "Task",
							"subject": subject,
							"priority": priority,
							"exp_end_date": ahead(days) if days >= 0 else ago(-days),
							"one_steps": [{"step": step} for step in steps],
						}
					).insert().name
				often = REPEATS.get((user, subject))
				if often and not frappe.db.get_value("Task", name, "auto_repeat"):
					from frappe.automation.doctype.auto_repeat.auto_repeat import make_auto_repeat

					repeat = make_auto_repeat("Task", name, often)
					frappe.db.set_value("Task", name, "auto_repeat", repeat.name, update_modified=False)


def _assign(task, user):
	from frappe.desk.form.assign_to import add

	if user and not frappe.db.exists(
		"ToDo", {"reference_type": "Task", "reference_name": task, "allocated_to": user, "status": "Open"}
	):
		add({"doctype": "Task", "name": task, "assign_to": [user], "notify": 0})


def _finish(task, status, on_day):
	if status in ("Open", None):
		return
	doc = frappe.get_doc("Task", task)
	if doc.status == status:
		return
	if status == "Completed":
		for row in doc.depends_on:
			_finish(row.task, "Completed", on_day)
		doc.reload()
		doc.completed_on = min(getdate(on_day or today()), today())
		doc.completed_by = PM
	doc.status = status
	doc.save()


def _time(project, people, activity, starts, weeks, hours, phase=None, task=True):
	"""A timesheet a week for each person, for so many weeks, or up to this
	week where work still goes on (None). Each day is on the project's task
	under way then, in `phase` where it is given, or on none (`task` False),
	as running a job is."""
	from onedesk.one_project.hours import bills_hours

	filters = {"project": project, "is_group": 0}
	if phase:
		filters["parent_task"] = frappe.db.get_value("Task", {"project": project, "subject": phase, "is_group": 1})
	tasks = (
		frappe.get_all(
			"Task",
			filters=filters,
			fields=["name", "status", "exp_start_date", "exp_end_date"],
			order_by="exp_start_date asc",
		)
		if task
		else []
	)
	billable = 1 if bills_hours(project) else 0
	if weeks is None:
		weeks = date_diff(today(), starts) // 7 + 1
	for first in people:
		employee = frappe.db.get_value("Employee", {"first_name": first})
		for week in range(weeks):
			begins = add_days(starts, week * 7)
			if begins >= today():
				break
			sheet = frappe.new_doc("Timesheet")
			sheet.employee = employee
			sheet.company = COMPANY
			sheet.parent_project = project
			for day in range(min(5, max(1, round(hours / 6)))):
				when = add_days(begins, day)
				if when >= today():
					break
				sheet.append(
					"time_logs",
					{
						"activity_type": activity,
						"from_time": _free(employee, when),
						"hours": round(hours / 5, 1),
						"project": project,
						"is_billable": billable,
						**_on(tasks, when),
					},
				)
			if sheet.time_logs:
				with as_user(frappe.db.get_value("Employee", employee, "user_id") or PM):
					save(sheet)
				with as_user(PM):
					sheet.reload()
					sheet.submit()


def _on(tasks, day):
	"""The task a day's time goes on: the one scheduled that day, or the last
	one begun. A log on a task already done is marked completed, since
	ERPNext sets a task with time logged on it back to Working otherwise."""
	day = getdate(day)
	started = [t for t in tasks if t.exp_start_date and getdate(t.exp_start_date) <= day]
	found = next(
		(t for t in started if day <= getdate(t.exp_end_date or day)),
		started[-1] if started else None,
	)
	if not found:
		return {}
	return {"task": found.name, "completed": int(found.status == "Completed")}


def _free(employee, day):
	"""When the person's day is free from: eight, or after what they have
	logged that day on another project."""
	last = frappe.db.sql(
		"""select max(log.to_time) from `tabTimesheet Detail` log
		join `tabTimesheet` sheet on sheet.name = log.parent
		where sheet.employee = %s and sheet.docstatus < 2 and date(log.from_time) = %s""",
		(employee, day),
	)[0][0]
	return str(last) if last else f"{day} 08:00:00"


def _extra_work(parent, customer, title, lines, date):
	"""Extra work the customer asks for: a quotation marked as extra work,
	ordered, which makes it a sub-project (billing.ordered)."""
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	quote = frappe.new_doc("Quotation")
	quote.update(
		{
			"quotation_to": "Customer",
			"party_name": customer,
			"project": parent,
			"one_extra_work": 1,
			"title": title,
		}
	)
	dated(quote, date, "transaction_date")
	quote.valid_till = add_days(date, 30)
	for code, qty, rate in lines:
		quote.append("items", {"item_code": code, "qty": qty, "rate": rate})
	save(quote, submit=True)
	order = make_sales_order(quote.name)
	dated(order, add_days(date, 6), "transaction_date")
	order.delivery_date = ahead(40)
	for row in order.items:
		row.delivery_date = order.delivery_date
	save(order, submit=True)


def _retainer(project, first_month, months, people, hours):
	from onedesk.one_project.retainer import invoice_month

	for i in range(months):
		month = get_first_day(add_months(on(first_month, 1), i))
		_time(
			project,
			people,
			"Maintenance",
			add_days(month, 2),
			weeks=4,
			hours=hours[i % len(hours)],
		)
		with as_user(ACCOUNTS_USER):
			draft = invoice_month(project, month=str(month), item="SVC-MAINT", overage=1)
			_redate(draft, add_days(add_months(month, 1), -1))
			invoice = save(draft, submit=True)
		if date_diff(today(), invoice.posting_date) > 40:
			_pay(invoice, add_days(invoice.posting_date, 21))
	month = get_first_day(add_months(on(first_month, 1), months))
	_time(project, people, "Maintenance", add_days(month, 2), weeks=None, hours=hours[months % len(hours)])


def _update(project, note, date, by):
	"""A team member's update, given on the day it was asked for."""
	from onedesk.one_project.updates import post

	with as_user(by):
		made = post(project, note)
	frappe.db.set_value("Project Update", made, "date", date)


COST_TYPES = {
	"Materials": "Cost of Goods Sold",
	"Subcontracts": "Subcontract Costs",
	"Labour": "Site Labour",
	"Equipment": "Equipment Hire",
}


def _accounts():
	parent = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_name": "Direct Expenses", "is_group": 1}
	)
	for name in ("Subcontract Costs", "Site Labour", "Equipment Hire"):
		if not frappe.db.exists("Account", account(name)):
			make(
				{
					"doctype": "Account",
					"account_name": name,
					"parent_account": parent,
					"company": COMPANY,
					"account_type": "Expense Account",
				}
			)
	item = frappe.get_doc("Item", "SVC-SUB")
	row = next((one for one in item.item_defaults if one.company == COMPANY), None) or item.append(
		"item_defaults", {"company": COMPANY}
	)
	if row.expense_account != account("Subcontract Costs"):
		row.expense_account = account("Subcontract Costs")
		item.save()


AGREED = {
	"Bayview Tower Curtain Wall": (None, "Construction Works"),
	"Acme New York Lobby": ("Net 30", "Construction Works"),
	"Nordlicht Showroom Design": ("Net 15", "Professional Services"),
	"Marina Hotels Glazing Care": ("Net 15", "Professional Services"),
}


SUBCONTRACT = "Subcontract Agreement"


def _terms():
	"""The workspace's payment terms and terms and conditions, as copying the
	library's presets makes them, and Bayview's own terms: 45 days. A glazing
	company holds retention, so the workspace does."""
	frappe.db.set_single_value("Projects Settings", "one_retention", 1)
	for key in ("Net 15", "Net 30", "Net 45"):
		library._payment_terms(key)
	for key in ("Construction Works", "Professional Services"):
		library._conditions(key)
	if not frappe.db.exists("Contract Template", SUBCONTRACT):
		frappe.get_doc(
			{
				"doctype": "Contract Template",
				"title": SUBCONTRACT,
				"contract_terms": "<p>The subcontractor carries out the package of work in its order, to the programme and the drawings issued. "
				"Work is billed as it is done, less the retention the order holds. Variations are agreed in writing before the work starts.</p>",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.get_value("Customer", "Bayview Developments", "payment_terms"):
		frappe.db.set_value("Customer", "Bayview Developments", "payment_terms", "Net 45")


def _template():
	"""The Aluminium & Glazing template, copied in from the library as a
	person's first use of it would."""
	tag(frappe.get_doc("Project Template", library.copy("aluminium_and_glazing")))
