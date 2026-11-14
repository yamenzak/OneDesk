"""What OneQuality's inspector does on its own (agent.py WATCH): an
inspection that failed, raised as a non conformance. It answers actions,
which the agents' door takes (one_ai/agents/work.py)."""

import frappe
from frappe import _

from onedesk.one_ai.reading.act import Action


def rejected(inspection) -> list[Action]:
	"""A submitted Quality Inspection that was rejected, as an open Non
	Conformance with the readings that failed, against the procedure named
	as the inspection's template or the workspace's only procedure; with
	neither, against the procedure used last, as a card. Nothing without a
	procedure, or once one is raised for it."""
	if inspection.status != "Rejected":
		return []
	subject = _("{0} failed inspection {1}").format(inspection.item_name or inspection.item_code, inspection.name)
	if frappe.db.exists("Non Conformance", {"subject": subject}):
		return []
	procedure, sure = _procedure(inspection)
	if not procedure:
		return []
	failed = [row.specification for row in inspection.get("readings") or [] if row.get("status") == "Rejected" and row.specification]
	details = [_("{0} {1} on {2} {3}.").format(_("Quality Inspection"), inspection.name, _(inspection.reference_type), inspection.reference_name)]
	if failed:
		details.append(_("Rejected readings: {0}").format(", ".join(failed)))
	if inspection.remarks:
		details.append(inspection.remarks)
	values = {"subject": subject, "procedure": procedure, "status": "Open", "details": "<br>".join(frappe.utils.escape_html(one) for one in details)}
	return [Action("Create", "Non Conformance", values=values, key=f"one_quality|inspection|{inspection.name}", why=_("Inspection {0} was rejected.").format(inspection.name), propose=not sure)]


def _procedure(inspection) -> tuple[str | None, bool]:
	"""The procedure a failed inspection is raised against, and whether it is
	sure: the one named as its template, the only one, or the one used last."""
	template = inspection.get("quality_inspection_template")
	if template and frappe.db.exists("Quality Procedure", template):
		return template, True
	procedures = frappe.get_all("Quality Procedure", filters={"is_group": 0}, pluck="name", limit=2)
	if len(procedures) == 1:
		return procedures[0], True
	return frappe.db.get_value("Non Conformance", {}, "procedure", order_by="creation desc"), False
