"""A project's contracts: ERPNext's own Contract, naming the project, with its
customer or one of its suppliers.

Draw Up Contract makes one, the Overview lists them, About says whether the
customer's is signed, and Needs You asks for each signature or renewal. The
README's agreement.py says more.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

#: How many days before a signed contract ends that Needs You says so.
ENDING = 30

#: Who a project's contract may be with.
PARTIES = ("Customer", "Supplier")


@frappe.whitelist(methods=["POST"])
def draw_up(
	project: Annotated[str, "The project the contract is for."],
	template: Annotated[str | None, "A Contract Template to start the wording from."] = None,
	party_type: Annotated[str, "Customer or Supplier."] = "Customer",
	party: Annotated[str | None, "The supplier, for a contract with one of the project's suppliers."] = None,
) -> str:
	"""A draft Contract naming the project, running over its dates, with its
	customer or one of its suppliers. Returns its name."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("read")
	frappe.has_permission("Contract", "create", throw=True)
	if party_type == "Customer":
		party = doc.customer
		if not party:
			frappe.throw(_("Pick the customer {0} bills first.").format(doc.project_name))
	elif party_type != "Supplier" or party not in suppliers(doc.name):
		frappe.throw(_("Pick one of the suppliers on {0}.").format(doc.project_name))
	contract = frappe.new_doc("Contract")
	contract.update(
		{
			"party_type": party_type,
			"party_name": party,
			"document_type": "Project",
			"document_name": doc.name,
			"start_date": doc.expected_start_date,
			"end_date": doc.expected_end_date,
			"contract_template": template,
		}
	)
	contract.contract_terms = _wording(contract, doc, template)
	contract.insert()
	return contract.name


@frappe.whitelist()
@frappe.read_only()
def parties(project: Annotated[str, "The project."]) -> list[dict]:
	"""Who Draw Up Contract offers: the customer, then each supplier on the
	project, by name."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("read")
	found = []
	if doc.customer:
		name = frappe.db.get_value("Customer", doc.customer, "customer_name") or doc.customer
		found.append({"party_type": "Customer", "party": doc.customer, "label": name})
	names = dict(frappe.get_all("Supplier", filters={"name": ["in", suppliers(project)]}, fields=["name", "supplier_name"], as_list=True))
	found += [{"party_type": "Supplier", "party": one, "label": names.get(one) or one} for one in suppliers(project)]
	return found


def suppliers(project: str) -> list[str]:
	"""The suppliers on a project: those ordered from for it, and those on its
	contacts."""
	from onedesk.one_project import tree

	projects = list(tree.scope(project))
	ordered = frappe.get_all(
		"Purchase Order",
		filters={"project": ["in", projects], "docstatus": 1},
		pluck="supplier",
		distinct=True,
	)
	listed = frappe.get_all(
		"Project Contact", filters={"parent": project, "supplier": ["is", "set"]}, pluck="supplier"
	)
	return list(dict.fromkeys([*ordered, *listed]))


def _wording(contract, project, template: str | None) -> str:
	"""The template's wording as ERPNext's form fills it in, or else, with the
	customer, the project's terms and conditions."""
	if template:
		from erpnext.crm.doctype.contract_template.contract_template import get_contract_template

		said = get_contract_template(template, contract.as_dict()).get("contract_terms")
		if said:
			return said
	if contract.party_type == "Customer" and project.get("one_terms"):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_and_conditions

		return get_terms_and_conditions(project.one_terms, contract.as_dict())
	if contract.party_type == "Supplier":
		frappe.throw(_("Pick a contract template for a supplier's contract."))
	frappe.throw(_("Pick a contract template, or give {0} its terms and conditions.").format(project.project_name))


def contracts(projects: list[str]) -> list[dict]:
	"""Every contract not cancelled on the projects, newest first: who it is
	with, whether it is signed and when it ends, said to whoever reads the
	project. Its wording opens only for those ERPNext lets read contracts,
	as an employee's are contracts too."""
	if not projects:
		return []
	found = frappe.get_all(
		"Contract",
		filters={"document_type": "Project", "document_name": ["in", projects], "docstatus": ["<", 2]},
		fields=["name", "party_type", "party_name", "party_full_name", "is_signed", "status", "end_date", "signed_on", "document_name", "contract_template"],
		order_by="creation desc",
	)
	reads = frappe.has_permission("Contract", "read")
	titles = dict(frappe.get_all("Project", filters={"name": ["in", list(projects)]}, fields=["name", "project_name"], as_list=True))
	# Each party's logo, as the page shows the customer's and suppliers' elsewhere.
	logos = {}
	for kind in PARTIES:
		named = [one.party_name for one in found if one.party_type == kind]
		if named:
			logos.update({(kind, name): image for name, image in frappe.get_all(kind, filters={"name": ["in", named]}, fields=["name", "image"], as_list=True)})
	return [
		{
			"name": one.name,
			"party_type": one.party_type,
			"party": one.party_name,
			"with": one.party_full_name or one.party_name,
			"image": logos.get((one.party_type, one.party_name)),
			"project": one.document_name,
			"project_title": titles.get(one.document_name),
			"template": one.contract_template,
			"signed": bool(one.is_signed),
			"status": one.status,
			"ends": str(one.end_date) if one.end_date else None,
			"signed_on": str(getdate(one.signed_on)) if one.signed_on else None,
			"route": f"/desk/contract/{one.name}" if reads and frappe.has_permission("Contract", "read", doc=one.name) else None,
		}
		for one in found
	]


def main(project: str, listed: list[dict] | None = None) -> dict | None:
	"""The customer's contract About shows: the latest signed, else the latest."""
	own = [one for one in (listed if listed is not None else contracts([project])) if one["party_type"] == "Customer" and one["project"] == project]
	return next((one for one in own if one["signed"]), own[0] if own else None)


def asks(doc, listed: list[dict]) -> list[dict]:
	"""Needs You, while the project is open: each contract not signed yet, and
	each signed one ending within a month or ended."""
	if doc.status != "Open":
		return []
	today = getdate(nowdate())
	found = []
	for one in listed:
		if not one["signed"]:
			found.append({"tone": "orange", "text": _("Get the contract signed"), "dim": " · ".join(filter(None, [one["with"], covers(one, doc.name)])), "route": one["route"]})
			continue
		if not one["ends"] or _renewed(one, listed):
			continue
		days = (getdate(one["ends"]) - today).days
		if days > ENDING:
			continue
		if days < 0:
			when = _("Ended 1 day ago") if days == -1 else _("Ended {0} days ago").format(-days)
		elif days == 0:
			when = _("Ends today")
		else:
			when = _("Ends tomorrow") if days == 1 else _("Ends in {0} days").format(days)
		found.append({"tone": "red" if days < 0 else "orange", "text": _("Renew the contract"), "dim": " · ".join([one["with"], when]), "route": one["route"]})
	return found


def covers(one: dict, project: str) -> str | None:
	"""What a contract is for, beside who it is with: the project under this
	one it names, else the template it was drawn up from. Pure."""
	if one.get("project") and one["project"] != project:
		return one.get("project_title") or one["project"]
	return one.get("template") or None


def _renewed(one: dict, listed: list[dict]) -> bool:
	"""Whether a later signed contract with the same party runs past this one."""
	return any(
		other["party"] == one["party"] and other["signed"] and other["ends"] and other["ends"] > one["ends"]
		for other in listed
	)
