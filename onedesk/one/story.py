"""The months a Home's story counts by: the year to this month, and the month
a day falls in, the same on every story (OneBook, OneCRM, OneHR,
OneInventory). The arithmetic is figures.months."""

from datetime import date

from frappe.utils import add_months, get_first_day, getdate, today

from onedesk.one import figures

MONTHS = 12


def story_months(back: int = MONTHS, ahead: int = 0) -> list[date]:
	"""The first day of each month from `back` months to this one, this one
	counted, and `ahead` months after it, oldest first."""
	return figures.months(getdate(add_months(get_first_day(today()), ahead)), back + ahead)


def month_of(day) -> str:
	"""The month a day falls in, as its first day, the key a story's figures
	are kept by."""
	return get_first_day(getdate(day)).isoformat()
