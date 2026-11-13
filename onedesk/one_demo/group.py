"""The group the demo's companies belong to: Al Mansoori Holding, Faisal's
family holding, owns Sahara Glass and its Saudi company and four companies
in other fields, each declared beside the step that builds its year. The
setup job makes the holding and the four with Sahara Glass (setup.answers);
this step joins the Saudi company, which branch makes, to the group."""

import frappe

HOLDING = "Al Mansoori Holding"
HOLDING_ABBR = "AMH"


def members():
	"""The four companies after Sahara Glass, in the order they are built."""
	from onedesk.one_demo import clinic, consulting, realty, trading

	return (clinic.FIRM, realty.FIRM, trading.FIRM, consulting.FIRM)


def answers() -> list[dict]:
	"""The holding and the four, as the setup job's answers give them."""
	holding = {"name": HOLDING, "abbr": HOLDING_ABBR, "country": "United Arab Emirates", "currency": "AED", "chart": "Standard", "year_starts": "01-01"}
	return [holding, *(one.answer(HOLDING) for one in members())]


def invited() -> list[dict]:
	return [person for one in members() for person in one.invited()]


def run(password=None):
	from onedesk.one.companies import join
	from onedesk.one_demo.branch import BRANCH

	if frappe.db.exists("Company", BRANCH):
		join(BRANCH, HOLDING)
