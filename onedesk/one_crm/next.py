"""What happens next on a lead or a deal, and when.

Two fields on the record rather than a ToDo: a ToDo on a record marks the
record assigned to whoever holds it, and closing it unassigns them, so the
step and the owner would be one thing. On the record, a missing next step is
a filter, a column and a count on Home, and the step shows on the board card.

The owner is reminded at the time with frappe's own Reminder. `done` writes
the step that was done on the timeline before setting the next one, so the
history of a deal is what was done, not only what was planned.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull
from frappe.utils import escape_html, format_datetime, get_datetime, now_datetime

#: The statuses in which somebody still has something to do.
OPEN = {
	"Lead": ("Lead", "Open", "Replied", "Interested"),
	"Opportunity": ("Open", "Quotation", "Replied"),
}

#: Who a record belongs to.
OWNER = {"Lead": "lead_owner", "Opportunity": "opportunity_owner"}


def settle() -> None:
	"""Give every unowned lead and deal its maker as owner. Home counts what is
	the reader's, so a record nobody owns is due on nobody's day."""
	for doctype, field in OWNER.items():
		table = frappe.qb.DocType(doctype)
		(
			frappe.qb.update(table)
			.set(table[field], table.owner)
			.where(IfNull(table[field], "") == "")
			.run()
		)


def on_update(doc, method=None) -> None:
	"""Keep one reminder per record, at the step's time, for the record's owner."""
	before = doc.get_doc_before_save()
	moved = not before or (before.one_next_on, before.one_next_step, before.get(OWNER[doc.doctype])) != (
		doc.one_next_on,
		doc.one_next_step,
		doc.get(OWNER[doc.doctype]),
	)
	if moved:
		remind(doc)


def remind(doc) -> None:
	frappe.db.delete(
		"Reminder", {"reminder_doctype": doc.doctype, "reminder_docname": doc.name, "notified": 0}
	)
	if not doc.one_next_on or get_datetime(doc.one_next_on) <= now_datetime():
		return
	if doc.get("status") not in OPEN[doc.doctype]:
		return
	reminder = frappe.get_doc(
		{
			"doctype": "Reminder",
			"remind_at": doc.one_next_on,
			"description": f"{doc.one_next_step or _('Next Step')}: {doc.get('title') or doc.name}",
			"reminder_doctype": doc.doctype,
			"reminder_docname": doc.name,
		}
	).insert(ignore_permissions=True)
	# A Reminder is always the saver's; the step is the owner's.
	owner = doc.get(OWNER[doc.doctype])
	if owner and owner != reminder.user:
		reminder.db_set("user", owner)


@frappe.whitelist(methods=["POST"])
def done(
	doctype: Annotated[str, "Lead or Opportunity."],
	name: str,
	next_step: str | None = None,
	next_on: str | None = None,
) -> None:
	"""The current step is done: say so on the timeline, and set the next."""
	if doctype not in OPEN:
		frappe.throw(_("Only a lead or a deal has a next step."))
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
