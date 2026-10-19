"""Projects, under their parents, with their consultants and suppliers as
Project Contacts, and the contract value as the project's Sales Order. A
tender was never a job: it is an Opportunity.

The old app named a project after its client's words ("Mr. X Private
Villa"), so the name stays as the project's title and the record takes
One's own number.

Two habits of the old app are undone. A sub-project called "Original
Contract" or "Original Scope" is the main project's own work, which One shows as the main
project's Main view: it folds into the main project, and so does one Rua
later merged into the main contract (`merged`). And a main project
whose contract is the total of its sub-projects' would count that work
twice: it keeps only what is its own (`own_contracts`).
"""

import frappe
from frappe.utils import flt, getdate

from rua.importer.base import clean, parsed
from rua.importer.parties import PARTY, customer_of, supplier_of

PROJECT = "RUA Project"
STATUS = {"In Progress": "Open", "Job in Hand": "Open", "Completed": "Completed", "Cancelled": "Cancelled"}
VAT = "UAE VAT 5%"
DATED = ("RUA Invoice", "RUA Payment", "RUA LPO", "RUA RFQ", "RUA Quotation")
FOLDED = ("original contract", "original scope")
TOTAL = 0.95


def merged() -> set[str]:
	"""The sub-projects Rua later merged into their main project's contract
	(`rua_merged` in site_config, by their old names): they fold like an
	Original Contract, and their value is already in the main's."""
	return set(frappe.conf.get("rua_merged") or [])


def folded(project, merged=()) -> bool:
	"""A sub-project that is its parent's own work under another name. Pure."""
	return bool(project.get("parent1")) and (
		clean(project["name"]).lower().startswith(FOLDED) or project["name"] in merged
	)


def home(projects, name, merged=()) -> str:
	"""The old project a record of `name` belongs to once folding is done. Pure."""
	found = {one["name"]: one for one in projects}.get(name)
	return found["parent1"] if found and folded(found, merged) else name


def own_contracts(projects, merged=()) -> tuple[dict, dict]:
	"""Each old project's own contract, and what a main project said beyond
	its parts. A folded sub-project's contract is its parent's own work, and
	a merged one's is already in it. Where the main project said more than
	its parts, the main is right and the rest is its own work; where it said
	less, its own work is what was folded into it. A main project with
	nothing folded whose value is the total of its parts (at least 95% of it
	is theirs) has none of its own. Pure."""
	value = {one["name"]: flt(one.get("contract_value")) for one in projects if one.get("status") != "Tender"}
	parts, inside = {}, {}
	for one in projects:
		parent = one.get("parent1")
		if not parent or one["name"] not in value or one["name"] in merged:
			continue
		into = inside if folded(one, merged) else parts
		into[parent] = into.get(parent, 0) + value[one["name"]]
	own, beyond = {}, {}
	for one in projects:
		name = one["name"]
		if name not in value or folded(one, merged):
			continue
		mine, theirs = value[name], parts.get(name, 0)
		if name in inside:
			own[name] = max(inside[name], mine - theirs)
			if abs(mine - theirs - inside[name]) >= 0.005:
				beyond[name] = mine - theirs - inside[name]
		elif mine and theirs >= TOTAL * mine:
			own[name], beyond[name] = 0, mine - theirs
		else:
			own[name] = mine
	return own, beyond


def run(run_):
	projects = run_.docs(PROJECT)
	first = started(run_)
	joined = merged()
	own, beyond = own_contracts(projects, joined)
	for project in sorted(projects, key=lambda one: (bool(one.get("parent1")), one.get("creation") or "")):
		if project.get("status") == "Tender":
			tender(run_, project, first)
			continue
		if folded(project, joined):
			parent = run_.made(PROJECT, project["parent1"], "Project")
			if parent and not run_.made(PROJECT, project["name"], "Project"):
				run_.remember(PROJECT, project["name"], "Project", parent)
			if parent:
				run_.note(
					"Folded",
					"Project",
					parent,
					f"{project['name']}: the main project's own work, now its Main",
				)
			order = run_.made(PROJECT, project["parent1"], "Sales Order")
			if order and not run_.made(PROJECT, project["name"], "Sales Order"):
				run_.remember(PROJECT, project["name"], "Sales Order", order)
			continue
		name = run_.made(PROJECT, project["name"], "Project")
		if not name:
			name = make(run_, project, first)
		if flt(own.get(project["name"])) > 0 and not run_.made(PROJECT, project["name"], "Sales Order"):
			contract(run_, project, name, first, own[project["name"]])
		if project["name"] in beyond:
			said, over = flt(project.get("contract_value")), flt(beyond[project["name"]])
			if not flt(own.get(project["name"])):
				run_.note(
					"Contract Counted Twice",
					"Project",
					name,
					f"{project['name']}: its contract of {said:,.2f} was the total of its sub-projects' and isn't "
					f"ordered again (it differs from theirs by {over:,.2f})",
				)
			elif over > 0:
				run_.note(
					"Contract Above Its Parts",
					"Project",
					name,
					f"{project['name']}: its contract of {said:,.2f} is {over:,.2f} more than its parts, "
					"which is ordered as its own work",
				)
			else:
				run_.note(
					"Contract Below Its Parts",
					"Project",
					name,
					f"{project['name']}: its contract of {said:,.2f} is {-over:,.2f} less than its parts, "
					"which are ordered as they are",
				)


def started(run_) -> dict:
	"""The day each project's first record is dated: the old projects were
	typed in long after they began, so their own creation says little."""
	first = {}
	for doctype in DATED:
		for row in run_.docs(doctype):
			when = row.get("date")
			if row.get("project") and when:
				first[row["project"]] = min(first.get(row["project"], when), when)
	return first


def client(run_, project):
	for one in parsed(project.get("parties"), []):
		if one.get("type") == "Client":
			found = customer_of(run_, one.get("name"))
			if found:
				return found
	for row in run_.docs("RUA Invoice"):
		if row.get("project") == project["name"] and customer_of(run_, row.get("party")):
			return customer_of(run_, row.get("party"))
	return None


def contacts(run_, project):
	parties = {one["name"]: one for one in run_.docs(PARTY)}
	rows = []
	for one in parsed(project.get("parties"), []):
		kind = one.get("type") or ""
		party = parties.get(one.get("name")) or one
		if kind == "Consultant":
			rows.append(
				{
					"role": "Consultant",
					"organisation": clean(party.get("party") or one.get("name")),
					"email": clean(party.get("email")) or None,
					"phone": clean(party.get("phone")) or None,
				}
			)
		elif kind.startswith("Supplier") and supplier_of(run_, one.get("name")):
			rows.append({"role": "Supplier", "supplier": supplier_of(run_, one.get("name"))})
	return rows


def make(run_, project, first):
	parent = run_.made(PROJECT, project.get("parent1"), "Project") if project.get("parent1") else None
	start = first.get(project["name"]) or str(getdate(project.get("creation")))
	notes = "".join(
		f"<p>{frappe.utils.escape_html(clean(text))}</p>"
		for text in (project.get("description"), project.get("location"))
		if clean(text)
	)
	doc = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": clean(project.get("project_name") or project["name"])[:140],
			"status": STATUS.get(project.get("status"), "Open"),
			"company": run_.company,
			"customer": client(run_, project),
			"expected_start_date": start,
			"percent_complete_method": "Manual",
			"percent_complete": flt(project.get("completion")),
			"notes": notes or None,
			"one_parent": parent,
			"one_kind": "Fixed Price" if flt(project.get("contract_value")) else None,
		}
	)
	for row in contacts(run_, project):
		doc.append("one_contacts", row)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return run_.remember(PROJECT, project["name"], "Project", doc.name)


def tax_template(run_):
	return frappe.db.get_value(
		"Sales Taxes and Charges Template", {"company": run_.company, "title": VAT}
	) or frappe.db.get_value("Sales Taxes and Charges Template", {"company": run_.company, "is_default": 1})


def taxes(run_, inclusive, doctype="Sales Taxes and Charges Template"):
	"""The VAT rows of the company's 5% template, in or on top of the price."""
	from erpnext.controllers.accounts_controller import get_taxes_and_charges

	template = tax_template(run_) if doctype.startswith("Sales") else purchase_template(run_)
	rows = get_taxes_and_charges(doctype, template) or []
	for row in rows:
		row["included_in_print_rate"] = 1 if inclusive else 0
	return template, rows


def purchase_template(run_):
	return frappe.db.get_value("Purchase Taxes and Charges Template", {"company": run_.company, "title": VAT})


def contract(run_, project, name, first, value):
	"""The contract as its Sales Order: the old value was with VAT, so the
	order's price includes it and its total is the contract to the dirham."""
	from onedesk.one_project.kinds import CONTRACT_ITEM

	customer = frappe.db.get_value("Project", name, "customer")
	if not customer:
		run_.note(
			"To Check",
			"Project",
			name,
			f"{project['name']}: a contract of {value:,.2f} and no client to order it",
		)
		return
	when = first.get(project["name"]) or str(getdate(project.get("creation")))
	template, rows = taxes(run_, inclusive=True)
	order = frappe.get_doc(
		{
			"doctype": "Sales Order",
			"company": run_.company,
			"customer": customer,
			"project": name,
			"transaction_date": when,
			"delivery_date": when,
			"taxes_and_charges": template,
			"taxes": rows,
			"disable_rounded_total": 1,
			"items": [
				{
					"item_code": CONTRACT_ITEM,
					"qty": 1,
					"rate": flt(value, 2),
					"delivery_date": when,
					"description": clean(project.get("project_name") or project["name"]),
				}
			],
		}
	)
	order.insert(ignore_permissions=True)
	order.submit()
	frappe.db.set_value("Project", name, "sales_order", order.name, update_modified=False)
	run_.remember(PROJECT, project["name"], "Sales Order", order.name)


def tender(run_, project, first):
	if run_.made(PROJECT, project["name"], "Opportunity"):
		return
	customer = client(run_, project)
	if not customer:
		run_.note("Left Out", None, None, f"{project['name']}: a tender with no client named")
		return
	doc = frappe.get_doc(
		{
			"doctype": "Opportunity",
			"opportunity_from": "Customer",
			"party_name": customer,
			"title": clean(project.get("project_name") or project["name"])[:140],
			"company": run_.company,
			"transaction_date": first.get(project["name"]) or str(getdate(project.get("creation"))),
			"opportunity_amount": flt(project.get("contract_value")),
			"currency": run_.currency,
			"status": "Open",
		}
	)
	doc.insert(ignore_permissions=True)
	run_.remember(PROJECT, project["name"], "Opportunity", doc.name)


def project_of(run_, old):
	return run_.made(PROJECT, old, "Project") if old else None


def order_of(run_, old):
	return run_.made(PROJECT, old, "Sales Order") if old else None
