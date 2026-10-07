"""The integration suite: the demo workspace read back as the people in it.

    bench --site <site> execute onedesk.one_demo.check.run
"""

import traceback

import frappe
from frappe.utils import add_days, flt, getdate, today

from onedesk.one_demo.base import COMPANY, as_user, on, wh
from onedesk.one_demo.people import OWNER, PEOPLE

CHECKS = []


def check(fn):
	CHECKS.append(fn)
	return fn


def run(only: str | None = None) -> int:
	failed = []
	for fn in CHECKS:
		if only and fn.__name__ != only:
			continue
		try:
			fn()
			print(f"ok    {fn.__name__}")
		except Exception as e:
			failed.append(fn.__name__)
			# A bare assert says nothing; the line it stopped on says which.
			said = str(e) or f"line {traceback.extract_tb(e.__traceback__)[-1].lineno}"
			print(f"FAIL  {fn.__name__}: {type(e).__name__} {said[:600]}")
		finally:
			frappe.db.rollback()
			frappe.set_user("Administrator")
	print(f"{len(CHECKS) - len(failed)} of {len(CHECKS)} passed" if not only else "")
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

	project = _projects()[0].name
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
		for label, figures, doctype, child in (
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
			assert "Only the books set a budget" in str(e), e
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
def every_intake_sample_makes_what_it_should():
	"""Each mail and file in tests/samples/intake, arriving as it would, makes
	the records its sample says, and nothing is kept."""
	from onedesk.one_demo import samples

	wrong = {}
	for path in samples.samples():
		frappe.db.savepoint("sample")
		try:
			missing = samples.unmet(path, samples.handle(path))
		except Exception as e:
			missing = [repr(e)[:300]]
		finally:
			frappe.db.rollback(save_point="sample")
			frappe.set_user("Administrator")
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
	from onedesk.one_project import kinds, library, template_view, templates
	from onedesk.one_demo.projects import TEMPLATE

	with as_user("samir@one.test"):
		said = template_view.read(TEMPLATE)
		assert sum(1 for one in said["tasks"] if not one["is_group"]) == 25, said["tasks"]
		assert all(one["is_milestone"] for one in said["tasks"] if one["is_group"])
		assert said["used"] >= 1 and said["can_write"]
		first, phase = said["tasks"][1]["name"], said["tasks"][0]["name"]
		template_view.change(TEMPLATE, first, "duration", 4)
		made = template_view.add(TEMPLATE, "Check the anchors", phase)
		template_view.wait(TEMPLATE, made, first, 1)
		template_view.nest(TEMPLATE, made, None)
		after = {one["name"]: one for one in template_view.read(TEMPLATE)["tasks"]}
		assert after[first]["duration"] == 4 and after[made]["depth"] == 0 and after[made]["waits"] == [first]
		template_view.remove(TEMPLATE, made)
		assert made not in {one["name"] for one in template_view.read(TEMPLATE)["tasks"]}

		copied = library.copy("website")
		assert library.copy("website") == copied, "the second use takes the same copy"
		name = kinds.make({"kind": "Internal", "title": "Our Summer Event", "starts": today(), "library": "event", "time": "Not Tracked"})
		assert frappe.db.count("Task", {"project": name}) == 20, "an Event's 15 tasks and its 5 phases"
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
	as cards."""
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
	with as_user(OWNER):
		ready.fix("depreciation")


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

		assert not frappe.db.get_value("Lead", priya, "lead_owner"), "the web form gives a lead no owner"
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
