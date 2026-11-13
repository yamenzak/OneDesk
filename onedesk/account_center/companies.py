"""Companies, in AccountCenter's Workspace: the workspace's companies, each
frappe's own Company, and another made as the setup job makes every company
after the first (one/setup_job.py, company), so it pays payroll and sends
invoices from the start. An administrator's alone (roles.require)."""

from typing import Annotated

import frappe
from frappe import _

from onedesk.one import roles, setup_answers
from onedesk.one.companies import LETTER_HEADS


def asked(name: str | None, country: str | None, currency: str | None, chart: str | None, letter_head: str | None) -> dict:
	"""The company as the setup job takes it, from what the dialog sent, or
	ValueError saying what is wrong. Pure."""
	name = " ".join((name or "").split())
	if not name:
		raise ValueError(_("Company Name is required."))
	if not country:
		raise ValueError(_("Country is required."))
	chart = chart or setup_answers.CHARTS[0]
	if chart not in setup_answers.CHARTS:
		raise ValueError(_("{0} is not a chart of accounts a company can be made with.").format(chart))
	letter_head = letter_head or LETTER_HEADS[0]
	if letter_head not in LETTER_HEADS:
		raise ValueError(_("{0} is not a letter head choice.").format(letter_head))
	said = {"name": name, "country": country, "chart": chart, "letter_head": letter_head}
	if currency:
		said["currency"] = currency
	return said


def rows(companies: list[dict], default: str | None) -> list[dict]:
	"""Each company as the section lists it, the default first. Pure."""
	return sorted(
		({**one, "default": one["name"] == default} for one in companies),
		key=lambda one: (not one["default"], one["name"].lower()),
	)


def listed() -> dict:
	"""The section: every company, the first company's letter head, and
	what a new one is asked first."""
	from onedesk.one.company import workspace_company

	default = workspace_company()
	held = frappe.get_all("Company", fields=["name", "abbr", "country", "default_currency", "default_letter_head"], limit_page_length=0)
	first = next((one for one in held if one["name"] == default), {})
	return {
		"companies": rows(held, default),
		"country": first.get("country"),
		"letter_head": first.get("default_letter_head") or frappe.db.get_value("Letter Head", {"is_default": 1, "disabled": 0}),
		"charts": list(setup_answers.CHARTS),
	}


@frappe.whitelist()
@frappe.read_only()
def currency(country: Annotated[str, "The country."]) -> str | None:
	"""The country's own currency, which a new company is offered."""
	from frappe.geo.country_info import get_country_info

	roles.require()
	return (get_country_info(country) or {}).get("currency")


@frappe.whitelist(methods=["POST"])
def make(
	company_name: Annotated[str, "The company's name."],
	country: Annotated[str, "Its country."],
	currency: Annotated[str | None, "Its currency, the country's when not said."] = None,
	chart: Annotated[str | None, "Standard or Standard with Numbers."] = None,
	letter_head: Annotated[str | None, "own for a new letter head with its name, first for the first company's."] = None,
) -> str:
	"""Make another company, as the setup job makes every company after the
	first. Only an administrator of the workspace may."""
	from onedesk.one import setup_job

	roles.require()
	try:
		said = asked(company_name, country, currency, chart, letter_head)
	except ValueError as wrong:
		frappe.throw(str(wrong))
	if frappe.db.exists("Company", said["name"]):
		frappe.throw(_("{0} already exists.").format(said["name"]), frappe.DuplicateEntryError)
	if not frappe.db.exists("Country", said["country"]):
		frappe.throw(_("{0} is not a country.").format(said["country"]))
	if said.get("currency") and not frappe.db.exists("Currency", said["currency"]):
		frappe.throw(_("{0} is not a currency.").format(said["currency"]))
	return setup_job.company(said)
