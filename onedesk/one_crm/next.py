"""What happens next on a lead or a deal, and when.

Two fields on the record rather than a ToDo. The owner is told when it comes due
(tell.py's `due`, the Next Step Due notification).
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull
from frappe.utils import escape_html, format_datetime

#: The statuses in which somebody still has something to do.
OPEN = {
	"Lead": ("Lead", "Open", "Replied", "Interested"),
	"Opportunity": ("Open", "Quotation", "Replied"),
}

#: Who a record belongs to.
OWNER = {"Lead": "lead_owner", "Opportunity": "opportunity_owner"}


def settle() -> None:
	"""Give every unowned deal its maker as owner. Home counts what is the
	reader's, so a deal nobody owns is due on nobody's day. A lead without an
	owner is left alone, since it waits on Home as unclaimed (capture.py)."""
	table = frappe.qb.DocType("Opportunity")
	(
		frappe.qb.update(table)
		.set(table.opportunity_owner, table.owner)
		.where(IfNull(table.opportunity_owner, "") == "")
		.where(table.owner != "Guest")
		.run()
	)


@frappe.whitelist(methods=["POST"])
def done(
	doctype: Annotated[str, "Lead or Opportunity."],
	name: str,
	next_step: str | None = None,
	next_on: str | None = None,
) -> None:
	"""The current step is done: say so on the timeline, and set the next."""
	if doctype not in OPEN:
		frappe.throw(_("Only a lead or an opportunity has a next step."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if doc.one_next_step:
		said = _("Done: {0}").format(escape_html(doc.one_next_step))
		if doc.one_next_on:
			said += f" <span class='text-muted'>({format_datetime(doc.one_next_on)})</span>"
		doc.add_comment("Info", said)
	doc.one_next_step = (next_step or "").strip() or None
	doc.one_next_on = next_on or None
	doc.save()
