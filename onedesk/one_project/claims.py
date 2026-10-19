"""A project's invoices are its claims: each takes the next number within
its project when it is submitted, and its print says where the contract
stands (one/print_blocks.py, `claim`)."""

import frappe
from frappe.utils import flt


def numbered(doc, method=None) -> None:
	"""Sales Invoice on_submit: the next claim number within the project. An
	amendment keeps the number of the invoice it replaces, and one given its
	number already (an import) keeps it. One that bills nothing now, all of
	it held as retention, is not a claim."""
	if not doc.get("project") or doc.get("is_return") or doc.get("one_claim"):
		return
	if not flt(doc.get("net_total")) and any(row.get("one_held") for row in doc.get("items") or []):
		return
	number = (
		frappe.db.get_value("Sales Invoice", doc.amended_from, "one_claim")
		if doc.get("amended_from")
		else None
	)
	if not number:
		frappe.db.sql("select name from `tabProject` where name = %s for update", doc.project)
		number = next_claim(
			frappe.get_all(
				"Sales Invoice",
				filters={"project": doc.project, "docstatus": ["!=", 0], "name": ["!=", doc.name]},
				pluck="one_claim",
			)
		)
	doc.db_set("one_claim", number, update_modified=False)


def next_claim(taken: list) -> int:
	"""One more than the highest claim so far. Pure."""
	return max([int(one or 0) for one in taken] or [0]) + 1


def standing(doc) -> dict | None:
	"""Where the invoice's contract stands as of it: the contract, what was
	billed before it, it, what has been received, and what is left. None
	when its project has no submitted order to be a contract."""
	project = doc.get("project")
	if not project:
		return None
	orders = frappe.get_all(
		"Sales Order", filters={"project": project, "docstatus": 1}, fields=["name", "grand_total"]
	)
	contract = sum(flt(one.grand_total) for one in orders)
	if not contract:
		return None
	billed = frappe.get_all(
		"Sales Invoice",
		filters={"project": project, "docstatus": 1, "name": ["!=", doc.name]},
		fields=["name", "grand_total", "posting_date", "creation"],
	)
	before = [one for one in billed if earlier(one, doc)]
	before_total = sum(flt(one.grand_total) for one in before)
	this = flt(doc.grand_total)
	references = [one.name for one in before] + [doc.name] + [one.name for one in orders]
	received = flt(
		frappe.db.sql(
			"""select sum(r.allocated_amount) from `tabPayment Entry Reference` r
			join `tabPayment Entry` p on p.name = r.parent
			where p.docstatus = 1 and p.payment_type = 'Receive'
			and r.reference_doctype in ('Sales Invoice', 'Sales Order') and r.reference_name in %s""",
			[tuple(references)],
		)[0][0]
	)
	return {
		"claim": doc.get("one_claim"),
		"contract": contract,
		"before": before_total,
		"this": this,
		"to_date": before_total + this,
		"received": received,
		"left": contract - before_total - this,
	}


def earlier(one, doc) -> bool:
	"""Whether an invoice came before this one: posted earlier, or the same
	day and made first. Pure."""
	if str(one.posting_date) != str(doc.posting_date):
		return str(one.posting_date) < str(doc.posting_date)
	return str(one.creation) < str(doc.get("creation") or "9999")
