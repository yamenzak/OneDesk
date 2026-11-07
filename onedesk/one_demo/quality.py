"""OneQuality's demo: how a curtain wall is installed, the goal of getting
it right the first time and last month's review of it, the action the review
asked for, sealant laid in the cold against the procedure, the monthly quality
meeting, and what Marina Hotels thought of their pool fence."""

import frappe
from frappe.utils import add_days, add_months, get_first_day

from onedesk.one_demo.base import as_user, make, once, today

MANAGER = "karim@one.test"
SUPERVISOR = "tariq@one.test"

PROCEDURE = "Installing a Curtain Wall"
GOAL = "Installed Right the First Time"
TEMPLATE = "After Installation"

PARTS = ("_procedure", "_goal", "_review", "_nonconformance", "_meeting", "_feedback")


def run(password=None):
	for part in PARTS:
		globals()[part]()


def _procedure():
	with as_user(MANAGER):
		once(
			"Quality Procedure",
			{"quality_procedure_name": PROCEDURE},
			{
				"quality_procedure_name": PROCEDURE,
				"process_owner": SUPERVISOR,
				"processes": [
					{"process_description": step}
					for step in (
						"Survey the openings against the drawings and mark the anchor points.",
						"Fix the brackets and check them level with a laser.",
						"Hang the mullions and transoms, then glaze from the bottom up.",
						"Seal at 5°C or above, and leave it to cure before the cover caps go on.",
						"Water test one bay in ten, and clear the site of packaging.",
					)
				],
			},
		)


def _goal():
	with as_user(MANAGER):
		once(
			"Quality Goal",
			{"goal": GOAL},
			{
				"goal": GOAL,
				"procedure": PROCEDURE,
				"frequency": "Monthly",
				"date": "1",
				"objectives": [
					{"objective": "Bays that pass the water test at the first try", "target": "98", "uom": "Percent"},
					{"objective": "Snags the customer raises at handover", "target": "5", "uom": "Nos"},
				],
			},
		)


def _review():
	"""Last month's review, which failed on snags, and the action it asked for."""
	with as_user(MANAGER):
		review = once(
			"Quality Review",
			{"goal": GOAL},
			{
				"goal": GOAL,
				"procedure": PROCEDURE,
				"date": get_first_day(add_months(today(), -1)),
				"status": "Failed",
				"reviews": [
					{"objective": "Bays that pass the water test at the first try", "target": "98", "uom": "Percent", "review": "99 of 100 passed.", "status": "Passed"},
					{"objective": "Snags the customer raises at handover", "target": "5", "uom": "Nos", "review": "Bayview raised 9, most of them packaging left behind.", "status": "Failed"},
				],
				"additional_information": "Packaging left on site is now its own step of the procedure.",
			},
		)
		once(
			"Quality Action",
			{"review": review.name},
			{
				"corrective_preventive": "Corrective",
				"review": review.name,
				"goal": GOAL,
				"procedure": PROCEDURE,
				"date": add_days(review.date, 2),
				"status": "Open",
				"resolutions": [
					{
						"problem": "Crates and wrap left on finished floors.",
						"resolution": "The site supervisor signs each floor clear before the team leaves it.",
						"responsible": SUPERVISOR,
						"completion_by": add_days(today(), 14),
						"status": "Open",
					}
				],
			},
		)


def _nonconformance():
	"""Sealant laid in the cold, and the action taken on it: the bays sealed
	again, and the crews' briefing three days late."""
	with as_user(SUPERVISOR):
		problem = once(
			"Non Conformance",
			{"subject": "Sealant laid below 5°C"},
			{
				"subject": "Sealant laid below 5°C",
				"procedure": PROCEDURE,
				"status": "Open",
				"details": "Two bays on level 14 of Bayview Tower were sealed at 3°C before dawn.",
				"corrective_action": "Cut the sealant out of both bays and seal them again in the afternoon.",
				"preventive_action": "No sealing before 9 in the morning from December to February.",
			},
		)
	with as_user(MANAGER):
		once(
			"Quality Action",
			{"one_non_conformance": problem.name},
			{
				"corrective_preventive": "Corrective",
				"one_non_conformance": problem.name,
				"procedure": PROCEDURE,
				"date": add_days(today(), -6),
				"status": "Open",
				"resolutions": [
					{
						"problem": "Two bays on level 14 sealed at 3°C.",
						"resolution": "Sealant cut out and both bays sealed again in the afternoon.",
						"responsible": SUPERVISOR,
						"completion_by": add_days(today(), -5),
						"status": "Completed",
					},
					{
						"problem": "Crews not told about sealing in the cold.",
						"resolution": "Brief every installation crew on the 5°C rule at the morning talk.",
						"responsible": SUPERVISOR,
						"completion_by": add_days(today(), -3),
						"status": "Open",
					},
				],
			},
		)


def _meeting():
	with as_user(MANAGER):
		if frappe.db.exists("Quality Meeting", {}):
			return
		review = frappe.db.get_value("Quality Review", {"goal": GOAL})
		action = frappe.db.get_value("Quality Action", {"review": review})
		make(
			{
				"doctype": "Quality Meeting",
				"status": "Open",
				"agenda": [
					{"agenda": "Last month's review of installing right the first time"},
					{"agenda": "Sealing in the cold at Bayview"},
				],
				"minutes": [
					{"document_type": "Quality Review", "document_name": review, "minute": "Snags at handover were nearly twice the target."},
					{"document_type": "Quality Action", "document_name": action, "minute": "Tariq to have each floor signed clear from now on."},
				],
			}
		)


def _feedback():
	with as_user(MANAGER):
		once(
			"Quality Feedback Template",
			{"name": TEMPLATE},
			{
				"template": TEMPLATE,
				"parameters": [{"parameter": one} for one in ("Arrived on time", "Left the site clean", "Finish of the work")],
			},
		)
		if frappe.db.exists("Quality Feedback", {"document_name": "Marina Hotels Group"}):
			return
		make(
			{
				"doctype": "Quality Feedback",
				"template": TEMPLATE,
				"document_type": "Customer",
				"document_name": "Marina Hotels Group",
				"parameters": [
					{"parameter": "Arrived on time", "rating": "5"},
					{"parameter": "Left the site clean", "rating": "4"},
					{"parameter": "Finish of the work", "rating": "5", "feedback": "The pool fence looks like it floats."},
				],
			}
		)
