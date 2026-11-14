"""Palm Key Properties, the group's real estate agency in Dubai Marina: it
lets homes and offices for their landlords and manages most of them, and
sells for owners. Each tenancy is a signed contract with the tenant, who
pays the agency's fee of five per cent of the year's rent when it is signed;
a landlord is billed each month for the homes the agency manages; a seller
pays two per cent when a sale goes through. Zayed's viewings are on the
calendar."""

import frappe
from frappe.utils import add_days, add_months, get_last_day

from onedesk.one_demo import firm, realty_field
from onedesk.one_demo.base import as_user, make, on, today
from onedesk.one_demo.firm import Firm, Person

FIRM = Firm(
	name=realty_field.COMPANY,
	abbr="PKP",
	field=realty_field.REAL_ESTATE.id,
	emirate="Dubai",
	street="Office 1402, Marina Plaza, Dubai Marina",
	phone="+971 4 455 9120",
	email="hello@palmkey.test",
	website="palmkey.test",
	tax_id="100623456700003",
	bank="Emirates Islamic",
	iban="AE900342201477350010001",
	sales_tax="UAE VAT 5%",
	opening=180000,
	people=(
		Person("Sophie", "Laurent", "sophie@one.test", "Management", "Managing Broker", "Female", "2020-02-03", 18000, (("one_crm", "Manager"), ("one_book", "Manager"), ("one_calendar", "User"), ("one_portal", "Manager"))),
		Person("Zayed", "Al Falasi", "zayed@one.test", "Sales", "Leasing Agent", "Male", "2022-06-19", 5000, (("one_crm", "User"), ("one_calendar", "User"))),
		Person("Joanna", "Silva", None, "Operations", "Property Manager", "Female", "2021-10-04", 9000),
		Person("Hamad", "Al Suwaidi", None, "Sales", "Sales Agent", "Male", "2023-05-21", 5000),
	),
)

BROKER = "sophie@one.test"
AGENT = "zayed@one.test"

ITEMS = (
	("PKP-LET", "Letting Fee", "Property Services", "Nos", None, False),
	("PKP-MGMT", "Property Management, a Month", "Property Services", "Nos", None, False),
	("PKP-SALE", "Sales Commission", "Property Services", "Nos", None, False),
	("PKP-ADS", "Property Listing Subscription", "Property Services", "Nos", 0, False),
	("PKP-PRINT", "Printing and Signage", "Property Services", "Nos", 0, False),
	("PKP-CLEAN", "Handover Cleaning", "Property Services", "Nos", 0, False),
)

OWNERS = (
	("Robert Hale", "Individual", "robert.hale@example.com", "+447700900311", None),
	("Al Sufouh Investments", "Company", "leasing@alsufouhinv.example", "+97143990120", ("Omar", "Bin Hendi")),
	("Priya Raman", "Individual", "priya.raman@example.com", "+971502770144", None),
)

TENANTS = (
	("Claire Dubois", "Individual", "claire.dubois@example.com", "+971503110021", None),
	("Lumen Tech FZ-LLC", "Company", "office@lumentech.example", "+97143210088", ("Daniel", "Okafor")),
	("Nadeem Qureshi", "Individual", "nadeem.qureshi@example.com", "+971503110043", None),
	("Hannah Weiss", "Individual", "hannah.weiss@example.com", "+971503110054", None),
	("Saeed Al Amiri", "Individual", "saeed.alamiri@example.com", "+971503110065", None),
	("Kestrel Advisory DMCC", "Company", "admin@kestreladvisory.example", "+97144320177", ("Laura", "Finch")),
	("Kofi Mensah", "Individual", "kofi.mensah@example.com", "+971503110087", None),
	("Ali Reza Tehrani", "Individual", "alireza.tehrani@example.com", "+971503110098", None),
	("Isabel Romero", "Individual", "isabel.romero@example.com", "+971503110109", None),
	("Arjun Nair", "Individual", "arjun.nair@example.com", "+971503110110", None),
)

SELLERS = (
	("Elena Petrova", "Individual", "elena.petrova@example.com", "+79161230045", None),
	("Hamdan Al Mazrouei", "Individual", "hamdan.almazrouei@example.com", "+971506220031", None),
	("Ingrid Svensson", "Individual", "ingrid.svensson@example.com", "+46701230099", None),
	("Marcus Lindqvist", "Individual", "marcus.lindqvist@example.com", "+46701230188", None),
	("Sultan Al Ketbi", "Individual", "sultan.alketbi@example.com", "+971506220077", None),
)

LEASES = (
	("Claire Dubois", "Robert Hale", "Marina Gate 2, Apartment 1804", 145000, (1, 15), True),
	("Lumen Tech FZ-LLC", "Al Sufouh Investments", "Al Sufouh Business Tower, Office 905", 210000, (2, 1), True),
	("Nadeem Qureshi", "Al Sufouh Investments", "Lake View Tower, JLT, Apartment 2207", 98000, (3, 10), True),
	("Hannah Weiss", "Al Sufouh Investments", "Delphine Tower, Marina Promenade, Apartment 1506", 165000, (4, 3), True),
	("Saeed Al Amiri", "Priya Raman", "Arabian Ranches, Villa 47", 260000, (5, 1), False),
	("Kestrel Advisory DMCC", "Robert Hale", "Jumeirah Bay X2, Office 1203", 185000, (6, 15), True),
	("Kofi Mensah", "Al Sufouh Investments", "Bay Central, Dubai Marina, Apartment 1112", 120000, (7, 20), True),
	("Ali Reza Tehrani", "Priya Raman", "Town Square, Zahra Townhouse 18", 115000, (8, 8), False),
	("Isabel Romero", "Robert Hale", "Executive Tower B, Business Bay, Apartment 3010", 135000, (9, 1), True),
	("Arjun Nair", "Priya Raman", "Belgravia 3, JVC, Apartment 402", 72000, (10, 15), False),
)
"""(tenant, landlord, property, the year's rent, first day, managed by us)"""

SALES = (
	("Elena Petrova", "Shoreline 8, Palm Jumeirah, Apartment 604", 3400000, (3, 18), (4, 2), 1.0),
	("Ingrid Svensson", "The Nest, Al Barari, Villa 4", 5100000, (5, 20), (6, 5), 1.0),
	("Hamdan Al Mazrouei", "Maple 2, Dubai Hills Estate, Villa 118", 4150000, (6, 12), (6, 30), 1.0),
	("Marcus Lindqvist", "Burj Vista 1, Downtown, Apartment 2405", 2850000, (8, 27), (9, 15), 1.0),
	("Elena Petrova", "Sunrise Bay, Emaar Beachfront, Apartment 1907", 3900000, (9, 24), (10, 10), 0.5),
	("Sultan Al Ketbi", "Jumeirah Islands, Cluster 12, Villa 9", 6200000, (10, 29), None, 0),
)
"""(seller, property, price, transfer day, paid on, part paid)"""

LATE = {("Robert Hale", 9)}
"""A landlord's month still unpaid."""

SUPPLIERS = (
	("Dubai Listings Portal", "Services", "billing@dubailistings.example", ("Sara", "Mahmoud")),
	("Marina Print & Signs", "Local", "orders@marinaprint.example", ("George", "Thomas")),
	("Clean Sweep Maintenance", "Services", "jobs@cleansweep.example", ("Bashir", "Rahman")),
)

BILLS = (
	("Dubai Listings Portal", (1, 5), "DLP-Q1-2291", "PKP-ADS", 9500, "Marketing Expenses", (1, 20)),
	("Clean Sweep Maintenance", (2, 25), "CSM-0418", "PKP-CLEAN", 1850, "Office Maintenance Expenses", (3, 10)),
	("Marina Print & Signs", (3, 2), "MPS-7731", "PKP-PRINT", 3800, "Print and Stationery", (3, 30)),
	("Dubai Listings Portal", (4, 5), "DLP-Q2-2417", "PKP-ADS", 9500, "Marketing Expenses", (4, 21)),
	("Dubai Listings Portal", (7, 5), "DLP-Q3-2560", "PKP-ADS", 9500, "Marketing Expenses", (7, 19)),
	("Clean Sweep Maintenance", (8, 2), "CSM-0593", "PKP-CLEAN", 2450, "Office Maintenance Expenses", (8, 30)),
	("Marina Print & Signs", (9, 10), "MPS-7904", "PKP-PRINT", 4600, "Print and Stationery", None),
	("Dubai Listings Portal", (10, 5), "DLP-Q4-2702", "PKP-ADS", 9500, "Marketing Expenses", (10, 20)),
)

VIEWINGS = (
	(-2, "17:00", "Viewing: Delphine Tower, Apartment 2210"),
	(-1, "11:00", "Viewing: Bay Central, Apartment 804"),
	(1, "18:00", "Viewing: Executive Tower B, Apartment 1702"),
	(3, "10:30", "Valuation visit: Arabian Ranches, Villa 112"),
)
"""Zayed's viewings around today, days from it."""


def run(password=None):
	bank = firm.settle(FIRM, password)
	for code, name, group, uom, price, stocked in ITEMS:
		firm.item(code, name, group, uom, price, stocked)
	for name, kind, email, phone, contact in (*OWNERS, *TENANTS, *SELLERS):
		firm.customer(name, kind, email, phone, contact)
	for name, group, email, contact in SUPPLIERS:
		firm.supplier(name, group, email, contact)
	if not frappe.db.exists("Sales Invoice", {"company": FIRM.name, "docstatus": 1}):
		_let()
		_managed()
		_sold()
		_billed()
	firm.monthly(FIRM, bank, 7500, (1200, 1150, 1250, 1400, 1650, 1900, 2100, 2150, 1850, 1500, 1300))
	for days, at, subject in VIEWINGS:
		firm.event(AGENT, subject, f"{add_days(today(), days)} {at}:00", 0.75, team=(BROKER,))


def _let():
	"""Each tenancy signed, and the tenant's fee invoiced and paid that week."""
	for tenant, landlord, place, rent, day, managed in LEASES:
		starts = on(*day)
		ends = add_days(add_months(starts, 12), -1)
		with as_user(BROKER):
			make(
				{
					"doctype": "Contract",
					"party_type": "Customer",
					"party_name": tenant,
					"start_date": starts,
					"end_date": ends,
					"is_signed": 1,
					"signee": tenant,
					"signed_on": f"{starts} 12:00:00",
					"contract_terms": (
						f"<p>Tenancy of {place}, let by {landlord} to {tenant} for twelve months from {starts}"
						f" at AED {rent:,} a year, paid in four cheques.</p>"
						+ (f"<p>{FIRM.name} manages the property for {landlord}.</p>" if managed else "")
					),
				},
				submit=True,
			)
		invoice = firm.sell(FIRM, BROKER, tenant, starts, (("PKP-LET", 1, round(rent * 0.05)),), due=7, remarks=f"Letting fee, {place}")
		firm.settled(FIRM, BROKER, invoice, add_days(starts, 2))


def _managed():
	"""Each landlord's month, for every home the agency managed in it: five
	per cent of its rent, billed on the month's last day and paid from the
	rent collected ten days on."""
	landlords = sorted({landlord for _t, landlord, *_r, managed in LEASES if managed})
	for month in range(1, today().month):
		ends = get_last_day(on(month, 1))
		for landlord in landlords:
			lines = tuple(
				("PKP-MGMT", 1, round(rent * 0.05 / 12), f"Management of {place}")
				for _tenant, owner, place, rent, day, managed in LEASES
				if managed and owner == landlord and on(*day) <= ends
			)
			if not lines:
				continue
			invoice = firm.sell(FIRM, BROKER, landlord, ends, lines, due=15, remarks=f"Management, {ends.strftime('%B')}")
			if (landlord, month) not in LATE:
				firm.settled(FIRM, BROKER, invoice, add_days(ends, 10))


def _sold():
	for seller, place, price, day, paid, part in SALES:
		invoice = firm.sell(FIRM, BROKER, seller, on(*day), (("PKP-SALE", 1, round(price * 0.02)),), due=14, remarks=f"Sale of {place} for AED {price:,}")
		if paid:
			firm.settled(FIRM, BROKER, invoice, on(*paid), part)


def _billed():
	for supplier, day, number, code, amount, spent, paid in BILLS:
		bill = firm.buy(FIRM, BROKER, supplier, on(*day), number, ((code, 1, amount, spent),))
		if paid:
			firm.settled(FIRM, BROKER, bill, on(*paid))
