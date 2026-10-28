"""What OneCRM shows on the portal, read by OnePortal's engine
(one_portal/portal.py) through the one_portal hook: a customer's quotations,
which they accept or decline there, and their sales orders. Each entry of
KINDS is one kind of record, in the keys one_portal/AGENTS.md lists."""

import frappe
from frappe import _, _lt

from onedesk.one_portal import portal as engine


def _quotation_steps(doc) -> list[tuple[str, bool]]:
	if doc.status == "Lost":
		return [(_("Sent"), True), (_("Declined"), True)]
	ordered = doc.status == "Ordered"
	return [(_("Sent"), True), (_("Accepted"), ordered or bool(accepted(doc.name))), (_("Ordered"), ordered)]


def _order_steps(doc) -> list[tuple[str, bool]]:
	from frappe.utils import flt

	billed = flt(doc.per_billed) >= 100
	return [
		(_("Confirmed"), True),
		(_("Delivered"), flt(doc.per_delivered) >= 100),
		(_("Invoiced"), billed),
		(_("Paid"), billed and not engine.owed("Sales Invoice", "sales_order", doc.name)),
	]


def _taken(doc) -> bool:
	"""Accepted on the portal and not yet confirmed as an order."""
	return doc.status == "Open" and bool(accepted(doc.name))


KINDS = {
	"Quotation": {
		"transaction": True,
		"party": "party_name",
		"icon": "file-text",
		"said": {"Lost": ("gray", _lt("Declined"))},
		"chain": ((), (("Sales Order", "Sales Order Item", "prevdoc_docname"),)),
		"ahead": ("valid_till", _lt("Valid until {0}")),
		"ended": ("Ordered", "Partially Ordered", "Lost"),
		"settled": lambda doc: bool(accepted(doc.name)),
		"badge": lambda doc: ("blue", _("Accepted")) if _taken(doc) else None,
		"summary": lambda doc: {"line": _("Accepted. We'll confirm your order.")} if _taken(doc) else {},
		"answer": lambda doc: answerable(doc),
		"asks": (lambda doc: answerable(doc), _lt("Review")),
		"steps": _quotation_steps,
		"ships": True,
	},
	"Sales Order": {
		"transaction": True,
		"party": "customer",
		"icon": "package",
		"said": {
			"To Deliver and Bill": ("blue", _lt("Confirmed")),
			"To Deliver": ("blue", _lt("Confirmed")),
			"To Bill": ("green", _lt("Delivered")),
		},
		"chain": (
			(("Quotation", "prevdoc_docname"),),
			(
				("Delivery Note", "Delivery Note Item", "against_sales_order"),
				("Sales Invoice", "Sales Invoice Item", "sales_order"),
			),
		),
		"ahead": ("delivery_date", _lt("Delivery {0}")),
		"steps": _order_steps,
		"ships": True,
	},
}


def accepted(quotation: str) -> str | None:
	"""The order a quotation was accepted as on the portal, or made into."""
	return frappe.db.get_value(
		"Sales Order Item", {"prevdoc_docname": quotation, "docstatus": ("<", 2)}, "parent"
	)


def answerable(doc) -> bool:
	"""Whether the customer may still accept or decline a quotation: sent,
	open, not run out (unless the workspace takes orders on those, as
	erpnext's Selling Settings says), and not accepted already."""
	from frappe.utils import getdate, today

	if doc.docstatus != 1 or doc.status not in ("Open", "Replied"):
		return False
	if doc.valid_till and getdate(doc.valid_till) < getdate(today()):
		if not frappe.db.get_single_value(
			"Selling Settings", "allow_sales_order_creation_for_expired_quotation"
		):
			return False
	return not accepted(doc.name)


def _answer(kind: str, name: str):
	"""A quotation the reader may answer, through erpnext's own page context,
	which checks it is theirs."""
	from erpnext.templates.pages import order

	if engine._kind(kind) != "Quotation":
		raise frappe.PermissionError
	doc = engine._opened("Quotation", name, order).doc
	if not answerable(doc):
		frappe.throw(_("This quotation can no longer be answered."))
	return doc


@frappe.whitelist(methods=["POST"])
def accept_quote(kind: str, name: str, wanted: str, reference: str | None = None) -> str:
	"""The customer accepts a quotation on the portal (`accept`)."""
	from frappe.utils import get_fullname

	doc = _answer(kind, name)
	user = frappe.session.user
	return accept(
		doc, wanted, reference, user, engine._contact_of(user, "Customer", doc.party_name), get_fullname(user)
	)


def accept(doc, wanted: str, reference: str | None, user: str, contact: str | None, by: str) -> str:
	"""A quotation accepted: erpnext's own mapper makes the order from it, as
	the team would on the desk, with the date they need it by and their
	reference, named for whoever accepted (`contact`). It is kept a draft for
	whoever made the quotation to check and submit, and they are told."""
	from erpnext.selling.doctype.quotation.mapper import make_sales_order
	from frappe.utils import getdate, today

	from onedesk.one_crm import tell

	if not wanted or getdate(wanted) < getdate(today()):
		frappe.throw(_("Choose the date you need it by, today or later."))
	frappe.session.user = "Administrator"
	try:
		order = make_sales_order(doc.name)
		order.contact_person = contact or order.contact_person
		order.delivery_date = wanted
		for row in order.items:
			row.delivery_date = wanted
		if reference and reference.strip():
			order.po_no, order.po_date = reference.strip()[:140], today()
		order.flags.ignore_permissions = True
		order.insert()
		doc.add_comment("Info", _("Accepted on the portal by {0}: order {1}.").format(by, order.name))
	finally:
		frappe.session.user = user
	tell.quotation_accepted(doc, order, user if user != "Guest" else "Administrator", engine._date(wanted))
	return order.name


@frappe.whitelist(methods=["POST"])
def decline_quote(kind: str, name: str, reason: str | None = None) -> None:
	"""The customer declines a quotation on the portal (`decline`)."""
	from frappe.utils import get_fullname

	user = frappe.session.user
	decline(_answer(kind, name), reason, user, get_fullname(user))


def decline(doc, reason: str | None, user: str, by: str) -> None:
	"""A quotation declined: erpnext's own Set as Lost, with their reason,
	and whoever made it is told."""
	from onedesk.one_crm import tell

	reason = (reason or "").strip()[:1000]
	frappe.session.user = "Administrator"
	try:
		doc.declare_enquiry_lost([], [], detailed_reason=reason or _("Declined on the portal."))
		doc.add_comment("Info", _("Declined on the portal by {0}.").format(by))
	finally:
		frappe.session.user = user
	tell.quotation_declined(doc, user if user != "Guest" else "Administrator", reason)
