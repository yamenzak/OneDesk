"""The integration suite: the demo workspace read back as the people in it.

Each check opens what a person would open, as that person, and holds what it
shows against ERPNext's own records: the books balance, stock never went
below nothing, every party is billed in its own currency, every project page
opens for its team and its figures are the documents behind them, every
report of One's runs, and every rail link opens for the app's people.

    bench --site <site> execute onedesk.one_demo.check.run

prints a line a check and the count that failed. Nothing is written: each
check is rolled back.
"""

import frappe
from frappe.utils import flt, getdate, today

from onedesk.one_demo.base import COMPANY, as_user, on
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
			print(f"FAIL  {fn.__name__}: {str(e)[:600]}")
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
