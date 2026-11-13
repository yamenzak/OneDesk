"""OneProject's part of the integration suite (one_demo/check.py runs it):
every view of a project's page as its people read it, its money as its
documents, billing, retention and claims, its terms, its people and its
portal, its templates, and the one ability.

It stays one file past 1500 lines: the runner imports one checks.py a
module, and the guards read each module's checks by that name."""

import frappe
from frappe.utils import (
	add_days,
	add_months,
	add_to_date,
	cint,
	date_diff,
	flt,
	get_first_day,
	getdate,
	now_datetime,
	today,
)

from onedesk.one_demo.base import COMPANY, as_user, wh
from onedesk.one_demo.checking import (
	ACME,
	MARINA,
	SHOWROOM,
	TOWER,
	VILLA,
	_bulk,
	_close,
	_each_way,
	_employee,
	_refused,
	_Told,
	check,
)
from onedesk.one_demo.people import OWNER


def _projects():
	return frappe.get_all("Project", filters={"project_type": ["!=", "Employee Boarding"]}, fields=["name", "project_name", "one_kind"])


def _team(project):
	return set(frappe.get_all("Project User", filters={"parent": project}, pluck="user"))


@check
def every_project_page_opens_for_its_people():
	"""A project's two reads, as the owner, the project manager, the books
	and each member of its team."""
	from onedesk.one_project import money, view

	broken = []
	for project in _projects():
		for user in {OWNER, "samir@one.test", "huda@one.test", *_team(project.name)}:
			if not frappe.has_permission("Project", "read", doc=project.name, user=user):
				continue
			if frappe.db.get_value("User", user, "user_type") != "System User":
				continue
			try:
				with as_user(user):
					view.said(project.name)
					money.money(project.name)
			except Exception as e:
				broken.append((project.project_name, user, f"{type(e).__name__}: {e}"[:160]))
	assert not broken, broken


@check
def a_project_is_closed_to_who_has_no_part_in_it():
	from onedesk.one_project import view

	project = next(one.name for one in _projects() if "yousef@one.test" not in _team(one.name))
	try:
		with as_user("yousef@one.test"):
			view.said(project)
	except frappe.PermissionError:
		return
	raise AssertionError("an installer with no projects access read a project page")


def _figures(side):
	return {row["label"]: flt(row["value"]) for row in side}


@check
def a_projects_figures_are_its_documents():
	"""Ordered, invoiced and billed on the page are the sums of the
	submitted documents carrying the project, its sub-projects' too."""
	from onedesk.one_project import money, tree
	from onedesk.one_project.retention import ITEM

	wrong = []
	for project in _projects():
		said = money.money(project.name)
		scope = sorted(tree.scope(project.name))
		customer, cost = _figures(said.get("customer", [])), _figures(said.get("cost", []))
		for label, figures, _doctype, child in (
			("Ordered", customer, "Sales Order", "Sales Order Item"),
			("Invoiced", customer, "Sales Invoice", "Sales Invoice Item"),
			("Billed", cost, "Purchase Invoice", "Purchase Invoice Item"),
		):
			if label not in figures:
				continue
			held = " and ifnull(one_held, '') = ''" if frappe.db.has_column(child, "one_held") else ""
			found = frappe.db.sql(
				f"""select sum(base_net_amount) from `tab{child}` where project in %s and docstatus = 1
				and ifnull(item_code, '') != %s{held}""",
				(scope, ITEM),
			)[0][0]
			if not _close(figures[label], found, 1):
				wrong.append((project.project_name, label, figures[label], flt(found)))
	assert not wrong, wrong


@check
def a_project_shows_how_far_along_it_is():
	"""Progress is stored on the project, and a project with tasks done says
	more than nothing."""
	moved = [p.project_name for p in _projects() if flt(frappe.db.get_value("Project", p.name, "percent_complete"))]
	assert len(moved) >= 5, moved


@check
def every_retainer_month_is_invoiced_once():
	twice = frappe.db.sql(
		"""select project, one_retainer_month, count(*) from `tabSales Invoice`
		where docstatus = 1 and ifnull(one_retainer_month, '') != '' and ifnull(is_return, 0) = 0
		group by project, one_retainer_month having count(*) > 1"""
	)
	assert not twice, twice


@check
def no_time_is_invoiced_twice():
	twice = frappe.db.sql(
		"""select timesheet_detail, count(*) from `tabSales Invoice Timesheet` row
		join `tabSales Invoice` invoice on invoice.name = row.parent
		where invoice.docstatus = 1 and ifnull(row.timesheet_detail, '') != ''
		group by timesheet_detail having count(*) > 1"""
	)
	assert not twice, twice


@check
def a_project_manager_logs_and_approves_the_crews_time():
	"""The workshop has no accounts, so Samir logs their days, two of them
	at the same hour (one_hr/timesheet.py)."""
	same_hour = frappe.db.sql(
		"""select log.from_time from `tabTimesheet Detail` log
		join `tabTimesheet` sheet on sheet.name = log.parent
		join `tabEmployee` person on person.name = sheet.employee
		where sheet.docstatus = 1 and ifnull(person.user_id, '') = ''
		group by log.from_time having count(distinct sheet.employee) > 1 limit 1"""
	)
	assert same_hour, "nobody without an account was logged at the same hour as another"
	timesheet = frappe.get_all("Timesheet", filters={"docstatus": 1}, fields=["name", "employee"], limit=1)[0]
	with as_user("samir@one.test"):
		assert frappe.has_permission("Timesheet", "read", doc=timesheet.name), timesheet
		assert frappe.has_permission("Timesheet", "submit"), "submit"


@check
def the_books_read_every_project():
	with as_user("huda@one.test"):
		seen = set(frappe.get_list("Project", pluck="name", limit=0))
	assert {p.name for p in _projects()} <= seen, {p.name for p in _projects()} - seen


@check
def a_project_manager_sets_a_projects_budget_and_not_a_cost_centres():
	from onedesk.one_project.budget import set_budget

	project = frappe.db.get_value("Project", {"project_name": "Bayview Tower Curtain Wall"})
	account = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Equipment Hire", "is_group": 0})
	with as_user("samir@one.test"):
		set_budget(project, account, 12345, "Warn")
		made = frappe.get_last_doc("Budget", filters={"project": project, "account": account, "docstatus": 1})
		budget = frappe.copy_doc(made)
		budget.update({"budget_against": "Cost Center", "project": None, "cost_center": frappe.db.get_value("Company", COMPANY, "cost_center")})
		try:
			budget.insert()
		except frappe.ValidationError as e:
			assert "Only an accounts user sets a budget" in str(e), e
			return
	raise AssertionError("a project manager set a cost centre's budget")


@check
def a_project_with_open_work_is_not_closed_by_hand():
	project = frappe.db.get_value("Project", {"project_name": "Bayview Tower Curtain Wall"})
	_refused(_each_way("samir@one.test", "Project", project, {"status": "Completed"}), "still has open work")


@check
def an_internal_project_bills_nobody():
	"""A customer's project with nothing billed yet, made internal, bills
	nobody. One with orders or invoices keeps its customer (kinds.settled)."""
	from onedesk.one_project.kinds import in_use

	project = next(
		name
		for name in frappe.get_all(
			"Project", filters={"customer": ["is", "set"], "status": "Open", "one_kind": ["!=", "Internal"]}, pluck="name", order_by="name"
		)
		if not in_use(name)
	)
	seen = _each_way("samir@one.test", "Project", project, {"one_kind": "Internal"}, ("customer", "one_markup"))
	for way, got in seen.items():
		assert not isinstance(got, Exception), (way, got)
		assert got.one_kind == "Internal" and not got.customer and not flt(got.one_markup), (way, got)


@check
def a_projects_budget_is_its_cost_types():
	budgeted = frappe.get_all("Budget", filters={"docstatus": 1, "budget_against": "Project"}, pluck="project", limit=1)
	assert budgeted, "no project has a budget"
	project = budgeted[0]
	was = frappe.db.get_value("Project", project, "estimated_costing")
	for way, got in _each_way("samir@one.test", "Project", project, {"estimated_costing": 1}).items():
		assert not isinstance(got, Exception), (way, got)
		assert _close(got.estimated_costing, was), (way, got.estimated_costing, was)


@check
def a_cancelled_budget_leaves_its_project():
	from onedesk.one_project.budget import _budgets

	budget = frappe.get_all("Budget", filters={"docstatus": 1, "budget_against": "Project"}, fields=["name", "project"], limit=1)[0]
	with as_user("samir@one.test"):
		_bulk("Budget", budget.name, "cancel")
	left = sum(flt(one.budget_amount) for one in _budgets(budget.project))
	assert _close(frappe.db.get_value("Project", budget.project, "estimated_costing"), left), budget


@check
def a_template_is_laid_out_and_changed_on_its_page():
	"""The project manager opens the Aluminium & Glazing template, changes it
	in place, copies a preset in from the library and starts a project and a
	running project's extra tasks from them. A projects user only reads."""
	from onedesk.one_demo.projects import TEMPLATE
	from onedesk.one_project import kinds, library, template_view, templates

	with as_user("samir@one.test"):
		said = template_view.read(TEMPLATE)
		assert sum(1 for one in said["tasks"] if not one["is_group"]) == 25, said["tasks"]
		assert all(one["is_milestone"] for one in said["tasks"] if one["is_group"])
		assert said["used"] >= 1 and said["can_write"]
		def listed(name):
			return tuple(frappe.db.get_value("Project Template", name, ["one_tasks", "one_days", "one_projects"]))

		assert listed(TEMPLATE) == (25, said["days"], said["used"]), "the list says what the page says"
		first, phase = said["tasks"][1]["name"], said["tasks"][0]["name"]
		template_view.change(TEMPLATE, first, "duration", 4)
		made = template_view.add(TEMPLATE, "Check the anchors", phase)
		template_view.wait(TEMPLATE, made, first, 1)
		template_view.nest(TEMPLATE, made, None)
		after = {one["name"]: one for one in template_view.read(TEMPLATE)["tasks"]}
		assert after[first]["duration"] == 4 and after[made]["depth"] == 0 and after[made]["waits"] == [first]
		assert listed(TEMPLATE)[0] == 26
		template_view.remove(TEMPLATE, made)
		assert made not in {one["name"] for one in template_view.read(TEMPLATE)["tasks"]}
		assert listed(TEMPLATE)[0] == 25
		last = max(template_view.read(TEMPLATE)["tasks"], key=lambda one: one["start"] + one["duration"])
		task = frappe.get_doc("Task", last["name"])
		task.duration += 10
		task.save()
		assert listed(TEMPLATE)[1] == said["days"] + 10, listed(TEMPLATE)

		copied = library.copy("website")
		assert library.copy("website") == copied, "the second use takes the same copy"
		name = kinds.make({"kind": "Internal", "title": "Our Summer Event", "starts": today(), "library": "event", "time": "Not Tracked"})
		assert frappe.db.count("Task", {"project": name}) == 20, "an Event's 15 tasks and its 5 phases"
		event = frappe.db.get_value("Project", name, "project_template")
		assert listed(event) == (15, 75, 1), listed(event)
		assert listed(copied)[2] == 0, "a copy nobody has started from"
		running = frappe.get_all("Project", filters={"project_name": "Mansour Villa Windows and Doors"}, pluck="name")[0]
		assert templates.add(running, library="client_onboarding", starts=today()) == 14

	with as_user("rania@one.test"):
		assert not template_view.read(TEMPLATE)["can_write"]
		try:
			template_view.change(TEMPLATE, first, "duration", 9)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a projects user changed a template")


@check
def oneai_drafts_a_template_as_a_card():
	"""A template OneAI drafts is a card: nothing is made until the project
	manager approves it, approving makes it as the library would, and a
	projects user is not offered one."""
	from onedesk.one_ai import proposals
	from onedesk.one_project import agent, template_view

	phases = [
		{"subject": "Strip-Out", "milestone": True, "tasks": [{"subject": "Protect the floors", "day": 0, "days": 1}, {"subject": "Take out the old units", "day": 1, "days": 2}]},
		{"subject": "Fit", "milestone": True, "tasks": [{"subject": "Fit the new units", "day": 3, "days": 3}, {"subject": "Worktops", "day": 6, "days": 1, "after": ["Fit the new units"]}]},
	]
	with as_user("samir@one.test"):
		known = agent.project_templates()
		assert "Aluminium & Glazing" in known["templates"] and len(known["library"]) == 12
		said = agent.draft_template("Kitchen Refit", phases, about="A kitchen taken out and fitted again.")
		assert said.get("state") == "Proposed", said
		assert not frappe.db.exists("Project Template", "Kitchen Refit"), "nothing is made before it is approved"
		assert agent.draft_template("Aluminium & Glazing", phases).get("mend") == "draft_template"
		assert agent.draft_template("Bad", [{"subject": "A", "tasks": [{"subject": "b", "when": 3}]}]).get("mend")
		proposals.apply(said["proposal"])
		made = template_view.read("Kitchen Refit")
		assert [one["subject"] for one in made["tasks"]] == ["Strip-Out", "Protect the floors", "Take out the old units", "Fit", "Fit the new units", "Worktops"]
		assert made["days"] == 7 and all(one["is_milestone"] for one in made["tasks"] if one["is_group"])
	with as_user("rania@one.test"):
		assert "error" in agent.draft_template("Garden Shed", phases)


def _another_villa_order(tax=None) -> str:
	"""A second order for the villa, as its first, submitted, saying `tax` or
	nothing; checks roll it back."""
	villa = frappe.db.get_value("Project", VILLA, "sales_order")
	with as_user(OWNER):
		order = frappe.copy_doc(frappe.get_doc("Sales Order", villa))
		order.one_retention_tax = tax
		order.insert()
		order.submit()
	return order.name


def _png(**drawn) -> bytes:
	from onedesk.one_demo.projects import _photo

	return _photo(**drawn)


@check
def a_project_pays_for_stock_once():
	"""The villa paid for the bar issued to it less the 4 m that came back,
	at what it was charged, and the return is taken off its cost of goods in
	the books. A supplier bill line whose goods went into a store isn't the
	project's cost when billed, only when issued."""
	from onedesk.one_project import materials, money

	villa = frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	back = frappe.get_all("Stock Entry", filters={"docstatus": 1, "stock_entry_type": materials.RETURN, "project": villa}, pluck="name")
	try:
		materials.give_back(wh("Stores"), [{"item": "ALU-6063", "qty": 0}], villa)
		raise AssertionError("a return of nothing was made")
	except frappe.ValidationError:
		pass
	assert back, "the offcut came back"
	row = frappe.get_all("Stock Entry Detail", filters={"parent": back[0]}, fields=["qty", "uom", "transfer_qty", "amount", "expense_account"])[0]
	assert row.uom == "Meter" and flt(row.transfer_qty) == 4, row
	bar = frappe.db.sql(
		"""select line.valuation_rate from `tabStock Entry Detail` line join `tabStock Entry` entry on entry.name = line.parent
		where entry.docstatus = 1 and line.project = %s and line.item_code = 'ALU-6063' and line.uom = 'Bar'""",
		villa,
	)
	assert bar and abs(flt(row.amount) - 4 * flt(bar[0][0])) < 0.01, (row.amount, bar)
	from erpnext.projects.doctype.project.project import Project

	plain, project = frappe.get_doc("Project", villa), frappe.get_doc("Project", villa)
	Project.set_consumed_material_cost(plain)
	project.set_consumed_material_cost()
	assert abs(flt(plain.total_consumed_material_cost) - flt(project.total_consumed_material_cost) - flt(row.amount)) < 0.01, "less what came back"
	goods = frappe.get_cached_value("Company", project.company, "default_expense_account")
	credited = frappe.db.get_value("GL Entry", {"voucher_no": back[0], "account": goods, "is_cancelled": 0}, ["credit", "project"], as_dict=True)
	assert credited and abs(flt(credited.credit) - flt(row.amount)) < 0.01 and credited.project == villa, credited
	for name in frappe.get_all("Project", pluck="name"):
		stored = materials.into_store([name])
		if not stored:
			continue
		bought = money._lines("Purchase Invoice", [name])
		doc = frappe.get_doc("Project", name)
		doc.update_purchase_costing()
		assert flt(doc.total_purchase_cost) <= bought - stored + 0.01 and stored <= bought, (name, stored)
		break
	else:
		raise AssertionError("no project bought anything into a store")


@check
def oneproject_every_tab_of_a_project_page_reads_for_samir():
	"""The villa's page as Samir reads it, tab by tab, the tower's tree added
	up, the Projects list's tree and timeline, the retainer's months and what
	OneAI reads of them."""
	from onedesk.one_project import (
		activity,
		agent,
		billing,
		budget,
		buying,
		chain,
		contacts,
		hours,
		kinds,
		library,
		media,
		overview,
		progress,
		retainer,
		status,
		team,
		tree,
		updates,
		view,
	)

	with as_user("samir@one.test"):
		said = overview.overview(VILLA)
		assert said["projects"] == 2 and said["tasks"] and 0 < said["share"] < 100, said
		added = tree.totals(TOWER)
		assert added["projects"] == 3 and len(added["under"]) == 2
		assert {one["value"] for one in tree.nodes(is_root=1)} >= {VILLA, TOWER, ACME}
		assert tree.milestones([VILLA, TOWER])
		assert media.featured(VILLA)[0]["kind"] == "photo"
		assert VILLA not in {one["name"] for one in view.picker("PROJ-0002")["open"]}, "the parent is in the breadcrumb already"
		assert frappe.db.get_value("Project", "PROJ-0002", "project_name") == "Staircase balustrade", "extra work is called what it was quoted as"
		assert view.to_quote("Acme Holdings") == ACME and chain.customer_project("Acme Holdings") == ACME
		assert view.to_quote("Mansour & Sons") is None, "two open projects, so neither is guessed"
		assert len(view.updates(VILLA)) >= 2 and activity.timeline("Project", VILLA)
		assert billing.bills(VILLA)["bills"]
		assert billing.unbilled(SHOWROOM)["hours"] > 0 and billing.unbilled(SHOWROOM)["currency"] == "EUR"
		assert len(budget.lines(VILLA)["lines"]) == 4
		assert buying.papers(VILLA)["papers"], "the request for the next run of profile"
		assert contacts.contacts(VILLA)["can_change"]
		time = hours.entries(VILLA)
		assert time["entries"] and time["kind"] == "Fixed Price" and not time["bills_hours"]
		assert len(team.team(VILLA)["people"]) >= 4
		months = retainer.months(MARINA)
		assert months["fee"] and months["months"]
		assert retainer.asked(MARINA, str(get_first_day(add_months(today(), -1))))["fee"] == months["fee"]
		assert status.ask(VILLA)["tasks"]
		assert updates.asked(VILLA) is False
		assert kinds.defaults("Acme Holdings")["currency"] == "USD"
		assert len(library.presets()) == 12
		assert progress.progress("Sales Order", frappe.db.get_value("Project", VILLA, "sales_order"))["retention"] == 10
		facts = agent.project_facts(VILLA)
		assert facts["title"] == "Mansour Villa Windows and Doors" and facts["sub_projects"] == 1
		assert VILLA in {one["project"] for one in agent.projects_needing_attention()["projects"]}
	with as_user("huda@one.test"):
		assert billing.invoices(VILLA)["invoices"], "the books see the villa's invoices"


@check
def oneproject_buying_says_what_oneinventory_says():
	"""A project's Buying says each order, request and receipt in ERPNext's
	status, as urgent as its own head in OneInventory says it is: Al Noor's
	late order on the villa is red there as it is on the order. Issue Stock from the project uses stock
	on it, as Transfer Stock moves it, and its cost is the project's. To
	Order and Quotes name a request's project by its name."""
	from onedesk.one_inventory import heads, order, quotes, stock
	from onedesk.one_project import buying

	villa = frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	with as_user("samir@one.test"):
		papers = buying.papers(villa)["papers"]
	for one in papers:
		if one["doctype"] in heads.STANDS:
			doc = frappe.get_doc(one["doctype"], one["name"])
			assert one["tone"] == heads.stands(doc), (one, heads.stands(doc))
			assert one["status"] == ("Draft" if doc.docstatus == 0 else doc.status), one
	late = [one for one in papers if one["doctype"] == "Purchase Order" and one["tone"] == "red"]
	assert late and all(one["status"].startswith("To Receive") for one in late), papers
	with as_user("karim@one.test"):
		rows = order.rows()
		asked = quotes.asked()
	named = {row.get("project_title") for row in rows if row.get("project")}
	assert "Mansour Villa Windows and Doors" in named, named
	assert not any(one["project"] and one["project"].startswith("PROJ-") for one in asked), asked
	with as_user("karim@one.test"):
		item = frappe.db.get_value("Bin", {"warehouse": wh("Stores"), "actual_qty": [">", 5]}, "item_code")
		made = stock.issue(wh("Stores"), [{"item": item, "qty": 1}], villa, "Demo check")
	entry = frappe.get_doc("Stock Entry", made)
	assert entry.docstatus == 1 and entry.purpose == "Material Issue" and entry.project == villa, entry.as_dict()
	assert all(row.project == villa for row in entry.items)
	entry.cancel()
	frappe.delete_doc("Stock Entry", made, force=True)


@check
def oneproject_a_timesheet_says_what_is_left_to_bill():
	"""A timesheet's head says what is left to bill on it: one with billable
	hours not yet invoiced in orange with its Billed step under way, one with
	none billable in gray with only its Logged step."""
	from onedesk.one import head

	record = frappe.get_doc("Record Head", "Timesheet")
	with as_user("samir@one.test"):
		billable = frappe.get_all("Timesheet", filters={"docstatus": 1, "total_billable_hours": [">", 0], "per_billed": ["<", 100]}, pluck="name", limit=1)
		own = frappe.get_all("Timesheet", filters={"docstatus": 1, "total_billable_hours": 0}, pluck="name", limit=1)
		assert billable and own, (billable, own)
		said = head.said(frappe.get_doc("Timesheet", billable[0]), record)
		assert said["sentence"]["colour"] == "orange", said["sentence"]
		assert [(step["label"], step["state"]) for step in said["band"][0]["steps"]] == [("Submitted", "done"), ("Billed", "now")], said["band"]
		said = head.said(frappe.get_doc("Timesheet", own[0]), record)
		assert said["sentence"]["colour"] == "gray" and [step["label"] for step in said["band"][0]["steps"]] == ["Submitted"], said


@check
def oneproject_samir_runs_a_project():
	"""What Samir changes on a project: the team, a contact, time,
	a cost type's budget, the update he is asked for, a template from the
	villa's tasks, a contract on Acme's lobby, a project grouped above
	another, a photo added, and the villa closed with its open work."""
	from onedesk.one_project import (
		agent,
		budget,
		contacts,
		hours,
		kinds,
		media,
		status,
		team,
		templates,
		tree,
		updates,
	)
	from onedesk.one_cloud import upload

	with as_user("samir@one.test"):
		assert "huda@one.test" in {one["user"] for one in team.add(VILLA, "huda@one.test")["people"]}
		assert "huda@one.test" not in {one["user"] for one in team.remove(VILLA, "huda@one.test")["people"] if one["member"]}
		row = next(
			one
			for one in contacts.save(VILLA, "Consultant", organisation="Gulf Façade Consultants", note="Signs off the façade drawings")["contacts"]
			if one["company"] == "Gulf Façade Consultants"
		)
		assert row["company"] == "Gulf Façade Consultants"
		assert row["row"] not in {one["row"] for one in contacts.remove(VILLA, row["row"])["contacts"]}
		sheet = hours.log(VILLA, today(), 3, "Project Management", description="Site walk with Khalid")
		assert frappe.db.exists("Timesheet Detail", {"parent": sheet, "project": VILLA, "hours": 3})
		account = budget.lines(VILLA)["lines"][0]["account"]
		was = frappe.db.get_value("Budget", {"project": VILLA, "account": account, "docstatus": 1})
		budget.set_budget(VILLA, account, 155000)
		now = frappe.db.get_value("Budget", {"project": VILLA, "account": account, "docstatus": 1}, ["name", "budget_amount", "revision_of"], as_dict=True)
		assert flt(now.budget_amount) == 155000 and (not was or (now.revision_of == was and frappe.db.get_value("Budget", was, "docstatus") == 2)), (was, now)
		assert all(one["account"] != account for one in budget.remove_budget(VILLA, account)["lines"] if one.get("budget"))
		posted = updates.post(VILLA, "Glass for the first floor is in.")
		assert frappe.db.exists("Project User", {"parenttype": "Project Update", "parent": posted, "user": "samir@one.test"})
		assert agent.draft_update(VILLA, "I walked the site with Khalid. The first floor glass is in.").get("state") == "Proposed"
		made = templates.save_as(VILLA, "Villa Glazing")
		assert frappe.db.count("Project Template Task", {"parent": made}) == frappe.db.count("Task", {"project": VILLA, "status": ["!=", "Cancelled"]})
		order = kinds.add_contract(ACME, 85000, "SVC-INST", retention=5)
		assert frappe.db.get_value("Sales Order", order, ["docstatus", "currency"]) == (1, "USD")
		assert frappe.db.get_value("Project", ACME, "sales_order") == order, "the contract is the project's order"
		above = tree.group_under(ACME, "Acme Americas")
		assert frappe.db.get_value("Project", ACME, "one_parent") == above
		upload._place(media.node(ACME), None, {"file_name": "Lobby mock-up.png", "content": _png()})
		assert media.featured(ACME)[0]["title"] == "Lobby mock-up.png"
		try:
			status.change(VILLA, "Completed")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a project with open work closed without saying so")
		assert status.change(VILLA, "Completed", close=1) == "Completed"
		assert not frappe.db.count("Task", {"project": VILLA, "status": ["not in", ("Completed", "Cancelled", "Template")]})
	with as_user("rania@one.test"):
		try:
			budget.set_budget(VILLA, account, 1000)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a projects user set a budget")
	with as_user("yousef@one.test"):
		try:
			team.add(TOWER, "huda@one.test")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who may only read a project changed its team")


@check
def oneproject_the_books_invoice_time_a_month_and_progress():
	"""What Huda bills from a project's page: the showroom's time in euros,
	its Time Billed the same as its lines to the cent, the retainer's last
	month, and the villa's order as far as the work has got. Each a draft, as
	the page opens it."""
	from onedesk.one_project import billing, progress, retainer

	with as_user("huda@one.test"):
		invoice = billing.invoice_time(SHOWROOM, item="SVC-MAINT")
		assert invoice.currency == "EUR" and invoice.items and invoice.is_new()
		billed = flt(sum(flt(row.billing_amount, 2) for row in invoice.timesheets), 2)
		lines = flt(sum(flt(row.amount) for row in invoice.items if not row.get("one_rebills")), 2)
		assert billed == lines, (billed, lines)
		try:
			retainer.invoice_month(MARINA, month=str(get_first_day(add_months(today(), -1))), item="SVC-MAINT")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("last month was billed twice")
		fee = retainer.invoice_month(MARINA, month=str(get_first_day(today())), item="SVC-MAINT")
		assert fee.items[0].rate == flt(frappe.db.get_value("Project", MARINA, "one_monthly_fee"))
		order = frappe.db.get_value("Project", VILLA, "sales_order")
		windows = progress.progress("Sales Order", order)["lines"][0]
		draft = progress.bill_progress(order, "Sales Order", lines={windows["line"]: 100})
		assert [row.item_code for row in draft.items if not row.get("one_held")] == ["WIN-CS12"] and draft.is_new()


@check
def oneproject_a_new_retention_date_reaches_the_receivables():
	"""The villa's retention moved a month on its order: the invoices already
	made from it, their payment schedules and both ledgers carry the new date,
	so Accounts Receivable ages the retention by it."""
	from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as receivable

	from onedesk.one_project.progress import RETENTION

	name = frappe.db.get_value("Project", VILLA, "sales_order")
	invoices = sorted({one.parent for one in frappe.get_all("Sales Invoice Item", filters={"sales_order": name, "docstatus": 1}, fields=["parent"])})
	held = [one for one in invoices if frappe.db.exists("Payment Schedule", {"parent": one, "payment_term": RETENTION})]
	assert held, "the villa has invoices holding retention"
	with as_user(OWNER):
		order = frappe.get_doc("Sales Order", name)
		moved = add_days(order.one_retention_due, 30)
		order.one_retention_due = moved
		order.save()
	for invoice in held:
		assert getdate(frappe.db.get_value("Payment Schedule", {"parent": invoice, "payment_term": RETENTION}, "due_date")) == getdate(moved)
		assert getdate(frappe.db.get_value("Sales Invoice", invoice, "due_date")) == getdate(moved)
		for ledger in ("Payment Ledger Entry", "GL Entry"):
			dates = set(frappe.get_all(ledger, filters={"voucher_no": invoice, "due_date": ["is", "set"]}, pluck="due_date"))
			assert dates == {getdate(moved)}, (ledger, invoice, dates)
	customer = frappe.db.get_value("Project", VILLA, "customer")
	rows = receivable(frappe._dict(company=COMPANY, report_date=today(), party_type="Customer", party=[customer], ageing_based_on="Due Date", range="30, 60, 90, 120"))[1]
	aged = {row.get("voucher_no"): getdate(row.get("due_date")) for row in rows if row.get("voucher_no") in held}
	assert aged and set(aged.values()) == {getdate(moved)}, aged


@check
def oneproject_an_invoice_is_its_projects_next_claim():
	"""A progress invoice on the villa takes the next claim number within the
	project when it's submitted, and its print says where the contract
	stands: the contract, billed before, this claim, billed to date,
	received and left to bill. Its amendment keeps the number."""
	from onedesk.one_project import claims, progress

	order = _another_villa_order()
	before = claims.next_claim(frappe.get_all("Sales Invoice", filters={"project": VILLA, "docstatus": ["!=", 0]}, pluck="one_claim"))
	with as_user("huda@one.test"):
		windows = progress.progress("Sales Order", order)["lines"][0]
		invoice = progress.bill_progress(order, "Sales Order", lines={windows["line"]: 50})
		invoice.insert()
		assert not invoice.one_claim, "a draft has no number yet"
		invoice.submit()
	invoice.reload()
	assert invoice.one_claim == before, (invoice.one_claim, before)
	said = claims.standing(invoice)
	contract = sum(flt(one) for one in frappe.get_all("Sales Order", filters={"project": VILLA, "docstatus": 1}, pluck="grand_total"))
	assert _close(said["contract"], contract, 0.01) and _close(said["this"], invoice.grand_total, 0.01), said
	assert _close(said["to_date"], said["before"] + said["this"], 0.01) and _close(said["left"], contract - said["to_date"], 0.01), said
	printed = frappe.get_print("Sales Invoice", invoice.name, "One Sales Invoice")
	assert f"Claim {before} on the Contract" in printed and "Left to Bill" in printed
	with as_user("huda@one.test"):
		invoice.cancel()
		again = frappe.copy_doc(invoice)
		again.amended_from = invoice.name
		again.insert()
		again.submit()
	assert frappe.db.get_value("Sales Invoice", again.name, "one_claim") == before, "the amendment keeps its number"


@check
def oneproject_retention_is_taxed_when_released():
	"""In the UAE tax on retention is due when it's released, so a new order
	for the villa starts that way and its progress invoice is taxed on the
	work less its retention, which waits
	in Retention Receivable; Release Retention is then an invoice for the
	retention with its own VAT, after which none is held. The same bill from
	a subcontractor holds it in Retention Payable."""
	from onedesk.one_project import progress, retention

	assert retention.when_released(), "Sahara is in the UAE"
	order = _another_villa_order()
	with as_user("huda@one.test"):
		windows = progress.progress("Sales Order", order)["lines"][0]
		invoice = progress.bill_progress(order, "Sales Order", lines={windows["line"]: 100})
		invoice.insert()
		work = sum(flt(row.amount) for row in invoice.items if not row.get("one_held"))
		held = -sum(flt(row.amount) for row in invoice.items if row.get("one_held"))
		assert _close(held, work * flt(invoice.one_retention) / 100, 0.02), (work, held)
		assert _close(invoice.net_total, work - held, 0.01), "taxed on the work less its retention"
		invoice.submit()
	booked = {row.account: flt(row.debit) for row in frappe.get_all("GL Entry", {"voucher_no": invoice.name, "is_cancelled": 0}, ["account", "debit"])}
	assert _close(booked.get(retention.account(COMPANY, "Sales Invoice")), held, 0.01), booked
	kept = retention.held_on("Sales Invoice", [invoice.name])
	assert _close(sum(amount for _due, amount in kept[invoice.name]), held, 0.01) and not retention.held_on("Sales Invoice", [invoice.name], owed=True)
	frappe.db.set_value("Project", VILLA, "one_completed_on", add_days(add_months(today(), -12), 15))
	with as_user(OWNER):
		asked = [one for one in retention.asks([VILLA], OWNER) if one["route"].endswith(invoice.name)]
		assert any("before its tax falls due" in one["text"] for one in asked), asked
	frappe.db.set_value("Project", VILLA, "one_completed_on", None)
	from erpnext.accounts.doctype.sales_invoice.mapper import make_sales_return

	with as_user("huda@one.test"):
		credit = make_sales_return(invoice.name)
		for row in credit.items:
			if not row.get("one_held"):
				row.qty = row.qty / 2
		credit.insert()
		credit.submit()
	kept = retention.held_on("Sales Invoice", [invoice.name])
	assert _close(sum(amount for _due, amount in kept[invoice.name]), held / 2, 0.02), (kept, held)
	held = held / 2
	with as_user(OWNER):
		releasing = retention.release(VILLA, invoice=invoice.name)
		assert releasing.doctype == "Sales Invoice" and _close(releasing.net_total, held, 0.01), releasing.net_total
		assert releasing.total_taxes_and_charges > 0, "the retention is taxed when it's released"
		releasing.insert()
		releasing.submit()
	assert not retention.held_on("Sales Invoice", [invoice.name])[invoice.name], "released"


@check
def oneproject_an_order_says_how_its_retention_is_taxed():
	"""Sahara taxes retention when it's released, but Khalid's contract for
	the villa taxes each bill in full, so its order says With Invoice and
	its bills hold the retention in their payment terms. An order nobody
	told starts as the workspace does; one already invoiced keeps what it
	said."""
	from onedesk.one_project import progress, retention
	from onedesk.one_project.progress import HELD

	assert retention.when_released(), "Sahara is in the UAE"
	villa = frappe.db.get_value("Project", VILLA, "sales_order")
	with as_user(OWNER):
		invoiced = frappe.get_doc("Sales Order", villa)
		assert invoiced.one_retention_tax == retention.WITH_INVOICE, invoiced.one_retention_tax
		invoiced.one_retention_tax = retention.WHEN_RELEASED
		try:
			invoiced.save()
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("an invoiced order changed how its retention is taxed")
	untold = _another_villa_order()
	assert frappe.db.get_value("Sales Order", untold, "one_retention_tax") == retention.WHEN_RELEASED
	for name, lines in ((untold, True), (_another_villa_order(retention.WITH_INVOICE), False)):
		with as_user("huda@one.test"):
			line = progress.progress("Sales Order", name)["lines"][0]
			invoice = progress.bill_progress(name, "Sales Order", lines={line["line"]: 50})
			invoice.insert()
		held = [row for row in invoice.items if row.get("one_held")]
		work = sum(flt(row.amount) for row in invoice.items if not row.get("one_held"))
		if lines:
			assert held and _close(invoice.net_total, work + sum(flt(row.amount) for row in held), 0.01), "taxed on the work less its retention"
		else:
			assert not held and set(HELD) & {row.payment_term for row in invoice.payment_schedule}, invoice.payment_schedule
			assert _close(invoice.net_total, work, 0.01), "taxed on all the work"


@check
def oneproject_retention_is_released_and_its_people_follow_the_work():
	"""The villa's retention released in one payment against its invoices'
	retention terms, after which none is held; somebody given a task or
	mentioned joins the project; its customer and kind stay once it has
	orders; and Samir sets its time budget and reads what a cost type booked."""
	from onedesk.one_project import budget, kinds, members, retention, tree
	from onedesk.one_project.progress import HANDOVER, RETENTION

	with as_user(OWNER):
		payment = retention.release(VILLA)
		assert payment.payment_type == "Receive" and payment.references, "a draft receipt against the invoices"
		assert {row.payment_term for row in payment.references} <= {HANDOVER, RETENTION}
		assert _close(payment.paid_amount, sum(flt(row.allocated_amount) for row in payment.references), 0.01)
		payment.reference_no, payment.reference_date = "RET-1", today()
		payment.insert()
		payment.submit()
		try:
			retention.release(VILLA)
		except frappe.ValidationError as e:
			assert "No retention is held here" in str(e), e
		else:
			raise AssertionError("released twice")

	outsider = "mariam@one.test"
	with as_user("samir@one.test"):
		assert members.joins(VILLA, outsider) == frappe.utils.get_fullname(outsider)
		said = members.unseen(VILLA, f'<p><span class="mention" data-id="{outsider}" data-value="Mariam">@Mariam</span> please look</p>')
		assert [one["user"] for one in said["people"]] == [outsider] and said["can_add"]
		members.let_in(VILLA, [outsider])
		assert members.joins(VILLA, outsider) is None, "she is in now"
	assert frappe.has_permission("Project", "read", doc=VILLA, user=outsider)

	assert set(kinds.settled_fields(VILLA)) == {"customer", "one_kind"}
	free = [one for one in frappe.get_all("Project", pluck="name") if not kinds.in_use(one)]
	assert free and kinds.settled_fields(free[0]) == []

	with as_user("samir@one.test"):
		budget.set_time(VILLA, time_budget=12000, hours=400)
		assert (flt(frappe.db.get_value("Project", VILLA, "one_time_budget")), flt(frappe.db.get_value("Project", VILLA, "one_hours_planned"))) == (12000, 400)
		account = budget._budgets(VILLA)[0].account
		rows = budget.booked(VILLA, account)
	gl = sum(flt(one.debit) - flt(one.credit) for one in frappe.get_all("GL Entry", filters={"project": ["in", list(tree.scope(VILLA))], "account": account, "is_cancelled": 0}, fields=["debit", "credit"]))
	assert _close(sum(flt(one["amount"]) for one in rows), flt(gl), 0.01), (rows, gl)


@check
def oneproject_its_terms_travel_from_quotation_to_invoice():
	"""What a project agreed with its customer is on every document made for
	it: a quotation starts with the villa's 30 days and its construction
	terms unless somebody picks others, an order keeps what its quotation
	said, Bill Progress dates the villa's invoice 30 days on with its
	retention after, and the showroom's time is due in 15 days. A supplier's
	bill is due as its purchase order says."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	from onedesk.one_project import billing, progress, retention
	from onedesk.one_project.retention import RETENTION

	villa = frappe.db.get_value("Project", VILLA, ["customer", "one_payment_terms", "one_terms"], as_dict=True)
	assert (villa.one_payment_terms, villa.one_terms) == ("Net 30", "Construction Works"), villa

	def quote(**values):
		doc = frappe.new_doc("Quotation")
		doc.update({"company": COMPANY, "quotation_to": "Customer", "party_name": villa.customer, "project": VILLA, **values})
		doc.append("items", {"item_code": "WIN-CS12", "qty": 2, "rate": 2400})
		doc.insert()
		return doc

	with as_user(OWNER):
		carried = quote()
		assert (carried.payment_terms_template, carried.tc_name) == ("Net 30", "Construction Works"), (carried.payment_terms_template, carried.tc_name)
		assert "Retention" in (carried.terms or ""), carried.terms
		assert quote(tc_name="Professional Services").tc_name == "Professional Services", "terms picked on a quotation are kept"
		carried.submit()
		order = make_sales_order(carried.name)
		order.delivery_date = add_days(today(), 30)
		for row in order.items:
			row.delivery_date = order.delivery_date
		order.insert()
		assert (order.payment_terms_template, order.tc_name) == ("Net 30", "Construction Works"), "the order keeps its quotation's terms"

	with as_user("huda@one.test"):
		name = frappe.db.get_value("Project", VILLA, "sales_order")
		windows = progress.progress("Sales Order", name)["lines"][0]
		draft = progress.bill_progress(name, "Sales Order", lines={windows["line"]: 100})
		assert getdate(draft.due_date) == getdate(add_days(draft.posting_date, 30)), (draft.posting_date, draft.due_date)
		assert draft.tc_name == "Construction Works", draft.tc_name
		schedule = {row.payment_term: getdate(row.due_date) for row in draft.payment_schedule}
		if frappe.db.get_value("Sales Order", name, "one_retention_tax") == retention.WHEN_RELEASED:
			held = {row.one_held: getdate(row.one_release_on) for row in draft.items if row.get("one_held")}
			assert max(schedule.values()) == getdate(draft.due_date) and held.get(RETENTION) > getdate(draft.due_date), (schedule, held)
		else:
			assert schedule.get(None) == getdate(draft.due_date) and schedule.get(RETENTION, schedule[None]) > schedule[None], schedule
		invoice = billing.invoice_time(SHOWROOM, item="SVC-MAINT")
		assert (invoice.payment_terms_template, invoice.tc_name) == ("Net 15", "Professional Services"), (invoice.payment_terms_template, invoice.tc_name)
		assert getdate(invoice.due_date) == getdate(add_days(invoice.posting_date, 15)), (invoice.posting_date, invoice.due_date)

	po = frappe.db.get_value("Purchase Order", {"project": VILLA, "docstatus": 1, "per_billed": ["<", 100]})
	assert po, "the villa has a purchase order to bill"
	frappe.db.set_value("Purchase Order", po, "payment_terms_template", "Net 45")
	with as_user(OWNER):
		bill = make_purchase_invoice(po)
		bill.bill_no, bill.bill_date = "TERMS-1", today()
		bill.insert()
	assert bill.payment_terms_template == "Net 45" and bill.tc_name != "Construction Works", (bill.payment_terms_template, bill.tc_name)


@check
def oneproject_a_project_starts_with_its_customers_and_its_templates_terms():
	"""A new project's payment terms are its customer's own before its
	template's, and its wording the template's. A preset from the library
	brings both and its retention onto the contract, where the workspace holds
	retention. Add Contract may agree others, and an internal project has none."""
	from onedesk.one_demo.projects import TEMPLATE
	from onedesk.one_project import kinds, library

	with as_user("samir@one.test"):
		said = kinds.defaults("Bayview Developments", TEMPLATE)
		assert (said["payment_terms"], said["terms"]) == ("Net 45", "Construction Works"), said
		said = kinds.defaults("Mansour & Sons", TEMPLATE)
		assert (said["payment_terms"], said["terms"], said["retention"], said["retention_handover"]) == ("Net 30", "Construction Works", 5, 50), said
		frappe.db.set_single_value("Projects Settings", "one_retention", 0)
		assert kinds.defaults("Mansour & Sons", TEMPLATE)["retention"] == 0, "no retention where the workspace holds none"
		frappe.db.set_single_value("Projects Settings", "one_retention", 1)
		website = library.copy("website")
		assert frappe.db.get_value("Project Template", website, ["one_payment_terms", "one_terms"]) == ("Net 15", "Software and Websites")
		assert "belongs to the client" in frappe.db.get_value("Terms and Conditions", "Software and Websites", "terms")
		days = frappe.get_doc("Payment Terms Template", "Net 15").terms
		assert [(row.invoice_portion, row.credit_days) for row in days] == [(100, 15)], days
		name = kinds.make({"title": "Mansour Pool House", "kind": "Fixed Price", "client": "Mansour & Sons", "library": "interior_fit_out", "starts": today(), "ends": add_days(today(), 365), "contract": 40000, "item": "SVC-INST"})
		project = frappe.db.get_value("Project", name, ["one_payment_terms", "one_terms", "sales_order"], as_dict=True)
		assert (project.one_payment_terms, project.one_terms) == ("Net 30", "Construction Works"), project
		order = frappe.db.get_value("Sales Order", project.sales_order, ["payment_terms_template", "tc_name", "one_retention", "one_retention_handover"], as_dict=True)
		assert (order.payment_terms_template, order.tc_name, flt(order.one_retention), flt(order.one_retention_handover)) == ("Net 30", "Construction Works", 5, 50), order
		inside = kinds.make({"title": "Workshop Shelving", "kind": "Internal", "starts": today(), "ends": add_days(today(), 365), "template": TEMPLATE})
		assert frappe.db.get_value("Project", inside, ["one_payment_terms", "one_terms"]) == (None, None)
		order = kinds.add_contract(ACME, 85000, "SVC-INST", payment_terms="Net 15", conditions="Professional Services")
	assert frappe.db.get_value("Project", ACME, ["one_payment_terms", "one_terms"]) == ("Net 15", "Professional Services")
	assert frappe.db.get_value("Sales Order", order, ["payment_terms_template", "tc_name"]) == ("Net 15", "Professional Services")


@check
def oneproject_its_page_says_only_what_is_so():
	"""Samir runs projects but reads no invoices. The retainer still says
	which months are invoiced and how they stand, without the invoice, and
	Invoiced says what's paid, the project's own total. The showroom's
	unbilled time reads the same in its card and its list, in the company's
	currency. A finished job's fourth card is its Margin, and a sub-project
	whose work is on its parent's order says so and bills on its terms."""
	from onedesk.one_project import retainer, terms, view

	with as_user("samir@one.test"):
		assert not frappe.has_permission("Sales Invoice", "read")
		months = {one["month"]: one["invoice"] for one in retainer.months(MARINA)["months"]}
		done = [month for month, invoice in months.items() if invoice]
		assert done and all(months[m]["status"] and months[m]["name"] is None and months[m]["total"] is None for m in done), months
		assert not set(done) & set(retainer.waiting(MARINA)), "an invoiced month waits"
		invoiced = next(card for card in view.said(MARINA)["cards"] if card["key"] == "invoiced")
		assert invoiced["note_money"], invoiced
		showroom = view.said(SHOWROOM)
		card = next(one for one in showroom["cards"] if one["key"] == "unbilled")
		assert abs(card["money"] - sum(one["amount"] for one in showroom["overview"]["unbilled"])) < 1, (card, showroom["overview"]["unbilled"])
		finished = view.said("PROJ-0007")
		assert [one["key"] for one in finished["cards"]][-1] == "margin", finished["cards"]
		podium = view.said("PROJ-0004")
		first = podium["cards"][0]
		assert first["value"] == "–" and "Bayview Tower Curtain Wall" in first["note"], first
		assert podium["terms_from"] == "Bayview Tower Curtain Wall"
		assert terms.of("PROJ-0004")[0] == frappe.db.get_value("Project", TOWER, "one_payment_terms") == podium["payment_terms"]


@check
def oneproject_its_tabs_add_up():
	"""Tasks, Time and Money read true to Samir, who reads no invoices. Work
	under way says how far along it is. Time's groups add up every entry,
	the older ones not sent included, and its count is all of them. Money
	shows the customer's totals that its figures are made of, opening the
	invoices only for those who may, in the company's currency."""
	from onedesk.one_project import hours, money

	with as_user("samir@one.test"):
		working = frappe.get_all("Task", filters={"project": VILLA, "status": "Working"}, pluck="progress")
		assert working and all(working), working
		said = hours.entries(VILLA)
		assert said["more"] and said["all_route"].startswith("/desk/timesheet?"), said["more"]
		assert sum(one["entries"] for one in said["sums"]) == len(said["entries"]) + said["more"]
		assert abs(sum(one["hours"] for one in said["sums"]) - said["totals"]["hours"]) < 0.1
		for project in (MARINA, SHOWROOM):
			cash = money.money(project)
			invoiced = next(one for one in cash["customer"] if one["label"] == "Invoiced")
			assert abs(invoiced["value"] - cash["invoiced"]) < 1 and "route" not in invoiced, invoiced
			company = frappe.db.get_value("Project", project, "company")
			assert cash["currency"] == frappe.db.get_value("Company", company, "default_currency")


@check
def oneproject_its_invoices_suppliers_team_and_activity_read_true():
	"""An invoice is due as its terms say from its own date, not the day the
	demo was built; retention stays held until it's released, on both sides;
	each customer's project names who speaks for them; and the team's time is
	one line a week in Activity, naming everyone who logged it."""
	from onedesk.one_project import activity, contacts
	from onedesk.one_project.retention import HELD

	for doctype in ("Sales Invoice", "Purchase Invoice"):
		for one in frappe.get_all(doctype, filters={"docstatus": 1, "project": ["in", [VILLA, TOWER]]}, fields=["name", "posting_date"]):
			own = frappe.get_all(
				"Payment Schedule",
				filters={"parent": one.name, "parenttype": doctype, "payment_term": ["not in", HELD]},
				fields=["due_date", "payment_term"],
			)
			for row in own:
				days = frappe.db.get_value("Payment Term", row.payment_term, "credit_days") if row.payment_term else 0
				assert date_diff(row.due_date, one.posting_date) >= (days or 0), (one.name, row)
	from onedesk.one_project import tree
	from onedesk.one_project.retention import held_on, invoices

	for doctype in ("Sales Invoice", "Purchase Invoice"):
		held = held_on(doctype, invoices(doctype, sorted(tree.scope(VILLA))))
		assert held and all(amount > 0 for parts in held.values() for _due, amount in parts), (doctype, held)
	with as_user("samir@one.test"):
		assert "Client's Representative" in {one["role"] for one in contacts.contacts(VILLA)["contacts"]}
		weeks = activity._time(sorted(tree.scope(VILLA)), activity._People())
		keys = [one["key"] for one in weeks]
		assert len(keys) == len(set(keys)) and any(one["data"]["people"] > 1 for one in weeks), keys[:5]


@check
def oneproject_oneai_reminds_adds_and_the_rules_stand():
	"""OneAI reads the late invoices and what is due to each subcontractor,
	and its cards remind a customer, add a member and add a contact only when
	approved, the reminder opening to send rather than sent. A bill due today
	is told to the manager. A member who can't sign in can't join, however
	they're added. Each document says it was made on its own date."""
	from unittest.mock import patch

	from onedesk.one_ai import proposals
	from onedesk.one_project import agent, billing, contacts
	from onedesk.one_project.retention import HELD

	with as_user(OWNER):
		facts = agent.project_facts(TOWER)
		late = facts["invoices"]["overdue"]
		assert late and all(one["days_late"] > 0 for one in late), facts["invoices"]
		assert all("to_pay" in one and "due" in one for one in facts["money"]["subcontracts"])
		mails = frappe.db.count("Communication")
		card = agent.remind_customer(late[0]["invoice"], "Dear Bayview,\n\nA reminder that this invoice is past its date.")
		said = proposals.apply(card["proposal"])
		assert said["mail"]["text"].startswith("Dear Bayview") and said["mail"]["subject"], said
		assert frappe.db.count("Communication") == mails, "a reminder is opened to send, never sent"
	with as_user("samir@one.test"):
		assert not agent.project_facts(TOWER)["invoices"]["overdue"]
		on = set(frappe.get_all("Project User", filters={"parent": VILLA, "parenttype": "Project"}, pluck="user"))
		joins = next(one for one in ("rania@one.test", "nadia@one.test", "tariq@one.test", "omar@one.test", "karim@one.test") if one not in on)
		card = agent.add_member(VILLA, joins)
		assert card.get("state") == "Proposed", card
		assert not frappe.db.exists("Project User", {"parent": VILLA, "user": joins})
		proposals.apply(card["proposal"])
		assert frappe.db.exists("Project User", {"parent": VILLA, "user": joins})
		card = agent.add_contact(VILLA, "Engineer", organisation="Gulf Structural Engineers", note="Checks the brackets")
		proposals.apply(card["proposal"])
		assert "Gulf Structural Engineers" in {one["company"] for one in contacts.contacts(VILLA)["contacts"]}
	bill = frappe.get_all("Purchase Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0], "project": ["is", "set"]}, pluck="name")[0]
	for row in frappe.get_all("Payment Schedule", filters={"parent": bill, "parenttype": "Purchase Invoice"}, fields=["name", "payment_term"]):
		if row.payment_term not in HELD:
			frappe.db.set_value("Payment Schedule", row.name, {"due_date": today(), "outstanding": 1000})
	told = []
	with patch("onedesk.one_project.tell.bill_due", side_effect=lambda *args: told.append(args)):
		billing.bills_due()
	assert bill in {one[0] for one in told}, told
	gone = frappe.get_doc({"doctype": "User", "email": "gone@one.test", "first_name": "Gone", "enabled": 0, "send_welcome_email": 0}).insert(ignore_permissions=True)
	project = frappe.get_doc("Project", VILLA)
	project.append("users", {"user": gone.name})
	try:
		project.save(ignore_permissions=True)
	except frappe.ValidationError:
		pass
	else:
		raise AssertionError("somebody who can't sign in joined the project")
	first = frappe.get_all("Sales Invoice", filters={"docstatus": 1}, fields=["name", "posting_date", "creation"], order_by="posting_date asc", limit=1)[0]
	assert getdate(first.creation) == getdate(first.posting_date), first


@check
def oneproject_workload_time_and_templates_read_true():
	"""Workload says who is over this week and who is late, its cards to a
	tenth of an hour; OneAI reads the same week; a timesheet prints as One
	Timesheet; and the template is Samir's."""
	from onedesk.one_ai import tools
	from onedesk.one_project.report.workload import workload

	with as_user("samir@one.test"):
		_columns, rows, _week, _chart, cards = workload.execute({"week": today()})
		assert any((one["load"] or 0) > 100 for one in rows), [(one["full_name"], one["load"]) for one in rows]
		assert any(one["late"] for one in rows)
		assert all("." not in str(one["value"]) or len(str(one["value"]).split(".")[-1]) == 1 for one in cards), cards
		said = tools.run_report("Workload", {"week": today()}, limit=100)
		assert said["rows"] and {one["user"] for one in said["rows"]} == {one["user"] for one in rows}
		assert said.get("summary"), "the week's totals ride along"
		sheet = frappe.get_all("Timesheet", filters={"docstatus": 1}, pluck="name", limit=1)[0]
		printed = frappe.get_print("Timesheet", sheet, "One Timesheet")
		assert frappe.db.get_value("Timesheet", sheet, "employee_name") in printed
	assert frappe.db.get_value("Project Template", "Aluminium & Glazing", "owner") == "samir@one.test"


@check
def oneproject_and_onetask_reports_open_for_their_people():
	"""ERPNext's and HRMS's project reports in the two rails run for Samir,
	the busy ones with rows, under their own names; Mariam, who works on no
	project, is not offered Task Delays."""
	from frappe.desk.desk_views import DeskViews
	from frappe.desk.query_report import run

	rails = {
		"OneProject": {
			"Project Progress": "Project Progress",
			"Project Profitability": "Project Profitability",
			"Timesheet Billing Summary": "Timesheet Billing Summary",
			"Daily Timesheet Summary": "Daily Timesheet Summary",
			"Stock by Project": "Stock by Project",
		},
		"OneTask": {"Delayed Tasks Summary": "Delayed Tasks Summary"},
	}
	company = frappe.defaults.get_global_default("company")
	month = {"from_date": add_days(today(), -60), "to_date": today()}
	wanted = {
		"Project Profitability": {"start_date": month["from_date"], "end_date": month["to_date"]},
		"Timesheet Billing Summary": {**month, "group_by": "Group by Employee"},
		"Daily Timesheet Summary": month,
	}
	busy = {"Project Progress", "Timesheet Billing Summary", "Daily Timesheet Summary", "Stock by Project", "Delayed Tasks Summary"}
	with as_user("samir@one.test"):
		for sidebar, reports in rails.items():
			for report, label in reports.items():
				row = frappe.db.get_value("Sidebar Item", {"parent": sidebar, "link_to": report}, "label")
				assert row == label, (sidebar, report, row)
				said = run(report, filters={"company": company, **wanted.get(report, {})})
				assert report not in busy or said["result"], report
		checklists = set(frappe.get_all("Project", filters={"project_type": "Employee Boarding"}, pluck="name"))
		assert checklists
		for report in ("Project Progress", "Stock by Project"):
			rows = run(report, filters={})["result"]
			named = {row.get("name") or row.get("project_id") for row in rows}
			assert not named & checklists, (report, named & checklists)
	with as_user("mariam@one.test"):
		assert "Delayed Tasks Summary" not in DeskViews.get_allowed_reports()


@check
def oneproject_its_contracts_are_on_the_page():
	"""A project has as many contracts as it signs. The villa's contract is
	signed and its staircase addendum, on the staircase's sub-project, waits
	for the customer, so About shows the signed one, the Overview lists both
	with what each covers, and Needs You asks for the addendum by name. The tower's scaffolding subcontractor signed from the
	subcontract template. Samir reads them but draws none up. A supplier's
	contract needs a template and a supplier on the project. One ending in a
	month is to renew, unless a later one with the same party runs on."""
	from onedesk.one_demo.projects import SUBCONTRACT
	from onedesk.one_project import agreement, view

	with as_user("samir@one.test"):
		villa = view.said(VILLA)
		own = [one for one in villa["contracts"] if one["project"] == VILLA]
		assert [one["signed"] for one in own] == [True], own
		addendum = [one for one in villa["contracts"] if one["project_title"] == "Staircase balustrade"]
		assert [one["signed"] for one in addendum] == [False], villa["contracts"]
		assert villa["agreement"]["signed"] and villa["agreement"]["ends"] and not villa["agreement"]["route"], villa["agreement"]
		assert not villa["can_draw_up"]
		asked = agreement.asks(frappe.get_doc("Project", VILLA), villa["contracts"])
		assert [(one["text"], one["dim"]) for one in asked] == [("Get the contract signed", "Mansour & Sons · Staircase balustrade")], asked
		tower = view.said(TOWER)
		scaffold = [one for one in tower["contracts"] if one["party_type"] == "Supplier"]
		assert [(one["party"], one["signed"]) for one in scaffold] == [("Rapid Scaffolding", True)], scaffold
		assert tower["agreement"]["party"] == "Bayview Developments" and not tower["agreement"]["signed"], tower["agreement"]
		try:
			agreement.draw_up(ACME)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who may not make contracts drew one up")
	with as_user(OWNER):
		offered = {(one["party_type"], one["party"]) for one in agreement.parties(TOWER)}
		assert {("Customer", "Bayview Developments"), ("Supplier", "Rapid Scaffolding")} <= offered, offered
		for kwargs in ({"party_type": "Supplier", "party": "Rapid Scaffolding"}, {"party_type": "Supplier", "party": "Precision Installers", "template": SUBCONTRACT}):
			try:
				agreement.draw_up(TOWER, **kwargs)
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError(f"a supplier's contract was drawn up from {kwargs}")
		again = frappe.get_doc("Contract", agreement.draw_up(TOWER, template=SUBCONTRACT, party_type="Supplier", party="Rapid Scaffolding"))
		assert (again.party_type, again.document_name) == ("Supplier", TOWER) and "subcontractor" in again.contract_terms
		assert view.said(ACME)["can_draw_up"]
		doc = frappe.get_doc("Contract", agreement.draw_up(ACME))
		acme = frappe.db.get_value("Project", ACME, ["customer", "expected_start_date", "expected_end_date"], as_dict=True)
		assert (doc.party_type, doc.party_name, doc.document_type, doc.document_name) == ("Customer", acme.customer, "Project", ACME)
		assert (doc.start_date, doc.end_date) == (acme.expected_start_date, acme.expected_end_date)
		assert "Materials stay ours" in doc.contract_terms and doc.status == "Unsigned", doc.contract_terms
		doc.update({"is_signed": 1, "signee": "Dana Brooks", "signed_on": now_datetime(), "start_date": getdate(add_days(today(), -30)), "end_date": getdate(add_days(today(), 10))})
		doc.submit()
		project = frappe.get_doc("Project", ACME)
		said = agreement.asks(project, agreement.contracts([ACME]))
		assert [(one["text"], one["dim"]) for one in said] == [("Renew the contract", "Acme Holdings · Ends in 10 days")], said
		renewal = frappe.get_doc("Contract", agreement.draw_up(ACME))
		renewal.update({"is_signed": 1, "signee": "Dana Brooks", "signed_on": now_datetime(), "start_date": getdate(add_days(today(), 10)), "end_date": getdate(add_days(today(), 375))})
		renewal.submit()
		assert agreement.asks(project, agreement.contracts([ACME])) == [], "a renewed contract is not asked for again"
		assert agreement.main(ACME)["name"] == renewal.name


@check
def oneproject_a_project_is_seen_by_its_people_and_its_plan_follows():
	"""Rania sees the projects she is on, what is under them and those nobody
	is on, in the company she is limited to, and no other. Somebody made a project's manager sees it. A member
	added is told in One and shared the project, never sent ERPNext's mail,
	and loses the share when taken off. A slip moves what waits on it in a
	sub-project, work already started included."""
	from onedesk.one_project import members, team, tree

	assert members.narrowed("rania@one.test") and not members.narrowed("huda@one.test")
	of = tree.parents()
	teams = {one.name: _team(one.name) for one in frappe.get_all("Project", fields=["name"])}
	hers = tree.below({name for name, people in teams.items() if "rania@one.test" in people or not people}, of)
	limited = set(frappe.get_all("User Permission", {"user": "rania@one.test", "allow": "Company"}, pluck="for_value"))
	if limited:
		hers = {name for name in hers if frappe.db.get_value("Project", name, "company") in limited}
	with as_user("rania@one.test"):
		seen = set(frappe.get_list("Project", pluck="name", limit=0))
	assert seen == hers and "PROJ-0002" in seen and "PROJ-0011" not in seen, (seen ^ hers)

	frappe.db.set_value("Project", "PROJ-0011", "one_manager", "rania@one.test")
	members.forget()
	with as_user("rania@one.test"):
		assert frappe.has_permission("Project", "read", doc="PROJ-0011"), "the manager sees what they run"

	queued = frappe.db.count("Email Queue")
	with _Told() as told, as_user("samir@one.test"):
		team.add("PROJ-0013", "rania@one.test")
	assert "rania@one.test" in told.to("Added to Project"), told.said
	assert frappe.db.get_value("Project User", {"parent": "PROJ-0013", "user": "rania@one.test"}, "welcome_email_sent") == 1
	assert frappe.db.count("Email Queue") == queued, "ERPNext's invitation went out"
	assert frappe.db.exists("DocShare", {"share_doctype": "Project", "share_name": "PROJ-0013", "user": "rania@one.test"})
	with as_user("samir@one.test"):
		team.remove("PROJ-0013", "rania@one.test")
	assert not frappe.db.exists("DocShare", {"share_doctype": "Project", "share_name": "PROJ-0013", "user": "rania@one.test"})
	members.forget()
	with as_user("rania@one.test"):
		assert not frappe.has_permission("Project", "read", doc="PROJ-0013")

	with as_user("samir@one.test"):
		first = frappe.get_doc({"doctype": "Task", "subject": "Fix the stair posts", "project": VILLA, "exp_start_date": today(), "exp_end_date": add_days(today(), 2)}).insert()
		then = frappe.get_doc({"doctype": "Task", "subject": "Fit the balustrade glass", "project": "PROJ-0002", "status": "Working", "exp_start_date": add_days(today(), 3), "exp_end_date": add_days(today(), 5), "depends_on": [{"task": first.name}]}).insert()
		first.exp_end_date = add_days(today(), 6)
		first.save()
	moved = frappe.db.get_value("Task", then.name, ["exp_start_date", "exp_end_date"], as_dict=True)
	assert (getdate(moved.exp_start_date), getdate(moved.exp_end_date)) == (getdate(add_days(today(), 7)), getdate(add_days(today(), 9))), moved


@check
def oneproject_a_template_hands_on_what_erpnext_leaves_out():
	"""A template task is nobody's work, and everybody in projects reads it.
	Added to the villa, once the villa has a prefix, the tasks take its
	prefix, and the one Samir gave steps to brings them, with whether it is a
	milestone and the hours it is planned at."""
	from onedesk.one_demo.projects import TEMPLATE
	from onedesk.one_project import template_view, templates

	with as_user("samir@one.test"):
		source = next(one for one in template_view.read(TEMPLATE)["tasks"] if not one["is_group"])["name"]
		step = frappe.get_doc("Task", source)
		step.append("one_steps", {"step": "Check the anchor spacing"})
		step.save()
		frappe.db.set_value("Task", source, {"is_milestone": 1, "expected_time": 6})
		made = template_view.add(TEMPLATE, "Seal the joints")
		assert not frappe.parse_json(frappe.db.get_value("Task", made, "_assign") or "[]"), "a template task is given to nobody"
		villa = frappe.get_doc("Project", VILLA)
		villa.one_key = "vil"
		villa.expected_end_date = add_days(today(), 365)
		villa.save()
		assert villa.one_key == "VIL"
		count = templates.add(VILLA, template=TEMPLATE, starts=today())
	added = frappe.get_all("Task", filters={"project": VILLA, "template_task": ["is", "set"], "creation": [">=", add_to_date(now_datetime(), minutes=-1)]}, fields=["name", "template_task", "is_milestone", "expected_time"])
	assert len(added) == count and all(one.name.startswith("VIL-") for one in added), [one.name for one in added]
	copy = next(one for one in added if one.template_task == source)
	assert copy.is_milestone and flt(copy.expected_time) == 6, copy
	assert frappe.get_all("Task Step", filters={"parent": copy.name}, pluck="step") == ["Check the anchor spacing"]
	with as_user("rania@one.test"):
		assert frappe.has_permission("Task", "read", doc=source), "a projects user reads the template's tasks"
		assert source in frappe.get_list("Task", filters={"is_template": 1}, pluck="name", limit=0)
	with as_user("samir@one.test"):
		try:
			frappe.get_doc("Project", TOWER).update({"one_key": "VIL"}).save()
		except frappe.ValidationError as e:
			assert "already names the tasks of" in str(e), e
		else:
			raise AssertionError("two projects took the same prefix")


@check
def oneproject_money_reads_as_its_documents_and_its_people_are_told():
	"""A margin to come needs a price, so a retainer, an internal project and
	time with no order have none, and the margin so far is what was earned
	less what was spent. Extra work ordered is the sub-project's order. A
	progress bill keeps the order's prices and sets advances off, and its
	draft is the manager's to check. A retainer's month bills its time. Who
	runs a project hears when a cost type passes its budget, a retainer its
	hours, a task its plan and the project its end. Whoever may not read
	invoices is not shown them."""
	from onedesk.one_project import billing, budget, hours, money, progress, retainer, status, view

	with as_user("samir@one.test"):
		for project in ("PROJ-0010", MARINA, "PROJ-0013"):
			assert money.money(project)["forecast_margin"] is None, project
		for project in (VILLA, SHOWROOM, MARINA, "PROJ-0013"):
			said = money.money(project)
			assert _close(said["margin"], said["earned"] - said["spent"], 1) and _close(said["earned"], said["invoiced"] + said["to_invoice"], 1), (project, said)
		villa = money.money(VILLA)
		assert _close(villa["forecast_margin"], villa["contract"] - villa["forecast_cost"], 1), villa

	extra = frappe.db.get_value("Project", "PROJ-0002", ["sales_order", "one_parent"], as_dict=True)
	assert extra.one_parent == VILLA and frappe.db.get_value("Sales Order", extra.sales_order, "project") == "PROJ-0002"
	assert set(frappe.get_all("Sales Order Item", filters={"parent": extra.sales_order}, pluck="project")) == {"PROJ-0002"}

	order = frappe.db.get_value("Project", VILLA, "sales_order")
	with as_user("huda@one.test"):
		windows = progress.progress("Sales Order", order)["lines"][0]
		draft = progress.bill_progress(order, "Sales Order", lines={windows["line"]: 100})
		ordered = frappe.db.get_value("Sales Order Item", windows["line"], "rate")
		assert _close(draft.items[0].rate, ordered, 0.01) and draft.allocate_advances_automatically and flt(draft.one_progress), draft.as_dict()
		with _Told() as told:
			draft.insert()
		assert "samir@one.test" in told.to("Progress Bill Drafted"), told.said
		month = retainer.invoice_month(MARINA, month=str(get_first_day(today())), item="SVC-MAINT")
		logged = frappe.get_all("Timesheet Detail", filters={"project": MARINA, "docstatus": 1, "from_time": [">=", get_first_day(today())], "is_billable": 1, "sales_invoice": ["is", "not set"]}, pluck="name")
		assert {row.timesheet_detail for row in month.timesheets} == set(logged), (month.timesheets, logged)

	with as_user("samir@one.test"):
		line = next(one for one in budget.lines(VILLA)["lines"] if flt(one.get("committed")))
		budget.set_budget(VILLA, line["account"], flt(line["spent"]) + 1)
		with _Told() as told:
			budget.over(VILLA)
		assert "samir@one.test" in told.to("Over Budget"), told.said

		used = retainer.logged(MARINA, get_first_day(today()))
		frappe.db.set_value("Project", MARINA, {"one_monthly_hours": used + 2, "one_manager": "huda@one.test"})
		sheet = hours.log(MARINA, today(), 3, "Project Management", description="Inspection round")
		with _Told() as told:
			frappe.get_doc("Timesheet", sheet).submit()
		assert "huda@one.test" in told.to("Retainer Hours Used"), (used, told.said)

		task = frappe.get_doc({"doctype": "Task", "subject": "Seal the frames", "project": VILLA, "expected_time": 1}).insert()
		frappe.desk.form.assign_to.add({"doctype": "Task", "name": task.name, "assign_to": ["rania@one.test"]})
		sheet = hours.log(VILLA, today(), 2, "Installation", task=task.name)
		with _Told() as told:
			frappe.get_doc("Timesheet", sheet).submit()
		assert "rania@one.test" in told.to("Hours Over Plan"), told.said
		assert frappe.db.get_value("Task", task.name, "status") != "Completed", "timing a task does not finish it"

	with _Told() as told, as_user(OWNER):
		status.change("PROJ-0010", "Completed", close=1)
	assert "samir@one.test" in told.to("Project Completed"), told.said

	with as_user("rania@one.test"):
		shown = view.said(VILLA)["views"]
		assert "invoices" not in shown and "suppliers" in shown, shown
		try:
			assert not billing.invoices(VILLA)["invoices"]
		except frappe.PermissionError:
			pass


@check
def oneproject_its_people_are_asked_and_its_customer_reads_their_own():
	"""A project's team is asked for an update in One. A retainer whose last
	month is not invoiced is told to whoever runs it. OneAI reads a project
	only for somebody who may open it. The villa's customer, invited to the
	portal by Omar, reads the villa and not another customer's project, and sees
	nothing of who in the team does what."""
	from unittest import mock

	from onedesk.one_portal import invite as portal_invite
	from onedesk.one_project import agent, portal, tell, updates

	with _Told() as told:
		updates._ask(VILLA)
	assert _team(VILLA) - {"yousef@one.test"} <= told.to("Project Update Asked"), told.said
	assert frappe.db.exists("Project Update", {"project": VILLA, "date": today()})

	frappe.db.set_value("Sales Invoice", {"project": "PROJ-0012", "one_retainer_month": str(add_months(get_first_day(today()), -1))}, "one_retainer_month", None)
	with _Told() as told:
		tell.retainer_months()
	assert "samir@one.test" in told.to("Retainer Month to Invoice"), told.said

	with as_user("rania@one.test"):
		assert agent.project_facts(VILLA)["title"] == "Mansour Villa Windows and Doors"
		assert "error" in agent.project_facts(MARINA), "a project she is not on"

	contact = next(one.parent for one in frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "link_doctype": "Customer", "link_name": "Mansour & Sons"}, fields=["parent"]))
	with as_user("omar@one.test"), mock.patch("onedesk.one.tell.invited_to_portal"):
		assert portal_invite.invite_contact(contact)["status"] in ("invited", "active")
	khalid = frappe.db.get_value("Contact", contact, "user")
	with as_user(khalid):
		said = portal.view(VILLA)
		assert said["tasks"] and not {"_assign", "owner"} & set(said["tasks"][0]), said["tasks"][0]
		try:
			portal.view(TOWER)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a customer read another customer's project")


@check
def oneproject_profit_on_billed_hours():
	"""Imran is paid by the hour from his timesheets, and his retainer hours
	are invoiced, so ERPNext's Profit on Billed Hours has his rows. His slip
	pays his hours at his rate; each row costs his month's gross pay times
	the share of the month he billed, and its profit is the invoice less
	that. The rows name him, from the timesheet's title."""
	from hrms.hr.report.project_profitability.project_profitability import execute

	from onedesk.one_demo.hr import HOUR_RATE, HOURS

	imran = _employee("Imran")
	slips = frappe.get_all("Salary Slip", filters={"employee": imran, "docstatus": 1, "salary_slip_based_on_timesheet": 1}, pluck="name")
	assert slips, "Imran has no slip worked out from his timesheets"
	for name in slips:
		slip = frappe.get_doc("Salary Slip", name)
		paid = sum(flt(row.amount) for row in slip.earnings if row.salary_component == HOURS)
		assert flt(paid, 2) == flt(slip.total_working_hours * HOUR_RATE, 2), (name, paid, slip.total_working_hours)
	rows = execute(frappe._dict(company=COMPANY, employee=imran))[1]
	assert rows, "Profit on Billed Hours has no rows"
	standard = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours"))
	places = cint(frappe.db.get_default("float_precision")) or 2
	for row in rows:
		share = flt(flt(row.total_billed_hours) / (flt(row.total_working_days) * standard), places)
		assert row.utilization == share, row
		assert row.profit == flt(flt(row.base_grand_total) - flt(row.base_gross_pay) * share, places), row
		assert row.employee_name == "Imran Khan", row.employee_name


@check
def oneproject_what_a_member_sees_on_the_portal():
	"""Khalid is on the villa's team. His row on Team says he sees its files on
	the portal and not its timesheets, and the portal does as it says; shown,
	the time is the villa's submitted hours."""
	from onedesk.one_project import portal, team

	khalid = frappe.db.get_value("User", {"email": "khalid@mansour.example"})
	with as_user("samir@one.test"):
		row = next(one for one in team.team(VILLA)["people"] if one["user"] == khalid)
	assert row["member"] and row["portal"] and row["files"] and not row["timesheets"], row
	with as_user(khalid):
		said = portal.view(VILLA)
	assert said["time"] is None and said["files"] is not None, said["time"]
	with as_user("samir@one.test"):
		team.show(VILLA, khalid, timesheets=1)
	try:
		with as_user(khalid):
			said = portal.view(VILLA)
		logged = frappe.db.sql(
			"select sum(hours) from `tabTimesheet Detail` where project=%s and docstatus=1", VILLA
		)[0][0]
		assert said["time"] and flt(said["time"]["hours"]) == flt(logged), (said["time"], logged)
	finally:
		with as_user("samir@one.test"):
			team.show(VILLA, khalid, timesheets=0)


@check
def oneproject_a_day_on_site_and_the_projects_pictures():
	"""The tower counts its time by attendance on its site: the installers'
	days there are on it, a day Tariq clocked in there is a day on the tower, and cancelling the attendance
	takes it off again. The villa's Cover is shown first, and deleting it
	hands the Cover on rather than leaving the project pointing at nothing."""
	from onedesk.one_project import hours, media

	assert frappe.db.get_value("Project", TOWER, "one_time") == hours.ATTENDANCE, "the tower counts its time by attendance"
	assert frappe.get_all("Timesheet", filters={"one_attendance": ["is", "set"], "parent_project": TOWER, "docstatus": 1}), "no installer's day on site is on the tower"
	tariq = _employee("Tariq")
	day = next(
		one
		for one in (add_days(today(), -n) for n in range(1, 90))
		if not frappe.db.exists("Attendance", {"employee": tariq, "attendance_date": one, "docstatus": ["<", 2]})
		and not frappe.db.exists("Leave Application", {"employee": tariq, "from_date": ["<=", one], "to_date": [">=", one], "docstatus": ["<", 2]})
	)
	frappe.get_doc({"doctype": "Employee Checkin", "employee": tariq, "log_type": "IN", "time": f"{day} 07:40:00", "latitude": 25.0806, "longitude": 55.1402}).insert(ignore_permissions=True)
	with as_user("mariam@one.test"):
		attendance = frappe.get_doc({"doctype": "Attendance", "employee": tariq, "attendance_date": day, "status": "Present", "company": COMPANY}).insert()
		attendance.submit()
	sheet = frappe.db.get_value("Timesheet", {"one_attendance": attendance.name, "docstatus": 1})
	assert sheet and frappe.db.get_value("Timesheet Detail", {"parent": sheet}, "project") == TOWER, sheet
	spent = frappe.db.get_value("Timesheet Detail", {"parent": sheet}, ["hours", "costing_amount", "activity_type"], as_dict=True)
	rate = frappe.db.get_value("Activity Cost", {"employee": tariq, "activity_type": spent.activity_type}, "costing_rate") or frappe.db.get_value("Activity Type", spent.activity_type, "costing_rate")
	assert flt(rate) > 0 and flt(spent.costing_amount, 2) == flt(spent.hours * rate, 2), (spent, rate)
	with as_user("mariam@one.test"):
		attendance.reload()
		attendance.cancel()
	assert frappe.db.get_value("Timesheet", sheet, "docstatus") == 2, "the day went with its attendance"

	from onedesk.one_cloud import upload

	with as_user("samir@one.test"):
		upload._place(media.node(VILLA), None, {"file_name": "Dusk on site.png", "content": _png(sky=(250, 196, 140))})
	cover = frappe.db.get_value("File", {"file_name": "Dusk on site.png", "attached_to_name": VILLA}, "file_url")
	frappe.db.set_value("Project", VILLA, "one_cover", cover)
	assert cover and media.shown(VILLA)[0]["url"] == cover
	with as_user("samir@one.test"):
		frappe.delete_doc("File", frappe.db.get_value("File", {"file_url": cover, "attached_to_name": VILLA}))
	assert frappe.db.get_value("Project", VILLA, "one_cover") not in (cover, None), "the Cover still pointed at a deleted photo"


@check
def oneproject_its_views_read_as_their_people_and_oneai_starts_one():
	"""Rania's Projects list, its counts and its charts are her own projects,
	and the villa is among those needing attention. OneAI's card makes a
	project only when approved, with the customer's terms, and a project made
	any other way starts with them too."""
	from frappe.desk.doctype.dashboard_chart.dashboard_chart import get as chart
	from frappe.desk.doctype.number_card.number_card import get_result

	from onedesk.one_ai import proposals
	from onedesk.one_demo.projects import TEMPLATE
	from onedesk.one_project import agent

	open_ = {"status": "Open", "project_type": ["!=", "Employee Boarding"]}
	every = frappe.get_all("Project", filters=open_, pluck="name")
	with as_user("rania@one.test"):
		mine = frappe.get_list("Project", filters=open_, pluck="name")
		assert mine and len(mine) < len(every), "Rania reads only her projects"
		card = frappe.get_doc("Number Card", "Projects Under Way")
		assert get_result(card.as_dict(), card.filters_json) == len(mine)
		for name in ("Projects by Kind", "Projects by Health"):
			drawn = chart(chart_name=name, refresh=1)
			assert sum(drawn["datasets"][0]["values"]) == len(mine), (name, drawn)
		assert VILLA in {one["project"] for one in agent.projects_needing_attention()["projects"]}
	with as_user("samir@one.test"):
		assert agent.draft_project("Mansour Garden Room", "Fixed Price", "Mansour & Sons", contract=30000).get("error"), "a contract is billed as an item"
		card = agent.draft_project("Mansour Garden Room", "Fixed Price", "Mansour & Sons", template=TEMPLATE, contract=30000, item="SVC-INST", ends=add_days(today(), 365))
		assert card.get("state") == "Proposed", card
		assert not frappe.db.exists("Project", {"project_name": "Mansour Garden Room"}), "nothing is made until approved"
		name = proposals.apply(card["proposal"])
		project = frappe.db.get_value("Project", {"project_name": "Mansour Garden Room"}, ["name", "one_payment_terms", "one_terms", "one_retention"], as_dict=True)
		assert project and (project.one_payment_terms, project.one_terms, flt(project.one_retention)) == ("Net 30", "Construction Works", 5), (name, project)
		bare = frappe.get_doc({"doctype": "Project", "project_name": "Mansour Gate", "customer": "Mansour & Sons", "project_template": TEMPLATE, "one_kind": "Fixed Price"}).insert()
		assert (bare.one_payment_terms, bare.one_terms, flt(bare.one_retention)) == ("Net 30", "Construction Works", 5), bare.as_dict()


@check
def oneproject_its_overview_keeps_its_rules_and_tells_its_people():
	"""A project's milestones bill at most its whole contract, however they're
	added, and OneAI's card adds one only when approved. A cancelled project
	takes no new work. Putting a project on hold or moving its end tells its
	people, and OneAI's status card closes open work only when asked. What's
	overdue on the Overview is what Needs You chases, and the villa prints its
	sub-projects and its contract."""
	from unittest.mock import patch

	from onedesk.one_ai import proposals
	from onedesk.one_project import agent, tree, view
	from onedesk.one_studio.print_blocks import progress

	told = []
	with as_user("samir@one.test"), patch("onedesk.one.notify.notify", side_effect=lambda name, *args, **kwargs: told.append(name)):
		assert agent.add_milestone(VILLA, "Glass signed off", str(add_days(today(), 20)), bill_share=5).get("error"), "the villa's milestones bill all of it already"
		card = agent.add_milestone(VILLA, "Glass signed off", str(add_days(today(), 20)))
		assert card.get("state") == "Proposed" and not frappe.db.exists("Task", {"project": VILLA, "subject": "Glass signed off"})
		proposals.apply(card["proposal"])
		assert frappe.db.get_value("Task", {"project": VILLA, "subject": "Glass signed off"}, "is_milestone") == 1
		try:
			frappe.get_doc({"doctype": "Task", "project": VILLA, "subject": "Over the contract", "is_milestone": 1, "one_bill_share": 5}).insert()
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("the milestones bill more than the contract")
		assert agent.set_status(VILLA, "Completed").get("mend") == "set_status", "open work is closed only when asked"
		card = agent.set_status(ACME, "On hold")
		assert frappe.db.get_value("Project", ACME, "status") == "Open"
		proposals.apply(card["proposal"])
		assert frappe.db.get_value("Project", ACME, "status") == "On hold" and "Project Stopped" in told, told
		doc = frappe.get_doc("Project", VILLA)
		doc.expected_end_date = add_days(doc.expected_end_date, 7)
		doc.save()
		assert "Project End Moved" in told, told
	frappe.db.set_value("Project", SHOWROOM, "status", "Cancelled")
	try:
		frappe.get_doc({"doctype": "Task", "project": SHOWROOM, "subject": "More work"}).insert(ignore_permissions=True)
	except frappe.ValidationError:
		pass
	else:
		raise AssertionError("work was added to a cancelled project")
	with as_user(OWNER):
		scope = sorted(tree.scope(VILLA))
		chased = sum(one["money"] for one in view._overdue_invoices(scope, OWNER) if one["text"].startswith("Chase"))
		assert _close(view._overdue(scope), chased), (view._overdue(scope), chased)
		printed = progress(frappe.get_doc("Project", VILLA))
		assert "Staircase balustrade" in {one[0] for one in printed["projects"]} and printed["contract"], printed


@check
def oneproject_its_tasks_time_and_money_keep_their_rules():
	"""Time on a project billed by the hour is billable however it's written,
	desk's form asks before ticking it, and a row's task is on its project.
	Hours, shares and budgets are never below 0. OneAI's time and budget
	cards change nothing until approved. Passing the villa's planned hours
	tells its manager. A time and materials invoice prints the hours it bills,
	the villa's subcontract costs as a subcontract, and no task still to do
	has time on it."""
	from unittest.mock import patch

	from onedesk.one_ai import proposals
	from onedesk.one_project import agent, hours

	rania = frappe.db.get_value("Employee", {"user_id": "rania@one.test"})
	with as_user("samir@one.test"):
		assert hours.billed_hourly(SHOWROOM) and not hours.billed_hourly(VILLA)
	sheet = frappe.get_doc(
		{
			"doctype": "Timesheet",
			"employee": rania,
			"company": COMPANY,
			"time_logs": [{"activity_type": "Design", "from_time": now_datetime(), "hours": 2, "project": SHOWROOM}],
		}
	).insert(ignore_permissions=True)
	assert sheet.time_logs[0].is_billable == 1, "time on a project billed by the hour is billable"
	elsewhere = frappe.db.get_value("Task", {"project": SHOWROOM, "is_group": 0})
	sheet.append("time_logs", {"activity_type": "Installation", "from_time": add_days(now_datetime(), 1), "hours": 1, "project": VILLA, "task": elsewhere})
	try:
		sheet.save(ignore_permissions=True)
	except frappe.ValidationError:
		pass
	else:
		raise AssertionError("a row's task was on another project")
	for doctype, name, field in (("Project", VILLA, "one_time_budget"), ("Project", VILLA, "one_hours_planned"), ("Task", elsewhere, "expected_time"), ("Task", elsewhere, "one_bill_share")):
		doc = frappe.get_doc(doctype, name)
		doc.set(field, -1)
		try:
			doc.save(ignore_permissions=True)
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError(f"{doctype} {field} took -1")
	with as_user("samir@one.test"):
		card = agent.log_time(SHOWROOM, 3, "Design", task=elsewhere)
		assert card.get("state") == "Proposed" and agent.log_time(SHOWROOM, 0, "Design").get("mend") == "log_time"
		before = frappe.db.count("Timesheet Detail", {"project": SHOWROOM})
		proposals.apply(card["proposal"])
		assert frappe.db.count("Timesheet Detail", {"project": SHOWROOM}) == before + 1
		card = agent.set_cost_budget(ACME, "Subcontract Costs", 12000)
		assert card.get("state") == "Proposed" and not frappe.db.exists("Budget", {"project": ACME, "docstatus": 1})
		proposals.apply(card["proposal"])
		assert frappe.db.exists("Budget", {"project": ACME, "docstatus": 1})
	told = []
	planned = sum(frappe.get_all("Timesheet Detail", filters={"project": VILLA, "docstatus": 1}, pluck="hours"))
	frappe.db.set_value("Project", VILLA, "one_hours_planned", planned + 1)
	frappe.db.set_value("Task", {"project": VILLA}, "expected_time", 0)
	over = frappe.get_doc(
		{
			"doctype": "Timesheet",
			"employee": rania,
			"company": COMPANY,
			"time_logs": [{"activity_type": "Project Management", "from_time": add_days(now_datetime(), 2), "hours": 2, "project": VILLA}],
		}
	).insert(ignore_permissions=True)
	with patch("onedesk.one.notify.notify", side_effect=lambda name, *args, **kwargs: told.append(name)):
		over.submit()
	assert "Hours Over Plan" in told, told
	invoice = frappe.db.get_value("Sales Invoice Timesheet", {"parenttype": "Sales Invoice"}, "parent")
	printed = frappe.get_print("Sales Invoice", invoice, print_format="One Sales Invoice")
	assert "Time Billed" in printed or "Time Spent" in printed, "the invoice prints the hours it bills"
	subcontract = frappe.db.get_value("Purchase Invoice Item", {"item_code": "SVC-SUB", "docstatus": 1, "project": VILLA}, "expense_account")
	assert subcontract and frappe.db.get_value("Account", subcontract, "account_name") == "Subcontract Costs", subcontract
	early = frappe.db.sql(
		"""select log.task from `tabTimesheet Detail` log join `tabTask` task on task.name = log.task
		where log.docstatus = 1 and task.project = %s and task.status = 'Open'""",
		VILLA,
	)
	assert not early, early


@check
def oneproject_a_manager_sees_every_project_and_a_member_sees_their_own():
	"""See Every Project is a OneProject Manager's, which whoever holds
	Projects Manager is given: Samir opens a project whatever its members, and
	Rania, not on it, doesn't see it until she's added."""
	from onedesk.one_project import members

	assert members.manages("samir@one.test") and not members.manages("rania@one.test")
	closed = next(
		name
		for name in frappe.get_all("Project", filters={"project_type": ["!=", "Employee Boarding"]}, pluck="name")
		if frappe.db.exists("Project User", {"parent": name})
		and not frappe.db.exists("Project User", {"parent": name, "user": "rania@one.test"})
		and "rania@one.test" not in frappe.db.get_value("Project", name, ["one_manager", "owner"])
		and not frappe.db.get_value("Project", name, "one_parent")
	)
	with as_user("samir@one.test"):
		assert frappe.has_permission("Project", "read", closed), "a OneProject Manager sees every project"
	with as_user("rania@one.test"):
		assert not frappe.has_permission("Project", "read", closed), f"Rania sees {closed}, which she isn't on"
	members.join(closed, "rania@one.test")
	members.forget()
	with as_user("rania@one.test"):
		assert frappe.has_permission("Project", "read", closed), "a member sees their project"


@check
def oneproject_tasks_are_listed_under_their_milestones():
	"""A project's Tasks tab, sorted by Milestone, lists each milestone and
	then the steps under it, and says which is which."""
	from onedesk.one_project import milestones

	with as_user("samir@one.test"):
		rows = milestones.project_tasks(VILLA, sort_by="lft", sort_order="asc", page_length=100)
	heads = [i for i, row in enumerate(rows) if row["is_group"]]
	assert heads, rows[:3]
	for i in heads:
		after = rows[i + 1] if i + 1 < len(rows) else None
		assert after is None or after["is_group"] or after["parent_task"] == rows[i]["name"], (rows[i], after)


@check
def oneproject_riyadh_runs_its_own_job():
	"""Sahara Glass Saudi's job is its own: its money is in riyals, its tasks
	are the company's, Samir sees it, and Rania, limited to the Dubai company,
	does not."""
	from onedesk.one_project import money

	job = frappe.db.get_value("Project", {"company": "Sahara Glass Saudi"}, "name")
	assert job, "the Riyadh company has a project"
	with as_user("samir@one.test"):
		assert frappe.has_permission("Project", "read", job)
		assert money.money(job)["currency"] == "SAR"
	assert set(frappe.get_all("Task", {"project": job}, pluck="company")) == {"Sahara Glass Saudi"}
	with as_user("rania@one.test"):
		assert not frappe.has_permission("Project", "read", job)
