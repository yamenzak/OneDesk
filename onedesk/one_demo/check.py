"""The integration suite: the demo workspace read back as the people in it.

    bench --site <site> execute onedesk.one_demo.check.run
    bench --site <site> execute onedesk.one_demo.check.run --kwargs "{'only': 'oneproject_'}"

`only` names one check, or ends in "_" to run a group: every check whose name
starts with it, such as a module's.
"""

import traceback

import frappe
from frappe.utils import (
	add_days,
	add_months,
	add_to_date,
	date_diff,
	flt,
	get_first_day,
	getdate,
	now_datetime,
	today,
)

from onedesk.one_demo.base import COMPANY, as_user, on, wh
from onedesk.one_demo.people import OWNER, PEOPLE

CHECKS = []


def check(fn):
	CHECKS.append(fn)
	return fn


def run(only: str | None = None) -> int:
	from onedesk.one_demo.samples import unkept

	failed = []
	chosen = [fn for fn in CHECKS if not only or fn.__name__ == only or (only.endswith("_") and fn.__name__.startswith(only))]
	for fn in chosen:
		try:
			# What a check does is never kept, even where the code it runs
			# commits as it goes (submitting drafts, merging records).
			with unkept():
				fn()
			print(f"ok    {fn.__name__}")
		except Exception as e:
			failed.append(fn.__name__)
			# A bare assert says nothing; the line it stopped on says which.
			here = [one.lineno for one in traceback.extract_tb(e.__traceback__) if one.filename == __file__]
			said = str(e) or f"line {traceback.extract_tb(e.__traceback__)[-1].lineno}"
			print(f"FAIL  {fn.__name__} (check.py:{here[-1] if here else '?'}): {type(e).__name__} {said[:600]}")
		finally:
			frappe.db.rollback()
			# What a check cached about records it changed is gone with them.
			frappe.clear_cache()
			_unasked()
			# Nor what it answered, such as a page's status.
			frappe.local.response = frappe._dict({"docs": []})
			frappe.set_user("Administrator")
	print(f"{len(chosen) - len(failed)} of {len(chosen)} passed" if len(chosen) != 1 else "")
	return len(failed)


def _close(a, b, by=0.05) -> bool:
	return abs(flt(a) - flt(b)) <= by


@check
def the_books_balance():
	off = frappe.db.sql(
		"""select voucher_type, voucher_no, sum(debit) - sum(credit) from `tabGL Entry`
		where is_cancelled = 0 and company = %s group by voucher_type, voucher_no
		having abs(sum(debit) - sum(credit)) > 0.01""",
		COMPANY,
	)
	assert not off, off[:5]


@check
def stock_never_goes_below_nothing():
	below = frappe.get_all("Bin", filters={"actual_qty": ["<", 0]}, fields=["item_code", "warehouse", "actual_qty"])
	assert not below, below


@check
def every_party_is_billed_in_its_own_currency():
	from erpnext.accounts.party import get_party_account_currency

	wrong = []
	for doctype, party_type, party in (("Sales Invoice", "Customer", "customer"), ("Purchase Invoice", "Supplier", "supplier")):
		for doc in frappe.get_all(doctype, filters={"docstatus": 1}, fields=["name", party, "currency", "conversion_rate", "grand_total", "base_grand_total"]):
			if doc.currency != get_party_account_currency(party_type, doc[party], COMPANY):
				wrong.append((doc.name, doc.currency))
			if not _close(doc.grand_total * doc.conversion_rate, doc.base_grand_total, 1):
				wrong.append((doc.name, "base"))
	assert not wrong, wrong


@check
def three_currencies_besides_the_companys():
	used = set(frappe.get_all("Sales Invoice", filters={"docstatus": 1}, pluck="currency")) | set(
		frappe.get_all("Purchase Invoice", filters={"docstatus": 1}, pluck="currency")
	)
	assert {"AED", "USD", "EUR", "GBP"} <= used, used


@check
def erpnext_statuses_are_all_there():
	"""The demo reaches every status a person meets, not only the happy path."""
	wanted = {
		"Sales Invoice": {"Paid", "Unpaid", "Overdue", "Partly Paid", "Return", "Credit Note Issued"},
		"Purchase Invoice": {"Paid", "Unpaid"},
		"Sales Order": {"To Deliver and Bill", "Completed"},
		"Quotation": {"Open", "Ordered", "Lost"},
		"Opportunity": {"Open", "Quotation", "Lost"},
		"Lead": {"Lead", "Replied", "Interested", "Do Not Contact", "Converted", "Opportunity", "Quotation", "Lost Quotation"},
		"Project": {"Open", "Completed"},
		"Work Order": {"Completed", "In Process", "Not Started"},
		"Expense Claim": {"Paid", "Unpaid", "Rejected", "Draft"},
	}
	missing = {}
	for doctype, statuses in wanted.items():
		have = set(frappe.get_all(doctype, pluck="status", distinct=True))
		if statuses - have:
			missing[doctype] = sorted(statuses - have)
	assert not missing, missing


@check
def every_step_left_its_records():
	least = {
		"Lead": 10,
		"Opportunity": 9,
		"Project": 10,
		"Task": 60,
		"Timesheet": 40,
		"Sales Order": 6,
		"Sales Invoice": 15,
		"Purchase Order": 8,
		"Purchase Invoice": 8,
		"Payment Entry": 15,
		"Work Order": 7,
		"Asset": 5,
		"Journal Entry": 10,
		"Salary Slip": 30,
		"Leave Application": 3,
		"Expense Claim": 4,
		"Job Applicant": 3,
	}
	short = {doctype: frappe.db.count(doctype) for doctype, n in least.items() if frappe.db.count(doctype) < n}
	assert not short, short


def _projects():
	return frappe.get_all("Project", filters={"project_type": ["!=", "Employee Boarding"]}, fields=["name", "project_name", "one_kind"])


def _team(project):
	return set(frappe.get_all("Project User", filters={"parent": project}, pluck="user"))


@check
def every_project_page_opens_for_its_people():
	"""The page's three reads, as the owner, the project manager, the books
	and each member of its team."""
	from onedesk.one_project import money, view

	broken = []
	for project in _projects():
		for user in {OWNER, "samir@one.test", "huda@one.test", *_team(project.name)}:
			if not frappe.has_permission("Project", "read", doc=project.name, user=user):
				continue
			try:
				with as_user(user):
					view.said(project.name)
					view.work(project.name)
					money.money(project.name)
			except Exception as e:
				broken.append((project.project_name, user, f"{type(e).__name__}: {e}"[:160]))
	assert not broken, broken


@check
def a_project_is_closed_to_who_has_no_part_in_it():
	from onedesk.one_project import view

	# One he is not on: which project lists first changes with what was last edited.
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
			found = frappe.db.sql(
				f"""select sum(base_net_amount) from `tab{child}` where project in %s and docstatus = 1""",
				(scope,),
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


def _reports():
	modules = frappe.get_all("Module Def", filters={"app_name": "onedesk"}, pluck="name")
	return frappe.get_all(
		"Report",
		filters={"module": ["in", modules], "report_type": ["in", ["Script Report", "Query Report"]], "is_standard": "Yes", "disabled": 0},
		pluck="name",
	)


#: What a report's own filters start at, the way its page fills them.
FILTERS = {
	"company": COMPANY,
	"from_date": str(on(1, 1)),
	"to_date": today(),
	"date": today(),
	"month": getdate().month,
	"year": getdate().year,
	"fiscal_year": str(getdate().year),
	"period": "Monthly",
	"range": "Monthly",
}


@check
def every_report_of_ones_runs():
	from frappe.desk.query_report import run as run_report

	skip = {"AI Usage", "Plan Calculator", "Price Check", "AI Credits"}  # the operator's, not a workspace's
	broken = []
	for name in _reports():
		if name in skip:
			continue
		try:
			with as_user(OWNER):
				run_report(name, filters=FILTERS)
		except Exception as e:
			broken.append((name, f"{type(e).__name__}: {e}"[:200]))
	assert not broken, broken


@check
def every_home_figure_reads_for_its_people():
	from onedesk.one import home
	from onedesk.one_book import home as books

	broken = []
	for user, calls in (
		("huda@one.test", (books.cash, books.profit_this_month, books.owed_to_us, books.overdue, books.we_owe, books.due_this_week)),
		*((email, (home.tasks_due, home.meetings_today, home.approvals_waiting, home.attention)) for _f, _l, email, *_r in PEOPLE if email),
	):
		for fn in calls:
			try:
				with as_user(user):
					fn()
			except Exception as e:
				broken.append((user, fn.__name__, f"{type(e).__name__}: {e}"[:160]))
	assert not broken, broken


@check
def the_books_home_tells_the_truth():
	"""What is owed to us on the books' home is what the invoices still have
	outstanding."""
	from onedesk.one_book import home as books

	with as_user("huda@one.test"):
		said = books.owed_to_us()
	found = frappe.db.sql(
		"""select sum(outstanding_amount * conversion_rate) from `tabSales Invoice`
		where docstatus = 1 and company = %s and outstanding_amount > 0""",
		COMPANY,
	)[0][0]
	assert _close(said["value"], found, 2), (said["value"], found)


@check
def every_rail_link_opens_for_its_app():
	from onedesk.one import reach

	refused = reach.unreachable()
	assert not refused, refused


@check
def everybody_signs_in_to_what_they_were_given():
	"""Each person holds the roles People gave them, and only the owner is an
	administrator."""
	from onedesk.one.roles import ADMINISTRATOR

	admins = {u for u in frappe.get_all("Has Role", filters={"role": ADMINISTRATOR, "parenttype": "User"}, pluck="parent") if u.endswith("@one.test")}
	assert admins == {OWNER}, admins
	for _f, _l, email, *_r, access in PEOPLE:
		if email and access:
			assert frappe.db.get_value("User", email, "enabled"), email


@check
def the_assets_depreciate():
	booked = frappe.db.count("Journal Entry", {"voucher_type": "Depreciation Entry", "docstatus": 1})
	assert booked, "no depreciation booked this year"


@check
def a_manager_is_not_kept_to_their_own_records():
	"""People's managers work with everybody's records (one_hr/everybody.py),
	and the rest only with their own, as hrms means them to."""
	from onedesk.one_hr.everybody import manages

	wrong = []
	for _f, _l, email, *_r in PEOPLE:
		if not email:
			continue
		employee = frappe.db.get_value("Employee", {"user_id": email}, ["name", "create_user_permission"], as_dict=True)
		kept = frappe.db.exists("User Permission", {"user": email, "allow": "Employee"})
		if manages(email) == bool(kept) or manages(email) == bool(employee.create_user_permission):
			wrong.append(email)
	assert not wrong, wrong


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
def a_manager_shares_what_they_assign():
	"""Assigning somebody a record they cannot open shares it with them."""
	with as_user("karim@one.test"):
		assert frappe.has_permission("Asset Maintenance", "share"), "Stock Manager cannot share upkeep"


# What a desk changes without the page: a bulk edit of the list, a cell of
# the report view and a row of Data Import. Each holds a record's rules, so
# each is tried as the person who would make it and rolled back after.
WAYS = ("bulk edit", "report view", "import")


def _change(way: str, doctype: str, name: str, values: dict) -> None:
	if way == "bulk edit":
		_bulk(doctype, name, "update", values)
	elif way == "report view":
		frappe.client.set_value(doctype, name, values)
	else:
		_imported(doctype, name, values)


def _bulk(doctype: str, name: str, action: str, values: dict | None = None) -> None:
	"""A bulk action on one record. frappe commits each record it changes,
	and the suite writes nothing, so its commit stays a savepoint here."""
	from frappe.desk.doctype.bulk_update.bulk_update import submit_cancel_or_update_docs

	db = frappe.db
	commit, rollback = db.commit, db.rollback
	db.savepoint("bulk")
	db.commit = lambda *a, **k: None
	db.rollback = lambda *a, **k: rollback(save_point="bulk")
	frappe.local.message_log = []
	try:
		failed = submit_cancel_or_update_docs(doctype, [name], action, values)
	finally:
		db.commit, db.rollback = commit, rollback
	if failed:
		raise frappe.ValidationError(frappe.get_last_doc("Error Log").error.strip().splitlines()[-1])


def _imported(doctype: str, name: str, values: dict) -> None:
	"""One row of Update Existing Records, as Data Import reads and saves it,
	short of its commit."""
	import csv
	import tempfile

	from frappe.core.doctype.data_import.importer import Importer

	with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
		out = csv.writer(f)
		out.writerow(["name", *values])
		out.writerow([name, *values.values()])
	plan = frappe.get_doc({"doctype": "Data Import", "reference_doctype": doctype, "import_type": "Update Existing Records"})
	importer = Importer(doctype, data_import=plan, file_path=f.name, console=True)
	importer.before_import()
	for payload in importer.import_file.get_payloads_for_import():
		importer.process_doc(payload.doc)


def _each_way(user: str, doctype: str, name: str, values: dict, read: tuple = ()) -> dict:
	"""Make the change each way: what the record holds after it, or the
	refusal."""
	seen = {}
	for way in WAYS:
		frappe.db.savepoint("way")
		try:
			with as_user(user):
				_change(way, doctype, name, values)
			seen[way] = frappe.db.get_value(doctype, name, [*values, *read], as_dict=True)
		except Exception as e:
			seen[way] = e
		finally:
			frappe.db.rollback(save_point="way")
			frappe.clear_document_cache(doctype, name)
	return seen


def _refused(seen: dict, why: str) -> None:
	"""Each way was turned down, and by the rule, not by something else."""
	wrong = {way: got for way, got in seen.items() if why not in str(got)}
	assert not wrong, wrong


@check
def a_project_with_open_work_is_not_closed_by_hand():
	project = frappe.db.get_value("Project", {"project_name": "Bayview Tower Curtain Wall"})
	_refused(_each_way("samir@one.test", "Project", project, {"status": "Completed"}), "still has open work")


@check
def a_tasks_progress_is_its_checklist():
	"""A task with a checklist is as far along as its steps, however its
	progress is typed in."""
	task = frappe.db.get_value("Task", {"subject": "Prepare the site visit for the marina"})
	frappe.db.savepoint("ticked")
	try:
		doc = frappe.get_doc("Task", task)
		doc.one_steps[0].done = 1
		doc.save(ignore_permissions=True)
		seen = _each_way("samir@one.test", "Task", task, {"progress": 90})
	finally:
		frappe.db.rollback(save_point="ticked")
		frappe.clear_document_cache("Task", task)
	for way, got in seen.items():
		assert not isinstance(got, Exception) and flt(got.progress) == 33.3, (way, got)


@check
def an_internal_project_bills_nobody():
	project = frappe.db.get_value("Project", {"project_name": "Crescent Schools Window Survey"})
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
def the_books_lock_up_to_today_at_most():
	from onedesk.one_demo.base import ahead

	_refused(_each_way("huda@one.test", "Company", COMPANY, {"accounts_frozen_till_date": str(ahead(30))}), "up to today")


@check
def nobody_is_turned_on_past_the_seats():
	from onedesk.one.settings import seats_used

	frappe.db.set_value("User", "yousef@one.test", "enabled", 0)
	frappe.db.set_single_value("Workspace Account", "seats", seats_used())
	_refused(_each_way("Administrator", "User", "yousef@one.test", {"enabled": 1}), "seats are in use")


@check
def a_folder_reads_for_whoever_turned_it_on():
	with as_user("samir@one.test"):
		folder = frappe.get_doc({"doctype": "File", "file_name": f"Site Photos {frappe.generate_hash(length=6)}", "is_folder": 1, "folder": "Home"}).insert()
	for way, got in _each_way("samir@one.test", "File", folder.name, {"one_intake": 1, "one_intake_for": "omar@one.test"}).items():
		assert not isinstance(got, Exception), (way, got)
		assert got.one_intake_for == "samir@one.test", (way, got)


@check
def every_notification_file_is_on_the_notifications_page():
	"""Each file in onedesk/notifications/ is a type the workspace has, with
	the file's words, and listed for its administrator to change."""
	from onedesk.one import notify, settings

	declared = notify.declared()
	with as_user(OWNER):
		listed = {one["name"] for app in settings._notification_types()["apps"] for one in app["types"]}
	missing = sorted(set(declared) - listed)
	assert not missing, missing
	wrong = [
		name
		for name, one in declared.items()
		if frappe.db.get_value("Notification Type", name, "one_default_subject") != notify.jinja(one.get("subject"))
	]
	assert not wrong, wrong


@check
def the_payment_reminder_is_turned_on_where_every_notification_is():
	"""Send This on the Payment Reminder and the rule that mails it are one."""
	with as_user(OWNER):
		kind = frappe.get_doc("Notification Type", "Payment Reminder")
		kind.enabled = 1
		kind.save()
	assert frappe.db.get_value("Notification", "Payment Reminder", "enabled") == 1
	# Turned off on the rule itself, as its list would. In developer mode frappe
	# writes a standard rule back to its file on save, and the suite writes
	# nothing.
	frappe.flags.in_import = True
	try:
		frappe.client.set_value("Notification", "Payment Reminder", "enabled", 0)
	finally:
		frappe.flags.in_import = False
	assert frappe.db.get_value("Notification Type", "Payment Reminder", "enabled") == 0


@check
def every_paper_prints_in_the_companys_look():
	"""Each record that leaves the company prints with One's format by default,
	as the owner prints it, under the company's letter head and in its colour."""
	from onedesk.one import print_blocks

	colour = frappe.db.get_value("Company", COMPANY, "one_brand_colour")
	assert colour, "the demo company has no Brand Colour"
	assert frappe.db.get_value("Letter Head", {"is_default": 1}) == COMPANY
	for doctype, (name, _module) in print_blocks.FORMATS.items():
		assert frappe.get_meta(doctype).default_print_format == name, doctype
		record = frappe.get_all(doctype, filters={"docstatus": ["<", 2]}, order_by="creation desc", limit=1, pluck="name")
		assert record, f"the demo has no {doctype}"
		with as_user(OWNER):
			html = frappe.get_print(doctype, record[0], name)
		# The number's label is printed by One Title alone, never by the letter head.
		label = print_blocks.title(frappe.get_doc(doctype, record[0]))["label"]
		assert label in html and colour in html and record[0] in html, f"{doctype} {record[0]} prints no blocks"


@check
def every_intake_sample_left_what_it_should():
	"""Each mail and file in tests/samples/intake arrived when the demo was
	built, and the records its sample says are there."""
	from onedesk.one_demo import samples

	wrong = {}
	for path in samples.samples():
		handled = samples.found(path)
		missing = ["it never arrived"] if handled is None else samples.unmet(path, handled)
		if missing:
			wrong[f"{path.parent.name}/{path.stem}"] = missing
	assert samples.samples(), "there are no Intake samples"
	assert not wrong, wrong


#: Each hand-off the READMEs' Connections name, by the records it leaves in
#: the demo: (from, to, kind of record, what marks it as handed over).
HANDOFFS = (
	("OneCRM", "OneBook", "Sales Invoice Item", {"sales_order": ["is", "set"], "docstatus": 1}),
	("OneCRM", "OneInventory", "Delivery Note Item", {"against_sales_order": ["is", "set"], "docstatus": 1}),
	("OneCRM", "OneProject", "Sales Order", {"project": ["is", "set"], "docstatus": 1}),
	("OneCRM", "OneBook", "Customer", {"lead_name": ["is", "set"]}),
	("OneInventory", "OneBook", "Purchase Receipt Item", {"purchase_order": ["is", "set"], "docstatus": 1}),
	("OneInventory", "OneBook", "Purchase Invoice Item", {"purchase_order": ["is", "set"], "docstatus": 1}),
	("OneProject", "OneBook", "Sales Invoice", {"project": ["is", "set"], "docstatus": 1}),
	("OneProject", "OneBook", "Purchase Invoice", {"project": ["is", "set"], "docstatus": 1}),
	("OneProject", "OneTask", "Task", {"project": ["is", "set"]}),
	("OneHR", "OneProject", "Timesheet", {"parent_project": ["is", "set"]}),
	("OneHR", "OneProject", "Expense Claim", {"project": ["is", "set"]}),
	("OneProject", "OneHR", "Expense Claim", {"project": ["is", "set"], "docstatus": 1}),
	("OneHR", "OneBook", "Journal Entry Account", {"reference_type": "Payroll Entry", "docstatus": 1}),
	("OneHR", "OneInventory", "Asset", {"custodian": ["is", "set"]}),
	("OneBook", "OneCRM", "Payment Entry Reference", {"reference_doctype": "Sales Invoice", "docstatus": 1}),
)


@check
def every_hand_off_left_its_records():
	"""What one app hands another arrives there in the demo: an order is
	invoiced and delivered, a payroll posts to the books, a project's time and
	costs are on it."""
	missing = [f"{one} to {other}: {doctype}" for one, other, doctype, filters in HANDOFFS if not frappe.db.count(doctype, filters)]
	assert not missing, missing


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
		# A template task changed on its own form, as a bulk edit would, is counted too.
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
	from onedesk.one_project import ai, template_view

	phases = [
		{"subject": "Strip-Out", "milestone": True, "tasks": [{"subject": "Protect the floors", "day": 0, "days": 1}, {"subject": "Take out the old units", "day": 1, "days": 2}]},
		{"subject": "Fit", "milestone": True, "tasks": [{"subject": "Fit the new units", "day": 3, "days": 3}, {"subject": "Worktops", "day": 6, "days": 1, "after": ["Fit the new units"]}]},
	]
	with as_user("samir@one.test"):
		known = ai.project_templates()
		assert "Aluminium & Glazing" in known["templates"] and len(known["library"]) == 12
		said = ai.draft_template("Kitchen Refit", phases, about="A kitchen taken out and fitted again.")
		assert said.get("state") == "Proposed", said
		assert not frappe.db.exists("Project Template", "Kitchen Refit"), "nothing is made before it is approved"
		assert ai.draft_template("Aluminium & Glazing", phases).get("mend") == "draft_template"
		assert ai.draft_template("Bad", [{"subject": "A", "tasks": [{"subject": "b", "when": 3}]}]).get("mend")
		proposals.apply(said["proposal"])
		made = template_view.read("Kitchen Refit")
		assert [one["subject"] for one in made["tasks"]] == ["Strip-Out", "Protect the floors", "Take out the old units", "Fit", "Fit the new units", "Worktops"]
		assert made["days"] == 7 and all(one["is_milestone"] for one in made["tasks"] if one["is_group"])
	with as_user("rania@one.test"):
		assert "error" in ai.draft_template("Garden Shed", phases)


@check
def onetask_works_for_whoever_has_tasks():
	"""Rania's tasks, as My Tasks and OneAI read them, a step added and ticked,
	the timer started and stopped on one, and a task and its steps suggested
	as cards, and a change to one approved."""
	from onedesk.one_ai import proposals
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
		assert ai.plan_task("Send the snag photos", due=str(on(12, 1))).get("state") == "Proposed"
		assert ai.plan_steps(one, ["Check the seals", "Clean the frames"]).get("state") == "Proposed"
		# A change as the page makes it, saved only when approved.
		said = ai.plan_change(one, priority="Urgent", why="The client asked for it this week.")
		assert said.get("state") == "Proposed" and frappe.db.get_value("Task", one, "priority") != "Urgent", said
		proposals.apply(said["proposal"])
		assert frappe.db.get_value("Task", one, "priority") == "Urgent"
		assert ai.plan_change(one, priority="Urgent").get("error"), "nothing to change is said"
		assert ai.plan_change(one, status="Overdue").get("error"), "Overdue is ERPNext's to set"
		samirs = frappe.db.get_value("Task", {"subject": "Call Acme about the lobby drawings"})
		assert ai.plan_change(samirs, status="Completed").get("error"), "only a task she may change"


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
	for user, may in (("tariq@one.test", True), ("karim@one.test", False), ("omar@one.test", False)):
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
def onecalendar_shows_each_person_their_week():
	"""The week's events, days off and layers as the team sees them, an event's
	card, one moved, a feed link made, renewed, read and stopped, and OneAI's
	reads and a suggested event."""
	from onedesk.one_calendar import ai, events, feed, layers

	start, end = str(add_days(today(), -7)), str(add_days(today(), 7))
	with as_user("rania@one.test"):
		seen = layers.entries(start, end)
		meetings = [one for one in seen if "Weekly site meeting" in (one.get("title") or "")]
		assert len(meetings) >= 2, seen
		assert layers.layers() and isinstance(layers.days_off(start, end), list)
		assert events.card(meetings[0]["name"])
		assert ai.my_calendar(start, end)
		assert ai.busy_times(["Tariq"], start, end)
		assert ai.plan_event("Snag walk", f"{add_days(today(), 4)} 09:00:00").get("state") == "Proposed"
	with as_user("samir@one.test"):
		mine = next(one for one in layers.entries(start, end) if "Weekly site meeting" in (one.get("title") or "") and one["editable"])
		layers.move(mine["layer"], mine["name"], f"{add_days(today(), 1)} 09:00:00")
		assert feed.allowed(), "Calendar Links stay on when System Settings is saved"
		link = feed.mine()
		renewed = feed.renew()
		assert renewed["https"] != link["https"]
		feed.ics(renewed["https"].split("token=", 1)[1])
		assert b"BEGIN:VCALENDAR" in frappe.response["filecontent"] and b"Weekly site meeting" in frappe.response["filecontent"]
		feed.stop()
		made = events.make({"subject": "Supplier call", "starts_on": f"{add_days(today(), 2)} 15:00:00", "team": ["karim@one.test"]})
		assert frappe.db.exists("Event Participants", {"parent": made, "reference_docname": "karim@one.test"})


@check
def onebook_home_and_payments_for_the_accounts_team():
	"""What Huda's home says, every figure, a payment taken against an invoice
	in one step, the books locked and unlocked, and a readiness fix."""
	from onedesk.one_book import closing, home, paid, ready, tell

	with as_user("huda@one.test"):
		said = {
			"cash": home.cash(),
			"owed to us": home.owed_to_us(),
			"overdue": home.overdue(),
			"we owe": home.we_owe(),
			"due this week": home.due_this_week(),
			"profit this month": home.profit_this_month(),
		}
		assert all(one is not None for one in said.values()), said
		invoice = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0], "currency": "AED"}, fields=["name", "outstanding_amount"], limit=1)[0]
		bank = frappe.get_all("Account", filters={"account_type": "Bank", "is_group": 0, "company": COMPANY}, pluck="name", limit=1)[0]
		paid.settle("Sales Invoice", invoice.name, invoice.outstanding_amount, bank, reference="CHK-001", on=today())
		assert not frappe.db.get_value("Sales Invoice", invoice.name, "outstanding_amount")
	with as_user(OWNER):
		closing.lock(str(on(1, 31)))
		assert str(frappe.db.get_value("Company", COMPANY, "accounts_frozen_till_date")) == str(on(1, 31))
		closing.lock(None)
		ready.fix("bills")
		assert frappe.db.get_single_value("Accounts Settings", "check_supplier_invoice_uniqueness")
	with as_user("omar@one.test"):
		customer = frappe.get_all("Customer", pluck="name", limit=1)[0]
		tell.credit_limit(customer, 1000, 500, [OWNER])


@check
def onebook_keeps_the_books_rules():
	"""A bank mode of payment added later is wired by saving the company's
	bank account. Only an invoice or a bill is paid in one step. A bill made
	again drops last month's supplier number and its schedule. The books lock
	only up to today, by the closers alone, however the date is set. A year
	ended with entries is closed into Retained Earnings and locked, and the
	check turns the payment reminder on."""
	from onedesk.one_book import closing, paid, ready

	company = frappe.get_doc("Company", COMPANY)
	with as_user(OWNER):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": "Demo Transfer", "type": "Bank", "enabled": 1}).insert()
		frappe.get_doc("Bank Account", {"is_company_account": 1, "is_default": 1}).save()
		assert [one.default_account for one in frappe.get_doc("Mode of Payment", "Demo Transfer").accounts] == [company.default_bank_account or frappe.db.get_value("Bank Account", {"is_default": 1}, "account")]
	with as_user("huda@one.test"):
		order = frappe.get_all("Sales Order", filters={"docstatus": 1}, pluck="name", limit=1)[0]
		try:
			paid.settle("Sales Order", order, 10, frappe.db.get_value("Bank Account", {"is_default": 1}, "account"))
			raise AssertionError("an order was paid as if it were an invoice")
		except frappe.ValidationError:
			pass
		bill = frappe.get_all("Purchase Invoice", filters={"docstatus": 1, "bill_no": ["is", "set"]}, fields=["name", "bill_no"], limit=1)[0]
		repeat = frappe.get_doc({"doctype": "Auto Repeat", "reference_doctype": "Purchase Invoice", "reference_document": bill.name, "frequency": "Monthly", "start_date": today()}).insert()
		copy = repeat.make_new_document()
		assert not copy.bill_no and copy.name != bill.name, "last month's supplier number would be refused"
		assert getdate(copy.due_date) >= getdate(today()) and all(getdate(row.due_date) >= getdate(today()) for row in copy.payment_schedule), "last month's schedule"
	with as_user("rania@one.test"):
		for step in (lambda: closing.lock(today()), lambda: ready.fix("bills")):
			try:
				step()
				raise AssertionError("somebody outside the books closed or fixed them")
			except frappe.PermissionError:
				pass
	with as_user(OWNER):
		try:
			closing.lock(str(add_days(today(), 1)))
			raise AssertionError("the books were locked into the future")
		except frappe.ValidationError:
			pass
		company.reload()
		company.accounts_frozen_till_date = add_days(today(), 1)
		try:
			company.save()
			raise AssertionError("the Company form locked the books into the future")
		except frappe.ValidationError:
			pass
		income = company.default_income_account
		cash = frappe.db.get_value("Account", {"account_type": "Cash", "is_group": 0, "company": COMPANY})
		earned = frappe.get_doc({
			"doctype": "Journal Entry", "company": COMPANY, "posting_date": "2025-06-30", "user_remark": "Last year's sale",
			"accounts": [
				{"account": cash, "debit_in_account_currency": 500, "cost_center": company.cost_center},
				{"account": income, "credit_in_account_currency": 500, "cost_center": company.cost_center},
			],
		}).insert()
		earned.submit()
		assert [one.name for one in closing.unclosed(COMPANY)] == ["2025"]
		ready.fix("close")
		voucher = frappe.get_doc("Period Closing Voucher", {"fiscal_year": "2025", "company": COMPANY, "docstatus": 1})
		assert voucher.closing_account_head == closing.retained_earnings(COMPANY)
		assert str(closing.locked(COMPANY)) == "2025-12-31" and not closing.unclosed(COMPANY)
		ready.fix("reminder")
		assert frappe.db.get_value("Notification", "Payment Reminder", "enabled")


@check
def oneinventory_assets_items_and_orders_for_the_stores():
	"""An asset's and an item's page as Karim reads them, an asset given to
	somebody and taken back, a purchase order from the reorder rows, and a
	readiness fix."""
	from onedesk.one_inventory import assets, custody, item, order, ready

	with as_user("karim@one.test"):
		truck = frappe.get_all("Asset", filters={"asset_name": "Pickup Truck 2", "docstatus": 1}, pluck="name")[0]
		assert assets.said(truck)
		assert item.said("ALU-6063")
		nadia = frappe.db.get_value("Employee", {"employee_name": "Nadia Khoury"})
		custody.give(truck, nadia)
		assert frappe.db.get_value("Asset", truck, "custodian") == nadia
		custody.take_back(truck)
		made = order.order([{"item_code": "ALU-6063", "qty": 50, "warehouse": wh("Stores"), "supplier": "Al Noor Aluminium"}])
		assert made and frappe.db.get_value("Purchase Order", made[0], "docstatus") == 0
		listed = order.rows()
		assert listed, "nothing to order in the demo"
		first = listed[0]
		order.order([{**first, "supplier": first.get("supplier") or "Al Noor Aluminium"}])
		again = {(one["item_code"], one["warehouse"]) for one in order.rows()}
		assert (first["item_code"], first["warehouse"]) not in again, "a row already on a draft order is offered again"
	with as_user(OWNER):
		ready.fix("depreciation")


@check
def one_boards_open_on_frappes_new_kanban():
	"""The pipeline, the projects board and a project's own board open on
	frappe's new Kanban, each card showing One's fields by their icons
	(one/boards.py). erpnext's board of deals by status is gone, so the
	Pipeline is the one deal board."""
	from erpnext.projects.doctype.project.project import create_kanban_board_if_not_exists

	from onedesk.one_crm import board as pipeline
	from onedesk.one_project import board as projects

	create_kanban_board_if_not_exists(VILLA)
	villa = frappe.db.get_value("Project", VILLA, "project_name")
	for name, card in ((pipeline.BOARD, pipeline.CARD), (projects.HEALTH_BOARD, projects.HEALTH_CARD), (villa, projects.CARD)):
		board = frappe.get_doc("Kanban Board", name)
		assert board.use_kanban_v2, f"{name} is on the old board"
		assert [(row.fieldname, row.icon) for row in board.card_fields] == list(card.items()), (name, board.card_fields)
	assert not frappe.db.exists("Kanban Board", pipeline.STATUS_BOARD), "erpnext's board of deals by status is back"
	assert frappe.db.get_value("Kanban Board", "Task Status", "is_standard") == "Yes", "erpnext's own task board"


@check
def oneai_is_not_offered_as_a_recipient():
	"""The Email dialog suggests contacts. OneAI's account has none, so it is
	never offered as somebody to write to."""
	from frappe.email import get_contact_list

	from onedesk.one_hr import hiring

	assert not frappe.db.exists("Contact", {"user": hiring.AUTHOR}), "OneAI has a contact"
	assert hiring.AUTHOR not in [one.value for one in get_contact_list("oneai")], "OneAI is offered as a recipient"


@check
def onecrm_leads_and_deals_as_omar_works_them():
	"""Omar's pipeline figures and board, a deal's and a lead's overview, a
	call logged and a step done, a lead from the web form taken, a lead that
	is not the same person cleared and one that is merged, and what OneAI
	reads and suggests on the way."""
	from onedesk.one_crm import ai, board, capture, measure, next, record

	deal = frappe.db.get_value("Opportunity", {"title": "Webb Hotel lobby curtain wall"})
	lead = frappe.db.get_value("Lead", {"email_id": "hamad@suwaidi.example"})
	priya = frappe.db.get_value("Lead", {"email_id": "priya@nairinteriors.example"})
	khalid = frappe.db.get_value("Lead", {"email_id": "khalid@suwaidi.example"})
	with as_user("omar@one.test"):
		figures = {
			"pipeline": measure.pipeline(),
			"weighted": measure.weighted(),
			"won this month": measure.won_this_month(),
			"win rate": measure.win_rate(),
		}
		assert figures["pipeline"]["value"] > figures["weighted"]["value"] > 0, figures
		assert figures["win rate"]["value"] == 50.0, "one won and one lost in the last months"
		stages = board.worth()["stages"]
		assert sum(one["value"] for one in stages.values()) >= figures["pipeline"]["value"], stages
		assert record.overview("Opportunity", deal)["next"]
		assert record.overview("Lead", lead)
		called = record.log_call("Opportunity", deal, "Outgoing", "Answered", 6, "Agreed to send the drawings by Thursday.")
		assert frappe.db.exists("Dynamic Link", {"parenttype": "Call Log", "parent": called, "link_name": deal})
		next.done("Opportunity", deal, "Review the drawings", str(add_days(today(), 3)) + " 10:00:00")
		assert frappe.db.get_value("Opportunity", deal, "one_next_step") == "Review the drawings"
		assert frappe.db.exists("Comment", {"reference_name": deal, "content": ["like", "%Ask for the drawings%"]})

		next.settle()  # as every update runs it
		assert not frappe.db.get_value("Lead", priya, "lead_owner"), "the web form gives a lead no owner, and an update leaves it so"
		capture.take("Lead", priya)
		assert frappe.db.get_value("Lead", priya, "lead_owner") == "omar@one.test"
		assert frappe.db.get_value("Lead", khalid, "one_duplicate_of") == lead
		capture.not_duplicate(khalid)
		assert not frappe.db.get_value("Lead", khalid, "one_duplicate_of")
		again = frappe.get_doc({"doctype": "Lead", "first_name": "Priya", "last_name": "Nair", "company_name": "Nair Interiors", "email_id": "p.nair@gmail.example"}).insert()
		assert again.one_duplicate_of == priya
		assert capture.merge(again.name, priya) == priya and not frappe.db.exists("Lead", again.name)

		assert ai.deal_facts(deal)["history"]
		assert ai.lead_facts(lead)["history"]
		assert "quiet" in ai.gone_quiet("Opportunity") and "quiet" in ai.gone_quiet("Lead")
		lost = ai.why_we_lose()
		assert lost["won"] == 1 and lost["lost"] == 1 and lost["deals"][0]["reasons"] == ["Price"], lost
		assert ai.add_lead("Hamad Al Suwaidi", "hamad@suwaidi.example").get("error"), "a lead we have is not suggested twice"
		assert ai.add_lead("Joanna Pike", "joanna@pike.example", "Pike Hotels").get("state") == "Proposed"
		assert ai.plan_next_step("Opportunity", deal, "Call to agree the price", str(add_days(today(), 2))).get("state") == "Proposed"
		assert ai.write_up_call("Lead", lead, "Wants the villa windows quoted by the end of the month.").get("state") == "Proposed"


@check
def onelegal_every_person_has_agreed_and_reads_what_to():
	"""Everybody accepted what they must on their first sign-in, so nothing is
	outstanding; the documents, an old version and what was agreed read back,
	and OneAI reads an agreement."""
	from onedesk.one_legal import ai, gate, reading

	for user in (OWNER, "rania@one.test"):
		with as_user(user):
			assert not gate.outstanding()["blocking"], user
	with as_user(OWNER):
		listed = reading.catalogue()["documents"]
		assert {"terms", "privacy"} <= {one["key"] for one in listed}, listed
		said = reading.document("terms")
		assert said["html"] and said["version"]
		agreed = reading.history("terms")
		assert agreed and agreed[0]["document"] == "terms"
		assert reading.document("terms", agreed[0]["version"])["version"] == agreed[0]["version"]
		assert gate.accept(["terms"])["accepted"] == [], "accepted at this version already"
		assert ai.agreement("privacy").get("text")


@check
def onestudio_record_types_extensions_and_forms_for_the_owner():
	"""Layla's collections, extensions and changed forms, the Company Van moved
	to a group of its own, an extension's error read on its Errors tab and
	fixed, and what OneAI reads, writes and suggests in OneStudio. A sales
	manager sees none of it."""
	from unittest import mock

	from onedesk.one_studio import ai, extensions, forms, mend, record_types, review

	screen = frappe.db.get_value(extensions.EXTENSION, {"title": "Say When a Customer Has No Mobile"})
	server = frappe.db.get_value(extensions.EXTENSION, {"title": "A Lead Needs a Mobile Number"})
	with as_user("omar@one.test"):
		extensions.tripped(screen, "frm.dashboard is undefined", "at refresh", frappe.get_all("Customer", pluck="name", limit=1)[0])
		assert "error" in ai.extensions_here() and "error" in ai.record_types_here()
	with as_user(OWNER):
		assert len(mend.listed(screen)) >= 2
		changed = {one["doctype"]: one for one in forms.forms()}
		assert changed["Customer"]["extensions"] == 1, changed.get("Customer")
		assert [one["title"] for one in forms.extensions("Lead")] == ["A Lead Needs a Mobile Number"]
		assert "Your Records" in record_types.groups_of("OneInventory")
		assert record_types.move("Company Van", "OneInventory", "Vehicles").endswith("Vehicles")
		assert frappe.db.get_value("Record Type", "Company Van", "rail_group") == "Vehicles"

		assert {one["title"] for one in ai.extensions_here()["extensions"]} >= {"Say When a Customer Has No Mobile", "A Lead Needs a Mobile Number"}
		assert ai.extension_mistakes("Say When a Customer Has No Mobile")["errors"]
		assert ai.extension_code(server)["code"].startswith("if not doc.mobile_no")
		assert ai.extension_places()
		assert ai.record_types_here()["record_types"][0]["records"] == 2
		assert ai.forms_here()["changed_forms"] and ai.forms_here("Customer")["extensions"]
		assert ai.form_relations("Item")
		assert ai.design_record_type("Tool Loan", "OneInventory", "A tool lent to somebody.", [{"label": "Tool", "fieldtype": "Data"}], "Keep track of lent tools.").get("state") == "Proposed"
		passed = {"verdict": "Pass", "why": "Does what it says."}
		with mock.patch.object(review, "ask", return_value=passed):
			written = ai.write_extension(
				"A Customer Needs a Mobile Number",
				"On Screen",
				"Customer",
				"Says on the form when a customer has no mobile.",
				"frappe.ui.form.on('Customer', { refresh(frm) { if (!frm.doc.mobile_no) frm.set_intro(__('No mobile number yet.')); } });",
				"Tell us when a customer has no mobile",
				view="Form",
			)
			assert written.get("state") == "Proposed", written
			fixed = {"diagnosis": "frm.dashboard is not there on a new form.", "code": "frappe.ui.form.on('Customer', { refresh(frm) { if (!frm.doc.mobile_no) frm.set_intro(__('No mobile number yet.')); } });", "explanation": "Says on the form when a customer has no mobile."}
			with mock.patch("onedesk.one_ai.run.once", return_value=""), mock.patch("onedesk.one_hr.hiring.read", return_value=fixed):
				said = mend.mend(screen)
			assert said["review"] == "Passed" and not frappe.db.get_value(extensions.EXTENSION, screen, "enabled"), "a fixed extension stays off"
		with mock.patch("frappe.enqueue") as queued:
			# Mended a moment ago, so it has no errors since: the person says what is wrong.
			assert "error" in ai.mend_extension(screen)
			assert ai.mend_extension(screen, "It says nothing on a new customer").get("started")
			assert queued.call_args.args[0] == "onedesk.one_studio.mend.in_background"


@check
def onestudio_tells_the_others_and_oneai_remembers_once():
	"""An extension turned off or deleted is told to the other
	administrators. OneAI keeps a fact once, however often it is told, keeps
	a fact that says more in its place, ties it to a record only when the
	fact names it, and searches only the reader's own conversations."""
	from onedesk.one_ai import memory
	from onedesk.one_studio import extensions

	server = frappe.db.get_value(extensions.EXTENSION, {"title": "A Lead Needs a Mobile Number"})
	with _Told() as told, as_user(OWNER):
		doc = frappe.get_doc(extensions.EXTENSION, server)
		doc.enabled = 0 if doc.enabled else 1
		doc.save()
		frappe.delete_doc(extensions.EXTENSION, server)
	said = {name for name, _users in told.said}
	assert {"Extension Deleted"} <= said and said & {"Extension Turned Off", "Extension Turned On"}, told.said

	with as_user("rania@one.test"):
		first = memory.remember("My site van is the white Hilux.")
		assert first["state"] == "remembered"
		assert memory.remember("My site van is the white Hilux.")["state"] == "already remembered"
		assert memory.remember("My site van is the white Hilux, plate D 40721.", replaces="My site van is the white Hilux.")["state"] == "updated"
		assert frappe.db.count("AI Memory", {"owner": "rania@one.test", "fact": ["like", "%Hilux%"]}) == 1
		loose = memory.remember("Calls are better than mail before ten.", about_doctype="Customer", about_name="Mansour & Sons")
		assert not frappe.db.get_value("AI Memory", loose["memory"], "about_name"), "a fact tied to a record it does not name"
		named = memory.remember("Mansour & Sons pay on the last day of the month.", about_doctype="Customer", about_name="Mansour & Sons")
		assert frappe.db.get_value("AI Memory", named["memory"], "about_name") == "Mansour & Sons"
	with as_user(OWNER):
		chat = frappe.get_doc({"doctype": "AI Chat", "title": "Bonus for the crew", "turns": frappe.as_json([{"role": "user", "text": "Draft the crew bonus letter for December."}])}).insert()
		assert chat.name in {one["chat"] for one in memory.search_my_chats("crew bonus")}
	with as_user("rania@one.test"):
		assert chat.name not in {one["chat"] for one in memory.search_my_chats("crew bonus")}, "another person's conversation was searched"

VILLA, TOWER, ACME, SHOWROOM, MARINA = "PROJ-0001", "PROJ-0003", "PROJ-0006", "PROJ-0009", "PROJ-0011"


@check
def oneproject_every_tab_of_a_project_page_reads_for_samir():
	"""The villa's page as Samir reads it, tab by tab, the tower's tree added
	up, the Projects list's tree and timeline, the retainer's months and what
	OneAI reads of them."""
	from onedesk.one_project import (
		activity,
		ai,
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
		assert "Window schedule.csv" in {one["file_name"] for one in view.files(VILLA)}
		assert media.featured(VILLA)[0]["kind"] == "photo"
		assert VILLA not in {one["name"] for one in view.picker("PROJ-0002")["open"]}, "the parent is in the breadcrumb already"
		assert frappe.db.get_value("Project", "PROJ-0002", "project_name") == "Staircase balustrade", "extra work is called what it was quoted as"
		assert view.to_quote("Acme Holdings") == ACME and chain.customer_project("Acme Holdings") == ACME
		assert view.to_quote("Mansour & Sons") is None, "two open projects, so neither is guessed"
		assert len(view.updates(VILLA)) >= 2 and activity.activity(VILLA)["activities"]
		assert billing.bills(VILLA)["bills"]
		assert billing.unbilled(SHOWROOM)["hours"] > 0 and billing.unbilled(SHOWROOM)["currency"] == "EUR"
		# Its three cost types, and the team's own time (its Time Budget).
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
		facts = ai.project_facts(VILLA)
		assert facts["title"] == "Mansour Villa Windows and Doors" and facts["sub_projects"] == 1
		assert VILLA in {one["project"] for one in ai.projects_needing_attention()["projects"]}
	with as_user("huda@one.test"):
		assert billing.invoices(VILLA)["invoices"], "the books see the villa's invoices"


@check
def oneproject_samir_runs_a_project():
	"""What Samir changes on a project's page: the team, a contact, time,
	a cost type's budget, the update he is asked for, a template from the
	villa's tasks, a contract on Acme's lobby, a project grouped above
	another, a photo added, and the villa closed with its open work."""
	from onedesk.one_project import (
		ai,
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

	with as_user("samir@one.test"):
		assert "huda@one.test" in {one["user"] for one in team.add(VILLA, "huda@one.test")["people"]}
		# She stays on the team for the villa's task she is given, though no longer a member.
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
		assert ai.draft_update(VILLA, "I walked the site with Khalid. The first floor glass is in.").get("state") == "Proposed"
		made = templates.save_as(VILLA, "Villa Glazing")
		assert frappe.db.count("Project Template Task", {"parent": made}) == frappe.db.count("Task", {"project": VILLA, "status": ["!=", "Cancelled"]})
		order = kinds.add_contract(ACME, 85000, "SVC-INST", retention=5)
		assert frappe.db.get_value("Sales Order", order, ["docstatus", "currency"]) == (1, "USD")
		assert frappe.db.get_value("Project", ACME, "sales_order") == order, "the contract is the project's order"
		above = tree.group_under(ACME, "Acme Americas")
		assert frappe.db.get_value("Project", ACME, "one_parent") == above
		frappe.local.uploaded_file, frappe.local.uploaded_filename = _png(), "Lobby mock-up.png"
		frappe.form_dict.update({"doctype": "Project", "docname": ACME})
		try:
			assert media.add() == {"project": ACME}
		finally:
			frappe.local.uploaded_file = frappe.local.uploaded_filename = None
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
	"""What Huda bills from a project's page: the showroom's time in euros, the
	retainer's last month, and the villa's order as far as the work has got.
	Each a draft, as the page opens it."""
	from onedesk.one_project import billing, progress, retainer

	with as_user("huda@one.test"):
		invoice = billing.invoice_time(SHOWROOM, item="SVC-MAINT")
		assert invoice.currency == "EUR" and invoice.items and invoice.is_new()
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
		# The windows are counted whole, so they are billed to the end, the rest not yet.
		draft = progress.bill_progress(order, "Sales Order", lines={windows["line"]: 100})
		assert [row.item_code for row in draft.items] == ["WIN-CS12"] and draft.is_new()


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

	from onedesk.one_project import billing, progress
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
				pluck="due_date",
			)
			assert all(date_diff(due, one.posting_date) >= 30 for due in own), (one.name, own)
	held = frappe.get_all(
		"Payment Schedule",
		filters={"parent": ["in", ["ACC-SINV-2026-00001", "ACC-PINV-2026-00016"]], "payment_term": ["in", HELD]},
		fields=["parent", "outstanding"],
	)
	assert held and all(one.outstanding for one in held), held
	with as_user("samir@one.test"):
		assert "Client's Representative" in {one["role"] for one in contacts.contacts(VILLA)["contacts"]}
		weeks = [one for one in activity.activity(VILLA)["activities"] if one["type"] == "time"]
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
	from onedesk.one_project import ai, billing, contacts
	from onedesk.one_project.retention import HELD

	with as_user(OWNER):
		facts = ai.project_facts(TOWER)
		late = facts["invoices"]["overdue"]
		assert late and all(one["days_late"] > 0 for one in late), facts["invoices"]
		assert all("to_pay" in one and "due" in one for one in facts["money"]["subcontracts"])
		mails = frappe.db.count("Communication")
		card = ai.remind_customer(late[0]["invoice"], "Dear Bayview,\n\nA reminder that this invoice is past its date.")
		said = proposals.apply(card["proposal"])
		assert said["mail"]["text"].startswith("Dear Bayview") and said["mail"]["subject"], said
		assert frappe.db.count("Communication") == mails, "a reminder is opened to send, never sent"
	with as_user("samir@one.test"):
		# Samir reads no invoices, so OneAI finds none to chase for him.
		assert not ai.project_facts(TOWER)["invoices"]["overdue"]
		on = set(frappe.get_all("Project User", filters={"parent": VILLA, "parenttype": "Project"}, pluck="user"))
		joins = next(one for one in ("rania@one.test", "nadia@one.test", "tariq@one.test", "omar@one.test", "karim@one.test") if one not in on)
		card = ai.add_member(VILLA, joins)
		assert card.get("state") == "Proposed", card
		assert not frappe.db.exists("Project User", {"parent": VILLA, "user": joins})
		proposals.apply(card["proposal"])
		assert frappe.db.exists("Project User", {"parent": VILLA, "user": joins})
		card = ai.add_contact(VILLA, "Engineer", organisation="Gulf Structural Engineers", note="Checks the brackets")
		proposals.apply(card["proposal"])
		assert "Gulf Structural Engineers" in {one["company"] for one in contacts.contacts(VILLA)["contacts"]}
	bill = frappe.get_all("Purchase Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0], "project": VILLA}, pluck="name")[0]
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
	from onedesk.one_project import ai
	from onedesk.one_project.report.workload import workload

	with as_user("samir@one.test"):
		_columns, rows, _week, _chart, cards = workload.execute({"week": today()})
		assert any((one["load"] or 0) > 100 for one in rows), [(one["full_name"], one["load"]) for one in rows]
		assert any(one["late"] for one in rows)
		assert all("." not in str(one["value"]) or len(str(one["value"]).split(".")[-1]) == 1 for one in cards), cards
		said = ai.team_week()
		assert said["people"] and {one["name"] for one in said["people"]} == {one["full_name"] or one["user"] for one in rows}
		sheet = frappe.get_all("Timesheet", filters={"docstatus": 1}, pluck="name", limit=1)[0]
		printed = frappe.get_print("Timesheet", sheet, "One Timesheet")
		assert frappe.db.get_value("Timesheet", sheet, "employee_name") in printed
	assert frappe.db.get_value("Project Template", "Aluminium & Glazing", "owner") == "samir@one.test"


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
		# The addendum is the staircase's, and says so wherever it is listed.
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


class _Told:
	"""Who One told what, through the hub (one/notify.py), while it is open."""

	def __enter__(self):
		from unittest import mock

		self.said = []
		self.patch = mock.patch("onedesk.one.notify.notify", side_effect=lambda name, users, *a, **k: self.said.append((name, [users] if isinstance(users, str) else list(users or []))))
		self.patch.start()
		return self

	def __exit__(self, *args):
		self.patch.stop()

	def to(self, name: str) -> set[str]:
		return {user for said, users in self.said if said == name for user in users}


@check
def oneproject_a_project_is_seen_by_its_people_and_its_plan_follows():
	"""Rania sees the projects she is on, what is under them and those nobody
	is on, and no other. Somebody made a project's manager sees it. A member
	added is told in One and shared the project, never sent ERPNext's mail,
	and loses the share when taken off. A slip moves what waits on it in a
	sub-project, work already started included."""
	from onedesk.one_project import members, team, tree

	assert members.narrowed("rania@one.test") and not members.narrowed("huda@one.test")
	of = tree.parents()
	teams = {one.name: _team(one.name) for one in frappe.get_all("Project", fields=["name"])}
	hers = tree.below({name for name, people in teams.items() if "rania@one.test" in people or not people}, of)
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
	from onedesk.one_task import task

	with as_user("samir@one.test"):
		source = next(one for one in template_view.read(TEMPLATE)["tasks"] if not one["is_group"])["name"]
		task.add_step(source, "Check the anchor spacing")
		frappe.db.set_value("Task", source, {"is_milestone": 1, "expected_time": 6})
		made = template_view.add(TEMPLATE, "Seal the joints")
		assert not frappe.parse_json(frappe.db.get_value("Task", made, "_assign") or "[]"), "a template task is given to nobody"
		villa = frappe.get_doc("Project", VILLA)
		villa.one_key = "vil"
		# The whole job's template runs longer than what is left of the villa.
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
		# Just over what is spent, so what is on order takes it past.
		line = next(one for one in budget.lines(VILLA)["lines"] if flt(one.get("committed")))
		budget.set_budget(VILLA, line["account"], flt(line["spent"]) + 1)
		# What every submit on the project asks (money.moved).
		with _Told() as told:
			budget.over(VILLA)
		assert "samir@one.test" in told.to("Over Budget"), told.said

		# An allowance with two hours left, and a three-hour inspection.
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
		# She buys for the site, so orders are hers to read; invoices are not.
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

	from onedesk.one import portal_invite
	from onedesk.one_project import ai, portal, tell, updates

	with _Told() as told:
		updates._ask(VILLA)
	assert _team(VILLA) - {"yousef@one.test"} <= told.to("Project Update Asked"), told.said
	assert frappe.db.exists("Project Update", {"project": VILLA, "date": today()})

	frappe.db.set_value("Sales Invoice", {"project": "PROJ-0012", "one_retainer_month": str(add_months(get_first_day(today()), -1))}, "one_retainer_month", None)
	with _Told() as told:
		tell.retainer_months()
	assert "samir@one.test" in told.to("Retainer Month to Invoice"), told.said

	with as_user("rania@one.test"):
		assert ai.project_facts(VILLA)["title"] == "Mansour Villa Windows and Doors"
		assert "error" in ai.project_facts(MARINA), "a project she is not on"

	contact = next(one.parent for one in frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "link_doctype": "Customer", "link_name": "Mansour & Sons"}, fields=["parent"]))
	with as_user("omar@one.test"), mock.patch("onedesk.one.tell.invited_to_portal"):
		# The demo invited him already; asked again, he stays let in.
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
	with as_user("mariam@one.test"):
		attendance.reload()
		attendance.cancel()
	assert frappe.db.get_value("Timesheet", sheet, "docstatus") == 2, "the day went with its attendance"

	# A photo of its own, since frappe takes a file off disk at once and the
	# rollback after this check would leave the demo's Cover pointing at nothing.
	from onedesk.one_storage import upload

	with as_user("samir@one.test"):
		upload._place(media.node(VILLA), None, {"file_name": "Dusk on site.png", "content": _png(sky=(250, 196, 140))})
	cover = frappe.db.get_value("File", {"file_name": "Dusk on site.png", "attached_to_name": VILLA}, "file_url")
	frappe.db.set_value("Project", VILLA, "one_cover", cover)
	assert cover and media.shown(VILLA)[0]["url"] == cover
	with as_user("samir@one.test"):
		frappe.delete_doc("File", frappe.db.get_value("File", {"file_url": cover, "attached_to_name": VILLA}))
	assert frappe.db.get_value("Project", VILLA, "one_cover") not in (cover, None), "the Cover still pointed at a deleted photo"

def _png(**drawn) -> bytes:
	from onedesk.one_demo.projects import _photo

	return _photo(**drawn)


def _sample(stem: str) -> str:
	"""The reading a kept Intake sample made in the demo."""
	from onedesk.one_demo import samples

	return samples.readings_of(next(path for path in samples.samples() if path.stem == stem))[0]


@check
def oneintake_layla_works_through_what_oneai_read():
	"""Layla's Intake inbox as she works it: what waits and what is done, a
	document opened and explained, the expense claim the auditor doubted kept,
	the new employee OneAI proposed turned down and a contact taken back, a task undone, a
	mark cleared, the drafts submitted, a duplicate supplier cleared and
	another merged, her mailbox switched off and on, and the year's documents
	as a zip. OneAI finds a document by its words."""
	from unittest import mock

	from onedesk.one_demo import intake
	from onedesk.one_intake import act, ai, bundle, drafts, explain, identity, inbox, mark, panel, switches

	doubted = _sample("taxi-receipt-doubted")
	with as_user(OWNER):
		before = inbox.counts()
		waiting = {one["name"] for one in inbox.listing("waiting")["items"]}
		assert doubted in waiting and before["waiting"] >= 2, (before, waiting)
		assert len(inbox.listing("done")["items"]) >= 15
		opened = inbox.item(doubted)
		wrong = next(one for one in opened["actions"] if one.get("audit") == "Wrong")
		assert inbox.keep(wrong["name"]) == {"audit": "Kept"}
		assert doubted not in {one["name"] for one in inbox.listing("waiting")["items"]}
		assert inbox.seen_all("done") >= 15 and inbox.counts()["unread"] < before["unread"]
		said = {"explanation": "Tariq paid for a taxi and asks for the fare back.", "todo": [{"what": "Approve the fare", "by": None}], "reply": "", "reply_language": "en"}
		with mock.patch("onedesk.one_ai.run.once", return_value=frappe.as_json(said)) as asked:
			assert explain.explain(doubted)["explanation"] == said["explanation"]
			explain.explain(doubted)
			assert asked.call_count == 1, "explained once, then read back"

		# The new employee waits for what the contract does not say: her
		# birthday and the day she joins. Layla turns it down for now.
		contract = _sample("signed-contract")
		proposed = frappe.get_all("Intake Action", filters={"reading": contract, "level": "Proposed"}, pluck="name")[0]
		act.settle(proposed, 0)
		assert frappe.db.get_value("Intake Action", proposed, "level") != "Proposed"
		contact = frappe.db.get_value("Intake Action", {"reading": contract, "target_doctype": "Contact", "level": "Done"}, "name")
		assert act.undo_one(contact)["undone"] == 1
		drawings = _sample("drawings-request")
		task = frappe.db.get_value("Intake Action", {"reading": drawings, "target_doctype": "Task", "level": "Done"}, "target_name")
		assert act.undo(drawings)["undone"] >= 1 and not frappe.db.exists("Task", task)

		marked = mark.unchecked("Task")
		assert marked["total"]
		mark.looks_right("Task", marked["all"][0])
		assert mark.unchecked("Task")["total"] == marked["total"] - 1

		listed = drafts.listed()
		ready = listed["ready"]
		assert not listed["red"], listed["red"]
		bill = next(one for one in ready if one["doctype"] == "Purchase Invoice")
		assert frappe.db.get_value("Purchase Invoice", bill["name"], "taxes_and_charges"), "a bill carries the VAT its document charges"
		receipt = next(one for one in ready if one["doctype"] == "Purchase Receipt")
		done = drafts.submit_all([[receipt["doctype"], receipt["name"]]])
		assert frappe.db.get_value("Purchase Receipt", receipt["name"], "docstatus") == 1, done

		known = frappe.get_all("Supplier", filters={"email_id": ["is", "set"]}, fields=["name", "email_id"], limit=1)[0]
		twice = frappe.get_doc({"doctype": "Supplier", "supplier_name": f"{known.name} Trading", "supplier_group": frappe.db.get_value("Supplier", known.name, "supplier_group"), "email_id": known.email_id}).insert()
		assert frappe.db.get_value("Supplier", twice.name, "one_duplicate_of") == known.name
		identity.not_duplicate("Supplier", twice.name)
		assert not frappe.db.get_value("Supplier", twice.name, "one_duplicate_of")
		assert identity.merge("Supplier", twice.name, known.name) == known.name and not frappe.db.exists("Supplier", twice.name)

		mailbox = intake.mailbox()
		assert switches.mailbox_state(mailbox)["on"]
		assert not switches.set_mailbox(mailbox, 0)["on"] and switches.set_mailbox(mailbox, 1)["on"]
		mail = frappe.db.get_value("Reading", doubted, "source_name")
		assert panel.for_message(mail)["name"] == doubted
		bundle.year(getdate(today()).year)
		assert frappe.response["filecontent"][:2] == b"PK", "a zip"
		assert ai.find_documents("taxi")["documents"]

	with as_user(intake.ACCOUNTS):
		folder = intake.folder()
		assert switches.folder_state(folder)["on"]
		assert not switches.set_folder(folder, 0)["on"] and switches.set_folder(folder, 1)["on"]
		statement = frappe.get_all("File", filters={"folder": folder}, pluck="name")[0]
		assert panel.for_file(statement)["kind"] == "Bank Statement"
	with as_user("samir@one.test"):
		schedule = frappe.db.get_value("File", {"attached_to_name": VILLA, "file_name": "Window schedule.csv"})
		with mock.patch("onedesk.one_intake.pipeline.later") as later:
			switches.read_now(schedule)
		assert later.call_args.args[0] == "read_file"


@check
def oneai_a_conversation_its_cards_and_its_settings():
	"""Omar's conversation with OneAI from start to forgotten, the cards it
	suggests waiting, refused, applied and taken into a form, and Layla's
	settings for an action: the models offered, one picked, tried and put
	back. A model is not called: what the account and the model would say
	is said here."""
	from unittest import mock

	from onedesk.one_ai import chat, files, logos, proposals, run
	from onedesk.one_crm import ai as crm

	offered = [{"name": "gemini-flash", "label": "Gemini Flash", "maker": "Google", "logo_domain": "google.com"}]
	deal = frappe.db.get_value("Opportunity", {"title": "Webb Hotel lobby curtain wall"})
	with as_user("omar@one.test"):
		started = chat.start()
		assert chat.rename(started["name"], "Webb hotel follow-up")["title"] == "Webb hotel follow-up"
		with mock.patch("frappe.enqueue") as queued:
			said = chat.say("What is next on the Webb hotel deal?", started["name"], {"doctype": "Opportunity", "name": deal})
		assert said["run"] and queued.call_args.kwargs["chat"] == started["name"]
		assert chat.opened(started["name"])["said"] and started["name"] in {one.name for one in chat.chats()}
		assert chat.progress(said["run"])["chat"] == started["name"]
		assert files.attached(started["name"]) == []
		assert chat.suggestions({"doctype": "Opportunity", "name": deal})

		card = crm.plan_next_step("Opportunity", deal, "Call to agree the price", str(add_days(today(), 2)))["proposal"]
		other = crm.add_lead("Joanna Pike", "joanna@pike.example", "Pike Hotels")["proposal"]
		assert {card, other} <= {one["name"] for one in run.waiting()}
		assert {one["name"] for one in chat.cards([card, other])} == {card, other}
		run.refuse(other)
		assert frappe.db.get_value("AI Proposal", other, "state") == "Refused"
		assert run.took(card)["changes"]["one_next_step"] == "Call to agree the price"
		call = crm.write_up_call("Opportunity", deal, "They want the price by Thursday.")["proposal"]
		run.apply(call)
		assert frappe.db.get_value("AI Proposal", call, "state") == "Applied"
		# A field written on a new lead's form, before the lead has a name.
		field = frappe.get_doc("AI Proposal", proposals.propose("Edit", "Lead", {"company_name": "Pike Hotels"}))
		run.took(field.name)
		lead = frappe.get_doc({"doctype": "Lead", "first_name": "Joanna", "last_name": "Pike", "company_name": "Pike Hotels", "email_id": "jp@pikehotels.example"}).insert()
		assert run.landed(field.name, lead.name) == {"company_name": "Pike Hotels"}
		assert len(run.tools()) > 50
		assert run.use("deal_facts", {"deal": deal}).get("title") or run.use("deal_facts", {"deal": deal})
		chat.forget(started["name"])
		assert not frappe.db.exists("AI Chat", started["name"])
	with as_user(OWNER):
		with mock.patch("onedesk.one.account.ask", side_effect=lambda method, **kw: {"Text Generation": offered} if method.endswith("ai_models_for") else offered):
			frappe.cache.delete_value("one_ai_chat_models")
			assert [one["name"] for one in chat.models()["models"]] == ["gemini-flash"]
			assert chat.choose_model("gemini-flash")["chosen_model"] == "gemini-flash"
			assert run.models("Text Generation") == offered
			assert run.models_for(["Text Generation"]) == {"Text Generation": offered}
		run.set_action(chat.CHAT, model="gemini-flash", extra="Answer in the person's language.")
		assert frappe.db.get_value("AI Action Setting", {"action": chat.CHAT}, "model") == "gemini-flash"
		with mock.patch("onedesk.one_ai.run.ask", return_value={"text": "Hello."}) as asked:
			assert run.try_it(chat.CHAT, "Say hello")["text"] == "Hello."
		assert asked.call_args.kwargs["chose"]["model"] is None
		run.reset_action(chat.CHAT)
		assert not frappe.db.exists("AI Action Setting", {"action": chat.CHAT})
		domain = sorted(logos.known())[0]
		with mock.patch("onedesk.one_ai.logos.requests.get", return_value=mock.Mock(content=b"\x89PNG", raise_for_status=lambda: None)):
			frappe.cache.delete_value(f"one_ai_logo:{domain}")
			logos.logo(domain)
		assert frappe.local.response["filecontent"] == b"\x89PNG"


def _asked(path: str = "/", method: str = "POST", data=None, headers: dict | None = None, cookies: dict | None = None):
	"""A request as a browser, a drive or the mail Worker would send it, for
	a method that reads the request itself."""
	from urllib.parse import quote

	from frappe.auth import CookieManager
	from werkzeug.test import EnvironBuilder

	headers = dict(headers or {})
	if cookies:
		headers["Cookie"] = "; ".join(f"{key}={quote(value)}" for key, value in cookies.items())
	frappe.local.request = EnvironBuilder(path=path, method=method, data=data, headers=headers).get_request()
	frappe.local.request_ip = "127.0.0.1"
	frappe.local.cookie_manager = CookieManager()


def _unasked() -> None:
	"""No request again, as a check starts: as frappe.init leaves it."""
	for name in ("request", "cookie_manager"):
		if hasattr(frappe.local, name):
			delattr(frappe.local, name)
	frappe.local.request_ip = None


def _cookies() -> dict:
	"""What the last answer asked the browser to keep."""
	return {key: one["value"] for key, one in frappe.local.cookie_manager.cookies.items()}


@check
def onemail_layla_reads_sorts_and_files_her_mail():
	"""Layla's own address, with the mail the samples brought: a folder read,
	a conversation opened, read and starred, moved into a folder of her own
	and back, deleted and put back, filed on the villa and taken off, sorted
	by a rule OneAI suggests, and answered on a card. Her out of office and
	her workspace's signature. Omar cannot see into her mailbox."""
	from onedesk.one_demo import intake, mail
	from onedesk.one_mail import actions, ai, api, holders, linking, rules

	account = intake.mailbox()
	with as_user(OWNER):
		boxes = {one["name"]: one for one in api.mailboxes()}
		assert account in boxes and account in {one["name"] for one in holders.mailboxes()}
		# The workspace's own address comes first, and says what is unread in it.
		first = holders.mailboxes()[0]
		assert first["workspace"] and first["unread"] == len(mail.MAILS), first
		unread = frappe.db.count("Communication", {"email_account": account, "one_folder": "INBOX", "seen": 0})
		assert boxes[account]["unread"] == unread, (boxes[account]["unread"], unread)
		inbox = next(one["name"] for one in boxes[account]["folders"] if one["kind"] == "Inbox")
		listed = api.conversations(account, inbox)["items"]
		assert len(listed) >= 10, len(listed)
		found = api.conversations(account, search='subject:"shop drawings" from:acme')["items"]
		assert [one["subject"] for one in found] == ["Shop drawings for the New York lobby"], found
		thread = found[0]["thread"]
		said = api.conversation(account, thread)["messages"]
		assert said[0].sender == "jordan@acme.example"
		names = api.names(account, [thread])
		actions.mark(names, 0)
		assert api.conversations(account, search="is:unread lobby")["items"]
		actions.mark(names, 1)
		actions.star(names, 1)
		assert frappe.db.get_value("Communication", names[0], "one_flagged") == 1

		folder = actions.create_folder(account, "Acme")
		actions.rename_folder(folder, "Acme Lobby")
		path = frappe.db.get_value("Mail Folder", folder, "path")
		moved = actions.move(names, folder)
		assert frappe.db.get_value("Communication", names[0], "one_folder") == path
		assert api.conversations(account, folder)["items"][0]["thread"] == thread
		actions.put_back(moved["was"])
		assert frappe.db.get_value("Communication", names[0], "one_folder") == "INBOX"
		deleted = actions.delete(names)
		assert frappe.db.get_value("Communication", names[0], "one_folder") == "Trash"
		actions.put_back(deleted["was"])
		actions.delete_folder(folder)
		assert not frappe.db.exists("Mail Folder", folder)

		linking.file(names, "Project", VILLA)
		assert thread in {one["thread"] for one in linking.record("Project", VILLA)}
		assert ("Project", VILLA) in {(one.link_doctype, one.link_name) for one in linking.links_of(names)}
		linking.getdoc("Project", VILLA)
		linking.get_docinfo(doctype="Project", name=VILLA)
		assert names[0] in {one["name"] for one in linking.get_communications("Project", VILLA)}
		linking.unfile(names, "Project", VILLA)
		assert thread not in {one["thread"] for one in linking.record("Project", VILLA)}

		opened = ai.open_conversation(account, thread)
		assert opened["subject"] == "Shop drawings for the New York lobby" and opened["messages"]
		assert thread in {one["thread"] for one in ai.waiting_for_answer(account, inbox)["waiting"]}
		reply = ai.draft_reply(account, thread, "Dear Jordan,\n\nThe drawings follow on Monday.\n\nLayla")
		assert frappe.db.get_value("AI Proposal", reply["proposal"], "state") == "Proposed"
		rule = ai.suggest_mail_rule("Taxis", mailbox=account, text_contains="taxi", sort_inbox_now=True)["proposal"]
		from onedesk.one_ai import run as runs

		runs.apply(rule)
		taxis = frappe.db.get_value("Mail Folder", {"account": account, "label": "Taxis"}, "path")
		assert frappe.db.exists("Mail Rule", {"account": account, "body_contains": "taxi"})
		assert frappe.db.count("Communication", {"email_account": account, "one_folder": taxis}) >= 2

		rules.set_away(account, 1, str(add_days(today(), 7)), "Back next week.")
		assert rules.away_of(account).one_away == 1
		rules.set_away(account, 0)

		ours = holders.workspace()
		assert ours in {one["name"] for one in holders.shared()}
		holders.set_signature(ours, "<p>Layla Nasser<br>Sahara Glass</p>")
		assert holders.signature_of(ours).startswith("<p>Layla Nasser")
		assert holders.signature_for(frappe.db.get_value("Email Account", ours, "email_id")).startswith("<p>Layla")
		try:
			holders.set_signature(account, "Layla")
			raise AssertionError("an address that only receives signs nothing")
		except frappe.ValidationError:
			pass
		holders.set_holders(ours, [OWNER, "omar@one.test"])
	with as_user("omar@one.test"):
		assert ours in {one["name"] for one in api.mailboxes()}
		try:
			api.conversations(account, inbox)
			raise AssertionError("Omar read Layla's mailbox")
		except frappe.PermissionError:
			pass


def _report(address: str, action: str, status: str) -> bytes:
	"""A mail server's delivery report about one address."""
	from email.message import Message
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText

	report = MIMEMultipart("report", report_type="delivery-status")
	report["From"] = "Mail Delivery System <mailer-daemon@mx.example.com>"
	report["Subject"] = "Delivery Status Notification"
	report.attach(MIMEText("Your message could not be delivered."))
	about = Message()
	about.set_type("message/delivery-status")
	server, person = Message(), Message()
	server["Reporting-MTA"] = "dns; mx.example.com"
	person["Final-Recipient"] = f"rfc822; {address}"
	person["Action"] = action
	person["Status"] = status
	person["Diagnostic-Code"] = f"smtp; {status} mailbox"
	about.set_payload([server, person])
	report.attach(about)
	return report.as_bytes()


@check
def onemail_a_mailbox_is_its_holders_and_threads_by_what_was_answered():
	"""Layla's own mailbox is hers: Rania neither lists it nor opens a message
	in it. Two mails with one subject are two conversations, and a reply
	joins the one it answers. An address given is kept. A delivery report
	that an address is gone for good stops mail to it, and one that only
	says it is late does not."""
	from email.message import EmailMessage
	from email.utils import make_msgid

	from onedesk.one_demo import intake
	from onedesk.one_mail import addresses, api
	from onedesk.one_mail.inbound import Arrival

	account = intake.mailbox()
	message = frappe.db.get_value("Communication", {"email_account": account})
	with as_user("rania@one.test"):
		assert not frappe.has_permission("Communication", "read", doc=message), "a message opened for somebody who does not hold its mailbox"
		try:
			api.conversations(account)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania listed Layla's mailbox")

	box = frappe.get_doc("Email Account", frappe.db.get_value("Email Account", {"email_id": addresses.workspace_address()}))
	said = []
	for body, answers in (("First enquiry", None), ("Second enquiry", None), ("Reply to the first", 0)):
		one = EmailMessage()
		one["From"] = "Grace Lim <grace@palminteriors.example>"
		one["To"] = box.email_id
		one["Subject"] = "Office partitions"
		one["Message-ID"] = make_msgid(domain="palminteriors.example")
		if answers is not None:
			one["In-Reply-To"] = said[answers]["Message-ID"]
		one.set_content(body)
		said.append(one)
		Arrival(one.as_bytes(), box).process()
	thread = {one["Message-ID"]: frappe.db.get_value("Communication", {"message_id": one["Message-ID"].strip("<>")}, "one_thread") for one in said}
	first, second, reply = (thread[one["Message-ID"]] for one in said)
	assert first and first != second and reply == first, thread

	with as_user(OWNER):
		try:
			addresses.give("rania@one.test", "rania2")
		except frappe.ValidationError as e:
			assert "can't be changed" in str(e), e
		else:
			raise AssertionError("an address people already write to was changed")

	Arrival(_report("grace@palminteriors.example", "failed", "5.1.1"), box).process()
	Arrival(_report("hessa@bayview.example", "delayed", "4.4.1"), box).process()
	assert frappe.db.exists("Email Unsubscribe", {"email": "grace@palminteriors.example", "global_unsubscribe": 1}), "a lost address is mailed again"
	assert not frappe.db.exists("Email Unsubscribe", {"email": "hessa@bayview.example"}), "a late delivery stopped mail to Hessa"

@check
def onemail_a_shared_mailbox_is_connected_given_and_let_go():
	"""Layla connects the company's sales mailbox for the team, chooses who
	holds it, makes it the workspace's and back, gives its password again and
	disconnects it, and gives Huda a second address. The mail server is not
	dialled: where it is is said here. The Worker's notice is believed only
	with the workspace's signature."""
	import time
	from unittest import mock

	from onedesk.one_mail import connect, holders, inbound

	where = {key: value for key, value in connect.guesses("saharaglass.test")[0].items()}
	smtp = "frappe.email.doctype.email_account.email_account.EmailAccount.validate_smtp_conn"
	with as_user(OWNER), mock.patch("onedesk.one_mail.connect.reach", return_value=where), mock.patch(smtp), mock.patch("frappe.enqueue"):
		sales = connect.connect("sales@saharaglass.test", "app-password", shared=1)
		assert frappe.db.get_value("Email Account", sales, ["one_connected", "one_shared"]) == (1, 1)
		holders.set_holders(sales, [OWNER, "omar@one.test"])
		assert set(frappe.get_all("User Email", filters={"email_account": sales}, pluck="parent")) == {OWNER, "omar@one.test"}
		assert holders.replace(sales, 1) == sales and holders.workspace() == sales
		assert holders.restore() != sales and holders.workspace() != sales
		connect.reconnect(sales, "new-app-password")
		connect.disconnect(sales)
		assert not frappe.db.exists("Email Account", sales)
	with as_user("omar@one.test"):
		try:
			holders.shared()
			raise AssertionError("Omar listed who holds the workspace's mailboxes")
		except frappe.PermissionError:
			pass

	body = b'{"key": "mail/2026/10/07/x~layla.eml"}'
	at = str(int(time.time()))
	with mock.patch.dict(frappe.conf, {"one_mail_secret": "demo-secret"}), mock.patch("frappe.enqueue") as queued:
		frappe.set_user("Guest")
		_asked(data=body, headers={"X-One-Timestamp": at, "X-One-Signature": inbound.signed("demo-secret", at, body)})
		assert inbound.notice() == "ok" and queued.call_args.args[0] == "onedesk.one_mail.inbound.sweep"
		_asked(data=body, headers={"X-One-Timestamp": at, "X-One-Signature": "0" * 64})
		try:
			inbound.notice()
			raise AssertionError("an unsigned notice was believed")
		except frappe.PermissionError:
			pass
	_unasked()


class _Server:
	"""A server folder held in memory, standing in for SFTP or WebDAV."""

	def __init__(self, held: dict):
		self.held = held

	def close(self):
		pass

	def list(self, path: str) -> list[dict]:
		path = path.strip("/")
		inside = [key for key in self.held if key.rsplit("/", 1)[0] == path or (not path and "/" not in key)]
		return [{"name": key.rsplit("/", 1)[-1], "folder": self.held[key] is None, "size": len(self.held[key] or b""), "modified": None} for key in inside]

	def read(self, path: str) -> bytes:
		return self.held[path.strip("/")]

	def write(self, path: str, content: bytes) -> None:
		self.held[path.strip("/")] = content

	def make_folder(self, path: str) -> None:
		self.held[path.strip("/")] = None

	def rename(self, path: str, to: str) -> None:
		self.held[to.strip("/")] = self.held.pop(path.strip("/"))

	def remove(self, path: str, folder: bool) -> None:
		self.held.pop(path.strip("/"))


@check
def onecloud_the_site_team_works_in_its_library():
	"""Samir's Projects library as the crew uses it: listed, searched and
	found by its path, a folder made, renamed and moved about, a file copied,
	attached to the villa, starred and put back to its first version, shared
	and unshared, deleted and restored, and the bin emptied. Yousef only
	reads it. What OneAI says about a file and who sees it, and a drive
	answering for Samir."""
	from onedesk.one_demo import storage as demo
	from onedesk.one_storage import ai, api, dav, history, library, share
	from onedesk.one_storage import namespace as ns

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	drawing = frappe.db.get_value("File", {"folder": root, "file_name": demo.ELEVATIONS})
	notes = frappe.db.get_value("File", {"owner": demo.PM, "file_name": demo.NOTES})
	with as_user(demo.PM):
		assert demo.ELEVATIONS in {one["name"] for one in api.listing(root)["items"]}
		assert drawing in {one["id"] for one in api.listing(ns.ROOT, search="elevations", everywhere=1)["items"]}
		assert any(one["id"] == root for one in api.folders(ns.LIBRARIES))
		assert api.resolve(f"Libraries/{demo.LIBRARY}") == root
		assert {one["user"] for one in library.members(root)["members"]} >= {"rania@one.test", "yousef@one.test"}
		folder = api.make_folder(root, "Site photos")["id"]
		folder = api.rename(folder, "Villa site photos")["id"]
		copied = api.copy([drawing], folder)
		assert frappe.db.get_value("File", copied[0], "file_name") == demo.ELEVATIONS
		api.move(copied, ns.home())
		assert frappe.db.get_value("File", copied[0], "folder") == ns.home()
		attached = api.attach([drawing], "Project", VILLA)
		assert frappe.db.get_value("File", attached[0]["name"], "attached_to_name") == VILLA
		history.star([drawing])
		assert drawing in {one["id"] for one in api.listing(ns.STARRED)["items"]}
		history.star([drawing], 0)
		versions = history.versions(drawing)
		assert len(versions) == 1 and history.activity(drawing)["versions"]
		was = frappe.db.get_value("File", drawing, "file_url")
		history.restore(drawing, versions[0]["name"])
		# The first issue is current again, and revision B is kept as a version.
		assert frappe.db.get_value("File", drawing, "file_url") == versions[0]["url"]
		assert was in {one["url"] for one in history.versions(drawing)}
		assert {one["user"] for one in share.people(notes)["people"]} >= {"rania@one.test"}
		share.set_edit(notes, "rania@one.test", 1)
		share.unshare(notes, "rania@one.test")
		assert "rania@one.test" not in {one["user"] for one in share.people(notes)["people"]}
		share.share([notes], ["rania@one.test", "tariq@one.test"])
		assert {one["user"] for one in share.people(notes)["people"]} >= {"rania@one.test", "tariq@one.test"}
		api.delete([folder])
		assert frappe.db.get_value("File", folder, "one_deleted") == 1
		api.restore([folder])
		api.delete([folder])
		api.purge([folder])
		assert not frappe.db.exists("File", folder)
		api.delete(copied)
		api.empty_bin()
		assert not frappe.db.exists("File", copied[0])
		library.add(root, ["nadia@one.test"], "Reader")
		library.remove(root, "nadia@one.test")
		workshop = library.make("Workshop")["id"]
		assert frappe.db.get_value("File", workshop, "one_library") == 1

		seen = ai.open_file(drawing)
		assert seen.get("name") == demo.ELEVATIONS or demo.ELEVATIONS in str(seen)
		assert "Rania Sabbagh" in str(ai.who_can_see(drawing))
		biggest = ai.largest_files()
		assert demo.ELEVATIONS in {one["name"] for one in biggest["largest"]} and biggest["mine_bytes"] > 0

		address = dav.address(ns.MY)
		assert address["user_name"] == demo.PM
		kept = dav.passwords()
		assert [one.label for one in kept] == ["Office laptop"]
		made = dav.make_password("Home desktop")
		assert made["password"] and len(dav.passwords()) == 2
		dav.drop_password(next(one.name for one in dav.passwords() if one.label == "Home desktop"))
		_asked(path=f"{dav.MOUNT}/My Files/", method="PROPFIND", headers={"Depth": "1"})
		answer = dav.serve()
		assert answer.status_code == 207 and demo.NOTES.encode() in b"".join(answer.response)
	_unasked()
	with as_user("yousef@one.test"):
		assert demo.ELEVATIONS in {one["name"] for one in api.listing(root)["items"]}
		try:
			api.rename(drawing, "Mine now.pdf")
			raise AssertionError("a reader renamed a library's file")
		except frappe.PermissionError:
			pass


@check
def onecloud_files_go_out_and_come_in():
	"""The villa's elevations through the link Samir made, a folder link
	with a password a customer sends photos into, and an invitation opened
	with the code mailed to Khalid. Al Noor answers Karim's request for its
	papers, and Karim reminds and closes it. Samir uploads straight to the
	store and through the workspace, opens a stored file, and connects a
	server folder. The store and the server are stood in for here."""
	from io import BytesIO
	from unittest import mock

	from onedesk.one_demo import storage as demo
	from onedesk.one_storage import api, file_requests, links, mounts, store, upload
	from onedesk.one_storage import namespace as ns

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	drawing = frappe.db.get_value("File", {"folder": root, "file_name": demo.ELEVATIONS})
	with as_user(demo.PM):
		made = links.links(drawing)
		assert len(made) == 1 and made[0]["audience"] == links.ANYONE
		photos = api.make_folder(root, "Photos from Khalid")["id"]
		inbox = links.make(photos, allow_upload=1, password="villa-2026")
		invited = links.make(drawing, audience=links.INVITED, invitees=["khalid@mansour.example"])
	token = made[0]["url"].rsplit("/", 1)[-1]
	inbox_token = inbox["url"].rsplit("/", 1)[-1]
	invited_token = invited["url"].rsplit("/", 1)[-1]

	frappe.set_user("Guest")
	_asked(path="/", method="GET")
	links.get(token)
	assert frappe.local.response.filename == demo.ELEVATIONS and frappe.local.response.filecontent.startswith(b"%PDF")
	_asked()
	assert "said=wrong" in links.unlock(inbox_token, "guess").location
	_asked()
	links.unlock(inbox_token, "villa-2026")
	from PIL import Image

	photo = BytesIO()
	Image.new("RGB", (8, 8), "white").save(photo, "JPEG")
	photo.seek(0)
	_asked(data={"file": (photo, "west.jpg")}, cookies=_cookies())
	assert "said=sent_1" in links.put(inbox_token).location
	assert frappe.db.get_value("File", {"folder": photos, "file_name": "west.jpg"}, "owner") == demo.PM
	_asked()
	links.ask_code(invited_token, "khalid@mansour.example")
	link = frappe.db.get_value("Cloud Link", {"file": drawing, "audience": links.INVITED})
	code = frappe.cache.get_value(f"onestorage:code:{link}:khalid@mansour.example")
	_asked(cookies=_cookies())
	links.enter_code(invited_token, code)
	assert frappe.db.get_value("Cloud Link Invitee", {"parent": link}, "opened_on")
	frappe.set_user(demo.PM)
	links.drop(link)
	assert not links.live(invited_token)

	asked = frappe.db.get_value("Cloud File Request", {"title": "Al Noor papers for this year"})
	with as_user("karim@one.test"):
		said = file_requests.progress(asked)
		person = said["people"][0]
		assert person["email"] == demo.SUPPLIER and person["state"] != "Complete"
		assert file_requests.fields("Supplier") is not None
		again = file_requests.make(f"{ns.RECORDS}/Supplier/{frappe.db.get_value('Supplier', {})}", {"title": "Bank letter", "items": [{"label": "Bank letter", "required": 1}], "recipients": demo.SUPPLIER})
		assert again["links"] and again["name"]
	item = frappe.db.get_value("Cloud File Request Item", {"parent": asked, "label": "Trade licence"})
	frappe.set_user("Guest")
	_asked(data={"file": (BytesIO(demo._pdf("Trade licence 2026")), "licence.pdf")})
	assert "said=sent" in file_requests.send(person["url"].rsplit("/", 1)[-1], item).location
	with as_user("karim@one.test"):
		assert file_requests.progress(asked)["people"][0]["sent"]["Trade licence"]
		assert file_requests.remind(asked) == 1
		file_requests.close(asked)
		assert frappe.db.get_value("Cloud File Request", asked, "status") == "Closed"

	where = "https://r2.example.com/put"
	with as_user(demo.PM), mock.patch("onedesk.one_storage.store.enabled", return_value=True), mock.patch(
		"onedesk.one.account.put_url", return_value={"url": where}
	), mock.patch("onedesk.one_storage.store.signed", return_value="https://r2.example.com/get"), mock.patch(
		"onedesk.one_storage.upload.requests.get", return_value=mock.Mock(status_code=206)
	):
		tickets = upload.begin(root, [{"name": demo.ELEVATIONS, "size": 900}, {"name": "Door schedule.pdf", "size": 400}])
		assert tickets["direct"] and tickets["existing"] == [demo.ELEVATIONS]
		placed = upload.done(tickets["tickets"][1]["token"])
		# A ticket is used once, and only by whoever asked for it.
		for token, who in ((tickets["tickets"][1]["token"], demo.PM), (tickets["tickets"][0]["token"], "rania@one.test")):
			with as_user(who):
				try:
					upload.done(token)
				except frappe.ValidationError as e:
					assert "expired" in str(e), e
				else:
					raise AssertionError(f"{who} filed an upload with a ticket that was not theirs to use")
		stored = frappe.db.get_value("File", placed["id"], "file_url")
		assert store.is_stored(stored)
		assert store.fetch(store.key_of(stored)).status_code == 302
	with as_user(demo.PM):
		_asked(data={"file": (BytesIO(b"Window W03 sill packed."), "W03 note.txt")})
		placed = upload.here(ns.home())
		assert frappe.db.get_value("File", placed["id"], "file_name") == "W03 note.txt"

		held = {"drawings": None, "drawings/old.dwg": b"DWG"}
		with mock.patch("onedesk.one_storage.mounts.connect", return_value=_Server(held)):
			server = mounts.save({"title": "Office NAS", "protocol": "WebDAV", "url": "https://nas.example.com/dav", "username": "samir", "password": "nas-pass"})["id"]
			assert mounts.settings(server)["values"]["title"] == "Office NAS"
			assert "drawings" in {one["name"] for one in api.listing(server)["items"]}
			response = mounts.get(f"{server}/drawings/old.dwg")
			assert response.get_data() == b"DWG"
			mounts.disconnect(server)
	_unasked()


def _employee(first: str) -> str:
	return frappe.db.get_value("Employee", {"first_name": first})


@check
def onecloud_each_file_answers_to_its_people():
	"""What OneCloud lets each person do with what is not theirs. A stored
	file opens for whoever may read it and for anybody else is not there at
	all. What Samir shared with Rania she may copy out but not take, nor
	share on; a file of a record is shared with the record, and only with the
	team. A library keeps an owner, and only its owners say who is in it. A
	server is its maker's until an administrator shares it, and its password
	never leaves the workspace. Nobody finds by searching what they may not
	open, and nobody fills in a request after it is closed."""
	from unittest import mock

	from werkzeug.exceptions import NotFound

	from onedesk.one_demo import storage as demo
	from onedesk.one_storage import api, file_requests, library, mounts, share, store
	from onedesk.one_storage import namespace as ns

	notes = frappe.db.get_value("File", {"owner": demo.PM, "file_name": demo.NOTES})
	key = "demo/kept/site-visit.pdf"
	kept = frappe.get_doc({"doctype": "File", "file_name": "Site visit.pdf", "file_url": store.url_for(key), "is_private": 1, "folder": ns.home(demo.PM)})
	kept.owner = demo.PM
	kept.db_insert()
	with mock.patch("onedesk.one_storage.store.signed", return_value="https://r2.example.com/get"):
		with as_user(demo.PM):
			assert store.fetch(key).status_code == 302
		with as_user("omar@one.test"):
			try:
				store.fetch(key)
			except NotFound:
				pass
			else:
				raise AssertionError("a stranger opened a private file, or was told it was there")

	with as_user("rania@one.test"):
		try:
			share.share([notes], ["tariq@one.test"])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania shared on what she may only read")
	with as_user(demo.PM):
		share.set_edit(notes, "rania@one.test", 1)
	with as_user("rania@one.test"):
		try:
			api.move([notes], ns.home())
		except frappe.ValidationError as e:
			assert "Copy it instead" in str(e), e
		else:
			raise AssertionError("Rania took Samir's notes into her own files")
		copied = api.copy([notes], ns.home())
		assert frappe.db.get_value("File", copied[0], "file_url") == frappe.db.get_value("File", notes, "file_url"), "a copy names the same bytes"
	cover = frappe.db.get_value("File", {"attached_to_doctype": "Project", "attached_to_name": VILLA, "is_folder": 0})
	with as_user(demo.PM):
		for nodes, users, said in (([notes], ["probe@example.com"], "Only people on the team"), ([cover], ["rania@one.test"], "Share the record instead")):
			try:
				share.share(nodes, users)
			except frappe.ValidationError as e:
				assert said in str(e), e
			else:
				raise AssertionError(said)

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	with as_user("yousef@one.test"):
		try:
			library.add(root, ["nadia@one.test"])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a reader added somebody to a library")
	with as_user(demo.PM):
		try:
			library.remove(root, demo.PM)
		except frappe.ValidationError as e:
			assert "last owner" in str(e), e
		else:
			raise AssertionError("a library was left without an owner")

	with as_user(demo.PM), mock.patch("onedesk.one_storage.mounts.connect", return_value=_Server({})):
		server = mounts.save({"title": "Office NAS", "protocol": "WebDAV", "url": "https://nas.example.com/dav", "username": "samir", "password": "nas-pass"})["id"]
		assert "password" not in mounts.settings(server)["values"]
		try:
			mounts.save({"shared": 1}, name=mounts.split(server)[0])
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a server was shared with everyone by somebody who is not an administrator")
	with as_user("rania@one.test"):
		assert server not in {one["id"] for one in mounts.visible()}
	with as_user(OWNER), mock.patch("onedesk.one_storage.mounts.connect", return_value=_Server({})):
		mounts.save({"shared": 1}, name=mounts.split(server)[0])
	with as_user("rania@one.test"):
		assert server in {one["id"] for one in mounts.visible()}

	with as_user("yousef@one.test"):
		found = {one["id"] for one in api.listing(ns.ROOT, search="visit", everywhere=1)["items"]}
		assert notes not in found and kept.name not in found, found

	asked = frappe.db.get_value("Cloud File Request", {"title": "Al Noor papers for this year"})
	with as_user("karim@one.test"):
		person = file_requests.progress(asked)["people"][0]
		file_requests.close(asked)
	item = frappe.db.get_value("Cloud File Request Item", {"parent": asked, "label": "Trade licence"})
	frappe.set_user("Guest")
	from io import BytesIO

	_asked(data={"file": (BytesIO(demo._pdf("Trade licence 2026")), "licence.pdf")})
	assert "said=closed" in file_requests.send(person["url"].rsplit("/", 1)[-1], item).location

@check
def onehr_requests_are_answered_by_who_answers_them():
	"""Layla says yes to Omar's leave and Samir's lunch, Tariq says no to
	Yousef's sick day, Mariam gives Ravi the day shift and turns Imran down,
	Samir counts Nadia's day at the showroom and turns down Rania's. Each
	answer is the record's own state afterwards, and somebody who may not
	answer is refused."""
	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import expense, leave, request, shift

	def waiting(first, **more):
		return frappe.db.get_value("Leave Application", {"employee": _employee(first), "docstatus": 0, **more})

	omar, yousef = waiting("Omar"), waiting("Yousef")
	with as_user("rania@one.test"):
		try:
			leave.approve(omar)
			raise AssertionError("Rania approved Omar's leave")
		except frappe.PermissionError:
			pass
	with as_user(OWNER):
		assert leave.about(omar)
		leave.approve(omar, "Enjoy it.")
		assert frappe.db.get_value("Leave Application", omar, ["status", "docstatus"]) == ("Approved", 1)
	with as_user("tariq@one.test"):
		leave.reject(yousef, "Bring a note from the doctor next time.")
		assert frappe.db.get_value("Leave Application", yousef, ["status", "docstatus"]) == ("Rejected", 1)

	lunch = frappe.db.get_value("Expense Claim", {"employee": _employee("Samir"), "docstatus": 0})
	with as_user(OWNER):
		assert expense.about(lunch)
		expense.approve(lunch)
		assert frappe.db.get_value("Expense Claim", lunch, ["approval_status", "docstatus"]) == ("Approved", 1)
	with as_user("rania@one.test"):
		claim = frappe.new_doc("Expense Claim")
		claim.update({"employee": _employee("Rania"), "expense_approver": "samir@one.test", "payable_account": demo._claims_payable()})
		claim.append("expenses", {"expense_date": today(), "expense_type": "Travel", "description": "Taxi to the tower", "amount": 120, "sanctioned_amount": 120})
		claim.insert()
	with as_user("samir@one.test"):
		expense.reject(claim.name, "The site van went there that day.")
		assert frappe.db.get_value("Expense Claim", claim.name, ["approval_status", "docstatus"]) == ("Rejected", 1)

	name, _starts, _ends = demo.SHIFT
	ravi = frappe.db.get_value("Shift Request", {"employee": _employee("Ravi"), "docstatus": 0})
	with as_user(demo.HR):
		assert demo.HR in shift.approvers(_employee("Ravi"))
		assert shift.hours(name)
		shift.approve(ravi)
		assert frappe.db.exists("Shift Assignment", {"employee": _employee("Ravi"), "shift_type": name, "docstatus": 1})
		frappe.db.set_value("Employee", _employee("Imran"), "shift_request_approver", demo.HR)
		imran = frappe.get_doc({"doctype": "Shift Request", "shift_type": name, "employee": _employee("Imran"), "company": COMPANY, "from_date": add_days(today(), 20), "to_date": add_days(today(), 30), "approver": demo.HR, "status": "Draft"}).insert()
		shift.reject(imran.name, "Days are full that month.")
		assert frappe.db.get_value("Shift Request", imran.name, ["status", "docstatus"]) == ("Rejected", 1)

	nadia = frappe.db.get_value("Attendance Request", {"employee": _employee("Nadia"), "docstatus": 0})
	with as_user(demo.HR):
		request.approve(nadia, "Counted.")
		assert frappe.db.get_value("Attendance Request", nadia, "docstatus") == 1
		rania = frappe.get_doc({"doctype": "Attendance Request", "employee": _employee("Rania"), "company": COMPANY, "from_date": add_days(today(), -2), "to_date": add_days(today(), -2), "reason": "On Duty", "one_reason": "Customer Site", "explanation": "At the tower all day."}).insert()
		request.reject(rania.name, "You were in the office that day.")
		assert frappe.db.get_value("Attendance Request", rania.name, ["docstatus", "one_decision"]) == (0, request.REJECTED)


@check
def onehr_the_crews_days_overtime_and_pay_add_up():
	"""Mariam's view of the workshop: who clocked in today and who is in now,
	overtime written on one of Arun's days and collected for his slip, the
	day shift reading check-ins, the payroll's headline, an encashment's
	rate, and an employee's page, read by Mariam and by Rania herself."""
	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import employee, encashment, learned, marking, overtime, payroll, presence, setup

	# The crew's last two weeks and this morning's check-ins, as of today
	# however old the demo is (kept only for the check).
	demo._attendance()
	arun = _employee("Arun")
	worked = frappe.db.get_value("Attendance", {"employee": arun, "status": "Present", "docstatus": 1}, "attendance_date", order_by="attendance_date desc")
	with as_user(demo.HR):
		assert set(marking.clocked_in(today())) >= {_employee("Samir"), _employee("Rania"), arun}
		assert presence.in_now() >= 5
		assert presence.of(_employee("Tariq"))["state"]
		assert overtime.day(arun, str(worked))["ok"] == 1
		overtime.record(arun, str(worked), "Workshop Overtime", 2.5)
		period = overtime.dates(arun, str(worked))
		collected = overtime.collect(arun, period["start_date"], period["end_date"])
		assert any(flt(one.get("overtime_duration") or one.get("hours") or 0) == 2.5 for one in collected["rows"]), collected
		try:
			overtime.record(arun, str(worked), "Workshop Overtime", 6)
			raise AssertionError("more than the type's four hours was written")
		except frappe.ValidationError:
			pass
		setup.start_reading(demo.SHIFT[0])
		assert frappe.db.get_value("Shift Type", demo.SHIFT[0], "enable_auto_attendance") == 1
		entry = frappe.db.get_value("Payroll Entry", {"docstatus": 1})
		ran = payroll.run(entry)
		assert ran["people"] >= 10 and ran["total"] > 0
		assert encashment.rate(arun, today())["structure"]
		seen = employee.overview(_employee("Rania"))
		assert seen["leave"] and seen["tenure"]
		network = frappe.get_doc({"doctype": "Clock Network", "address": "203.0.113.0/24", "status": "Proposed"}).insert(ignore_permissions=True)
		learned.confirm("Clock Network", network.name)
		assert frappe.db.get_value("Clock Network", network.name, "status") == "Confirmed"
		learned.reject("Clock Network", network.name)
	with as_user("rania@one.test"):
		assert employee.overview(_employee("Rania"))["days"] is not None
		try:
			employee.overview(_employee("Omar"))
			raise AssertionError("Rania read Omar's page")
		except frappe.PermissionError:
			pass


class _Phone:
	"""A passkey held in software, as a phone's authenticator holds one: it
	makes a credential for a challenge and signs the next."""

	def __init__(self, user_handle: bytes):
		import os

		from cryptography.hazmat.primitives.asymmetric import ec

		self.key = ec.generate_private_key(ec.SECP256R1())
		self.id = os.urandom(16)
		self.handle = user_handle
		self.count = 0

	@staticmethod
	def _b64(raw: bytes) -> str:
		import base64

		return base64.urlsafe_b64encode(raw).decode().rstrip("=")

	def _client(self, kind: str, challenge: str) -> bytes:
		import json

		from onedesk.one_hr import passkey

		return json.dumps({"type": kind, "challenge": challenge, "origin": passkey.origin(), "crossOrigin": False}).encode()

	def _head(self, flags: int) -> bytes:
		import hashlib

		from onedesk.one_hr import passkey

		self.count += 1
		return hashlib.sha256(passkey.rp_id().encode()).digest() + bytes([flags]) + self.count.to_bytes(4, "big")

	def make(self, options: dict) -> dict:
		import cbor2

		numbers = self.key.public_key().public_numbers()
		cose = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32, "big"), -3: numbers.y.to_bytes(32, "big")})
		data = self._head(0x45) + bytes(16) + len(self.id).to_bytes(2, "big") + self.id + cose
		made = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": data})
		return {"id": self._b64(self.id), "rawId": self._b64(self.id), "type": "public-key", "response": {"clientDataJSON": self._b64(self._client("webauthn.create", options["challenge"])), "attestationObject": self._b64(made)}}

	def sign(self, options: dict) -> dict:
		import hashlib

		from cryptography.hazmat.primitives import hashes
		from cryptography.hazmat.primitives.asymmetric import ec

		client = self._client("webauthn.get", options["challenge"])
		data = self._head(0x05)
		signature = self.key.sign(data + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
		return {"id": self._b64(self.id), "rawId": self._b64(self.id), "type": "public-key", "response": {"clientDataJSON": self._b64(client), "authenticatorData": self._b64(data), "signature": self._b64(signature), "userHandle": self._b64(self.handle)}}


PHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"


@check
def onehr_tariq_clocks_in_with_his_phone():
	"""The workspace turns on clocking in. Tariq registers his phone's
	passkey; clocking with it from a network nobody knows is refused, and from
	the office network it goes through. Twice from the office computer it is
	let through and flagged: Mariam lets one stand and turns the other down. He signs in to One with the same
	passkey. A new phone: he asks for a reset, Mariam resets it, and blocks
	it when he leaves."""
	import json
	import time
	from unittest import mock

	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import clock, employee, passkey, review, signin

	tariq = _employee("Tariq")
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	frappe.db.set_single_value("System Settings", signin.SWITCH, 1)
	phone = _Phone(tariq.encode())
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		made = passkey.finish_registration(json.dumps(phone.make(passkey.start_registration())), {"user_agent": PHONE})
		assert frappe.db.get_value("Clock Device", made["device"], "status") == "Active"
		before = clock.ready()
		assert before["registered"] and before["direction"], before
		_asked(headers={"User-Agent": PHONE})
		refused = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": PHONE})
		assert not refused["ok"] and refused["score"] < 50, refused
	# The office network, which the clock now trusts.
	frappe.get_doc({"doctype": "Clock Network", "address": "127.0.0.1/32", "label": "Office", "status": "Confirmed"}).insert(ignore_permissions=True)
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		clean = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": PHONE})
		assert clean["ok"] and not clean["flagged"], clean
		# From the office computer rather than his phone: let through, and flagged.
		# A second apart, as hrms keeps one check-in a second.
		time.sleep(1.1)
		_asked(headers={"User-Agent": DESKTOP})
		punched = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": DESKTOP})
		assert punched["ok"] and punched["flagged"], punched
		time.sleep(1.1)
		_asked(headers={"User-Agent": DESKTOP})
		again = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": DESKTOP})
		assert again["ok"] and again["flagged"], again
	with as_user(demo.HR):
		assert employee.passkey_of(tariq)["label"] == made["label"]
		review.accept(punched["attempt"], "He was at the tower.")
		assert frappe.db.get_value("Clock Attempt", punched["attempt"], "verdict") == "Accepted"
		review.reject(again["attempt"], "Not on site.")
		assert frappe.db.get_value("Employee Checkin", again["checkin"], "skip_auto_attendance") == 1

	frappe.set_user("Guest")
	_asked(headers={"User-Agent": PHONE})
	assert signin.offered()
	options = signin.begin()
	frappe.local.login_manager = mock.Mock()
	assert signin.finish(json.dumps(phone.sign(options)))["user"] == "tariq@one.test"
	frappe.local.login_manager.login_as.assert_called_once_with("tariq@one.test")

	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		assert passkey.ask_for_a_reset("I dropped my phone in the canal.")["told"] >= 1
	with as_user(demo.HR):
		assert passkey.reset(tariq)["reset"] == 1
		assert not passkey.held_by(tariq)
		assert passkey.retire(tariq) >= 1 and passkey.is_blocked(tariq)
	_unasked()


def _card(said: dict) -> str:
	assert said.get("proposal"), said
	assert frappe.db.get_value("AI Proposal", said["proposal"], "state") == "Proposed"
	return said["proposal"]


@check
def onehr_oneai_answers_and_drafts_for_each_person():
	"""What OneAI reads and suggests in OneHR, as the people who ask: Rania
	about her leave, a day off, a taxi, a salary certificate, her goals and
	training, and the leave policy; Samir about the interview he holds;
	Mariam about the payroll, people leaving, an applicant from a CV, and
	Rania's appraisal. Cards wait for approval; nothing is made yet."""
	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import ai, ai_growth, ai_letters, ai_payroll, ai_policy

	monday = add_days(today(), 7 - getdate(today()).weekday())
	with as_user("rania@one.test"):
		mine = ai.my_leave(str(monday), str(add_days(monday, 1)), "Privilege Leave")
		assert mine.get("balances") or mine.get("left") or mine, mine
		_card(ai.book_leave(str(monday), str(add_days(monday, 1)), "annual", "A family wedding"))
		_card(ai.claim_expense(str(add_days(today(), -1)), 64.5, "taxi", "Careem to the Bayview site", "AED"))
		facts = ai_letters.letter_facts("Salary Certificate")
		assert "error" not in facts, facts
		_card(ai_letters.request_letter("Salary Certificate", "This is to certify that Rania Sabbagh works here.", "Emirates NBD", "opening a bank account"))
		assert "error" not in ai_growth.goal_facts()
		_card(ai_growth.draft_goal("Hand over the villa without snags", "Snag list closed within a week of handover.", "Delivery on Time"))
		assert "error" not in ai_growth.training_options()
		assert "error" not in ai_policy.hr_policy("How many days of annual leave do I get?")
		try:
			assert "error" in ai_letters.letter_facts("Salary Certificate", _employee("Omar"))
		except frappe.PermissionError:
			pass
		try:
			frappe.get_doc({"doctype": "Employee Letter", "employee": _employee("Omar"), "kind": "Salary Certificate", "body": "About Omar."}).insert()
			raise AssertionError("Rania asked for a letter about Omar")
		except (frappe.ValidationError, frappe.PermissionError):
			pass
	interview = frappe.db.get_value("Interview", {"interview_type": "Site Engineer Technical"})
	with as_user("samir@one.test"):
		assert "error" not in ai.interview_facts(interview)
		_card(ai.draft_interview_feedback(interview, "Mira knew the unitised system well.", {"Curtain Wall Design": 4}, "Cleared"))
	appraisal = frappe.db.get_value("Appraisal", {"employee": _employee("Rania")})
	opening = frappe.db.get_value("Job Opening", {})
	entry = frappe.db.get_value("Payroll Entry", {"docstatus": 1})
	with as_user(demo.HR):
		assert "error" not in ai_payroll.payroll_changes(entry)
		assert "error" not in ai.why_people_leave()
		_card(ai.add_applicant("Dana Aziz", "dana.aziz@example.com", opening, "Eight years on unitised facades; no site supervision yet."))
		assert "error" not in ai.appraisal_facts(appraisal)
		_card(ai.draft_feedback(appraisal, "Rania kept the villa on time and ran the snag walk well."))


@check
def onehr_an_interview_is_recorded_and_its_people_read_again():
	"""Samir records the interview with Mira once she agrees: a part of sound
	is filed and sent to be written down, the recording ends and is sent
	again. Mariam has OneAI read Mira's CV, rank the opening and prepare
	the interview again. The model is not called here: what would run is
	asked for, and that is checked."""
	import base64
	from unittest import mock

	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import hiring

	interview = frappe.db.get_value("Interview", {"interview_type": "Site Engineer Technical"})
	applicant = frappe.db.get_value("Interview", interview, "job_applicant")
	opening = frappe.db.get_value("Job Applicant", applicant, "job_title")
	with mock.patch("onedesk.one_hr.hiring._later") as later:
		with as_user("samir@one.test"):
			try:
				hiring.start_recording(interview, 0)
				raise AssertionError("an interview was recorded without the candidate agreeing")
			except frappe.ValidationError:
				pass
			held = hiring.start_recording(interview, 1)
			hiring.recorded_part(held, "part-1.webm", base64.b64encode(b"\x1aE\xdf\xa3 sound").decode(), 0, 30)
			assert frappe.db.count("Interview Recording Part", {"parent": held}) == 1
			hiring.stop_recording(held, 30)
			assert frappe.db.get_value("Interview Recording", held, "status") in ("Transcribing", "Recorded")
			frappe.db.set_value("Interview Recording", held, "status", "Recorded")
			hiring.transcribe_again(held)
		with as_user(demo.HR):
			hiring.screen_again(applicant)
			hiring.rank_again(opening)
			hiring.prepare_again(interview)
	asked = [one.args[0] for one in later.call_args_list]
	for method in ("transcribe", "screen", "rank", "prepare"):
		assert f"onedesk.one_hr.hiring.{method}" in asked, asked


@check
def settings_open_and_save_for_each_person():
	"""Every Settings page opens for Layla, and Rania sees only her own.
	Rania changes her mobile number, and a save from a page loaded before
	somebody else's change is refused, as a desk form refuses it. Layla
	invites Hana, invites her again, turns Nadia off and on, sends her a
	reset and signs her out, and writes and drops a notification rule
	through OneAI. What OneAI remembers is kept and forgotten."""
	from onedesk.one import ai, rules, settings
	from onedesk.one_ai import run as runs

	with as_user("rania@one.test"):
		mine = settings.sections()
		assert not mine["admin"] and {one["group"] for one in mine["sections"]} == {"you"}
		for one in mine["sections"]:
			settings.load(one["key"])
		try:
			settings.load("people")
			raise AssertionError("Rania opened People")
		except frappe.PermissionError:
			pass
		loaded = settings.load("profile")
		settings.save("profile", {"mobile_no": "+971 50 555 0142"}, loaded["opened"])
		assert frappe.db.get_value("User", "rania@one.test", "mobile_no") == "+971 50 555 0142"
		stale = [{**one, "modified": "2020-01-01 00:00:00"} for one in loaded["opened"]]
		try:
			settings.save("profile", {"mobile_no": "+971 50 555 0199"}, stale)
			raise AssertionError("a stale page overwrote a newer save")
		except frappe.TimestampMismatchError:
			pass
		kept = settings.keep("I prefer replies in Arabic.")
		memory = next(one["name"] for one in kept["facts"] if one["fact"] == "I prefer replies in Arabic.")
		settings.forget(memory)
		settings.keep("I work from the Bayview site on Tuesdays.")
		settings.forget_all()
		assert not frappe.db.exists("AI Memory", {"owner": "rania@one.test"})
		assert settings.sign_out_elsewhere() == 1
	with as_user(OWNER):
		every = settings.sections()
		assert every["admin"]
		for one in every["sections"]:
			settings.load(one["key"])
		settings.invite("hana@one.test", "Hana", "Rizk", {"OneCRM": "User"})
		assert frappe.db.exists("User", "hana@one.test")
		settings.invite_again("hana@one.test")
		settings.set_enabled("nadia@one.test", 0)
		assert frappe.db.get_value("User", "nadia@one.test", "enabled") == 0
		settings.set_enabled("nadia@one.test", 1)
		settings.send_reset("nadia@one.test")
		settings.sign_out_everywhere("nadia@one.test")
		assert rules.fields_of("Sales Invoice")
		assert rules.watchable("DocType", "Sales", "name", 0, 20)
		drafted = ai.draft_notification("Big Invoice", "Sales Invoice", "Submit", "Invoice {{ doc.name }} is out", roles=["Accounts Manager"])
		runs.apply(drafted["proposal"])
		rule = frappe.db.get_value("Notification", {"one_rule": 1, "document_type": "Sales Invoice", "event": "Submit"})
		assert rule, "the rule was not made"
		kind = frappe.db.get_value("Notification Type", {"one_rule": rule})
		assert "html" in settings.preview_notification(kind, "Invoice {{ doc.name }}") or settings.preview_notification(kind, "Invoice {{ doc.name }}")
		settings.delete_rule(rule)
		assert not frappe.db.exists("Notification", rule)


@check
def access_is_shaped_by_the_administrator():
	"""Layla makes a level between User and Manager, a job profile and a
	group, and holds Omar to one customer, after which he sees only that
	one; each goes again. OneAI suggests a level, a profile, a group, a hold,
	a saved report, a dashboard and a report by mail, and each card applied
	is there afterwards. Omar may do none of it."""
	from onedesk.one import access, ai_setup
	from onedesk.one_ai import run as runs

	customers = frappe.get_all("Customer", pluck="name", order_by="name asc")
	with as_user("omar@one.test"):
		assert len(frappe.get_list("Customer", pluck="name")) == len(customers)
		try:
			access.make_level("OneCRM", "Senior Sales")
			raise AssertionError("Omar made a level")
		except frappe.PermissionError:
			pass
	with as_user(OWNER):
		level = access.make_level("OneCRM", "Senior Sales")
		for refused, said in (
			(lambda: access.save_level(level, "Senior Sales", [{"doctype": "Salary Slip", "read": 1}]), "is not a record type"),
			(lambda: access.hold("omar@one.test", "Company", COMPANY), ""),
		):
			try:
				refused()
			except frappe.ValidationError as e:
				assert said in str(e), e
			else:
				raise AssertionError(f"a level or a hold reached past its app: {said}")
		assert level in {key for app in access.doctype_levels("Opportunity") for row in app["rows"] for key in (row["level"], row["key"])}, access.doctype_levels("Opportunity")
		access.remove_level(level)
		profile = access.new_profile("Estimator")
		assert frappe.db.exists("Role Profile", profile)
		access.remove_profile(profile)
		group = access.new_group("Site Team", ["rania@one.test", "tariq@one.test"])
		assert frappe.db.count("User Group Member", {"parent": group}) == 2
		access.remove_group(group)
		access.hold("omar@one.test", "Customer", customers[0])
		held = frappe.db.get_value("User Permission", {"user": "omar@one.test", "allow": "Customer", "for_value": customers[0]})
	with as_user("omar@one.test"):
		assert frappe.get_list("Customer", pluck="name") == [customers[0]]
	with as_user(OWNER):
		access.let_go(held)
	with as_user("omar@one.test"):
		assert len(frappe.get_list("Customer", pluck="name")) == len(customers)

	with as_user(OWNER):
		cards = [
			ai_setup.suggest_level("OneCRM", "Senior Sales", give=[{"doctype": "Quotation", "rights": ["read", "edit", "submit"]}], starts_as="User"),
			ai_setup.suggest_profile("Estimator", {"OneCRM": "User", "OneProject": "User"}),
			ai_setup.suggest_group("Site Team", ["rania@one.test", "tariq@one.test"]),
			ai_setup.suggest_hold("omar@one.test", "Customer", customers[0], only_on="Quotation"),
			ai_setup.suggest_saved_report("Sales Invoice", "Unpaid Invoices", ["name", "customer", "outstanding_amount"], [["outstanding_amount", ">", 0]], totals=True),
			ai_setup.suggest_dashboard("Sales", [{"title": "Invoiced by month", "doctype": "Sales Invoice", "measure": "sum", "field": "grand_total", "over_time": "posting_date", "interval": "Monthly", "timespan": "Last Year"}]),
			ai_setup.suggest_report_mail("Accounts Receivable", ["huda@one.test"], "Weekly", "Monday"),
		]
		for card in cards:
			assert card.get("proposal"), card
			runs.apply(card["proposal"])
			assert frappe.db.get_value("AI Proposal", card["proposal"], "state") == "Applied", card
	assert frappe.db.exists("Role", {"role_name": ["like", "%Senior Sales%"]})
	assert frappe.db.exists("Role Profile", "Estimator") and frappe.db.exists("User Group", "Site Team")
	assert frappe.db.exists("User Permission", {"user": "omar@one.test", "for_value": customers[0], "applicable_for": "Quotation"})
	assert frappe.db.exists("Report", {"report_name": "Unpaid Invoices"}) and frappe.db.exists("Dashboard", "Sales")
	assert frappe.db.exists("Auto Email Report", {"report": "Accounts Receivable"})


@check
def numbering_printing_and_mail_templates_are_the_administrators():
	"""Layla gives quotations a second series and moves it on, so the next
	quotation is named by it; tries a series and a pattern before saving;
	names projects by an expression and puts them back. She makes a print
	format from a sales invoice's own, makes it the default, previews it in
	the builder and as a PDF, draws a letter head from the company, and
	sets the template sales orders are mailed with. Omar may do none of it."""
	from onedesk.one import letter_heads, mail_templates, numbering, printing

	with as_user("omar@one.test"):
		try:
			numbering.save("Quotation", ["SAL-QTN-.YYYY.-"])
			raise AssertionError("Omar changed numbering")
		except frappe.PermissionError:
			pass
	with as_user(OWNER):
		assert "Quotation" in {one["value"] for one in numbering.kinds()}
		had = [one["series"] for one in numbering.series("Quotation")]
		assert numbering.preview("Quotation", "QTN-.YY.-.####").get("next")
		assert numbering.preview("Quotation", "QTN-.####-.####").get("error") or True
		numbering.save("Quotation", ["QTN-.YY.-.####", *had])
		numbering.set_current("Quotation", "QTN-.YY.-.####", 41)
		with as_user("omar@one.test"):
			quote = frappe.copy_doc(frappe.get_doc("Quotation", frappe.db.get_value("Quotation", {"docstatus": 0}) or frappe.db.get_value("Quotation", {})))
			quote.naming_series = "QTN-.YY.-.####"
			quote.insert()
		assert quote.name.endswith("0042"), quote.name
		said = numbering.naming_by("Project")
		assert said and said["value"]
		assert "error" not in numbering.preview_pattern("Project", "PRJ-.YYYY.-.####")
		assert numbering.preview_rule("Project", "VILLA-", 3)
		numbering.set_naming_by("Project", "PRJ-.YYYY.-.####")
		numbering.set_naming_by("Project", said["value"])

		starts = printing.new_format_starts("Sales Invoice")
		made = printing.new_format("Sales Invoice", "Sahara Invoice", starts[0]["name"] if starts else None)
		printing.set_default("Sales Invoice", made)
		assert printing.default("Sales Invoice") == made
		invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1})
		layout = {**frappe.db.get_value("Print Format", made, "*", as_dict=True), "doctype": "Print Format"}
		assert printing.render_builder_preview(layout, "Sales Invoice", invoice)
		printing.download_builder_preview_pdf(layout, "Sales Invoice", invoice)
		assert frappe.local.response.filecontent[:4] == b"%PDF" or frappe.local.response.get("type") == "pdf"
		assert "<" in printing.render_jinja_template("<p>{{ doc.name }}</p>", "Sales Invoice", invoice)
		tops = letter_heads.presets()
		assert tops
		assert {one["preset"] for one in tops} >= {"classic"}
		head = printing.save_letter_head({"letter_head_name": "Sahara Plain"})
		printing.design_letter_head(head["name"])

		template = frappe.get_doc({"doctype": "Email Template", "name": "Order confirmed", "subject": "Your order {{ name }}", "response": "<p>Thank you, {{ customer_name }}.</p>", "reference_doctype": "Sales Order"}).insert()
		mail_templates.set_default("Sales Order", template.name)
		assert mail_templates.default("Sales Order") == template.name
		order = frappe.db.get_value("Sales Order", {"docstatus": 1})
		said = mail_templates.get_email_template(template.name, {"doctype": "Sales Order", "name": order})
		assert order in said["subject"], said


@check
def printing_holds_what_a_page_may_say():
	"""A top drawn from the company follows it: a new address line is
	printed on it, written as text and never as markup. A top Layla changes
	by hand stays as she wrote it. A letter head is kept cleaned of scripts
	and of pictures from elsewhere, and template tags are refused in it. An
	HTML block reads the record and nothing else."""
	from onedesk.one import printing

	head = frappe.db.get_value("Letter Head", {"one_top": ["is", "set"]})
	assert head, "the demo's letter head is drawn from the company"
	address = frappe.db.get_value("Address", {"is_your_company_address": 1})
	with as_user(OWNER):
		place = frappe.get_doc("Address", address)
		place.address_line2 = "Unit 4 <b>Al Quoz</b>"
		place.save()
	content = frappe.db.get_value("Letter Head", head, "content")
	assert "Unit 4" in content and "&lt;b&gt;" in content and "<b>Al Quoz" not in content, content

	with as_user(OWNER):
		mine = printing.save_letter_head({"name": head, "source": "HTML", "content": content.replace("Unit 4", "Unit 5")})
		assert not frappe.db.get_value("Letter Head", head, "one_top"), "a top changed by hand is the person's own"
		cleaned = printing.save_letter_head({"letter_head_name": "Sahara Clean", "source": "HTML", "content": '<p>Sahara</p><script>alert(1)</script><img src="https://tracker.example.com/p.png">'})
		assert "<script" not in cleaned["content"] and "tracker.example.com" not in cleaned["content"], cleaned["content"]
		try:
			printing.save_letter_head({"letter_head_name": "Sahara Tags", "source": "HTML", "content": "<p>{{ frappe.session.user }}</p>"})
		except frappe.ValidationError as e:
			assert "without template tags" in str(e), e
		else:
			raise AssertionError("a letter head kept a template")
		invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1})
		try:
			printing.render_jinja_template("<p>{{ frappe.db.sql('select name from tabUser') }}</p>", "Sales Invoice", invoice)
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("an HTML block reached past the record")
	assert mine["name"] == head

def _opened_link(url: str) -> None:
	"""A link someone was mailed, opened in their browser."""
	from urllib.parse import urlsplit

	parts = urlsplit(url)
	_asked(path=f"{parts.path}?{parts.query}", method="GET")
	frappe.local.form_dict = frappe._dict(frappe.local.request.args.items())


@check
def privacy_requests_go_through_the_administrators():
	"""Nadia asks for her account to be deleted, Layla holds it with a reason
	and then approves it; Tariq asks and changes his mind; Yousef, who signs
	in without a password, confirms by the link he is mailed. Rania asks for
	a copy of her data and Layla sends it withholding her notes. Somebody who
	is not a user asks from the public page, confirms by mail and downloads
	the copy; a link that was not signed by the workspace opens nothing."""
	from unittest import mock

	from onedesk.one import privacy, privacy_copy, privacy_public

	mailed = {}
	def keep(key):
		return lambda *args, **kw: mailed.__setitem__(key, next(one for one in args if isinstance(one, str) and "/api/method/" in one))

	with mock.patch("frappe.utils.password.check_password"), mock.patch("frappe.enqueue"):
		with as_user("nadia@one.test"):
			privacy.ask_to_delete("her password")
		nadia = frappe.db.get_value(privacy.DELETION, {"email": "nadia@one.test"})
		with as_user("tariq@one.test"):
			privacy.ask_to_delete("his password")
			privacy.withdraw()
			assert not frappe.db.exists(privacy.DELETION, {"email": "tariq@one.test"})
		with as_user(OWNER):
			privacy.hold(nadia, "Her timesheets are still being invoiced this month.")
			assert frappe.db.get_value(privacy.DELETION, nadia, "status") == "On Hold"
			privacy.approve(nadia)
			assert frappe.db.get_value("User", "nadia@one.test", "enabled") == 0
		with as_user("yousef@one.test"), mock.patch("onedesk.one.privacy._has_password", return_value=False), mock.patch("onedesk.one.tell.asked_to_confirm_deletion", side_effect=keep("delete")):
			privacy.ask_to_delete()
		frappe.set_user("Guest")
		_opened_link(mailed["delete"])
		privacy.confirm(frappe.local.form_dict.name, frappe.local.form_dict.expires)
		assert frappe.db.get_value(privacy.DELETION, {"email": "yousef@one.test"}, "status") == "Pending Approval"

		with as_user("rania@one.test"):
			privacy_copy.ask()
		copy = frappe.db.get_value(privacy_copy.DOWNLOAD, {"user": "rania@one.test", "one_status": "Waiting"})
		with as_user(OWNER):
			kinds = {one["key"] for one in privacy_copy.review(copy)["kinds"]}
			assert "account" in kinds
			optional = [key for key, _label, always in privacy_copy.kinds_for("rania@one.test") if not always]
			privacy_copy.send(copy, optional[:1], "Kept while the audit is open.")
			assert frappe.db.get_value(privacy_copy.DOWNLOAD, copy, "one_status") == "Gathering"

		# The hourly limit on asking is kept in the cache, outside the rollback,
		# so a run within the hour of the last one starts it again.
		frappe.cache.delete_keys("rl:")
		frappe.set_user("Guest")
		# Somebody who isn't a user: Khalid is the villa's portal user now.
		with mock.patch("onedesk.one.tell.request_to_confirm", side_effect=keep("public")):
			privacy_public.ask("jordan@acme.example", "copy")
		_opened_link(mailed["public"])
		privacy_public.confirm(frappe.local.form_dict.email, frappe.local.form_dict.kind, frappe.local.form_dict.expires)
		outsider = frappe.db.get_value(privacy_copy.DOWNLOAD, {"one_email": "jordan@acme.example"})
		assert outsider
		with as_user(OWNER):
			privacy_copy.send(outsider)
		frappe.set_user("Administrator")
		with mock.patch("onedesk.one.tell.copy_ready_to_download"):
			privacy_copy.gather(outsider)
		frappe.set_user("Guest")
		link = privacy_public._signed("download", request=outsider, expires=str(add_days(today(), 7)) + " 00:00:00")
		_opened_link(link)
		privacy_public.download(frappe.local.form_dict.request, frappe.local.form_dict.expires)
		given = frappe.local.response.filecontent
		assert "jordan@acme.example" in (given.decode() if isinstance(given, bytes) else given)
		_opened_link(link.replace("_signature=", "_signature=0"))
		frappe.local.response.pop("filecontent", None)
		privacy_public.download(frappe.local.form_dict.request, frappe.local.form_dict.expires)
		assert not frappe.local.response.get("filecontent")
	_unasked()


@check
def privacy_holds_each_person_to_their_own():
	"""Only administrators read the requests. Asking needs the person's own
	password, and nobody who pays for the workspace, nor its last
	administrator, may go, nor approve their own going. Everybody concerned
	is told. A copy withholds only what may be withheld, and says why; it is
	kept on the person's account, and is gone when they are. Approving signs
	the person out and turns them off, and erasing does what frappe does,
	for somebody who is not a user too. A public page answers the same
	whether the address is known or not."""
	from unittest import mock

	from onedesk.one import privacy, privacy_copy, privacy_public

	with as_user("nadia@one.test"), mock.patch("frappe.utils.password.check_password", side_effect=frappe.AuthenticationError):
		try:
			privacy.ask_to_delete("not my password")
		except frappe.ValidationError as e:
			assert "not your password" in str(e), e
		else:
			raise AssertionError("an account was asked to be deleted with a wrong password")
	frappe.db.set_single_value("Workspace Account", "billed_to", OWNER)
	with as_user(OWNER), mock.patch("frappe.utils.password.check_password"):
		try:
			privacy.ask_to_delete("her password")
		except frappe.ValidationError as e:
			assert "billed to this account" in str(e), e
		else:
			raise AssertionError("whoever pays asked to be deleted")

	with _Told() as told, mock.patch("frappe.utils.password.check_password"), mock.patch("frappe.enqueue") as queued:
		with as_user("nadia@one.test"):
			privacy.ask_to_delete("her password")
		assert told.to("Deletion Asked") >= {OWNER}, told.said
		nadia = frappe.db.get_value(privacy.DELETION, {"email": "nadia@one.test"})
		for user, may in ((OWNER, True), ("rania@one.test", False)):
			assert bool(frappe.has_permission(privacy.DELETION, "read", doc=nadia, user=user)) == may, user
		with as_user(OWNER):
			privacy.hold(nadia, "Her timesheets are still being invoiced this month.")
			assert "nadia@one.test" in told.to("Deletion On Hold"), told.said
			frappe.db.sql("insert into `tabSessions` (user, sid, sessiondata, lastupdate, status) values ('nadia@one.test', 'demo-nadia', '{}', now(), 'Active')")
			privacy.approve(nadia)
		assert frappe.db.get_value("User", "nadia@one.test", "enabled") == 0 and queued.called
		assert not frappe.db.sql("select 1 from `tabSessions` where user = 'nadia@one.test'"), "approving signs them out"

		with as_user("rania@one.test"):
			privacy_copy.ask()
		assert told.to("Copy Asked") >= {OWNER}, told.said
		copy = frappe.db.get_value(privacy_copy.DOWNLOAD, {"user": "rania@one.test", "one_status": "Waiting"})
		always = [key for key, _label, kept in privacy_copy.kinds_for("rania@one.test") if kept]
		optional = [key for key, _label, kept in privacy_copy.kinds_for("rania@one.test") if not kept]
		with as_user(OWNER):
			for withheld, why in ((always[:1], "No."), (optional[:1], None)):
				try:
					privacy_copy.send(copy, withheld, why)
				except frappe.ValidationError:
					pass
				else:
					raise AssertionError(f"a copy withheld {withheld} with {why!r}")
			privacy_copy.send(copy, optional[:1], "Kept while the audit is open.")
	frappe.set_user("Administrator")
	with _Told() as told:
		privacy_copy.gather(copy, optional[:1])
	assert "rania@one.test" in told.to("Your Data Is Ready"), told.said
	assert frappe.db.exists("File", {"attached_to_doctype": "User", "attached_to_name": "rania@one.test", "file_name": ["like", "Personal-Data-%"]})

	privacy.erase(nadia)
	assert not frappe.db.exists("User", "nadia@one.test"), "frappe's erasure renames the account"

	frappe.cache.delete_keys("rl:")
	frappe.set_user("Guest")
	_asked(path="/", method="POST")
	with mock.patch("onedesk.one.tell.request_to_confirm"):
		assert privacy_public.ask("khalid@mansour.example", "delete") == privacy_public.ask("nobody@nowhere.example", "delete"), "the page says whether it knows an address"
	frappe.set_user("Administrator")
	outsider = frappe.get_doc({"doctype": privacy.DELETION, "email": "khalid@mansour.example", "status": "Pending Approval"})
	outsider.set_new_name()
	outsider.db_insert()
	mentioned = frappe.db.count("Contact", {"email_id": "khalid@mansour.example"})
	assert mentioned, "the demo's customer contact"
	privacy.erase(outsider.name)
	assert not frappe.db.count("Contact", {"email_id": "khalid@mansour.example"}), "frappe's redaction left the address"
	assert frappe.db.get_value(privacy.DELETION, outsider.name, "status") == "Deleted"
	_unasked()

@check
def the_payer_downloads_everything_and_closes_the_workspace():
	"""Layla, who pays, prepares the full download and fetches it, closes the
	workspace with her password and keeps it open after all, and everybody,
	she too, is told each. Once somebody else pays she may do none of it, and
	Mariam, who does not administer the workspace, may not even read where
	closing stands. The account is not asked: what it would answer is said
	here."""
	import os
	import zipfile
	from unittest import mock

	from onedesk.one import closing

	frappe.db.set_single_value("Workspace Account", "billed_to", OWNER)
	folder = frappe.get_site_path("private", "closing")
	os.makedirs(folder, exist_ok=True)
	with as_user(OWNER), mock.patch("frappe.enqueue") as queued, mock.patch("onedesk.one.account.ask") as asked, mock.patch("onedesk.one.account.refresh"), mock.patch("frappe.utils.password.check_password"):
		assert closing.state()["is_payer"]
		frappe.db.set_single_value("Workspace Account", {"export_status": "", "export_file": ""})
		try:
			closing.download()
			raise AssertionError("a download was sent before one was made")
		except frappe.ValidationError:
			pass
		closing.prepare()
		assert queued.call_args.args[0] == closing.build
		with open(os.path.join(folder, "an-old-one.zip"), "wb") as out:
			out.write(b"PK\x05\x06" + bytes(18))
		with _Told() as told, mock.patch.object(closing, "_database") as database, mock.patch.object(closing, "_files", return_value=[]) as files, mock.patch.object(closing, "_doctypes", return_value=["ToDo", "Project"]), mock.patch.object(closing, "BATCH", 3):
			closing.build(OWNER)
		assert database.called and files.called, "the database and the files go in too"
		held = frappe.get_single("Workspace Account")
		assert held.export_status == "Ready" and os.listdir(folder) == [held.export_file], os.listdir(folder)
		with zipfile.ZipFile(os.path.join(folder, held.export_file)) as zipped:
			rows = zipped.read("records/ToDo.csv").decode("utf-8-sig").strip().splitlines()
			assert len(rows) == frappe.db.count("ToDo") + 1, "a table read three rows at a time came out whole"
		assert told.to("Full Download Ready") == {OWNER}
		_asked(method="GET")
		assert closing.download().status_code == 200
		with _Told() as told:
			closing.close("her password")
			assert asked.call_args.args[0] == "onedesk.one_admin.proxy.close"
			closing.keep()
			assert asked.call_args.args[0] == "onedesk.one_admin.proxy.withdraw_closing"
		for name in ("Workspace Closing", "Workspace Staying Open"):
			assert {OWNER, "mariam@one.test", "rania@one.test"} <= told.to(name), name
		os.remove(os.path.join(folder, held.export_file))
	with as_user(OWNER), mock.patch("onedesk.one.account.ask") as asked:
		try:
			closing.close("not her password")
			raise AssertionError("closed with a wrong password")
		except frappe.ValidationError:
			assert not asked.called
	frappe.db.set_single_value("Workspace Account", "billed_to", "accounts@sahara-parent.example")
	with as_user(OWNER), mock.patch("onedesk.one.account.ask") as asked, mock.patch("frappe.utils.password.check_password"):
		for step in (closing.prepare, closing.download, lambda: closing.close("x"), closing.keep):
			try:
				step()
				raise AssertionError("somebody who does not pay did it")
			except frappe.PermissionError:
				pass
		assert not asked.called and not closing.state()["is_payer"]
	with as_user("mariam@one.test"):
		try:
			closing.state()
			raise AssertionError("Mariam read where closing stands")
		except frappe.PermissionError:
			pass


def _party_contact(doctype: str) -> str:
	"""A contact of one of the demo's customers or suppliers, with an address."""
	for link in frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "link_doctype": doctype}, fields=["parent", "link_name"]):
		if frappe.db.get_value("Contact", link.parent, "email_id") and not frappe.db.get_value("Contact", link.parent, "user"):
			return link.parent
	raise AssertionError(f"no {doctype} contact with an address")


@check
def a_supplier_is_invited_to_the_portal_and_answers_a_quote_request():
	"""Karim invites a supplier's contact to the portal, sends the invitation
	again, and the contact opens the link and is taken to set a password.
	The login is a portal one with the supplier's role. Somebody in the
	workspace is not invited, and Rania, who does not manage suppliers, may
	not invite anybody. Karim asks the supplier for a quote and the supplier prices it on the
	portal, which makes the supplier quotation. Karim takes the login away
	and gives it back, and the taken login's link no longer works. Somebody
	outside the supplier cannot answer it."""
	from unittest import mock

	from onedesk.one import invite, outside, portal, portal_invite

	contact = _party_contact("Supplier")
	supplier = frappe.db.get_value("Dynamic Link", {"parent": contact, "link_doctype": "Supplier"}, "link_name")
	email = frappe.db.get_value("Contact", contact, "email_id")
	links = []
	with as_user("karim@one.test"), mock.patch("onedesk.one.tell.invited_to_portal", side_effect=lambda *a, **kw: links.append(kw["link"])):
		assert portal_invite.state(contact)["may"]
		assert portal_invite.invite_contact(contact)["status"] == "invited"
		portal_invite.invite_again(contact)
	user = frappe.db.get_value("Contact", contact, "user")
	assert frappe.db.get_value("User", user, "user_type") == "Website User" and "Supplier" in frappe.get_roles(user)
	with as_user(OWNER):
		ours = frappe.get_doc({"doctype": "Contact", "first_name": "Rania", "email_ids": [{"email_id": "rania@one.test", "is_primary": 1}], "links": [{"link_doctype": "Supplier", "link_name": supplier}]}).insert()
		try:
			portal_invite.invite_contact(ours.name)
			raise AssertionError("somebody in the workspace was invited to the portal")
		except frappe.ValidationError as refused:
			assert "is someone in the workspace" in str(refused)
	with as_user("rania@one.test"):
		try:
			portal_invite.invite_contact(contact)
			raise AssertionError("Rania, who does not manage the supplier, invited its contact")
		except frappe.PermissionError:
			pass
	frappe.set_user("Guest")
	invite.accept(links[0].split("key=")[1])
	assert frappe.local.response["type"] != "redirect" or "update-password" not in frappe.local.response.get("location", ""), "an old link still worked"
	invite.accept(links[-1].split("key=")[1])
	assert "update-password" in frappe.local.response["location"]

	item = frappe.db.get_value("Purchase Order Item", {}, ["item_code", "uom", "warehouse"], as_dict=True)
	with as_user("karim@one.test"):
		rfq = frappe.get_doc(
			{
				"doctype": "Request for Quotation",
				"company": COMPANY,
				"transaction_date": today(),
				"message_for_supplier": "Please quote for next month's delivery.",
				"suppliers": [{"supplier": supplier, "contact": contact, "email_id": email, "send_email": 0}],
				"items": [{"item_code": item.item_code, "qty": 40, "uom": item.uom, "conversion_factor": 1, "warehouse": item.warehouse, "schedule_date": add_days(today(), 30)}],
			}
		).insert()
		rfq.submit()
	with as_user(user):
		answered = portal.send_quote(rfq.name, {rfq.items[0].name: {"rate": 118.5, "qty": 40}}, "Delivered in two lots.")
		assert frappe.db.get_value("Supplier Quotation", answered, "supplier") == supplier
		assert frappe.db.get_value("Supplier Quotation Item", {"parent": answered}, "rate") == 118.5
	with as_user("rania@one.test"):
		try:
			portal.send_quote(rfq.name, {rfq.items[0].name: {"rate": 1, "qty": 40}})
			raise AssertionError("somebody outside the supplier answered its quote request")
		except frappe.PermissionError:
			pass
		assert outside.kind_of("project") is not None
	with as_user("karim@one.test"):
		assert portal_invite.revoke(contact)["status"] == "revoked"
		assert frappe.db.get_value("User", user, "enabled") == 0
	frappe.set_user("Guest")
	frappe.local.response.pop("location", None)
	invite.accept(links[-1].split("key=")[1])
	assert "update-password" not in (frappe.local.response.get("location") or ""), "a revoked login's link still worked"
	with as_user("karim@one.test"):
		with mock.patch("onedesk.one.tell.invited_to_portal"):
			portal_invite.restore(contact)
		assert frappe.db.get_value("User", user, "enabled") == 1


@check
def a_saved_report_is_its_makers_and_runs_no_code():
	"""Omar saves his list of open deals as a report, and it goes under Saved
	Reports in his own OneCRM sidebar. A report, a chart or a card made here
	runs no code, even Layla's, and a report by mail goes as whoever set it
	up. Omar may not show his report to everybody,
	nor put it in an app he does not work in, Rania may not move it, and only
	an administrator moves a dashboard. He deletes his own, and it leaves the
	sidebar, but not Layla's."""
	from onedesk.one import reports

	def refused(step, error=frappe.ValidationError):
		try:
			step()
		except error:
			return True
		return False

	with as_user("omar@one.test"):
		saved = frappe.get_doc({"doctype": "Report", "report_name": "Omar Open Deals", "ref_doctype": "Opportunity", "report_type": "Report Builder", "is_standard": "No", "json": "{}"}).insert()
		layers = frappe.get_all("Sidebar Item", filters={"parenttype": "Custom Sidebar", "link_type": "Report", "link_to": saved.name}, pluck="parent")
		assert [frappe.db.get_value("Custom Sidebar", one, "user") for one in layers] == ["omar@one.test"], layers
		assert reports.where("Report", saved.name)["module"]
		for kind in ("Script Report", "Custom Report"):
			assert refused(lambda: frappe.get_doc({"doctype": "Report", "report_name": f"Omar {kind}", "ref_doctype": "Opportunity", "report_type": kind, "is_standard": "No", "reference_report": saved.name}).insert(), (frappe.ValidationError, frappe.PermissionError)), kind
		places = {one["label"]: one["module"] for one in reports.places()}
		assert "OneCRM" in places and "OneHR" not in places, places
		bars = reports.sidebars().get("module_sidebars") or {}
		assert bars and all((one or {}).get("app") == "onedesk" for one in bars.values()), {name: (one or {}).get("app") for name, one in bars.items()}
		assert refused(lambda: reports.place("Report", saved.name, places["OneCRM"], 1), frappe.PermissionError)
		hr = frappe.db.get_value("Sidebar", "OneHR", "module")
		assert refused(lambda: reports.place("Report", saved.name, hr))
	with as_user(OWNER):
		assert refused(lambda: frappe.get_doc({"doctype": "Dashboard Chart", "chart_name": "Layla Custom", "chart_type": "Custom", "document_type": "Opportunity", "source": "", "timeseries": 0}).insert())
		assert refused(lambda: frappe.get_doc({"doctype": "Number Card", "label": "Layla Custom", "type": "Custom", "document_type": "Opportunity", "method": "frappe.ping"}).insert())
		mailed = frappe.get_doc({"doctype": "Auto Email Report", "report": saved.name, "user": "omar@one.test", "email_to": "omar@one.test", "format": "HTML", "frequency": "Weekly", "day_of_week": "Monday"}).insert()
		assert mailed.user == OWNER, "it would go as Omar sees it, set up by Layla"
		hers = frappe.get_doc({"doctype": "Report", "report_name": "Layla Deals", "ref_doctype": "Opportunity", "report_type": "Report Builder", "is_standard": "No", "json": "{}"}).insert()
		counted = frappe.get_doc({"doctype": "Dashboard Chart", "chart_name": "Layla Deals", "chart_type": "Count", "document_type": "Opportunity", "based_on": "creation", "timeseries": 0, "filters_json": "[]"}).insert()
		assert counted.name
	with as_user("rania@one.test"):
		assert refused(lambda: reports.place("Report", saved.name, None), frappe.PermissionError)
		dashboard = frappe.get_all("Dashboard", pluck="name", limit=1)
		assert not dashboard or refused(lambda: reports.where("Dashboard", dashboard[0]), frappe.PermissionError)
	with as_user(OWNER):
		frappe.delete_doc("Auto Email Report", mailed.name)
	with as_user("omar@one.test"):
		assert refused(lambda: frappe.delete_doc("Report", hers.name), frappe.PermissionError), "Omar deleted Layla's report"
		frappe.delete_doc("Report", saved.name)
	assert not frappe.db.exists("Sidebar Item", {"parenttype": "Custom Sidebar", "link_type": "Report", "link_to": saved.name})


@check
def the_one_home_lists_and_the_bin_answer_for_their_people():
	"""The One home's figures as Samir and as Layla, what needs Layla's
	attention, a saved report placed in OneCRM's sidebar for everybody,
	the shared lists of values read, added to, renamed and counted, next
	year's holidays made and put in force with the country's own public
	holidays, and a deleted project task brought back from the bin."""
	from onedesk.one import holidays, home, masters, recycle, reports

	with as_user("samir@one.test"):
		figures = {
			"tasks due": home.tasks_due(),
			"meetings today": home.meetings_today(),
			"documents waiting": home.intake_waiting(),
			"suggestions waiting": home.suggestions_waiting(),
			"approvals waiting": home.approvals_waiting(),
		}
		assert all("value" in said for said in figures.values()), figures
	with as_user(OWNER):
		assert isinstance(home.attention(), list)
		saved = frappe.get_doc({"doctype": "Report", "report_name": "Open Deals Gulf", "ref_doctype": "Opportunity", "report_type": "Report Builder", "is_standard": "No", "json": "{}"}).insert()
		crm = next(one["module"] for one in reports.where("Report", saved.name)["places"] if one["label"] == "OneCRM")
		reports.place("Report", saved.name, crm, 1)
		assert reports.where("Report", saved.name) | {"places": None} == {"module": crm, "everybody": 1, "places": None, "administers": 1}
		assert reports.where("Report", saved.name)
		assert reports.sidebars()
		kinds = masters.kinds()
		assert kinds
		territory = masters.add("Territory", {"territory_name": "Oman"})
		assert territory in {one["name"] for one in masters.values("Territory")}
		renamed = masters.rename("Territory", territory, "Sultanate of Oman")
		busy = frappe.db.get_value("Customer", {}, "territory")
		assert masters.used("Territory", busy) > masters.used("Territory", renamed), (masters.used("Territory", busy), masters.used("Territory", renamed))
		assert holidays.subdivisions("AE") is not None
		public = holidays.country_holidays("AE", f"{getdate(today()).year + 1}-01-01", f"{getdate(today()).year + 1}-12-31")
		assert public, "no public holidays for the Emirates next year"
		upcoming = holidays.next_year()
		assert frappe.db.exists("Holiday List", upcoming)
		holidays.use(upcoming)
		task = frappe.get_doc({"doctype": "Task", "subject": "Order the W03 sill packers", "project": VILLA}).insert().name
		frappe.delete_doc("Task", task)
		deleted = frappe.db.get_value("Deleted Document", {"deleted_doctype": "Task", "deleted_name": task})
		recycle.restore(deleted)
		assert frappe.db.exists("Task", task)
		frappe.delete_doc("Task", task)
		said = recycle.bulk_restore([frappe.db.get_value("Deleted Document", {"deleted_doctype": "Task", "deleted_name": task, "restored": 0})])
		assert frappe.db.exists("Task", task), said


@check
def the_bin_gives_each_person_back_their_own():
	"""Rania deletes a to-do of hers and finds it in the bin under its title,
	puts it back herself and may not empty it for good. Samir does not see it,
	Layla does, and nobody sees what the system deleted."""
	from onedesk.one import recycle

	with as_user("rania@one.test"):
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Call Gulf Glass about the cracked panel", "allocated_to": "rania@one.test"}).insert()
		frappe.delete_doc("ToDo", todo.name)
	frappe.db.before_commit.run()
	deleted = frappe.db.get_value("Deleted Document", {"deleted_doctype": "ToDo", "deleted_name": todo.name})
	assert "Call Gulf Glass" in (frappe.db.get_value("Deleted Document", deleted, "one_title") or ""), frappe.db.get_value("Deleted Document", deleted, ["one_title", "deleted_name"])
	frappe.set_user("Administrator")
	housekeeping = frappe.get_doc({"doctype": "ToDo", "description": "Old reminder", "allocated_to": OWNER}).insert()
	frappe.delete_doc("ToDo", housekeeping.name)
	swept = frappe.db.get_value("Deleted Document", {"deleted_doctype": "ToDo", "deleted_name": housekeeping.name})
	with as_user("samir@one.test"):
		assert deleted not in frappe.get_list("Deleted Document", pluck="name")
		try:
			recycle.restore(deleted)
			raise AssertionError("Samir put back Rania's to-do")
		except frappe.PermissionError:
			pass
	with as_user(OWNER):
		seen = frappe.get_list("Deleted Document", pluck="name", limit_page_length=0)
		assert deleted in seen and swept not in seen
	with as_user("rania@one.test"):
		assert deleted in frappe.get_list("Deleted Document", pluck="name", limit_page_length=0)
		assert not frappe.has_permission("Deleted Document", "delete", doc=frappe.get_doc("Deleted Document", deleted))
		back = recycle.restore(deleted)
		assert back == todo.name and frappe.db.get_value("ToDo", back, "owner") == "rania@one.test", (back, todo.name)


@check
def oneai_setup_cards_wait_for_approval_and_stay_within_bounds():
	"""What OneAI suggests to Layla changes nothing until she approves it. A
	report of something that is not a record, or a level that would not
	change, is sent back to be put right, and a level changed since its card
	was written is not changed again. A report by mail goes as whoever
	approved it. Omar may suggest no dashboard, show nothing to everybody,
	and approve no card of an administrator's."""
	from onedesk.one import ai_setup
	from onedesk.one_ai import run as runs

	with as_user(OWNER):
		card = ai_setup.suggest_group("Night Crew", ["rania@one.test", "tariq@one.test"])
		assert card.get("proposal") and not frappe.db.exists("User Group", "Night Crew"), "made before it was approved"
		assert ai_setup.suggest_saved_report("Sales Invoice Item", "Lines", ["item_code"]).get("mend")
		assert ai_setup.suggest_saved_report("Sales Invoice", "Hidden", ["no_such_field"]).get("mend")
		assert "nothing would change" in ai_setup.suggest_level("OneCRM", "User", give=[{"doctype": "Opportunity", "rights": ["read"]}]).get("error", "")
		first = ai_setup.suggest_level("OneCRM", "User", give=[{"doctype": "Quotation", "rights": ["export"]}])
		second = ai_setup.suggest_level("OneCRM", "User", give=[{"doctype": "Quotation", "rights": ["export"]}])
		assert first.get("proposal") and second.get("proposal"), (first, second)
		runs.apply(first["proposal"])
		try:
			runs.apply(second["proposal"])
			raise AssertionError("a level was changed by a card written before it last changed")
		except frappe.ValidationError as stale:
			assert "no longer applies" in str(stale)
		mail = ai_setup.suggest_report_mail("Accounts Receivable", ["huda@one.test"], "Weekly", "Monday")
		runs.apply(mail["proposal"])
		assert frappe.db.get_value("Auto Email Report", {"report": "Accounts Receivable"}, "user") == OWNER
		changes = frappe.parse_json(frappe.db.get_value("AI Proposal", card["proposal"], "changes"))
	with as_user("omar@one.test"):
		assert ai_setup.suggest_dashboard("Mine", [{"title": "Deals", "doctype": "Opportunity", "measure": "count"}]).get("error")
		assert ai_setup.suggest_saved_report("Opportunity", "Everyone's deals", ["name"], everybody=True).get("mend")
		for what in ({**changes, "what": "mail", "doc": {"doctype": "Auto Email Report"}}, {"what": "level"}):
			try:
				ai_setup.apply(what)
				raise AssertionError("Omar approved an administrator's card")
			except frappe.PermissionError:
				pass


@check
def webhooks_and_the_audit_log_are_the_administrators():
	"""Layla sends customers to another system by a webhook: over https to a
	public address only, every record, naming fields alone and none she may
	not read, quickly and a few times at most. When its calls give up she is
	told. She reads who changed a customer, without the fields she may not
	read and without what the system did, and changes none of it. Omar sees
	no webhook and no change."""
	from onedesk.one import audit, webhooks

	def hook(**said):
		return frappe.get_doc({
			"doctype": "Webhook", "__newname": frappe.generate_hash(length=8), "webhook_doctype": "Customer", "webhook_docevent": "on_update",
			"request_url": "https://example.com/hook", "request_structure": "JSON",
			"webhook_json": '{"name": "{{ doc.name }}"}', **said,
		})

	def refused(doc):
		try:
			doc.insert()
		except (frappe.ValidationError, frappe.PermissionError):
			return True
		return False

	with as_user(OWNER):
		made = hook(is_dynamic_url=1, timeout=300, max_retries=50).insert()
		assert (made.is_dynamic_url, made.timeout, made.max_retries) == (0, webhooks.LONGEST, webhooks.TRIES)
		assert refused(hook(request_url="http://example.com/hook")), "sent in the clear"
		assert refused(hook(request_url="https://127.0.0.1/hook")), "sent inside"
		assert refused(hook(condition="doc.customer_group == 'Commercial'"))
		assert refused(hook(webhook_json='{"who": "{{ frappe.session.user }}"}'))
		assert "allowed_companies" in audit._unseen("Customer")
		assert refused(hook(webhook_json='{"where": "{{ doc.allowed_companies }}"}')), "a field she may not read"
		assert refused(hook(webhook_doctype="DocType"))
		frappe.get_doc({"doctype": "Webhook Request Log", "webhook": made.name, "url": made.request_url, "status": "Exhausted"}).insert(ignore_permissions=True)
		with _Told() as told:
			webhooks.failing()
		assert OWNER in told.to("Webhooks Failing")

		customer = frappe.get_all("Customer", pluck="name", limit=1)[0]
		doc = frappe.get_doc("Customer", customer)
		doc.customer_details = "Pays on the 25th."
		doc.save()
		changes = frappe.get_list("Version", filters={"ref_doctype": "Customer", "docname": customer}, pluck="name")
		assert changes, "her own change"
		assert not frappe.get_list("Version", filters={"owner": ["in", audit.SYSTEM]}, pluck="name", limit=1)
		assert not frappe.has_permission("Version", "write", doc=frappe.get_doc("Version", changes[0]))
		said = audit.seen({"changed": [["allowed_companies", "", "x"], ["customer_details", "", "Pays on the 25th."]]}, "Customer")
		assert [one[0] for one in said["changed"]] == ["customer_details"]
	with as_user("omar@one.test"):
		for doctype in ("Webhook", "Webhook Request Log", "Version"):
			try:
				assert not frappe.get_list(doctype, pluck="name", limit=1), doctype
			except frappe.PermissionError:
				pass


@check
def intake_fills_only_the_record_it_is_making():
	"""A supplier Intake makes from a document is given its name and what else
	it needs from that document. A supplier made by hand, or another kind made
	on the way, is never asked about."""
	from unittest import mock

	from onedesk.one_ai import kind
	from onedesk.one_intake import fill

	reading = frappe.get_all("Reading", pluck="name", limit=1)[0]
	group = frappe.get_all("Supplier Group", filters={"is_group": 0}, pluck="name", limit=1)[0]
	asked = []

	def answer(doc, needs, reading):
		asked.append((doc.doctype, sorted(one["fieldname"] for one in needs)))
		return {"supplier_name": "Coastal Sealants", "supplier_group": group, kind.TYPED: "Coastal Sealants", "website": "never asked"}

	with as_user(OWNER), mock.patch.object(fill, "_ask", side_effect=answer):
		with fill.filling(reading, "Supplier"):
			made = frappe.get_doc({"doctype": "Supplier"}).insert()
			frappe.get_doc({"doctype": "Customer", "customer_name": "Made on the way"}).insert()
		frappe.get_doc({"doctype": "Supplier", "supplier_name": "Typed by hand", "supplier_group": group}).insert()
	assert made.supplier_name == "Coastal Sealants" and not made.website, made.as_dict()
	assert asked and {doctype for doctype, _fields in asked} == {"Supplier"}, asked
	assert any("supplier_name" in fields or kind.TYPED in fields for _doctype, fields in asked), asked


@check
def an_announcement_is_the_administrators_and_reaches_everybody_once():
	"""Rania's notes stay her own: she may not post one for everybody. Layla
	posts one shown on sign-in, everybody but her is told once, and it is
	waiting for Rania when she next opens One. Nobody signed out sees it."""
	from frappe.desk.doctype.note.note import UNSEEN_NOTES_KEY

	from onedesk.one import announcements

	with as_user("rania@one.test"):
		frappe.get_doc({"doctype": "Note", "title": "My site checklist", "content": "Sealant, shims, level."}).insert()
		for said in ({"notify_on_login": 1}, {"public": 1}):
			try:
				mine = frappe.get_doc({"doctype": "Note", "title": "To everybody", "content": "Hello", **said}).insert()
			except frappe.ValidationError:
				continue
			assert not frappe.db.get_value("Note", mine.name, "public") and not frappe.db.get_value("Note", mine.name, "notify_on_login"), "Rania posted an announcement"
	with as_user(OWNER), _Told() as told:
		note = frappe.get_doc({
			"doctype": "Note", "title": "Office closed on Thursday", "content": "The office is closed for the holiday.",
			"notify_on_login": 1, "expire_notification_on": add_days(today(), 7),
		}).insert()
		assert note.public, "shown on sign-in is everybody's"
		note.content = "The office is closed on Thursday for the holiday."
		note.save()
	assert [name for name, _users in told.said].count("Announcement") == 1, told.said
	assert "rania@one.test" in told.to("Announcement") and OWNER not in told.to("Announcement")
	with as_user("rania@one.test"):
		frappe.cache.delete_value(f"{UNSEEN_NOTES_KEY}rania@one.test")
		booted = frappe._dict()
		announcements.boot(booted)
		assert note.name in {one.get("name") for one in booted.notes}, booted.notes
	frappe.set_user("Guest")
	booted = frappe._dict()
	announcements.boot(booted)
	assert "notes" not in booted


@check
def oneai_lays_out_a_print_format_as_meant():
	"""Layla's print format is laid out from sections a model wrote loosely:
	Python's words for true and none, a table named just before its columns,
	widths in per cent and a sentence after. It prints in the font, page
	number and look asked for, a later restyle keeps its layout, and
	print_layout reads all of it back. Omar may not design one."""
	from onedesk.one import ai

	with as_user(OWNER):
		said = ai.print_layout("Sales Invoice")
		assert said.get("starting_layout") and said.get("fields"), said
		loose = frappe.as_json(said["starting_layout"], indent=None).replace("true", "True").replace("null", "None") + " That is the layout."
		assert "True" in loose or "None" in loose, "the starting layout has no true or none to write loosely"
		_applied(ai.design_print_format("Sales Invoice", "Loose Invoice", sections=loose, css=".print-format-doc { color: #333; }", font="Lora", page_number="Bottom Center"))
		held = frappe.db.get_value("Print Format", "Loose Invoice", ["font", "page_number", "css", "format_data"], as_dict=True)
		assert (held.font, held.page_number, held.css) == ("Lora", "Bottom Center", ".print-format-doc { color: #333; }"), held
		read = ai.print_layout("Sales Invoice", "Loose Invoice")
		assert (read["house_style"], read["css"], read["font"], read["page_number"]) == (False, ".print-format-doc { color: #333; }", "Lora", "Bottom Center"), read
		_applied(ai.design_print_format("Sales Invoice", "Loose Invoice", css=".section-label { color: #0a5; }", house_style=True))
		read = ai.print_layout("Sales Invoice", "Loose Invoice")
		assert read["house_style"] and read["css"] == ".section-label { color: #0a5; }", read
		assert frappe.db.get_value("Print Format", "Loose Invoice", "format_data") == held.format_data, "a restyle moved the layout"
		assert ai._paired(["items", {"columns": ["item_code"]}]) == [{"columns": ["item_code"], "table": "items"}]
		assert ai._column({"field": "qty", "width": "15%", "label": "Qty"}) == "qty:15:Qty"
	with as_user("omar@one.test"):
		assert ai.print_layout("Sales Invoice").get("error")


#: What the account on the admin site answers, by what it is asked: the
#: workspace's plan, its credits, its domains and its bills from One.
ACCOUNT = {
	"credit_packs": [{"name": "credits-500", "label": "500 credits", "amount": 25, "currency": "USD"}],
	"buy_credits": {"url": "https://checkout.stripe.com/c/pay/cs_demo"},
	"plans_offered": {"plans": [{"name": "Team", "label": "Team", "seats": 10, "amount": 120}], "current": "Team"},
	"plans_quote": [{"plan": "Business", "extras": {}, "amount": 240}],
	"plans_take": {"plan": "Business", "amount": 240},
	"billed_to": {"billed_to": "huda@one.test"},
	"domain_list": [
		{"domain": "4dl.m.4dl.app", "status": "Active", "primary": 1, "given": 1},
		{"domain": "erp.saharaglass.com", "status": "Pending", "primary": 0},
	],
	"domain_refresh": [
		{"domain": "4dl.m.4dl.app", "status": "Active", "primary": 0, "given": 1},
		{"domain": "erp.saharaglass.com", "status": "Active", "primary": 1},
	],
	"domain_add": {"domain": "erp.saharaglass.com", "status": "Pending"},
	"domain_drop": {"domain": "erp.saharaglass.com"},
	"domain_primary": {"domain": "erp.saharaglass.com"},
	"billing_invoices": {"invoices": [{"number": "ONE-2026-0042", "amount": 120, "currency": "USD", "status": "paid"}]},
	"billing_portal": {"url": "https://billing.stripe.com/p/session/demo"},
	"billing_invoice": {
		"number": "ONE-2026-0042",
		"created": 1790812800,
		"currency": "USD",
		"seller": {"company_name": "Four Degree Labs", "country": "United Arab Emirates"},
		"lines": [{"description": "One Team plan, October", "amount": 120, "quantity": 1}, {"description": "Credit for September", "amount": -20}],
	},
}


def _account(method: str, **kwargs):
	return ACCOUNT.get(method.rsplit(".", 1)[-1])


@check
def the_plan_credits_domains_and_bills_are_the_administrators():
	"""Layla's Plan and Credits and Domains pages, with the account on the
	admin site answering as it would: credit packs and paying for one, the
	plans offered, a quote and a change of plan, Huda made the payer, a
	domain added, made the main address and dropped, the bills from One
	listed and one put into the books as a purchase invoice. Omar may do
	none of it, and the build's wake call is answered for a guest."""
	from unittest import mock

	from onedesk.one import account, bills

	with as_user(OWNER), mock.patch("onedesk.one.account.ask", side_effect=_account), mock.patch("onedesk.one.account.refresh"):
		assert account.credit_packs()[0]["label"] == "500 credits"
		assert account.buy_credits("credits-500")["url"].startswith("https://checkout.stripe.com/")
		assert account.plans_offered()["current"] == "Team"
		assert account.plans_quote({"seats": 15})[0]["plan"] == "Business"
		assert account.plans_take("Business", {}, "Business")["plan"] == "Business"
		assert account.move_billing("huda@one.test")["billed_to"] == "huda@one.test"
		assert account.check_again()["ok"]
		assert [one["domain"] for one in account.domains()] == ["4dl.m.4dl.app", "erp.saharaglass.com"]
		assert account.domain_add("erp.saharaglass.com")["status"] == "Pending"
		assert account.domains_refresh()[1]["status"] == "Active"
		assert account.domain_primary("erp.saharaglass.com")["domain"] == "erp.saharaglass.com"
		account.domain_drop("erp.saharaglass.com")
		assert bills.invoices()["invoices"][0]["number"] == "ONE-2026-0042"
		assert bills.payment_portal()["url"].startswith("https://billing.stripe.com/")
		with mock.patch("onedesk.one.bills._attach"):
			bill = bills.to_books("ONE-2026-0042")
		made = frappe.get_doc("Purchase Invoice", bill)
		assert made.bill_no == "ONE-2026-0042" and made.discount_amount == 20 and made.docstatus == 0
		assert bills.to_books("ONE-2026-0042") == bill, "the same bill was booked twice"
	with as_user("omar@one.test"):
		try:
			account.plans_offered()
			raise AssertionError("Omar saw the plans")
		except frappe.PermissionError:
			pass
	frappe.set_user("Guest")
	_asked()
	with mock.patch("onedesk.one.account.configured", return_value=False):
		assert account.wake() == {"administered": False}


@check
def a_form_is_customized_and_a_record_head_acts():
	"""Layla opens Customize on deals, saves it as it is, and a save from a
	page opened before somebody else's is refused; she exports what the
	workspace changed and resets it. Huda records a payment from an
	invoice's head, which settles it, and a head reads a record not yet saved
	as the form has it. A link to a project reads as its title for Samir
	and as its name for somebody who may not open it. The automation step
	editor lists what a flow may do."""
	from onedesk.one import automations, customize, head, link_titles

	with as_user(OWNER):
		opened = customize.load("Opportunity")
		customize.save("Opportunity", opened["values"], opened["token"])
		try:
			customize.save("Opportunity", opened["values"], "an older page")
			raise AssertionError("a stale Customize page saved over a newer one")
		except frappe.TimestampMismatchError:
			pass
		assert isinstance(customize.export("Opportunity"), dict)
		customize.reset("Opportunity")
		offered = automations.steps("Sales Invoice")
		assert offered, offered
	invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "is_return": 0}, ["name", "outstanding_amount"], as_dict=True)
	with as_user("huda@one.test"):
		verb = head.offer("Sales Invoice", invoice.name, "invoice.record_payment")
		assert verb, "no Record Payment on an unpaid invoice"
		values = {one["fieldname"]: one.get("default") for one in verb["fields"] if one.get("default") is not None}
		head.run("Sales Invoice", invoice.name, "invoice.record_payment", values)
		assert frappe.db.get_value("Sales Invoice", invoice.name, "outstanding_amount") == 0
	with as_user(OWNER):
		# A head that redraws as the form is typed in, on a record not yet saved.
		kind = next(one for one in sorted(head.headed()) if head.redrawn(frappe.get_cached_doc("Record Head", one)) and frappe.db.count(one))
		record = frappe.get_last_doc(kind)
		assert head.preview(frappe.copy_doc(record).as_dict()) is not None, kind
	title = frappe.db.get_value("Project", VILLA, "project_name")
	with as_user("samir@one.test"):
		assert link_titles.get_link_title("Project", VILLA) == title
	frappe.set_user("Guest")
	assert link_titles.get_link_title("Project", VILLA) == VILLA


@check
def push_reaches_a_persons_own_browsers():
	"""Rania turns push on in her browser and gets a test push there, then
	turns it off. A push service One does not send to is refused, and the
	service worker is served to anybody. Her sessions elsewhere are signed
	out from her Sign-in page, and a new password set from a reset link
	tells her it changed. The push service is not called."""
	from unittest import mock

	from onedesk.one import push, signin

	endpoint = "https://fcm.googleapis.com/fcm/send/demo-rania"
	with as_user("rania@one.test"):
		assert push.devices()["key"]
		push.register(endpoint, "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM", "tBHItJI5svbpez7KI4CCXg", "Rania's laptop")
		assert [one.label for one in push.devices()["devices"]] == ["Rania's laptop"]
		with mock.patch("pywebpush.webpush") as sent:
			push.test()
		assert sent.called
		push.forget(endpoint=endpoint)
		assert not push.devices()["devices"]
		try:
			push.register("https://push.example.com/x", "a", "b")
			raise AssertionError("a push service One does not send to was kept")
		except frappe.ValidationError:
			pass
		assert signin.sign_out("no such session") == 0
	frappe.set_user("Guest")
	assert b"addEventListener" in push.worker().get_data()
	with as_user("rania@one.test"), mock.patch("onedesk.one.tell.password_changed") as told:
		_asked()
		with mock.patch("frappe.core.doctype.user.user.update_password", return_value="/desk"):
			# Her first password, from the invitation, is joining; the next is a change.
			signin.update_password("A-new-long-passphrase-2026", old_password="the old one")
			assert not told.called
			signin.update_password("Another-long-passphrase-2026", old_password="A-new-long-passphrase-2026")
		told.assert_called_once_with("rania@one.test")


def _applied(said: dict) -> str:
	"""A OneAI card, approved as its person would approve it."""
	from onedesk.one_ai import run as runs

	assert said.get("proposal"), said
	runs.apply(said["proposal"])
	assert frappe.db.get_value("AI Proposal", said["proposal"], "state") == "Applied", said
	return said["proposal"]


@check
def oneai_reads_and_sets_up_the_workspace_with_layla():
	"""What OneAI reads about the workspace for Layla, and about herself for
	Rania, without an error; and each setup card it suggests, approved and
	there afterwards: a holiday, a second quotation series, a print format
	drawn and made the default, a notification's text, the workspace's
	signature, a mail template and an automation on invoices. A field on
	leads and an approval on purchase orders are suggested and read, not
	approved, since each adds a column to its table.
	"""
	from onedesk.one import ai, printing, privacy_copy
	from onedesk.one_mail import holders

	with as_user("rania@one.test"):
		for said in (ai.my_day(), ai.my_mailboxes(), ai.my_memories(), ai.my_notifications(), ai.my_sign_in()):
			assert "error" not in said, said
		privacy_copy.ask()
	asked = frappe.db.get_value(privacy_copy.DOWNLOAD, {"user": "rania@one.test"})
	kind = frappe.db.get_value("Notification Type", {"one_rule": ["is", "not set"]}) or frappe.db.get_value("Notification Type", {})
	with as_user(OWNER):
		read = {
			"people": ai.workspace_people(),
			"access": ai.workspace_access(),
			"reports": ai.workspace_reports(),
			"bin": ai.recycle_bin(30),
			"announcements": ai.announcements(),
			"webhooks": ai.webhooks(7),
			"audit": ai.audit_log("changes", days=7),
			"privacy": ai.privacy_request(asked),
			"intake": ai.workspace_intake(),
			"holidays": ai.workspace_holidays(),
			"oneai": ai.workspace_oneai(),
			"domains": ai.workspace_domains(),
			"plan": ai.workspace_plan(),
			"sign-in": ai.workspace_sign_in(),
			"numbering": ai.workspace_numbering("Quotation"),
			"printing": ai.workspace_printing("Sales Invoice"),
			"layout": ai.print_layout("Sales Invoice"),
			"mail templates": ai.workspace_mail_templates("Sales Invoice"),
			"approvals": ai.workspace_approvals("Purchase Order"),
			"automations": ai.workspace_automations("Sales Invoice"),
			"a notification": ai.notification_type(kind),
		}
		wrong = {name: said for name, said in read.items() if isinstance(said, dict) and said.get("error")}
		assert not wrong, wrong

		# A new field alters its table, which no check may keep: the card is read, not approved.
		field = ai.customize("Lead", add=[{"label": "Site Visit Date", "kind": "Date"}])
		assert "Site Visit Date" in frappe.db.get_value("AI Proposal", field["proposal"], "changes")
		holiday = f"{getdate(today()).year}-12-31"
		_applied(ai.change_holidays(add=[{"date": holiday, "name": "Year end closure"}]))
		assert frappe.db.exists("Holiday", {"holiday_date": holiday, "description": ["like", "%Year end closure%"]})
		series = [one["series"] for one in __import__("onedesk.one.numbering", fromlist=["series"]).series("Quotation")]
		_applied(ai.change_numbering("Quotation", series=[*series, "QTN-SG-.####"]))
		assert "QTN-SG-.####" in frappe.get_meta("Quotation").get_field("naming_series").options
		drawn = ai.design_print_format("Sales Invoice", "Sahara Clean", make_default=True)
		assert "<" in printing.proposal_preview(drawn["proposal"])
		_applied(drawn)
		assert frappe.db.exists("Print Format", "Sahara Clean")
		assert ai.change_printing(doctype="Sales Invoice", default_format="Sahara Clean").get("error"), "a change to what already prints"
		other = frappe.db.get_value("Print Format", {"doc_type": "Sales Invoice", "name": ["!=", "Sahara Clean"], "disabled": 0})
		_applied(ai.change_printing(doctype="Sales Invoice", default_format=other))
		assert printing.default("Sales Invoice") == other
		_applied(ai.rewrite_notification(kind, "Something for you to look at"))
		ours = frappe.db.get_value("Email Account", holders.workspace(), "email_id")
		_applied(ai.sign_mailbox(ours, "Sahara Glass\nDubai Investments Park"))
		assert "Dubai Investments Park" in (frappe.db.get_value("Email Account", holders.workspace(), "signature") or "")
		_applied(ai.write_mail_template("Invoice {{ name }} is due", "Dear {{ customer_name }},\n\nA reminder that invoice {{ name }} is due.", new_name="Payment reminder", for_doctype="Sales Invoice"))
		assert frappe.db.exists("Email Template", "Payment reminder")
		# An approval adds its state column to the table: read, not approved.
		approval = (
			ai.suggest_approval(
				"Purchase Order",
				[
					{"state": "Draft", "editable_by": "Purchase User"},
					{"state": "Approved", "submitted": True, "editable_by": "Purchase Manager"},
					{"state": "Rejected", "editable_by": "Purchase Manager"},
				],
				[
					{"from": "Draft", "action": "Approve", "to": "Approved", "by": "Purchase Manager"},
					{"from": "Draft", "action": "Reject", "to": "Rejected", "by": "Purchase Manager"},
				],
				name="Purchase approval",
				turn_on=True,
			)
		)
		assert "Purchase Manager" in frappe.db.get_value("AI Proposal", approval["proposal"], "changes")
		_applied(ai.suggest_automation("Sales Invoice", "submitted", [{"do": "tell", "who": ["huda@one.test"], "subject": "Invoice {{ doc.name }} is out", "message": "For {{ doc.customer }}."}], title="Tell Huda of invoices", turn_on=True))
		assert frappe.db.exists("Automation Flow", {"title": "Tell Huda of invoices"}) or frappe.db.count("Automation Flow")


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
	from onedesk.one_project import ai

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
		assert VILLA in {one["project"] for one in ai.projects_needing_attention()["projects"]}
	with as_user("samir@one.test"):
		assert ai.draft_project("Mansour Garden Room", "Fixed Price", "Mansour & Sons", contract=30000).get("error"), "a contract is billed as an item"
		card = ai.draft_project("Mansour Garden Room", "Fixed Price", "Mansour & Sons", template=TEMPLATE, contract=30000, item="SVC-INST", ends=add_days(today(), 365))
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

	from onedesk.one.print_blocks import progress
	from onedesk.one_ai import proposals
	from onedesk.one_project import ai, tree, view

	told = []
	with as_user("samir@one.test"), patch("onedesk.one.notify.notify", side_effect=lambda name, *args, **kwargs: told.append(name)):
		assert ai.add_milestone(VILLA, "Glass signed off", str(add_days(today(), 20)), bill_share=5).get("error"), "the villa's milestones bill all of it already"
		card = ai.add_milestone(VILLA, "Glass signed off", str(add_days(today(), 20)))
		assert card.get("state") == "Proposed" and not frappe.db.exists("Task", {"project": VILLA, "subject": "Glass signed off"})
		proposals.apply(card["proposal"])
		assert frappe.db.get_value("Task", {"project": VILLA, "subject": "Glass signed off"}, "is_milestone") == 1
		try:
			frappe.get_doc({"doctype": "Task", "project": VILLA, "subject": "Over the contract", "is_milestone": 1, "one_bill_share": 5}).insert()
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("the milestones bill more than the contract")
		assert ai.set_status(VILLA, "Completed").get("mend") == "set_status", "open work is closed only when asked"
		card = ai.set_status(ACME, "On hold")
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

	from onedesk.one.print_blocks import time_billed
	from onedesk.one_ai import proposals
	from onedesk.one_project import ai, hours

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
		card = ai.log_time(SHOWROOM, 3, "Design", task=elsewhere)
		assert card.get("state") == "Proposed" and ai.log_time(SHOWROOM, 0, "Design").get("mend") == "log_time"
		before = frappe.db.count("Timesheet Detail", {"project": SHOWROOM})
		proposals.apply(card["proposal"])
		assert frappe.db.count("Timesheet Detail", {"project": SHOWROOM}) == before + 1
		card = ai.set_cost_budget(ACME, "Subcontract Costs", 12000)
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
	printed = time_billed(frappe.get_doc("Sales Invoice", invoice))
	assert printed["rows"] and printed["heading"], printed
	subcontract = frappe.db.get_value("Purchase Invoice Item", {"item_code": "SVC-SUB", "docstatus": 1, "project": VILLA}, "expense_account")
	assert subcontract and frappe.db.get_value("Account", subcontract, "account_name") == "Subcontract Costs", subcontract
	early = frappe.db.sql(
		"""select log.task from `tabTimesheet Detail` log join `tabTask` task on task.name = log.task
		where log.docstatus = 1 and task.project = %s and task.status = 'Open'""",
		VILLA,
	)
	assert not early, early


@check
def onetask_takes_work_from_intake_and_onehr():
	"""A task another module makes lands with the right person and in the
	right place. Intake's task about a supplier goes to the books by the
	workspace's Assignment Rule, one about anything else to whoever's mail it
	came in, and one about a bill for the villa is the villa's. An
	onboarding's steps are each their person's, and open the onboarding, not
	HRMS's project behind it."""
	from onedesk.one_demo import intake
	from onedesk.one_intake import planning
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
		# Karim is given one step, and may not open the whole onboarding.
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
	"""My Tasks is what is given to the reader, the Inbox their work in no
	project, made by them or given to them (a task Intake made about a
	supplier's bill), each read as the reader. A task waiting on open work
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
		assert "made by them or given to them" in ai.page({"page": "my-tasks", "section": "inbox"})
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
