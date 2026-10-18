"""The workspace set up as a new one is: frappe's setup wizard with One's own
questions answered, then the settings a contractor's books and stock want."""

import frappe
from frappe.utils import getdate

from onedesk.one_demo.base import ABBR, COMPANY, CURRENCY, today

BUILDER = "admin@example.com"


def run(password=None):
	if not frappe.is_setup_complete():
		from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

		year = today().year
		said = setup_complete(
			{
				"language": "English",
				"country": "United Arab Emirates",
				"timezone": "Asia/Dubai",
				"currency": CURRENCY,
				"full_name": "Workspace Builder",
				"email": BUILDER,
				"password": password or frappe.generate_hash(),
				"company_name": COMPANY,
				"company_abbr": ABBR,
				"fy_start_date": f"{year}-01-01",
				"fy_end_date": f"{year}-12-31",
				"setup_demo": 0,
				"onedesk_theme": "Light",
				"onedesk_day_starts": "08:00:00",
				"onedesk_day_ends": "17:00:00",
				"onedesk_weekly_off": "Sunday",
			}
		)
		if (said or {}).get("status") != "ok":
			frappe.throw(f"The setup wizard did not finish: {said}")
		frappe.db.commit()
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
