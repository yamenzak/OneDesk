"""OneTask's part of the integration suite (one_demo/check.py runs it): My
Tasks and the inbox as their reader has them, a task's own page, who sees
and ends a task, work arriving from OneAI and OneHR, and the one ability."""

import frappe
from frappe.utils import add_days, flt, today

from onedesk.one_demo.base import as_user, on
from onedesk.one_demo.check import SHOWROOM, VILLA, _Told, check
from onedesk.one_demo.people import OWNER


@check
def onetask_works_for_whoever_has_tasks():
	"""Rania's tasks, as My Tasks and OneAI read them, a step added and ticked,
	the timer started and stopped on one, and a task and its steps suggested
	as cards, and a change to one approved."""
	from onedesk.one_ai import proposals, tools
	from onedesk.one_task import ai, mine, task, timer

	with as_user("rania@one.test"):
		groups = mine.tasks("mine")
		counts = mine.counts()
		assert groups and counts.get("mine"), (groups, counts)
		assert ai.my_tasks("mine")["groups"]
		one = groups[0]["tasks"][0].name
		row = task.add_step(one, "Photograph the anchors")
		task.tick(one, row, 1)
		assert frappe.db.get_value("Task Step", row, "done") == 1
		timer.start(one)
		assert timer.running()["task"] == one
		timer.stop()
		assert not timer.running()
		other = next(task.name for group in groups for task in group["tasks"] if task.name != one)
		timer.start(one)
		timer.start(other)
		said = timer.timers()
		assert said["running"]["task"] == other and [p["task"] for p in said["paused"]] == [one], said
		timer.pause()
		said = timer.timers()
		assert not said["running"] and {p["task"] for p in said["paused"]} == {one, other}, said
		timer.start(one)
		assert timer.timers()["running"]["task"] == one
		timer.stop()
		timer.stop(other)
		assert timer.timers() == {"running": None, "paused": []}
		assert ai.plan_task("Send the snag photos", due=str(on(12, 1))).get("state") == "Proposed"
		assert ai.plan_steps(one, ["Check the seals", "Clean the frames"]).get("state") == "Proposed"
		said = tools.edit_record("Task", one, {"priority": "Urgent"}, why="The client asked for it this week.")
		assert said.get("state") == "Proposed" and frappe.db.get_value("Task", one, "priority") != "Urgent", said
		proposals.apply(said["proposal"])
		assert frappe.db.get_value("Task", one, "priority") == "Urgent"
		samirs = frappe.db.get_value("Task", {"subject": "Call Acme about the lobby drawings"})
		for task_name, changes, why in (
			(one, {"priority": "Urgent"}, "nothing to change is said"),
			(samirs, {"status": "Completed"}, "only a task she may change"),
		):
			try:
				tools.edit_record("Task", task_name, changes)
			except (frappe.ValidationError, frappe.PermissionError):
				continue
			raise AssertionError(why)


@check
def onetask_oneai_gives_a_task_on_approval():
	"""OneAI gives one of Rania's tasks to Tariq as a card: nobody has it until
	she approves, then he has it as the page's Assign gives it. Not twice, not
	to nobody, not a task she may not change, and not to somebody switched off
	since the card was made."""
	from onedesk.one_ai import proposals
	from onedesk.one_task import ai, mine

	frappe.db.savepoint("onetask_assign")
	try:
		with as_user("rania@one.test"):
			one = next(
				t.name
				for group in mine.tasks("mine")
				for t in group["tasks"]
				if "tariq@one.test" not in (frappe.parse_json(frappe.db.get_value("Task", t.name, "_assign")) or [])
			)
			said = ai.assign_task(one, ["Tariq Haidar"], why="He is on site tomorrow.")
			assert said.get("state") == "Proposed", said
			assert "tariq@one.test" not in frappe.parse_json(frappe.db.get_value("Task", one, "_assign")), "not before approval"
			proposals.apply(said["proposal"])
			assert "tariq@one.test" in frappe.parse_json(frappe.db.get_value("Task", one, "_assign"))
			todo = {"reference_type": "Task", "reference_name": one, "allocated_to": "tariq@one.test", "status": "Open"}
			assert frappe.db.get_value("ToDo", todo, "assigned_by") == "rania@one.test", "given by the approver"
			assert ai.assign_task(one, ["tariq@one.test"]).get("error"), "he has it already"
			assert ai.assign_task(one, ["Nobody Called This"]).get("error"), "a colleague, or ask"
			samirs = frappe.db.get_value("Task", {"subject": "Call Acme about the lobby drawings"})
			assert ai.assign_task(samirs, ["tariq@one.test"]).get("error"), "only a task she may change"
			later = ai.assign_task(one, ["yousef@one.test"])
			assert later.get("state") == "Proposed", later
		frappe.db.set_value("User", "yousef@one.test", "enabled", 0)
		with as_user("rania@one.test"):
			try:
				proposals.apply(later["proposal"])
				raise AssertionError("given to somebody switched off")
			except frappe.ValidationError:
				pass
	finally:
		frappe.db.rollback(save_point="onetask_assign")


@check
def onetask_a_task_is_its_peoples_and_ends_as_they_say():
	"""A task of nobody's project is its maker's and given to them, and nobody
	else reads it, not even a manager; a project's task is read by the
	project's people and nobody outside it. A to-do about nothing becomes a
	task, and ticking off its last to-do completes it, where a project's task
	waits for its project. Who gave a task hears it done, the one who did it
	does not. A repeat is due again, its steps undone, and given to the same
	people."""
	from frappe.desk.form.assign_to import add as assign

	from onedesk.one_task import task

	with as_user("rania@one.test"):
		own = frappe.get_doc({"doctype": "Task", "subject": "Book the scaffold inspection"}).insert()
	assert frappe.parse_json(frappe.db.get_value("Task", own.name, "_assign")) == ["rania@one.test"]
	for user, may in (("rania@one.test", True), ("samir@one.test", False), ("tariq@one.test", False)):
		assert bool(frappe.has_permission("Task", "read", doc=own.name, user=user)) == may, user
	villa_task = frappe.get_all("Task", filters={"project": VILLA, "is_group": 0}, pluck="name", limit=1)[0]
	for user, may in (("tariq@one.test", True), ("mariam@one.test", False), ("omar@one.test", False)):
		assert bool(frappe.has_permission("Task", "read", doc=villa_task, user=user)) == may, user

	with as_user("rania@one.test"):
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Order more sealant", "allocated_to": "rania@one.test"}).insert()
	made = todo.reference_name
	assert todo.reference_type == "Task" and frappe.db.get_value("Task", made, "subject") == "Order more sealant"
	assert frappe.db.count("ToDo", {"reference_type": "Task", "reference_name": made}) == 1, "the to-do is the assignment"
	with as_user("rania@one.test"):
		todo.reload()
		todo.status = "Closed"
		todo.save()
	assert frappe.db.get_value("Task", made, "status") == "Completed"

	with as_user("samir@one.test"):
		assign({"doctype": "Task", "name": villa_task, "assign_to": ["tariq@one.test"]})
	was = frappe.db.get_value("Task", villa_task, "status")
	with as_user("tariq@one.test"):
		given = frappe.get_doc("ToDo", {"reference_name": villa_task, "allocated_to": "tariq@one.test", "status": "Open"})
		given.status = "Closed"
		given.save()
	assert frappe.db.get_value("Task", villa_task, "status") == was, "a project's task waits for its project"

	with as_user("samir@one.test"):
		job = frappe.get_doc({"doctype": "Task", "subject": "Measure the stair void", "project": VILLA, "exp_end_date": add_days(today(), 3)}).insert()
		assign({"doctype": "Task", "name": job.name, "assign_to": ["rania@one.test"]})
		task.add_step(job.name, "Take the laser")
	with _Told() as told, as_user("rania@one.test"):
		done = frappe.get_doc("Task", job.name)
		done.status = "Completed"
		done.save()
	assert told.to("Task Done") == {"samir@one.test"}, told.said

	from frappe.automation.doctype.auto_repeat.auto_repeat import make_auto_repeat

	with as_user("samir@one.test"):
		repeat = make_auto_repeat("Task", job.name, "Weekly")
		again = repeat.make_new_document()
	assert again.status == "Open" and not any(step.done for step in again.one_steps), again.as_dict()
	assert frappe.parse_json(frappe.db.get_value("Task", again.name, "_assign")) == ["rania@one.test"], "the repeat of a task done goes to who did it"
	frappe.db.set_value("Task", job.name, "auto_repeat", repeat.name)
	with as_user("rania@one.test"):
		assert task.repeat_of(job.name)["frequency"] == "Weekly", "whoever reads the task reads how it repeats"
		task.stop_repeat(job.name)
	assert frappe.db.get_value("Auto Repeat", repeat.name, "disabled") == 1
	with as_user("omar@one.test"):
		try:
			make_auto_repeat("Task", own.name, "Daily")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody repeated a task they may not change")


@check
def onetask_takes_work_from_intake_and_onehr():
	"""A task another module makes lands with the right person and in the
	right place. Intake's task about a supplier goes to the books by the
	workspace's Assignment Rule, one about anything else to whoever's mail it
	came in, and one about a bill for the villa is the villa's. An
	onboarding's steps are each their person's, and open the onboarding, not
	HRMS's project behind it."""
	from onedesk.one_ai.reading import planning
	from onedesk.one_demo import intake
	from onedesk.one_task import mine, view

	scaffolding = frappe.db.get_value("Task", {"subject": "Rapid Scaffolding invoice RS-5512"}, ["name", "project", "_assign", "expected_time"], as_dict=True)
	assert scaffolding.project == VILLA, "a bill for the villa is the villa's work"
	assert frappe.parse_json(scaffolding._assign) == [intake.ACCOUNTS] and not flt(scaffolding.expected_time)
	assert frappe.db.exists("Assignment Rule", intake.RULE)
	made = []
	try:
		made.append(planning.make_task({"subject": "Check the delivery from Gulf Sealants", "one_about_doctype": "Supplier", "one_about": "Gulf Sealants Trading LLC", "assign_to": OWNER}))
		made.append(planning.make_task({"subject": "Answer the lobby question", "assign_to": OWNER}))
		assigned = [frappe.parse_json(frappe.db.get_value("Task", one.name, "_assign")) for one in made]
		assert assigned == [[intake.ACCOUNTS], [OWNER]], assigned
	finally:
		for one in made:
			frappe.delete_doc("Task", one.name, force=1, ignore_permissions=True)
	onboarding = frappe.db.get_value("Employee Onboarding", {"employee_name": "Feras Odeh"}, ["name", "project"], as_dict=True)
	assert onboarding and onboarding.project
	steps = frappe.get_all("Task", filters={"project": onboarding.project}, fields=["name", "_assign"])
	assert {frappe.parse_json(one._assign)[0] for one in steps} == {"mariam@one.test", "karim@one.test", "samir@one.test"}
	with as_user("mariam@one.test"):
		mine_ = [one for group in mine.tasks("mine") for one in group["tasks"] if one.project == onboarding.project]
		assert mine_ and mine_[0].place["kind"] == "Employee Onboarding" and mine_[0].place["label"] == "Feras Odeh"
		said = view.read(mine_[0].name)
		assert said["place"]["route"].endswith(onboarding.name), said["place"]
	with as_user("karim@one.test"):
		mine_ = [one for group in mine.tasks("mine") for one in group["tasks"] if one.project == onboarding.project]
		assert mine_ and mine_[0].place["label"] == "Feras Odeh" and not mine_[0].place["route"], mine_[0].place


@check
def onetask_all_tasks_and_its_views_leave_templates_out():
	"""Every view of All Tasks is the work, not a template's steps. The
	calendar draws a task planned by the day as a day, the tree names each
	task once, the list has room for a task's name, and ERPNext's own board
	keeps no Overdue column."""
	import json

	from frappe.utils import add_days, nowdate

	from onedesk.one_task import views

	templates = set(frappe.get_all("Task", filters={"is_template": 1}, pluck="name"))
	assert templates, "the demo's template has its steps"
	field_map = json.dumps({"start": "exp_start_date", "end": "exp_end_date", "id": "name", "title": "subject", "allDay": "allDay"})
	with as_user("samir@one.test"):
		shown = views.events("Task", add_days(nowdate(), -30), add_days(nowdate(), 60), field_map)
		assert shown and not {one.name for one in shown} & templates
		call = next(one for one in shown if one.subject == "Call Acme about the lobby drawings")
		assert call.allDay == 1, "a task planned by the day is a day"
		roots = views.children("Task", is_root=True)
		assert roots and not {one.value for one in roots} & templates
		phase = next(one for one in roots if one.expandable)
		assert views.children("Task", parent=phase.value) and "status" in phase
	assert frappe.get_meta("Task").get_field("subject").width
	overdue = frappe.db.get_value("Kanban Board Column", {"parent": "Task Status", "column_name": "Overdue"}, "status")
	assert overdue == "Archived", "ERPNext's board puts Overdue away"


@check
def onetask_my_tasks_and_the_inbox_are_the_readers_own():
	"""My Tasks is what is given to the reader, the Inbox what is given to them
	in no project (a to-do of their own, a task Intake made about a supplier's
	bill), each read as the reader and each a board of frappe's. A task waiting on open work
	says so, a phase is not waiting on its own sub-tasks, and the late count
	is the Overdue group."""
	from onedesk.one_task import ai, mine

	def names(groups):
		return {one.name for group in groups for one in group["tasks"]}

	with as_user("samir@one.test"):
		inbox, groups, counts = mine.tasks("inbox"), mine.tasks("mine"), mine.counts()
		own = set(frappe.get_all("Task", filters={"owner": "samir@one.test", "project": ["is", "not set"], "status": "Open"}, pluck="name"))
		assert own and own <= names(inbox) <= names(groups), "his own to-dos are on both"
		late = next((group for group in groups if group["key"] == "overdue"), {"tasks": []})
		assert counts["late"] == len(late["tasks"]) > 0 and counts["inbox"] == len(names(inbox))
		assert frappe.db.exists("Kanban Board", "My Tasks") and frappe.db.exists("Kanban Board", "Inbox")
		assert ai.page({"page": "my-tasks"}) is None, "the boards are frappe's, OneAI reads them as Task"
	with as_user("rania@one.test"):
		assert not own & names(mine.tasks("inbox")), "Samir's to-dos are his"
	with as_user(OWNER):
		given = [one for group in mine.tasks("inbox") for one in group["tasks"] if one.get("about_title")]
		assert given and all(not one.project for one in given), "a task Intake gave is on the Inbox"
	snag = frappe.db.get_value("Task", {"project": VILLA, "subject": "Snag list and rectification"})
	glass = frappe.db.get_value("Task", {"project": VILLA, "subject": "Install glass"})
	phase = frappe.db.get_value("Task", glass, "parent_task")
	assert mine._waiting([snag]).get(snag), "the snag list waits on the water test"
	assert not mine._waiting([phase]), "a phase does not wait on its own sub-tasks"


@check
def onetask_a_task_opens_on_its_own_page():
	"""A task opens on its page as its reader may see it: the villa's glass
	says it is late, a phase lists its tasks as sub-tasks and not as what it
	waits on, and a step waiting on another says so. OneAI reads the task as
	the page does, and somebody who may not see the project's tasks is
	refused."""
	from onedesk.one_task import ai, view

	glass = frappe.db.get_value("Task", {"project": VILLA, "subject": "Install glass"})
	phase = frappe.db.get_value("Task", glass, "parent_task")
	snag = frappe.db.get_value("Task", {"project": VILLA, "subject": "Snag list and rectification"})
	with as_user("samir@one.test"):
		said = view.read(glass)
		assert said["headline"]["key"] == "late" and said["late_by"] > 0, said["headline"]
		assert phase not in {one["name"] for one in said["blocking"]}, "a sub-task does not hold up its parent"
		assert said["above"] and said["above"][-1]["name"] == phase and said["project_title"]
		assert said["time"]["logged"] > 0 and said["can_write"]
		group = view.read(phase)
		assert group["sub_tasks"] and not {one.name for one in group["sub_tasks"]} & {one["name"] for one in group["waits"]}
		assert view.read(snag)["headline"]["key"] == "waiting"
		assert view.files(glass) == 0
		facts = ai.task_facts(glass)
		assert facts["late_by_days"] > 0 and facts["hours_by_person"], facts
		assert "task_facts" in (ai.page({"page": "task-view", "record": glass}) or "")
	elsewhere = frappe.db.get_value("Task", {"project": SHOWROOM, "is_group": 0})
	with as_user("rania@one.test"):
		try:
			view.read(elsewhere)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania read a task on a project she may not see")
		assert ai.task_facts(elsewhere).get("error")


@check
def onetask_a_manager_sees_every_task_and_nobody_else_does():
	"""See Every Task is a OneTask Manager's, a role the workspace gives by
	choice: Tariq, made one, opens a to-do Karim keeps to himself, and Rania,
	who works in projects as he does, sees neither it in her list nor its page."""
	from onedesk.one_task import access

	with as_user("karim@one.test"):
		kept = frappe.get_doc({"doctype": "Task", "subject": "Call the glass supplier back"}).insert()
	assert not access.every("tariq@one.test"), "somebody sees every to-do without being given it"
	frappe.get_doc("User", "tariq@one.test").add_roles("OneTask Manager")
	frappe.clear_cache(user="tariq@one.test")
	assert access.every("tariq@one.test") and not access.every("rania@one.test")
	with as_user("tariq@one.test"):
		assert frappe.has_permission("Task", "read", kept.name), "a OneTask Manager sees every task"
		assert kept.name in frappe.get_list("Task", filters={"name": kept.name}, pluck="name")
	with as_user("rania@one.test"):
		assert not frappe.has_permission("Task", "read", kept.name), "Rania sees a to-do that isn't hers"
		assert not frappe.get_list("Task", filters={"name": kept.name}, pluck="name")
