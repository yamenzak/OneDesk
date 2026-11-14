"""The workspace set up as a new one is, through the same setup job a
signup's site runs (one/setup_job.py) with the demo's answers, then the
settings a contractor's books and stock want."""

import frappe
from frappe.utils import getdate

from onedesk.one import registry
from onedesk.one_demo.base import ABBR, COMPANY, CURRENCY, today

BUILDER = "faisal@one.test"


def answers(password=None) -> dict:
	"""What the demo's builder answers: Sahara Glass in Dubai, first, and the
	rest of Al Mansoori Holding's group (one_demo/group.py), its working week,
	and the team invited from People with the apps each one's work needs
	(one_demo/people.py), then each company's own people."""
	from onedesk.one_demo import group
	from onedesk.one_demo.making_field import CONTRACTING
	from onedesk.one_demo.people import OWNER, PEOPLE

	return {
		"owner": {"email": BUILDER, "first_name": "Faisal", "last_name": "Al Mansoori", "password": password or frappe.generate_hash()},
		"language": "en",
		"time_zone": "Asia/Dubai",
		"field": CONTRACTING.id,
		"theme": "Light",
		"companies": [
			{"name": COMPANY, "abbr": ABBR, "country": "United Arab Emirates", "currency": CURRENCY, "year_starts": "01-01", "parent": group.HOLDING},
			*group.answers(),
		],
		"working_day": {**CONTRACTING.answers["working_day"], "days_off": ["Sunday"]},
		"people": [
			{
				"email": email,
				"first_name": first,
				"last_name": last,
				"levels": {registry.by_name(name).id: level for name, level in (access or {}).items()},
				"admin": email == OWNER,
			}
			for first, last, email, *_rest, access in PEOPLE
			if email
		]
		+ group.invited(),
	}


def run(password=None):
	from onedesk.one import setup_job

	setup_job.run(answers(password))
	_kept()
	settle()


def settle():
	"""What a contractor sets once: rates for the currencies its customers and
	suppliers use, stock that may not go below nothing, and orders that reach
	their projects."""
	for currency, rate in (("USD", 3.6725), ("EUR", 3.98), ("GBP", 4.62)):
		frappe.db.set_value("Currency", currency, "enabled", 1)
		if not frappe.db.exists("Currency Exchange", {"from_currency": currency, "to_currency": CURRENCY}):
			frappe.get_doc(
				{
					"doctype": "Currency Exchange",
					"date": f"{today().year}-01-01",
					"from_currency": currency,
					"to_currency": CURRENCY,
					"exchange_rate": rate,
					"for_buying": 1,
					"for_selling": 1,
				}
			).insert()
	rose = getdate(f"{today().year}-07-20")
	if rose <= today() and not frappe.db.exists("Currency Exchange", {"from_currency": "EUR", "date": rose}):
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": rose,
				"from_currency": "EUR",
				"to_currency": CURRENCY,
				"exchange_rate": 4.05,
				"for_buying": 1,
				"for_selling": 1,
			}
		).insert()
	last_years()
	frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)
	frappe.db.set_single_value("Selling Settings", "so_required", "No")
	frappe.db.set_single_value("Buying Settings", "po_required", "No")
	frappe.db.set_single_value("Global Defaults", "default_company", COMPANY)
	frappe.db.set_default("company", COMPANY)


def last_years(back=3):
	"""The years before this one, for what was bought and depreciated before
	the workspace was set up: the wizard only makes the current year."""
	for year in range(today().year - back, today().year):
		if not frappe.db.exists("Fiscal Year", str(year)):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": str(year),
					"year_start_date": f"{year}-01-01",
					"year_end_date": f"{year}-12-31",
					"companies": [{"company": COMPANY}],
				}
			).insert()



def _kept() -> None:
	"""One of each thing an administrator sets up by hand in frappe: a
	module profile for the site crew, a layout of a non conformance for a
	report from site, and a package for the company's own changes."""
	if not frappe.db.exists("Module Profile", "Site Crew"):
		frappe.get_doc(
			{"doctype": "Module Profile", "module_profile_name": "Site Crew", "block_modules": [{"module": one} for one in ("Accounts", "Payroll", "Buying")]}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("DocType Layout", "Site Report"):
		frappe.get_doc({"doctype": "DocType Layout", "title": "Site Report", "document_type": "Non Conformance"}).insert(ignore_permissions=True)
	if not frappe.db.exists("Package", "Sahara-Customisations"):
		frappe.get_doc(
			{"doctype": "Package", "name": "Sahara-Customisations", "package_name": "Sahara-Customisations", "readme": "The fields and layouts Sahara Glass added to One, kept to move to a new workspace."}
		).insert(ignore_permissions=True)
