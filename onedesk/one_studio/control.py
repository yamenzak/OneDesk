"""OneStudio's ControlCenter (docs/ONE.md, stage 3): Numbering, Printing and
Approvals, how a workspace adapts what One makes. Each section reads and
writes the records that already hold it. Workspace administrators only."""

from typing import Annotated

import frappe
from frappe import _, _lt

from onedesk.one import control, roles

SECTIONS = [
	("numbering", _lt("Numbering"), "hash"),
	("printing", _lt("Printing"), "printer"),
	("approvals", _lt("Approvals"), "route"),
]


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section: numbering, printing or approvals."],
	record: Annotated[str | None, "Not used: each is one page."] = None,
) -> dict:
	roles.require()
	loaders = {"numbering": _numbering, "printing": _printing, "approvals": _approvals}
	if section not in loaders:
		frappe.throw(_("There is no such section."))
	return loaders[section]()


def _numbering() -> dict:
	"""Every kind of record the administrator may renumber (one_studio/numbering.py)."""
	from onedesk.one_studio import numbering

	return {"rows": numbering.doctypes()}


def _approvals() -> dict:
	"""Every approval, and how many steps it has (one_studio/approvals.py)."""
	from onedesk.one_studio import approvals

	return {"rows": approvals.approvals()}


def _printing() -> dict:
	"""The workspace's letter heads and its own print formats (one_studio/printing.py)."""
	from onedesk.one_studio import printing

	company = control._company()
	heads = printing.letter_heads()
	doc = {"company": company.name if company else None}
	for one in heads:
		one["drawn_top"], one["drawn_foot"] = (_drawn(one.get(key), doc) for key in ("content", "footer"))
	return {
		"letter_heads": heads,
		"formats": printing.formats(),
		"company_logo": company.company_logo if company else None,
	}


def _drawn(template: str | None, doc: dict) -> str:
	if not template or "{" not in template:
		return template or ""
	try:
		return frappe.utils.jinja.render_template(template, {"doc": frappe._dict(doc)})
	except Exception:
		return ""
