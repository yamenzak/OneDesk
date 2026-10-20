"""A project's budget by cost type: ERPNext's own Budget against the project."""

from typing import Annotated

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate, nowdate

from onedesk.one_project import money, tree

ACTIONS = ("Warn", "Stop")


def left(budget: float, committed: float, spent: float) -> float:
	"""What's left of a cost type's budget. Negative once it's over. Pure."""
	return flt(budget) - flt(committed) - flt(spent)


def _budgets(project: str) -> list:
	return frappe.get_all(
		"Budget",
		filters={"budget_against": "Project", "project": project, "docstatus": 1},
		fields=["name", "owner", "account", "budget_amount", "action_if_annual_budget_exceeded_on_po"],
		order_by="account asc",
	)


@frappe.whitelist()
@frappe.read_only()
def lines(project: Annotated[str, "The project."]) -> dict:
	"""Each cost type over the project and those under it (money.py)."""
	return money.money(project)["cost_types"]


def types(project: str, projects: list[str]) -> list[dict]:
	"""Each cost type over the projects, with the project's own budget and
	its Over Budget where it has one."""
	found = across(projects)
	own = {one.account: one for one in _budgets(project)}
	for one in found:
		mine = own.get(one["account"])
		one["own"] = flt(mine.budget_amount) if mine else None
		one["action"] = (mine.action_if_annual_budget_exceeded_on_po or "Warn") if mine else "Warn"
	return found


def _lines(project: str) -> list[dict]:
	budgets = _budgets(project)
	accounts = [one.account for one in budgets]
	committed = _committed([project], accounts)
	spent = _spent([project], accounts)
	names = dict(
		frappe.get_all(
			"Account", filters={"name": ["in", accounts]}, fields=["name", "account_name"], as_list=True
		)
	)
	return [
		{
			"account": one.account,
			"cost_type": names.get(one.account) or one.account,
			"budget": flt(one.budget_amount),
			"committed": committed.get(one.account, 0.0),
			"spent": spent.get(one.account, 0.0),
			"left": left(one.budget_amount, committed.get(one.account), spent.get(one.account)),
			"action": one.action_if_annual_budget_exceeded_on_po or "Warn",
			"budget_name": one.name,
			"set_by": one.owner,
		}
		for one in budgets
	]


def across(projects: list[str]) -> list[dict]:
	"""Each cost type over the projects, a project and those under it: the
	budgets for the same account added up, with what's committed, spent and
	left of them. A cost type counts what's spent and ordered only on the
	projects that budget for it, as ERPNext checks each project's own; the
	rest is Other's."""
	budgets = frappe.get_all(
		"Budget",
		filters={"budget_against": "Project", "project": ["in", projects], "docstatus": 1},
		fields=["project", "account", "budget_amount"],
	)
	if not budgets:
		return []
	accounts = sorted({one.account for one in budgets})
	committed = _committed(projects, accounts, by_project=True)
	spent = _spent(projects, accounts, by_project=True)
	found: dict = {}
	for one in budgets:
		line = found.setdefault(one.account, {"budget": 0.0, "committed": 0.0, "spent": 0.0})
		line["budget"] += flt(one.budget_amount)
		line["committed"] += committed.get((one.project, one.account), 0.0)
		line["spent"] += spent.get((one.project, one.account), 0.0)
	names = dict(
		frappe.get_all(
			"Account", filters={"name": ["in", accounts]}, fields=["name", "account_name"], as_list=True
		)
	)
	return [
		{
			"account": account,
			"cost_type": names.get(account) or account,
			**line,
			"left": left(line["budget"], line["committed"], line["spent"]),
		}
		for account, line in sorted(found.items())
	]


def other(lines: list[dict], budget: float, spent: float, committed: float) -> dict | None:
	"""What the cost types leave out of the project's figures: budget not
	split into cost types, and cost booked or ordered outside them (time
	among it, which ERPNext doesn't book to an account). None when there's
	nothing. Pure."""
	rest = {
		"budget": max(0.0, flt(budget) - sum(one["budget"] for one in lines)),
		"spent": max(0.0, flt(spent) - sum(one["spent"] for one in lines)),
		"committed": max(0.0, flt(committed) - sum(one["committed"] for one in lines)),
	}
	if not any(value >= 1 for value in rest.values()):
		return None
	return {**rest, "left": left(rest["budget"], rest["committed"], rest["spent"])}


def _committed(projects: list[str], accounts: list[str], by_project: bool = False) -> dict:
	"""What suppliers still have to bill on the projects' orders, by account,
	or by project and account."""
	if not accounts:
		return {}
	item = frappe.qb.DocType("Purchase Order Item")
	po = frappe.qb.DocType("Purchase Order")
	rows = (
		frappe.qb.from_(item)
		.join(po)
		.on(item.parent == po.name)
		.select(item.project, item.expense_account, item.amount, item.billed_amt, item.base_net_amount)
		.where(
			item.project.isin(projects)
			& item.expense_account.isin(accounts)
			& (po.docstatus == 1)
			& (po.status != "Closed")
			& money._not_stocked(item)
		)
		.run(as_dict=True)
	)
	found: dict = {}
	for row in rows:
		key = (row.project, row.expense_account) if by_project else row.expense_account
		found[key] = found.get(key, 0.0) + money.unbilled([row])
	return found


def _spent(projects: list[str], accounts: list[str], by_project: bool = False) -> dict:
	"""What's been booked to each account on the projects, or to each
	project and account: the ledger."""
	if not accounts:
		return {}
	gl = frappe.qb.DocType("GL Entry")
	rows = (
		frappe.qb.from_(gl)
		.select(gl.project, gl.account, (Sum(gl.debit) - Sum(gl.credit)).as_("spent"))
		.where(gl.project.isin(projects) & gl.account.isin(accounts) & (gl.is_cancelled == 0))
		.groupby(gl.project, gl.account)
		.run(as_dict=True)
	)
	found: dict = {}
	for row in rows:
		key = (row.project, row.account) if by_project else row.account
		found[key] = found.get(key, 0.0) + flt(row.spent)
	return found


BOOKS = ("Accounts User", "Accounts Manager")


def kept_to_projects(doc, method=None) -> None:
	"""Budget validate: somebody who keeps budgets only as a project's manager
	sets them against a project, however the budget is made."""
	held = set(frappe.get_roles())
	if doc.budget_against != "Project" and "Projects Manager" in held and not held & set(BOOKS):
		frappe.throw(_("Only an accounts user sets a budget for a cost centre. Set this one against a project."))


@frappe.whitelist(methods=["POST"])
def set_budget(
	project: Annotated[str, "The project."],
	account: Annotated[str, "The expense account the cost type is."],
	amount: Annotated[float, "The budget for it."],
	action: Annotated[str, "Warn or Stop when an order or expense goes over."] = "Warn",
) -> dict:
	"""Add a cost type, or change one's budget, as ERPNext's own Budget."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	frappe.has_permission("Budget", "create", throw=True)
	if action not in ACTIONS:
		frappe.throw(_("Over Budget is Warn or Stop."))
	if flt(amount) <= 0:
		frappe.throw(_("Give the cost type a budget."))
	existing = next((one for one in _budgets(project) if one.account == account), None)
	if existing:
		old = frappe.get_doc("Budget", existing.name)
		old.cancel()
		new = frappe.copy_doc(old)
		new.revision_of = old.name
	else:
		new = frappe.new_doc("Budget")
		new.update(
			{
				"budget_against": "Project",
				"project": project,
				"company": _company(project),
				"account": account,
				"distribution_frequency": "Yearly",
				"distribute_equally": 1,
				"applicable_on_purchase_order": 1,
				"applicable_on_booking_actual_expenses": 1,
				"action_if_accumulated_monthly_budget_exceeded_on_po": "Ignore",
				"action_if_accumulated_monthly_budget_exceeded": "Ignore",
				"applicable_on_cumulative_expense": 1,
				"action_if_accumulated_monthly_exceeded_on_cumulative_expense": "Ignore",
				**_years(project),
			}
		)
	new.budget_amount = flt(amount)
	new.action_if_annual_budget_exceeded_on_po = action
	new.action_if_annual_budget_exceeded = action
	new.action_if_annual_exceeded_on_cumulative_expense = action
	new.insert()
	new.submit()
	return lines(project)


@frappe.whitelist(methods=["POST"])
def remove_budget(
	project: Annotated[str, "The project."], account: Annotated[str, "The cost type's account."]
) -> dict:
	"""Take a cost type off: its Budget is cancelled."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	frappe.has_permission("Budget", "cancel", throw=True)
	for one in _budgets(project):
		if one.account == account:
			frappe.get_doc("Budget", one.name).cancel()
	return lines(project)


def over(project: str) -> None:
	"""Tell the project's manager and whoever set it when a cost type's
	orders and spending pass its budget: once for each budget, so a revised
	budget can tell again (money.moved, after every submit)."""
	from onedesk.one_project import tell

	gone = [one for one in _lines(project) if one["left"] < 0]
	if not gone:
		return
	tell.over_budget(project, gone)


def sync(project: str) -> None:
	"""The project's Budget is its cost types added up, and its Time Budget,
	which no cost type can hold, when it has any."""
	budgets = _budgets(project)
	if budgets:
		time = flt(frappe.db.get_value("Project", project, "one_time_budget"))
		frappe.db.set_value(
			"Project", project, "estimated_costing", sum(flt(one.budget_amount) for one in budgets) + time
		)
		tree.forget()


def synced(doc, method=None) -> None:
	"""Budget on_submit and on_cancel: a project's Budget follows its cost
	types, however a budget is made or taken off (the page, ERPNext's form,
	an import)."""
	if doc.budget_against == "Project" and doc.project:
		sync(doc.project)


def summed(doc, method=None) -> None:
	"""Project validate: a project with cost types has their sum as its
	Budget, so a bulk edit of it does not part the two."""
	if doc.is_new():
		return
	budgets = _budgets(doc.name)
	if budgets:
		doc.estimated_costing = sum(flt(one.budget_amount) for one in budgets) + flt(doc.get("one_time_budget"))


def _company(project: str) -> str:
	return frappe.db.get_value("Project", project, "company") or frappe.defaults.get_global_default("company")


def _years(project: str) -> dict:
	"""From the fiscal year the project starts in (or this one) to the one it
	ends in, or the last there is."""
	start, end = frappe.db.get_value("Project", project, ["expected_start_date", "expected_end_date"])
	years = frappe.get_all(
		"Fiscal Year", fields=["name", "year_start_date", "year_end_date"], order_by="year_start_date asc"
	)
	if not years:
		frappe.throw(_("Set up a fiscal year in OneBook first."))

	def holding(day):
		day = getdate(day)
		return next((one.name for one in years if one.year_start_date <= day <= one.year_end_date), None)

	first = holding(start or nowdate()) or holding(nowdate()) or years[0].name
	last = holding(end) if end else None
	if not last or getdate(frappe.get_cached_value("Fiscal Year", last, "year_start_date")) < getdate(
		frappe.get_cached_value("Fiscal Year", first, "year_start_date")
	):
		last = years[-1].name
	return {"from_fiscal_year": first, "to_fiscal_year": last}


@frappe.whitelist(methods=["POST"])
def set_time(
	project: Annotated[str, "The project."],
	time_budget: Annotated[float, "What the team's own hours may cost."] = 0,
	hours: Annotated[float, "The hours planned, when its tasks plan none."] = 0,
	budget: Annotated[float | None, "The whole budget, for a project without cost types."] = None,
) -> None:
	"""The Budget dialog: the Time Budget and Planned Hours, and the Budget
	itself where no cost types add it up."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	doc.one_time_budget = flt(time_budget)
	doc.one_hours_planned = flt(hours)
	if budget is not None and not _budgets(project):
		doc.estimated_costing = flt(budget)
	doc.save()


@frappe.whitelist()
@frappe.read_only()
def booked(
	project: Annotated[str, "The project."], account: Annotated[str, "The cost type's account."]
) -> list[dict]:
	"""What was booked to a cost type on the project and those under it, the
	latest first: each bill, claim, stock issue or journal, and what it came to."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	projects = list(tree.scope(project))
	gl = frappe.qb.DocType("GL Entry")
	rows = (
		frappe.qb.from_(gl)
		.select(gl.voucher_type, gl.voucher_no, gl.posting_date, (Sum(gl.debit) - Sum(gl.credit)).as_("amount"))
		.where(gl.project.isin(projects) & (gl.account == account) & (gl.is_cancelled == 0))
		.groupby(gl.voucher_type, gl.voucher_no, gl.posting_date)
		.orderby(gl.posting_date, order=frappe.qb.desc)
		.limit(100)
		.run(as_dict=True)
	)
	return [
		{
			"doctype": one.voucher_type,
			"name": one.voucher_no,
			"date": str(one.posting_date),
			"amount": flt(one.amount),
			"open": bool(frappe.has_permission(one.voucher_type, "read", doc=one.voucher_no)),
		}
		for one in rows
		if flt(one.amount)
	]
