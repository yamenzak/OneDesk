"""OneAI on a payroll run: what changed against last month, before it is paid.

The comparing is done here, in plain code, and the model is handed the
differences rather than the slips: which amounts moved and by how much is
arithmetic, and a model asked to find them in two hundred slips misses some
and invents others. What the model adds is the sentence — "Rania's net is
down 1,800 because the housing allowance is missing" — and the order, most
money first.

Read as the person asking, so a slip they may not see is not compared: the
salary rules in `one_hr/money.py` apply here exactly as on the list.
"""

from typing import Annotated

import frappe
from frappe.utils import flt

#: A change this large, as a share of what it was, is worth a line.
SHARE = 0.10

#: And a change smaller than this is not, whatever its share — a 5 on a 20
#: deduction is 25% and nobody's problem.
LEAST = 50

#: The most flagged slips handed over. A run where more than this moved is a
#: run where something changed for everybody, and the first thirty say what.
MOST_FLAGGED = 30


def payroll_changes(
	payroll_entry: Annotated[str, "The payroll entry's id."] | None = None,
	salary_slip: Annotated[str, "One salary slip's id, to compare just that one."] | None = None,
) -> dict:
	"""What changed on each salary slip against the same person's last
	submitted slip: pay that moved, components added or dropped, days not
	paid, and people paid last time who are missing now. Explain each flag in
	a line, most money first; say plainly when nothing stands out."""
	if not payroll_entry and not salary_slip:
		return {"error": "Say which payroll entry or salary slip to check."}

	if salary_slip:
		slips = frappe.get_list("Salary Slip", filters={"name": salary_slip}, fields=FIELDS)
		entry = None
	else:
		frappe.get_doc("Payroll Entry", payroll_entry).check_permission("read")
		entry = payroll_entry
		slips = frappe.get_list(
			"Salary Slip",
			filters={"payroll_entry": payroll_entry, "docstatus": ["<", 2]},
			fields=FIELDS,
			limit_page_length=0,
		)
	if not slips:
		return {"error": "There are no salary slips here to check yet."}

	flagged, steady, now_total, then_total = [], 0, 0.0, 0.0
	earlier = {slip.name: _before(slip) for slip in slips}
	# A workspace's first payroll has nothing before it for anybody, and
	# "first slip" on every line is a list of nothing. Said once instead.
	first = not any(earlier.values())
	for slip in slips:
		before = earlier[slip.name]
		reasons = changes(_shape(slip), _shape(before) if before else None)
		if first:
			reasons = [one for one in reasons if not one.startswith("first slip")]
		now_total += flt(slip.net_pay)
		then_total += flt(before.net_pay) if before else 0
		if reasons:
			flagged.append(
				{
					"slip": slip.name,
					"employee": slip.employee_name,
					"net": flt(slip.net_pay),
					"net_before": flt(before.net_pay) if before else None,
					"moved": abs(flt(slip.net_pay) - (flt(before.net_pay) if before else 0)),
					"why": reasons,
				}
			)
		else:
			steady += 1

	flagged.sort(key=lambda one: one["moved"], reverse=True)
	return {
		"period": f"{slips[0].start_date} to {slips[0].end_date}",
		"slips": len(slips),
		"unchanged": steady,
		"net_total": round(now_total, 2),
		"net_total_last_time": round(then_total, 2),
		"flagged": flagged[:MOST_FLAGGED],
		"missing": _missing(slips) if entry else [],
		"first_payroll": first,
		"next": "Explain each flagged slip in one line, most money first, with the reason in plain words. "
		"Name anybody missing. If nothing is flagged, say the run matches last month; if this is the "
		"first payroll, say there is nothing to compare it with yet.",
	}


FIELDS = [
	"name",
	"employee",
	"employee_name",
	"start_date",
	"end_date",
	"gross_pay",
	"net_pay",
	"total_deduction",
	"payment_days",
	"total_working_days",
]


def _before(slip):
	"""The same person's last submitted slip before this one, if there is one."""
	held = frappe.get_list(
		"Salary Slip",
		filters={"employee": slip.employee, "docstatus": 1, "start_date": ["<", slip.start_date]},
		fields=FIELDS,
		order_by="start_date desc",
		limit_page_length=1,
	)
	return held[0] if held else None


def _shape(slip) -> dict:
	"""A slip as the numbers compared: pay, days and every component."""
	parts = frappe.get_all(
		"Salary Detail",
		filters={"parent": slip.name, "parenttype": "Salary Slip"},
		fields=["salary_component", "amount", "parentfield"],
	)
	return {
		"gross": flt(slip.gross_pay),
		"net": flt(slip.net_pay),
		"days": flt(slip.payment_days),
		"working": flt(slip.total_working_days),
		"components": {
			f"{one.salary_component} ({'deduction' if one.parentfield == 'deductions' else 'earning'})": flt(one.amount)
			for one in parts
		},
	}


def changes(now: dict, before: dict | None) -> list[str]:
	"""Every reason a slip is worth a look, against the one before it. Pure."""
	said = []
	if before is None:
		said.append("first slip for this person: nothing to compare with")
	if now["net"] <= 0:
		said.append(f"net pay is {now['net']:g}")
	if now["working"] and now["days"] < now["working"]:
		said.append(f"paid for {now['days']:g} of {now['working']:g} working days")
	if before is None:
		return said

	if _moved(now["net"], before["net"]):
		said.append(f"net {before['net']:g} → {now['net']:g}")
	for name in sorted(set(now["components"]) | set(before["components"])):
		was, is_ = before["components"].get(name), now["components"].get(name)
		if was is None and is_:
			said.append(f"{name} is new: {is_:g}")
		elif is_ is None and was:
			said.append(f"{name} is gone (was {was:g})")
		elif was is not None and is_ is not None and _moved(is_, was):
			said.append(f"{name} {was:g} → {is_:g}")
	return said


def _moved(now: float, before: float) -> bool:
	gap = abs(now - before)
	return gap >= LEAST and gap >= abs(before) * SHARE


def _missing(slips) -> list[str]:
	"""People paid in the run before this one who have no slip in this one."""
	start = slips[0].start_date
	here = {one.employee for one in slips}
	last = frappe.get_list(
		"Salary Slip",
		filters={"docstatus": 1, "start_date": ["<", start]},
		fields=["start_date"],
		order_by="start_date desc",
		limit_page_length=1,
	)
	if not last:
		return []
	paid = frappe.get_list(
		"Salary Slip",
		filters={"docstatus": 1, "start_date": last[0].start_date},
		fields=["employee", "employee_name"],
		limit_page_length=0,
	)
	gone = []
	for one in paid:
		if one.employee in here:
			continue
		left = frappe.db.get_value("Employee", one.employee, ["status", "relieving_date"], as_dict=True) or {}
		note = f" (left {left.relieving_date})" if left.get("status") == "Left" else ""
		gone.append(f"{one.employee_name}{note}")
	return gone
