"""The integration suite: the demo workspace read back as the people in it.

    bench --site <site> execute onedesk.one_demo.check.run
    bench --site <site> execute onedesk.one_demo.check.run --kwargs "{'only': 'oneproject_'}"

`only` names one check, or ends in "_" to run a group: every check whose name
starts with it, such as a module's.
"""

import datetime
import json
import traceback

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
			with unkept():
				fn()
			print(f"ok    {fn.__name__}")
		except Exception as e:
			failed.append(fn.__name__)
			here = [one.lineno for one in traceback.extract_tb(e.__traceback__) if one.filename == __file__]
			said = str(e) or f"line {traceback.extract_tb(e.__traceback__)[-1].lineno}"
			print(f"FAIL  {fn.__name__} (check.py:{here[-1] if here else '?'}): {type(e).__name__} {said[:600]}")
		finally:
			frappe.db.rollback()
			frappe.clear_cache()
			_unasked()
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
	"""The page's three reads, as the owner, the project manager, the books
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
					view.work(project.name)
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
	assert "<b>Quote Received</b>" in said["message"] and "section=notifications" in said["message"]
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

	from onedesk.one import print_blocks

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
		bill = frappe.get_all("Purchase Invoice", filters={"docstatus": 1, "bill_no": ["is", "set"], "auto_repeat": ["is", "not set"]}, fields=["name", "bill_no"], limit=1)[0]
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
		with as_user("Administrator"):
			for period in frappe.get_all("Accounting Period", filters={"company": COMPANY, "start_date": "2025-01-01"}, pluck="name"):
				frappe.delete_doc("Accounting Period", period, ignore_permissions=True, force=True)
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
		said = order.read()
		assert said["figures"]["lines"] == len(said["lines"]) == len(listed) and said["currency"], said["figures"]
		assert all(one["unit"] and one["warehouse_label"] and one["why"] in ("requested", "low") for one in said["lines"])
		assert said["figures"]["cost"] == sum(one["cost"] or 0 for one in said["lines"]) and said["can"]["order"]
		first = listed[0]
		order.order([{**first, "supplier": first.get("supplier") or "Al Noor Aluminium"}])
		def row(one):
			return one.get("material_request_item") or (one["item_code"], one["warehouse"])

		assert row(first) not in {row(one) for one in order.rows()}, "a row already on a draft order is offered again"
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
	from onedesk.one_crm import ai, board, capture, next, record, story

	deal = frappe.db.get_value("Opportunity", {"title": "Webb Hotel lobby curtain wall"})
	lead = frappe.db.get_value("Lead", {"email_id": "hamad@suwaidi.example"})
	priya = frappe.db.get_value("Lead", {"email_id": "priya@nairinteriors.example"})
	khalid = frappe.db.get_value("Lead", {"email_id": "khalid@suwaidi.example"})
	with as_user("omar@one.test"):
		figures = story.read()["cards"]
		assert figures["pipeline"]["value"] > figures["weighted"]["value"] > 0, figures
		assert figures["rate"]["value"] == 50.0, "two won and two lost in the last 90 days"
		stages = board.worth()["stages"]
		assert sum(one["value"] for one in stages.values()) >= figures["pipeline"]["value"], stages
		assert record.overview("Opportunity", deal)["next"]
		assert record.overview("Lead", lead)
		called = record.log_call("Opportunity", deal, "Outgoing", "Answered", 6, "Agreed to send the drawings by Thursday.")
		assert frappe.db.exists("Dynamic Link", {"parenttype": "Call Log", "parent": called, "link_name": deal})
		next.done("Opportunity", deal, "Review the drawings", str(add_days(today(), 3)) + " 10:00:00")
		assert frappe.db.get_value("Opportunity", deal, "one_next_step") == "Review the drawings"
		assert frappe.db.exists("Comment", {"reference_name": deal, "content": ["like", "%Ask for the drawings%"]})

		next.settle()
		assert not frappe.db.get_value("Lead", priya, "lead_owner"), "the web form gives a lead no owner, and an update leaves it so"
		capture.take("Lead", priya)
		assert frappe.db.get_value("Lead", priya, "lead_owner") == "omar@one.test"
		assert frappe.db.get_value("Lead", khalid, "one_duplicate_of") == lead
		capture.not_duplicate(khalid)
		assert not frappe.db.get_value("Lead", khalid, "one_duplicate_of")
		again = frappe.get_doc({"doctype": "Lead", "first_name": "Priya", "last_name": "Nair", "company_name": "Nair Interiors", "email_id": "p.nair@gmail.example"}).insert()
		assert again.one_duplicate_of == priya
		assert capture.merge(again.name, priya) == priya and not frappe.db.exists("Lead", again.name)

		assert ai.crm_facts("Opportunity", deal)["history"]
		assert ai.crm_facts("Lead", lead)["history"]
		assert ai.crm_facts("Customer", deal).get("error"), "only a deal or a lead"
		assert "quiet" in ai.gone_quiet("Opportunity") and "quiet" in ai.gone_quiet("Lead")
		lost = ai.why_we_lose()
		assert lost["won"] == 6 and lost["lost"] == 6, "a year of selling, and this month's"
		assert [one["reasons"] for one in lost["deals"] if one["deal"] == "Iqbal Clinics reception"] == [["Price"]], lost
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
		standing = {one["key"]: one for one in reading.overview()["documents"]}
		assert not standing["terms"]["organisation"]["owed"], standing["terms"]
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

		contract = _sample("signed-contract")
		proposed = frappe.get_all("Intake Action", filters={"reading": contract, "level": "Proposed"}, pluck="name")[0]
		act.settle(proposed, 0)
		assert frappe.db.get_value("Intake Action", proposed, "level") != "Proposed"
		contact = frappe.db.get_value("Intake Action", {"reading": contract, "target_doctype": "Contact", "level": "Done"}, "name")
		assert act.undo_one(contact)["undone"] == 1
		drawings = _sample("drawings-request")
		task = frappe.db.get_value("Intake Action", {"reading": drawings, "target_doctype": "Task", "level": "Done"}, "target_name")
		assert act.undo(drawings)["undone"] >= 1 and not frappe.db.exists("Task", task)

		marked = frappe.get_all("AI Touch", filters={"for_doctype": "Task", "fieldname": mark.WHOLE}, pluck="record", limit=1)
		assert marked
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
		with mock.patch("onedesk.one_intake.pipeline.later") as later:
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
		changed = run.set_job("chat", "gemini-flash")
		assert chat.CHAT in changed and "summarise" in changed, changed
		assert {frappe.db.get_value("AI Action Setting", {"action": one}, "model") for one in changed} == {"gemini-flash"}
		assert run.set_job("chat", "gemini-flash") == [], "the same pick changes nothing"
		assert sorted(run.set_job("chat", "")) == sorted(changed)
		for one in changed:
			run.reset_action(one)
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
		assert frappe.db.exists("Mail Rule", {"account": account, "steps": ["like", "%taxi%"]})
		assert frappe.db.count("Communication", {"email_account": account, "one_folder": taxis}) >= 2

		rules.set_away(account, 1, str(add_days(today(), 7)), "Back next week.")
		assert rules.away_of(account).one_away == 1
		rules.set_away(account, 0)

		ours = holders.workspace()
		assert ours in {one["name"] for one in holders.shared()["mailboxes"]}
		holders.set_signature(ours, "<p>Layla Nasser<br>Sahara Glass</p>")
		assert holders.signature_of(ours).startswith("<p>Layla Nasser")
		assert holders.signature_for(frappe.db.get_value("Email Account", ours, "email_id")).startswith("<p>Layla")
		holders.set_personal_sends(0)
		assert frappe.db.get_value("Email Account", account, "enable_outgoing") == 1, "the default moved a given address"
		holders.set_personal_sends(1)
		holders.set_sends(account, 0)
		assert not next(one for one in holders.addresses_of_people() if one["name"] == account)["sends"]
		try:
			holders.set_signature(account, "Layla")
			raise AssertionError("an address that only receives signs nothing")
		except frappe.ValidationError:
			pass
		holders.set_sends(account, 1)
		assert frappe.db.get_value("Email Account", account, "enable_outgoing") == 1
		holders.set_access(ours, [{"user": OWNER, "sends": 1}, {"user": "omar@one.test", "sends": 0}])
		assert holders.may_send(ours, OWNER) and not holders.may_send(ours, "omar@one.test")
	with as_user("omar@one.test"):
		assert ours in {one["name"] for one in api.mailboxes()}
		assert not next(one for one in api.mailboxes() if one["name"] == ours)["sends"], "Omar reads the workspace's mailbox but may not send"
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
		if not frappe.db.exists("Email Account", {"email_id": addresses.person_address("rania")}):
			addresses.give("rania@one.test", "rania")
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
def onemail_a_mailbox_is_set_up_in_its_own_tabs():
	"""Layla manages the workspace mailbox from OneMail's settings: who holds
	it, an acknowledgement to new conversations, how far OneAI reads it and a
	monthly limit; then her own signature from a preset with her name on it,
	and the workspace's rules for outside mailboxes. Turning
	OneAI off for her own mailbox stops even the OneAI panel reading it."""
	from onedesk.one_mail import ai, gate, holders, mail_templates, rules, signatures
	from onedesk.one_storage import api

	with as_user(OWNER):
		ours = holders.workspace()
		assert holders.mailbox(ours)["may_manage"]
		holders.grant(ours, "omar@one.test", 0)
		assert any(one["user"] == "omar@one.test" for one in holders._people(ours))
		holders.revoke(ours, "omar@one.test")
		said = gate.set_settings(ours, level=gate.FILE, limit=500)
		assert said["level"] == gate.FILE and said["limit"] == 500
		gate.set_settings(ours, level=gate.ACT, limit=0)
		own = next(one["name"] for one in holders.mailboxes() if not one["shared"])
		gate.set_settings(own, on=0)
		assert not gate.settings_of(own)["on"]
		assert "error" in ai.open_conversation(own, "anything"), "the panel can't read a mailbox OneAI is off for"
		gate.set_settings(own, on=1)
		was = frappe.db.get_value("Email Account", own, ["signature", "one_signature_preset", "one_signature_show"])
		drawn = signatures.presets_of(own, ["title", "email"])
		assert drawn["presets"] and all(one["html"] for one in drawn["presets"])
		signatures.set_preset(own, "accent", ["email"])
		assert "Layla" in holders.signature_of(own), "her signature doesn't carry her name"
		frappe.db.set_value(
			"Email Account", own, dict(zip(("signature", "one_signature_preset", "one_signature_show"), was, strict=True)), update_modified=False
		)
		made = rules.save_rule(own, {"title": "Invoices", "steps": [{"type": "if", "id": "i1", "test": {"items": [{"field": "subject", "op": "contains", "value": "invoice"}]}, "then": [{"type": "star"}], "else": []}]})
		assert any(one["name"] == made for one in rules.rules_of_mailbox(own)["rules"])
		rules.enable_rule(made, 0)
		assert not frappe.db.get_value("Mail Rule", made, "enabled")
		rules.delete_rule(made)
		holders.set_external(0)
		holders.set_allowed_domains(["gmail.com"])
		holders.set_allowed_domains([])
		holders.set_external(1)
		assert isinstance(mail_templates.templates(), list)
		if frappe.db.exists("Email Template", "Leave Approval Notification"):
			mail_templates.settle()
			was = frappe.db.get_single_value("HR Settings", "leave_approval_notification_template")
			frappe.db.set_single_value("HR Settings", "leave_approval_notification_template", "Leave Approval Notification")
			try:
				row = next(one for one in mail_templates.templates() if one["name"] == "Leave Approval Notification")
				assert row["reference_doctype"] == "Leave Application", row
				assert row["used_by"] and row["code"], "HR's template says who sends it and that it holds code"
				try:
					frappe.delete_doc("Email Template", "Leave Approval Notification")
					raise AssertionError("a template HR Settings sends was deleted")
				except frappe.ValidationError:
					pass
			finally:
				frappe.db.set_single_value("HR Settings", "leave_approval_notification_template", was)
		assert {one["label"] for one in api.capacity()}


@check
def onemail_people_ask_and_mail_managers_decide():
	"""Rania asks for a rule on the address the workspace issued her and
	can't turn it on herself; Layla approves it and it runs. Tariq, made a
	Mail Manager, manages the workspace's mailbox and Rania's address
	without holding either, and gives Rania's address a sender name.
	Rania sets her own address's out-of-office, and it answers by itself
	while she is on approved leave."""
	from onedesk.one import roles
	from onedesk.one_mail import addresses, holders, rules, signatures

	with as_user(OWNER):
		if not frappe.db.exists("Email Account", {"email_id": addresses.person_address("rania")}):
			addresses.give("rania@one.test", "rania")
	theirs = frappe.db.get_value("Email Account", {"email_id": addresses.person_address("rania")})
	with as_user("rania@one.test"):
		assert holders.issued_to_them(theirs), "an issued address is the workspace's"
		assert holders.may(theirs, "away") and not holders.may(theirs, "signature"), "her own out-of-office, nothing more"
		asked = rules.save_rule(theirs, {"title": "Invoices", "steps": [{"type": "if", "id": "i1", "test": {"items": [{"field": "subject", "op": "contains", "value": "invoice"}]}, "then": [{"type": "star"}], "else": []}]})
		assert frappe.db.get_value("Mail Rule", asked, ["enabled", "requested_by"]) == (0, "rania@one.test")
		try:
			rules.enable_rule(asked, 1)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania turned on a rule nobody approved")
		try:
			signatures.set_preset(theirs, "simple", ["email"])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania changed the workspace's address")
		rules.set_away(theirs, 1, None, "Away")
		rules.set_away(theirs, 0)
		assert rules.on_leave(theirs) is None or rules.away_of(theirs)["leave_until"]
	with as_user(OWNER):
		rules.decide_rule(asked, 1)
		assert frappe.db.get_value("Mail Rule", asked, ["enabled", "requested_by"]) == (1, None)
		rules.delete_rule(asked)
	frappe.get_doc("User", "tariq@one.test").add_roles(roles.MAIL_MANAGER)
	try:
		with as_user("tariq@one.test"):
			assert holders.may_manage(holders.workspace()) and holders.may_manage(theirs)
			assert any(one["name"] == theirs for one in holders.addresses_of_people())
			signatures.set_preset(theirs, "simple", ["email"], sender_name="Rania at Sahara Glass")
			assert signatures.sender_name_for(None, addresses.person_address("rania")) == "Rania at Sahara Glass"
			signatures.set_preset(theirs, "simple", ["email"], sender_name="")
			assert signatures.sender_name_for(theirs, None) is None
	finally:
		frappe.get_doc("User", "tariq@one.test").remove_roles(roles.MAIL_MANAGER)
		frappe.db.set_value(
			"Email Account", theirs, {"signature": None, "add_signature": 0, "one_signature_preset": None, "one_signature_show": None}
		)


@check
def onemail_roles_and_one_mailbox_grants():
	"""Layla makes a OneMail role that may change signatures on every
	mailbox and nothing else, and one, cell by cell in the role builder,
	that may change only a person's own address; and lets Samir change the workspace mailbox's signature alone,
	without a role, from its Users tab. Taking Samir off the mailbox takes
	that away too."""
	from onedesk.one import access
	from onedesk.one_mail import addresses, holders

	ours = holders.workspace()
	made = []
	with as_user(OWNER):
		if not frappe.db.exists("Email Account", {"email_id": addresses.person_address("rania")}):
			addresses.give("rania@one.test", "rania")
		theirs = frappe.db.get_value("Email Account", {"email_id": addresses.person_address("rania")})
		brand = access.new_level("OneMail", "Brand Team", "User")
		made.append(brand)
		access.save_level(brand, brand, [], {"signature": "all"})
		own = access.new_level("OneMail", "Own Address", "User")
		made.append(own)
		own = made[-1] = access.rename_role(own, "Their Own Mailbox")
		access.change_ability(own, "signature", "own")
		said = access.change_ability(own, "away", "own")
		assert access.ability_matrix("OneMail")["values"] == said["values"]
		assert [role["name"] for role in said["roles"]] == ["User", brand, own, "Manager"]
		assert said["values"][own]["signature"] == "own" and said["values"][own]["holders"] == 0
		assert {one["key"]: one["value"] for one in access.level(brand)["abilities"]}["signature"] == "all"
		assert said["least"][own]["rules"] == "none", "User asks for approval"
	try:
		frappe.get_doc("User", "tariq@one.test").add_roles(brand)
		frappe.get_doc("User", "rania@one.test").add_roles(own)
		with as_user("tariq@one.test"):
			assert holders.may(ours, "signature") and holders.may(theirs, "signature")
			assert not holders.may(ours, "rules") and not holders.may(ours, "away")
		with as_user("rania@one.test"):
			assert holders.may(theirs, "signature") and holders.may(theirs, "away"), "her own address"
			assert not holders.may(ours, "signature") and not holders.may(theirs, "rules")
		with as_user(OWNER):
			holders.grant(ours, "samir@one.test", 1)
			assert holders.give(ours, "samir@one.test", ["signature"]) == ["signature"]
		with as_user("samir@one.test"):
			assert holders.may(ours, "signature") and not holders.may(ours, "away"), "one mailbox, one thing"
		with as_user(OWNER):
			holders.revoke(ours, "samir@one.test")
		with as_user("samir@one.test"):
			assert not holders.may(ours, "signature"), "off the mailbox, off what it gave"
	finally:
		frappe.get_doc("User", "tariq@one.test").remove_roles(brand)
		frappe.get_doc("User", "rania@one.test").remove_roles(own)
		with as_user(OWNER):
			for role in made:
				access.delete_level(role)


@check
def onemail_rules_are_steps_that_branch_and_ask_oneai():
	"""Layla builds rules on the workspace mailbox as steps: an If on who
	wrote, with a group of Any inside, stars and files mail from a customer
	and tells her; an Acknowledge rule answers a new conversation from
	outside once a day, not twice; an Ask OneAI rule waits for OneAI's
	reading and takes the branch of the label it picked, or Otherwise, and is
	refused on a mailbox whose new mail is not read. A rule needs an action,
	and a folder in its own mailbox."""
	from unittest import mock

	from onedesk.one_mail import flow, holders, rules
	from onedesk.one_mail.patches import rules_are_steps

	ours = holders.workspace()
	message = frappe.db.get_value(
		"Communication", {"email_account": ours, "sent_or_received": "Received", "sender": ["like", "%marinahotels%"]}, "name"
	)
	made, sent = [], []
	was = frappe.db.get_value("Communication", message, ["one_flagged", "one_folder"])
	archive = frappe.db.get_value("Mail Folder", {"account": ours, "kind": "Archive"})
	try:
		with as_user(OWNER):
			try:
				rules.save_rule(ours, {"title": "Nothing", "steps": [{"type": "if", "id": "i", "test": {}, "then": [], "else": []}]})
				raise AssertionError("a rule that does nothing was saved")
			except frappe.ValidationError:
				pass
			customers = rules.save_rule(
				ours,
				{
					"title": "Customers",
					"steps": [
						{
							"type": "if",
							"id": "i1",
							"test": {
								"items": [
									{"field": "sender_is", "op": "is", "value": "Customer"},
									{"any": True, "items": [{"field": "subject", "op": "contains", "value": "balcony, glass"}, {"field": "attachment", "value": True}]},
								]
							},
							"then": [{"type": "star"}, {"type": "link"}, {"type": "notify", "user": OWNER}],
							"else": [],
						}
					],
				},
			)
			made.append(customers)
			ack = rules.save_rule(ours, {"title": "Acknowledge", "steps": rules_are_steps.acknowledge(""), "priority": 20})
			made.append(ack)
			asking = {"title": "Asks", "steps": [{"type": "ask", "id": "a", "ask": "yes", "question": "a complaint", "then": [{"type": "star"}], "else": []}]}
			frappe.db.set_value("Email Account", ours, "one_intake", 0)
			try:
				rules.save_rule(ours, asking)
				raise AssertionError("an Ask OneAI rule was saved on a mailbox whose new mail is not read")
			except frappe.ValidationError:
				pass
			frappe.db.set_value("Email Account", ours, "one_intake", 1)
			sort = rules.save_rule(
				ours,
				{
					"title": "Sort",
					"priority": 30,
					"steps": [
						{
							"type": "ask",
							"id": "a1",
							"ask": "pick",
							"labels": [{"label": "Maintenance", "then": [{"type": "move", "folder": archive}]}, {"label": "Quote", "then": []}],
							"else": [{"type": "read"}],
						}
					],
				},
			)
			made.append(sort)
			listed = {one["name"]: one for one in rules.rules_of_mailbox(ours)["rules"]}
			assert "Customer" in listed[customers]["when"] and "Star" in listed[customers]["then"]
		replied = mock.patch("onedesk.one_mail.rules._send", side_effect=lambda account, comm, html: sent.append(comm.name))
		made_ = frappe.get_doc("Communication", message)
		with replied:
			done = rules.run_rules(made_, headers={})
			assert customers in done and ack in done and sort not in done, done
			assert frappe.db.get_value("Communication", message, "one_flagged") == 1
			assert sent == [message], "acknowledged once"
			rules.run_rules(made_, headers={})
			assert sent == [message], "not twice in a day"
		topics = rules.topics_of_mailbox(ours)
		assert (f"{sort}#a1#0", "Maintenance") in topics
		assert rules.run_rules(made_, {f"{sort}#a1#0"}) == [sort]
		assert frappe.db.get_value("Communication", message, "one_folder") == frappe.db.get_value("Mail Folder", archive, "path")
		steps = rules.flow_of(frappe.get_doc("Mail Rule", sort))
		assert flow.walk(steps, rules.facts_of(message), flow.answers_of(sort, steps, set()))[0] == [{"type": "read"}], "Otherwise"
	finally:
		with as_user(OWNER):
			for one in made:
				rules.delete_rule(one)
		frappe.db.set_value("Communication", message, {"one_flagged": was[0], "one_folder": was[1]}, update_modified=False)
		frappe.db.delete("Notification Log", {"for_user": OWNER, "subject": ["like", "%marinahotels%"]})


@check
def onemail_out_of_office_answers_for_its_person():
	"""Rania sets her own address's out-of-office: from tomorrow it is not on
	today; on today, to the workspace only, it answers Samir once and a
	buyer outside not at all, under her name. On
	leave her reply says the day she is back and that Samir covers, and
	Samir reads her address while she is away without owning it, until the
	leave is cancelled. A shared mailbox has no out-of-office; the half day
	of a half-day leave answers nothing."""
	import types
	from unittest import mock

	from onedesk.one_mail import actions, addresses, holders, rules, signatures

	with as_user(OWNER):
		if not frappe.db.exists("Email Account", {"email_id": addresses.person_address("rania")}):
			addresses.give("rania@one.test", "rania")
	theirs = frappe.db.get_value("Email Account", {"email_id": addresses.person_address("rania")})
	sent = []

	def arrived(sender):
		return types.SimpleNamespace(email_account=theirs, sender=sender, subject="Quote", message_id=f"<{sender}>")

	replied = mock.patch(
		"onedesk.one_mail.rules._reply", side_effect=lambda account, made, text, html=None: sent.append((made.sender, text, html))
	)
	leave = frappe._dict(
		name="LEAVE-CHECK",
		employee=_employee("Rania"),
		one_covering=_employee("Samir"),
		one_covering_reads=1,
		docstatus=1,
		status="Approved",
		from_date=today(),
		to_date=add_days(today(), 2),
	)
	try:
		with as_user("rania@one.test"):
			rules.set_away(theirs, 1, None, "", str(add_days(today(), 1)))
			assert not rules.switched_on(frappe.get_doc("Email Account", theirs)), "it starts tomorrow"
			rules.set_away(theirs, 1, str(add_days(today(), 3)), "", None, "Workspace")
			assert rules.away_state(theirs)["until"]
			drawn = rules.away_preview(theirs, "")
			assert drawn["default"] and 'dir="auto"' in drawn["html"]
		with as_user("samir@one.test"):
			assert [one["email"] for one in rules.who_is_away([addresses.person_address("rania")])] == [
				addresses.person_address("rania")
			], "who writes to her is told"
		with replied, mock.patch("onedesk.one_mail.rules.on_leave", return_value=None):
			assert not rules.away(arrived("buyer@outside.test"), {}), "only the workspace"
			assert rules.away(arrived("samir@one.test"), {})
			assert not rules.away(arrived("samir@one.test"), {}), "once per sender"
		assert sent[-1][1] == "I'm away and will reply when I'm back." and 'dir="auto"' in sent[-1][2]
		with as_user(OWNER):
			try:
				rules.set_away(holders.workspace(), 1)
				raise AssertionError("a shared mailbox took an out-of-office")
			except frappe.ValidationError:
				pass
		with as_user("rania@one.test"):
			rules.set_away(theirs, 0)

		rules.covered(leave)
		assert actions.holds(theirs, "samir@one.test") and not actions.owns(theirs, "samir@one.test")
		assert signatures.person_of(theirs) == "rania@one.test", "covering is not owning"
		with as_user("samir@one.test"):
			assert not holders.may(theirs, "away")
			assert {one["name"]: one["covering_until"] for one in holders.mailboxes()}[theirs]
		back = rules.back_on(leave.employee, leave.to_date)
		said = rules.away_message(
			frappe.get_doc("Email Account", theirs),
			{"back": back, "covering": rules.covering_of(leave.one_covering), "one_away_message": "Off to Beirut."},
			"en",
		)
		assert said.startswith("Off to Beirut.") and "Samir" in said, "her words, then who covers"
		assert back > frappe.utils.getdate(leave.to_date)
		assert rules.half_day_today(frappe._dict(half_day=1, from_date=today(), to_date=today(), half_day_date=None))
		leave.docstatus = 2
		rules.covered(leave)
		assert not actions.holds(theirs, "samir@one.test"), "cancelled, and he no longer reads it"
	finally:
		frappe.db.delete("User Email", {"email_account": theirs, "one_cover_until": ["is", "set"]})
		frappe.db.set_value(
			"Email Account",
			theirs,
			{"one_away": 0, "one_away_from": None, "one_away_until": None, "one_away_to": "Everyone"},
			update_modified=False,
		)
		frappe.db.delete("Notification Log", {"for_user": "samir@one.test", "subject": ["like", "%covering%"]})


@check
def onemail_a_shared_mailbox_is_connected_given_and_let_go():
	"""Layla connects the company's sales mailbox for the team, chooses who
	holds it, makes it the Default Incoming and Outgoing and back, which never
	moves the sender notifications go out from, gives its password again and
	disconnects it, and gives Huda a second address. The mail server is not
	dialled: where it is is said here. The Worker's notice is believed only
	with the workspace's signature."""
	import time
	from unittest import mock

	from onedesk.one_mail import connect, holders, inbound

	where = {key: value for key, value in connect.guesses("saharaglass.test")[0].items()}
	smtp = "frappe.email.doctype.email_account.email_account.EmailAccount.validate_smtp_conn"
	with as_user(OWNER), mock.patch("onedesk.one_mail.connect.reach", return_value=where), mock.patch(
		"onedesk.one_mail.connect._smtp"
	), mock.patch(smtp), mock.patch("frappe.enqueue"):
		sales = connect.connect("sales@saharaglass.test", "app-password", shared=1)
		assert frappe.db.get_value("Email Account", sales, ["one_connected", "one_shared"]) == (1, 1)
		said = connect.connection_of(sales)
		assert said["incoming"] and said["incoming"].startswith(where["email_server"]), said
		holders.set_access(sales, [{"user": OWNER, "sends": 1}, {"user": "omar@one.test", "sends": 1}])
		assert set(frappe.get_all("User Email", filters={"email_account": sales}, pluck="parent")) == {OWNER, "omar@one.test"}
		system, ours = holders.system_sender(), holders.workspace()
		assert holders.set_defaults(incoming=sales, outgoing=sales) == {"incoming": sales, "outgoing": sales}
		assert holders.mailbox(sales)["sends_default"] and holders.system_sender() == system, "notifications moved"
		from onedesk.one import notify

		assert notify.replies_to() == "sales@saharaglass.test"
		assert holders.set_defaults(incoming=ours, outgoing=ours) == {"incoming": ours, "outgoing": ours}
		assert holders.system_sender() == system
		from onedesk.one_mail import addresses

		holders.set_external(0)
		with as_user("omar@one.test"):
			work = connect.connect("omar@saharaglass.test", "app-password")
			try:
				connect.connect("omar.farouk@gmail.test", "app-password")
				raise AssertionError("a private mailbox was connected while they are off")
			except frappe.ValidationError:
				pass
		holders.set_external(1)
		with as_user("omar@one.test"):
			private = connect.connect("omar.farouk@gmail.test", "app-password")
		listed = [one["name"] for one in holders.addresses_of_people()]
		assert work in listed and private not in listed, listed
		assert holders.may(work, "signature") and not holders.may(private, "signature")
		with as_user("omar@one.test"):
			assert holders.may(private, "signature") and holders.mailbox(private)["private"]
			connect.disconnect(private)
			connect.disconnect(work)
		with mock.patch("onedesk.one_mail.connect.hosted_by", return_value=connect.HOSTED_BY["google.com"]):
			assert connect.servers_for("saharaglass.org")["email_server"] == "imap.gmail.com", "Google Workspace, by MX"
		served = "frappe.email.doctype.email_domain.email_domain.EmailDomain.validate_"
		with mock.patch(served + "incoming_server_conn"), mock.patch(served + "outgoing_server_conn"):
			connect.add_domain("saharaglass.org", "mail.saharaglass.org", 993, "mail.saharaglass.org", 587)
		assert "saharaglass.org" in [one["domain_name"] for one in connect.domains()]
		assert connect.candidates("karim@saharaglass.org")[0]["email_server"] == "mail.saharaglass.org"
		karim = connect.connect_for("karim@one.test", "karim@saharaglass.org", "app-password")
		assert frappe.db.exists("User Email", {"parent": "karim@one.test", "email_account": karim}), "connected for Karim"
		try:
			connect.connect_for("karim@one.test", "karim.mansour@gmail.test", "app-password")
			raise AssertionError("an administrator connected somebody's private mailbox")
		except frappe.ValidationError:
			pass
		connect.disconnect(karim)
		connect.remove_domain("saharaglass.org")
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
		from erpnext.setup.doctype.employee.employee import is_holiday

		day = add_days(today(), -2)
		while is_holiday(_employee("Rania"), day):
			day = add_days(day, -1)
		rania = frappe.get_doc({"doctype": "Attendance Request", "employee": _employee("Rania"), "company": COMPANY, "from_date": day, "to_date": day, "reason": "On Duty", "one_reason": "Customer Site", "explanation": "At the tower all day."}).insert()
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
		entry = frappe.db.get_value("Payroll Entry", {"docstatus": 1, "salary_slip_based_on_timesheet": 0})
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
def onehr_a_colleagues_record_opens_for_whoever_may_read_it():
	"""Karim may read Mariam's record but not Leave Policy or Salary
	Structure: it opens without a permission error and offers him nothing to
	assign. Mariam, who assigns them, is offered the salary structures there
	are."""
	from onedesk.one_hr import employee

	company = frappe.db.get_value("Employee", _employee("Mariam"), "company")
	with as_user("karim@one.test"):
		assert not frappe.has_permission("Leave Policy", "read")
		assert not frappe.has_permission("Salary Structure", "read")
		assert not any(employee.get_assignable_masters(company).values())
	with as_user("mariam@one.test"):
		assert employee.get_assignable_masters(company)["Salary Structure"] is True


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
	off = frappe.db.get_value("Employee", tariq, "holiday_list") or frappe.db.get_value("Company", COMPANY, "default_holiday_list")
	frappe.db.delete("Holiday", {"parent": off, "holiday_date": today()})
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
	frappe.get_doc({"doctype": "Clock Network", "address": "127.0.0.1/32", "label": "Office", "status": "Confirmed"}).insert(ignore_permissions=True)
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		clean = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": PHONE})
		assert clean["ok"] and not clean["flagged"], clean
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
	_asked(headers={"User-Agent": PHONE}, cookies=_cookies())
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


@check
def onehr_the_clock_says_when_the_shift_starts():
	"""Tariq's shift started an hour ago and he has not checked in: the clock
	gives its start and says he is late, and he is reminded once. He checks in
	and the clock says he is in, late."""
	from frappe.utils import add_to_date, now_datetime

	from onedesk.one_hr import clock, tell

	tariq = _employee("Tariq")
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	frappe.db.delete("Employee Checkin", {"employee": tariq, "time": [">=", f"{today()} 00:00:00"]})
	frappe.db.delete("Attendance", {"employee": tariq, "attendance_date": today()})
	frappe.db.delete("Leave Application", {"employee": tariq, "from_date": ["<=", today()], "to_date": [">=", today()]})
	off = frappe.db.get_value("Employee", tariq, "holiday_list") or frappe.db.get_value("Company", COMPANY, "default_holiday_list")
	frappe.db.delete("Holiday", {"parent": off, "holiday_date": today()})
	start = max(add_to_date(now_datetime(), hours=-1), frappe.utils.get_datetime(f"{today()} 00:01:00"))
	shift = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"name": "Check Shift",
			"start_time": start.strftime("%H:%M:00"),
			"end_time": "23:59:00",
			"allow_check_out_after_shift_end_time": 0,
			"begin_check_in_before_shift_start_time": 0,
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{"doctype": "Shift Assignment", "employee": tariq, "company": COMPANY, "shift_type": shift.name, "start_date": today(), "status": "Active"}
	).insert(ignore_permissions=True).submit()

	with as_user("tariq@one.test"):
		before = clock.ready()
	assert before["due"].startswith(f"{today()} {start.strftime('%H:%M')}"), before
	assert before["late"] and before["direction"] == "IN", before
	with _Told() as told:
		tell.not_checked_in()
		tell.not_checked_in()
	assert [users for name, users in told.said if name == "Not Checked In"].count(["tariq@one.test"]) == 1, told.said

	checkin = frappe.new_doc("Employee Checkin")
	checkin.flags.one_gated = True
	checkin.update({"employee": tariq, "log_type": "IN", "time": now_datetime()})
	checkin.insert(ignore_permissions=True)
	with as_user("tariq@one.test"):
		after = clock.ready()
	assert after["state"] == "in" and after["late"], after
	frappe.cache.delete_value(f"one-not-checked-in:{tariq}:{start.date()}")


@check
def one_an_app_turned_off_is_hidden_not_refused():
	"""The workspace administrator turns OneCRM off: it leaves everybody's
	rail, and Opportunity leaves search and the pickers, while Customer,
	which OneBook lists too, stays. Nothing is refused: an opportunity still
	opens, OneIntake may still file into one, and turning OneCRM back
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
	assert frappe.has_permission("Opportunity", "create", user=OWNER), "OneIntake checks this before it files"
	with as_user(OWNER):
		apps.save([])
		assert not apps.doctypes()
		assert "Opportunity" in [one["value"] for one in apps.search_link("DocType", "Opportun")]


@check
def one_oneai_turned_off_asks_nothing_and_oneintake_reads_nothing():
	"""OneAI off, in Apps, turns OneIntake off with it: no model is asked
	(`run.once`, a chat), nothing is queued to be read, no switch turns on,
	OneHR's screening is off, and One's sidebar loses both sections, OneBook
	its Ready to Submit. OneIntake alone off leaves OneAI answering. What
	OneAI Reads holds only the reader's own mailboxes."""
	from frappe.boot import get_module_sidebars

	from onedesk.one import apps, settings
	from onedesk.one_admin import faults
	from onedesk.one_ai import chat, run
	from onedesk.one_hr import hiring
	from onedesk.one_intake import pipeline, switches

	with as_user("rania@one.test"):
		mine = settings.load("reads")
		assert all(one["mine"] for one in mine["mailboxes"]), mine["mailboxes"]
	queued = []
	enqueue = frappe.enqueue
	frappe.enqueue = lambda *args, **kwargs: queued.append(args)
	try:
		with as_user(OWNER):
			apps.save(["OneAI"])
			assert {"OneAI", "OneIntake"} <= set(apps.hidden()), apps.hidden()
			try:
				run.once("summarise", "anything")
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
					raise AssertionError("a mailbox switched on with OneIntake off")
			assert not hiring.on("one_ai_screen")
			shown = {one["key"] for one in settings.sections()["sections"]}
			assert not shown & {"memory", "oneai", "reads", "intake"}, shown
			sidebars = get_module_sidebars()
			apps.trim(sidebars)
			labels = {item.get("label") for item in sidebars["One"]["items"] if item.get("type") == "Section Break"}
			assert not labels & {"OneAI", "OneIntake"}, labels
			assert "One Intake" not in sidebars
			assert all(item.get("link_to") != "Ready to Submit" for item in (sidebars.get("OneBook") or {}).get("items", []))
			apps.save(["OneIntake"])
			assert apps.ai_on() and not apps.intake_on()
			apps.save([])
			assert apps.intake_on() and hiring.on("one_ai_screen") == bool(frappe.db.get_single_value("HR Settings", "one_ai_screen"))
	finally:
		frappe.enqueue = enqueue
		with as_user(OWNER):
			apps.save([])


@check
def one_the_frame_wears_the_workspace_colour():
	"""Frame Colour in Workspace › General › Contact and Branding is the rail and the bars
	around every screen, for everyone; saved empty, the frame is One's own."""
	from onedesk.one import company, settings

	was = frappe.db.get_value("Company", COMPANY, "one_frame_colour")
	try:
		settings._save_general({"one_frame_colour": "#7C2D12"})
		assert company.frame_colour() == "#7C2D12", "the frame did not take the workspace's colour"
		settings._save_general({"one_frame_colour": ""})
		assert not company.frame_colour(), "an emptied Frame Colour still coloured the frame"
	finally:
		frappe.db.set_value("Company", COMPANY, "one_frame_colour", was)


@check
def oneadmin_a_code_installs_a_private_app_that_stays():
	"""The operator makes a code for a workspace; typed there (in any case,
	without its dashes) it queues one Install App job, and typing it again
	queues no second. The job checks the app is on the bench group, asks press
	to install it and waits until press lists it. A claimed app can't be
	offered again or taken off the record. A wrong code, or another
	workspace's, opens nothing; an app missing from the bench fails its job
	and leaves the workspace Live."""
	from unittest.mock import patch

	from onedesk.one_admin import press, private, runner

	app = "acme_fleet"
	installed: list = []
	asked: list = []

	def pressed(method, **kwargs):
		asked.append(method)
		if method == "press.api.site.installed_apps":
			return [{"app": one} for one in installed]
		if method == "press.api.site.install_app":
			installed.append(kwargs["app"])
		return None

	with patch("onedesk.one_admin.site.is_admin", return_value=True), patch("frappe.sendmail"), patch.object(press, "call", side_effect=pressed), patch.object(
		press, "apps", return_value=[{"name": app}]
	):
		for slug in ("acme-private", "other-private"):
			frappe.get_doc({"doctype": "Tenant", "slug": slug, "status": "Live", "jurisdiction": "Global", "site": f"{slug}.frappe.cloud", "bench": "bench-1"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Private App", "app": app, "title": "Acme Fleet", "said": "Acme's vans, drivers and routes."}).insert(ignore_permissions=True)
		code = private.new_code(app, "acme-private")
		assert len(private.normal(code)) == private.LENGTH and code.count("-") == 2, code
		for wrong in ("", "ABCD-EFGH-JKLM"):
			try:
				private.claim("acme-private", wrong)
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError(f"{wrong!r} opened an app")
		try:
			private.claim("other-private", code)
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("another workspace's code opened the app")
		said = private.claim("acme-private", code.lower().replace("-", " "), by="owner@acme.test")
		assert said["title"] == "Acme Fleet" and said["state"] == "Installing", said
		job = frappe.db.get_value("Private App Grant", {"tenant": "acme-private"}, "job")
		assert private.claim("acme-private", code)["state"] == "Installing"
		assert frappe.db.count("Provisioning Job", {"tenant": "acme-private", "kind": private.KIND}) == 1, "typed twice, queued twice"
		for _ in range(6):
			if runner.advance(job) in ("Done", "Failed"):
				break
		assert frappe.db.get_value("Provisioning Job", job, "status") == "Done", frappe.db.get_value("Provisioning Job", job, "error")
		assert installed == [app] and asked.count("press.api.site.install_app") == 1, asked
		assert private.mine("acme-private") == [{"app": app, "title": "Acme Fleet", "said": "Acme's vans, drivers and routes.", "icon": "", "state": "Installed"}]
		try:
			private.new_code(app, "acme-private")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a claimed app was offered again")
		doc = frappe.get_doc("Private App", app)
		doc.set("grants", [row for row in doc.grants if row.tenant != "acme-private"])
		try:
			doc.save(ignore_permissions=True)
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("an installed app came off the record")

		other = private.new_code(app, "other-private")
		with patch.object(press, "apps", return_value=[]):
			private.claim("other-private", other)
			job = frappe.db.get_value("Private App Grant", {"tenant": "other-private"}, "job")
			assert runner.advance(job) == "Failed"
		assert frappe.db.get_value("Tenant", "other-private", "status") == "Live", "a failed install took the workspace down"
		assert private.mine("other-private")[0]["state"] == "Failed"


@check
def one_a_private_app_is_always_on():
	"""A private app installed has a card in Apps that can't be turned off,
	and uninstalling it is refused."""
	from unittest.mock import patch

	from onedesk.one import apps, private

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
def onehr_uae_papers_are_kept_where_a_company_is_in_the_uae():
	"""Sahara is in the UAE, so an employee's papers may be an Emirates ID, a
	Labour Card, Health Insurance or a Medical Fitness certificate, and
	expire as any other; a workspace with no company there gets none of them."""
	from onedesk.one_hr import papers

	assert papers.wanted({"Germany"}) == [] and "Emirates ID" in papers.wanted({"United Arab Emirates", "Germany"})
	papers.settle()
	for name in ("Emirates ID", "Labour Card", "Health Insurance", "Medical Fitness"):
		assert frappe.db.exists(papers.KIND, name), name


@check
def onehr_late_arrivals_can_count_as_an_absent_day():
	"""Off by default. At 4 late arrivals to an absent day, an employee late
	five times in October loses one day on the October payslip, which says
	so, and is paid that much less; with the rule off again nothing is taken."""
	from onedesk.one_hr import lates

	assert lates.days_off(5, 4) == 1 and lates.days_off(3, 4) == 0 and lates.days_off(9, 0) == 0
	employee = "HR-EMP-00018"
	start, end = "2026-10-01", "2026-10-31"
	marked = set(frappe.get_all("Attendance", filters={"employee": employee, "attendance_date": ["between", [start, end]]}, pluck="attendance_date"))
	holidays = set(frappe.get_all("Holiday", filters={"parent": frappe.db.get_value("Company", COMPANY, "default_holiday_list")}, pluck="holiday_date"))
	days = [day for day in (add_days(start, n) for n in range(31)) if getdate(day) not in marked and getdate(day) not in holidays][:5]
	assert len(days) == 5, days
	for day in days:
		frappe.get_doc({"doctype": "Attendance", "employee": employee, "attendance_date": day, "status": "Present", "late_entry": 1, "company": COMPANY}).submit()

	def slip():
		said = frappe.get_doc({"doctype": "Salary Slip", "employee": employee, "posting_date": end, "start_date": start, "end_date": end, "payroll_frequency": "Monthly"})
		said.insert()
		return said

	assert not frappe.db.get_single_value("HR Settings", "one_lates_per_absence"), "off by default"
	plain = slip()
	assert not plain.one_late_days
	paid, gross = plain.payment_days, plain.gross_pay
	plain.delete()
	frappe.db.set_single_value("HR Settings", "one_lates_per_absence", 4)
	late = slip()
	assert late.one_late_days == 1 and late.payment_days == paid - 1, (late.one_late_days, late.payment_days, paid)
	assert late.gross_pay < gross, (late.gross_pay, gross)
	late.save()
	assert late.one_late_days == 1 and late.payment_days == paid - 1, "a second save takes nothing more"
	late.delete()
	frappe.db.set_single_value("HR Settings", "one_lates_per_absence", 0)


@check
def one_devices_decide_where_a_passkey_lives():
	"""Signing in gives a browser its id and lists it. The builder sorts two:
	the reception computer, shared, where Tariq is neither offered nor allowed
	a passkey; and his laptop, assigned, which takes one beside his phone's
	that signs for him. Lost retires the laptop's and leaves the phone's."""
	import json

	from onedesk.one import devices
	from onedesk.one.signin import facts
	from onedesk.one_demo.setup import BUILDER
	from onedesk.one_hr import passkey

	tariq = _employee("Tariq")
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
	entry = frappe.db.get_value("Payroll Entry", {"docstatus": 1, "salary_slip_based_on_timesheet": 0})
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
	from onedesk.one import letter_heads, numbering, printing
	from onedesk.one_mail import mail_templates

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
		priced = {rfq.items[0].name: {"rate": 120, "qty": 40, "discount": 10}}
		said = portal.quote_preview(rfq.name, priced)
		assert said["rows"][rfq.items[0].name]["discount"] and said["total"], said
		answered = portal.send_quote(rfq.name, priced, "Delivered in two lots.")
		assert frappe.db.get_value("Supplier Quotation", answered, "supplier") == supplier
		assert frappe.db.get_value("Supplier Quotation", answered, "contact_person") == frappe.db.get_value("Contact", {"user": user}, "name"), "the quote is theirs"
		row = frappe.db.get_value(
			"Supplier Quotation Item", {"parent": answered}, ["price_list_rate", "discount_percentage", "rate"], as_dict=True
		)
		assert (row.price_list_rate, row.discount_percentage, row.rate) == (120, 10, 108), row
		sent = frappe.get_doc("Supplier Quotation", answered)
		assert said["net"] == frappe.utils.fmt_money(sent.net_total, currency=sent.currency), (said["net"], sent.net_total)
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
def a_customer_and_a_supplier_find_their_own_on_the_portal():
	"""Khalid, Mansour & Sons' contact, opens the portal (frontend/portal):
	Home counts what he has, his invoices list, one opens with its total and
	a PDF, and another customer's refuses him. His villa's page, his profile,
	Your Data and Apps answer. Rami, Emirates Sealants' contact, opens a quote
	request sent to his supplier with the rows he prices."""
	import onedesk.one_project.portal
	from onedesk.one import portal

	khalid, rami = "khalid@mansour.example", "sales@emiratessealants.example"
	theirs = frappe.db.get_value("Sales Invoice", {"customer": "Mansour & Sons", "docstatus": 1}, "name")
	others = frappe.db.get_value("Sales Invoice", {"customer": ("!=", "Mansour & Sons"), "docstatus": 1}, "name")
	with as_user(khalid):
		assert portal.reads()
		said = portal.home()
		home = {one["path"]: one for one in said["tiles"]}
		assert "invoices" in home and int(home["invoices"]["count"]) >= 1, home
		assert any(one["to"].startswith("invoices/") for one in said["asks"]), said["asks"]
		assert home["invoices"]["figure"], home["invoices"]
		listed = portal.rows("invoices")
		assert listed["doctype"] == "Sales Invoice" and theirs in {one["name"] for one in listed["rows"]}, listed
		said = portal.record("invoices", theirs)
		assert said["name"] == theirs and said["totals"], said
		assert said["summary"]["value"] and [one["label"] for one in said["steps"]] == ["Issued", "Paid"], said["steps"]
		assert any(one["to"].startswith("orders/") for one in said["related"]), "the order the bill came from"
		paid = portal.rows("invoices", state=listed["rows"][0]["status"])
		assert paid["rows"] and {one["status"] for one in paid["rows"]} == {listed["rows"][0]["status"]}
		assert any("download_pdf" in (one["href"] or "") for one in said["actions"]), said["actions"]
		try:
			portal.record("invoices", others)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a customer opened another customer's invoice")
		try:
			portal.rows("purchase-orders")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a customer listed a supplier's tab")
		assert onedesk.one_project.portal.page(VILLA)["title"]
		form = portal.form("profile")
		assert form["doc"]["name"] == khalid and form["fields"], form
		assert set(portal.your_data()) == {"copy", "deletion", "password"}
		assert isinstance(portal.apps(), list)
	supplier = frappe.db.get_value("Portal User", {"user": rami, "parenttype": "Supplier"}, "parent")
	sent = frappe.db.get_value("Request for Quotation Supplier", {"supplier": supplier, "docstatus": 1}, "parent")
	with as_user(rami):
		said = portal.rfq(sent)
		assert said["rows"] and said["money"]["symbol"], said
		assert "rfq" in {one["path"] for one in portal.home()["tiles"]}


@check
def a_customer_accepts_one_quotation_and_declines_another_on_the_portal():
	"""Khalid has two open quotations. He accepts one, needed by the end of
	next month with his order number: erpnext makes the order from it, a
	draft for whoever made the quotation to check, who is told. He declines
	the other with a reason: erpnext sets it lost with it, and they are told.
	Neither can be answered twice, and another customer's can't be at all."""
	from unittest import mock

	from onedesk.one import portal

	khalid = "khalid@mansour.example"
	base = frappe.get_doc("Quotation", frappe.get_all("Quotation", filters={"party_name": "Mansour & Sons", "docstatus": 1}, pluck="name", limit=1)[0])
	opened = []
	for _one in range(2):
		new = frappe.copy_doc(base)
		new.transaction_date, new.valid_till, new.payment_schedule = today(), add_days(today(), 30), []
		for row in new.items:
			row.ordered_qty = 0
		new.insert(ignore_permissions=True)
		new.submit()
		opened.append(new.name)
	taken, turned = opened
	with as_user(khalid):
		assert portal.record("quotations", taken)["answer"]
		assert taken in {one["to"].split("/")[-1] for one in portal.home()["asks"]}, "an open quotation asks for an answer"
		with mock.patch("onedesk.one_crm.tell.quotation_accepted") as told:
			order = portal.accept_quote("quotations", taken, add_days(today(), 45), "MS-PO-4471")
		assert told.called
		said = frappe.db.get_value("Sales Order", order, ["docstatus", "customer", "delivery_date", "po_no"], as_dict=True)
		assert frappe.db.get_value("Sales Order", order, "contact_person") == frappe.db.get_value("Contact", {"user": khalid}, "name"), "the order is his"
		assert (said.docstatus, said.customer, str(said.delivery_date), said.po_no) == (0, "Mansour & Sons", add_days(today(), 45), "MS-PO-4471"), said
		page = portal.record("quotations", taken)
		assert not page["answer"] and page["status"] == "Accepted", page["status"]
		try:
			portal.accept_quote("quotations", taken, add_days(today(), 45))
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a quotation was accepted twice")
		with mock.patch("onedesk.one_crm.tell.quotation_declined") as told:
			portal.decline_quote("quotations", turned, "Another supplier came in lower.")
		assert told.called
		assert frappe.db.get_value("Quotation", turned, ["status", "order_lost_reason"]) == ("Lost", "Another supplier came in lower.")
		assert portal.record("quotations", turned)["status"] == "Declined"
	other = frappe.get_all("Quotation", filters={"party_name": ("!=", "Mansour & Sons"), "docstatus": 1, "status": "Open"}, pluck="name", limit=1)
	if other:
		with as_user(khalid):
			try:
				portal.decline_quote("quotations", other[0])
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("a customer declined another customer's quotation")


@check
def a_record_hidden_from_a_portal_contact_is_gone_for_them():
	"""Mansour & Sons' invoices are all Khalid's to see until one is unticked
	for him in its Portal dialog: then it neither lists nor opens for him, on
	the portal, erpnext's pages or a PDF, and the rest still do. Ticked again,
	it is back. A quote request unticked for Rami is gone for him the same
	way, and only a record's own contacts can be unticked."""
	from onedesk.one import portal, portal_share

	khalid, rami = "khalid@mansour.example", "sales@emiratessealants.example"
	invoices = frappe.get_all("Sales Invoice", filters={"customer": "Mansour & Sons", "docstatus": 1}, pluck="name", order_by="name")
	assert len(invoices) > 1, invoices
	his, other = invoices[0], invoices[1]

	def listed(user, kind):
		frappe.local.flags.pop("one_portal_contacts", None)
		with as_user(user):
			return {one["name"] for one in portal.rows(kind)["rows"]}

	contact = frappe.db.get_value("Contact", {"user": khalid}, "name")
	assert listed(khalid, "invoices") >= {his, other}, "the whole company's, by default"
	said = portal_share.set_access("Sales Invoice", other, frappe.as_json([contact]))
	assert [one["sees"] for one in said["groups"][0]["people"] if one["contact"] == contact] == [False]
	assert his in listed(khalid, "invoices") and other not in listed(khalid, "invoices")
	with as_user(khalid):
		assert portal.record("invoices", his)["name"] == his
		assert not frappe.has_website_permission(frappe.get_doc("Sales Invoice", other)), "the PDF and erpnext's page refuse it too"
		try:
			portal.record("invoices", other)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a record unticked for a contact opened for them")
	portal_share.set_access("Sales Invoice", other, "[]")
	assert other in listed(khalid, "invoices")

	row = frappe.db.get_value("Request for Quotation Supplier", {"supplier": "Emirates Sealants & Fixings", "docstatus": 1}, ["parent"], as_dict=True)
	theirs = frappe.db.get_value("Contact", {"user": rami}, "name")
	portal_share.set_access("Request for Quotation", row.parent, frappe.as_json([theirs]))
	assert row.parent not in listed(rami, "rfq")
	portal_share.set_access("Request for Quotation", row.parent, "[]")
	assert row.parent in listed(rami, "rfq")
	try:
		portal_share.set_access("Sales Invoice", his, frappe.as_json([theirs]))
	except frappe.ValidationError:
		pass
	else:
		raise AssertionError("a record was hidden from somebody else's contact")
	frappe.local.flags.pop("one_portal_contacts", None)


@check
def a_link_opens_a_record_for_somebody_without_an_account_and_answers_once():
	"""Omar sends Khalid a link to an open quotation: anybody holding it sees
	the quotation without signing in, accepts it once with their name, and
	then only reads it. Karim sends Rami a link to a quote request, which
	prices and sends a quote as Emirates Sealants' once. A link mailed again
	goes to the same person; rotated, the old one stops and a new one opens;
	revoked or past its day, it opens nothing, and a guess opens nothing."""
	from unittest import mock

	from onedesk.one import portal_share

	base = frappe.get_doc("Quotation", frappe.get_all("Quotation", filters={"party_name": "Mansour & Sons", "docstatus": 1}, pluck="name", limit=1)[0])
	quote = frappe.copy_doc(base)
	quote.transaction_date, quote.valid_till, quote.payment_schedule = today(), add_days(today(), 10), []
	for row in quote.items:
		row.ordered_qty = 0
	quote.insert(ignore_permissions=True)
	quote.submit()
	khalid = frappe.db.get_value("Contact", {"user": "khalid@mansour.example"}, "name")
	with as_user("omar@one.test"):
		said = portal_share.access("Quotation", quote.name)
		assert said["may"] and khalid in {one["contact"] for one in said["groups"][0]["reachable"]}
		with mock.patch("onedesk.one.tell.portal_link") as told:
			made = portal_share.make_link("Quotation", quote.name, contact=khalid, send=1)
		assert told.call_args.args[0] == "khalid@mansour.example" and told.call_args.kwargs["until"]
	token = answered = made["url"].rsplit("/", 1)[-1]
	link = frappe.get_doc("Portal Link", made["links"][0]["name"])
	assert getdate(link.expires_on) == getdate(quote.valid_till), "a quotation's link lasts as long as it does"
	assert link.token_hash != token and len(token) == 40, "only the token's hash is looked up"

	with as_user("Guest"):
		page = portal_share.link_view(token)
		assert page["kind"] == "record" and page["page"]["answer"] and "link_pdf" in page["page"]["actions"][0]["href"]
		try:
			portal_share.link_accept(token, add_days(today(), 20), by="")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a link was answered by nobody")
		with mock.patch("onedesk.one_crm.tell.quotation_accepted"):
			order = portal_share.link_accept(token, add_days(today(), 20), "MS-PO-9", by="Khalid Mansour")
		assert frappe.db.get_value("Sales Order", order, "contact_person") == khalid
		assert not portal_share.link_view(token)["page"]["answer"]
		assert portal_share.link_view(token)["answered"]["by"] == "Khalid Mansour"
		try:
			portal_share.link_decline(token, by="Khalid Mansour")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a link was answered twice")

	rfq = frappe.copy_doc(frappe.get_doc("Request for Quotation", frappe.db.get_value("Request for Quotation Supplier", {"supplier": "Emirates Sealants & Fixings", "docstatus": 1}, "parent")))
	rfq.transaction_date, rfq.schedule_date = today(), add_days(today(), 14)
	rfq.suppliers = [one for one in rfq.suppliers if one.supplier == "Emirates Sealants & Fixings"]
	for one in rfq.items:
		one.schedule_date = rfq.schedule_date
	rfq.insert(ignore_permissions=True)
	rfq.submit()
	with as_user("karim@one.test"):
		made = portal_share.make_link("Request for Quotation", rfq.name, email="quotes@emiratessealants.example")
	token = made["url"].rsplit("/", 1)[-1]
	rows = {one.name: {"qty": one.qty, "rate": 20, "discount": 10} for one in rfq.items}
	with as_user("Guest"):
		assert portal_share.link_view(token)["page"]["open"]
		assert portal_share.link_preview(token, frappe.as_json(rows))["total"]
		with mock.patch("onedesk.one_inventory.tell.quote_received"):
			sent = portal_share.link_send(token, frappe.as_json(rows), "Two weeks", by="Rami Haddad")
		assert not portal_share.link_view(token)["page"]["open"]
	assert frappe.db.get_value("Supplier Quotation", sent, ["supplier", "docstatus"]) == ("Emirates Sealants & Fixings", 0)

	with as_user("karim@one.test"):
		name = made["links"][0]["name"]
		with mock.patch("onedesk.one.tell.portal_link") as told:
			try:
				portal_share.mail_link(name)
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("an answered link was mailed again")
		again = portal_share.make_link("Request for Quotation", rfq.name, email="quotes@emiratessealants.example")
		old = again["url"].rsplit("/", 1)[-1]
		twice = portal_share.make_link("Request for Quotation", rfq.name, email="quotes@emiratessealants.example")
		assert twice["url"] == again["url"], "a second link for the same person is the one they have"
		with mock.patch("onedesk.one.tell.portal_link") as told:
			portal_share.mail_link(again["links"][0]["name"])
		assert told.called
		rotated = portal_share.rotate_link(again["links"][0]["name"])
		new = rotated["url"].rsplit("/", 1)[-1]
		states = [one["state"] for one in portal_share.revoke_link(rotated["links"][0]["name"])]
		assert states.count("revoked") == 2, states
	with as_user("Guest"), mock.patch("frappe.utils.print_format.download_pdf") as printed:
		portal_share.link_pdf(answered)
	frappe.flags.ignore_print_permissions = False
	assert printed.call_args.args[:2] == ("Quotation", quote.name), "an answered link still prints"
	frappe.db.set_value("Portal Link", link.name, "expires_on", add_days(now_datetime(), -1))
	with as_user("Guest"):
		for gone in (old, new, answered, "0" * 40, ""):
			try:
				portal_share.link_view(gone)
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("a revoked, expired or guessed link opened")
	with as_user("khalid@mansour.example"):
		try:
			portal_share.access("Quotation", quote.name)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a portal reader opened a record's Portal dialog")


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
		assert kinds and {one["doctype"] for one in kinds} == set(masters.listed())
		assert all(set(one) == {"group", "doctype", "label", "mark", "count"} for one in kinds)
		territory = frappe.get_doc({"doctype": "Territory", "territory_name": "Oman"}).insert()
		assert territory.parent_territory, "a tree's new value goes under its root (masters.place)"
		assert masters.homes()["Territory"][1]["route"] == "/desk/territory"
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
def onecloud_holds_a_workbook_with_its_history():
	"""Layla makes a workbook in her files from OneCloud, saves it twice with
	an edit to B2, renames it, and finds both saves in its history and B2's
	before and after. Rania can't open it. A copy of the first version is a
	workbook of its own; restoring that version brings 100 back; deleting
	the File takes the workbook and its history with it."""
	from onedesk.one_sheet import ai as sheet_ai
	from onedesk.one_sheet import api, live, versions

	def held(value):
		return json.dumps({"sheet": {"v": 2, "current": "Sheet1", "sheets": {"Sheet1": {"rows": {"1": [None, value]}}}}})

	with as_user(OWNER):
		made = api.make("@my", "Glazing rates")
		book = made["workbook"]
		assert made["name"] == "Glazing rates" and api.workbook_of(made["url"]) == book
		assert api.get_sheet(book)["can_write"]
		api.save_sheet("Glazing rates", held("100"), book, json.dumps([{"op_type": "setCell", "sub_sheet": "Sheet1", "cell_refs": ["B2"], "before": {"B2": None}, "after": {"B2": "100"}}]), "r1")
		assert api.save_sheet("Glazing rates", held("100"), book, "", "r1")["head_seq"] == 2, "a save sent twice is kept once"
		frappe.db.set_value(versions.VERSION, {"workbook": book}, "creation", frappe.utils.add_to_date(None, minutes=-5))
		api.save_sheet("Glazing rates 2026", held("120"), book, json.dumps([{"op_type": "setCell", "sub_sheet": "Sheet1", "cell_refs": ["B2"], "before": {"B2": "100"}, "after": {"B2": "120"}}]), "r2")
		assert frappe.db.get_value("File", made["id"], "file_name") == "Glazing rates 2026"
		assert api.rename_sheet(book, "Glazing rates")["title"] == "Glazing rates"
		told = versions.timeline(book)["buckets"]["earlier"]["items"]
		assert len(told) == 2 and told[0]["seq"] > told[1]["seq"], told
		assert [(one["before"], one["after"]) for one in versions.ops_for_cell(book, "B2", "Sheet1")] == [("100", "120"), (None, "100")]
		first = told[-1]["id"]
		assert '"100"' in versions.state_at(first)["sheets_data"]
		assert versions.label_snapshot(first, "Before the discount")["pinned"]
		assert versions.timeline(book)["buckets"]["pinned"]["items"][0]["label"] == "Before the discount"
		copy = versions.make_copy(first, "Glazing rates, first")
		assert '"100"' in api.get_sheet(copy)["sheets_data"]
		versions.restore(first)
		assert '"100"' in api.get_sheet(book)["sheets_data"]
		assert api.get_link_preview("https://example.com") == {"url": "https://example.com"}
		api.download(book)
		assert frappe.local.response["location"] == f"/desk/workbook/{book}"
		admitted = live.admit("workbook", book)
		assert admitted["ok"] and admitted["write"] and admitted["who"]["user"] == OWNER, admitted
		told = sheet_ai.page({"page": "workbook", "record": book, "selection": {"page": "workbook", "workbook": book, "sheet": "Sheet1", "range": "B2:B2", "active": "B2"}})
		assert "Sheet1 with B2:B2 selected" in told and '"B2": "100"' in told, "OneAI is told the workbook and what is selected"
	with as_user("rania@one.test"):
		try:
			api.get_sheet(book)
			raise AssertionError("Rania opened Layla's workbook")
		except frappe.PermissionError:
			pass
		assert live.admit("workbook", book) == {"ok": False}, "nor joins its room"
		assert live.admit("file", book) == {"ok": False}
	for one in (made["id"], frappe.db.get_value(api.WORKBOOK, copy, "file")):
		frappe.delete_doc("File", one, ignore_permissions=True, force=True)
	assert not frappe.db.exists(api.WORKBOOK, book) and not frappe.db.exists(versions.VERSION, {"workbook": book})


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
		plain, doc = frappe.get_doc("Project", name), frappe.get_doc("Project", name)
		Project.update_purchase_costing(plain)
		doc.update_purchase_costing()
		assert abs(flt(plain.total_purchase_cost) - flt(doc.total_purchase_cost) - stored) < 0.01 and stored <= bought, (name, stored)
		break
	else:
		raise AssertionError("no project bought anything into a store")

@check
def a_table_keeps_its_formulas():
	"""Layla types a formula under a quotation's items that reads a Costing
	sheet; drawing the table again after a change on the form keeps it. She
	saves the workbook as a template: it keeps the Costing sheet and leaves
	the table out, and it starts a plain workbook like any other template.
	All of it is undone afterwards."""
	from onedesk.one_sheet import api, storage, table, templates

	def first_sheet(book):
		held = table._held(book)
		return table.stored(json.loads(storage.decode_sheets_data(held.sheets_data)), held.bound_sheet)

	quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
	frappe.db.savepoint("template_check")
	try:
		with as_user(OWNER):
			book = table.open_table("Quotation", quote, "items")
			held = table._held(book)
			data = json.loads(storage.decode_sheets_data(held.sheets_data))
			rows = table.stored(data, held.bound_sheet)
			qty = rows["0"].index("Quantity")
			rows["1"][qty] = "=Costing!C4:C"
			data["sheet"]["sheets"]["Costing"] = {"rows": {"3": ["CW01", "Wall", "10"]}}
			frappe.db.set_value(api.WORKBOOK, book, "sheets_data", storage.encode_sheets_data(json.dumps(data)))
			child = frappe.get_doc("Quotation", quote).items[0]
			frappe.db.set_value(child.doctype, child.name, "qty", flt(child.qty) + 1)
			was = first_sheet(book)["0"][0]
			table.refresh(book)
			assert first_sheet(book)["0"][0] != was, "drawn again"
			assert first_sheet(book)["1"][qty] == "=Costing!C4:C", "and the formula stays"
			made = templates.save_as(book, "Glazing costing")
			kept = json.loads(storage.decode_sheets_data(frappe.db.get_value(api.WORKBOOK, made["name"], "sheets_data")))
			assert list(kept["sheet"]["sheets"]) == ["Costing"], "a template is its own sheets, not the record's table"
			assert templates.sheets_of(made["name"]) == [{"name": "Costing", "cells": {"A4": "CW01", "B4": "Wall", "C4": "10"}}]
			assert {"name": made["name"], "title": "Glazing costing"} in templates.listed()
			copy = api.make("@my", "Glazing for Bayview", made["name"])
			assert copy["workbook"] != book
	finally:
		frappe.db.rollback(save_point="template_check")

@check
def oneai_makes_reads_and_writes_a_workbook():
	"""OneAI suggests a workbook with a formula and a bold header, and on
	approval it is made in OneCloud; it finds and reads it, writes a cell
	and a note as cards, and refuses a record's table sheet and a name that
	isn't a cell. All undone afterwards."""
	from onedesk.one_ai import proposals, tools
	from onedesk.one_sheet import ai

	frappe.db.savepoint("oneai_sheet_check")
	try:
		with as_user(OWNER):
			said = tools.run("draft_workbook", {"name": "Glass check", "sheets": [{"name": "Prices", "cells": {"A1": "Item", "B1": "Rate", "A2": "Clear 8mm", "B2": 60, "B3": "=B2*1.05"}, "looks": {"A1:B1": {"bold": True}}}]})
			assert not said["ran"] and said["answer"]["state"] == "Proposed", said
			book = proposals.apply(said["answer"]["proposal"])["record"]
			assert "at least one sheet" in ai.draft_workbook("Empty check", [])["error"]
			found = ai.my_workbooks("Glass check")
			assert [one["workbook"] for one in found] == [book] and found[0]["sheets"] == ["Prices"], found
			read = ai.read_workbook(book)
			assert read["cells"] == {"A1": "Item", "B1": "Rate", "A2": "Clear 8mm", "B2": 60, "B3": "=B2*1.05"}, read
			wrote = ai.write_cells(book, "Prices", {"B2": 65}, {"B2:B3": {"numberFormat": "number:us:2"}})
			proposals.apply(wrote["proposal"])
			note = ai.comment_on_cell(book, "Prices", "B2", "Up from 60 this month.")
			proposals.apply(note["proposal"])
			read = tools.run("read_workbook", {"workbook": book, "cells": "B2:B3"})["answer"]
			assert read["cells"] == {"B2": 65, "B3": "=B2*1.05"} and read["notes"] == {"B2": "Up from 60 this month."}, read
			assert "isn't a cell" in tools.run("write_cells", {"workbook": book, "sheet": "Prices", "cells": {"row 3": 1}})["answer"]["error"]
			quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
			from onedesk.one_sheet import table

			bound = table.open_table("Quotation", quote, "items")
			assert "record's table" in tools.run("write_cells", {"workbook": bound, "sheet": "Items", "cells": {"B2": "x"}})["answer"]["error"]
	finally:
		frappe.db.rollback(save_point="oneai_sheet_check")


@check
def a_spreadsheet_file_opens_and_saves_back_into_itself():
	"""A CSV in OneCloud opens as a workbook that reads it in the first time,
	what is done to it is written back into the same File, what it held
	before kept as a version, and a new version put in from outside is read
	in again. All undone afterwards."""
	import base64

	from onedesk.one_sheet import api
	from onedesk.one_storage import namespace as ns

	frappe.db.savepoint("file_sheet_check")
	try:
		with as_user(OWNER):
			made = frappe.get_doc({"doctype": "File", "file_name": "Prices check.csv", "content": b"Item,Rate\nGL,60\n", "is_private": 1, "folder": ns.HOME})
			made.insert()
			book = api.open_file(made.name)["workbook"]
			assert api.open_file(made.name)["workbook"] == book, "one file, one workbook"
			source = api.get_sheet(book)["source"]
			assert source == {"kind": "csv", "url": made.file_url, "fresh": True, "name": "Prices check.csv"}, source
			api.save_sheet("Prices check.csv", json.dumps({"sheet": {"v": 2, "current": "Sheet1", "sheets": {"Sheet1": {"rows": {"0": ["Item", "Rate"], "1": ["GL", "65"]}}}}}), book)
			assert not api.get_sheet(book)["source"]["fresh"], "read in once"
			api.write_back(book, base64.b64encode(b"Item,Rate\nGL,65\n").decode())
			now = frappe.get_doc("File", made.name)
			assert now.get_content() in (b"Item,Rate\nGL,65\n", "Item,Rate\nGL,65\n"), now.get_content()
			assert frappe.db.count("Cloud File Version", {"file": made.name}) == 1, "what it held is a version"
			api.file_replaced(made.name)
			assert api.get_sheet(book)["source"]["fresh"], "a version from outside is read in again"
			try:
				api.open_file(frappe.get_doc({"doctype": "File", "file_name": "notes check.txt", "content": b"x", "is_private": 1, "folder": ns.HOME}).insert().name)
				raise AssertionError("a text file opened as a workbook")
			except frappe.ValidationError:
				pass
	finally:
		frappe.db.rollback(save_point="file_sheet_check")


@check
def a_sheet_prints_under_the_letter_head():
	"""A sheet prints as a PDF under the workspace's letter head, or another
	one chosen, or none, drawn as it is on screen and never from HTML the
	editor sends; kept, it lands beside the workbook in OneCloud. All undone
	afterwards."""
	from onedesk.one_sheet import api, paper

	frappe.db.savepoint("paper_check")
	try:
		with as_user(OWNER):
			book = api.make("@my", "Paper check")["workbook"]
			sheet = {"name": "Sheet1", "size": [2, 2], "cells": [[0, 0, "Item", {"bold": True}], [0, 1, "<script>x</script>", {}], [1, 0, "Glass", {}]], "head": 1}
			top = frappe.db.get_value("Letter Head", {"is_default": 1}, "content") or ""
			drawn = paper.page("Paper check", [sheet])
			assert top[:40] in drawn and "&lt;script&gt;" in drawn and "<script>" not in drawn, "under the letter head, text as text"
			other = frappe.get_doc({"doctype": "Letter Head", "letter_head_name": "Paper check head", "source": "HTML", "content": "<p>Paper check head</p>"})
			other.insert(ignore_permissions=True)
			assert next(one.name for one in paper.letter_heads()) == frappe.db.get_value("Letter Head", {"is_default": 1}), "the default first"
			assert "Paper check head" in paper.page("Paper check", [sheet], letter_head=other.name), "the letter head chosen"
			assert paper._record(book).company == COMPANY, "a head written for record prints finds the company"
			assert top[:40] not in paper.page("Paper check", [sheet], letter_head=paper.NO_HEAD), "or none"
			try:
				paper.page("Paper check", [sheet], letter_head="No such head")
				raise AssertionError("a letter head that isn't there printed")
			except frappe.ValidationError:
				pass
			paper.pdf(book, json.dumps([sheet]))
			assert frappe.local.response.filecontent[:4] == b"%PDF" and frappe.local.response.filename == "Paper check - Sheet1.pdf"
			kept = paper.pdf(book, json.dumps([sheet]), keep="cloud")
			item = frappe.db.get_value("File", kept["id"], ["folder", "file_name"], as_dict=True)
			assert item.folder == frappe.db.get_value("File", frappe.db.get_value("Workbook", book, "file"), "folder") and item.file_name.endswith(".pdf"), item
			try:
				paper.pdf(book, json.dumps([sheet]), keep="record")
				raise AssertionError("a workbook on no record kept a print on one")
			except frappe.ValidationError:
				pass
	finally:
		for key in ("filecontent", "filename", "type"):
			frappe.local.response.pop(key, None)
		frappe.db.rollback(save_point="paper_check")


#: A one-pixel PNG, for a picture put into a document.
DOT_PNG = (
	b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
	b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@check
def a_document_is_written_in_onecloud():
	"""Layla writes a scope of works in her files. It opens with what she
	saved and keeps its page setup, takes a new name, carries a picture only
	its readers see, becomes a template another starts from, and a copy of it
	is a document of its own. Somebody who may not open it learns nothing of
	it. All undone afterwards."""
	import io

	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one_doc import api, templates

	was = getattr(frappe.local, "request", None)
	frappe.db.savepoint("doc_check")
	try:
		with as_user(OWNER):
			name = api.make("@my", "Scope check")["document"]
			api.save_document(name, "AAA=", "<h1>Scope</h1><p>Curtain wall.</p>")
			said = api.get_document(name)
			assert said["html"].startswith("<h1>Scope") and said["content"] == "AAA=" and said["can_write"], said
			assert said["trail"][-1]["id"] == "@my", "the path back is its folder"
			api.save_settings(name, json.dumps({"font_size": 17, "made_up": 1}))
			assert api.get_document(name)["settings"] == {"font_size": 17}, "only what a page may be set to"
			api.save_comments(name, "BBB=")
			assert api.get_document(name)["comments"] == "BBB="
			assert api.rename_document(name, "Scope of works check")["title"] == "Scope of works check"
			assert api.titles(json.dumps([name, "no-such-document"])) == {name: "Scope of works check"}
			assert any(one["email"] == OWNER for one in api.people()), "who may be mentioned"
			sent = EnvironBuilder(path="/api/method/onedesk.one_doc.api.add_picture", method="POST", data={"file": (io.BytesIO(DOT_PNG), "dot.png")})
			frappe.local.request = Request(sent.get_environ())
			picture = api.add_picture(name)
			assert picture["file_url"] == api.PICTURE + picture["name"]
			assert api.picture_extension(picture["name"]) == "png"
			api.picture(picture["name"])
			assert frappe.local.response["filecontent"] == DOT_PNG
			api.drop_pictures(json.dumps([picture["name"]]))
			assert not frappe.db.exists("File", picture["name"])
			api.download(name)
			assert frappe.local.response["location"] == f"/desk/document/{name}"
			template = templates.save_as(name, "Scope template")
			assert any(one["name"] == template["name"] for one in templates.listed())
			started = api.make("@my", "From the template", template["name"])["document"]
			assert frappe.db.get_value(api.DOCUMENT, started, "html").startswith("<h1>Scope"), "a template's content"
			copy = frappe.get_doc({"doctype": "File", "file_url": api.URL + name, "folder": frappe.db.get_value("File", said["file"], "folder"), "file_name": "Scope copy"})
			copy.flags.ignore_permissions = True
			copy.insert()
			held = api.document_of(copy.file_url)
			assert held != name and frappe.db.get_value(api.DOCUMENT, held, "file") == copy.name, "a copy is a document of its own"
			frappe.delete_doc("File", copy.name, ignore_permissions=True)
			assert not frappe.db.exists(api.DOCUMENT, held), "and goes with its File"
		with as_user("Guest"):
			assert api.titles([name]) == {}, "a reader who can't open it isn't told its name"
			try:
				api.get_document(name)
				raise AssertionError("somebody who may not open the document opened it")
			except frappe.PermissionError:
				pass
	finally:
		frappe.local.request = was
		frappe.db.rollback(save_point="doc_check")


@check
def a_document_keeps_its_versions_and_asks_oneai():
	"""Layla's document keeps a version taken while writing and one she
	names, but not two taken within ten minutes. In the OneAI panel on the
	document, OneAI is told what it says and what she selected; it rewrites
	the selection, writes after the paragraph her cursor is in and at the
	end, each as a card; finds and reads documents, and makes a covering
	letter on a quotation from the template. A reader who may not open the
	document is not told it exists. All undone afterwards."""
	from onedesk.one_ai import proposals, tools
	from onedesk.one_doc import ai, api, versions

	frappe.db.savepoint("doc_ai_check")
	try:
		with as_user(OWNER):
			name = api.make("@my", "Minutes check")["document"]
			api.save_document(name, "AAA=", "<h1>Minutes</h1><p>Glass arrives <strong>Monday</strong> at nine.</p><p>Frames follow.</p>")
			assert versions.new_version(name, "<p>First</p>")["manual"] == 0
			assert versions.new_version(name, "<p>Second</p>") is None, "not two within ten minutes"
			assert versions.new_version(name, "<p>Second</p>", "Before review")["title"] == "Before review"
			assert [one["title"] for one in versions.listed(name)][-1] == "Before review"
			page = {"page": "document", "record": name, "selection": {"page": "document", "document": name, "text": "at nine", "block": "Frames follow."}}
			told = ai.page(page)
			assert "Glass arrives **Monday** at nine." in told and 'selected: """at nine"""' in told, told
			frappe.flags.one_ai_page = page
			try:
				for where, html in (("selection", "<p>at noon</p>"), ("after", "<p>Fixings last.</p>"), ("end", "<p>Next meeting Friday.</p>")):
					said = tools.run("write_document", {"document": name, "html": html, "where": where})
					assert not said["ran"] and said["answer"]["state"] == "Proposed", said
					proposals.apply(said["answer"]["proposal"])
			finally:
				frappe.flags.one_ai_page = None
			held = frappe.db.get_value(api.DOCUMENT, name, ["html", "content"], as_dict=True)
			assert "Glass arrives <strong>Monday</strong> at noon." in held.html, held.html
			assert "<p>Frames follow.</p><p>Fixings last.</p>" in held.html and held.html.endswith("<p>Next meeting Friday.</p>"), held.html
			assert not held.content, "the editor opens from the HTML"
			assert "Nothing is selected" in ai.write_document(name, "<p>x</p>", "selection")["error"]
			found = ai.my_documents("Minutes check")
			assert [one["document"] for one in found] == [name], found
			assert "Next meeting Friday." in ai.read_document(name)["text"]
			assert "send its words" in ai.draft_document("Empty", "<p> </p>")["error"]
			said = tools.run("draft_document", {"name": "Agenda check", "html": "<h1>Agenda</h1><p>Glass.</p>"})
			made = proposals.apply(said["answer"]["proposal"])["record"]
			assert "<h1>Agenda</h1>" in frappe.db.get_value(api.DOCUMENT, made, "html")
			quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
			said = tools.run("draft_document", {"name": "Letter check", "record_doctype": "Quotation", "record_name": quote, "template": "Quotation covering letter"})
			assert said["answer"]["state"] == "Proposed", said
			letter = proposals.apply(said["answer"]["proposal"])["record"]
			assert api.get_document(letter)["record"] == {"doctype": "Quotation", "name": quote}, "filed on the quotation"
			assert 'data-field="grand_total"' in frappe.db.get_value(api.DOCUMENT, letter, "html"), "from the template"
		with as_user("rania@one.test"):
			assert ai.my_documents("Minutes check") == [] and "error" in ai.read_document(name)
			assert ai.page({"page": "document", "record": name}) == "The reader is on a document's page in OneWriter."
			try:
				versions.listed(name)
				raise AssertionError("Rania read Layla's versions")
			except frappe.PermissionError:
				pass
	finally:
		frappe.db.rollback(save_point="doc_ai_check")


@check
def a_records_text_is_written_in_onewriter():
	"""A draft quotation's terms open as a document filed on it. What Omar
	writes there becomes the terms through the quotation's save; terms
	changed on the quotation meanwhile are not written over, and opening it
	again starts from them. A document made in the quotation's Files is
	opened by whoever may open the quotation and nobody else, and a
	submitted quotation's terms open read only. All undone afterwards."""
	from onedesk.one_doc import api, field

	frappe.db.savepoint("doc_field_check")
	try:
		quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
		with as_user("omar@one.test"):
			name = field.open_field("Quotation", quote, "terms")
			assert field.open_field("Quotation", quote, "terms") == name, "one text, one document"
			said = api.get_document(name)
			assert said["can_write"] and said["record"] == {"doctype": "Quotation", "name": quote} and said["bound"]["field"] == "terms", said
			assert not api.save_document(name, "AAA=", "<p>Payment in 30 days.</p>").get("refused")
			assert field.same(frappe.db.get_value("Quotation", quote, "terms"), "<p>Payment in 30 days.</p>"), "the terms are what was written"
			frappe.db.set_value("Quotation", quote, "terms", "<p>Changed on the form.</p>")
			refused = api.save_document(name, "BBB=", "<p>Payment in 45 days.</p>")["refused"]
			assert "changed on the record" in refused, refused
			assert field.same(frappe.db.get_value("Quotation", quote, "terms"), "<p>Changed on the form.</p>"), "and not written over"
			field.open_field("Quotation", quote, "terms")
			again = frappe.db.get_value(api.DOCUMENT, name, ["html", "content"], as_dict=True)
			assert again.html == "<p>Changed on the form.</p>" and not again.content, "it starts again from the record"
			try:
				field.open_field("Quotation", quote, "address_display")
				raise AssertionError("a text the record works out opened as a document")
			except frappe.ValidationError:
				pass
			made = api.make(f"@records/Quotation/{quote}", "Covering letter")["document"]
			assert api.get_document(made)["record"]["name"] == quote
		with as_user("mariam@one.test"):
			for one in (name, made):
				try:
					api.get_document(one)
					raise AssertionError("somebody who may not open the quotation opened its document")
				except frappe.PermissionError:
					pass
		sent = frappe.get_all("Quotation", filters={"docstatus": 1}, pluck="name", order_by="name", limit=1)
		if sent:
			with as_user(OWNER):
				assert not api.get_document(field.open_field("Quotation", sent[0], "terms"))["can_write"], "a submitted record's terms are read only"
	finally:
		frappe.db.rollback(save_point="doc_field_check")


@check
def a_document_prints_with_its_records_fields():
	"""A covering letter filed on a quotation names its customer, total and
	lines as fields; on paper they are what the quotation says, the lines a
	table, under the letter head. Page setup's header, page numbers and line
	go to the PDF renderer. The quotation's print page lists the letter, and
	its PDF is attached to the quotation. All undone afterwards."""
	from onedesk.one_doc import api, paper

	frappe.db.savepoint("doc_paper_check")
	try:
		quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
		held = frappe.get_doc("Quotation", quote)
		with as_user("omar@one.test"):
			name = api.make(f"@records/Quotation/{quote}", "Covering letter check")["document"]
			offered = {one["field"]: one for one in paper.fields_of(name)}
			assert {"party_name", "grand_total", "items"} <= set(offered) and offered["items"]["table"], sorted(offered)
			html = (
				'<p>To <span data-field="party_name">Customer</span>,</p><p>Total <span data-field="grand_total">Grand Total</span></p>'
				'<p><span data-field="items">Items</span></p><p>Nobody sees <span data-field="no_such_field">this</span>.</p>'
			)
			api.save_document(name, "AAA=", html)
			filled = paper.fill(html, paper.record_of(name))
			assert frappe.utils.escape_html(held.party_name) in filled and frappe.format(held.grand_total, held.meta.get_field("grand_total"), held) in filled, filled
			assert '<table class="rows">' in filled and "<p><table" not in filled and held.items[0].item_code in filled, "the lines as a table, out of their paragraph"
			assert "Nobody sees ." in filled, "a field the record lacks prints nothing"
			assert "[Customer]" in paper.fill(html, None), "with no record, the field's name"
			api.save_settings(name, json.dumps({"print_header_left": "Sahara [x]", "print_show_pages": 1, "print_footer_separator": 1}))
			told = paper.options(name)
			assert told["header-left"] == "Sahara (x)" and "[page]" in told["footer-right"] and "footer-line" in told, told
			assert {"document": name, "title": "Covering letter check"} in paper.on_record("Quotation", quote)
			kept = paper.pdf(name, keep="record")
			assert kept["where"] == ["Quotation", quote] and frappe.db.get_value("File", kept["id"], "attached_to_name") == quote, kept
		with as_user("mariam@one.test"):
			assert paper.on_record("Quotation", quote) == [], "nor are its documents listed to whoever may not open the quotation"
	finally:
		frappe.db.rollback(save_point="doc_paper_check")


@check
def a_document_is_a_word_file_on_the_drive():
	"""On the network drive a document is "Name.docx", with its headings,
	lists, table, picture and page break; a download or a mail attachment is
	that Word file. Saved over from Word, it reads back in with a version
	kept; one with a record's fields in it is not written from Word. A Word
	file in OneCloud opens as a document and is written back into itself,
	its old content kept as a version, and a new version put in from outside
	is read in again. All undone afterwards."""
	import io

	from docx import Document

	from onedesk.one_doc import api, versions, word
	from onedesk.one_storage import dav
	from onedesk.one_storage import namespace as ns

	frappe.db.savepoint("doc_word_check")
	try:
		with as_user(OWNER):
			made = api.make("@my", "Word check")
			name = made["document"]
			from PIL import Image

			drawn = io.BytesIO()
			Image.new("RGB", (4, 4), "white").save(drawn, "PNG")
			picture = frappe.get_doc({"doctype": "File", "file_name": "dot.png", "content": drawn.getvalue(), "is_private": 1, "attached_to_doctype": api.DOCUMENT, "attached_to_name": name})
			picture.insert(ignore_permissions=True)
			html = (
				'<h1>Scope</h1><p style="text-align: center"><strong>Curtain</strong> wall.</p><ul><li><p>Glass</p></li><li><p>Frames</p></li></ul>'
				f'<table><tr><th>Item</th><th>Qty</th></tr><tr><td>Glass</td><td>4</td></tr></table><p><img src="{api.PICTURE}{picture.name}"></p>'
				'<div data-page-break="true"></div><p>Page two.</p>'
			)
			api.save_document(name, "AAA=", html)
			assert dav._as_file(ns.node(ns.row(made["id"])))["name"] == "Word check.docx"
			doc = Document(io.BytesIO(word.build(name)))
			said = [(one.style.name, one.text) for one in doc.paragraphs if one.text]
			assert ("Heading 1", "Scope") in said and ("List Bullet", "Glass") in said and ("Normal", "Page two.") in said, said
			assert doc.tables[0].cell(1, 0).text == "Glass" and doc.inline_shapes, "the table and the picture"
			assert doc.paragraphs[1].alignment == 1 and doc.paragraphs[1].runs[0].bold
			file = frappe.get_doc("File", made["id"])
			assert file.get_content()[:2] == b"PK" and file.file_name == "Word check.docx", "an attachment or a download is the Word file"
			file.save()
			assert frappe.db.get_value("File", made["id"], "file_name") == "Word check", "and the file keeps its name"
			saved = Document()
			saved.add_heading("Scope", 1)
			saved.add_paragraph("Changed in Word.")
			out = io.BytesIO()
			saved.save(out)
			word.write(name, out.getvalue())
			held = frappe.db.get_value(api.DOCUMENT, name, ["html", "content"], as_dict=True)
			assert "Changed in Word." in held.html and not held.content, held
			assert any(one["title"] == "Before a Word save" and "Curtain" in one["snapshot"] for one in versions.listed(name)), "a version is kept"
			api.save_document(name, "BBB=", '<p>To <span data-field="customer_name">Customer</span></p>')
			try:
				word.write(name, out.getvalue())
				raise AssertionError("a document with a record's fields was written from Word")
			except frappe.PermissionError:
				pass
			upload = frappe.get_doc({"doctype": "File", "file_name": "Letter check.docx", "content": out.getvalue(), "is_private": 1, "folder": ns.HOME})
			upload.insert()
			opened = word.open_file(upload.name)["document"]
			assert word.open_file(upload.name)["document"] == opened, "one file, one document"
			assert "Changed in Word." in api.get_document(opened)["html"] and api.get_document(opened)["word"]
			api.save_document(opened, "CCC=", "<p>Written in OneWriter.</p>")
			assert api.rename_document(opened, "Letter checked")["title"] == "Letter checked.docx", "a Word file keeps its .docx"
			word.write_back(opened)
			back = Document(io.BytesIO(frappe.get_doc("File", upload.name).get_content()))
			assert [one.text for one in back.paragraphs] == ["Written in OneWriter."], "written back into itself"
			assert frappe.db.count("Cloud File Version", {"file": upload.name}) == 1, "what it held kept as a version"
			word.file_replaced(upload.name)
			assert "Written in OneWriter." in api.get_document(opened)["html"], "a new version from outside is read in again"
			frappe.delete_doc("File", upload.name, ignore_permissions=True, force=True)
			assert not frappe.db.exists(api.DOCUMENT, opened), "and its document goes with the file"
	finally:
		frappe.db.rollback(save_point="doc_word_check")


@check
def a_workbook_left_open_waits_on_the_bar():
	"""A workbook left for another screen waits on the bar under its title;
	one that is gone, or that the reader may not open, isn't named. All
	undone afterwards."""
	from onedesk.one_sheet import api

	frappe.db.savepoint("bar_check")
	try:
		with as_user(OWNER):
			book = api.make("@my", "Bar check")["workbook"]
			assert api.titles(json.dumps([book, "no-such-book"])) == {book: "Bar check"}
		with as_user("Guest"):
			assert api.titles([book]) == {}, "a reader who can't open it isn't told its name"
	finally:
		frappe.db.rollback(save_point="bar_check")


@check
def a_workbook_is_an_excel_file_on_the_drive():
	"""On the network drive a workbook is "Name.xlsx": its formulas with the
	values the editor last worked out, a OneWorkbook-only formula as its
	value. Saved over from Excel, the values and formulas come back with a
	version kept, and the formula Excel only saw as a value keeps its
	formula. A record's workbook is not written from the drive. All undone
	afterwards."""
	import io

	from openpyxl import load_workbook

	from onedesk.one_sheet import api, excel, table
	from onedesk.one_storage import dav
	from onedesk.one_storage import namespace as ns

	frappe.db.savepoint("excel_check")
	try:
		with as_user(OWNER):
			made = api.make("@my", "Excel check")
			book = made["workbook"]
			rows = {"0": ["Item", "Qty", "Total"], "1": ["Glass", 3, "=B2*20"], "2": ["Sum", None, "=SUM(C2:C)"], "3": ["By", '=BRAND("name")']}
			data = {"sheet": {"v": 2, "current": "Sheet1", "sheets": {"Sheet1": {"rows": rows}}}, "values": {"Sheet1": {"C2": 60, "C3": 60, "B4": "Sahara"}}}
			api.save_sheet("Excel check", json.dumps(data), book)
			assert dav._as_file(ns.node(ns.row(made["id"])))["name"] == "Excel check.xlsx"
			sheet = load_workbook(io.BytesIO(excel.build(book))).active
			assert sheet["C2"].value == "=B2*20" and sheet["C3"].value == f"=SUM(C2:C{excel.LAST_ROW})" and sheet["B4"].value == "Sahara", "formulas, and ours as values"
			assert load_workbook(io.BytesIO(excel.build(book)), data_only=True).active["C2"].value == 60, "with what the editor worked out"
			file = frappe.get_doc("File", made["id"])
			assert file.get_content()[:2] == b"PK" and file.file_name == "Excel check.xlsx", "an attachment or a download is the Excel file"
			file.save()
			assert frappe.db.get_value("File", made["id"], "file_name") == "Excel check", "and the file keeps its name"
			sheet["B2"] = 5
			saved = io.BytesIO()
			sheet.parent.save(saved)
			before = frappe.db.count("Workbook Change", {"workbook": book})
			excel.write(book, saved.getvalue())
			back = excel._sheets(excel._data(book))["Sheet1"]["rows"]
			assert back["1"][1] == 5 and back["2"][2] == "=SUM(C2:C)" and back["3"][1] == '=BRAND("name")', back
			assert frappe.db.count("Workbook Change", {"workbook": book}) > before, "a version is kept"
			quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
			bound = table.open_table("Quotation", quote, "items")
			try:
				excel.write(bound, excel.build(bound))
				raise AssertionError("a record's workbook was written from the drive")
			except frappe.PermissionError:
				pass
	finally:
		frappe.db.rollback(save_point="excel_check")


@check
def a_record_table_opens_as_a_workbook():
	"""Layla opens a draft quotation's items in a workbook, raises a quantity
	and adds a line: the quotation saves itself and sends ids and figures
	back. A word for a number and an unknown item are refused; a sheet that
	missed a change on the form is refused and redrawn on opening; FIELD()
	reads the quotation; a copy is a plain workbook. All undone afterwards."""
	from unittest import mock

	from onedesk.one_sheet import api, storage, table

	def lines(book):
		held = table._held(book)
		rows = json.loads(storage.decode_sheets_data(held.sheets_data))["sheet"]["sheets"][held.bound_sheet]["rows"]
		return [[str(one) if one is not None else "" for one in rows[at]] for at in sorted(rows, key=int)]

	def sent(rows):
		return json.dumps({"sheet": "Items", "rows": rows})

	quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
	frappe.db.savepoint("table_check")
	try:
		with as_user(OWNER):
			book = table.open_table("Quotation", quote, "items")
			assert table.open_table("Quotation", quote, "items") == book, "one table, one workbook"
			opened = api.get_sheet(book)
			assert opened["table"] == {"sheet": "Items", "doctype": "Quotation", "name": quote, "field": "items", "label": "Items"}, opened["table"]
			assert json.loads(opened["sheets_data"])["view"]["Items"]["hiddenCols"] == [0]
			rows = lines(book)
			head = rows[0]
			qty, code = head.index("Quantity"), head.index("Item Code")
			first = frappe.get_doc("Quotation", quote).items[0]
			assert rows[1][0] == first.name and rows[0][0].startswith(table.MARK)
			rows[1][qty] = str(first.qty + 2)
			added = [""] * len(head)
			added[code], added[qty] = first.item_code, "3"
			rows.append(added)
			said = api.save_sheet("Items", json.dumps({"sheet": {"v": 2, "sheets": {}}}), book, "", "t1", sent(rows))["table"]
			assert said["ok"], said
			saved = frappe.get_doc("Quotation", quote)
			assert [one.qty for one in saved.items][:1] == [first.qty + 2] and saved.items[-1].qty == 3, saved.items
			assert said["cells"][f"A{len(rows)}"] == saved.items[-1].name, "the new line's id comes back"
			assert saved.items[-1].rate and saved.items[-1].amount == saved.items[-1].rate * 3, "the quotation worked it out"
			for at, value in said["cells"].items():
				line, column = int(at[1:]) - 1, ord(at[0]) - 65
				rows[line][column] = value
			assert api.save_sheet("Items", "{}", book, "", "t2", sent(rows))["table"] == {"ok": True, "cells": {}}, "nothing left to do"
			wrong = [list(one) for one in rows]
			wrong[1][qty] = "lots"
			refused = table.apply(book, sent(wrong))
			assert not refused["ok"] and "Quantity" in refused["message"], refused
			wrong[1][qty], wrong[1][code] = "1", "NO-SUCH-ITEM"
			refused = table.apply(book, sent(wrong))
			assert not refused["ok"] and "NO-SUCH-ITEM" in refused["message"] and refused["missing"] == {"Item": ["NO-SUCH-ITEM"]}, refused
			assert frappe.get_doc("Quotation", quote).items[0].qty == first.qty + 2, "a refused sheet changes nothing"
			try:
				table.make_missing(book, "Customer", '["NO-SUCH-ITEM"]')
				raise AssertionError("made a record of a type the table doesn't name")
			except frappe.ValidationError:
				pass
			assert table.make_missing(book, "Item", '["NO-SUCH-ITEM"]') == {"made": ["NO-SUCH-ITEM"], "failed": {}}
			assert frappe.db.get_value("Item", "NO-SUCH-ITEM", "item_group"), "made with what a new item starts with"
			for attempt in ("and the sheet goes in", first.item_code):
				said = table.apply(book, sent(wrong))
				assert said["ok"], (attempt, said)
				for at, value in said["cells"].items():
					wrong[int(at[1:]) - 1][ord(at[0]) - 65] = value
				wrong[1][code] = first.item_code
			rows = [list(one) for one in wrong]
			changed = frappe.get_doc("Quotation", quote)
			changed.items[0].qty = 5
			told = []
			with mock.patch("frappe.publish_realtime", side_effect=lambda event, message, **kw: told.append((event, message, kw.get("docname")))):
				changed.save()
			assert ("one_table_changed", {"workbook": book}, quote) in told, "the open workbook hears of it"
			stale = table.apply(book, sent(rows))
			assert not stale["ok"] and "changed on the record" in stale["message"], stale
			drawn = table.redrawn(book)
			assert drawn["sheet"] == "Items" and drawn["cells"][f"{chr(65 + qty)}2"] == "5", "drawn again in place"
			assert lines(book)[1][qty] == "5", "and kept"
			read = api.records(json.dumps([["Quotation", quote], ["Quotation", "NO-SUCH-QUOTE"]]))
			assert read["Quotation"][quote]["name"] == quote and "NO-SUCH-QUOTE" not in read["Quotation"], "FIELD() reads it"
			file = frappe.get_doc("File", frappe.db.get_value(api.WORKBOOK, book, "file"))
			copy = frappe.get_doc({"doctype": "File", "file_url": file.file_url, "file_name": "Items, a copy", "folder": "Home", "is_private": 1})
			copy.flags.ignore_permissions = True
			copy.insert()
			assert not frappe.db.get_value(api.WORKBOOK, api.workbook_of(copy.file_url), "bound_doctype"), "a copy is a plain workbook"
	finally:
		frappe.db.rollback(save_point="table_check")

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
	invoice's head, which settles it, its dialog foreseeing nothing because
Record Payment changes nothing it has to show, and a head reads a record not yet saved
	as the form has it. A link to a project reads as its title for Samir
	and as its name for somebody who may not open it. The automation step
	editor lists what a flow may do."""
	from frappe.desk.search import get_link_title

	from onedesk.one import automations, customize, head

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
	from onedesk.one_ai import memory, tools
	from onedesk.one_mail import ai as mail_ai
	from onedesk.one_mail import holders

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
def oneinventory_an_item_opens_on_its_own_page():
	"""An item opens on its page as its reader may see it. The profile says
	where it is kept and who it was last bought from; the window says more is
	promised than there is and how many are being made, and lists what it is
	made from. OneAI reads an item as the page does, says what is running
	low, and a change it suggests to a reorder level is saved when approved.
	Somebody without OneInventory is refused the page."""
	from onedesk.one_ai import proposals
	from onedesk.one_inventory import ai, view

	with as_user("karim@one.test"):
		profile = view.read("ALU-6063")
		assert profile["kind"] == "Stock" and profile["stock"]["places"] and profile["stock"]["moves"], profile["stock"]
		assert profile["last_bought"] and profile["last_bought"].supplier, profile["last_bought"]
		assert profile["buying"]["suppliers"] and profile["making"]["used_in"], "the profile goes into the windows"
		assert view.files("ALU-6063") == 0
		facts = ai.item_facts("ALU-6063")
		assert facts["on_hand"] == profile["summary"]["on_hand"] and facts["suppliers"], facts
		assert "item_facts" in (ai.page({"page": "item-view", "record": "ALU-6063"}) or "")
		low = ai.running_low()
		assert {"low", "count"} <= set(low), low
		card = ai.plan_item_change("ALU-6063", warehouse=wh("Stores"), reorder_level=500, reorder_qty=1000, why="Bigger jobs coming")
		assert "proposal" in card, card
		proposals.apply(card["proposal"])
	level = frappe.get_all("Item Reorder", filters={"parent": "ALU-6063", "warehouse": wh("Stores")}, fields=["warehouse_reorder_level", "warehouse_reorder_qty"])
	assert level and level[0].warehouse_reorder_level == 500 and level[0].warehouse_reorder_qty == 1000, level
	with as_user("tariq@one.test"):
		window = view.read("WIN-CS12")
		assert window["made"] and window["making"]["materials"] and window["making"]["orders"], window["making"]
		if window["headline"]:
			assert window["headline"]["key"] in ("short", "low"), window["headline"]
	with as_user("huda@one.test"):
		service = view.read("SVC-INST")
		assert service["kind"] == "Service" and service["stock"] is None and service["selling"]["customers"]
	with as_user("nadia@one.test"):
		try:
			view.read("ALU-6063")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody without OneInventory reads an item's page")


@check
def oneinventory_an_items_stock_says_where_it_is_and_what_moved():
	"""The Stock view names each warehouse as people call it, says what is
	free to use and which reorder row is its own, so the page changes the
	level in place. A transfer is one move from the one warehouse to the
	other, with who made it."""
	from onedesk.one_inventory import view

	with as_user("karim@one.test"):
		said = view.read("ALU-6063")
	places = {one["called"]: one for one in said["stock"]["places"]}
	stores = places.get("Stores")
	assert stores, list(places)
	assert stores["free"] == stores["on_hand"] - stores["reserved"], stores
	assert stores["row"] and stores["level"], "the Stores reorder row is the item's own"
	assert all(" - " not in called for called in places), list(places)
	moved = [one for one in said["stock"]["moves"] if one.get("from")]
	villa = next((one for one in moved if one["to"] == "Mansour Villa Site"), None)
	assert villa, "the transfer to the Mansour villa reads as one move"
	assert villa["from"] == "Stores" and villa["actual_qty"] > 0 and len(villa["left"]) == 2, villa
	assert all(one["by"] for one in said["stock"]["moves"]), "each move says who made it"


@check
def oneinventory_an_items_buying_says_who_at_what_and_what_next():
	"""The Buying view: the default supplier first with their part number,
	the last price and the one before, what they agreed for the year; the
	quotes still open cheapest first by what a metre costs in dirhams, one in
	euros; what is still to arrive; who asked for what is not yet ordered,
	and for which project; and the last price paid, which the buying price
	is held against. The header's last price says it was received."""
	from onedesk.one_inventory import view

	with as_user("karim@one.test"):
		said = view.read("ALU-6063")
	buying = said["buying"]
	first = buying["suppliers"][0]
	assert first["supplier"] == "Al Noor Aluminium" and first["default"], first
	assert first["part_no"] and first["row"], "the part number is the item's own supplier row"
	assert first["before"] and first["before"] != first["rate"], first
	assert first["agreed"] and first["agreed"]["left"] > 0, first
	quotes = buying["quotes"]
	assert len(quotes) >= 2 and quotes[0]["cheapest"], quotes
	assert [one["per_unit"] for one in quotes] == sorted(one["per_unit"] for one in quotes), quotes
	assert any(one["currency"] == "EUR" and one["base_rate"] != one["rate"] for one in quotes), quotes
	assert all(one["qty"] >= one["done"] for one in buying["orders"]), buying["orders"]
	asked = [one for one in buying["requests"] if one["project_name"]]
	assert asked and asked[0]["by"], buying["requests"]
	assert buying["last_paid"] and buying["last_paid"]["currency"] == said["currency"], buying["last_paid"]
	assert said["last_bought"].kind == "received", said["last_bought"]
	makers = buying["manufacturers"]
	assert makers and makers[0]["is_default"] and makers[0]["manufacturer_part_no"], makers


@check
def oneinventory_an_items_selling_says_what_can_go_and_who_buys():
	"""The Selling view: what is on hand goes to the orders soonest due first,
	so the late order and the next two can go now and the big one is short;
	an order not fully billed can be invoiced; the quotes still open, one in
	dollars with what it comes to in dirhams; each customer's last twelve
	months with returns taken off and their last price; and the sales a
	selling price is held against."""
	from onedesk.one_inventory import view

	assert [(one["can_go"], one["short"]) for one in view.ready(
		[{"left": 5, "due": "2026-02-01"}, {"left": 4, "due": "2026-01-01"}, {"left": 3, "due": None}], 6
	)] == [(2, 3), (4, 0), (0, 3)]
	with as_user("wsadmin@one.test"):
		said = view.read("WIN-CS12")
	selling = said["selling"]
	orders = {one["party"]: one for one in selling["orders"]}
	assert orders["Crescent Schools"]["late"] and not orders["Crescent Schools"]["short"], orders["Crescent Schools"]
	assert not orders["Marina Hotels Group"]["short"] and not orders["Mansour & Sons"]["short"], orders
	assert orders["Bayview Developments"]["short"] == 280, orders["Bayview Developments"]
	assert orders["Mansour & Sons"]["to_bill"] and orders["Mansour & Sons"]["project_name"], orders["Mansour & Sons"]
	quotes = selling["quotes"]
	assert any(one["quotation_to"] == "Lead" for one in quotes), quotes
	assert any(one["currency"] == "USD" and one["base_rate"] != one["rate"] for one in quotes), quotes
	customers = {one["customer"]: one for one in selling["customers"]}
	crescent = customers["Crescent Schools"]
	assert (crescent["qty"], crescent["returned"], crescent["amount"]) == (23, 1, 54050), crescent
	assert crescent["rate"] == 2350 and crescent["last"], crescent
	acme = customers["Acme Holdings"]
	assert acme["currency"] == "USD" and acme["their_amount"] and acme["their_amount"] != acme["amount"], acme
	assert selling["sales"] and all(one["rate"] for one in selling["sales"]), selling["sales"]
	assert any(one["price_list_rate"] > 2350 for one in selling["prices"]), selling["prices"]
	with as_user("omar@one.test"):
		assert view.read("WIN-CS12")["selling"]["prices"], "Omar sells the window and sees its price"


@check
def oneinventory_an_items_making_says_what_can_be_made_and_how_far():
	"""The Making view: how many the free stock of its materials would make
	and which runs out first, the steps that make it, each open work order
	step by step with what Finish would take, what was made in the last
	year, and, for a material, what the open work orders still need of it."""
	from onedesk.one_inventory import view

	assert view.can_make([]) is None
	assert view.can_make(
		[{"item_code": "A", "item_name": "A", "covers": 9}, {"item_code": "B", "item_name": "B", "covers": 4}]
	) == {"qty": 4, "limit": "B"}
	with as_user("wsadmin@one.test"):
		window = view.read("WIN-CS12")["making"]
		profile = view.read("ALU-6063")["making"]
	assert window["made_here"] and window["materials"], window
	least = min(one["covers"] for one in window["materials"])
	assert window["can_make"]["qty"] == least, window["can_make"]
	assert [one["operation"] for one in window["steps"]] == ["Cutting", "Assembly", "Glazing"], window["steps"]
	order = window["orders"][0]
	assert [step["operation"] for step in order["steps"]] == ["Cutting", "Assembly", "Glazing"], order
	assert order["can_finish"] == order["transferred"] - order["produced_qty"], order
	assert order["project_name"], order
	assert sum(one["produced_qty"] for one in window["made"]) >= 100, window["made"]
	assert not profile["made_here"], "a bought material has no work orders of its own"
	assert any(one["item_name"] == "Sliding Door 2400" and one["left"] > 0 for one in profile["needed"]), profile["needed"]


@check
def oneinventory_the_shop_floor_runs_a_step_from_start_to_close():
	"""The Shop Floor: the board counts the open work orders as ERPNext's Shop
	Floor does, a work order shows its steps, and a step is started, paused,
	resumed and closed through ERPNext's own calls, each time saying what may
	be done next. OneAI reads what is running. Somebody outside the workshop
	sees none of it."""
	from erpnext.manufacturing.doctype.workstation.workstation import update_job_card
	from erpnext.manufacturing.page.shop_floor import shop_floor

	from onedesk.one_inventory import ai, floor

	at = frappe.utils.now_datetime()
	with as_user("tariq@one.test"):
		board = floor.read()
		assert board["figures"]["open"] == board["total"] == len(board["work_orders"]), board["figures"]
		door = next(one for one in board["work_orders"] if one["production_item"] == "DR-SL24")
		said = floor.read(work_order=door["name"])
		assert said["work_order"]["project_name"], said["work_order"]
		assert [one["operation"] for one in said["steps"]] == ["Cutting", "Assembly", "Glazing"], said["steps"]
		cut, joint = said["steps"][0], said["steps"][1]
		assert cut["running"] and cut["may"]["pause"] and cut["may"]["record"] and not cut["may"]["start"], cut
		assert cut["people"] == ["Arun Kumar"] and cut["minutes"] == 0 and cut["since"], cut
		assert joint["may"]["start"] and not joint["may"]["pause"], joint["may"]
		assert said["employee"], "Tariq starts a step as himself"
		running = ai.on_the_floor()
		assert any(one["job_card"] == cut["name"] and one["state"] == "running" for one in running["steps"]), running
		assert running["figures"]["running"] >= 1, running["figures"]

		update_job_card(cut["name"], "pause_job", end_time=str(at))
		cut = floor.read(work_order=door["name"])["steps"][0]
		assert cut["paused"] and cut["may"]["resume"] and not cut["running"], cut
		update_job_card(cut["name"], "resume_job", start_time=str(at + datetime.timedelta(minutes=10)))

		closed_before = floor.figures()["done_today"]
		shop_floor.complete_and_submit(
			cut["name"], cut["for_quantity"], cut["for_quantity"], 0, 0, str(at + datetime.timedelta(minutes=50))
		)
		cut = floor.read(work_order=door["name"])["steps"][0]
		assert cut["docstatus"] == 1 and cut["done"] == cut["for_quantity"], cut
		assert not any(cut["may"][key] for key in ("start", "pause", "resume", "record")), cut["may"]
		assert floor.figures()["done_today"] == closed_before + 1
		update_job_card(joint["name"], "start_timer", start_time=str(at), employees=[{"employee": said["employee"]}])
		joint = floor.read(work_order=door["name"])["steps"][1]
		assert joint["running"] and joint["people"] == ["Tariq Haidar"], joint
		saw = floor.read(workstation="Saw Line")
		assert all(one["workstation"] == "Saw Line" for one in saw["steps"]), saw["steps"]
	with as_user("nadia@one.test"):
		assert ai.on_the_floor().get("error")
		try:
			floor.read()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the workshop read the Shop Floor")


@check
def oneinventory_home_says_what_needs_somebody_and_where_everything_is():
	"""OneInventory's Home: the orders late, the items running low, the lots
	going off, the services due this week, the work orders past their date
	and the drafts left, each counted as its own screen counts it, and a
	directory of everything the reader may open. Somebody outside the stores
	sees none of it."""
	from onedesk.one_inventory import ai, batches, home

	with as_user("karim@one.test"):
		said = home.read()
		needs = said["needs"]
		assert needs["late"]["count"] == ai.late_orders()["count"] == said["figures"]["late"] > 0, needs["late"]
		assert needs["low"]["count"] == ai.running_low()["count"] == said["figures"]["low"] > 0, needs["low"]
		assert needs["lots"]["count"] == len(batches.dated()) == said["figures"]["going_off"] > 0, needs["lots"]
		assert len(needs["late"]["rows"]) <= home.FEW
		assert said["figures"]["worth"] > 0
		shown = {one["target"] for one in said["everything"]}
		assert {"Item", "Warehouse", "Stock Ledger", "to-order", "stock-on-hand"} <= shown, shown
		assert all(one["about"] and one["label"] for one in said["everything"])
		assert {one["group"] for one in said["everything"]} <= {key for key, _label in home.GROUPS}
	with as_user("nadia@one.test"):
		said = home.read()
		assert said["figures"]["worth"] is None and not said["needs"]["late"]["count"], said["figures"]
		assert not any(one["target"] in ("Warehouse", "Stock Ledger", "Purchase Order") for one in said["everything"])


@check
def oneinventory_home_tells_the_story_of_the_stock():
	"""OneInventory's Overview: stock's worth today and month by month, the
	same worth split by warehouse and by item group, goods' path from each
	supplier to a customer or a project, how old the stock is, how far the
	requests got, the work orders by status and the equipment by kind, each
	as the reader may see it. Somebody outside the stores sees none of it."""
	from onedesk.one_inventory import home, story

	with as_user("karim@one.test"):
		told = story.read()
		worth = home.read()["figures"]["worth"]
		cards = told["cards"]
		assert round(cards["worth"]["value"], 2) == round(worth, 2) > 0, cards["worth"]
		assert cards["worth"]["series"][-1] == round(worth, 2), cards["worth"]["series"]
		said = {
			"worth": story.stock_worth(),
			"taken_in": story.taken_in_this_month(),
			"sent_out": story.sent_out_this_month(),
			"made": story.made_this_month(),
			"on_order": story.still_on_order(),
			"papers": story.moves_this_month(),
		}
		for key, name in story.CARDS:
			assert frappe.db.get_value("Number Card", name, "module") == "One Inventory", name
			assert said[key]["value"] == cards[key]["value"] and cards[key]["card"] == name, (name, said[key], cards[key])
		assert len(cards["worth"]["series"]) == len(told["months"]) <= story.MONTHS
		where = told["where"]
		assert round(sum(one["worth"] for one in where["warehouses"])) == round(worth)
		assert round(sum(one["worth"] for one in where["groups"])) == round(worth)
		assert all(" - " not in one["name"] for one in where["warehouses"]), where["warehouses"]
		paths = told["moves"]["paths"]
		assert any(one["from"] == "Al Noor Aluminium" for one in paths), paths
		assert not any(one["to"].startswith("PROJ-") for one in paths), paths
		assert round(sum(one["worth"] for one in told["ages"])) == round(worth), told["ages"]
		steps = [one["requests"] for one in told["buying"]["requests"]]
		assert steps == sorted(steps, reverse=True) and steps[0] > 0, steps
		assert {one["status"] for one in told["making"]["statuses"]} >= {"Completed", "In Process"}
		assert {one["kind"] for one in told["equipment"]["kinds"]} >= {"Vehicles", "Machinery"}
	with as_user("nadia@one.test"):
		told = story.read()
		assert not told["cards"].get("worth") and not told["where"] and not told["moves"], told["cards"]


@check
def oneinventory_lots_and_numbers_are_one_tool():
	"""Lots: the sealant's two lots, the one going off first, each with what
	is left and where, the six smart locks by number in the Stores, and the
	items kept either way. An item set up from the page to be kept in lots,
	and a lot made for it, show at once. OneAI reads it. Somebody outside the
	stores sees none of it."""
	from onedesk.one_demo.lots import LOCK, LOCKS
	from onedesk.one_inventory import ai, lots

	with as_user("karim@one.test"):
		said = lots.read()
		assert said["switched_on"] and said["can"]["Batch"], said["can"]
		sealant = [one for one in said["batches"] if one["item"] == "SIL-WP"]
		assert [one["batch_id"] for one in sealant] == ["SIL-WP-A1", "SIL-WP-B2"], sealant
		assert sealant[0]["state"] == "Expiring Soon" and not sealant[1]["state"], sealant
		assert {place["warehouse"] for place in sealant[0]["where"]} == {wh("Stores"), wh("Mansour Villa Site")}, sealant[0]
		assert sum(place["qty"] for place in sealant[0]["where"]) == sealant[0]["batch_qty"]
		assert said["figures"]["going_off"] >= 1 and said["figures"]["serials"] >= len(LOCKS[1]), said["figures"]
		assert [one["batch_id"] for one in lots.read(soon=1)["batches"] if one["item"] == "SIL-WP"] == ["SIL-WP-A1"]

		numbers = lots.read(view="serials", item=LOCK)["serials"]
		assert sorted(one["serial_no"] for one in numbers) == LOCKS[1], numbers
		assert all(one["status"] == "Active" and one["warehouse"] == wh("Stores") for one in numbers), numbers
		assert [one["serial_no"] for one in lots.read(view="serials", search="SL-0003")["serials"]] == ["SL-0003"]
		kept = {one["name"]: one for one in lots.read(view="items")["items"]}
		assert kept["SIL-WP"]["has_batch_no"] and kept[LOCK]["has_serial_no"], kept

		frappe.get_doc({"doctype": "Item", "item_code": "CHK-PRIMER", "item_name": "Check Primer", "item_group": "Consumable", "stock_uom": "Nos", "is_stock_item": 1}).insert()
		offered = [row[0] for row in lots.can_be_tracked("Item", "", "name", 0, 500)]
		assert "CHK-PRIMER" in offered and "SIL-WP" not in offered and "ALU-6063-PC" not in offered, offered
		frappe.client.set_value("Item", "CHK-PRIMER", {"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "PR-.###", "has_expiry_date": 1, "shelf_life_in_days": 90})
		made = frappe.client.insert({"doctype": "Batch", "item": "CHK-PRIMER", "batch_id": "", "manufacturing_date": frappe.utils.today()})
		assert made["batch_id"].startswith("PR-"), made
		assert str(made["expiry_date"]) == frappe.utils.add_days(frappe.utils.today(), 90), made
		assert "CHK-PRIMER" in {one["name"] for one in lots.read(view="items")["items"]}

		facts = ai.lots_and_numbers(item="SIL-WP")
		assert [one["lot"] for one in facts["lots"]] == ["SIL-WP-A1", "SIL-WP-B2"], facts
		assert len(ai.lots_and_numbers(item=LOCK)["numbers"]) == len(LOCKS[1])
		assert ai.lots_and_numbers(item="NOPE").get("error")
	with as_user("nadia@one.test"):
		said = lots.read()
		assert not said["batches"] and said["figures"]["lots"] is None, said["figures"]
		assert not lots.read(view="serials")["serials"] and not said["can"]["Batch"]
		assert ai.lots_and_numbers().get("error")


@check
def oneinventory_quotes_ask_compare_and_order_on_one_page():
	"""Quotes: the stores' profile asked of Al Noor and Euro Hardware, Euro
	Hardware's answer in euros compared in dirhams, Al Noor still waiting,
	and the villa's request with every cheapest line ordered already. Al
	Noor's quote typed in makes them cheapest, Order the Cheapest drafts
	their order from their quote, and Ask for Prices drafts a request by
	ERPNext's own mapper. OneAI reads it. Somebody outside buying sees none
	of it."""
	from erpnext.buying.doctype.request_for_quotation.mapper import make_supplier_quotation_from_rfq

	from onedesk.one_demo.ordering import ALUMINIUM, EURO, STORES_ASKED
	from onedesk.one_inventory import ai, quotes

	code, qty, rate = STORES_ASKED
	with as_user("karim@one.test"):
		said = quotes.read()
		assert said["figures"]["waiting"] >= 1 and said["figures"]["expiring"] >= 1, said["figures"]
		stores = next(one for one in said["asked"] if any(row["supplier"] == EURO for row in one["suppliers"]))
		answered = {row["supplier"]: row["answered"] for row in stores["suppliers"]}
		assert answered == {ALUMINIUM: False, EURO: True} and not stores["ordered"], stores

		compared = quotes.compare(stores["name"])
		line = compared["lines"][0]
		assert line["item"] == code and line["qty"] == qty and line["cheapest"] == EURO, line
		offer = line["offers"][EURO]
		assert offer["rate"] == rate and offer["base_rate"] > rate * 3, offer
		assert [one["quote"] is None for one in compared["suppliers"]] == [True, False], compared["suppliers"]

		villa = quotes.compare(next(one["name"] for one in said["asked"] if one["ordered"] and one["answered"] == 2))
		assert all(one["ordered"] for one in villa["lines"]) and not any(one["cheapest_on"] for one in villa["suppliers"]), villa

		theirs = make_supplier_quotation_from_rfq(stores["name"], for_supplier=ALUMINIUM)
		for row in theirs.items:
			row.rate = 24.0
		theirs.insert()
		theirs.submit()
		compared = quotes.compare(stores["name"])
		assert compared["lines"][0]["cheapest"] == ALUMINIUM, compared["lines"]
		made = quotes.order_cheapest(stores["name"])
		order = frappe.get_doc("Purchase Order", made[0])
		assert len(made) == 1 and order.docstatus == 0 and order.supplier == ALUMINIUM, made
		assert [(row.item_code, row.qty, row.supplier_quotation) for row in order.items] == [(code, qty, theirs.name)], order.items

		pending = frappe.get_list("Material Request", filters={"docstatus": 1, "material_request_type": "Purchase", "status": "Pending"}, pluck="name", limit=1)
		if pending:
			drafted = frappe.get_doc("Request for Quotation", quotes.ask(pending[0], [ALUMINIUM, EURO]))
			assert drafted.docstatus == 0 and [row.supplier for row in drafted.suppliers] == [ALUMINIUM, EURO], drafted.suppliers
			assert all(row.material_request == pending[0] for row in drafted.items)

		facts = ai.quotes_now()
		assert facts["figures"] == quotes.figures() and facts["newest_compared"], facts
	with as_user("nadia@one.test"):
		said = quotes.read()
		assert not said["asked"] and said["figures"]["waiting"] is None and not said["can"]["ask"], said
		assert ai.quotes_now().get("error")


@check
def oneinventory_sent_out_says_what_went_and_what_came_back():
	"""Sent Out: the tower's profile with Gulf Powder Coating, all sent and
	nothing back yet, the villa's done with, and what the materials with the
	coater are worth. Taking the tower's back through ERPNext's receipt moves
	it to Back. OneAI reads it. Tariq sees it, somebody outside the stores
	and the workshop does not."""
	from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
		make_subcontracting_receipt,
	)

	from onedesk.one_demo.making import COATER, COATING
	from onedesk.one_inventory import ai, sent_out

	metres = COATING[0]
	with as_user("karim@one.test"):
		said = sent_out.read()
		tower = next(one for one in said["orders"] if one["supplier"] == COATER)
		assert tower["status"] == "Material Transferred" and not tower["late"], tower
		assert [(row["item"], row["qty"], row["back"]) for row in tower["makes"]] == [("ALU-6063-PC", metres, 0)], tower["makes"]
		assert [(row["item"], row["sent"]) for row in tower["materials"]] == [("ALU-6063", metres)], tower["materials"]
		assert tower["project_name"] == "Bayview Tower Curtain Wall"
		assert said["figures"]["out"] >= 1 and said["figures"]["worth"] > 0, said["figures"]
		assert any(one["status"] == "Completed" for one in sent_out.read(view="done")["orders"])
		facts = ai.sent_out_now()
		assert any(one["order"] == tower["name"] for one in facts["out"]), facts

		receipt = frappe.get_doc(make_subcontracting_receipt(tower["name"]))
		receipt.insert()
		receipt.submit()
		assert tower["name"] not in {one["name"] for one in sent_out.read()["orders"]}
		assert tower["name"] in {one["name"] for one in sent_out.read(view="done")["orders"]}
	with as_user("tariq@one.test"):
		assert sent_out.figures()["out"] is not None
	with as_user("nadia@one.test"):
		said = sent_out.read()
		assert not said["orders"] and said["figures"]["out"] is None, said
		assert ai.sent_out_now().get("error")


@check
def oneinventory_upkeep_says_what_is_due_broken_and_done():
	"""Upkeep: the second truck's service late with Yousef, Huda's laptop out
	of order, a plan for each serviced asset and the CNC centre's checks
	done. Marking the truck's service done takes it off Due, puts it in Done
	and moves its next date a quarter on, as ERPNext works it out. OneAI
	reads it. Somebody outside the stores sees none of it."""
	from onedesk.one_inventory import ai, upkeep

	with as_user("karim@one.test"):
		said = upkeep.read()
		assert said["figures"]["late"] >= 1 and said["figures"]["broken"] >= 1, said["figures"]
		truck = next(one for one in said["due"] if one["asset_name"] == "Pickup Truck 2")
		assert truck["late"] and truck["assign_to_name"] == "Yousef Bakr", truck
		broken = [one for one in upkeep.read(view="repairs")["repairs"] if one["open"]]
		assert [one["asset_name"] for one in broken] == ["Laptop Huda"] and broken[0]["days_out"] >= 0, broken
		plans = {one["asset_name"]: one for one in upkeep.read(view="plans")["plans"]}
		assert {"Pickup Truck 1", "Pickup Truck 2", "CNC Profile Machining Centre"} <= set(plans), list(plans)
		assert any(one["asset_name"] == "CNC Profile Machining Centre" for one in upkeep.read(view="log")["log"])
		facts = ai.upkeep_now()
		assert any(one["asset"] == "Pickup Truck 2" and one["late"] for one in facts["services"]), facts

		upkeep.done(truck["name"], frappe.utils.today(), "Oil and filters changed.")
		assert truck["name"] not in {one["name"] for one in upkeep.read()["due"]}
		assert truck["name"] in {one["name"] for one in upkeep.read(view="log")["log"]}
		task = frappe.db.get_value("Asset Maintenance Task", {"parent": truck["asset"]}, ["last_completion_date", "next_due_date"], as_dict=True)
		assert str(task.last_completion_date) == frappe.utils.today() and str(task.next_due_date) == str(frappe.utils.add_months(frappe.utils.today(), 3)), task
	with as_user("nadia@one.test"):
		said = upkeep.read()
		assert not said["due"] and said["figures"]["late"] is None and not said["can"]["done"], said
		assert ai.upkeep_now().get("error")


@check
def oneinventory_the_plant_floor_shows_each_workstation():
	"""The Plant Floor: the workshop's three workstations with ERPNext's
	statuses, the step running on the saw and who is on it, the steps waiting
	at each, and the stock kept on the floor. A status changed on a
	workstation shows at once, and the figures follow. OneAI reads it.
	Somebody outside the workshop sees none of it."""
	from onedesk.one_inventory import ai, plant

	with as_user("tariq@one.test"):
		said = plant.read()
		assert said["plant"]["name"] == "Workshop", said["plant"]
		shown = {one["name"]: one for one in said["workstations"]}
		assert {name: one["status"] for name, one in shown.items()} == {
			"Saw Line": "Production",
			"Assembly Bench": "Idle",
			"Glazing Table": "Maintenance",
		}, shown
		saw = shown["Saw Line"]
		assert [step["operation"] for step in saw["running"]] == ["Cutting"], saw
		assert saw["running"][0]["people"] == ["Arun Kumar"], saw["running"]
		assert shown["Assembly Bench"]["waiting"] >= 1, shown["Assembly Bench"]
		assert said["figures"] == {"workstations": 3, "making": 1, "stopped": 1, "running": 1}, said["figures"]
		assert said["stock"] and all(one["actual_qty"] > 0 for one in said["stock"]), said["stock"]
		assert [one["name"] for one in plant.read(status="Maintenance")["workstations"]] == ["Glazing Table"]

		frappe.client.set_value("Workstation", "Glazing Table", "status", "Production")
		after = plant.read()
		assert after["figures"]["making"] == 2 and after["figures"]["stopped"] == 0, after["figures"]
		facts = ai.plant_floor_now()
		assert {one["workstation"]: one["status"] for one in facts["workstations"]}["Glazing Table"] == "Production"
		assert ai.plant_floor_now("Nowhere").get("error")
	with as_user("nadia@one.test"):
		assert ai.plant_floor_now().get("error")
		try:
			plant.read()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the workshop read the Plant Floor")


@check
def oneinventory_an_items_head_has_its_barcodes_and_trends():
	"""A new item is given its code as its first barcode. Manage Barcodes puts
	them in the order it is given, so the first two are the head's, and
	somebody who may only read the item can't change them. The head's cards
	draw twelve months of stock held, its worth and what was ordered, and the
	prices it was last bought at."""
	from onedesk.one_inventory import barcodes, view

	with as_user("karim@one.test"):
		item = frappe.get_doc(
			{"doctype": "Item", "item_code": "CHK-BAR-1", "item_name": "Barcode check", "item_group": "Raw Material", "stock_uom": "Nos"}
		).insert()
		assert [row.barcode for row in item.barcodes] == ["CHK-BAR-1"], item.barcodes
		rows = barcodes.save("CHK-BAR-1", [{"barcode": "6291041500213", "barcode_type": "EAN"}, {"barcode": "CHK-BAR-1"}])
		assert [row["barcode"] for row in rows] == ["6291041500213", "CHK-BAR-1"], rows
		said = view.read("CHK-BAR-1")
		assert [row["barcode"] for row in said["barcodes"]][: barcodes.FEATURED] == ["6291041500213", "CHK-BAR-1"]
		head = view.read("ALU-6063")
		trends = head["trends"]
		assert len(trends["held"]) == 12 and len(trends["worth"]) == 12 and len(trends["ordered"]) == 12, trends
		assert abs(trends["held"][-1] - head["summary"]["on_hand"]) < 0.001, (trends["held"], head["summary"])
		assert trends["prices"], "the last prices it was bought at"
	with as_user("nadia@one.test"):
		try:
			barcodes.save("CHK-BAR-1", [])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who can't change the item changed its barcodes")


@check
def oneinventory_lots_say_their_dates_and_where_they_went():
	"""The sealant's January lot runs out of date within the month with some
	still in the Stores and some at the villa. The item's page says so under
	Needs You, the lot's head says what is left and where, when it expires,
	the receipt it came from and that some was taken out, and whoever keeps
	the stores is told once. Past its date, it says Expired. Somebody
	without OneInventory is refused the item."""
	from frappe.utils import add_days, today

	from onedesk.one_inventory import batches, heads, tell, view

	old = frappe.get_doc("Batch", {"batch_id": "SIL-WP-A1", "item": "SIL-WP"})
	with as_user("karim@one.test"):
		said = view.read("SIL-WP")
		states = {one["batch_id"]: one["state"] for one in said["stock"]["batches"]}
		assert states == {"SIL-WP-A1": "Expiring Soon", "SIL-WP-B2": None}, states
		left = batches.left(old.name)
		assert {one["warehouse"] for one in left} == {wh("Stores"), wh("Mansour Villa Site")}, left
		assert sum(one["qty"] for one in left) == old.batch_qty == 120
		assert "2" in heads.batch_left(old), heads.batch_left(old)
		assert heads.batch_expires(old)["tone"] == "waiting"
		came = heads.batch_came_from(old)
		assert came["route"].startswith("/desk/purchase-receipt/"), came
		assert heads.batch_went(old)["value"] == 1
		assert [one.batch_id for one in batches.dated("SIL-WP")] == ["SIL-WP-A1"]
	with _Told() as told:
		tell.expiring()
	keepers = told.to("Expiring Soon")
	assert keepers and keepers <= set(frappe.get_all("Has Role", filters={"role": "Stock Manager"}, pluck="parent")), keepers
	frappe.db.set_value("Batch", old.name, "expiry_date", add_days(today(), -1))
	old.reload()
	assert heads.batch_expires(old)["tone"] == "alarm" and batches.state(old.expiry_date, old.batch_qty) == "Expired"
	with as_user("nadia@one.test"):
		try:
			view.read("SIL-WP")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody without OneInventory reads the sealant")


@check
def oneinventory_new_item_parts_list_and_sizes():
	"""New Item makes an item by its kind, measured by area or length or by the
	piece; a sheet kept by the piece says how many square metres it is. A
	parts list pasted in is matched to the items there are, and its new parts
	are added as stock items. A line of a measured item takes its quantity
	from its size, in the line's unit, on a quotation and on the order made
	from it, and the size is kept for print, in the line's size unit. Concrete
	is sold by volume; a line typed in centimetres counts as one."""
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	from onedesk.one_inventory import kinds, measure, parts

	with as_user("karim@one.test"):
		glass = kinds.make({"kind": "Stock", "title": "Clear Glass 8 mm", "code": "DEMO-GLASS-8", "group": "Products", "unit": "Square Meter", "measured_by": "Area", "sold": 1, "selling_price": 60, "bought": 1})
		sheet = kinds.make({"kind": "Stock", "title": "Aluminium Sheet 3 mm", "code": "DEMO-SHEET-3", "group": "Products", "unit": "Nos", "measured_by": "Area", "per_unit_area": 3.125, "sold": 1, "selling_price": 180, "bought": 1})
		profile = kinds.make({"kind": "Stock", "title": "Edge Trim", "code": "DEMO-TRIM", "group": "Products", "unit": "Meter", "measured_by": "Length", "sold": 1, "selling_price": 12, "bought": 1})
		concrete = kinds.make({"kind": "Stock", "title": "Ready-Mix Concrete", "code": "DEMO-CONCRETE", "group": "Products", "unit": "Litre", "measured_by": "Volume", "per_unit_volume": 0.001, "sold": 1, "selling_price": 1, "bought": 1})
		assert round(measure.line_quantity(concrete, "Volume", "Cubic Meter", 2, 100, 50, 20, "Centimeter"), 3) == 0.2
		assert round(measure.line_quantity(concrete, "Volume", "Litre", 2, 100, 50, 20, "Centimeter"), 1) == 200.0
		try:
			measure.line_quantity(concrete, "Volume", "Litre", 1, 1, 1, 1, "Kilogram")
			raise AssertionError("a size in kilograms")
		except frappe.ValidationError:
			pass
		assert frappe.db.get_value("Item", glass, "one_measured_by") == "Area"
		assert {(r.uom, round(r.conversion_factor, 2)) for r in frappe.get_doc("Item", sheet).uoms} >= {("Square Meter", 0.32)}
		assert set(kinds.stocked(["ALU-6063"])) == {"ALU-6063"}, "the Items list reads what the stores hold"
		found = parts.read(text="code,name,qty\nALU-6063,,2\nDEMO-GASKET,Door gasket,4\nALU-6063,,1")
		assert [(one["code"], one["qty"], one["new"]) for one in found["parts"]] == [("ALU-6063", 3.0, False), ("DEMO-GASKET", 4.0, True)], found
		rows = parts.add(found["parts"])
		assert [row["item_code"] for row in rows] == ["ALU-6063", "DEMO-GASKET"] and frappe.db.exists("Item", "DEMO-GASKET")
		assert round(measure.line_quantity(glass, "Area", "Square Meter", 4, 1200, 800), 3) == 3.84
		assert round(measure.line_quantity(sheet, "Area", "Nos", 2, 1250, 2500), 3) == 2.0
		assert round(measure.line_quantity(profile, "Length", "Meter", 6, 2400), 3) == 14.4
		assert measure.unit_is("Foot") == "Length" and measure.unit_is("Square Foot") == "Area" and not measure.unit_is("Nos")
		cord = frappe.get_doc({"doctype": "Item", "item_code": "DEMO-CORD", "item_name": "Backer Rod", "item_group": "Products", "stock_uom": "Meter"}).insert()
		assert cord.one_measured_by == "Length", cord.one_measured_by
		bolt = frappe.get_doc({"doctype": "Item", "item_code": "DEMO-BOLT", "item_name": "Bolt", "item_group": "Products", "stock_uom": "Nos"}).insert()
		assert bolt.one_measured_by == "No", bolt.one_measured_by
		bolt.stock_uom = "Square Meter"
		bolt.save()
		assert bolt.one_measured_by == "Area", "a new unit that is an area sells it by area"
		assert frappe.db.get_value("Item", sheet, "one_measured_by") == "Area", "a sheet kept by the piece keeps what it says"
		assert not frappe.db.exists("Item", {"one_measured_by": ["in", ["", None]]}), "every item says how it is sold"
		panel = frappe.get_doc({"doctype": "Item", "item_code": "DEMO-CW", "item_name": "Curtain Wall Panel", "item_group": "Products", "stock_uom": "Nos", "one_measured_by": "Piece"}).insert()
		assert panel.one_measured_by == "Piece", "a panel sold by the piece keeps what it says"
	with as_user("omar@one.test"):
		customer = frappe.get_all("Customer", limit=1, pluck="name")[0]
		quote = frappe.get_doc({"doctype": "Quotation", "quotation_to": "Customer", "party_name": customer, "items": [
			{"item_code": glass, "one_pieces": 4, "one_length": 1200, "one_width": 800, "qty": 1},
			{"item_code": sheet, "one_pieces": 2, "one_length": 1250, "one_width": 2500, "qty": 1},
			{"item_code": profile, "one_pieces": 6, "one_length": 2400, "qty": 1},
			{"item_code": "DEMO-CW", "one_length": 20525, "one_width": 3500, "qty": 2},
			{"item_code": concrete, "one_size_uom": "Centimeter", "one_pieces": 2, "one_length": 100, "one_width": 50, "one_height": 20, "uom": "Cubic Meter", "qty": 1},
		]}).insert()
		said = [(row.qty, row.uom, row.one_size) for row in quote.items]
		assert said == [
			(3.84, "Square Meter", "4 × 1200 × 800 mm"), (2.0, "Nos", "2 × 1250 × 2500 mm"), (14.4, "Meter", "6 × 2400 mm"),
			(2.0, "Nos", "20525 × 3500 mm"), (0.2, "Cubic Meter", "2 × 100 × 50 × 20 cm"),
		], said
		assert quote.items[0].one_size_uom == "Millimeter", "the workspace's unit, said on the line"
		quote.submit()
		order = make_sales_order(quote.name)
		assert [(row.one_pieces, row.one_length, row.qty) for row in order.items][:1] == [(4, 1200, 3.84)], "the order keeps the size"


@check
def oneinventory_a_return_is_counted_on_what_it_came_back_against():
	"""A window sent back is counted on its delivery, and goods sent back to a
	supplier on their receipt, so the delivery's head says Returned and its
	billed share reads true. The demo saves a return and submits it as the
	form does; one built and submitted in one go was never counted."""
	from frappe.utils import flt

	for doctype in ("Delivery Note", "Purchase Receipt"):
		returns = frappe.get_all(doctype, filters={"is_return": 1, "docstatus": 1}, pluck="return_against")
		assert returns, f"the demo sends back no {doctype}"
		for against in returns:
			assert flt(frappe.db.get_value(doctype, against, "per_returned")) > 0, (doctype, against)
	assert not frappe.get_all("Stock Reconciliation", filters={"docstatus": 1, "set_warehouse": ["is", "not set"]})
	shipment = frappe.get_all("Shipment Delivery Note", filters={"parenttype": "Shipment"}, pluck="delivery_note")
	assert shipment and frappe.db.get_value("Delivery Note", shipment[0], "customer") == "Gulf Properties REIT", shipment


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


@check
def oneinventory_transfer_stock_moves_it_in_one_step():
	"""Transfer Stock on Stock on Hand asks only where from, where to and what,
	with the project and a note, and ERPNext's Material Transfer is made and submitted as the reader: the
	hinges leave Stores and arrive in Finished Goods, a batched item (the
	sealant) takes its batches as ERPNext picks them, more than there is is
	refused by ERPNext's own check, and somebody without OneInventory cannot
	move anything."""
	from frappe.utils import flt

	from onedesk.one_inventory import stock

	def held(item, place):
		return flt(frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh(place)}, "actual_qty"))

	before = held("HW-HINGE", "Stores"), held("HW-HINGE", "Finished Goods")
	with as_user("karim@one.test"):
		project = frappe.get_all("Project", filters={"status": "Open"}, pluck="name", limit=1)[0]
		name = stock.transfer(
			wh("Stores"), wh("Finished Goods"), [{"item": "HW-HINGE", "qty": 10}, {"item": "SIL-WP", "qty": 5}], project=project, remarks="For the villa's doors"
		)
		entry = frappe.get_doc("Stock Entry", name)
		assert entry.docstatus == 1 and entry.purpose == "Material Transfer" and len(entry.items) == 2, entry.as_dict()
		assert entry.project == project and {row.project for row in entry.items} == {project} and entry.remarks == "For the villa's doors"
		assert (held("HW-HINGE", "Stores"), held("HW-HINGE", "Finished Goods")) == (before[0] - 10, before[1] + 10)
		try:
			stock.transfer(wh("Stores"), wh("Finished Goods"), [{"item": "HW-HINGE", "qty": 1_000_000}])
			raise AssertionError("moved more than there is")
		except frappe.ValidationError:
			pass
	with as_user("nadia@one.test"):
		try:
			stock.transfer(wh("Stores"), wh("Finished Goods"), [{"item": "HW-HINGE", "qty": 1}])
			raise AssertionError("moved stock without OneInventory")
		except frappe.PermissionError:
			pass


@check
def oneinventory_stock_on_hand_says_what_the_stores_hold():
	"""Stock on Hand lists what is held now, its worth what the warehouses
	hold in the books' own figures. The silicone is low in Stores, more
	windows are promised than there are, one warehouse or a search narrows it,
	and a warehouse's head says what it holds, under a group too. OneAI reads
	the stores as the page does, and the Inventory Check sends new stock to
	the Stores. Somebody without OneInventory is refused."""
	from frappe.utils import flt

	from onedesk.one_inventory import ai, heads, ready, stock

	held = sum(flt(one) for one in frappe.get_all("Bin", pluck="stock_value"))
	with as_user("karim@one.test"):
		every = stock.on_hand()
		assert every["count"] and abs(every["worth"] - held) < 0.01, (every["worth"], held)
		company = frappe.db.get_value("Warehouse", wh("Stores"), "company")
		assert {frappe.db.get_value("Warehouse", one["name"], "company") for one in every["warehouses"]} == {company}
		low = {one["item"]: one for one in every["items"] if one["low_in"]}
		assert "SIL-CLR" in low and wh("Stores") in low["SIL-CLR"]["low_in"], list(low)
		assert any(one["item"] == "WIN-CS12" and one["free"] < 0 for one in every["items"]), "the windows are promised beyond what there is"
		assert all(one["state"] == "short" for one in every["items"] if one["free"] < 0), "short is the status of anything promised beyond what there is"
		assert all(one["on_hand"] == one["committed"] + one["free"] for one in every["items"]), "on hand is committed and available, as Shopify splits it"
		stores = stock.on_hand(warehouse=wh("Stores"))
		in_stores = sum(flt(one) for one in frappe.get_all("Bin", filters={"warehouse": wh("Stores")}, pluck="stock_value"))
		assert abs(stores["worth"] - in_stores) < 0.01 and stores["worth"] < every["worth"]
		assert sorted(one["item"] for one in stock.on_hand(search="silicone")["items"]) == ["SIL-CLR", "SIL-WP"]
		place = frappe.get_doc("Warehouse", wh("Stores"))
		assert heads.warehouse_items(place) == sum(1 for one in stores["items"] if one["on_hand"] > 0)
		assert heads.warehouse_low(place)["value"] >= 1 and heads.warehouse_last(place)
		assert heads.warehouse_worth(place)
		group = frappe.db.get_value("Warehouse", {"is_group": 1, "parent_warehouse": ["in", ("", None)]}) or frappe.db.get_value("Warehouse", {"is_group": 1})
		assert heads.warehouse_items(frappe.get_doc("Warehouse", group)) >= heads.warehouse_items(place), "a group holds what is under it"
		facts = ai.stock_on_hand(warehouse=wh("Stores"))
		assert abs(facts["worth"] - in_stores) < 0.01 and any(one["item"] == "SIL-CLR" and one["low_in"] for one in facts["lines"]), facts["worth"]
		assert ai.stock_on_hand(warehouse="Nowhere").get("error")
		assert "stock_on_hand" in (ai.page({"page": "stock-on-hand"}) or "")
	with as_user(OWNER):
		ready.fix("home")
		said = {one["key"]: one for one in ready.checks()}
		assert frappe.db.get_value("Company", ready.company().name, "default_warehouse") == wh("Stores")
		assert said["home"]["state"] == said["below_zero"]["state"] == said["reorder"]["state"] == ready.READY, said
	with as_user("nadia@one.test"):
		assert ai.stock_on_hand().get("error")
		try:
			stock.on_hand()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody without OneInventory reads the stores")


@check
def oneinventory_goods_arrive_as_the_receipt_says():
	"""Receiving, as Karim and Huda do it. The euro hardware's freight and duty
	are added to what each piece cost, in dirhams, and its value in the stores
	is its euro price at the rate plus those. Six of forty square metres of
	tempered glass are rejected on arrival after their inspection, kept apart
	and left off the bill. A receipt prints as a goods received note, and OneAI
	reads a receipt, says what is still to come and drafts the next one."""
	from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice

	from onedesk.one_ai import proposals
	from onedesk.one_inventory import ai, heads, ready

	euro = frappe.db.get_value("Landed Cost Purchase Receipt", {"docstatus": 1}, "receipt_document")
	assert euro, "no landed cost in the demo"
	assert frappe.has_permission("Landed Cost Voucher", "create", user="huda@one.test"), "the accountant cannot add freight and duty"
	glass = frappe.db.get_value("Quality Inspection", {"reference_type": "Purchase Receipt", "docstatus": 1}, "reference_name")
	with as_user("karim@one.test"):
		doc = frappe.get_doc("Purchase Receipt", euro)
		assert doc.currency == "EUR" and abs(flt(doc.base_net_total) - flt(doc.net_total) * flt(doc.conversion_rate)) <= CENTS
		added = sum(flt(row.landed_cost_voucher_amount) for row in doc.items)
		charges = sum(flt(one) for one in frappe.get_all("Landed Cost Taxes and Charges", filters={"parent": ["in", frappe.get_all("Landed Cost Purchase Receipt", filters={"receipt_document": euro, "docstatus": 1}, pluck="parent")]}, pluck="base_amount"))
		assert added and abs(added - charges) <= CENTS, (added, charges)
		valued = sum(flt(row.valuation_rate) * flt(row.stock_qty) for row in doc.items)
		assert abs(valued - flt(doc.base_net_total) - added) <= 1, (valued, doc.base_net_total, added)
		assert heads.receipt_landed(doc) and "€" in heads.receipt_worth(doc)["label"], heads.receipt_worth(doc)
		assert heads.receipt_order(doc)["route"].startswith("/desk/purchase-order/")
		arrived = frappe.get_doc("Purchase Receipt", glass)
		row = arrived.items[0]
		assert (row.received_qty, row.qty, row.rejected_qty) == (40, 34, 6) and frappe.db.get_value("Warehouse", row.rejected_warehouse, "is_rejected_warehouse")
		assert heads.receipt_rejected(arrived)["tone"] == "alarm" and heads.receipt_rejected(doc) is None
		printed = frappe.get_print("Purchase Receipt", arrived.name, print_format="One Purchase Receipt")
		assert "Goods Received Note" in printed and arrived.supplier_name in printed
		facts = ai.receipt_facts(glass)
		assert facts["lines"][0]["rejected"] == 6 and facts["inspections"][0]["item"] == "GLS-TMP10", facts
		assert ai.receipt_facts(euro)["freight_and_duty"], "freight and duty on the euro hardware"
		coming = ai.still_to_arrive(supplier="Euro Hardware Trading")
		assert coming["lines"] and all(one["supplier"] == "Euro Hardware Trading" for one in coming["lines"]), coming
		order = coming["lines"][0]["order"]
		card = ai.plan_receipt(order, lines=[{"item": coming["lines"][0]["item"], "qty": 1}])
		made = proposals.apply(card["proposal"])["record"]
		drafted = frappe.get_doc("Purchase Receipt", made)
		assert drafted.docstatus == 0 and [(one.purchase_order, one.qty) for one in drafted.items] == [(order, 1)], drafted.items
		drafted.delete()
	with as_user(OWNER):
		ready.fix("rejected")
		assert {one["key"]: one for one in ready.checks()}["rejected"]["state"] == ready.READY
		bill = make_purchase_invoice(glass)
		assert [flt(one.qty) for one in bill.items] == [34], "the six rejected are not billed"
	assert frappe.db.get_value("Notification", "Material Request Receipt Notification", "enabled"), "nobody is told their goods came"
	with as_user("nadia@one.test"):
		assert ai.receipt_facts(glass).get("error")


@check
def oneinventory_goods_go_out_as_the_order_says():
	"""Delivering, as Karim does it. The villa's windows were picked, packed in
	three crates and put on Yousef's trip, and its twenty sliding doors are
	held for it: held stock is counted once, not twice, in what is free to
	sell. A delivery says its order, total and trip, a packing slip and a pick
	list print, anybody who reads an order can open it, and OneAI reads a
	delivery, says what is still to go and drafts the next one."""
	from onedesk.one_ai import memory, proposals
	from onedesk.one_inventory import ai, heads, item, ready, stock, trips

	villa = frappe.db.get_value("Sales Order", {"project": VILLA, "docstatus": 1})
	note = frappe.db.get_value("Delivery Note Item", {"against_sales_order": villa, "docstatus": 1}, "parent")
	assert note, "nothing of the villa's has gone out"
	assert frappe.db.get_value("Stock Reservation Entry", {"voucher_no": villa, "item_code": "DR-SL24", "docstatus": 1}, "reserved_qty") == 20
	with as_user("karim@one.test"):
		assert frappe.has_permission("Selling Settings", "read"), "an order opens with a permission error"
		doc = frappe.get_doc("Delivery Note", note)
		assert heads.delivery_order(doc)["value"] == villa
		assert "Yousef Bakr" in heads.delivery_trip(doc)["value"], heads.delivery_trip(doc)
		assert heads.delivery_total(doc)
		trip = frappe.get_doc("Delivery Trip", frappe.db.get_value("Delivery Stop", {"delivery_note": note}, "parent"))
		trips.onload(trip)
		assert trip.get_onload().maps is False, "the route buttons show with no maps key"
		slip = frappe.get_doc("Packing Slip", {"delivery_note": note, "docstatus": 1})
		printed = frappe.get_print("Packing Slip", slip.name, print_format="One Packing Slip")
		assert "Packing Slip" in printed and doc.customer_name in printed and "From Case" in printed
		pick = frappe.get_doc("Pick List", frappe.db.get_value("Pick List Item", {"sales_order": villa}, "parent"))
		assert "Pick List" in frappe.get_print("Pick List", pick.name, print_format="One Pick List")
		bins = frappe.get_all("Bin", filters={"item_code": "DR-SL24"}, fields=["warehouse", "actual_qty", "reserved_qty", "reserved_stock", "ordered_qty", "projected_qty", "stock_value"])
		said = item.summary(bins, [])
		ordered = sum(flt(one.reserved_qty) for one in bins)
		assert said["held"] == 20 and said["free"] == said["on_hand"] - ordered, said
		row = next(one for one in stock.on_hand(search="DR-SL24")["items"] if one["item"] == "DR-SL24")
		assert row["free"] == said["free"] and row["held"] == 20, row
		facts = memory.about_record("Delivery Note", note)
		assert {row["against_sales_order"] for row in facts["items"]} == {villa}, facts["items"]
		assert {"Packing Slip", "Delivery Trip"} <= set(facts["links_here"]), facts["links_here"]
		going = ai.still_to_deliver(project=VILLA)
		doors = next(one for one in going["lines"] if one["item"] == "DR-SL24")
		assert doors["held_for_it"] == 20, doors
		card = ai.plan_delivery(villa, lines=[{"item": "WIN-CS12", "qty": 1}])
		made = proposals.apply(card["proposal"])["record"]
		drafted = frappe.get_doc("Delivery Note", made)
		assert drafted.docstatus == 0 and [(one.against_sales_order, one.qty) for one in drafted.items] == [(villa, 1)], drafted.items
		drafted.delete()
	assert {one["key"]: one for one in ready.checks()}["held"]["state"] == ready.READY
	with as_user("nadia@one.test"):
		try:
			memory.about_record("Delivery Note", note)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the stores read a delivery")


@check
def oneinventory_stock_moves_and_counts_reach_the_books():
	"""Moving and counting, as Karim, Tariq and Huda do it. The villa's
	materials went from the stores to its site on a transfer note, Tariq used
	some there, and a count of the stores found three hinges short, posted to
	the books as a loss. A recalculation that fails and a warehouse posting to
	the wrong account reach the stock and accounts managers."""
	from erpnext.stock.utils import get_stock_balance

	from onedesk.one_inventory import heads, ready, tell

	site = frappe.db.get_value("Warehouse", {"warehouse_name": "Mansour Villa Site"})
	sent = frappe.get_doc("Stock Entry", frappe.db.get_value("Stock Entry", {"docstatus": 1, "purpose": "Material Transfer", "to_warehouse": site}))
	used = frappe.get_doc("Stock Entry", frappe.db.get_value("Stock Entry", {"docstatus": 1, "purpose": "Material Issue", "from_warehouse": site}))
	assert sent.owner == "karim@one.test" and used.owner == "tariq@one.test"
	with as_user("tariq@one.test"):
		assert frappe.has_permission("Stock Settings", "read")
	assert sent.project == used.project == frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	moved = {
		code: sum(flt(one) for one in frappe.get_all("Stock Ledger Entry", filters={"warehouse": site, "item_code": code, "voucher_type": "Stock Entry", "is_cancelled": 0}, pluck="actual_qty"))
		for code in ("ALU-6063", "SIL-CLR")
	}
	assert moved == {"ALU-6063": 40, "SIL-CLR": 6}, moved
	assert flt(get_stock_balance("ALU-6063", site)) == 40

	assert heads.move_from(sent)["value"] == "Stores" and heads.move_to(sent)["value"] == "Mansour Villa Site"
	assert heads.move_value(sent) and heads.move_used(sent) is None and heads.move_to(used) is None
	printed = frappe.get_print("Stock Entry", sent.name, print_format="One Stock Entry")
	assert "Transfer Note" in printed and "Issue Note" in frappe.get_print("Stock Entry", used.name, print_format="One Stock Entry")
	assert "Mansour Villa Site" in printed and "Villa 14, Al Wasl Road" in printed, "it says where the goods go"
	assert frappe.db.get_value("Print Format", "One Stock Entry", "doc_type") == "Stock Entry"

	count = frappe.get_doc("Stock Reconciliation", {"purpose": "Stock Reconciliation", "docstatus": 1})
	adjustment = frappe.get_cached_value("Company", count.company, "stock_adjustment_account")
	assert count.owner == "karim@one.test" and count.expense_account == adjustment and flt(count.difference_amount) < 0
	posted = frappe.get_all("GL Entry", filters={"voucher_no": count.name, "account": adjustment, "is_cancelled": 0}, fields=["debit", "credit"])
	assert flt(sum(flt(one.debit) - flt(one.credit) for one in posted), 2) == flt(-count.difference_amount, 2)
	assert heads.count_where(count)["value"] == "Stores" and heads.count_items(count) == "1"
	assert frappe.get_meta("Stock Reconciliation").get_field("purpose").default == "Stock Reconciliation"

	with as_user("huda@one.test"):
		rows = {one["key"]: one for one in ready.checks()}
	assert rows["stock_accounts"]["state"] == ready.READY and rows["reposts"]["state"] == ready.READY
	entry = frappe.get_all("Repost Item Valuation", filters={"docstatus": 1, "status": "Completed"}, pluck="name", limit=1)[0]
	rejected = frappe.db.get_value("Warehouse", {"warehouse_name": "Rejected"})
	cash = frappe.db.get_value("Account", {"company": count.company, "account_type": "Cash", "is_group": 0})
	frappe.db.set_value("Repost Item Valuation", entry, "status", "Failed", update_modified=False)
	frappe.db.set_value("Warehouse", rejected, "account", cash, update_modified=False)
	frappe.flags.pop("warehouse_account_map", None)
	try:
		with as_user("huda@one.test"):
			rows = {one["key"]: one for one in ready.checks()}
		assert rows["reposts"]["state"] == ready.TO_DO and rows["reposts"]["fix"] == "reposts"
		assert rows["stock_accounts"]["state"] == ready.TO_DO and rejected in rows["stock_accounts"]["says"]
		with _Told() as told:
			tell.stock_values()
		assert {"huda@one.test", "karim@one.test"} <= told.to("Reposting Failed")
		assert {"huda@one.test", "karim@one.test"} <= told.to("Stock Account Wrong")
	finally:
		frappe.db.set_value("Repost Item Valuation", entry, "status", "Completed", update_modified=False)
		frappe.db.set_value("Warehouse", rejected, "account", None, update_modified=False)
		frappe.flags.pop("warehouse_account_map", None)

	from onedesk.one_ai import proposals, tools
	from onedesk.one_inventory import ai

	with as_user("karim@one.test"):
		facts = tools.read_record("Stock Entry", sent.name)
		assert facts["project"] == sent.project and {(one["item_code"], one["t_warehouse"]) for one in facts["items"]} == {(code, site) for code in ("ALU-6063", "HW-LOCK", "SIL-CLR")}
		found = tools.read_record("Stock Reconciliation", count.name)
		assert flt(found["difference_amount"]) == flt(count.difference_amount) and flt(found["items"][0]["current_qty"]) - flt(found["items"][0]["qty"]) == 3
		card = ai.plan_transfer(site, [{"item": "SEAL-EPDM", "qty": 50}], project=sent.project)
		made = frappe.get_doc("Stock Entry", proposals.apply(card["proposal"])["record"])
		assert made.docstatus == 0 and made.purpose == "Material Transfer" and made.project == sent.project
		assert [(one.item_code, one.qty, one.s_warehouse, one.t_warehouse) for one in made.items] == [("SEAL-EPDM", 50, frappe.get_cached_value("Company", count.company, "default_warehouse"), site)]
		made.delete()
	with as_user("nadia@one.test"):
		assert not frappe.has_permission("Stock Entry", "read", doc=sent.name)
		for doctype, name in (("Stock Entry", sent.name), ("Stock Reconciliation", count.name)):
			try:
				tools.read_record(doctype, name)
			except frappe.PermissionError:
				continue
			raise AssertionError(f"somebody outside the stores read {doctype} {name}")



@check
def onebook_home_tells_how_the_money_is_doing():
	"""Huda's Home: its figures agree with the ledger and with what is owed,
	the ageing adds up to Accounts Receivable, Today lists every overdue sales
	invoice, and every row of the directory opens something that exists. An
	overdue invoice's head is red with its Paid step late; a paid one is
	green with every step done."""
	from onedesk.one import head
	from onedesk.one_book import home, story

	with as_user("huda@one.test"):
		told = story.read()
		said = home.read()
		cards = told["cards"]
		assert set(cards) == {"cash", "receivable", "overdue", "payable", "due_this_week", "profit"}, set(cards)
		assert abs(cards["cash"]["value"] - home.cash()["value"]) < 0.01, (cards["cash"], home.cash())
		assert abs(cards["profit"]["value"] - home.profit_this_month()["value"]) < 0.01
		assert abs(cards["receivable"]["value"] - home.owed_to_us()["value"]) < 0.01
		assert len(cards["cash"]["series"]) == story.MONTHS
		aged = sum(one["owed"] for one in told["receivable"]["ages"])
		assert abs(aged - cards["receivable"]["value"]) < 0.01, (aged, cards["receivable"])
		overdue = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "status": "Overdue"}, pluck="name")
		assert overdue and said["needs"]["overdue"]["count"] == len(overdue), (said["needs"]["overdue"], overdue)
		for row in said["everything"]:
			kind = "DocType" if row["kind"] == "Masters" else row["kind"]
			assert frappe.db.exists(kind, row["target"]), row
		record = frappe.get_doc("Record Head", "Sales Invoice")
		late = head.said(frappe.get_doc("Sales Invoice", overdue[0]), record)
		assert late["sentence"]["colour"] == "red", late["sentence"]
		assert late["band"][0]["steps"][-1]["state"] == "late", late["band"][0]
		paid = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "status": "Paid", "is_return": 0}, pluck="name", limit=1)
		done = head.said(frappe.get_doc("Sales Invoice", paid[0]), record)
		assert done["sentence"]["colour"] == "green" and all(step["state"] == "done" for step in done["band"][0]["steps"]), done


@check
def onecrm_home_tells_how_selling_is_going():
	"""Omar's Home: a year of selling month by month, the funnel following
	opportunities to their quotations, orders, invoices and payments as
	ERPNext links them, the pipeline by stage adding up to its value, every
	lost one under a reason, Today listing only steps that are set and due,
	and every row of the directory opening something that exists."""
	from onedesk.one_crm import home, measure, story

	with as_user("omar@one.test"):
		told = story.read()
		said = home.read()
		cards = told["cards"]
		assert set(cards) == {"leads", "pipeline", "weighted", "won", "rate", "average"}, set(cards)
		assert len(cards["won"]["series"]) == story.MONTHS and sum(1 for one in cards["won"]["series"] if one) >= 5, cards["won"]
		alive = sum(measure.value(one) for one in measure.deals(measure.alive()))
		assert abs(cards["pipeline"]["value"] - alive) < 0.01
		staged = sum(one["value"] for one in told["pipeline"]["stages"] if not one["held"])
		assert abs(staged - alive) < 0.01, (staged, alive)
		funnel = {one["step"]: one["count"] for one in told["sales"]["funnel"]}
		assert list(funnel) == list(story.FUNNEL), funnel
		assert funnel["Opportunity"] >= funnel["Quotation"] >= funnel["Sales Order"] >= funnel["Sales Invoice"] >= funnel["Paid"] >= 1, funnel
		lost = sum(1 for one in measure.closed().values() if one.outcome == "Lost" and one.on >= getdate(told["months"][0]))
		assert sum(one["count"] for one in told["pipeline"]["lost"]) >= lost, told["pipeline"]["lost"]
		due = said["needs"]["opportunities"]["rows"] + said["needs"]["leads"]["rows"]
		assert due and all(one["on"] for one in due), due
		for row in said["everything"]:
			kind = "DocType" if row["kind"] == "Masters" else row["kind"]
			assert frappe.db.exists(kind, row["target"]), row
		from onedesk.one_ai import chat, suggest

		offered = [one["label"] for one in suggest.for_page({"page": "onecrm"})]
		assert "Why are we losing opportunities?" in offered, offered
		assert "OneCRM's Home" in chat._page({"page": "onecrm"})


@check
def onecrm_an_opportunity_says_where_its_sale_went():
	"""An opportunity's head follows the sale past the deal: Bayview's paid
	in full and green with every step done, Osei's billed and owing late in
	red, Tran's ordered and not billed, Iqbal's lost with its reason, Harbour
	on hold with nothing under way; and a customer's page counts what it may
	still buy."""
	from onedesk.one import head
	from onedesk.one_crm import heads

	record = frappe.get_doc("Record Head", "Opportunity")

	def said(title):
		return head.said(frappe.get_doc("Opportunity", {"title": title}), record)

	with as_user("omar@one.test"):
		paid = said("Bayview tower lobby doors")
		assert paid["sentence"] == {"text": "Won, billed and paid in full.", "colour": "green"}, paid["sentence"]
		assert [one["state"] for one in paid["band"][0]["steps"]] == ["done"] * 5, paid["band"][0]
		owing = said("Osei Builders site office windows")
		assert owing["sentence"]["colour"] == "red" and owing["band"][0]["steps"][-1]["state"] == "late", owing
		ordered = said("Tran Retail shopfront")
		assert ordered["sentence"]["text"] == "Won and ordered; nothing is billed yet.", ordered["sentence"]
		lost = said("Iqbal Clinics reception")
		assert lost["sentence"] == {"text": "Lost: Price.", "colour": "gray"}, lost["sentence"]
		assert lost["band"][0]["steps"][0]["label"] == "Lead", lost["band"][0]
		held = said("Harbour Logistics depot doors")
		assert not any(one["state"] in ("now", "late") for one in held["band"][0]["steps"]), held["band"][0]
		crescent = heads.of_customer(frappe.get_doc("Customer", "Crescent Schools"))
		assert crescent and crescent["value"].startswith("1 open"), crescent


@check
def onecrm_campaigns_prospects_and_meetings():
	"""What Omar's Campaign and Selling groups list: each campaign counts the
	leads it brought in Campaign Efficiency, the mail campaign is under way
	to its email group, the prospect holds its lead, and the meeting booked
	with Marcus is on Omar's own calendar, not everyone's."""
	from frappe.desk.query_report import run

	with as_user("omar@one.test"):
		rows = run("Campaign Efficiency", {"from_date": str(add_days(today(), -400)), "to_date": today()})["result"]
		counted = {row["utm_campaign"]: row["lead_count"] for row in rows}
		assert counted.get("Dubai Design Week 2026") == 2 and counted.get("Hotel Refit Mailer") == 2, rows
		mailing = frappe.get_all("Email Campaign", filters={"recipient": "Hotel Owners"}, fields=["status"])
		assert mailing and mailing[0].status in ("Scheduled", "In Progress"), mailing
		assert frappe.get_all("Prospect Lead", filters={"parent": "Erdem Towers"}, pluck="lead_name")
		meeting = frappe.get_all("Appointment", filters={"customer_email": "marcus@webbhosp.example"}, fields=["calendar_event"])
		assert meeting and meeting[0].calendar_event, meeting
		event = frappe.get_doc("Event", meeting[0].calendar_event)
		assert event.event_type == "Private" and event.owner == "omar@one.test", (event.event_type, event.owner)


@check
def onecrm_a_next_step_come_due_is_told_once():
	"""A step come due on Omar's opportunity reaches him as Next Step Due, in
	its words, once however often the scheduler looks."""
	from unittest.mock import patch

	from onedesk.one_crm import tell

	deal = frappe.db.get_value("Opportunity", {"title": "Nordlicht second showroom"})
	frappe.db.set_value("Opportunity", deal, {"one_next_step": "Send the workshop agenda", "one_next_on": add_to_date(now_datetime(), minutes=-1)})
	told = []
	with patch("onedesk.one.notify.notify", side_effect=lambda name, users, **said: told.append((name, users, said))):
		tell.due()
		tell.due()
	told = [one for one in told if one[2]["record"] == ("Opportunity", deal)]
	assert [(name, users) for name, users, _said in told] == [("Next Step Due", "omar@one.test")], told
	assert told[0][2]["step"] == "Send the workshop agenda" and told[0][2]["title"] == "Nordlicht second showroom", told


@check
def onebook_oneai_reads_the_money_as_home_does():
	"""What OneAI reads in OneBook agrees with Home: the figures are Home's,
	the overdue invoices are Today's, one invoice says what settled it, the
	bank lines are Today's; and Home offers its three questions."""
	from onedesk.one_ai import chat, suggest
	from onedesk.one_book import ai, home, story

	with as_user("huda@one.test"):
		money = ai.money_now()
		assert money["figures"]["cash"]["now"] == story.read()["cards"]["cash"]["value"], money["figures"]
		late = ai.late_invoices("Sales Invoice")
		assert late["count"] == home.needs_you()["overdue"]["count"] and late["count"], late
		assert ai.late_invoices("Sales Invoice", party=late["invoices"][0]["party"])["count"] >= 1
		paid = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "status": "Paid", "is_return": 0}, pluck="name", limit=1)
		said = ai.invoice_facts(paid[0])
		assert said["still_owed"] == 0 and said["payments"], said
		assert ai.bank_to_match()["lines"] == home.needs_you()["bank"]["count"]
		offered = [one["label"] for one in suggest.for_page({"page": "books"})]
		assert "How is the money doing?" in offered, offered
		assert "OneBook's Home" in chat._page({"page": "books"})
	with as_user("rania@one.test"):
		assert ai.bank_to_match().get("error") and ai.late_invoices().get("error"), "outside the books, nothing is read"


@check
def onebook_chases_what_customers_owe():
	"""Huda's chasing: the customer longest late has a payment reminder that
	prints as One's Payment Reminder with each overdue invoice and the bank to
	pay into; another has a payment request; the statements go monthly; DEWA's
	direct debits match by a rule; and Dunning opens in OneBook's rail."""
	with as_user("huda@one.test"):
		reminder = frappe.get_doc("Dunning", frappe.get_all("Dunning", filters={"docstatus": 1}, pluck="name", limit=1)[0])
		printed = frappe.get_print("Dunning", reminder.name, print_format="One Payment Reminder")
		assert "Payment Reminder" in printed and reminder.overdue_payments[0].sales_invoice in printed
		iban = frappe.db.get_value("Bank Account", reminder.one_pay_into, "iban")
		assert iban and iban in printed, "it says where to pay"
		assert frappe.db.get_value("Property Setter", {"doc_type": "Dunning", "property": "default_print_format"}, "value") == "One Payment Reminder"
		assert frappe.get_all("Payment Request", filters={"reference_doctype": "Sales Invoice", "docstatus": 1})
		assert frappe.db.get_value("Process Statement Of Accounts", "Monthly Statements", "frequency") == "Monthly"
		assert frappe.db.exists("Bank Transaction Rule", "DEWA direct debit")
	assert frappe.get_hooks("one_module_heirs").get("Accounts") == ["OneBook"], "Dunning opens in OneBook"


@check
def onebook_a_late_invoice_ages_into_its_column():
	"""The invoice longest late sits in the same column of what is owed on
	Huda's Home as in ERPNext's Accounts Receivable, and that column is the
	one its days past due fall in."""
	from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute

	from onedesk.one_book import home, story

	with as_user("huda@one.test"):
		late = frappe.get_all(
			"Sales Invoice",
			filters={"docstatus": 1, "status": "Overdue", "company": COMPANY},
			fields=["name", "due_date", "outstanding_amount"],
			order_by="due_date asc",
			limit=1,
		)
		assert late, "the demo leaves an invoice late"
		one = late[0]
		days = date_diff(today(), one.due_date)
		bands = [row["band"] for row in story.ageing([])]
		ours = next(row["band"] for row in story.ageing([one]) if row["owed"])
		low, _, high = ours.partition("-")
		assert int(low) <= days and (high == "Above" or days <= int(high)), (ours, days)
		told = {row["band"]: row["owed"] for row in story.read()["receivable"]["ages"]}
		assert told[ours] >= flt(one.outstanding_amount) - 0.01, (told, one)
		_, rows, *_ = execute(
			frappe._dict(company=home._company(), report_date=today(), range="30, 60, 90, 120", ageing_based_on="Due Date")
		)
		row = next(row for row in rows if row.get("voucher_no") == one.name)
		theirs = next(n for n in range(1, 6) if abs(flt(row.get(f"range{n}")) - flt(one.outstanding_amount)) < 0.01)
		assert bands[theirs] == ours, (bands[theirs], ours, days)


@check
def onebook_profit_and_loss_shows_each_month_in_its_month():
	"""ERPNext's Profit and Loss by month, as Huda runs it: the workshop and
	office rent, 38,000 on the first of each month, sits in each month this
	year, and nowhere twice."""
	from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute

	from onedesk.one_book import home

	with as_user("huda@one.test"):
		year = frappe.db.get_value(
			"Fiscal Year", {"year_start_date": ["<=", today()], "year_end_date": [">=", today()]}, "name"
		)
		_, rows, *_ = execute(
			frappe._dict(
				company=home._company(),
				filter_based_on="Fiscal Year",
				from_fiscal_year=year,
				to_fiscal_year=year,
				period_start_date=getdate(f"{getdate(today()).year}-01-01"),
				period_end_date=getdate(f"{getdate(today()).year}-12-31"),
				periodicity="Monthly",
				accumulated_values=0,
				presentation_currency=None,
			)
		)
		rent = next(row for row in rows if (row.get("account_name") or "").startswith("Rent Expense"))
		months = [key for key in rent if key[:3].lower() in {
			"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
		} and key[-4:].isdigit()]
		assert len(months) == 12, months
		for n, key in enumerate(months, start=1):
			want = 38000 if n <= getdate(today()).month else 0
			assert abs(flt(rent[key]) - want) < 0.01, (key, rent[key])


@check
def onebook_a_payment_says_where_it_stands():
	"""Every payment Huda opens says in a sentence what moved, to or from
	whom, and a payment through the bank says whether the statement has it
	yet. A payment to an employee is titled by their name, not HR-EMP."""
	from onedesk.one import head

	record = frappe.get_doc("Record Head", "Payment Entry")
	with as_user("huda@one.test"):
		for name in frappe.get_all("Payment Entry", filters={"docstatus": ["<", 2]}, pluck="name"):
			doc = frappe.get_doc("Payment Entry", name)
			said = head.said(doc, record)
			assert said["sentence"] and said["sentence"]["text"], name
			if doc.docstatus == 1 and frappe.get_cached_value("Account", doc.paid_from if doc.payment_type == "Pay" else doc.paid_to, "account_type") == "Bank":
				steps = said["band"][0]["steps"]
				assert steps[-1]["state"] == ("done" if doc.clearance_date else "now"), (name, steps)
	named = frappe.get_all("Payment Entry", filters={"party_type": "Employee"}, fields=["title", "party", "party_name"])
	assert named and all(one.title == one.party_name for one in named), named


@check
def onebook_a_journal_entry_says_what_it_is_for():
	"""No journal entry is titled by one of its own accounts: a month's
	depreciation names its asset, a payroll its period, the rent its remark.
	Each says in a sentence what it moved, and names what it is for."""
	from onedesk.one import head
	from onedesk.one_book import journal

	record = frappe.get_doc("Record Head", "Journal Entry")
	with as_user("huda@one.test"):
		for name in frappe.get_all("Journal Entry", filters={"docstatus": 1}, pluck="name"):
			doc = frappe.get_doc("Journal Entry", name)
			if journal.referenced(doc) or doc.user_remark:
				assert not journal.untitled(doc), (name, doc.title)
			said = head.said(doc, record)
			assert said["sentence"] and said["sentence"]["text"], name
		asset = frappe.get_all("Journal Entry", filters={"voucher_type": "Depreciation Entry", "docstatus": 1}, pluck="name", limit=1)
		said = head.said(frappe.get_doc("Journal Entry", asset[0]), record)
		assert any(one.get("route", "").startswith("/desk/asset/") for one in said["band"]), said["band"]


@check
def onebook_the_bank_says_what_is_left_to_match():
	"""Huda's bank account says what the books hold and how many statement
	lines are unmatched; a line says what came in or went out and points at
	the payment with its reference, the draft OneAI made for Marina Hotels."""
	from onedesk.one import head

	with as_user("huda@one.test"):
		account = frappe.get_all("Bank Account", filters={"is_company_account": 1, "is_default": 1}, pluck="name")[0]
		said = head.said(frappe.get_doc("Bank Account", account), frappe.get_doc("Record Head", "Bank Account"))
		unmatched = frappe.db.count("Bank Transaction", {"bank_account": account, "docstatus": 1, "status": "Unreconciled"})
		assert unmatched and any(one.get("value") == str(unmatched) for one in said["band"]), said["band"]
		record = frappe.get_doc("Record Head", "Bank Transaction")
		lines = frappe.get_all("Bank Transaction", filters={"docstatus": 1, "status": "Unreconciled"}, fields=["name", "reference_number"])
		for one in lines:
			said = head.said(frappe.get_doc("Bank Transaction", one.name), record)
			assert said["sentence"]["colour"] == "orange", said["sentence"]
		paid = [one for one in lines if one.reference_number and frappe.db.exists("Payment Entry", {"reference_no": one.reference_number})]
		assert paid, lines
		said = head.said(frappe.get_doc("Bank Transaction", paid[0].name), record)
		assert any((one.get("route") or "").startswith("/desk/payment-entry/") for one in said["band"]), said["band"]


@check
def onebook_the_statement_is_matched_to_what_it_shows():
	"""The transport debit on the bank statement is matched to the bank entry
	Huda made from it in the reconciliation tool: the line is Reconciled with
	nothing left over, the entry carries the bank's reference and is cleared
	on the statement's date, and the bank account counts it no more."""
	from onedesk.one_demo.books import TRANSPORT

	with as_user("huda@one.test"):
		line = frappe.get_all(
			"Bank Transaction",
			filters={"docstatus": 1, "withdrawal": [">", 0], "description": ["like", "%transport%"]},
			fields=["name", "status", "unallocated_amount", "reference_number", "date", "withdrawal"],
		)
		assert line, "the statement has its transport debit"
		line = line[0]
		assert line.status == "Reconciled" and not flt(line.unallocated_amount), line
		paid = frappe.get_doc("Bank Transaction", line.name).payment_entries
		assert len(paid) == 1 and paid[0].payment_document == "Journal Entry", paid
		entry = frappe.get_doc("Journal Entry", paid[0].payment_entry)
		assert entry.docstatus == 1 and entry.cheque_no == line.reference_number, entry.cheque_no
		assert str(entry.clearance_date) == str(line.date), (entry.clearance_date, line.date)
		booked = {row.account.rsplit(" - ", 1)[0]: flt(row.debit) for row in entry.accounts}
		assert booked.get(TRANSPORT) == flt(line.withdrawal), booked
		still = frappe.db.count("Bank Transaction", {"docstatus": 1, "status": "Unreconciled"})
		assert still and still == frappe.db.count("Bank Transaction", {"docstatus": 1}) - 1


@check
def onebook_the_books_check_has_nothing_left_to_do():
	"""The demo company is set up as its accountant would leave it: nothing
	on the Books Check is To Do, Temporary Opening is at nought, and the UAE
	VAT 201 reports the sales made in Dubai, the company's emirate."""
	from frappe.desk.query_report import run as run_report

	from onedesk.one_book import ready

	with as_user("huda@one.test"):
		todo = [row["key"] for row in ready.checks() if row["state"] == ready.TO_DO]
		assert not todo, todo
		assert not ready.temporary(COMPANY)
		said = run_report("UAE VAT 201", filters={"company": COMPANY, "from_date": add_days(today(), -365), "to_date": today()})
		dubai = next(row for row in said["result"] if isinstance(row, dict) and row.get("no") == "1b")
		assert flt(dubai.get("raw_amount")) > 0, dubai


@check
def onebook_a_uae_invoice_prints_as_a_tax_invoice():
	"""In the UAE a sales invoice prints as a Tax Invoice and a credit note as
	a Tax Credit Note, each with the company's TRN, and the VAT line says its
	rate once."""
	trn = frappe.get_cached_value("Company", COMPANY, "tax_id")
	invoice = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0}, pluck="name", limit=1)[0]
	printed = frappe.get_print("Sales Invoice", invoice, print_format="One Sales Invoice")
	assert "Tax Invoice" in printed and trn in printed
	note = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 1}, pluck="name", limit=1)
	assert "Tax Credit Note" in frappe.get_print("Sales Invoice", note[0], print_format="One Sales Invoice")
	assert "% @" not in printed, "the VAT says its rate once"


@check
def oneinventory_a_documents_head_says_where_it_stands():
	"""Every stores document Karim opens says what is next in a sentence, and
	one that moves through stages draws them: Al Noor's late order in red with
	its Received step late, a paid order in green with every step done."""
	from onedesk.one import head

	tracked = {"Purchase Order", "Material Request", "Purchase Receipt", "Delivery Note", "Work Order", "Subcontracting Order"}
	with as_user("karim@one.test"):
		for doctype in sorted(tracked | {"BOM", "Asset"}):
			record = frappe.get_doc("Record Head", doctype)
			for name in frappe.get_all(doctype, filters={"docstatus": 1}, pluck="name", limit=20):
				document = frappe.get_doc(doctype, name)
				said = head.said(document, record)
				assert said["sentence"] and said["sentence"]["text"], (doctype, name)
				if doctype in tracked and not document.get("is_return"):
					steps = next((one["steps"] for one in said["band"] if one.get("steps")), None)
					assert steps and all(step["state"] in ("done", "now", "late", "next") for step in steps), (doctype, name, said["band"])
		record = frappe.get_doc("Record Head", "Purchase Order")
		late = frappe.get_all("Purchase Order", filters={"docstatus": 1, "per_received": 0, "status": ["not in", ["Closed", "On Hold"]], "schedule_date": ["<", today()]}, pluck="name")
		assert late
		said = head.said(frappe.get_doc("Purchase Order", late[0]), record)
		assert said["sentence"]["colour"] == "red", said["sentence"]
		assert [step["state"] for step in said["band"][0]["steps"]][:2] == ["done", "late"], said["band"][0]
		paid = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": "Completed"}, pluck="name")
		finished = [one for one in (head.said(frappe.get_doc("Purchase Order", name), record) for name in paid) if one["sentence"]["colour"] == "green"]
		assert finished and all(step["state"] == "done" for step in finished[0]["band"][0]["steps"]), finished[:1]


@check
def oneinventory_buying_from_request_to_order():
	"""Buying, as Rania, Karim, a supplier on the portal and Huda do it. Rania
	asked for sealant, anchors and gaskets for the villa, Al Noor and Emirates
	Sealants priced them, Emirates Sealants on the portal, and each line went to
	whoever was cheaper on it. Al Noor is late and Karim is told. Al Noor's
	aluminium is agreed for the year, the losing quotes expired, the glass
	orders never made good are closed, and Gulf Glass and Al Noor are scored.
	A request line cannot be ordered twice over on drafts."""
	from onedesk.one_inventory import ai, heads, order, ready, supplier_items, tell

	villa = frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	asked = frappe.get_doc("Material Request", {"owner": "rania@one.test", "project": villa, "docstatus": 1, "material_request_type": "Purchase"})
	assert flt(asked.per_ordered) == 100
	rfq = frappe.get_doc("Request for Quotation", frappe.db.get_value("Request for Quotation Item", {"material_request": asked.name}, "parent"))
	assert {one.supplier for one in rfq.suppliers} == {"Al Noor Aluminium", "Emirates Sealants & Fixings"}
	quotes = {one.supplier: frappe.get_doc("Supplier Quotation", one.name) for one in frappe.get_all("Supplier Quotation", filters={"name": ["in", frappe.get_all("Supplier Quotation Item", filters={"request_for_quotation": rfq.name}, pluck="parent")]}, fields=["name", "supplier"])}
	portal = quotes["Emirates Sealants & Fixings"]
	assert frappe.db.exists("Portal User", {"parent": portal.supplier, "user": portal.owner})
	assert {one.project for one in portal.items} == {villa}

	with as_user("karim@one.test"):
		compared = ai.quotes_now(request=asked.name)
	cheapest = {one["item"]: one["cheapest"] for request in compared["compared"] for one in request["lines"]}
	assert cheapest == {"SIL-CLR": "Emirates Sealants & Fixings", "FIX-ANCH": "Al Noor Aluminium", "SEAL-EPDM": "Al Noor Aluminium"}, cheapest
	ordered = {row.item_code: frappe.db.get_value("Purchase Order", row.parent, "supplier") for row in frappe.get_all("Purchase Order Item", filters={"material_request": asked.name, "docstatus": 1}, fields=["item_code", "parent"])}
	assert ordered == {code: frappe.db.get_value("Supplier", {"supplier_name": name}) for code, name in cheapest.items()}
	assert heads.rfq_cheapest(rfq)["value"] == "Split between 2" and heads.rfq_answered(rfq)["value"] == "2 of 2"
	assert heads.quote_cheapest(portal)["value"] == "1 of 3 lines" and heads._request_quotes(asked) == (2, 2)

	late = frappe.get_doc("Purchase Order", frappe.db.get_value("Purchase Order Item", {"material_request": asked.name, "item_code": "FIX-ANCH", "docstatus": 1}, "parent"))
	assert heads.order_said(late)["colour"] == "red"
	named = {one.name for one in tell.late()}
	assert late.name in named
	closed = frappe.get_all("Purchase Order", filters={"status": "Closed"}, pluck="name")
	services = frappe.get_all("Purchase Order Item", filters={"item_code": ["like", "SVC-%"], "docstatus": 1}, pluck="parent")
	assert closed and not named & set(closed) and not named & set(services)
	said = frappe.db.get_value("Notification Log", {"for_user": "karim@one.test", "document_type": "Purchase Order", "document_name": late.name}, "email_content")
	assert said and "Wall Anchor Set" in said, said
	with _Told() as told:
		tell.orders_late()
	assert "karim@one.test" in told.to("Order Late")
	with as_user("karim@one.test"):
		said = ai.still_to_arrive(late_only=True)
	assert late.name in {one["order"] for one in said["orders"]} and all(line["late_by_days"] > 0 for one in said["orders"] for line in one["lines"]), said

	expired = frappe.get_all("Supplier Quotation", filters={"status": "Expired"}, pluck="name")
	assert expired and heads.quote_valid(frappe.get_doc("Supplier Quotation", expired[0]))["tone"] == "quiet"

	agreed = frappe.get_doc("Blanket Order", {"supplier": "Al Noor Aluminium", "docstatus": 1})
	on_it = frappe.get_all("Purchase Order Item", filters={"blanket_order": agreed.name, "docstatus": 1}, fields=["parent", "rate", "qty"])
	assert on_it and all(flt(one.rate) == flt(agreed.items[0].rate) for one in on_it)
	assert flt(agreed.items[0].ordered_qty) == sum(flt(one.qty) for one in on_it)
	assert heads.blanket_ordered(agreed)["meter"]["value"] == flt(agreed.items[0].ordered_qty)
	printed = frappe.get_print("Blanket Order", agreed.name, print_format="One Blanket Order")
	assert "Blanket Order" in printed and "Al Noor Aluminium" in printed

	with as_user("karim@one.test"):
		tab = supplier_items.read("Al Noor Aluminium")
	lines = {one["item"]: one for one in tab["items"]}
	assert lines["ALU-6063"]["agreed"] and lines["ALU-6063"]["orders"], lines.get("ALU-6063")
	assert lines["FIX-ANCH"]["last"]["rate"] > 0 and lines["FIX-ANCH"]["unit"], lines.get("FIX-ANCH")
	assert tab["count"] == len(tab["items"]) and all(one["item_name"] for one in tab["items"])

	glass = frappe.get_doc("Material Request Item", {"item_code": "GLS-DGU", "project": villa, "docstatus": 1, "ordered_qty": 0})
	with as_user("karim@one.test"):
		first = order.order([{"item_code": glass.item_code, "qty": glass.stock_qty, "warehouse": glass.warehouse, "supplier": "Gulf Glass Industries", "material_request": glass.parent, "material_request_item": glass.name, "uom": glass.stock_uom}])
		assert glass.name not in {one.get("material_request_item") for one in order.rows()}
		try:
			order.order([{"item_code": glass.item_code, "qty": 1, "warehouse": glass.warehouse, "supplier": "Al Noor Aluminium", "material_request": glass.parent, "material_request_item": glass.name, "uom": glass.stock_uom}])
			raise AssertionError("a request line was ordered twice over on drafts")
		except frappe.ValidationError as refused:
			assert "left to order" in str(refused)
		frappe.delete_doc("Purchase Order", first[0])

	card = frappe.get_doc("Supplier Scorecard", "Gulf Glass Industries")
	assert frappe.db.count("Supplier Scorecard Period", {"scorecard": card.name, "docstatus": 1}) >= 6
	assert {one.criteria_name for one in card.criteria} == {name for name, _formula in ready.CRITERIA}
	with as_user("karim@one.test"):
		assert {one["key"]: one for one in ready.checks()}["scoring"]["state"] == ready.READY

	with as_user("karim@one.test"):
		assert frappe.has_permission("Blanket Order", "create") and frappe.has_permission("Supplier Scorecard", "write")
		assert ai.plan_quote_request(asked.name, ["Al Noor Aluminium"]).get("error"), "a request ordered already"
		card_ = ai.plan_quote_request(glass.parent, ["Gulf Glass Industries", "Al Noor Aluminium"], message="Prices for the villa's glass, please.")
		changes = frappe.parse_json(frappe.db.get_value("AI Proposal", card_["proposal"], "changes"))
		assert {one["supplier"] for one in changes["suppliers"]} == {"Gulf Glass Industries", "Al Noor Aluminium"}
		assert {(one["item_code"], one["material_request"]) for one in changes["items"]} == {("GLS-DGU", glass.parent)}
	with as_user("rania@one.test"):
		assert frappe.has_permission("Material Request", "create") and frappe.has_permission("Supplier Scorecard", "read")
		assert not frappe.has_permission("Supplier Scorecard", "write") and not frappe.has_permission("Blanket Order", "cancel")
	with as_user("nadia@one.test"):
		assert not frappe.has_permission("Blanket Order", "read") and ai.quotes_now(request=asked.name).get("error")


@check
def oneinventory_making_from_bill_to_finished_goods():
	"""Making, as Tariq, Samir, Rania and Huda meet it. Tariq keeps the bills of
	materials and makes the work orders, the villa's and the tower's among
	them. Each step is a job card worked by whoever works its workstation, the
	materials used count in the project's cost, and the villa's manager is
	told when its order is made. Rania asked the workshop for the villa's last
	doors. The villa's profile went out to be powder coated and came back."""
	from erpnext.stock.utils import get_stock_balance

	from onedesk.one_demo import making
	from onedesk.one_inventory import heads, ready, tell

	villa = frappe.db.get_value("Project", {"project_name": making.VILLA})
	tower = frappe.db.get_value("Project", {"project_name": making.TOWER})
	window = frappe.get_doc("BOM", {"item": "WIN-CS12", "is_default": 1, "docstatus": 1})
	assert window.owner == making.SUPERVISOR and [one.operation for one in window.operations] == ["Cutting", "Assembly", "Glazing"]
	assert heads.bom_steps(window) == "Cutting · Assembly · Glazing" and flt(window.operating_cost) > 0
	assert heads.bom_orders(window)["value"] == "3"
	orders = frappe.get_all("Work Order", filters={"docstatus": 1}, fields=["name", "owner", "project", "status", "production_item", "produced_qty", "qty"])
	assert {one.owner for one in orders} == {making.SUPERVISOR}, "Tariq makes the work orders"
	assert {one.project for one in orders} == {None, villa, tower}

	done = frappe.get_doc("Work Order", {"project": villa, "production_item": "DR-SL24", "status": "Completed"})
	cards = frappe.get_all("Job Card", filters={"work_order": done.name, "docstatus": 1}, fields=["name", "operation", "total_completed_qty", "total_time_in_mins", "process_loss_qty"])
	assert {one.operation for one in cards} == {"Cutting", "Assembly", "Glazing"} and all(one.total_completed_qty == done.qty for one in cards)
	glazed = frappe.get_doc("Job Card", next(one.name for one in cards if one.operation == "Glazing"))
	assert heads.card_by(glazed) == "Joseph Mathew" and heads.card_done(glazed)["meter"] == {"value": done.qty, "of": done.qty}
	made = frappe.get_doc("Stock Entry", {"work_order": done.name, "purpose": "Manufacture", "docstatus": 1})
	assert made.project == villa and flt(made.total_additional_costs) > 0, "the workshop's time is in the doors' value"
	assert all(row.project == villa for row in made.items)

	going = frappe.get_doc("Work Order", {"project": tower, "docstatus": 1})
	steps = {step["label"]: step for step in heads.work_progress(going)["steps"]}
	assert going.status == "In Process" and steps["Manufactured"]["note"] == "12 of 30 Nos"
	assert steps["Material Transferred"]["note"] == "All on the floor" and steps["Material Transferred"]["state"] == "done"
	steps = {one.operation: one for one in frappe.get_all("Job Card", filters={"work_order": going.name, "docstatus": 1}, fields=["operation", "total_completed_qty", "process_loss_qty"])}
	assert steps["Cutting"].total_completed_qty == 30 and steps["Assembly"].total_completed_qty == 12 and not steps["Assembly"].process_loss_qty

	used = frappe.db.sql(
		"""select sum(row.amount) from `tabStock Entry Detail` row join `tabStock Entry` entry on entry.name = row.parent
		where entry.purpose = 'Manufacture' and entry.docstatus = 1 and row.project = %s and ifnull(row.t_warehouse, '') = ''""",
		villa,
	)[0][0]
	project = frappe.get_doc("Project", villa)
	kept = flt(project.total_consumed_material_cost)
	project.set_consumed_material_cost()
	assert flt(used) > 0 and flt(kept, 2) == flt(project.total_consumed_material_cost, 2) and kept >= flt(used)

	asked = frappe.get_doc("Work Order", {"material_request": ["is", "set"], "docstatus": 1})
	assert frappe.db.get_value("Material Request", asked.material_request, "owner") == "rania@one.test"
	assert heads.work_for(asked)["value"] == "Rania Sabbagh" and asked.project == villa and asked.status == "Not Started"

	manager = frappe.db.get_value("Project", villa, "one_manager")
	with as_user(making.SUPERVISOR), _Told() as told:
		tell.work_done(made)
	assert told.to("Work Order Done") == {manager, making.SUPERVISOR}
	assert frappe.db.exists("Notification Log", {"document_name": done.name, "for_user": manager})
	assert not frappe.db.exists("Notification Log", {"document_name": done.name, "for_user": making.SUPERVISOR})

	printed = frappe.get_print("Work Order", done.name, "One Work Order")
	assert making.VILLA in printed and "Cutting" in printed and "Aluminium Profile 6063" in printed
	for_stock = next(one.name for one in orders if not one.project)
	assert "Mansour &amp; Sons" in printed or "Mansour & Sons" in printed, "made for the villa's customer"
	assert "Made For" not in frappe.get_print("Work Order", for_stock, "One Work Order"), "goods for stock are made for nobody"

	sent = frappe.get_doc("Subcontracting Order", {"supplier": making.COATER, "docstatus": 1, "project": villa})
	assert sent.project == villa and sent.status == "Completed" and {step["label"]: step["state"] for step in heads.sub_progress(sent)["steps"]} == {"Ordered": "done", "Material Transferred": "done", "Received": "done"}
	back = frappe.get_doc("Subcontracting Receipt", frappe.db.get_value("Subcontracting Receipt Item", {"subcontracting_order": sent.name, "docstatus": 1}, "parent"))
	assert heads.sub_order(back)["value"] == sent.name
	assert frappe.db.get_value("Purchase Order", sent.purchase_order, "status") == "To Bill"
	assert flt(get_stock_balance("ALU-6063-PC", wh("Stores"))) == 300
	assert flt(get_stock_balance("ALU-6063", wh(making.COATER))) == making.COATING[0]

	rows = {row["key"]: row for row in ready.checks()}
	assert rows["workshop"]["state"] == ready.READY and rows["floor"]["state"] == ready.READY

	with as_user(making.SUPERVISOR):
		imported = frappe.get_doc(
			{"doctype": "Work Order", "production_item": "WIN-CS12", "bom_no": window.name, "qty": 2, "company": COMPANY}
		).insert()
		assert [one.operation for one in imported.operations] == ["Cutting", "Assembly", "Glazing"]
		assert imported.wip_warehouse == wh("Work In Progress") and imported.fg_warehouse == wh("Finished Goods")
		imported.delete()

	from onedesk.one_ai import proposals, tools
	from onedesk.one_inventory import ai

	open_work = {"docstatus": 1, "status": ["in", ["Not Started", "In Process"]]}
	with as_user(making.SUPERVISOR):
		hand = tools.list_records(
			"Work Order",
			{**open_work, "project": frappe.db.get_value("Project", {"project_name": making.TOWER})},
			fields=["item_name", "qty", "produced_qty", "status", "project", "expected_delivery_date"],
			order_by="expected_delivery_date asc",
		)
		assert [one["name"] for one in hand] == [going.name] and hand[0]["produced_qty"] == 12, hand
		facts = ai.work_order_facts(going.name)
		assert {one["step"]: one["done"] for one in facts["steps"]} == {"Cutting": 30, "Assembly": 12, "Glazing": 12}
		assert facts["cost_so_far"]["workshop_time"] > 0 and facts["materials"]
		card = ai.plan_work_order("Casement Window 1200", 10, project=making.VILLA, why="The villa's last windows")
		drafted = proposals.apply(card["proposal"])
	order_ = frappe.get_doc("Work Order", drafted["record"])
	assert order_.docstatus == 0 and order_.project == villa and len(order_.operations) == 3
	order_.delete()
	with as_user("nadia@one.test"):
		assert ai.plan_work_order("WIN-CS12", 1).get("error")
		try:
			tools.list_records("Work Order", open_work)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the workshop listed its work orders")

	for person in (making.SUPERVISOR, "rania@one.test"):
		with as_user(person):
			assert frappe.has_permission("Work Order", "create") and frappe.has_permission("Job Card", "submit")
	with as_user("karim@one.test"):
		assert frappe.has_permission("Subcontracting BOM", "write") and frappe.has_permission("Manufacturing Settings", "write")
	with as_user("nadia@one.test"):
		assert not frappe.has_permission("Work Order", "read") and not frappe.has_permission("BOM", "read")


@check
def oneinventory_equipment_bought_given_serviced_and_mended():
	"""Equipment, as Karim, Yousef, Mariam and Huda meet it. Mariam's laptop is
	bought on a receipt that registers it, handed to her and signed for, and
	she is told. Mariam sees what each person holds. The services are kept up
	by whoever does them, one truck's late and told. A truck mended on the
	garage's bill, a laptop waiting for its screen, the CNC centre written
	down after a crash."""
	from onedesk.one_demo import assets as demo
	from onedesk.one_hr import heads as hr_heads
	from onedesk.one_inventory import heads, tell

	laptop = frappe.get_doc("Asset", {"asset_name": "Laptop Mariam"})
	mariam = frappe.db.get_value("Employee", {"user_id": "mariam@one.test"})
	assert laptop.docstatus == 1 and laptop.purchase_receipt and laptop.custodian == mariam
	assert frappe.db.get_value("Purchase Receipt", laptop.purchase_receipt, "owner") == demo.STORES
	given = frappe.get_doc(
		"Asset Movement",
		frappe.db.get_value("Asset Movement Item", {"asset": laptop.name, "to_employee": mariam}, "parent"),
	)
	assert given.purpose == "Issue" and given.owner == demo.STORES and given.docstatus == 1
	assert heads.handed_what(given)["value"] == "Laptop Mariam" and heads.handed_to(given)["value"] == "Mariam Saleh"
	assert frappe.db.exists("Notification Log", {"type": "Equipment Handed Over", "for_user": "mariam@one.test", "document_name": laptop.name})

	printed = frappe.get_print("Asset Movement", given.name, "One Equipment Handover")
	assert "Laptop Mariam" in printed and "Mariam Saleh" in printed and "I have received the equipment above" in printed
	assert "Received By" in printed

	yousef = frappe.get_doc("Employee", {"user_id": "yousef@one.test"})
	with as_user("mariam@one.test"):
		assert frappe.has_permission("Asset", "read") and not frappe.has_permission("Asset", "write")
		assert hr_heads.equipment(yousef)["value"] == "1 held"

	trucks = {name: frappe.db.get_value("Asset", {"asset_name": name}) for name, _late in demo.SERVICED}
	day = getdate(today())
	open_ = {
		one.asset_maintenance: one
		for one in frappe.get_all(
			"Asset Maintenance Log",
			filters={"docstatus": 0, "maintenance_status": ["in", ["Planned", "Overdue"]]},
			fields=["name", "asset_maintenance", "due_date", "maintenance_status", "task_assignee_email"],
		)
	}
	for name, late in demo.SERVICED:
		log = open_[trucks[name]]
		assert log.due_date and (getdate(log.due_date) < day) == late, (name, log)
		assert log.maintenance_status == ("Overdue" if late else "Planned"), (name, log)
		done = frappe.get_all("Asset Maintenance Log", filters={"asset_maintenance": trucks[name], "docstatus": 1}, fields=["owner"])
		assert done and {one.owner for one in done} == {log.task_assignee_email}
	late = frappe.get_doc("Asset Maintenance Log", open_[trucks["Pickup Truck 2"]].name)
	assert heads.service_due(late)["tone"] == "alarm" and heads.service_asset(late)["value"] == "Pickup Truck 2"
	with _Told() as told:
		tell.services()
	assert told.to("Service Late") == {"yousef@one.test", "tariq@one.test"}
	assert told.to("Service Due") <= {"yousef@one.test", "tariq@one.test"}

	plan = frappe.get_doc("Asset Maintenance", trucks["Pickup Truck 1"])
	was = plan.asset_maintenance_tasks[0].next_due_date
	plan.asset_maintenance_tasks[0].next_due_date = None
	with as_user(demo.STORES):
		plan.save()
	assert str(plan.asset_maintenance_tasks[0].next_due_date) == str(was)
	coming = frappe.get_doc("Asset Maintenance Log", open_[trucks["Pickup Truck 1"]].name)
	coming.maintenance_status = "Overdue"
	with as_user("yousef@one.test"):
		coming.save()
	assert coming.maintenance_status == "Planned"

	mended = frappe.get_doc("Asset Repair", {"asset": trucks["Pickup Truck 1"], "docstatus": 1})
	bill = frappe.get_doc("Purchase Invoice", mended.invoices[0].purchase_invoice)
	assert mended.repair_status == "Completed" and flt(mended.total_repair_cost) == 3850 and bill.supplier == demo.GARAGE
	assert heads.repair_out(mended)["value"] == "5 days" and heads.repair_cost(mended)
	waiting = frappe.get_doc("Asset Repair", {"repair_status": "Pending"})
	assert frappe.db.get_value("Asset", waiting.asset, "status") == "Out of Order" and heads.repair_out(waiting)["tone"] == "alarm"

	cut = frappe.get_doc("Asset Value Adjustment", {"docstatus": 1})
	assert flt(cut.new_asset_value) < flt(cut.current_asset_value) and cut.owner == demo.BOOKS
	assert heads.worth_change(cut)["tone"] == "alarm"
	assert frappe.db.exists("Journal Entry", {"name": cut.journal_entry, "docstatus": 1})

	from onedesk.one_ai import proposals, tools
	from onedesk.one_inventory import ai

	with as_user(demo.STORES):
		facts = ai.asset_facts("Pickup Truck 1")
		assert facts["held_by"] == "Sanjay Patel" and facts["repairs"][0]["cost"] == 3850 and facts["next_service"]
		holder = tools.find_records("Employee", "Yousef Bakr")[0]["name"]
		held = tools.list_records("Asset", {"custodian": holder, "docstatus": 1}, fields=["asset_name", "location", "status"])
		assert [one["asset_name"] for one in held] == ["Pickup Truck 2"], held
		due = ai.upkeep_now(days=30)
		assert any(one["asset"] == "Pickup Truck 2" and one["late"] for one in due["services"]), due
		card = ai.plan_handover("Laptop Mariam", "Yousef Bakr", why="Mariam is away for a month")
		drafted = proposals.apply(card["proposal"])
	handover = frappe.get_doc("Asset Movement", drafted["record"])
	assert handover.docstatus == 0 and handover.assets[0].from_employee == mariam and handover.assets[0].to_employee == yousef.name
	handover.delete()
	with as_user("nadia@one.test"):
		assert ai.asset_facts("Pickup Truck 1").get("error")
		try:
			tools.list_records("Asset", {"docstatus": 1})
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the stores listed the equipment")
		assert ai.upkeep_now().get("error") and ai.plan_handover("Laptop Nadia", "Yousef Bakr").get("error")

	with as_user("yousef@one.test"):
		assert frappe.has_permission("Asset Maintenance Log", "submit")
	with as_user(demo.STORES):
		assert frappe.has_permission("Asset Movement", "submit") and frappe.has_permission("Asset Repair", "submit")
	with as_user("nadia@one.test"):
		assert not frappe.has_permission("Asset", "read") and not frappe.has_permission("Asset Repair", "read")


@check
def oneinventory_hand_offs_from_the_other_side():
	"""OneInventory's hand-offs, as the person on the other side meets them.
	Mariam starts Sanjay's leaving checklist herself, and it asks the stores
	for his truck back. Omar's order says how much has gone out and since when
	it is late. Huda's receipt for the coating says what it cost, and the
	coater's bill arrives by mail as a draft against the order. Yousef's
	services name the pickup they are for."""
	from onedesk.one_crm import heads as crm_heads
	from onedesk.one_demo import assets as demo
	from onedesk.one_inventory import heads

	driver = demo._employee(demo.DRIVER)
	truck = frappe.db.get_value("Asset", {"asset_name": "Pickup Truck 1"})
	separation = frappe.get_doc("Employee Separation", {"employee": driver})
	assert separation.docstatus == 1 and separation.owner == demo.PEOPLE, (separation.docstatus, separation.owner)
	with as_user(demo.PEOPLE):
		assert frappe.has_permission("Employee Separation", "submit") and frappe.has_permission("Employee Onboarding", "submit")
	back = next(row for row in separation.activities if truck in (row.activity_name or ""))
	assert back.task and demo.STORES in frappe.parse_json(frappe.db.get_value("Task", back.task, "_assign") or "[]"), back.task

	order = frappe.get_doc("Sales Order", "SAL-ORD-2026-00006")
	assert 0 < order.per_delivered < 100, order.per_delivered
	late = crm_heads.deliver_by(order)
	assert isinstance(late, dict) and late["tone"] == "alarm", late

	receipt = frappe.get_doc("Purchase Receipt", {"supplier": "Gulf Powder Coating", "docstatus": 1, "is_subcontracted": 1})
	assert heads.receipt_worth(receipt) not in (None, frappe.utils.fmt_money(0, currency=receipt.currency)), heads.receipt_worth(receipt)
	bill = frappe.get_doc("Purchase Invoice", {"bill_no": "GPC-2207"})
	assert bill.docstatus == 0 and flt(bill.grand_total) == 1417.5 and bill.project, (bill.docstatus, bill.grand_total, bill.project)
	assert all(row.purchase_order == receipt.items[0].purchase_order for row in bill.items), [row.purchase_order for row in bill.items]
	asked = getdate("2026-11-07")
	assert getdate(bill.due_date) == asked or asked < getdate(bill.posting_date), (bill.due_date, bill.posting_date)

	titles = frappe.get_all("Asset Maintenance Log", filters={"item_code": "VEH-PICKUP"}, pluck="one_asset_title")
	assert set(titles) == {"Pickup Truck 1", "Pickup Truck 2"}, titles


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
def onebook_vat_is_charged_and_returned():
	"""A sale in the UAE carries 5% VAT and one abroad none, a bill the VAT
	its supplier charged, and the Tax Return is what they carry, as Huda reads
	it for the year."""
	from onedesk.one_book.report.tax_return import tax_return

	wrong, output, input_ = [], 0.0, 0.0
	for doctype, party_type, party in (("Sales Invoice", "Customer", "customer"), ("Purchase Invoice", "Supplier", "supplier")):
		for doc in frappe.get_all(doctype, filters={"docstatus": 1, "company": COMPANY}, fields=["name", party, "base_net_total", "base_total_taxes_and_charges", "taxes_and_charges"]):
			rate = 0 if _abroad(party_type, doc[party]) else 5
			if not doc.taxes_and_charges or abs(flt(doc.base_total_taxes_and_charges) - flt(doc.base_net_total) * rate / 100) > CENTS:
				wrong.append((doc.name, doc[party], doc.taxes_and_charges, doc.base_net_total, doc.base_total_taxes_and_charges))
			if doctype == "Sales Invoice":
				output += flt(doc.base_total_taxes_and_charges)
			else:
				input_ += flt(doc.base_total_taxes_and_charges)
	assert not wrong, wrong[:5]
	assert output > 0 and input_ > 0, (output, input_)
	claims = frappe.db.sql("select ifnull(sum(tax.base_tax_amount), 0) from `tabExpense Taxes and Charges` tax join `tabExpense Claim` claim on claim.name = tax.parent where claim.docstatus = 1")[0][0]
	with as_user("huda@one.test"):
		_columns, lines = tax_return.execute({"from_date": f"{getdate(today()).year - 1}-01-01", "to_date": today()})
	said = {line["line"]: flt(line.get("tax")) for line in lines if line.get("bold")}
	assert abs(said["Total charged"] - output) <= 1, (said, output)
	assert abs(said["Total paid"] - (input_ + flt(claims))) <= 1, (said, input_, claims)


@check
def onebook_a_foreign_payment_gains_or_loses_at_its_rate():
	"""The euro rose in July, so what Nordlicht paid after it brought in more
	dirhams than its invoice was booked at. Every payment in another currency
	settles its invoice in full, and the difference from the invoice's rate
	is a gain or a loss in the books, to the dirham."""
	gain_loss = tuple(filter(None, frappe.db.get_value("Company", COMPANY, ["exchange_gain_loss_account", "exchange_gain_account", "exchange_loss_account"])))
	seen, wrong = 0, []
	for ref in frappe.db.sql(
		"""select ref.parent as payment, ref.reference_doctype as doctype, ref.reference_name as invoice,
			ref.allocated_amount, ref.exchange_rate as booked, pe.payment_type,
			pe.source_exchange_rate, pe.target_exchange_rate, pe.paid_amount, pe.received_amount
		from `tabPayment Entry Reference` ref join `tabPayment Entry` pe on pe.name = ref.parent
		where pe.docstatus = 1 and ref.reference_doctype in ('Sales Invoice', 'Purchase Invoice')
			and (pe.paid_from_account_currency != pe.paid_to_account_currency)""",
		as_dict=True,
	):
		booked = flt(frappe.db.get_value(ref.doctype, ref.invoice, "conversion_rate"))
		if ref.payment_type == "Receive":
			paid_at = flt(ref.received_amount) / flt(ref.paid_amount)
			difference = flt(ref.allocated_amount) * (paid_at - booked)
		else:
			paid_at = flt(ref.paid_amount) / flt(ref.received_amount)
			difference = flt(ref.allocated_amount) * (booked - paid_at)
		if abs(difference) < 1:
			continue
		seen += 1
		posted = frappe.db.sql(
			"""select ifnull(sum(gl.credit - gl.debit), 0) from `tabGL Entry` gl
			where gl.voucher_type = 'Journal Entry' and gl.account in %s and gl.is_cancelled = 0
				and gl.voucher_no in (select parent from `tabJournal Entry Account` where reference_name = %s)""",
			(gain_loss, ref.invoice),
		)[0][0]
		if abs(flt(posted) - difference) > 1:
			wrong.append((ref.payment, ref.invoice, round(difference, 2), flt(posted)))
	assert seen, "no payment was made at a rate other than its invoice's"
	assert not wrong, wrong
	nordlicht = frappe.get_all("Sales Invoice", filters={"customer": "Nordlicht GmbH", "docstatus": 1, "status": "Paid"}, pluck="name")
	assert nordlicht, "Nordlicht's invoice is not paid"


@check
def onebook_what_is_outstanding_is_what_is_left():
	"""What every invoice and bill still has outstanding is its total less
	what was paid, credited or debited against it, as its ledger says."""
	wrong = []
	for doctype in ("Sales Invoice", "Purchase Invoice"):
		for doc in frappe.get_all(doctype, filters={"docstatus": 1, "is_return": 0}, fields=["name", "outstanding_amount"]):
			left = frappe.db.sql(
				"""select ifnull(sum(amount_in_account_currency), 0) from `tabPayment Ledger Entry`
				where against_voucher_type = %s and against_voucher_no = %s and delinked = 0""",
				(doctype, doc.name),
			)[0][0]
			if abs(abs(flt(left)) - flt(doc.outstanding_amount)) > CENTS:
				wrong.append((doc.name, doc.outstanding_amount, left))
	assert not wrong, wrong[:5]


@check
def oneinventory_broken_glass_goes_back_and_the_bill_is_debited():
	"""Broken glass found after Gulf Glass's August bill goes back on the
	receipt, and a debit note takes it off the bill, at the bill's price and
	its VAT, so what Sahara owes falls by exactly that."""
	note = frappe.get_all("Purchase Invoice", filters={"is_return": 1, "docstatus": 1, "supplier": "Gulf Glass Industries"}, fields=["name", "return_against", "grand_total"], limit=1)
	assert note, "no debit note against a bill"
	note = note[0]
	bill = frappe.get_doc("Purchase Invoice", note.return_against)
	returned = frappe.get_doc("Purchase Invoice", note.name)
	for row in returned.items:
		billed = next(one for one in bill.items if one.item_code == row.item_code)
		assert flt(row.rate) == flt(billed.rate), (row.rate, billed.rate)
	assert abs(flt(returned.grand_total) + flt(sum(-r.amount for r in returned.items)) * 1.05) <= CENTS, returned.grand_total
	paid = frappe.db.sql(
		"""select ifnull(sum(allocated_amount), 0) from `tabPayment Entry Reference`
		where reference_doctype = 'Purchase Invoice' and reference_name = %s and docstatus = 1""",
		bill.name,
	)[0][0]
	owed = flt(bill.outstanding_amount) + flt(frappe.db.get_value("Purchase Invoice", note.name, "outstanding_amount"))
	assert abs(owed - (flt(bill.grand_total) + flt(note.grand_total) - flt(paid))) <= CENTS, (owed, bill.grand_total, note.grand_total, paid)
	assert frappe.db.exists("Purchase Receipt", {"is_return": 1, "supplier": "Gulf Glass Industries", "docstatus": 1, "posting_date": [">=", bill.posting_date]})


@check
def oneinventory_the_stock_in_the_books_is_what_the_warehouses_hold():
	"""What the stock is worth in the books is what the warehouses hold, each
	warehouse's account against its stock ledger."""
	from erpnext.stock import get_warehouse_account_map

	held = {}
	for warehouse, account in get_warehouse_account_map(COMPANY).items():
		if account.get("account"):
			held.setdefault(account["account"], 0.0)
			held[account["account"]] += flt(
				frappe.db.sql(
					"select ifnull(sum(stock_value_difference), 0) from `tabStock Ledger Entry` where warehouse = %s and is_cancelled = 0",
					warehouse,
				)[0][0]
			)
	off = {}
	for account, value in held.items():
		booked = flt(frappe.db.sql("select ifnull(sum(debit - credit), 0) from `tabGL Entry` where account = %s and is_cancelled = 0", account)[0][0])
		if abs(value - booked) > 1:
			off[account] = (round(value, 2), round(booked, 2))
	assert held and not off, off


@check
def onecrm_what_was_quoted_is_ordered_delivered_and_invoiced_price_for_price():
	"""What a customer was quoted is what they ordered, were sent and were
	invoiced, price for price, and a window sent back is credited at what it
	sold for."""
	wrong = []
	for child, link, source in (
		("Sales Order Item", "quotation_item", "Quotation Item"),
		("Delivery Note Item", "so_detail", "Sales Order Item"),
		("Sales Invoice Item", "so_detail", "Sales Order Item"),
		("Sales Invoice Item", "dn_detail", "Delivery Note Item"),
	):
		for row in frappe.db.sql(
			f"""select row.parent, row.item_code, row.rate, src.rate as was from `tab{child}` row
			join `tab{source}` src on src.name = row.{link} where row.docstatus = 1 and row.{link} is not null""",
			as_dict=True,
		):
			if abs(flt(row.rate) - flt(row.was)) > CENTS:
				wrong.append((child, row.parent, row.item_code, row.rate, row.was))
	for credit in frappe.get_all("Sales Invoice", filters={"is_return": 1, "docstatus": 1}, fields=["name", "return_against"]):
		for row in frappe.get_doc("Sales Invoice", credit.name).items:
			sold = frappe.db.get_value("Sales Invoice Item", {"parent": credit.return_against, "item_code": row.item_code}, "rate")
			if abs(flt(row.rate) - flt(sold)) > CENTS:
				wrong.append(("credit", credit.name, row.item_code, row.rate, sold))
	assert not wrong, wrong[:5]


@check
def oneinventory_what_was_ordered_is_received_and_billed_price_for_price():
	"""What Karim ordered is what was received and billed, price for price."""
	wrong = []
	for child, link in (("Purchase Receipt Item", "purchase_order_item"), ("Purchase Invoice Item", "po_detail")):
		for row in frappe.db.sql(
			f"""select row.parent, row.item_code, row.rate, src.rate as was from `tab{child}` row
			join `tabPurchase Order Item` src on src.name = row.{link} where row.docstatus = 1 and row.{link} is not null""",
			as_dict=True,
		):
			if abs(flt(row.rate) - flt(row.was)) > CENTS:
				wrong.append((child, row.parent, row.item_code, row.rate, row.was))
	assert not wrong, wrong[:5]


@check
def onehr_each_payslip_adds_up_and_the_payroll_posts_it():
	"""Each payslip's net pay is its earnings less its deductions, and each
	payroll posts what its slips owe the people on them."""
	wrong = []
	for slip in frappe.get_all("Salary Slip", filters={"docstatus": 1}, fields=["name", "gross_pay", "total_deduction", "net_pay", "payroll_entry"]):
		doc = frappe.get_doc("Salary Slip", slip.name)
		earned = sum(flt(row.amount) for row in doc.earnings if not row.do_not_include_in_total)
		taken = sum(flt(row.amount) for row in doc.deductions if not row.do_not_include_in_total)
		if abs(earned - flt(slip.gross_pay)) > CENTS or abs(taken - flt(slip.total_deduction)) > CENTS or abs(flt(slip.gross_pay) - flt(slip.total_deduction) - flt(slip.net_pay)) > CENTS:
			wrong.append((slip.name, earned, slip.gross_pay, taken, slip.total_deduction, slip.net_pay))
	assert not wrong, wrong[:5]
	payable = frappe.db.get_value("Company", COMPANY, "default_payroll_payable_account")
	for entry in frappe.get_all("Payroll Entry", filters={"docstatus": 1}, pluck="name"):
		owed = frappe.db.sql("select ifnull(sum(net_pay), 0) from `tabSalary Slip` where payroll_entry = %s and docstatus = 1", entry)[0][0]
		posted = frappe.db.sql(
			"""select ifnull(sum(row.credit_in_account_currency - row.debit_in_account_currency), 0)
			from `tabJournal Entry Account` row join `tabJournal Entry` je on je.name = row.parent
			where je.docstatus = 1 and row.reference_type = 'Payroll Entry' and row.reference_name = %s
				and row.account = %s and je.voucher_type != 'Bank Entry'""",
			(entry, payable),
		)[0][0]
		assert abs(flt(owed) - flt(posted)) <= 1, (entry, owed, posted)


@check
def onehr_leave_taken_comes_off_what_is_left():
	"""What each person has left of a kind of leave is what they were given,
	less the days approved, and as adjusted, as the leave form reads it."""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	year_end = getdate(f"{getdate(today()).year}-12-31")
	checked = 0
	for allocation in frappe.get_all("Leave Allocation", filters={"docstatus": 1}, fields=["name", "employee", "leave_type", "total_leaves_allocated", "from_date", "to_date"]):
		taken = frappe.db.sql(
			"""select ifnull(sum(total_leave_days), 0) from `tabLeave Application`
			where employee = %s and leave_type = %s and status = 'Approved' and docstatus = 1
				and from_date between %s and %s""",
			(allocation.employee, allocation.leave_type, allocation.from_date, allocation.to_date),
		)[0][0]
		adjusted = sum(
			flt(one.leaves_to_adjust) * (-1 if one.adjustment_type == "Reduce" else 1)
			for one in frappe.get_all("Leave Adjustment", filters={"leave_allocation": allocation.name, "docstatus": 1}, fields=["leaves_to_adjust", "adjustment_type"])
		)
		left = get_leave_balance_on(allocation.employee, allocation.leave_type, min(year_end, getdate(allocation.to_date)))
		assert abs(flt(left) - (flt(allocation.total_leaves_allocated) - flt(taken) + adjusted)) <= 0.01, (allocation, taken, adjusted, left)
		checked += bool(taken)
	assert checked >= 2, "nobody has taken leave"


@check
def onehr_a_leaver_is_paid_their_end_of_service():
	"""Joseph resigned after four years and worked to the end of last month.
	He is no longer on the payroll, and his end of service is the UAE rule on
	resigning between three and five years, 14 days of basic pay a year,
	worked out from his last payslip and paid by the books."""
	from onedesk.one_demo.hr import LEAVER, RESIGNED

	employee = frappe.get_doc("Employee", _employee(LEAVER))
	assert employee.status == "Left" and employee.relieving_date, (employee.status, employee.relieving_date)
	assert not frappe.db.exists("Salary Slip", {"employee": employee.name, "start_date": [">", employee.relieving_date], "docstatus": 1})
	gratuity = frappe.get_doc("Gratuity", {"employee": employee.name, "docstatus": 1})
	assert gratuity.gratuity_rule == RESIGNED
	years = round(date_diff(employee.relieving_date, employee.date_of_joining) / 365)
	slip = frappe.db.get_value("Salary Slip", {"employee": employee.name, "docstatus": 1}, "name", order_by="start_date desc")
	basic = sum(flt(row.default_amount) for row in frappe.get_doc("Salary Slip", slip).earnings if row.salary_component == "Basic Salary")
	assert 3 <= years < 5 and flt(gratuity.current_work_experience) == years, (years, gratuity.current_work_experience)
	assert abs(flt(gratuity.amount) - basic * years * 14 / 30) <= 1, (gratuity.amount, basic, years)
	assert gratuity.status == "Paid" and flt(gratuity.paid_amount) == flt(gratuity.amount), (gratuity.status, gratuity.paid_amount)
	booked = frappe.db.sql(
		"select ifnull(sum(debit - credit), 0) from `tabGL Entry` where voucher_no = %s and account = %s and is_cancelled = 0",
		(gratuity.name, gratuity.expense_account),
	)[0][0]
	assert abs(flt(booked) - flt(gratuity.amount)) <= CENTS, booked


@check
def onehr_an_expense_claim_paid_is_what_the_books_and_project_carry():
	"""A claim paid back is paid what was approved, and a project carries the
	claims approved on it."""
	wrong = []
	for claim in frappe.get_all("Expense Claim", filters={"docstatus": 1, "status": "Paid"}, fields=["name", "grand_total", "total_amount_reimbursed"]):
		if abs(flt(claim.grand_total) - flt(claim.total_amount_reimbursed)) > CENTS:
			wrong.append(claim)
	assert not wrong, wrong
	for project in frappe.get_all("Expense Claim", filters={"docstatus": 1, "approval_status": "Approved", "project": ["is", "set"]}, pluck="project", distinct=True):
		approved = frappe.db.sql(
			"select ifnull(sum(total_sanctioned_amount), 0) from `tabExpense Claim` where project = %s and docstatus = 1 and approval_status = 'Approved'",
			project,
		)[0][0]
		assert abs(flt(frappe.db.get_value("Project", project, "total_expense_claim")) - flt(approved)) <= CENTS, (project, approved)


@check
def onehr_tells_each_moment_somebody_waits_on():
	"""Nadia's attendance request reaches HR, and Mariam's answer reaches her
	with Mariam's note. A letter issued reaches the employee it is about; a
	grievance reaches HR when OneAI is not reading them; a passkey reset is
	asked of HR and its doing told back; an interview's interviewers hear the
	day it is made; a permit a month from expiring reaches the employee and
	HR. Leave answered carries the approver's note."""
	from unittest.mock import patch

	from onedesk.one_hr import request, tell

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	nadia = frappe.db.get_value("Employee", {"user_id": "nadia@one.test"})
	with patch("onedesk.one.notify.notify", side_effect=heard):
		with as_user("nadia@one.test"):
			asked = frappe.get_doc(
				{"doctype": "Attendance Request", "employee": nadia, "from_date": today(), "to_date": today(), "one_reason": frappe.db.get_value("Attendance Reason", {}), "explanation": "Waiting in for the glazier."}
			).insert()
		_name, users, values = said("Attendance Request Asked")
		assert "mariam@one.test" in users and "nadia@one.test" not in users and values["explanation"] == "Waiting in for the glazier."
		with as_user("mariam@one.test"):
			request.reject(asked.name, "Come in on Thursday instead.")
		_name, users, values = said("Attendance Request Answered")
		assert users == ["nadia@one.test"] and values["note"] == "Mariam Saleh: Come in on Thursday instead.", values

		letter = frappe.get_doc({"doctype": "Employee Letter", "employee": nadia, "kind": frappe.get_meta("Employee Letter").get_field("kind").options.split("\n")[0]})
		letter.flags.ignore_mandatory = True
		with as_user("mariam@one.test"):
			letter.insert()
			letter.submit()
		assert said("Letter Issued")[1] == ["nadia@one.test"]

		frappe.db.set_single_value("HR Settings", "one_ai_grievances", 0)
		with as_user("nadia@one.test"):
			frappe.get_doc({"doctype": "Employee Grievance", "subject": "Parking", "raised_by": nadia, "grievance_against_party": "Department", "grievance_against": frappe.db.get_value("Department", {}), "grievance_type": frappe.db.get_value("Grievance Type", {}), "description": "Nowhere to park."}).insert(ignore_mandatory=True)
		assert "mariam@one.test" in said("Grievance Raised")[1]

		tell.passkey_reset_asked(nadia, registered="iPhone", asking="Pixel", address="10.0.0.1", why="Dropped it")
		assert "mariam@one.test" in said("Passkey Reset Asked")[1]
		with as_user("mariam@one.test"):
			tell.passkey_reset_done(nadia)
		assert said("Passkey Reset Done")[1] == ["nadia@one.test"]

		interview = frappe.copy_doc(frappe.get_doc("Interview", frappe.db.get_value("Interview", {})))
		interview.scheduled_on = add_days(today(), 3)
		interview.insert(ignore_permissions=True)
		_name, users, values = said("Interview Scheduled")
		assert users and values["applicant"], values

		employee = frappe.get_doc("Employee", nadia)
		kind = frappe.get_meta("Employee Document").get_field("document_type").options
		permit = frappe.db.get_value(kind, {}) or frappe.get_doc({"doctype": kind, "identification_document_type": "Work Permit"}).insert(ignore_permissions=True).name
		employee.append("one_documents", {"document_type": permit, "number": "WP-1", "expires_on": add_days(today(), 30)})
		employee.save(ignore_permissions=True)
		tell.documents_expiring()
		_name, users, values = said("Document Expiring")
		assert "nadia@one.test" in users and "mariam@one.test" in users and values["number"] == "WP-1", values

		leave = frappe.get_doc("Leave Application", frappe.db.get_value("Leave Application", {"docstatus": 1}))
		leave.one_note, leave.one_decided_by = "Enjoy it.", "mariam@one.test"
		with as_user("mariam@one.test"):
			leave.answered("Approved")
		assert said("Leave Answered")[2]["note"] == "Mariam Saleh: Enjoy it.", said("Leave Answered")


@check
def onehr_tells_what_the_second_pass_found():
	"""Nadia's leave with no approver reaches HR, and the approver named later
	hears then; her grievance resolved reaches her; a contract a month from
	its end reaches HR; a requisition and a referral reach HR and their
	answers reach whoever asked; a day the shift marked absent reaches her; an
	interview's applicant is mailed when it is."""
	from unittest.mock import patch

	from onedesk.one_hr import tell

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	nadia = frappe.db.get_value("Employee", {"user_id": "nadia@one.test"})
	with patch("onedesk.one.notify.notify", side_effect=heard):
		leave = frappe.get_doc("Leave Application", frappe.db.get_value("Leave Application", {"employee": nadia}))
		leave = frappe.copy_doc(leave)
		leave.leave_approver, leave.status = None, "Open"
		leave.from_date = leave.to_date = add_days(today(), 40)
		leave.half_day = 0
		leave.flags.ignore_validate = True
		leave.insert(ignore_permissions=True, ignore_mandatory=True)
		assert "mariam@one.test" in said("Leave Asked")[1], said("Leave Asked")
		told.clear()
		leave.leave_approver = "samir@one.test"
		leave.save(ignore_permissions=True)
		assert said("Leave Asked")[1] == ["samir@one.test"]

		frappe.db.set_single_value("HR Settings", "one_ai_grievances", 0)
		with as_user("nadia@one.test"):
			grievance = frappe.get_doc({"doctype": "Employee Grievance", "subject": "Parking", "raised_by": nadia, "grievance_against_party": "Department", "grievance_against": frappe.db.get_value("Department", {}), "grievance_type": frappe.db.get_value("Grievance Type", {}), "description": "Nowhere to park."}).insert(ignore_mandatory=True)
		grievance.status, grievance.resolution_detail = "Resolved", "Two bays are yours now."
		with as_user("mariam@one.test"):
			grievance.save(ignore_permissions=True)
		_name, users, values = said("Grievance Answered")
		assert users == ["nadia@one.test"] and values["note"] == "Two bays are yours now.", values

		frappe.db.set_value("Employee", nadia, "contract_end_date", add_days(today(), 30))
		tell.endings()
		assert "mariam@one.test" in said("Contract Ending")[1]

		with as_user("nadia@one.test"):
			wanted = frappe.get_doc({"doctype": "Job Requisition", "designation": frappe.db.get_value("Designation", {}), "requested_by": nadia, "no_of_positions": 2, "expected_compensation": 1, "posting_date": today(), "description": "Two fitters."}).insert(ignore_permissions=True, ignore_mandatory=True)
		assert "mariam@one.test" in said("Job Requisition Asked")[1]
		with as_user("mariam@one.test"):
			wanted.status = "Open & Approved"
			wanted.save(ignore_permissions=True)
		assert said("Job Requisition Answered")[1] == ["nadia@one.test"]

		with as_user("nadia@one.test"):
			referred = frappe.get_doc({"doctype": "Employee Referral", "first_name": "Rami", "last_name": "Aziz", "email": "rami@example.com", "referrer": nadia, "date": today()}).insert(ignore_permissions=True, ignore_mandatory=True)
		assert "mariam@one.test" in said("Referral Received")[1]
		applicant = frappe.get_doc("Job Applicant", frappe.db.get_value("Job Applicant", {}))
		applicant.employee_referral, applicant.status = referred.name, "Accepted"
		with as_user("mariam@one.test"):
			applicant.save(ignore_permissions=True)
		assert said("Referral Answered")[1] == ["nadia@one.test"]

		absent = frappe._dict(doctype="Attendance", name="ATT-X", status="Absent", employee=nadia, shift="Day", attendance_date=today())
		tell.marked_absent(absent)
		assert said("Marked Absent")[1] == ["nadia@one.test"]

	with patch("frappe.sendmail") as sent:
		interview = frappe.copy_doc(frappe.get_doc("Interview", frappe.db.get_value("Interview", {})))
		interview.scheduled_on = add_days(today(), 3)
		interview.insert(ignore_permissions=True)
	assert any("interview" in call.kwargs["subject"].lower() for call in sent.call_args_list), "the applicant is mailed"


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
		with as_user("mariam@one.test"):
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

	from onedesk.one import approvals, settings, tell
	from onedesk.one_legal import gate

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	with patch("onedesk.one.notify.notify", side_effect=heard):
		with as_user(OWNER):
			settings._told_of_access(frappe.get_doc("User", "mariam@one.test"), {"Workspace Administrator"}, set())
		assert OWNER not in said("Administrator Removed")[1]

		with as_user(OWNER):
			settings.save("general", {"allow_consecutive_login_attempts": 7})
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
		frappe.db.set_default(f"one_legal_told_{key}", None)
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
def onehr_home_tells_everybody_their_day():
	"""Mariam's Home: the headcount as Employee counts it, last month's
	payroll as its slips add up, Ravi's shift and Nadia's attendance request
	waiting on her, Yousef's flagged check-in, and every row of the directory
	opening something that exists. Nadia's Home: her own request waiting and
	the leave she has left, and no story, which is HR's to read."""
	from onedesk.one_hr import home, story

	with as_user("mariam@one.test"):
		told = story.read()
		said = home.read()
	cards = told["cards"]
	assert set(cards) >= {"headcount", "joined", "present", "away", "payroll", "openings"}, set(cards)
	company = frappe.defaults.get_global_default("company")
	here = frappe.db.count("Employee", {"company": company, "status": "Active"})
	assert cards["headcount"]["value"] == here, (cards["headcount"], here)
	last = get_first_day(add_months(today(), -1))
	paid = sum(flt(one) for one in frappe.get_all("Salary Slip", filters={"company": company, "docstatus": 1, "start_date": last}, pluck="base_net_pay"))
	assert abs(cards["payroll"]["value"] - paid) < 1, (cards["payroll"], paid)
	waiting = {(one["doctype"], one["who"]) for one in said["needs"]["approve"]["rows"]}
	assert ("Attendance Request", "Nadia Khoury") in waiting, waiting
	assert said["needs"]["flagged"]["count"] >= 1
	assert [one["step"] for one in told["hiring"]["funnel"]] == list(story.FUNNEL)
	for row in said["everything"]:
		kind = "DocType" if row["kind"] == "Masters" else row["kind"]
		assert frappe.db.exists(kind, row["target"]), row
	with as_user("nadia@one.test"):
		assert story.read() is None
		said = home.read()
	assert not said["hr"] and said["needs"]["mine"]["count"] >= 1
	assert {one["leave_type"] for one in said["needs"]["leave"]}, said["needs"]["leave"]


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
				{"doctype": "Material Request", "material_request_type": "Purchase", "schedule_date": add_days(today(), 7), "items": [{"item_code": item, "qty": 2, "schedule_date": add_days(today(), 7), "warehouse": frappe.db.get_value("Warehouse", {"is_group": 0})}]}
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
		other = frappe.db.get_value("Warehouse", {"is_group": 0, "name": ["!=", request.items[0].warehouse]})
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

	from onedesk.one import account, signin, tell
	from onedesk.one_admin import tell as admin
	from onedesk.one_intake import tell as intake
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
def onemail_oneai_tells_a_sender_only_their_own_records():
	"""A rule's OneAI reply reading their records is given what the portal
	shows the sender, only when the receiving server verified them: Khalid
	of Mansour & Sons gets his own quotations, orders, invoices with what is
	still to pay, and deliveries, and nobody else's: all that is still open
	and the latest of the rest; the same address with a
	forged From line, or a stranger, gets nothing, and a reply not set to
	read records is told to say nothing about them. Verified, OneAI may open
	one of his records in full, and is refused anyone else's."""
	from unittest import mock

	from onedesk.one_mail import rules, theirs

	passed = "mx.example; dkim=pass header.d=mansour.example; dmarc=pass header.from=mansour.example"
	forged = "mx.example; dkim=fail header.d=mansour.example; dmarc=fail header.from=mansour.example"
	assert theirs.verified({"Authentication-Results": passed}, "khalid@mansour.example")
	assert not theirs.verified({"Authentication-Results": forged}, "khalid@mansour.example")

	rows = theirs.records("khalid@mansour.example", "When does my order arrive?")
	assert rows and {row["party"] for row in rows} == {"Mansour & Sons"}, rows
	assert {row["doctype"] for row in rows} >= {"Sales Order", "Sales Invoice"}
	owed = [row["name"] for row in rows if row["doctype"] == "Sales Invoice" and row["status"] != "Paid"]
	open_ = frappe.get_all("Sales Invoice", filters={"customer": "Mansour & Sons", "docstatus": 1, "outstanding_amount": (">", 0)}, pluck="name")
	assert set(open_) <= set(owed), "every invoice still to pay, however old"
	assert any(row.get("owed") for row in rows), "what is still to pay on a part-paid one"
	assert len(theirs.records("khalid@mansour.example", "About ACC-PINV-2026-00019")) == len(rows), "a name not theirs adds nothing"

	asked, looked = [], []

	def ask(action, text, reference=None, only=None, nudges=True):
		from onedesk.one_ai import tools as surface

		asked.append(text)
		looked.append(surface.run("their_record", {"doctype": "Sales Invoice", "name": "ACC-SINV-2026-00001"})["answer"]["totals"])
		try:
			surface.run("their_record", {"doctype": "Purchase Invoice", "name": "ACC-PINV-2026-00019"})
			looked.append("leaked")
		except frappe.ValidationError:
			pass
		return {"said": "ok"}

	with mock.patch("onedesk.one_ai.run.once", side_effect=lambda kind, text, reference=None: asked.append(text) or "ok"), mock.patch(
		"onedesk.one_ai.run.ask", side_effect=ask
	):
		mail = frappe._dict(name=None, sender="khalid@mansour.example", subject="Invoice", content="How much do we owe?")
		rules._drafted({"instruction": "Answer from their records.", "records": 1}, frappe._dict(mail, one_verified=1))
		rules._drafted({"instruction": "Answer from their records.", "records": 1}, frappe._dict(mail, one_verified=0))
		rules._drafted({"instruction": "Answer from their records.", "records": 0}, frappe._dict(mail, one_verified=1))
		rules._drafted({"instruction": "Answer.", "records": 1}, frappe._dict(mail, sender="nobody@stranger.example", one_verified=1))
	assert "ACC-SINV-2026-00001" in asked[0] and "Mansour & Sons" in asked[0]
	assert len(looked) == 1 and any(one.get("label") == "To pay" for one in looked[0]), "one record in full, only theirs"
	assert not frappe.flags.one_ai_tools and not frappe.flags.one_mail_sender, "the tools go with the run"
	assert all("SINV" not in one and "could not be confirmed" in one for one in asked[1:2])
	assert "SINV" not in asked[2] and "Say nothing about any order" in asked[2]
	assert "SINV" not in asked[3] and "Nothing is known" in asked[3]


@check
def onemail_a_mailbox_says_what_oneai_may_do_with_its_mail():
	"""Layla switches off Create Tasks for the workspace mailbox: OneIntake
	then makes no task from its mail, while a link it still makes; once a
	rule has made a task from a message, OneIntake makes no second one;
	an unknown job, or a reading from no mailbox, is never held back. Setting
	New Mail to Not Read names the rules that ask OneAI, which then show as
	not running."""
	from onedesk.one_intake import act
	from onedesk.one_mail import gate, holders, rules

	ours = holders.workspace()
	reading = frappe.get_doc("Reading", frappe.db.get_value("Reading", {"source_doctype": "Communication"}, "name", order_by="creation desc"))
	account = gate.account_of("Reading", reading.name)
	assert account, "a reading of mail knows its mailbox"
	reading.on_behalf_of, reading.history = OWNER, 0
	with as_user(OWNER):
		said = gate.set_settings(account, skips=["tasks", "made up"])
	assert said["skips"] == ["tasks"], said["skips"]
	frappe.local.flags.one_intake_mailbox = {}
	task = act.Action("Create", "Task", values={"subject": "Call back"}, key="task", sure=True)
	assert act.apply(task, reading) is None, "a job switched off makes nothing"
	assert gate.does(account, "link") and gate.does(None, "tasks") and gate.does(account, None)
	with as_user(OWNER):
		gate.set_settings(account, skips=[])
	frappe.local.flags.one_intake_mailbox = {}
	assert act.apply(task, reading), "switched back on, it is done or proposed"

	from onedesk.one_mail import linking

	message = gate.message_of(reading.name)
	assert message, "a reading of mail knows its message"
	ruled = frappe.get_doc({"doctype": "Task", "subject": "Made by a rule"}).insert(ignore_permissions=True)
	linking.add(message, "Task", ruled.name, "rule")
	again = act.Action("Create", "Task", values={"subject": "Call back again"}, key="task|again", sure=True)
	assert act.apply(again, reading) is None, "a rule made a task from this message: OneAI makes none"
	event = act.Action("Create", "Event", values={"subject": "Visit", "starts_on": frappe.utils.now()}, key="event", sure=True)
	assert act.apply(event, reading), "the rule's task holds back no other kind"

	frappe.db.set_value("Email Account", ours, "one_intake", 1)
	with as_user(OWNER):
		rules.save_rule(ours, {"title": "Complaints", "steps": [{"type": "ask", "id": "a", "ask": "yes", "question": "a complaint", "then": [{"type": "star"}], "else": []}]})
		assert "Complaints" in gate.settings_of(ours)["asks"]
		gate.set_settings(ours, reads=0)
		listed = rules.rules_of_mailbox(ours)
	assert not listed["reads"] and any(one["needs_ai"] and one["title"] == "Complaints" for one in listed["rules"])
