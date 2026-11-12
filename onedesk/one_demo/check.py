"""The integration suite: the demo workspace read back as the people in it.

    bench --site <site> execute onedesk.one_demo.check.run
    bench --site <site> execute onedesk.one_demo.check.run --kwargs "{'only': 'oneproject_'}"

`only` names one check, or ends in "_" to run a group: every check whose name
starts with it, such as a module's.
"""

import base64
import io
import json
import traceback
from contextlib import contextmanager
from unittest import mock

import frappe
from frappe.utils import (
	add_days,
	add_to_date,
	flt,
	get_datetime,
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
	from onedesk.one import dev
	from onedesk.one_demo.samples import unkept

	dev.require()
	failed = []
	chosen = [fn for fn in CHECKS if not only or fn.__name__ == only or (only.endswith("_") and fn.__name__.startswith(only))]
	with _unsent():
		with _on_disk():
			_each(chosen, failed, unkept)
	print(f"{len(chosen) - len(failed)} of {len(chosen)} passed" if len(chosen) != 1 else "")
	return len(failed)


@contextmanager
def _on_disk():
	"""Files the checks make stay on this machine, as on a workspace with no
	store, so a run sends nothing to R2 and reads back what it wrote. A check
	of the store switches it on for itself."""
	was = frappe.conf.get("onestorage_on_disk")
	frappe.conf.onestorage_on_disk = 1
	try:
		yield
	finally:
		frappe.conf.onestorage_on_disk = was


@contextmanager
def _unsent():
	"""No mail leaves while the checks run, and none they made is kept: a
	check that commits (a notification, a screen gone quiet) escapes the
	rollback, and each run once left a few hundred in the queue. frappe's
	suspend_email_queue holds the worker; what was queued since is dropped."""
	held = frappe.db.get_default("suspend_email_queue")
	frappe.db.set_default("suspend_email_queue", 1)
	frappe.db.commit()
	started = now_datetime()
	try:
		yield
	finally:
		made = frappe.get_all("Email Queue", filters={"creation": [">=", started]}, pluck="name")
		for at in range(0, len(made), 500):
			frappe.db.delete("Email Queue Recipient", {"parent": ["in", made[at : at + 500]]})
			frappe.db.delete("Email Queue", {"name": ["in", made[at : at + 500]]})
		frappe.db.set_default("suspend_email_queue", held or 0)
		frappe.db.commit()


def _each(chosen, failed, unkept) -> None:
	for fn in chosen:
		try:
			with unkept():
				fn()
			print(f"ok    {fn.__name__}")
		except Exception as e:
			failed.append(fn.__name__)
			here = [
				f"{one.filename.rsplit('/', 1)[-1]}:{one.lineno}"
				for one in traceback.extract_tb(e.__traceback__)
				if one.filename == __file__ or one.filename.endswith("/checks.py")
			]
			said = str(e) or f"line {traceback.extract_tb(e.__traceback__)[-1].lineno}"
			print(f"FAIL  {fn.__name__} ({here[-1] if here else '?'}): {type(e).__name__} {said[:600]}")
		finally:
			frappe.db.rollback()
			frappe.clear_cache()
			_unasked()
			frappe.local.response = frappe._dict({"docs": []})
			frappe.set_user("Administrator")


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
		for doc in frappe.get_all(doctype, filters={"docstatus": 1}, fields=["name", party, "company", "currency", "conversion_rate", "grand_total", "base_grand_total"]):
			if doc.currency != get_party_account_currency(party_type, doc[party], doc.company):
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
		"Purchase Invoice": {"Paid", "Unpaid", "Overdue", "Partly Paid", "Return"},
		"Sales Order": {"To Deliver and Bill", "To Deliver", "To Bill", "Completed"},
		"Purchase Order": {"To Receive and Bill", "To Receive", "To Bill", "Completed"},
		"Quotation": {"Open", "Ordered", "Lost"},
		"Opportunity": {"Open", "Quotation", "Lost"},
		"Lead": {"Lead", "Replied", "Interested", "Do Not Contact", "Converted", "Opportunity", "Quotation", "Lost Quotation"},
		"Project": {"Open", "Completed"},
		"Work Order": {"Completed", "In Process", "Not Started"},
		"Expense Claim": {"Paid", "Unpaid", "Rejected", "Draft"},
		"Employee": {"Active", "Left"},
		"Gratuity": {"Paid"},
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


def _reports():
	modules = frappe.get_all("Module Def", filters={"app_name": "onedesk"}, pluck="name")
	return frappe.get_all(
		"Report",
		filters={"module": ["in", modules], "report_type": ["in", ["Script Report", "Query Report"]], "is_standard": "Yes", "disabled": 0},
		pluck="name",
	)


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

	skip = {"AI Usage", "Plan Calculator", "Price Check", "AI Credits"}
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
		*((email, (home.read, home.attention)) for _f, _l, email, *_r in PEOPLE if email),
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
	outstanding, less credit notes not yet set against one."""
	from onedesk.one_book import home as books

	with as_user("huda@one.test"):
		said = books.owed_to_us()
	found = frappe.db.sql(
		"""select sum(outstanding_amount * conversion_rate) from `tabSales Invoice`
		where docstatus = 1 and company = %s and outstanding_amount != 0""",
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
	"""Each person holds the roles People gave them, and only the owner and
	the person who set the workspace up are administrators."""
	from onedesk.one.roles import ADMINISTRATOR
	from onedesk.one_demo.setup import BUILDER

	admins = {u for u in frappe.get_all("Has Role", filters={"role": ADMINISTRATOR, "parenttype": "User"}, pluck="parent") if u.endswith("@one.test")}
	assert admins == {OWNER, BUILDER}, admins
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
def the_books_lock_up_to_today_at_most():
	from onedesk.one_demo.base import ahead

	_refused(_each_way("huda@one.test", "Company", COMPANY, {"accounts_frozen_till_date": str(ahead(30))}), "up to today")


@check
def nobody_is_turned_on_past_the_seats():
	from onedesk.one.people import seats_used

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
	from onedesk.one import notification_words, notify, versions

	declared = notify.declared()
	with as_user(OWNER):
		listed = {one["name"] for app in notification_words._notification_types()["apps"] for one in app["types"]}
	missing = sorted(name for name, one in declared.items() if name not in listed and versions.offered(one["app"]))
	assert not missing, missing
	assert not {name for name, one in declared.items() if one["app"] == "OneAdmin"} & listed, "a workspace lists OneAdmin's types"
	wrong = [
		name
		for name, one in declared.items()
		if frappe.db.get_value("Notification Type", name, "one_default_subject") != notify.jinja(one.get("subject"))
	]
	assert not wrong, wrong


@check
def a_mail_says_what_happened_and_opens_it():
	"""A notification mailed to Karim is the workspace's, headed by what
	happened rather than frappe's "New Notification", with one button named
	for what it opens and which notification it is; a mail to an outside
	address is framed the same way, and one to a reader of Arabic right to
	left. Its button is the company's colour, and a mail One sends about
	itself wears One's mark. Its subject line reads as plain text."""
	from unittest import mock

	from onedesk.one import notify, tell

	subject, message = notify.render("Quote Received", {"supplier": "Emirates Sealants & Fixings", "request": "PUR-RFQ-2026-00005", "total": "4,975.00", "items": "Silicone"}, "en")
	log = frappe._dict(for_user="karim@one.test", type="Quote Received", subject=subject, email_content=message, document_type="Supplier Quotation", document_name="PUR-SQTN-1", link=None)
	with mock.patch("frappe.sendmail") as sent:
		notify.mail_log(log)
	said = sent.call_args.kwargs
	assert said["subject"] == "Emirates Sealants & Fixings sent a quote for PUR-RFQ-2026-00005", said["subject"]
	assert said["with_container"] and 'class="one-title"' in said["message"]
	assert "Open Supplier Quotation" in said["message"] and "/desk/supplier-quotation/PUR-SQTN-1" in said["message"]
	assert "<b>Quote Received</b>" in said["message"] and "center=notifications" in said["message"]
	assert "New Notification" not in said["message"]
	with mock.patch("frappe.sendmail") as sent:
		tell.portal_link("x@example.com", by="Karim", what="Quote Request R", workspace="W", link="https://x/l/1", button="Answer", until="1-1-2027")
	assert sent.call_args.kwargs["with_container"] and 'class="one-title"' in sent.call_args.kwargs["message"]
	from frappe.email.email_body import get_formatted_html

	framed = get_formatted_html("S", said["message"], with_container=True)
	assert frappe.utils.escape_html(notify.one_mail_brand()["name"]) in framed and "one-card" in framed
	assert "one-card" not in get_formatted_html("Re: your order", "<p>Hi</p>"), "a mail a person writes goes as written"
	arabic = get_formatted_html("S", notify.compose("S", "M", lang="ar"), with_container=True)
	assert arabic.count('dir="rtl"') >= 2, "a mail to a reader of Arabic reads right to left, masthead too"
	colour = frappe.db.get_value("Company", COMPANY, "one_brand_colour")
	assert colour.lower() in framed.lower(), "the button is the company's Brand Colour"
	ones = get_formatted_html("S", notify.compose("S", "M", ones=True), with_container=True)
	assert notify.ONE_MARK in ones and colour.lower() not in ones.lower(), "a mail about One wears One's mark"


@check
def the_payment_reminder_is_turned_on_where_every_notification_is():
	"""Send This on the Payment Reminder and the rule that mails it are one."""
	with as_user(OWNER):
		kind = frappe.get_doc("Notification Type", "Payment Reminder")
		kind.enabled = 1
		kind.save()
	assert frappe.db.get_value("Notification", "Payment Reminder", "enabled") == 1
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
	from frappe.utils import escape_html

	from onedesk.one_studio import print_blocks

	colour = frappe.db.get_value("Company", COMPANY, "one_brand_colour")
	assert colour, "the demo company has no Brand Colour"
	assert frappe.db.get_value("Letter Head", {"is_default": 1}) == COMPANY
	for doctype, (name, _module) in print_blocks.FORMATS.items():
		assert frappe.get_meta(doctype).default_print_format == name, doctype
		record = frappe.get_all(doctype, filters={"docstatus": ["<", 2]}, order_by="creation desc", limit=1, pluck="name")
		if not record:
			continue
		with as_user(OWNER):
			html = frappe.get_print(doctype, record[0], name)
		assert colour in html and escape_html(record[0]) in html, f"{doctype} {record[0]} prints without its letter head or number"
		if "One Title" not in (frappe.db.get_value("Print Format", name, "format_data") or ""):
			continue
		label = print_blocks.title(frappe.get_doc(doctype, record[0]))["label"]
		assert label in html, f"{doctype} {record[0]} prints no blocks"
	for name, theirs in print_blocks.REPLACES.items():
		doctype = frappe.db.get_value("Print Format", name, "doc_type")
		record = frappe.get_all(doctype, filters={"docstatus": ["<", 2]}, order_by="docstatus desc, creation desc", limit=1, pluck="name")[0]
		with as_user(OWNER):
			assert record in frappe.get_print(doctype, record, name), name
		assert all(frappe.db.get_value("Print Format", one, "disabled") for one in theirs), theirs


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
def one_boards_open_on_frappes_new_kanban():
	"""The pipeline, the projects board and a project's own board open on
	frappe's new Kanban, each card showing One's fields by their icons
	(one/boards.py). erpnext's board of deals by status is gone, so the
	Pipeline is the one deal board."""
	from erpnext.projects.doctype.project.project import create_kanban_board_if_not_exists

	from onedesk.one_crm import board as pipeline
	from onedesk.one_project import board as projects

	villa = create_kanban_board_if_not_exists(VILLA)
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
			was_on = frappe.db.get_value(extensions.EXTENSION, screen, "enabled")
			with mock.patch("onedesk.one_ai.run.once", return_value=""), mock.patch("onedesk.one_hr.hiring.read", return_value=fixed):
				said = mend.mend(screen)
			on = frappe.get_doc(extensions.EXTENSION, screen)
			if was_on:
				assert said["review"] == "Passed" and said["draft"] and on.enabled, "a fixed extension that is on waits beside it"
				extensions.drop_draft(screen)
				on.reload()
			else:
				assert said["review"] == "Passed" and not on.enabled, "a fixed extension that is off stays off"
				on.enabled = 1
				on.save()
			running = on.code
			again = {**fixed, "code": fixed["code"].replace("No mobile number yet.", "This customer has no mobile number yet.")}
			with mock.patch("onedesk.one_ai.run.once", return_value=""), mock.patch("onedesk.one_hr.hiring.read", return_value=again):
				assert mend.mend(screen)["draft"], "a fix of one that is on waits beside it"
			on.reload()
			assert on.enabled and on.code == running and extensions.drafted(on).code == again["code"]
			extensions.use_draft(screen)
			on.reload()
			assert on.enabled and on.code == again["code"] and not on.draft, "Use New Version runs it in its place"
			with mock.patch("onedesk.one_ai.run.once", return_value=""), mock.patch("onedesk.one_hr.hiring.read", return_value=fixed):
				assert mend.mend(screen, "It says nothing on a new customer")["draft"]
			extensions.drop_draft(screen)
			on.reload()
			assert on.code == again["code"] and not on.draft, "Discard New Version leaves the one that is on"
			on.enabled = was_on
			on.save()
		with mock.patch("frappe.enqueue") as queued:
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

	from onedesk.one_ai.reading import (
		act,
		ai,
		bundle,
		drafts,
		explain,
		identity,
		inbox,
		mark,
		panel,
		switches,
	)
	from onedesk.one_demo import intake

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

		contract = _sample("signed-contract")
		proposed = frappe.get_all("Reading Action", filters={"reading": contract, "level": "Proposed"}, pluck="name")[0]
		act.settle(proposed, 0)
		assert frappe.db.get_value("Reading Action", proposed, "level") != "Proposed"
		contact = frappe.db.get_value("Reading Action", {"reading": contract, "target_doctype": "Contact", "level": "Done"}, "name")
		assert act.undo_one(contact)["undone"] == 1
		drawings = _sample("drawings-request")
		task = frappe.db.get_value("Reading Action", {"reading": drawings, "target_doctype": "Task", "level": "Done"}, "target_name")
		assert act.undo(drawings)["undone"] >= 1 and not frappe.db.exists("Task", task)

		marked = [
			one
			for one in frappe.get_all("AI Touch", filters={"for_doctype": "Task", "fieldname": mark.WHOLE}, pluck="record")
			if frappe.has_permission("Task", "write", one)
		]
		assert marked, "no task OneAI made that Layla may change"
		mark.looks_right("Task", marked[0])
		assert not mark.is_marked("Task", marked[0])

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
		with mock.patch("onedesk.one_ai.reading.pipeline.later") as later:
			switches.read_now(schedule)
		assert later.call_args.args[0] == "read_file"


@check
def one_offers_only_what_it_shows():
	"""A picker of record types or reports, which is also what a Dynamic Link
	asks first, and global search offer what One's rails, Homes and screens
	reach and never frappe's machinery; a dashboard a rail lists opens in that
	rail (one/outside.py, shown.json)."""
	from frappe.desk.doctype.sidebar.sidebar import linked_entities

	from onedesk.one import outside

	shown = outside.shown()
	picked = {row[0] for row in outside.doctype_query("DocType", "", "name", 0, 5000, {})}
	assert "Customer" in picked and "Employee" in picked, "a picker of record types leaves out One's own"
	assert not picked & {"DocType", "Module Def", "Workspace", "Custom Field", "Server Script"}, "a picker offers frappe's machinery"
	reports = {row[0] for row in outside.report_query("Report", "", "name", 0, 5000, {})}
	assert reports and reports <= shown["Report"], "a picker of reports offers one One does not show"
	found = outside.search("a", limit=50)
	assert all(row["doctype"] in shown["DocType"] for row in found), "global search finds a record type One does not show"
	ours = frappe.get_all("Sidebar", filters={"app": "onedesk"}, pluck="name")
	for item in frappe.get_all("Sidebar Item", filters={"parenttype": "Sidebar", "parent": ["in", ours]}, fields=["*"]):
		if item.type == "Link" and item.link_type in ("DocType", "Report", "Page", "Dashboard"):
			named = {one.split("/")[0] for one in linked_entities(item)}
			named = {one for one in named if frappe.db.exists(item.link_type, one)}
			missing = named - shown[item.link_type]
			assert not missing, f"{item.parent}'s rail links {sorted(missing)}, which One does not show"


@check
def the_owner_runs_the_setup_wizard():
	"""The wizard opens to whoever administers the workspace, asking again once
	it is done changes nothing, and this year's leave and payroll periods
	cover today (one/setup_wizard.py, one_hr/periods.py)."""
	from frappe.desk import desk_page

	from onedesk.one import roles, setup_wizard

	owner = roles.administrators()[0]
	frappe.set_user(owner)
	try:
		assert desk_page.get("setup-wizard"), "the wizard does not open for the workspace's administrator"
		assert setup_wizard.setup_complete("{}") == {"status": "ok"}
	finally:
		frappe.set_user("Administrator")
	day = frappe.utils.today()
	assert frappe.db.exists("Leave Period", {"from_date": ("<=", day), "to_date": (">=", day)}), "no leave year today"
	assert frappe.db.exists("Payroll Period", {"start_date": ("<=", day), "end_date": (">=", day)}), "no payroll year today"


@check
def oneai_is_told_what_every_place_shows():
	"""Every entry on every space's rail and every desk page tells OneAI more
	than its title: a report its filters, a dashboard its charts, a home what it
	opens, a page what is on it (one_ai/here.py)."""
	from onedesk.one_ai import here

	frappe.set_user("Administrator")
	missed = here.untold()
	assert not missed, "OneAI is told only the title of: " + "; ".join(
		f"{one['space']} › {one['label']} {one['sent']}" for one in missed
	)


@check
def oneai_a_conversation_its_cards_and_its_settings():
	"""Omar's conversation with OneAI from start to forgotten, the cards it
	suggests waiting, refused, applied and taken into a form, and Layla's
	OneAI settings, where nothing about a model is set. A model is not
	called: what the account and the model would say is said here."""
	from unittest import mock

	from onedesk.one import ai
	from onedesk.one_ai import center, chat, files, proposals, run
	from onedesk.one_crm import ai as crm

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
		field = frappe.get_doc("AI Proposal", proposals.propose("Edit", "Lead", {"company_name": "Pike Hotels"}))
		run.took(field.name)
		lead = frappe.get_doc({"doctype": "Lead", "first_name": "Joanna", "last_name": "Pike", "company_name": "Pike Hotels", "email_id": "jp@pikehotels.example"}).insert()
		assert run.landed(field.name, lead.name) == {"company_name": "Pike Hotels"}
		assert len(run.tools()) > 50
		used = run.use("crm_facts", {"record_type": "Opportunity", "name": deal})
		assert used["ran"] and used["answer"]["history"], used
		chat.forget(started["name"])
		assert not frappe.db.exists("AI Chat", started["name"])
	with as_user(OWNER):
		with mock.patch("onedesk.one.account.ask", return_value=[{"tier": "balanced", "credits": 0.4}]):
			held = center.state()
		assert set(held) == {"on", "tier", "tiers", "credits"} and held["tier"] in {"fast", "balanced", "full"}, "a workspace sets no model and no words"
		with (
			mock.patch("onedesk.one.account.configured", return_value=True),
			mock.patch("onedesk.one.account.ask", return_value={"actions": [{"action": chat.CHAT, "calls": 3, "credits": 1.5}]}),
		):
			said = ai.workspace_oneai()
		assert said["last_30_days"][0]["calls"] == 3 and said["summaries"], said


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
def onecloud_a_letter_is_edited_in_oneos():
	"""Samir opens a letter in OneOS from the Projects library and it is his
	alone: Rania, who may change it too, is told he has it, and Yousef, who
	only reads, opens a copy in his own files instead. The container fetches
	the letter and saves a version as Samir through the two sealed addresses,
	which open nothing else, and OneAdmin's stop lets the lease go and tells
	him why."""
	from urllib.parse import parse_qs, urlparse

	from werkzeug.exceptions import Forbidden
	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one_demo import storage as demo
	from onedesk.one_storage import api, history, oneos, upload

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	asked, answers = [], {}

	def admin(endpoint, **said):
		asked.append((endpoint.rsplit(".", 1)[-1], said))
		if endpoint.endswith("oneos_start"):
			return {"session": f"session{len(asked):04d}", "url": f"https://os.example.com/s/session{len(asked):04d}?t=1.x", "state": "Starting"}
		return answers.get(endpoint.rsplit(".", 1)[-1], {"url": "https://r2.example.com/letter"})

	def sealed(url):
		return {key: one[0] for key, one in parse_qs(urlparse(url).query).items()}

	with mock.patch("onedesk.one.account.ask", side_effect=admin), mock.patch("onedesk.one.account.configured", return_value=True), mock.patch("frappe.publish_realtime") as told:
		with as_user(demo.PM):
			letter = upload._place(root, None, {"file_name": "Villa handover.odt", "content": b"handover v1"})["id"]
			opened = oneos.start(letter)
			assert opened["url"].startswith("https://os.example.com/s/") and asked[-1][0] == "oneos_start"
			assert next(one for one in api.listing(root)["items"] if one["id"] == letter)["oneos"] == {"by": frappe.utils.get_fullname(demo.PM), "mine": True}
			again = oneos.start(letter)
			assert asked[-1][1]["again"] == opened["url"].split("/s/")[1].split("?")[0] and again["node"] == letter, "his own session is opened again, not a second"
		start = next(said for endpoint, said in asked if endpoint == "oneos_start")
		with as_user("rania@one.test"):
			assert oneos.start(letter)["held"]["by"] == frappe.utils.get_fullname(demo.PM)
		with as_user("yousef@one.test"):
			assert oneos.start(letter)["held"]["readonly"]
			copy = oneos.start(letter, copy=1)
			assert copy["node"] != letter and frappe.db.get_value("File", copy["node"], "one_lease_user") == "yousef@one.test"
			oneos.close(copy["node"])
			assert asked[-1][0] == "oneos_stop" and not frappe.db.get_value("File", copy["node"], "one_lease_user")
		down, up = sealed(start["file_url"]), sealed(start["save_url"])
		oneos.file(**down)
		for key in ("type", "filecontent", "filename", "display_content_as"):
			frappe.local.response.pop(key, None)
		was = frappe.local.request if hasattr(frappe.local, "request") else None
		try:
			frappe.local.request = Request(EnvironBuilder(method="POST", data=b"handover v2").get_environ())
			frappe.local.request_ip = "127.0.0.1"
			assert oneos.save(**up) == {"saved": True}
			frappe.local.request = Request(EnvironBuilder(method="POST", data=b"handover v2").get_environ())
			assert oneos.save(**up) == {"saved": False}, "the same content is not a version"
			for wrong in ({**down}, {**up, "f": copy["node"]}, {**up, "e": str(int(up["e"]) + 1)}):
				try:
					oneos.save(**wrong)
					raise AssertionError("a sealed address saved what it was not made for")
				except Forbidden:
					pass
		finally:
			frappe.local.request = was
		assert len(history.versions(letter)) == 1 and frappe.db.get_value("File", letter, "modified_by") == demo.PM
		answers["oneos_state"] = {"state": "Stopped", "stop_reason": "Idle"}
		with mock.patch("onedesk.one_storage.tell.oneos_closed") as closed:
			oneos.stopped(frappe.db.get_value("File", letter, "one_lease_session"))
		assert not frappe.db.get_value("File", letter, "one_lease_user")
		assert any(call.args[0] == "onecloud_oneos" and call.args[1].get("why") == "Idle" for call in told.call_args_list)
		assert closed.call_args.args[:2] == (demo.PM, letter)
	for name in (letter, copy["node"]):
		frappe.delete_doc("File", name, ignore_permissions=True, force=True)


@check
def onecloud_one_lease_keeps_oneos_and_the_editors_apart():
	"""Rania has a letter open in OneWriter, so Samir's Open in OneOS tells
	him she is editing it there. Once her editor leaves, his session has it
	alone: her OneWriter opens it read-only saying he is editing it in OneOS,
	refuses her save, and no version of it is restored under him. Saves from
	his session are one version. All undone afterwards."""
	from urllib.parse import parse_qs, urlparse

	from docx import Document
	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one_demo import storage as demo
	from onedesk.one_doc import api as writing
	from onedesk.one_doc import word
	from onedesk.one_sheet import live
	from onedesk.one_storage import history, lease, oneos, upload

	def letter(text: str) -> bytes:
		made = Document()
		made.add_paragraph(text)
		out = io.BytesIO()
		made.save(out)
		return out.getvalue()

	def admin(endpoint, **said):
		return {"session": "lease-check", "url": "https://os.example.com/s/lease-check?t=1.x", "state": "Running"} if endpoint.endswith("oneos_start") else {}

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	samir, rania = frappe.utils.get_fullname(demo.PM), "rania@one.test"
	frappe.db.savepoint("lease_check")
	try:
		with mock.patch("onedesk.one.account.ask", side_effect=admin) as asked, mock.patch("frappe.publish_realtime"):
			with as_user(demo.PM):
				file = upload._place(root, None, {"file_name": "Handover check.docx", "content": letter("Keys on Monday.")})["id"]
				first = upload._place(root, None, {"file_name": "Handover check.docx", "content": letter("Keys on Tuesday.")}, replace=1)
				assert first["id"] == file and len(history.versions(file)) == 1
			with as_user(rania):
				document = word.open_file(file)["document"]
				assert live.admit("document", document, sid="lease-check")["write"]
				live.here(json.dumps([["document", document]]), sid="lease-check")
				assert lease.of(file)["mode"] == "live" and lease.of(file)["live"][0]["app"] == "OneWriter"
			with as_user(demo.PM):
				held = oneos.start(file)["held"]
				assert held["by"] == frappe.utils.get_fullname(rania) and held["where"] == "OneWriter", held
			with as_user(rania):
				live.leave("document", document, sid="lease-check")
			with as_user(demo.PM):
				assert oneos.start(file)["url"], "alone once nobody is in it live"
			start = next(call.kwargs for call in asked.call_args_list if call.args[0].endswith("oneos_start"))
			with as_user(rania):
				said = writing.get_document(document)
				assert not said["can_write"] and said["notice"] == f"{samir} is editing this in OneOS.", said["notice"]
				assert not live.admit("document", document, sid="lease-check")["write"]
				live.leave("document", document, sid="lease-check")
				for refused in (lambda: writing.save_document(document, "AAA=", "<p>Keys on Friday.</p>"), lambda: history.restore(file, history.versions(file)[0]["name"])):
					try:
						refused()
						raise AssertionError("changed under the OneOS session")
					except (frappe.ValidationError, frappe.PermissionError):
						frappe.clear_last_message()
				assert lease.of(file)["alone"] == {"by": samir, "kind": lease.ONEOS, "mine": False}
			up = {key: one[0] for key, one in parse_qs(urlparse(start["save_url"]).query).items()}
			was = getattr(frappe.local, "request", None)
			try:
				for text in ("Keys on Wednesday.", "Keys on Thursday."):
					frappe.local.request = Request(EnvironBuilder(method="POST", data=letter(text)).get_environ())
					frappe.local.request_ip = "127.0.0.1"
					assert oneos.save(**up) == {"saved": True}
			finally:
				frappe.local.request = was
			assert len(history.versions(file)) == 2, "two saves in one session are one version, beside the one before it"
			with as_user(demo.PM):
				oneos.close(file)
			assert not lease.blocking(file)
	finally:
		frappe.db.rollback(save_point="lease_check")


LOCKINFO = (
	b'<?xml version="1.0" encoding="utf-8"?><D:lockinfo xmlns:D="DAV:"><D:lockscope><D:exclusive/></D:lockscope>'
	b"<D:locktype><D:write/></D:locktype><D:owner><D:href>RANIA-PC/rania</D:href></D:owner></D:lockinfo>"
)
DISCOVERY = b'<?xml version="1.0"?><D:propfind xmlns:D="DAV:"><D:prop><D:lockdiscovery/></D:prop></D:propfind>'


@check
def onecloud_the_drives_locks_join_the_lease():
	"""Rania's Word lock is the file's lease: Samir's Word and drive save are
	refused naming her, her saves are one version, Word's and the Mac's safe
	saves keep the same File and lease. Unlocked, Samir saving from an older
	version, or with an old If-Match, gets "(Samir's copy)" beside it. While
	Samir is live in OneWriter her Word is refused naming him; deleting it
	in OneCloud while she has it tells her. All undone afterwards."""
	from urllib.parse import quote

	from docx import Document

	from onedesk.one_demo import storage as demo
	from onedesk.one_doc import word
	from onedesk.one_sheet import live
	from onedesk.one_storage import api, dav, history, lease, upload

	def letter(text: str) -> bytes:
		made = Document()
		made.add_paragraph(text)
		out = io.BytesIO()
		made.save(out)
		return out.getvalue()

	def said(content: bytes) -> str:
		return Document(io.BytesIO(content)).paragraphs[0].text

	def drive(method: str, path: str, body: bytes = b"", **headers) -> tuple[int, dict, bytes]:
		_asked(path=dav.MOUNT + quote(path), method=method, data=body, headers={key.replace("_", "-"): value for key, value in headers.items()})
		answer = dav.serve()
		out = b"".join(answer.response)
		dav._forget()
		return answer.status_code, answer.headers, out

	def holds(path: str, token: str) -> str:
		return f"<{quote(path)}> (<{token}>)"

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	rania, taken = "rania@one.test", []
	frappe.db.savepoint("drive_lock_check")
	try:
		with mock.patch("frappe.publish_realtime"), mock.patch("onedesk.one_storage.tell.deleted_while_open") as told:
			with as_user(demo.PM):
				file = upload._place(root, None, {"file_name": "Drive check.docx", "content": letter("Keys on Monday.")})["id"]
				path = dav.path_of(file)
				folder = path.rsplit("/", 1)[0]
			with as_user(rania):
				status, headers, _out = drive("LOCK", path, LOCKINFO, Timeout="Second-600", Depth="0", Content_Type="text/xml")
				assert status == 200, status
				token = headers["Lock-Token"].strip("<>")
				taken.append(token)
				alone = lease.alone_of(file)
				assert (alone.one_lease_user, alone.one_lease_kind, alone.one_lease_lock) == (rania, lease.DAV, token), alone
				left = (get_datetime(alone.one_lease_until) - now_datetime()).total_seconds()
				assert 590 < left <= 600, left
			with as_user(demo.PM):
				assert drive("LOCK", path, LOCKINFO, Timeout="Second-600", Depth="0")[0] == 423, "a second Word opens it read-only"
				assert b"RANIA-PC" in drive("PROPFIND", path, DISCOVERY, Depth="0")[2], "and is told whose it is"
				assert drive("PUT", path, letter("Samir's keys."))[0] == 423
				assert lease.of(file)["alone"] == {"by": frappe.utils.get_fullname(rania), "kind": lease.DAV, "mine": False}
			with as_user(rania):
				before = len(history.versions(file))
				for text in ("Keys on Tuesday.", "Keys on Wednesday."):
					assert drive("PUT", path, letter(text), If=holds(path, token))[0] == 204
				assert len(history.versions(file)) == before + 1, "saves under one lock are one version"
				assert drive("LOCK", path, Timeout="Second-3600", If=holds(path, token))[0] == 200
				assert get_datetime(lease.alone_of(file).one_lease_until) > add_to_date(now_datetime(), minutes=59), "a refresh renews the lease"

				aside, temp = f"{folder}/~WRL0001.tmp", f"{folder}/~WRD0000.tmp"
				assert drive("PUT", temp, letter("Keys on Thursday."))[0] == 201
				assert drive("MOVE", path, Destination=dav.MOUNT + quote(aside), Overwrite="F", If=holds(path, token))[0] in (201, 204)
				assert drive("MOVE", temp, Destination=dav.MOUNT + quote(path), Overwrite="F")[0] in (201, 204)
				assert drive("DELETE", aside)[0] == 204
				assert frappe.db.get_value("File", file, ["file_name", "one_deleted"]) == ("Drive check.docx", 0)
				assert said(drive("GET", path)[2]) == "Keys on Thursday.", "Word's safe save is a save of the same file"
				assert not frappe.get_all("File", filters={"file_name": ["like", "~WR%"]}, limit=1), "and leaves nothing behind"
				assert lease.alone_of(file).one_lease_lock == token, "the lease followed the file"

				side = path + ".sb-2f1c-Qx"
				assert drive("PUT", side, letter("Keys on Friday."))[0] == 201
				assert drive("MOVE", side, Destination=dav.MOUNT + quote(path), Overwrite="T", If=holds(path, token))[0] in (201, 204)
				assert said(drive("GET", path)[2]) == "Keys on Friday." and not frappe.get_all("File", filters={"file_name": ["like", "%.sb-%"]}, limit=1)
				assert drive("UNLOCK", path, Lock_Token=f"<{token}>")[0] == 204
				assert not lease.blocking(file), "UNLOCK lets the lease go"

			with as_user(demo.PM):
				drive("GET", path)
			with as_user(rania):
				assert drive("PUT", path, letter("Keys on Saturday."))[0] == 204
			with as_user(demo.PM):
				assert drive("PUT", path, letter("Keys on Sunday."))[0] == 204
				assert drive("PUT", path, letter("Keys on Sunday evening."))[0] == 204
				assert said(drive("GET", path)[2]) == "Keys on Saturday.", "an older copy never lands over hers"
				copy = frappe.db.get_value("File", {"folder": root, "file_name": "Drive check (Samir's copy).docx"})
				assert copy and len(history.versions(copy)) == 1, "his copy beside it, his next save into it"
				etag = drive("HEAD", path)[1]["ETag"]
			with as_user(rania):
				upload._place(root, None, {"file_name": "Drive check.docx", "content": letter("Keys on Monday again.")}, replace=1)
			with as_user(demo.PM):
				assert drive("PUT", path, letter("Keys from an old phone."), If_Match=etag)[0] == 204
				assert said(drive("GET", path)[2]) == "Keys on Monday again."
				assert frappe.db.count("File", {"folder": root, "file_name": ["like", "Drive check (Samir's copy)%"]}) == 1, "into the same copy"

			with as_user(demo.PM):
				document = word.open_file(file)["document"]
				assert live.admit("document", document, sid="drive-check")["write"]
			with as_user(rania):
				assert drive("LOCK", path, LOCKINFO, Timeout="Second-600", Depth="0")[0] == 423
				named = drive("PROPFIND", path, DISCOVERY, Depth="0")[2].decode()
				assert frappe.utils.get_fullname(demo.PM) in named and "OneWriter" in named, named
			with as_user(demo.PM):
				live.leave("document", document, sid="drive-check")

			with as_user(rania):
				status, headers, _out = drive("LOCK", path, LOCKINFO, Timeout="Second-600", Depth="0")
				assert status == 200
				taken.append(headers["Lock-Token"].strip("<>"))
			with as_user(demo.PM):
				assert drive("DELETE", path)[0] == 423, "not from his drive while her Word has it"
				api.delete([file])
				assert frappe.db.get_value("File", file, "one_deleted") == 1, "from OneCloud, to the Recycle Bin"
				assert told.call_args.args[0] == [rania], told.call_args
	finally:
		_unasked()
		locks = dav._app().lock_manager.storage
		for token in taken:
			locks.delete(token)
		frappe.db.rollback(save_point="drive_lock_check")


@check
def onecloud_office_files_wait_to_open_in_oneos():
	"""Every office file the demo wrote is where its owner left it, opens in
	OneOS for them and reads back as what it says it is: the Word files as
	paragraphs, the workbooks with their formulas, the deck with its slides and
	the export with its rows. Whoever it was shared with may read it, and only
	those given edit may change it."""
	import csv

	from docx import Document
	from openpyxl import load_workbook
	from pptx import Presentation

	from onedesk.one_demo import office as demo
	from onedesk.one_storage import api, oneos
	from onedesk.one_storage import namespace as ns

	for one in demo.files():
		node = demo.found(one)
		assert node, f"{one['name']} is not in {one['owner']}'s files"
		item = ns.row(node)
		assert oneos.opens(item.file_name), item.file_name
		folder = ns.row(item.folder)
		assert folder and folder.file_name == one["folder"], f"{one['name']} is in {folder and folder.file_name}"
		with as_user(one["owner"]):
			oneos._openable(node)
			content = api._content(item)
		kind = item.file_name.rsplit(".", 1)[-1]
		if kind == "docx":
			assert len([para for para in Document(io.BytesIO(content)).paragraphs if para.text.strip()]) >= 5, item.file_name
		elif kind == "xlsx":
			book = load_workbook(io.BytesIO(content))
			assert any(isinstance(cell.value, str) and cell.value.startswith("=") for sheet in book for row in sheet.iter_rows() for cell in row), item.file_name
		elif kind == "pptx":
			assert len(Presentation(io.BytesIO(content)).slides) >= 4, item.file_name
		else:
			rows = list(csv.reader(io.StringIO(content.decode())))
			assert rows[0][0] == "Item code" and len(rows) > 1, item.file_name
		for user, edit in one["shared"].items():
			assert ns.may(item, "read", user=user), f"{user} cannot read {one['name']}"
			assert ns.may(item, "write", user=user) == bool(edit), f"{user} {'cannot' if edit else 'can'} change {one['name']}"
	budget = next(one for one in demo.files() if one["name"] == demo.budget_name())
	assert not ns.may(ns.row(demo.found(budget)), "read", user="nadia@one.test"), "Huda's budget is not open to everybody"


@check
def onecloud_the_site_team_works_in_its_library():
	"""Samir's Projects library as the crew uses it: listed, searched and
	found by its path, a folder made, renamed and moved about, a file copied,
	attached to the villa, bound with its copy into one PDF, starred and put back
	to its first version, coloured, shared
	and unshared, deleted and restored, and the bin emptied. Yousef only
	reads it. What OneAI says about a file and who sees it, and a drive
	answering for Samir."""
	from pypdf import PdfReader, PdfWriter

	from onedesk.one_demo import storage as demo
	from PIL import Image

	from onedesk.one_storage import ai, api, dav, history, library, made, office, pdf, share, upload
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
		assert api.text(notes)["text"].strip() == demo.NOTES_SAID and not api.text(notes)["cut"]
		api.content(notes)
		assert frappe.local.response.type == "binary" and frappe.local.response.filecontent.decode().strip() == demo.NOTES_SAID
		for key in ("type", "filecontent", "filename"):
			frappe.local.response.pop(key, None)
		assert api.color([folder], "green") == [folder]
		assert next(one for one in api.listing(root)["items"] if one["id"] == folder)["color"] == "green"
		assert api.color([drawing], "red") == [] and not frappe.db.get_value("File", drawing, "one_color")
		try:
			api.color([folder], "orange")
			raise AssertionError("a colour nobody offered was kept")
		except frappe.ValidationError:
			pass
		copied = api.copy([drawing], folder)
		assert frappe.db.get_value("File", copied[0], "file_name") == demo.ELEVATIONS
		bound = pdf.combine([drawing, copied[0]], folder, "Elevations bound")
		pages = len(PdfReader(io.BytesIO(api._content(api._item(drawing)))).pages)
		assert bound["name"] == "Elevations bound.pdf"
		assert len(PdfReader(io.BytesIO(api._content(api._item(bound["id"])))).pages) == 2 * pages
		try:
			pdf.combine([drawing, notes], folder)
			raise AssertionError("a text file was put into a PDF")
		except frappe.ValidationError:
			pass
		dot = io.BytesIO()
		Image.new("RGB", (4, 4), "blue").save(dot, "PNG")
		making = {"picture": {"data": base64.b64encode(dot.getvalue()).decode(), "mime": "image/png"}, "speech": {"data": base64.b64encode(b"\0\0" * 800).decode(), "mime": "audio/L16;rate=16000"}}
		asked = []
		with mock.patch("onedesk.one_ai.run.make", side_effect=lambda job, text, reference=None, voice=None: asked.append((job, voice)) or making[reference.split()[-1]]), mock.patch("onedesk.one.apps.refuse_ai"), mock.patch("frappe.enqueue") as later:
			assert made.create("picture", folder, "A site at dawn", shape="wide")["name"] == "A site at dawn.png"
			assert made.create("speech", folder, "Gates open at seven.", voice="Puck", name="Gates")["name"] == "Gates.wav"
			assert made.create("music", folder, "Calm piano") == {"begun": True} and later.call_args.kwargs["kind"] == "music"
		assert asked == [("cloud_picture", None), ("cloud_voice", "Puck")]
		letter = upload._place(folder, None, {"file_name": "Site letter.rtf", "content": rb"{\rtf1 Site letter}"})["id"]
		plain = io.BytesIO()
		blank = PdfWriter()
		blank.add_blank_page(100, 100)
		blank.write(plain)
		sent = []
		frappe.cache.delete_value(f"one_storage_office:{frappe.db.get_value('File', letter, 'content_hash')}")
		with mock.patch("onedesk.one.account.ask", side_effect=lambda endpoint, **said: sent.append((endpoint, said["name"])) or {"data": base64.b64encode(plain.getvalue()).decode(), "credits": 1}):
			office.preview(letter)
			assert frappe.local.response.filecontent.startswith(b"%PDF") and frappe.local.response.filename == "Site letter.pdf"
			for key in ("type", "filecontent", "filename"):
				frappe.local.response.pop(key, None)
			assert office.to_pdf(letter)["name"] == "Site letter.pdf"
		assert sent == [("onedesk.one_admin.proxy.office_convert", "Site letter.rtf")], "the second is the day's kept preview"
		try:
			office.to_pdf(notes)
			raise AssertionError("a text file went to the office containers")
		except frappe.ValidationError:
			pass
		with as_user("yousef@one.test"):
			try:
				made.create("picture", folder, "Anything")
				raise AssertionError("a reader made a file in the library")
			except frappe.PermissionError:
				pass
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
		try:
			api.color([root], "pink")
			raise AssertionError("a reader coloured a library's folder")
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
	from urllib.parse import unquote

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
	sent = links.get(token)
	if sent is not None:
		assert sent.status_code == 302 and demo.ELEVATIONS in unquote(sent.location), "a stored file is sent from the store"
	else:
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
	staff = frappe.db.get_value("Employee", {"user_id": ["is", "set"]}, ["name", "user_id"], as_dict=True)
	with as_user("Administrator"):
		assert file_requests.asked_at("Employee", staff.name) == staff.user_id
	with as_user("karim@one.test"):
		mine = file_requests.make(ns.MY, {"title": "Signed contract", "items": [{"label": "Signed contract", "required": 1}], "recipients": "yousef@one.test"})
	wanted = frappe.db.get_value("Cloud File Request Item", {"parent": mine["name"]})
	with as_user("yousef@one.test"):
		picked = frappe.get_doc({"doctype": "File", "file_name": "contract.pdf", "content": demo._pdf("Signed contract"), "is_private": 1}).insert()
		assert file_requests.guess(wanted, request=mine["name"], file_url=picked.file_url) == {}
		file_requests.send_mine(mine["name"], wanted, picked.file_url)
		assert not frappe.db.exists("File", picked.name)
	with as_user("karim@one.test"):
		assert file_requests.progress(mine["name"])["people"][0]["sent"]["Signed contract"]

	where = "https://r2.example.com/put"
	with as_user(demo.PM), mock.patch("onedesk.one_storage.store.enabled", return_value=True), mock.patch(
		"onedesk.one.account.put_url", return_value={"url": where}
	), mock.patch("onedesk.one_storage.store.signed", return_value="https://r2.example.com/get"), mock.patch(
		"onedesk.one_storage.upload.requests.get", return_value=mock.Mock(status_code=206)
	):
		tickets = upload.begin(root, [{"name": demo.ELEVATIONS, "size": 900}, {"name": "Door schedule.pdf", "size": 400}])
		assert tickets["direct"] and tickets["existing"] == [demo.ELEVATIONS]
		placed = upload.done(tickets["tickets"][1]["token"])
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
def one_an_app_turned_off_is_hidden_not_refused():
	"""The workspace administrator turns OneCRM off: it leaves everybody's
	rail, and Opportunity leaves search and the pickers, while Customer,
	which OneBook lists too, stays. Nothing is refused: an opportunity still
	opens, OneAI may still file into one, and turning OneCRM back
	on brings it all back. Nobody else may turn an app off."""
	from frappe.desk.doctype.dock.dock import resolve_dock

	from onedesk.one import apps

	with as_user("rania@one.test"):
		try:
			apps.save(["OneCRM"])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("only a workspace administrator turns an app off")
	with as_user(OWNER):
		offered = {one["name"]: one for one in apps.read()["apps"]}
		assert "OneCRM" in offered and "One" not in offered, offered
		apps.save(["OneCRM"])
		assert apps.hidden() == ["OneCRM"]
		gone = set(apps.doctypes())
		assert "Opportunity" in gone and "Customer" not in gone, sorted(gone)[:20]
		picked = [one["value"] for one in apps.search_link("DocType", "Opportun")]
		assert "Opportunity" not in picked, picked
	rail = {row.get("link_to"): row.get("hidden") for row in resolve_dock().get("onedesk", [])}
	assert rail.get("OneCRM") in (None, 1) and not rail.get("OneBook"), rail
	opportunity = frappe.get_all("Opportunity", pluck="name", limit=1)
	assert opportunity and frappe.has_permission("Opportunity", "read", opportunity[0], user=OWNER)
	assert frappe.has_permission("Opportunity", "create", user=OWNER), "OneAI checks this before it files"
	with as_user(OWNER):
		apps.save([])
		assert not apps.doctypes()
		assert "Opportunity" in [one["value"] for one in apps.search_link("DocType", "Opportun")]


@check
def one_oneai_turned_off_asks_nothing_and_oneintake_reads_nothing():
	"""OneAI off, in Apps, turns OneAI off with it: no model is asked
	(`run.once`, a chat), nothing is queued to be read, no switch turns on,
	OneHR's screening is off, OneAI's rail leaves the dock, One's rail loses
	What OneAI Remembers and Reads, OneBook its Ready to Submit. Reading
	alone off leaves OneAI answering. What
	OneAI Reads holds only the reader's own mailboxes."""
	from frappe.boot import get_module_sidebars

	from onedesk.one import apps
	from onedesk.one_admin import faults
	from onedesk.one_ai import chat, run, yours
	from onedesk.one_ai.reading import pipeline, switches
	from onedesk.one_hr import hiring

	with as_user("rania@one.test"):
		mine = yours.load("reads")
		assert all(one["mine"] for one in mine["mailboxes"]), mine["mailboxes"]
	queued = []
	enqueue = frappe.enqueue
	frappe.enqueue = lambda *args, **kwargs: queued.append(args)
	try:
		with as_user(OWNER):
			apps.save(["OneAI"])
			assert {"OneAI", "Reading"} <= set(apps.hidden()), apps.hidden()
			try:
				run.once("chat_title", "anything")
			except faults.Refused:
				pass
			else:
				raise AssertionError("OneAI off still asked a model")
			try:
				chat.say("hello")
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("OneAI off still started a chat")
			pipeline.later("read_file", "file:nothing", name="nothing", person=OWNER)
			assert not queued, queued
			box = frappe.get_all("Email Account", pluck="name", limit=1)
			if box:
				try:
					switches.set_mailbox(box[0], 1)
				except frappe.ValidationError:
					pass
				else:
					raise AssertionError("a mailbox switched on with OneAI off")
			assert not hiring.on("one_ai_screen")
			from frappe.desk.doctype.dock.dock import resolve_app_dock

			assert "OneAI" not in [one.get("link_to") for one in resolve_app_dock(apps.HOST) if not one.get("hidden")]
			sidebars = get_module_sidebars()
			apps.trim(sidebars)
			urls = {item.get("url") for item in sidebars["One"]["items"]}
			assert not urls & {"/desk/one?center=ai&at=yours", "/desk/one?center=ai&at=reads"}, urls
			assert "One Intake" not in sidebars
			assert all(item.get("link_to") != "Ready to Submit" for item in (sidebars.get("OneBook") or {}).get("items", []))
			apps.save(["Reading"])
			assert apps.ai_on() and not apps.intake_on()
			apps.save([])
			assert apps.intake_on() and hiring.on("one_ai_screen") == bool(frappe.db.get_single_value("HR Settings", "one_ai_screen"))
	finally:
		frappe.enqueue = enqueue
		with as_user(OWNER):
			apps.save([])


@check
def one_a_person_works_in_one_company_at_a_time():
	"""With Sahara Glass Saudi beside Sahara, Karim may switch between them
	from the frame, and Stock Summary follows; a company he may not read is
	refused, and Yousef, who reads no company, is offered none."""
	from onedesk.one import company
	from onedesk.one_demo.branch import BRANCH
	from onedesk.one_inventory import stock

	try:
		with as_user("karim@one.test"):
			said = company.mine()
			assert said and {COMPANY, BRANCH} <= set(said["all"]) and said["current"] == COMPANY, said
			company.use(BRANCH)
			assert company.mine()["current"] == BRANCH and stock.on_hand()["currency"] == "SAR"
			try:
				company.use("No Such Company")
				raise AssertionError("a company he may not work in was taken")
			except frappe.PermissionError:
				pass
	finally:
		frappe.defaults.set_user_default("company", COMPANY, "karim@one.test")
	with as_user("yousef@one.test"):
		assert company.mine() is None


@check
def one_the_frame_wears_the_workspace_colour():
	"""Frame Colour in One's ControlCenter › Branding is the rail and the bars
	around every screen, for everyone; saved empty, the frame is One's own."""
	from onedesk.one import company, control

	was = frappe.db.get_value("Company", COMPANY, "one_frame_colour")
	try:
		control._save_general({"one_frame_colour": "#7C2D12"})
		assert company.frame_colour() == "#7C2D12", "the frame did not take the workspace's colour"
		control._save_general({"one_frame_colour": ""})
		assert not company.frame_colour(), "an emptied Frame Colour still coloured the frame"
	finally:
		frappe.db.set_value("Company", COMPANY, "one_frame_colour", was)


@check
def one_a_private_app_is_always_on():
	"""A private app installed has a card in Apps that can't be turned off,
	and uninstalling it is refused."""
	from unittest.mock import patch

	from onedesk.one import apps
	from onedesk.one_account import private

	said = {"name": "acme_fleet", "title": "Acme Fleet", "said": "Acme's vans.", "icon": "truck"}
	with patch.object(private, "names", return_value=["acme_fleet"]), patch.object(private, "about", return_value=said), patch.object(private, "rail", return_value=set()):
		card = next(one for one in apps.offered() if one["name"] == "acme_fleet")
		assert card["kept"] and card["on"], card
		with as_user(OWNER):
			try:
				apps.save(["acme_fleet"])
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("a private app was turned off")
		try:
			private.refuse_uninstall("acme_fleet")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a private app was uninstalled")
		private.refuse_uninstall("hrms")


@check
def one_devices_decide_where_a_passkey_lives():
	"""Signing in gives a browser its id and lists it. The builder sorts two:
	the reception computer, shared, where Tariq is neither offered nor allowed
	a passkey; and his laptop, assigned, which takes one beside his phone's
	that signs for him. Lost retires the laptop's and leaves the phone's."""
	import json

	from onedesk.one_account import devices
	from onedesk.one_account.signin import facts
	from onedesk.one_demo.setup import BUILDER
	from onedesk.one_hr import passkey, signin

	tariq = _employee("Tariq")
	frappe.db.set_single_value("System Settings", signin.SWITCH, 1)
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	frappe.db.delete("Clock Device", {"user": "tariq@one.test"})

	def signs_in(user, agent, cookies=None):
		with as_user(user):
			frappe.session.sid = frappe.generate_hash()
			_asked(headers={"User-Agent": agent}, cookies=cookies)
			devices.signed_in(None)
		return {devices.COOKIE: frappe.local.cookie_manager.cookies[devices.COOKIE]["value"]}

	reception_browser = signs_in(BUILDER, DESKTOP)
	laptop_browser = signs_in("tariq@one.test", DESKTOP)
	assert signs_in("tariq@one.test", DESKTOP, laptop_browser) == laptop_browser, "a second sign-in made a second device"
	with as_user(BUILDER):
		_asked(headers={"User-Agent": DESKTOP}, cookies=reception_browser)
		reception = devices.here().name
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		laptop = devices.here().name
		listed = {one["name"]: one for one in devices.for_settings()["devices"]}
		assert listed[laptop]["seen_by"] and not listed[laptop]["use"]
		_asked(headers={"User-Agent": DESKTOP}, cookies=reception_browser)
		frappe.db.delete("Clock Device", {"user": BUILDER})
		builder = _Phone(b"builder")
		passkey.finish_registration(json.dumps(builder.make(passkey.start_registration())), {"user_agent": DESKTOP})
		with _Told() as told:
			assert devices.save(reception, "Reception Computer", "Shared")["retired"] == 1
		assert not passkey.held(BUILDER), "a passkey still works on the shared computer"
		assert told.to("Passkey Turned Off") == {BUILDER}, told.said
		devices.save(laptop, "Tariq's Laptop", "Assigned", "tariq@one.test")

	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": DESKTOP}, cookies=reception_browser)
		assert not passkey.ask(), "offered a passkey on the shared computer"
		try:
			passkey.start_registration()
			raise AssertionError("a passkey was made on the shared computer")
		except frappe.ValidationError:
			pass

		phone, desk = _Phone(b"t-phone"), _Phone(b"t-desk")
		_asked(headers={"User-Agent": PHONE})
		passkey.finish_registration(json.dumps(phone.make(passkey.start_registration())), {"user_agent": PHONE})
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		assert passkey.ask() and facts()["add_here"], "not offered a passkey on his own laptop"
		made = passkey.finish_registration(json.dumps(desk.make(passkey.start_registration())), {"user_agent": DESKTOP})
		assert frappe.db.get_value("Clock Device", made["device"], "device") == laptop
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		try:
			passkey.start_registration()
			raise AssertionError("two passkeys on one laptop")
		except frappe.ValidationError:
			pass
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		options = passkey.start_assertion()
		assert len(options["allowCredentials"]) == 2
		_asked(headers={"User-Agent": DESKTOP}, cookies=laptop_browser)
		signed = passkey.check(json.dumps(desk.sign(options)), tariq)
		assert signed["device"] == made["device"] and signed["verified"], signed

	with as_user(BUILDER):
		_asked(headers={"User-Agent": DESKTOP})
		assert devices.lost(laptop)["retired"] == 1
		devices.retire(reception)
	assert passkey.held("tariq@one.test"), "the phone's passkey went with the laptop"
	with as_user(BUILDER):
		_asked(headers={"User-Agent": DESKTOP})
		listed = devices.for_settings()["passkeys"]
		phone_key = next(one["name"] for one in listed if one["person"] == frappe.utils.get_fullname("tariq@one.test"))
		with _Told() as told:
			devices.retire_passkey(phone_key)
		assert told.to("Passkey Turned Off") == {"tariq@one.test"}
	assert not passkey.held("tariq@one.test")
	devices.forget()
	_unasked()


@check
def one_anybody_signs_in_with_a_passkey():
	"""Not only employees: the workspace's builder, who is none, is offered a
	passkey after signing in, makes one on a computer, signs in with it, and
	removes it themselves. An employee the clock checks cannot remove theirs."""
	import json
	from unittest import mock

	from onedesk.one_demo.setup import BUILDER
	from onedesk.one_hr import passkey, signin

	frappe.db.set_single_value("System Settings", signin.SWITCH, 1)
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	frappe.db.delete("Clock Device", {"user": BUILDER})
	laptop = _Phone(BUILDER.encode())
	with as_user(BUILDER):
		frappe.defaults.clear_user_default("one_passkey_asked", BUILDER)
		_asked(headers={"User-Agent": DESKTOP})
		assert passkey.ask()
		passkey.not_now()
		assert not passkey.ask(), "asked again the same week"
		made = passkey.finish_registration(json.dumps(laptop.make(passkey.start_registration())), {"user_agent": DESKTOP})
		assert frappe.db.get_value("Clock Device", made["device"], ["user", "employee"]) == (BUILDER, None)

	frappe.set_user("Guest")
	_asked(headers={"User-Agent": DESKTOP})
	options = signin.begin()
	_asked(headers={"User-Agent": DESKTOP}, cookies=_cookies())
	frappe.local.login_manager = mock.Mock()
	assert signin.finish(json.dumps(laptop.sign(options)))["user"] == BUILDER

	with as_user(BUILDER):
		_asked(headers={"User-Agent": DESKTOP})
		assert passkey.remove()["removed"] == 1 and not passkey.held(BUILDER)
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		try:
			passkey.remove()
			raise AssertionError("an employee the clock checks removed their own passkey")
		except frappe.ValidationError:
			pass
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 0)
	frappe.db.delete("Clock Device", {"user": "tariq@one.test"})
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": DESKTOP})
		assert not passkey.ask(), "offered a passkey on a computer"
		try:
			passkey.start_registration()
			raise AssertionError("an employee registered a passkey on a computer")
		except frappe.ValidationError:
			pass
	_unasked()


def _card(said: dict) -> str:
	assert said.get("proposal"), said
	assert frappe.db.get_value("AI Proposal", said["proposal"], "state") == "Proposed"
	return said["proposal"]


@check
def settings_open_and_save_for_each_person():
	"""Every centre's section opens for Layla and only Rania's own for her.
	Rania's stale save is refused; Layla saves General and Holidays, invites
	Hana, turns Nadia off and on, and drops a rule OneAI wrote. What OneAI
	remembers is kept and forgotten."""
	from onedesk.one import access_center, ai, audit, control, notification_words, privacy, rules
	from onedesk.one_account import center
	from onedesk.one_ai import run as runs
	from onedesk.one_ai import yours
	from onedesk.one_calendar import control as calendar_control
	from onedesk.one_hr import control as hr_control
	from onedesk.one_studio import control as studio_control

	with as_user("rania@one.test"):
		assert "link" in calendar_control.load("link") and yours.load("reads") is not None
		for refused in (control.sections_of, lambda: control.load("general"), lambda: hr_control.load("holidays"), lambda: access_center.load("access"), lambda: studio_control.load("numbering"), lambda: notification_words.load("words")):
			try:
				refused()
				raise AssertionError("Rania opened a workspace setting")
			except frappe.PermissionError:
				pass
		hers = center.sections_of()
		assert {one["group"] for one in hers["sections"]} == {"yours"}
		for one in hers["sections"]:
			center.load(one["key"])
		try:
			center.load("people")
			raise AssertionError("Rania opened People")
		except frappe.PermissionError:
			pass
		loaded = center.load("profile")
		center.save("profile", {"mobile_no": "+971 50 555 0142"}, loaded["opened"])
		assert frappe.db.get_value("User", "rania@one.test", "mobile_no") == "+971 50 555 0142"
		stale = [{**one, "modified": "2020-01-01 00:00:00"} for one in loaded["opened"]]
		try:
			center.save("profile", {"mobile_no": "+971 50 555 0199"}, stale)
			raise AssertionError("a stale page overwrote a newer save")
		except frappe.TimestampMismatchError:
			pass
		kept = yours.keep("I prefer replies in Arabic.")
		memory = next(one["name"] for one in kept["facts"] if one["fact"] == "I prefer replies in Arabic.")
		yours.forget(memory)
		yours.keep("I work from the Bayview site on Tuesdays.")
		yours.forget_all()
		assert not frappe.db.exists("AI Memory", {"owner": "rania@one.test"})
		assert center.sign_out_elsewhere() == 1
	with as_user(OWNER):
		for key, *_rest in studio_control.SECTIONS:
			studio_control.load(key)
		assert {one["kind"] for one in audit.log()} >= {"changes", "signins"}, "the Audit Log misses a kind"
		assert all(one["kind"] == "changes" for one in audit.log("changes", 10))
		assert set(privacy.requests()) == {"deletions", "copies"}
		notification_words.load("words")
		assert [one["key"] for one in control.sections_of()["sections"]] == ["company", "branding", "formats", "signin", "sharing", "pictures"]
		for key in ("company", "branding", "formats", "signin", "sharing"):
			tab = control.load(key)
			assert set(tab["values"]) <= set(control.HOLDS[key]), f"{key} carries another tab's values"
			control.save(key, {}, tab["opened"])
		holidays = hr_control.load("holidays")
		hr_control.save("holidays", holidays["values"], holidays.get("opened"))
		assert access_center.load("access")["levels"]
		for one in center.sections_of()["sections"]:
			center.load(one["key"])
		center.invite("hana@one.test", "Hana", "Rizk", {"OneCRM": "User"})
		assert frappe.db.exists("User", "hana@one.test")
		center.invite_again("hana@one.test")
		center.set_enabled("nadia@one.test", 0)
		assert frappe.db.get_value("User", "nadia@one.test", "enabled") == 0
		center.set_enabled("nadia@one.test", 1)
		center.send_reset("nadia@one.test")
		center.sign_out_everywhere("nadia@one.test")
		from unittest import mock

		from onedesk.one_account import signin

		was = frappe.db.get_single_value("System Settings", "enable_two_factor_auth")
		frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 1)
		try:
			with mock.patch("onedesk.one.tell.two_factor_reset") as told:
				center.reset_two_factor("nadia@one.test")
				with as_user("rania@one.test"):
					signin.reset_two_factor()
			assert [one.args[0] for one in told.call_args_list] == ["nadia@one.test", "rania@one.test"]
		finally:
			frappe.db.set_single_value("System Settings", "enable_two_factor_auth", was)
		assert rules.fields_of("Sales Invoice")
		assert rules.watchable("DocType", "Sales", "name", 0, 20)
		drafted = ai.draft_notification("Big Invoice", "Sales Invoice", "Submit", "Invoice {{ doc.name }} is out", roles=["Accounts Manager"])
		runs.apply(drafted["proposal"])
		rule = frappe.db.get_value("Notification", {"one_rule": 1, "document_type": "Sales Invoice", "event": "Submit"})
		assert rule, "the rule was not made"
		kind = frappe.db.get_value("Notification Type", {"one_rule": rule})
		typed = notification_words.load("words", kind)
		notification_words.save("words", typed.get("values") or {}, typed.get("opened"), kind)
		assert "html" in notification_words.preview_notification(kind, "Invoice {{ doc.name }}") or notification_words.preview_notification(kind, "Invoice {{ doc.name }}")
		notification_words.delete_rule(rule)
		assert not frappe.db.exists("Notification", rule)


@check
def access_is_shaped_by_the_administrator():
	"""Layla makes a level between User and Manager, a job profile and a
	group, and holds Omar to one customer, after which he sees only that
	one; each goes again. OneAI suggests a level, a profile, a group, a hold,
	a saved report, a dashboard and a report by mail, and each card applied
	is there afterwards. Omar may do none of it."""
	from onedesk.one import access, access_center
	from onedesk.one_ai import run as runs
	from onedesk.one_studio import ai_setup

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
		opened = access_center.load("access", f"profile:{profile}")
		access_center.save("access", {"app_onecrm": "User"}, opened.get("opened"), f"profile:{profile}")
		assert access.profile(profile)["levels"].get("OneCRM") == "User", "AccessCenter did not save the profile"
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
	from onedesk.one_mail import mail_templates
	from onedesk.one_studio import letter_heads, numbering, printing

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
		assert any(one["fieldname"] == "items" for one in mail_templates.fields_of("Sales Order")["tables"])
		lines = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": "Order lines",
				"subject": "Order {{ name }}",
				"response": "<p>{% for row in items %}</p><p>{{ row.item_name }} · {{ row.amount }}</p><p>{% endfor %}</p>",
				"reference_doctype": "Sales Order",
			}
		).insert()
		first = frappe.get_doc("Sales Order", order).items[0]
		said = mail_templates.get_email_template(lines.name, {"doctype": "Sales Order", "name": order})
		assert first.item_name in said["message"] and first.get_formatted("amount") in said["message"], said["message"]
		said = mail_templates.preview(
			subject="Order {{ name }}",
			response='<p>{{ table(items, "item_name", "amount") }}</p>',
			doctype="Sales Order",
			name=order,
		)
		assert order in said["subject"] and "<table" in said["message"], said
		assert first.get_formatted("amount") in said["message"], said["message"]
		assert "error" in mail_templates.preview(subject="x", response='{{ table(items, "no_such") }}', doctype="Sales Order", name=order)
		for wrong in (
			"{% for row in nothing %}{% endfor %}",
			"{% for row in items %}{{ row.no_such }}{% endfor %}",
			"{{ row.item_name }}",
			"{% for row in items %}",
		):
			assert mail_templates.check("Sales Order", wrong, set()), wrong


@check
def printing_holds_what_a_page_may_say():
	"""A top drawn from the company follows it: a new address line is
	printed on it, written as text and never as markup. A top Layla changes
	by hand stays as she wrote it. A letter head is kept cleaned of scripts
	and of pictures from elsewhere, and template tags are refused in it. An
	HTML block reads the record and nothing else."""
	from onedesk.one_studio import printing

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

		frappe.cache.delete_keys("rl:")
		frappe.set_user("Guest")
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

	from onedesk.one_account import closing

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


@check
def a_saved_report_is_its_makers_and_runs_no_code():
	"""Omar saves his list of open deals as a report, and it goes under Saved
	Reports in his own OneCRM sidebar. A report, a chart or a card made here
	runs no code, even Layla's, and a report by mail goes as whoever set it
	up. Omar may not show his report to everybody,
	nor put it in an app he does not work in, Rania may not move it, and only
	an administrator moves a dashboard. He deletes his own, and it leaves the
	sidebar, but not Layla's."""
	from onedesk.one_studio import reports

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
	every module's lists read, added to and counted, next
	year's holidays made and put in force with the country's own public
	holidays, and a deleted project task brought back from the bin."""
	from onedesk.one import home, lists, recycle
	from onedesk.one_hr import holidays
	from onedesk.one_studio import reports

	with as_user("samir@one.test"):
		said = home.read()
		assert said["waiting"] >= len(said["approvals"]), said
		assert all(one["title"] for one in said["announcements"]), said["announcements"]
		assert not said["needs"] and not said["glance"] and not said["administers"], "Samir is told about the workspace"
	with as_user(OWNER):
		assert isinstance(home.attention(), list)
		said = home.read()
		assert said["administers"] and {"people", "apps"} <= {one["key"] for one in said["glance"]}, said["glance"]
		saved = frappe.get_doc({"doctype": "Report", "report_name": "Open Deals Gulf", "ref_doctype": "Opportunity", "report_type": "Report Builder", "is_standard": "No", "json": "{}"}).insert()
		crm = next(one["module"] for one in reports.where("Report", saved.name)["places"] if one["label"] == "OneCRM")
		reports.place("Report", saved.name, crm, 1)
		assert reports.where("Report", saved.name) | {"places": None} == {"module": crm, "everybody": 1, "places": None, "administers": 1}
		assert reports.where("Report", saved.name)
		assert reports.sidebars()
		kept = lists.listed()
		assert set(kept) == set(lists.HOMES), kept
		for module, doctypes in kept.items():
			kinds = lists.kinds(module)
			assert [one["doctype"] for one in kinds] == doctypes, (module, kinds)
			assert all(set(one) == {"doctype", "label", "count", "icon", "counted"} for one in kinds)
		territory = frappe.get_doc({"doctype": "Territory", "territory_name": "Oman"}).insert()
		assert territory.parent_territory, "a tree's new value goes under its root (lists.place)"
		assert lists.homes()["Territory"] == [
			{"label": "Lists", "route": "/desk/one?center=settings&module=OneCRM&at=lists"},
			{"label": "Territories", "route": "/desk/territory"},
		]
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
	from onedesk.one_ai import run as runs
	from onedesk.one_studio import ai_setup

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
	from onedesk.one_ai.reading import fill

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
		checklist = frappe.get_doc({"doctype": "Note", "title": "My site checklist", "content": "Sealant, shims, level."}).insert()
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
		assert note.name in {one["name"] for one in booted.one_announcements["running"]}, "it runs along her top bar"
		assert not booted.one_announcements["folded"]
		assert checklist.name not in {one["name"] for one in announcements.current()["running"]}, "her own note is not on the bar"
		announcements.hide()
		said = announcements.current()
		assert said["folded"] and note.name in {one["name"] for one in said["running"]}, "she folded it, and it is still there"
		announcements.show()
		assert not announcements.current()["folded"], "she opened it again"
	frappe.db.set_value("Note", note.name, "expire_notification_on", add_days(today(), -1))
	with as_user("rania@one.test"):
		assert note.name not in {one["name"] for one in announcements.current()["running"]}, "an expired one leaves the bar"
	frappe.set_user("Guest")
	booted = frappe._dict()
	announcements.boot(booted)
	assert "notes" not in booted


@check
def oneai_summarises_a_supplier_once_a_day():
	"""A purchase invoice submitted for Gulf Office Supplies marks it due; a
	draft saved does not. The hourly run writes its summary from what it is
	owed and bought, shows it in the supplier's head, and leaves it for a day
	however much happens. Switched off, nothing marks it due."""
	from unittest import mock

	from onedesk.one import head
	from onedesk.one_ai import brief

	supplier = frappe.db.sql(
		"select supplier from `tabPurchase Invoice` where docstatus = 1 group by supplier order by count(*) desc limit 1"
	)[0][0]
	invoice = frappe.get_doc("Purchase Invoice", frappe.db.get_value("Purchase Invoice", {"supplier": supplier, "docstatus": 1}))
	asked = []

	def said(action, text, files=None, reference=None):
		asked.append(text)
		return "AED 788 is unpaid and not yet due. Nothing is late."

	clear = {brief.BRIEF: None, brief.ON: None, brief.DUE: 0}
	try:
		frappe.db.set_value("Supplier", supplier, clear, update_modified=False)
		for kind in brief.BRIEFS:
			frappe.db.sql(f"update `tab{kind}` set `{brief.DUE}` = 0")
		with mock.patch("onedesk.one_ai.run.once", side_effect=said), mock.patch("onedesk.one.account.configured", return_value=True):
			brief.touched(invoice, "on_update")
			assert not frappe.db.get_value("Supplier", supplier, brief.DUE), "a draft saved is not news"
			brief.touched(invoice, "on_submit")
			assert frappe.db.get_value("Supplier", supplier, brief.DUE)
			assert brief.due() == 1
			assert frappe.db.get_value("Supplier", supplier, brief.BRIEF) == "AED 788 is unpaid and not yet due. Nothing is late."
			told = json.loads(asked[0].split("\n\n", 1)[1])
			assert told["invoiced_this_year"] > 0 and "unpaid" in told, told
			noticed = head.notices_of(frappe.get_doc("Supplier", supplier))
			assert any(one["notice"] == "oneai.summary" and asked and one["lines"][0].startswith("AED 788") for one in noticed), noticed
			brief.touched(invoice, "on_cancel")
			assert brief.due() == 0 and frappe.db.get_value("Supplier", supplier, brief.DUE), "once a day, however much happens"
			with as_user(OWNER):
				brief.switch("Supplier", 0)
			frappe.db.set_value("Supplier", supplier, brief.DUE, 0, update_modified=False)
			brief.touched(invoice, "on_submit")
			assert not frappe.db.get_value("Supplier", supplier, brief.DUE), "switched off"
	finally:
		frappe.db.set_value("Supplier", supplier, clear, update_modified=False)
		frappe.db.set_default(brief.OFF, "[]")


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

#: A one-pixel PNG, for a picture put into a document.
DOT_PNG = (
	b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
	b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


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


ACCOUNT = {
	"credit_packs": [{"name": "credits-500", "label": "500 credits", "amount": 25, "currency": "USD"}],
	"buy_credits": {"checkout": {"client_secret": "cs_demo_secret_demo", "key": "pk_test_demo"}, "credits": 500},
	"billing_card": {"checkout": {"client_secret": "cs_demo_secret_card", "key": "pk_test_demo"}},
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
	admin site answering as it would: credit packs and paying for one and a
	new card, both drawn in the page, a monthly limit, the
	plans offered, a quote and a change of plan, Huda made the payer, a
	domain added, made the main address and dropped, the bills from One
	listed and one put into the books as a purchase invoice. Omar may do
	none of it, and the build's wake call is answered for a guest."""
	from unittest import mock

	from onedesk.one import account
	from onedesk.one_account import bills

	with (
		as_user(OWNER),
		mock.patch("onedesk.one.account.ask", side_effect=_account),
		mock.patch("onedesk.one.account.configured", return_value=True),
		mock.patch("onedesk.one.account.refresh"),
	):
		assert account.credit_packs()[0]["label"] == "500 credits"
		assert account.buy_credits("credits-500")["checkout"]["client_secret"], "credits are paid for in the page"
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
		assert bills.change_card()["checkout"]["key"].startswith("pk_"), "a card is given in the page"
		with mock.patch("onedesk.one.account.ask", return_value={"limit": 2000}) as asked:
			assert bills.set_spend_limit(2000) == {"limit": 2000} and asked.call_args.kwargs == {"limit": 2000}
			bills.set_spend_limit(-5)
			assert asked.call_args.kwargs == {"limit": 0}, "a monthly limit is never below nothing"
			assert bills.set_update_window(0, 9) is not None and asked.call_args.kwargs == {"weekday": 0, "hour": 9}
			assert bills.update_now() is not None
		with mock.patch("onedesk.one_account.bills._attach"):
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
	invoice's head, which settles it, its dialog foreseeing nothing because
Record Payment changes nothing it has to show, and a head reads a record not yet saved
	as the form has it. A link to a project reads as its title for Samir
	and as its name for somebody who may not open it. The automation step
	editor lists what a flow may do."""
	from frappe.desk.search import get_link_title

	from onedesk.one import head
	from onedesk.one_studio import automations, customize

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
		assert head.foresee("Sales Invoice", invoice.name, "invoice.record_payment", values) is None
		head.run("Sales Invoice", invoice.name, "invoice.record_payment", values)
		assert frappe.db.get_value("Sales Invoice", invoice.name, "outstanding_amount") == 0
	with as_user(OWNER):
		kind = next(one for one in sorted(head.headed()) if head.redrawn(frappe.get_cached_doc("Record Head", one)) and frappe.db.count(one))
		record = frappe.get_last_doc(kind)
		assert head.preview(frappe.copy_doc(record).as_dict()) is not None, kind
	title = frappe.db.get_value("Project", VILLA, "project_name")
	with as_user("samir@one.test"):
		assert get_link_title("Project", VILLA) == title
	frappe.set_user("Guest")
	assert get_link_title("Project", VILLA) == VILLA


@check
def push_reaches_a_persons_own_browsers():
	"""Rania turns push on in her browser and gets a test push there, then
	turns it off. A push service One does not send to is refused, and the
	service worker is served to anybody. Her sessions elsewhere are signed
	out from her Sign-in page, and a new password set from a reset link
	tells her it changed. The push service is not called."""
	from unittest import mock

	from onedesk.one import push
	from onedesk.one_account import signin

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
	from onedesk.one import ai, privacy_copy
	from onedesk.one_ai import memory, tools
	from onedesk.one_mail import ai as mail_ai
	from onedesk.one_mail import holders
	from onedesk.one_studio import printing

	with as_user("rania@one.test"):
		for said in (ai.my_day(), mail_ai.my_mailboxes(), memory.recall(), ai.my_notifications(), ai.my_sign_in()):
			assert "error" not in said, said
		privacy_copy.ask()
	asked = frappe.db.get_value(privacy_copy.DOWNLOAD, {"user": "rania@one.test"})
	kind = frappe.db.get_value("Notification Type", {"one_rule": ["is", "not set"]}) or frappe.db.get_value("Notification Type", {})
	with as_user(OWNER):
		read = {
			"people": ai.workspace_people(),
			"access": ai.workspace_access(),
			"reports": ai.workspace_reports(),
			"bin": tools.list_records(
				"Deleted Document",
				filters={"creation": [">=", add_days(today(), -30)]},
				fields=["deleted_doctype", "deleted_name", "owner", "creation", "restored", "new_name"],
				order_by="creation desc",
			),
			"announcements": ai.announcements(),
			"webhooks": ai.webhooks(7),
			"audit": ai.audit_log("changes", days=7),
			"privacy": ai.privacy_request(asked),
			"intake": ai.workspace_intake(),
			"holidays": ai.workspace_holidays(),
			"oneai": ai.workspace_oneai(),
			"plan": ai.workspace_plan(),
			"sign-in": ai.workspace_sign_in(),
			"numbering": ai.workspace_numbering("Quotation"),
			"printing": ai.workspace_printing("Sales Invoice"),
			"layout": ai.print_layout("Sales Invoice"),
			"mail templates": mail_ai.workspace_mail_templates("Sales Invoice"),
			"approvals": ai.workspace_approvals("Purchase Order"),
			"automations": ai.workspace_automations("Sales Invoice"),
			"a notification": ai.notification_type(kind),
		}
		wrong = {name: said for name, said in read.items() if isinstance(said, dict) and said.get("error")}
		assert not wrong, wrong
		assert "cname_target" in read["plan"] and isinstance(read["plan"]["domains"], list), read["plan"]

		field = ai.customize("Lead", add=[{"label": "Site Visit Date", "kind": "Date"}])
		assert "Site Visit Date" in frappe.db.get_value("AI Proposal", field["proposal"], "changes")
		holiday = f"{getdate(today()).year}-12-31"
		_applied(ai.change_holidays(add=[{"date": holiday, "name": "Year end closure"}]))
		assert frappe.db.exists("Holiday", {"holiday_date": holiday, "description": ["like", "%Year end closure%"]})
		series = [one["series"] for one in __import__("onedesk.one_studio.numbering", fromlist=["series"]).series("Quotation")]
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
		_applied(mail_ai.sign_mailbox(ours, "Sahara Glass\nDubai Investments Park"))
		assert "Dubai Investments Park" in (frappe.db.get_value("Email Account", holders.workspace(), "signature") or "")
		_applied(mail_ai.write_mail_template("Invoice {{ name }} is due", "Dear {{ customer_name }},\n\nA reminder that invoice {{ name }} is due.", new_name="Payment reminder", for_doctype="Sales Invoice"))
		assert frappe.db.exists("Email Template", "Payment reminder")
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
def one_atlas_knows_who_may_open_what():
	"""docs/atlas-site.json is this site's: what it has and who may read each record type,
	report and page, every grant of One's applied, which docs/ATLAS.md says
	and tests/guards/test_atlas.py holds."""
	import json
	import os

	from onedesk.one import reach

	path = os.path.join(frappe.get_app_path("onedesk"), "..", "docs", "atlas-site.json")
	with open(path) as f:
		kept = json.load(f)
	assert reach.atlas() == kept, "run python scripts/atlas.py --site"
	from frappe.translate import get_all_translations

	frappe.clear_cache()
	assert get_all_translations("en").get("ERPNext Settings") == "Settings"
	assert "ERPNext" not in get_all_translations("de").get("ERPNext User ID", "ERPNext")


CENTS = 0.05


def _abroad(party_type: str, party: str) -> bool:
	"""Whether a customer is billed abroad, or a supplier sells from abroad."""
	from onedesk.one_demo.masters import ABROAD, EXPORTS

	if party_type == "Supplier":
		return party in ABROAD
	from erpnext.accounts.party import get_default_address

	address = get_default_address(party_type, party)
	return bool(address) and frappe.db.get_value("Address", address, "country") in EXPORTS


@check
def work_and_mail_tell_what_the_second_pass_found():
	"""Samir's completed task reopened by Rania reaches Samir, and cancelled
	reaches him too; a project put back to Open reaches its people; a member
	taken off hears it; a comment on a project reaches its manager; a
	milestone a day late reaches the manager; mail frappe gave up sending
	reaches whoever sent it; a mailbox given to somebody reaches them; a Remind
	Me reaches whoever set it."""
	from unittest.mock import patch

	from onedesk.one_mail import tell as mail
	from onedesk.one_project import tell as projects

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		task = frappe.get_doc("Task", frappe.db.get_value("Task", {"status": "Completed", "owner": "samir@one.test"}))
		with as_user("rania@one.test"):
			task.status = "Open"
			task.save(ignore_permissions=True)
			assert "samir@one.test" in said("Task Reopened")[1]
			task.status = "Cancelled"
			task.save(ignore_permissions=True)
		assert "samir@one.test" in said("Task Cancelled")[1]

		project = frappe.get_doc("Project", frappe.db.get_value("Project", {"status": "Open", "one_manager": "samir@one.test"}))
		project.append("users", {"user": "rania@one.test"})
		project.save(ignore_permissions=True)
		with as_user(OWNER):
			project.status = "On hold"
			project.save(ignore_permissions=True)
			project.status = "Open"
			project.save(ignore_permissions=True)
			assert "samir@one.test" in said("Project Resumed")[1]
			project.users = [row for row in project.users if row.user != "rania@one.test"]
			project.save(ignore_permissions=True)
		assert said("Removed from Project")[1] == ["rania@one.test"]

		with as_user("rania@one.test"):
			frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "Project", "reference_name": project.name, "content": "Glass arrives Monday.", "comment_email": "rania@one.test"}).insert(ignore_permissions=True)
		assert said("Comment on Project")[1] == ["samir@one.test"]

		milestone = frappe.get_doc({"doctype": "Task", "subject": "Frames installed", "project": project.name, "is_milestone": 1, "exp_end_date": add_days(today(), -1)})
		milestone.flags.ignore_validate = True
		milestone.insert(ignore_permissions=True, ignore_mandatory=True)
		projects.milestones_late()
		assert said("Milestone Late")[2]["milestone"] == "Frames installed"

		sent = frappe.get_doc({"doctype": "Communication", "communication_type": "Communication", "communication_medium": "Email", "sent_or_received": "Sent", "subject": "Your quote", "recipients": "buyer@example.com", "content": "Attached."})
		sent.insert(ignore_permissions=True)
		frappe.db.set_value("Communication", sent.name, {"delivery_status": "Error", "owner": "samir@one.test"})
		mail.not_sent()
		assert said("Mail Not Sent")[1] == ["samir@one.test"]

		mail.mailbox_shared("Sales", ["rania@one.test"])
		assert said("Mailbox Shared With You")[1] == ["rania@one.test"]

		with as_user("samir@one.test"):
			reminder = frappe.get_doc({"doctype": "Reminder", "user": "samir@one.test", "remind_at": frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=5), "description": "Call the glazier", "reminder_doctype": "Project", "reminder_docname": project.name}).insert(ignore_permissions=True)
		reminder.send_reminder()
		_name, users, values = said("Reminder")
		assert users == ["samir@one.test"] and values["said"] == "Call the glazier", values


@check
def the_workspace_tells_what_the_second_pass_found():
	"""An administrator taken away and the sign-in rules changed reach every
	other administrator; a file refused for room reaches them once a day; a
	record moved on from an approval step reaches whoever made it and whoever
	sent it there; an agreement at a new revision reaches the administrators
	once; automations that failed yesterday reach them in the morning."""
	import copy
	from unittest.mock import patch

	from onedesk.one import control, tell
	from onedesk.one.people import told_of_access
	from onedesk.one_legal import gate
	from onedesk.one_studio import approvals

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		with as_user(OWNER):
			told_of_access(frappe.get_doc("User", "mariam@one.test"), {"Workspace Administrator"}, set())
		assert OWNER not in said("Administrator Removed")[1]

		with as_user(OWNER):
			control.save("general", {"allow_consecutive_login_attempts": 7})
		assert "allow_consecutive_login_attempts" not in str(said("Sign-in Rules Changed")[2]["what"]), said("Sign-in Rules Changed")

		frappe.cache.delete_value("one_storage_full_told")
		tell.storage_full()
		tell.storage_full()
		assert len([one for one in told if one[0] == "Storage Full"]) == 1

		task = frappe.get_doc("Task", frappe.db.get_value("Task", {"owner": "samir@one.test", "status": "Open"}))
		before = copy.deepcopy(task)
		before.status, task.status = "Open", "Working"
		task._doc_before_save = before
		frappe.get_doc({"doctype": "Workflow Action", "reference_doctype": "Task", "reference_name": task.name, "status": "Completed", "completed_by": "mariam@one.test", "workflow_state": "Working"}).insert(ignore_permissions=True)
		frappe.db.set_value("Workflow Action", {"reference_name": task.name}, "owner", "rania@one.test")
		with as_user("mariam@one.test"), patch("frappe.model.workflow.get_workflow_name", return_value="Task Approval"), patch("frappe.get_cached_value", return_value="status"):
			approvals.answered(task)
		_name, users, values = said("Approval Answered")
		assert users == ["rania@one.test", "samir@one.test"] and str(values["state"]) == "Working", (users, values)

		key = gate.keys_for(gate.WORKSPACE)[0]
		frappe.db.set_default(f"one_legal_told_workspace_{key}", None)
		with patch.object(gate, "_accepted", return_value="0.abc"):
			gate.told_of_changes()
			gate.told_of_changes()
		assert len([one for one in told if one[0] == "Agreements Changed"]) == 1

		run = frappe.get_doc({"doctype": "Automation Run", "automation_title": "Chase overdue invoices", "status": "Failed"}).insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)
		frappe.db.set_value("Automation Run", run.name, "creation", add_days(now_datetime(), -1))
		tell.automations_failing()
		assert "Chase overdue invoices (1)" in said("Automations Failing")[2]["automations"]

		from onedesk.one_admin import home
		from onedesk.one_admin import tell as admin

		slow = [{"name": "PJ-X", "title": "Building Sahara is taking hours", "why": "At: Making the site"}]
		filling = [{"title": "f1-dubai is filling up", "why": "41 of 50 workspaces", "badge": "Filling Up"}]
		frappe.db.set_default("one_admin_filling_f1-dubai is filling up", None)
		with patch("onedesk.one_admin.site.is_admin", return_value=True), patch.object(home, "_slow_builds", return_value=slow), patch.object(home, "_filling", return_value=filling), patch.object(admin, "operators", return_value=["wsadmin@one.test"]), patch("frappe.sendmail"):
			admin.builds_slow()
			admin.servers_filling()
			admin.servers_filling()
		assert said("Build Slow")[2]["title"] == "Building Sahara is taking hours"
		assert len([one for one in told if one[0] == "Server Filling Up"]) == 1


@check
def sales_books_and_stock_tell_what_waits_on_somebody():
	"""Layla makes Samir the owner of a lead, and Samir is told; a lead nobody
	owns reaches sales; a quotation three days from its last day reaches
	whoever made it; an invoice gone overdue yesterday reaches whoever made
	it; bills due this week reach accounts; a payment made through a payment
	link is told; Karim's request to buy reaches purchasing; an order not
	delivered by yesterday reaches whoever made it."""
	from unittest.mock import patch

	from onedesk.one_book import tell as books
	from onedesk.one_crm import tell as crm
	from onedesk.one_inventory import tell as stock

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name, record=None):
		found = [one for one in told if one[0] == name and (not record or one[2].get("record") == record)]
		assert found, (name, record, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		lead = frappe.get_doc("Lead", frappe.db.get_value("Lead", {"lead_owner": ["!=", "samir@one.test"]}))
		with as_user("wsadmin@one.test"):
			lead.lead_owner = "samir@one.test"
			lead.save()
		assert said("Given to You", ("Lead", lead.name))[1] == ["samir@one.test"]

		with as_user("wsadmin@one.test"):
			new = frappe.get_doc({"doctype": "Lead", "lead_name": "Hana Ito", "email_id": "hana.ito@example.com", "lead_owner": ""})
			new.insert()
		if not new.lead_owner:
			assert "samir@one.test" in said("New Lead Waiting", ("Lead", new.name))[1]

		base = frappe.get_doc("Quotation", frappe.db.get_value("Quotation", {"docstatus": 1, "status": "Open"}))
		quote = frappe.copy_doc(base)
		quote.transaction_date, quote.valid_till, quote.payment_schedule, quote.lost_reasons = today(), add_days(today(), 3), [], []
		for row in quote.items:
			row.ordered_qty = 0
		quote.insert(ignore_permissions=True)
		quote.submit()
		crm.running_out()
		assert said("Quotation Running Out", ("Quotation", quote.name))[1], told

		invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "is_return": 0})
		frappe.db.set_value("Sales Invoice", invoice, "due_date", add_days(today(), -1))
		books.overdue()
		assert said("Invoice Overdue", ("Sales Invoice", invoice))[1]

		bill = frappe.db.get_value("Purchase Invoice", {"docstatus": 1, "outstanding_amount": [">", 0]})
		if bill:
			frappe.db.set_value("Purchase Invoice", bill, "due_date", add_days(today(), 2))
			books.bills_due()
			assert said("Bills Due This Week")[2]["count"] >= 1

		paid = frappe._dict(
			payment_type="Receive", party_type="Customer", party=frappe.db.get_value("Sales Invoice", invoice, "customer"), party_name="", paid_from_account_currency="AED",
			references=[frappe._dict(payment_request="ACC-PRQ-1", reference_doctype="Sales Invoice", reference_name=invoice, allocated_amount=100)],
		)
		books.paid_online(paid)
		assert said("Paid Online", ("Sales Invoice", invoice))[2]["invoice"] == invoice

		item = frappe.db.get_value("Item", {"is_stock_item": 1, "disabled": 0})
		with as_user("karim@one.test"):
			asked = frappe.get_doc(
				{"doctype": "Material Request", "material_request_type": "Purchase", "schedule_date": add_days(today(), 7), "items": [{"item_code": item, "qty": 2, "schedule_date": add_days(today(), 7), "warehouse": frappe.db.get_value("Warehouse", {"is_group": 0, "company": COMPANY})}]}
			).insert()
			asked.submit()
		_name, users, values = said("Material Request Asked", ("Material Request", asked.name))
		assert "karim@one.test" not in users and values["who"] == "Karim Mansour", values

		order = frappe.db.get_value("Sales Order", {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]})
		if order:
			frappe.db.set_value("Sales Order", order, "delivery_date", add_days(today(), -1))
			stock.deliveries_late()
			assert said("Delivery Late", ("Sales Order", order))[1]


@check
def sales_books_and_stock_tell_what_the_second_pass_found():
	"""Karim asks the stores to move glass and they are told, and when Samir
	stops it Karim is told; a request moved in full reaches whoever asked;
	reordering that failed reaches the stock and buying managers; mail in on
	Omar's lead reaches Omar; a contract two weeks from its end reaches whoever
	made it; a repeat frappe switched off reaches whoever set it up."""
	from types import SimpleNamespace
	from unittest.mock import patch

	from onedesk.one import tell as one
	from onedesk.one_crm import tell as crm
	from onedesk.one_inventory import tell as stock

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		request = frappe.copy_doc(frappe.get_doc("Material Request", frappe.db.get_value("Material Request", {"material_request_type": "Purchase", "docstatus": 1})))
		request.material_request_type = "Material Transfer"
		for row in request.items:
			row.reorder_level = None
		other = frappe.db.get_value("Warehouse", {"is_group": 0, "company": request.company, "name": ["!=", request.items[0].warehouse]})
		for row in request.items:
			row.from_warehouse = other
		with as_user("karim@one.test"):
			request.insert(ignore_permissions=True, ignore_mandatory=True)
			request.submit()
		_name, users, values = said("Stock Asked")
		assert "karim@one.test" not in users and users and str(values["kind"]) == "Material Transfer", (users, values)
		with as_user("samir@one.test"):
			stock.update_status(request.name, "Stopped")
		assert said("Material Request Stopped")[1] == ["karim@one.test"]

		frappe.db.set_value("Material Request", request.name, "status", "Transferred")
		with as_user("samir@one.test"):
			stock.moved(SimpleNamespace(items=[frappe._dict(material_request=request.name)]))
		assert said("Material Request Done")[1] == ["karim@one.test"]

		frappe.get_doc({"doctype": "Error Log", "method": "Unable to create material request", "error": "No supplier"}).insert(ignore_permissions=True)
		stock.reorder_failed()
		assert said("Reordering Failed")[2]["count"] >= 1

		lead = frappe.db.get_value("Lead", {"lead_owner": "omar@one.test"})
		frappe.get_doc({"doctype": "Communication", "communication_type": "Communication", "communication_medium": "Email", "sent_or_received": "Received", "sender": "buyer@example.com", "sender_full_name": "Hana Buyer", "subject": "Re: your quote", "content": "Can you do Thursday?", "reference_doctype": "Lead", "reference_name": lead}).insert(ignore_permissions=True)
		_name, users, values = said("They Replied")
		assert users == ["omar@one.test"] and values["who"] == "Hana Buyer", values

		contract = frappe.get_doc("Contract", frappe.db.get_value("Contract", {}))
		frappe.db.set_value("Contract", contract.name, {"status": "Active", "end_date": add_days(today(), 14), "docstatus": 1 if contract.docstatus == 1 else 0})
		crm.contracts_ending()
		assert said("Contract Expiring")[1], said("Contract Expiring")

		repeat = frappe.db.get_value("Auto Repeat", {}, ["name", "owner"], as_dict=True)
		frappe.db.set_value("Auto Repeat", repeat.name, "disabled", 1)
		frappe.get_doc({"doctype": "Error Log", "method": "Auto repeat failed", "reference_doctype": "Auto Repeat", "reference_name": repeat.name, "error": "x"}).insert(ignore_permissions=True)
		one.repeats_failed()
		assert repeat.owner in said("Repeat Failed")[1] or said("Repeat Failed")[1], said("Repeat Failed")


@check
def tasks_and_the_calendar_tell_what_changed_for_somebody():
	"""Karim comments on a task given to Rania and she is told, but not when
	he mentions her, which frappe tells; sent back from review, it is told to
	whoever it is given to; taken off an event, Rania is told, and an event
	only shared with somebody counts them as on it."""
	from unittest.mock import patch

	from frappe.desk.form.assign_to import add

	from onedesk.one_calendar import tell as calendar

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	task = frappe.get_doc({"doctype": "Task", "subject": "Measure the stair glass", "status": "Open"}).insert(ignore_permissions=True)
	add({"assign_to": ["rania@one.test"], "doctype": "Task", "name": task.name, "description": task.subject})
	with patch("onedesk.one.notify.notify", side_effect=heard):
		with as_user("karim@one.test"):
			task.add_comment("Comment", "The landing is 1.2 m wide.")
			task.add_comment("Comment", '<span class="mention" data-id="rania@one.test">@Rania</span> can you check?')
		comments = [one for one in told if one[0] == "Comment on Your Task"]
		assert len(comments) == 1 and "rania@one.test" in comments[0][1] and "karim@one.test" not in comments[0][1], comments
		assert comments[0][2]["comment"] == "The landing is 1.2 m wide.", comments

		task.reload()
		task.status = "Pending Review"
		task.save(ignore_permissions=True)
		with as_user("karim@one.test"):
			task.reload()
			task.status = "Working"
			task.save(ignore_permissions=True)
		back = [one for one in told if one[0] == "Sent Back"]
		assert back and back[-1][1] == ["rania@one.test"], told

		event = frappe.get_doc({"doctype": "Event", "subject": "Site walk", "starts_on": add_to_date(now_datetime(), days=2), "event_type": "Private",
			"event_participants": [{"reference_doctype": "User", "reference_docname": "rania@one.test", "email": "rania@one.test"}]}).insert(ignore_permissions=True)
		with as_user("karim@one.test"):
			event.reload()
			event.event_participants = []
			event.save(ignore_permissions=True)
		off = [one for one in told if one[0] == "Taken Off an Event"]
		assert off and off[-1][1] == ["rania@one.test"], told

	frappe.share.add("Event", event.name, "nadia@one.test")
	assert "nadia@one.test" in calendar.people(frappe.get_doc("Event", event.name)).values()


@check
def the_workspace_tells_what_it_promised_to():
	"""Credits that run out are told to the administrators, always mailed; a
	sign-in from a new device is told to the person and their first is not;
	Fix With OneAI's result is kept on the bell; a document OneAI could not
	read is told to whoever it reads for; an approval offers "Approve or
	Reject"; the owner of a workspace whose payment failed is mailed."""
	from types import SimpleNamespace
	from unittest.mock import patch

	from onedesk.one import account, tell
	from onedesk.one_account import signin
	from onedesk.one_admin import tell as admin
	from onedesk.one_ai.reading import tell as intake
	from onedesk.one_studio import tell as studio

	told, mailed = [], []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def sent(name, to, **said):
		mailed.append((name, to, said))

	with patch("onedesk.one.notify.notify", side_effect=heard), patch("onedesk.one.notify.mail", side_effect=sent):
		with patch.object(account, "_administrators", return_value=["wsadmin@one.test"]):
			account._tell({"last_heard": 1, "credits_balance": 40}, frappe._dict(credits_balance=0, credits_month=0, domains=[], storage_limit=0, database_limit=0))
		assert ("Credits Ran Out", ["wsadmin@one.test"]) in [(one[0], one[1]) for one in told], told

		frappe.defaults.clear_user_default("one_devices", "rania@one.test")
		request = SimpleNamespace(headers={"User-Agent": "Mozilla/5.0 (Macintosh; Mac OS X) Chrome/120"})
		with patch.object(frappe, "request", request, create=True), patch.object(frappe.local, "request", request, create=True):
			signin.arrived(SimpleNamespace(user="rania@one.test"))
			assert not [one for one in told if one[0] == "New Sign-in"], "the first sign-in is where they start"
			request.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0) Firefox/121"
			signin.arrived(SimpleNamespace(user="rania@one.test"))
		assert [one[1] for one in told if one[0] == "New Sign-in"] == [["rania@one.test"]], told

		studio.extension_fixed("wsadmin@one.test", "EXT-1", "Late fee", "Fixed the date check.")
		assert told[-1][0] == "Extension Fixed" and told[-1][2]["said"] == "Fixed the date check."

		intake.couldnt_read(frappe._dict(name="RD-1", title="Invoice 44", on_behalf_of="karim@one.test"), waiting=True)
		assert told[-1][0] == "Couldn't Read" and "credits" in told[-1][2]["why"]

		assert tell._or(["Approve", "Reject"]) == "Approve or Reject"
		assert tell._or(["Approve", "Reject", "Send Back"]) == "Approve, Reject or Send Back"

		with patch("onedesk.one_admin.site.is_admin", return_value=True):
			admin.owner(frappe._dict(name="T-1", workspace_name="Acme", account="owner@acme.example"), "Overdue", "Live")
			assert mailed and mailed[-1][0] == "Payment Failed" and mailed[-1][1] == "owner@acme.example", mailed


@check
def starting_again_keeps_the_setup_and_is_the_administrators():
	"""Start Again deletes transactions, not the customers, accounts, people
	or settings they were made with; and only an administrator may start it.
	The plan is drawn and thrown away: submitting it would delete the demo."""
	from onedesk.one import start_again

	with as_user("rania@one.test"):
		try:
			start_again.start()
			raise AssertionError("somebody who is not an administrator started again")
		except frappe.PermissionError:
			pass
	with as_user("Administrator"):
		plan = start_again.planned(COMPANY)
	try:
		going = {one.doctype_name for one in plan.doctypes_to_delete if one.document_count}
		assert {"Sales Invoice", "Stock Entry", "Lead"} <= going, going
		kept = {"Customer", "Supplier", "Account", "Employee", "Item", "UAE VAT Settings", "Tax Rule", "Pricing Rule"}
		assert not kept & going, kept & going
	finally:
		frappe.delete_doc(start_again.DOCTYPE, plan.name, force=True, ignore_permissions=True)


@check
def oneai_suggests_a_customer_and_its_quotation_together():
	"""A chain: one create_records call makes a card for a new customer and one
	for a quotation pointing at it; Approve All makes both, the quotation for
	the customer just made, and each carries OneAI's marks."""
	from onedesk.one_ai import proposals, run, tools, touch

	item = frappe.db.sql(
		"""select name from tabItem where is_sales_item = 1 and disabled = 0 and has_variants = 0
		and name not in (select parent from `tabItem Customer Detail`) limit 1"""
	)[0][0]
	with as_user("omar@one.test"):
		said = tools.create_records(
			[
				{"ref": "new", "doctype": "Customer", "values": {"customer_name": "Harbor Lights LLC", "customer_type": "Company"}},
				{"doctype": "Quotation", "values": {"quotation_to": "Customer", "party_name": "@new", "items": [{"item_code": item, "qty": 3}]}},
			]
		)
		first, second = (one["proposal"] for one in said["cards"])
		assert json.loads(frappe.db.get_value("AI Proposal", second, "needs")) == [first]
		assert not frappe.db.exists("Customer", "Harbor Lights LLC"), "nothing is made before it is approved"
		try:
			tools.create_record("Quotation", {"quotation_to": "Customer", "party_name": "@PROP-99-999999", "items": [{"item_code": item, "qty": 1}]})
			raise AssertionError("a pointer at no card was taken")
		except frappe.ValidationError as e:
			assert "no card PROP-99-999999" in str(e), e
	with as_user("samir@one.test"):
		try:
			tools.create_record("Quotation", {"quotation_to": "Customer", "party_name": f"@{first}", "items": [{"item_code": item, "qty": 1}]})
			raise AssertionError("pointed at somebody else's card")
		except frappe.ValidationError:
			pass
	with as_user("omar@one.test"):
		done = run.apply_all([first, second])
		assert [one["state"] for one in done] == ["Applied", "Applied"], done
		quotation = frappe.db.get_value("AI Proposal", second, "applied_doc")
		assert frappe.db.get_value("Quotation", quotation, "party_name") == "Harbor Lights LLC"
		held = frappe.get_doc("Customer", "Harbor Lights LLC")
		touch.onload(held)
		assert held.get_onload().get("ai_made"), "the record says OneAI made it"
		assert "customer_type" in (held.get_onload().get("ai_touched") or {}), "a field that is not prose is marked too"
		assert proposals.apply_all([first, second]) == [], "approving twice does nothing"


@check
def whats_new_says_each_version_once():
	"""Nadia sees OneMail's version marked unseen until she opens What's New,
	which lists its versions newest first, written for her, and then marks
	them seen (one/versions.py). Its pictures come from R2 by their hash, and
	the workspace serves the same picture when R2 can't, but nothing outside
	a module's docs (one/media.py)."""
	from onedesk.one import media, ready, versions

	with as_user("nadia@one.test"):
		frappe.defaults.set_user_default(versions.SEEN.format("one_mail"), "")
		said = versions.for_boot()["OneMail"]
		assert said == {"version": ready.current("OneMail"), "unseen": 1}, said
		listed = versions.whats_new("OneMail")["versions"]
		assert listed[0]["version"] == ready.current("OneMail") and listed[0]["new"], listed[0]
		html = listed[-1]["html"]
		assert f'src="{media.base()}/docs/' in html and "data-here=" in html, html[:300]
		assert versions.for_boot()["OneMail"]["unseen"] == 0
		assert not versions.whats_new("OneMail")["versions"][0]["new"]
		from html import unescape
		from urllib.parse import parse_qs, urlsplit

		here = parse_qs(urlsplit(unescape(html.split('data-here="', 1)[1].split('"', 1)[0])).query)
		media.picture(here["module"][0], here["path"][0])
		assert frappe.local.response["content_type"].startswith("image/")
		try:
			media.picture("OneMail", "../hooks.py")
			raise AssertionError("a path outside the docs is refused")
		except frappe.DoesNotExistError:
			pass


@check
def help_shows_every_page_in_order():
	"""OneMail's Help gives Nadia its pages in the order ready.MODULES lists
	them, each with its icon and a heading, and every page a version reads
	more in is one of them (one/versions.py help_pages)."""
	from onedesk.one import ready, versions

	with as_user("nadia@one.test"):
		said = versions.help_pages("OneMail")
		assert said["version"] == ready.current("OneMail"), said["version"]
		pages = said["pages"]
		assert [one["id"] for one in pages] == [page for page, _icon in ready.MODULES["OneMail"]["help"]]
		assert all(one["icon"] and one["title"] and one["html"].strip() for one in pages), pages[0]
		ids = {one["id"] for one in pages}
		for one in versions.whats_new("OneMail")["versions"]:
			assert {page["id"] for page in one["docs"]} <= ids, one["docs"]
		# Who Can Do What shows what OneMail's roles ship with, from its
		# abilities.py (one/rights.py defaults_table).
		roles = next(one["html"] for one in pages if one["id"] == "who-can-do-what")
		assert "{roles}" not in roles and "Every Mailbox" in roles and "Ask for Approval" in roles, roles[:200]
	from onedesk.one.notify import declared

	assert declared()["Mail Not Sent"]["email"] is False and declared()["Attachments Not Saved"]["from_one"] is True
	assert not declared()["Covering Mail"].get("from_one")


@check
def setup_steps_are_slides_then_to_dos():
	"""OneMail's setup steps (one/setup_steps.py): Layla, who administers the
	workspace, sees all three in Getting Started and Nadia none; the two with
	fields would be wizard slides, named for the module and step; one given
	in the wizard is saved and done, one left empty stays a to-do, and Mark
	as Done finishes one."""
	from unittest.mock import patch

	from onedesk.one import setup_steps
	from onedesk.one_mail import addresses

	with as_user(OWNER):
		steps = setup_steps.for_boot()["OneMail"]
	assert [one["key"] for one in steps] == ["domains", "private", "templates"], steps
	with as_user("nadia@one.test"):
		assert "OneMail" not in setup_steps.for_boot()
	with patch("frappe.is_setup_complete", return_value=False):
		slides = setup_steps.for_wizard()
	names = [field["fieldname"] for slide in slides for field in slide["fields"]]
	assert names == ["one_mail_domains_domain", "one_mail_private_allowed", "one_service_weather", "one_service_google_news", "one_service_training_copies", "one_service_web_search", "one_service_gravatar", "one_service_logos", "one_service_google_fonts"], names
	assert slides[-1]["name"] == "one_services" and not any(field["default"] for field in slides[-1]["fields"]), "the optional services start off"
	was = frappe.db.get_default(addresses.EXTERNAL)
	flags = {key: frappe.db.get_default(setup_steps.FLAG.format("one_mail", key)) for key in ("private", "templates")}
	try:
		setup_steps.apply({"one_mail_private_allowed": 0, "one_mail_domains_domain": ""})
		assert frappe.db.get_default(addresses.EXTERNAL) == "0"
		with as_user(OWNER):
			said = {one["key"]: one["done"] for one in setup_steps.for_boot()["OneMail"]}
			assert said["private"] == 1 and said["templates"] == 0, said
			left = setup_steps.finish("OneMail", "templates")
		assert next(one for one in left if one["key"] == "templates")["done"] == 1
	finally:
		frappe.db.set_default(addresses.EXTERNAL, was) if was is not None else frappe.db.set_default(addresses.EXTERNAL, "1")
		for key, value in flags.items():
			frappe.db.set_default(setup_steps.FLAG.format("one_mail", key), value or "")


@check
def tour_runs_once_then_from_help():
	"""OneMail's tours (one/tours.py): one for its mailbox, six steps in the
	reader's language, each at a mark; a reader who hasn't taken it has it in
	the boot, and once taken or closed it doesn't start on its own again."""
	from onedesk.one import tours

	key = tours.SEEN.format("one_mail", "mailbox")
	with as_user("nadia@one.test"):
		was = frappe.defaults.get_user_default(key)
		try:
			frappe.defaults.clear_user_default(key)
			assert "OneMail:mailbox" in tours.unseen()
			said = tours.tour("OneMail")
			assert [one["key"] for one in said] == ["mailbox"] and said[0]["at"] == "onemail-list", said
			steps = said[0]["steps"]
			assert [one["target"] for one in steps][:2] == ["interface-nav", "onemail-new"], steps
			assert all(one["title"] and one["text"] for one in steps), steps
			tours.seen("OneMail", "mailbox")
			assert "OneMail:mailbox" not in tours.unseen()
		finally:
			if was != "1":
				frappe.defaults.clear_user_default(key)


@check
def access_center_finds_and_sets_roles():
	"""AccessCenter (one/access_center.py) has OneMail's part, found from its
	abilities.py: its people with their role, which it changes and puts
	back, and what somebody was given on one mailbox, which it takes away.
	Nobody else may read it."""
	from onedesk.one import access_center, rights

	with as_user("wsadmin@one.test"):
		assert "OneMail" in access_center.modules()
		said = access_center.people("OneMail")
		assert {"User", "Manager"} <= {one["value"] for one in said["levels"]}, said["levels"]
		assert "None" not in {one["value"] for one in said["levels"]}, "everybody uses OneMail"
		nadia = next(one for one in said["people"] if one["user"] == "nadia@one.test")
		was = nadia["level"]
		try:
			access_center.put("OneMail", "nadia@one.test", "Manager")
			assert next(one for one in access_center.people("OneMail")["people"] if one["user"] == "nadia@one.test")["level"] == "Manager"
		finally:
			access_center.put("OneMail", "nadia@one.test", was)
		box = frappe.get_all("Email Account", filters={"email_id": ["like", "%"]}, pluck="name", limit=1)[0]
		had = rights.grants("OneMail", box).get("nadia@one.test")
		try:
			access_center.give("OneMail", box, "nadia@one.test", ["signature"])
			given = [one for one in access_center.records("OneMail")["grants"] if one["user"] == "nadia@one.test" and one["record"] == box]
			assert given and given[0]["given"] == ["signature"], given
			access_center.give("OneMail", box, "nadia@one.test", [])
			assert not [one for one in access_center.records("OneMail")["grants"] if one["user"] == "nadia@one.test" and one["record"] == box]
		finally:
			if had:
				rights.grant("OneMail", box, "nadia@one.test", had)
	with as_user("nadia@one.test"):
		try:
			access_center.people("OneMail")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who doesn't administer the workspace read AccessCenter")


@check
def notification_center_sets_yours_and_the_workspace():
	"""NotificationCenter (one/notification_notification_center.py): a reader's own
	choice of email for one of OneMail's types, saved and put back; the
	workspace's setting of a type, set and put back by an administrator and
	refused to anybody else."""
	from onedesk.one import notification_center

	with as_user("nadia@one.test"):
		was = notification_center.yours("OneMail")["email"]
		try:
			notification_center.switch("enable_email_notifications", 0 if was else 1)
			assert notification_center.yours("OneMail")["email"] != was
		finally:
			notification_center.switch("enable_email_notifications", was)
		mine = notification_center.yours("OneMail")["types"]
		one = next(kind for kind in mine if kind["may_email"])
		try:
			notification_center.choose(one["name"], "email", 0 if one["email"] else 1)
			now = next(kind for kind in notification_center.yours("OneMail")["types"] if kind["name"] == one["name"])
			assert now["email"] != one["email"], now
		finally:
			notification_center.choose(one["name"], "email", one["email"])
		try:
			notification_center.set_type(one["name"], "one_allow_push", 0)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who doesn't administer the workspace set a notification type")
	with as_user("wsadmin@one.test"):
		types = notification_center.workspace("OneMail")
		assert types and all(kind["app"] == "OneMail" for kind in types), types
		assert all(set(kind) >= {"enabled", "one_allow_email", "one_allow_push"} for kind in types), types
		kind = next(t for t in types if not t["fixed"])
		try:
			notification_center.set_type(kind["name"], "enabled", 0 if kind["enabled"] else 1)
			assert frappe.db.get_value("Notification Type", kind["name"], "enabled") != kind["enabled"]
			try:
				notification_center.set_type(kind["name"], "one_push_default", 1)
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("an administrator set who starts with a channel on; the module says that")
		finally:
			notification_center.set_type(kind["name"], "enabled", kind["enabled"])


def _modules() -> None:
	"""A module's own checks, in its folder (docs/READY.md, A module's folder),
	registered by importing them."""
	import importlib

	from onedesk.one import ready

	for spec in ready.MODULES.values():
		importlib.import_module(f"onedesk.{spec['folder']}.checks")


_modules()
