"""OneQuality's part of the integration suite (one_demo/check.py runs it):
procedures, goals, problems and their actions, as the people in quality
read them, and its one ability."""

import frappe

from onedesk.one_demo.checking import _Told, check
from onedesk.one_demo.quality import PROCEDURE


@check
def onequality_a_problem_is_raised_told_and_resolved():
	"""Tariq, who uses OneQuality, reads the curtain wall's procedure and
	raises a non conformance against it; Karim, who manages quality, is told,
	and only he may set it to Resolved. Anybody may report a problem, as
	ERPNext lets every employee, but nobody outside quality resolves one or
	changes a procedure."""
	from onedesk.one_demo.base import as_user
	from onedesk.one_quality import resolve

	with as_user("tariq@one.test"):
		assert frappe.has_permission("Quality Procedure", "read", doc=PROCEDURE)
		assert frappe.has_permission("Quality Action", "write") and not resolve.held()
		with _Told() as told:
			raised = frappe.get_doc(
				{"doctype": "Non Conformance", "subject": "Cover caps fitted before the sealant cured", "procedure": PROCEDURE, "status": "Open"}
			).insert()
		managers = told.to("Non Conformance Raised")
		assert "karim@one.test" in managers and "tariq@one.test" not in managers and "Administrator" not in managers, managers
		raised.status = "Resolved"
		try:
			raised.save()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a quality user resolved a non conformance")
	with as_user("karim@one.test"), _Told() as told:
		assert resolve.held()
		done = frappe.get_doc("Non Conformance", raised.name)
		done.status = "Resolved"
		done.save()
	assert told.to("Non Conformance Resolved") == {"tariq@one.test"}, told.said
	with as_user("nadia@one.test"):
		assert frappe.has_permission("Non Conformance", "create"), "anybody may report a problem"
		assert not resolve.held() and not frappe.has_permission("Quality Procedure", "write")


@check
def onequality_home_says_what_is_open_late_and_failing():
	"""OneQuality's Home: the sealant problem is open with its one action,
	the crews' briefing is overdue with Tariq, and the curtain wall's goal
	fails on last month's review, all Sahara's: Riyadh's problem is on
Riyadh's Home only. An action made from the problem carries it,
	and the problem counts it. Tariq is told the morning after a step of his
	was due. OneAI reads the same through quality_now. Somebody outside
	quality cannot open the Home."""
	from frappe.utils import add_days, today

	from onedesk.one_demo.base import as_user
	from onedesk.one_demo.quality import GOAL
	from onedesk.one_quality import agent, heads, home, tell

	problem = frappe.db.get_value("Non Conformance", {"subject": "Sealant laid below 5°C"})
	with as_user("karim@one.test"):
		said = home.read()
		rows = {one["name"]: one for one in said["needs"]["problems"]["rows"]}
		assert rows[problem]["actions"] >= 1, rows
		assert any(one["who"] == "Tariq Haidar" and one["late_by"] > 0 for one in said["needs"]["late"]["rows"]), said["needs"]["late"]
		assert GOAL in {one["goal"] for one in said["needs"]["failing"]["rows"]}
		assert said["figures"]["problems"] == said["needs"]["problems"]["count"]
		now = agent.quality_now()
		assert problem in {one["name"] for one in now["open"]} and now["overdue_count"] == said["needs"]["late"]["count"], now
		before = heads.nc_actions(frappe.get_doc("Non Conformance", problem))
		made = frappe.get_doc(
			{"doctype": "Quality Action", "corrective_preventive": "Preventive", "one_non_conformance": problem, "procedure": PROCEDURE, "status": "Open",
			 "resolutions": [{"problem": "Sealing before 9 in winter.", "resolution": "Start sealing after 9 from December.", "responsible": "tariq@one.test", "completion_by": add_days(today(), -1), "status": "Open"}]}
		).insert()
		assert heads.action_problem(made)["value"] == "Sealant laid below 5°C"
		after = heads.nc_actions(frappe.get_doc("Non Conformance", problem))
		assert after["value"] != before["value"], (before, after)
	with _Told() as told:
		tell.overdue()
	assert "tariq@one.test" in told.to("Quality Step Overdue"), told.said

	from onedesk.one_demo.branch import BRANCH

	assert not frappe.get_meta("Non Conformance").get_field("company").hidden, "with two companies a problem shows its company"
	there = frappe.get_doc({"doctype": "Non Conformance", "subject": "Showroom glass fitted unlabelled", "procedure": PROCEDURE, "company": BRANCH}).insert()
	with as_user("karim@one.test"):
		assert there.name not in {one["name"] for one in home.read()["needs"]["problems"]["rows"]}, "Sahara's Home showed Riyadh's problem"
	frappe.defaults.set_user_default("company", BRANCH, "karim@one.test")
	try:
		with as_user("karim@one.test"):
			riyadh = {one["name"] for one in home.read()["needs"]["problems"]["rows"]}
	finally:
		frappe.defaults.clear_user_default("company", "karim@one.test")
	assert there.name in riyadh and problem not in riyadh, riyadh
	with as_user("tariq@one.test"):
		filled = frappe.get_doc({"doctype": "Non Conformance", "subject": "Cap missing", "procedure": PROCEDURE}).insert()
	assert filled.company, "a problem saved with no company takes the reader's"
	with as_user("nadia@one.test"):
		assert agent.quality_now().get("error")
		try:
			home.read()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside quality opened OneQuality's Home")


@check
def onequality_the_inspector_raises_a_rejected_inspection():
	"""A Quality Inspection submitted as rejected is raised by OneQuality's
	inspector as a non conformance with its readings, through the agents'
	door at the level its tab shows, for whoever submitted it: made against
	the only procedure, or a card where it is not sure which. Submitted
	again, nothing more is raised."""
	from onedesk.one.registry import agents
	from onedesk.one_ai.agents import levels, work
	from onedesk.one_demo.checking import at_once

	received = frappe.get_all("Purchase Receipt Item", filters={"docstatus": 1}, fields=["parent", "item_code"], limit=1)[0]
	frappe.db.set_single_value("Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery", 1)
	inspection = frappe.get_doc(
		{
			"doctype": "Quality Inspection",
			"report_date": frappe.utils.today(),
			"inspection_type": "Incoming",
			"reference_type": "Purchase Receipt",
			"reference_name": received.parent,
			"item_code": received.item_code,
			"sample_size": 1,
			"inspected_by": "Administrator",
			"manual_inspection": 1,
			"status": "Rejected",
			"remarks": "Seals split on two of five.",
		}
	)
	with at_once():
		inspection.insert().submit()
	rows = frappe.get_all(
		"Reading Action",
		filters={"agent": agents.email("one_quality"), "agent_action": "raise_non_conformance", "key": f"one_quality|inspection|{inspection.name}"},
		fields=["name", "level", "agent_level", "target_name", "on_behalf_of"],
	)
	assert len(rows) == 1, rows
	row = rows[0]
	assert row.agent_level == levels.of("one_quality", "raise_non_conformance") == "Draft", row
	assert row.on_behalf_of == "Administrator", row
	only = len(frappe.get_all("Quality Procedure", filters={"is_group": 0}, limit=2)) == 1
	assert row.level == ("Done" if only else "Proposed"), row
	if row.level == "Done":
		problem = frappe.get_doc("Non Conformance", row.target_name)
		assert inspection.name in problem.subject and problem.status == "Open" and "Seals split" in problem.details, problem.as_dict()
		assert problem.owner == agents.email("one_quality"), problem.owner
	with at_once():
		assert work.do("one_quality", "raise_non_conformance", "Quality Inspection", inspection.name) in ([], [row.name])
	assert frappe.db.count("Reading Action", {"key": f"one_quality|inspection|{inspection.name}"}) == 1
