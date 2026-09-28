"""Public holidays named in the workspace's language.

erpnext's `get_local_holidays` passed frappe's `en` to the `holidays`
package, which knows English as `en_US`, so a workspace set up in English
got its public holidays in the country's own language (Arabic in the
Emirates). A name nobody changed is renamed into the workspace's language;
a name somebody wrote stays (one/holidays.py, `local`)."""

import frappe
from frappe.utils import getdate


def execute():
	from holidays import country_holidays

	from onedesk.one import holidays

	frappe.local.lang = frappe.db.get_single_value("System Settings", "language") or "en"
	for held in frappe.get_all(
		"Holiday List",
		filters={"country": ["is", "set"]},
		fields=["name", "country", "subdivision", "from_date", "to_date"],
	):
		try:
			years = list(range(getdate(held.from_date).year, getdate(held.to_date).year + 1))
			native = country_holidays(held.country, subdiv=held.subdivision or None, years=years)
			wanted = {
				one["holiday_date"]: one["description"]
				for one in holidays.local(held.country, held.subdivision, held.from_date, held.to_date)
			}
		except Exception:
			continue
		for row in frappe.get_all(
			"Holiday",
			filters={"parent": held.name, "weekly_off": 0},
			fields=["name", "holiday_date", "description"],
		):
			day = getdate(row.holiday_date)
			said = frappe.utils.strip_html_tags(row.description or "").strip()
			better = wanted.get(str(day))
			if better and said == native.get(day) and said != better:
				frappe.db.set_value("Holiday", row.name, "description", better, update_modified=False)
