"""Jumeirah Family Clinic, the group's clinic: two doctors, a nurse and the
front desk. Patients pay for a visit on the day, two insurers are billed at
the end of each month and pay six weeks later, the clinic buys its gloves,
syringes and flu vaccine into its stores and uses them, and the doctors'
appointments are on the calendar. Care is zero-rated for VAT."""

import frappe
from frappe.utils import add_days

from onedesk.one_demo import clinic_field, firm
from onedesk.one_demo.base import as_user, dated, on, save, today
from onedesk.one_demo.firm import Firm, Person

FIRM = Firm(
	name=clinic_field.COMPANY,
	abbr="JFC",
	field=clinic_field.CLINIC.id,
	emirate="Dubai",
	street="Villa 22, Al Wasl Road, Jumeirah 1",
	phone="+971 4 344 7810",
	email="care@jumeirahclinic.test",
	website="jumeirahclinic.test",
	tax_id="100512345600003",
	bank="Mashreq",
	iban="AE230331019101234567890",
	sales_tax="UAE VAT Zero",
	opening=400000,
	people=(
		Person("Salma", "Rahimi", "salma@one.test", "Management", "Clinic Manager", "Female", "2021-03-14", 22000, (("one_book", "Manager"), ("one_calendar", "Manager"), ("one_inventory", "Manager"), ("one_crm", "User"), ("one_display", "Manager"))),
		Person("Rami", "Saad", "rami@one.test", "Operations", "General Practitioner", "Male", "2021-04-01", 28000, (("one_calendar", "User"), ("one_task", "User"))),
		Person("Aylin", "Demir", None, "Operations", "Paediatrician", "Female", "2022-09-12", 26000),
		Person("Joy", "Santos", None, "Operations", "Nurse", "Female", "2021-04-01", 8500),
		Person("Hiba", "Khalil", None, "Customer Service", "Receptionist", "Female", "2023-01-15", 6500),
	),
)

MANAGER = "salma@one.test"
DOCTOR = "rami@one.test"

ITEMS = (
	("JFC-GP", "General Consultation", "Medical Services", "Nos", 350, False),
	("JFC-PAED", "Paediatric Consultation", "Medical Services", "Nos", 450, False),
	("JFC-LAB", "Blood Test Panel", "Medical Services", "Nos", 280, False),
	("JFC-VAX", "Flu Vaccination", "Medical Services", "Nos", 120, False),
	("JFC-FLU", "Influenza Vaccine Dose", "Medical Supplies", "Nos", 90, True),
	("JFC-GLV", "Nitrile Gloves, Box of 100", "Medical Supplies", "Box", 0, True),
	("JFC-SYR", "Syringes 5 ml, Box of 100", "Medical Supplies", "Box", 0, True),
	("JFC-LABOUT", "Outsourced Laboratory Tests", "Medical Services", "Nos", 0, False),
)

INSURERS = (
	("Gulf Shield Health Insurance", ("Rana", "Haddad"), "claims@gulfshield.example", "+97142290100"),
	("Crescent Care Insurance", ("Imad", "Fakhoury"), "providers@crescentcare.example", "+97143310200"),
)

PATIENTS = (
	("Emma Clarke", "emma.clarke@example.com", "+971501230011"),
	("Rohan Mehta", "rohan.mehta@example.com", "+971501230022"),
	("Noura Al Shamsi", "noura.alshamsi@example.com", "+971501230033"),
	("Oliver Bennett", "oliver.bennett@example.com", "+971501230044"),
	("Latifa Al Zaabi", "latifa.alzaabi@example.com", "+971501230055"),
)

SUPPLIERS = (
	("Medline Gulf Supplies", "Local", "orders@medlinegulf.example", ("Anil", "Varghese")),
	("Emirates Vaccines Distribution", "Local", "sales@emiratesvaccines.example", ("Huda", "Al Kaabi")),
	("Dubai Diagnostics Lab", "Services", "accounts@dubaidiagnostics.example", ("Peter", "Novak")),
)

BOUGHT = (
	("Medline Gulf Supplies", (1, 8), "MGS-24011", (("JFC-GLV", 40, 32), ("JFC-SYR", 30, 45)), (1, 30), 1),
	("Medline Gulf Supplies", (4, 10), "MGS-24187", (("JFC-GLV", 40, 32), ("JFC-SYR", 20, 45)), (5, 8), 1),
	("Medline Gulf Supplies", (7, 14), "MGS-24390", (("JFC-GLV", 30, 33),), None, 0),
	("Emirates Vaccines Distribution", (9, 15), "EVD-7720", (("JFC-FLU", 300, 38),), (10, 15), 0.5),
)

LAB = (((3, 31), "DDL-2601", 8400, (4, 20)), ((6, 30), "DDL-2602", 9150, (7, 21)), ((9, 30), "DDL-2603", 9900, None))

USED = (((3, 31), 25, 15), ((6, 30), 28, 18), ((9, 30), 30, 12))
"""Each quarter's gloves and syringes taken from the stores."""

VISITS = (
	((1, 12), "Emma Clarke", (("JFC-GP", 1, 350),)),
	((2, 3), "Rohan Mehta", (("JFC-GP", 1, 350), ("JFC-LAB", 1, 280))),
	((2, 20), "Noura Al Shamsi", (("JFC-PAED", 1, 450),)),
	((3, 9), "Oliver Bennett", (("JFC-GP", 1, 350),)),
	((4, 22), "Latifa Al Zaabi", (("JFC-PAED", 1, 450), ("JFC-LAB", 1, 280))),
	((6, 5), "Emma Clarke", (("JFC-LAB", 1, 280),)),
	((8, 18), "Rohan Mehta", (("JFC-GP", 1, 350),)),
	((10, 2), "Noura Al Shamsi", (("JFC-VAX", 1, 120), ("JFC-FLU", 1, 90))),
	((10, 6), "Oliver Bennett", (("JFC-VAX", 1, 120), ("JFC-FLU", 1, 90))),
	((10, 21), "Latifa Al Zaabi", (("JFC-VAX", 2, 120), ("JFC-FLU", 2, 90))),
	((11, 4), "Emma Clarke", (("JFC-GP", 1, 350),)),
)
"""Patients who pay for their own visit, at the desk on the day."""

CLAIMS = {
	"Gulf Shield Health Insurance": (
		(158, 64, 92),
		(149, 71, 88),
		(171, 66, 97),
		(162, 70, 90),
		(168, 74, 95),
		(141, 58, 80),
		(122, 49, 71),
		(130, 55, 76),
		(176, 79, 101),
		(184, 83, 108),
	),
	"Crescent Care Insurance": (
		(58, 33, 39),
		(61, 30, 41),
		(55, 36, 37),
		(64, 29, 43),
		(60, 34, 40),
		(49, 27, 33),
		(44, 22, 30),
		(47, 25, 32),
		(63, 37, 42),
		(67, 39, 45),
	),
}
"""Each month's consultations, children's consultations and blood tests
billed to each insurer, at the rates agreed with it."""

AGREED = (300, 400, 240)

SHORT = {("Crescent Care Insurance", 9): 0.6}
"""A month an insurer paid only part of, holding back what it questioned."""

APPOINTMENTS = (
	(-3, "09:00", "Emma Clarke", "Follow-up on blood results"),
	(-1, "11:30", "Rohan Mehta", "Consultation"),
	(1, "09:30", "Oliver Bennett", "Consultation"),
	(1, "16:00", "Noura Al Shamsi", "Child's vaccination"),
	(2, "10:00", "Latifa Al Zaabi", "Annual check-up"),
	(4, "15:30", "Emma Clarke", "Consultation"),
)
"""Rami's appointments around today, days from it."""


def run(password=None):
	bank = firm.settle(FIRM, password)
	for code, name, group, uom, price, stocked in ITEMS:
		firm.item(code, name, group, uom, price, stocked)
	for name, contact, email, phone in INSURERS:
		firm.customer(name, "Company", email, phone, contact)
	for name, email, phone in PATIENTS:
		firm.customer(name, "Individual", email, phone)
	for name, group, email, contact in SUPPLIERS:
		firm.supplier(name, group, email, contact)
	if not frappe.db.exists("Sales Invoice", {"company": FIRM.name, "docstatus": 1}):
		_bought()
		_used()
		_seen()
		_claimed()
	firm.monthly(FIRM, bank, 18500, (2900, 2750, 3100, 3600, 4300, 5200, 5900, 6100, 5300, 4200, 3300))
	_booked()


def _bought():
	for supplier, day, number, lines, paid, part in BOUGHT:
		bill = firm.buy(FIRM, MANAGER, supplier, on(*day), number, lines, stock=True)
		if paid:
			firm.settled(FIRM, MANAGER, bill, on(*paid), part)
	for day, number, amount, paid in LAB:
		bill = firm.buy(FIRM, MANAGER, "Dubai Diagnostics Lab", on(*day), number, (("JFC-LABOUT", 1, amount, "Laboratory Costs"),))
		if paid:
			firm.settled(FIRM, MANAGER, bill, on(*paid))


def _used():
	"""What the nurses took from the stores each quarter, as a Material Issue."""
	for day, gloves, syringes in USED:
		with as_user(MANAGER):
			doc = frappe.new_doc("Stock Entry")
			doc.stock_entry_type = "Material Issue"
			doc.company = FIRM.name
			dated(doc, on(*day))
			doc.from_warehouse = FIRM.wh("Stores")
			doc.remarks = "Gloves and syringes used in the treatment rooms this quarter"
			for code, qty in (("JFC-GLV", gloves), ("JFC-SYR", syringes)):
				doc.append("items", {"item_code": code, "qty": qty, "s_warehouse": FIRM.wh("Stores")})
			save(doc, submit=True)


def _seen():
	for day, patient, lines in VISITS:
		stock = any(code == "JFC-FLU" for code, *_ in lines)
		invoice = firm.sell(FIRM, MANAGER, patient, on(*day), lines, due=0, stock=stock)
		firm.settled(FIRM, MANAGER, invoice, on(*day), reference=f"CARD-{invoice.name.rsplit('-', 1)[-1]}")


def _claimed():
	"""Each insurer's month, billed on its last day and paid six weeks on."""
	from frappe.utils import get_last_day

	for insurer, months in CLAIMS.items():
		for month, counts in enumerate(months, start=1):
			if month > today().month - 1:
				break
			ends = get_last_day(on(month, 1))
			lines = tuple((code, qty, rate) for code, qty, rate in zip(("JFC-GP", "JFC-PAED", "JFC-LAB"), counts, AGREED, strict=True))
			invoice = firm.sell(FIRM, MANAGER, insurer, ends, lines, due=45, remarks=f"Claims for {ends.strftime('%B')}")
			firm.settled(FIRM, MANAGER, invoice, add_days(ends, 42), SHORT.get((insurer, month), 1.0))


def _booked():
	"""Rami's appointments, each booked by the front desk for the patient."""
	for days, at, patient, why in APPOINTMENTS:
		firm.event(
			MANAGER,
			f"{why}: {patient}",
			f"{add_days(today(), days)} {at}:00",
			0.5,
			team=(DOCTOR,),
			about=("Customer", frappe.db.get_value("Customer", {"customer_name": patient})),
			place="Consultation room 2",
		)
