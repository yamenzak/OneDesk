"""A project's signed contract: ERPNext's own Contract, naming the project.

Draw Up Contract makes one, About says whether it is signed, and Needs You
asks for the signature or the renewal. The README's agreement.py says more.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

#: How many days before a signed contract ends that Needs You says so.
ENDING = 30


@frappe.whitelist(methods=["POST"])
def draw_up(
	project: Annotated[str, "The project the contract is for."],
	template: Annotated[str | None, "A Contract Template to start the wording from."] = None,
) -> str:
	"""A draft Contract with the project's customer, naming the project and
	running over its dates. Returns its name."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("read")
	frappe.has_permission("Contract", "create", throw=True)
	if not doc.customer:
		frappe.throw(_("Pick the customer {0} bills first.").format(doc.project_name))
	contract = frappe.new_doc("Contract")
	contract.update(
		{
			"party_type": "Customer",
			"party_name": doc.customer,
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


def _wording(contract, project, template: str | None) -> str:
	"""The template's wording as ERPNext's form fills it in, or else the
	project's terms and conditions."""
	if template:
		from erpnext.crm.doctype.contract_template.contract_template import get_contract_template

		said = get_contract_template(template, contract.as_dict()).get("contract_terms")
		if said:
			return said
	if project.get("one_terms"):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_and_conditions

		return get_terms_and_conditions(project.one_terms, contract.as_dict())
	frappe.throw(_("Pick a contract template, or give {0} its terms and conditions.").format(project.project_name))


def of(project: str) -> dict | None:
	"""The project's latest contract not cancelled, for About: whether it is
	signed and when it ends, said to whoever reads the project. Its wording
	opens only for those ERPNext lets read contracts, as an employee's are
	contracts too."""
	found = frappe.get_all(
		"Contract",
		filters={"document_type": "Project", "document_name": project, "docstatus": ["<", 2]},
		fields=["name", "is_signed", "status", "start_date", "end_date", "signed_on", "docstatus"],
		order_by="creation desc",
		limit=1,
	)
	if not found:
		return None
	one = found[0]
	return {
		"name": one.name,
		"signed": bool(one.is_signed),
		"status": one.status,
		"ends": str(one.end_date) if one.end_date else None,
		"signed_on": str(getdate(one.signed_on)) if one.signed_on else None,
		"route": f"/desk/contract/{one.name}" if frappe.has_permission("Contract", "read", doc=one.name) else None,
	}


def asks(doc) -> list[dict]:
	"""Needs You: the contract not signed yet, or a signed one ending within
	a month, or ended, while the project is open."""
	if doc.status != "Open":
		return []
	one = of(doc.name)
	if not one:
		return []
	if not one["signed"]:
		return [{"tone": "orange", "text": _("Get the contract signed"), "dim": one["name"], "route": one["route"]}]
	if not one["ends"]:
		return []
	days = (getdate(one["ends"]) - getdate(nowdate())).days
	if days > ENDING:
		return []
	if days < 0:
		dim = _("Ended 1 day ago") if days == -1 else _("Ended {0} days ago").format(-days)
	elif days == 0:
		dim = _("Ends today")
	else:
		dim = _("Ends tomorrow") if days == 1 else _("Ends in {0} days").format(days)
	return [{"tone": "red" if days < 0 else "orange", "text": _("Renew the contract"), "dim": dim, "route": one["route"]}]
