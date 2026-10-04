"""A project's budget by cost type: ERPNext's own Budget against the project.

A **cost type** is an expense account (labour, materials, subcontract,
equipment, or whatever accounts the workspace uses), and its budget is one
ERPNext **Budget** against the project for that account, submitted. ERPNext
then checks every purchase order and every expense booked on the project
against it, and warns or stops as the budget says (`Over Budget`).

- ERPNext checks orders and spending each on their own, and together when
  `applicable_on_cumulative_expense` is set, which a cost type always is:
  an order is over budget when it, the open orders and what's spent come to
  more than the budget.
- **Cost Types** on the Costing tab lists each one: its budget, what's
  committed on supplier orders not yet billed, what's been spent (the
  general ledger), and what's left (`lines`).
- **Add Cost Type** and changing one (`set_budget`) are ERPNext's own: a new
  Budget, or the old one revised as ERPNext's Revise Budget does it,
  cancelled and copied with the new amount. Removing one cancels it.
- The project's **Budget** is then the cost types added up (`sync`), so the
  forecast and the head read the same number.
- Making a budget is for whoever ERPNext lets make one (Accounts Manager);
  everybody who sees the project sees the cost types.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate, nowdate

from onedesk.one_project import money, tree

#: What happens when an order or an expense would go over a cost type's budget.
ACTIONS = ("Warn", "Stop")


def left(budget: float, committed: float, spent: float) -> float:
	"""What's left of a cost type's budget. Negative once it's over. Pure."""
	return flt(budget) - flt(committed) - flt(spent)


def _budgets(project: str) -> list:
	return frappe.get_all(
		"Budget",
		filters={"budget_against": "Project", "project": project, "docstatus": 1},
		fields=["name", "account", "budget_amount", "action_if_annual_budget_exceeded_on_po"],
		order_by="account asc",
	)


@frappe.whitelist()
@frappe.read_only()
def lines(project: Annotated[str, "The project."]) -> dict:
	"""Each cost type: budget, committed, spent and left."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	budgets = _budgets(project)
	accounts = [one.account for one in budgets]
	committed = _committed(project, accounts)
	spent = _spent(project, accounts)
	names = dict(
		frappe.get_all(
			"Account", filters={"name": ["in", accounts]}, fields=["name", "account_name"], as_list=True
		)
	)
	return {
		"can_set": bool(frappe.has_permission("Budget", "create")),
		"lines": [
			{
				"account": one.account,
				"cost_type": names.get(one.account) or one.account,
				"budget": flt(one.budget_amount),
				"committed": committed.get(one.account, 0.0),
				"spent": spent.get(one.account, 0.0),
				"left": left(one.budget_amount, committed.get(one.account), spent.get(one.account)),
				"action": one.action_if_annual_budget_exceeded_on_po or "Warn",
			}
			for one in budgets
		],
	}


def _committed(project: str, accounts: list[str]) -> dict:
	"""What suppliers still have to bill on the project's orders, by account."""
	if not accounts:
		return {}
	item = frappe.qb.DocType("Purchase Order Item")
	po = frappe.qb.DocType("Purchase Order")
	rows = (
		frappe.qb.from_(item)
		.join(po)
		.on(item.parent == po.name)
		.select(item.expense_account, item.amount, item.billed_amt, item.base_net_amount)
		.where(
			(item.project == project)
			& item.expense_account.isin(accounts)
			& (po.docstatus == 1)
			& (po.status != "Closed")
		)
		.run(as_dict=True)
	)
	found: dict = {}
	for row in rows:
		found[row.expense_account] = found.get(row.expense_account, 0.0) + money.unbilled([row])
	return found


def _spent(project: str, accounts: list[str]) -> dict:
	"""What's been booked to each account on the project: the ledger."""
	if not accounts:
		return {}
	gl = frappe.qb.DocType("GL Entry")
	rows = (
		frappe.qb.from_(gl)
		.select(gl.account, (Sum(gl.debit) - Sum(gl.credit)).as_("spent"))
		.where((gl.project == project) & gl.account.isin(accounts) & (gl.is_cancelled == 0))
		.groupby(gl.account)
		.run(as_dict=True)
	)
	return {row.account: flt(row.spent) for row in rows}


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
				# Orders and spending together, which is what a cost type's
				# budget is for; ERPNext's other checks take each alone.
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
	sync(project)
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
	sync(project)
	return lines(project)


def sync(project: str) -> None:
	"""The project's Budget is its cost types added up, when it has any."""
	budgets = _budgets(project)
	if budgets:
		frappe.db.set_value(
			"Project", project, "estimated_costing", sum(flt(one.budget_amount) for one in budgets)
		)
		tree.forget()


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
