"""How a lead arrives, and what is done with it before anybody opens it.

Three ways in: the desk, the **Get in Touch** web form, and mail to an inbox
whose Email Account appends to Lead. Whichever way, somebody who is already a
lead is not made a second time when that can be avoided, and is flagged when
it cannot:

- **Mail** from an address that is already a lead is added to that lead.
  frappe's mail receiver makes a new lead when no thread matches, and if the
  insert raises DuplicateEntryError it looks the sender up instead; raising
  exactly that is how the mail finds its lead.
- **The web form** cannot tell a visitor "you already exist", so the lead is
  made and marked as a possible duplicate, with Merge and Not a Duplicate on
  its page.
- **The desk** is told, as ERPNext's own email check told it; ERPNext's check
  is switched off at install because it refused the web form and the inbox
  as well.

A phone number or a business name already on a lead or a customer is never a
refusal, only a flag: two people share a switchboard, and "Ali" is a name.

A lead from the web form or the inbox belongs to nobody until somebody takes it
or an Assignment Rule shares it out. It is on Home as Unclaimed until then.
"""

import re
from typing import Annotated

import frappe
from frappe import _
from frappe.utils import now_datetime

#: What the lead's source reads as, by the way it came in.
WEBSITE = "Website"

#: The owners erpnext's `__user` default gives a lead nobody made at the desk.
NOBODY = ("Guest",)

#: How many trailing digits make two phone numbers the same number, so that
#: +971 50 123 4567 and 050-1234567 match and two short extensions do not.
DIGITS = 8


def before_insert(doc, method=None) -> None:
	if doc.lead_owner in NOBODY or frappe.flags.in_web_form:
		doc.lead_owner = None
	if frappe.flags.in_web_form and not doc.utm_source:
		doc.utm_source = WEBSITE

	same = matches(doc)
	by_email = next((one for one in same if one["on"] == "email" and one["doctype"] == "Lead"), None)
	if by_email and not frappe.flags.in_web_form:
		raise frappe.DuplicateEntryError(
			_("{0} is already a lead: {1}").format(doc.email_id, by_email["name"]),
			"Lead",
			by_email["name"],
		)
	if same:
		doc.one_duplicate_type, doc.one_duplicate_of, doc.one_duplicate_on = (
			same[0]["doctype"],
			same[0]["name"],
			same[0]["on"],
		)


def matches(doc) -> list[dict]:
	"""Leads and customers this lead may already be: by email, then phone, then
	business name, the order in which a match is more likely the same person."""
	found = []
	others = {"name": ["!=", doc.name or ""]}
	if doc.email_id:
		for name in frappe.get_all("Lead", filters={"email_id": doc.email_id, **others}, pluck="name", limit=1):
			found.append({"doctype": "Lead", "name": name, "on": "email"})
		for name in contact_links("email_id", doc.email_id):
			found.append({"doctype": "Customer", "name": name, "on": "email"})

	# Numbers are stored as typed, spaces and dashes included, so the database
	# narrows by the last four digits and the comparison is done on digits.
	phones = ("mobile_no", "phone", "whatsapp_no")
	for number in {tail(doc.get(field)) for field in phones} - {""}:
		for field in phones:
			for row in frappe.get_all(
				"Lead", filters={field: ["like", f"%{number[-4:]}"], **others}, fields=["name", field]
			):
				if tail(row[field]) == number:
					found.append({"doctype": "Lead", "name": row.name, "on": "phone"})

	business = (doc.company_name or "").strip()
	if business:
		for name in frappe.get_all("Lead", filters={"company_name": business, **others}, pluck="name", limit=1):
			found.append({"doctype": "Lead", "name": name, "on": "business name"})
		for name in frappe.get_all("Customer", filters={"customer_name": business}, pluck="name", limit=1):
			found.append({"doctype": "Customer", "name": name, "on": "business name"})

	seen, out = set(), []
	for one in found:
		if (one["doctype"], one["name"]) not in seen:
			seen.add((one["doctype"], one["name"]))
			out.append(one)
	return out


def contact_links(field: str, value: str) -> list[str]:
	"""Customers whose contacts carry this email."""
	contacts = frappe.get_all("Contact", filters={field: value}, pluck="name")
	if not contacts:
		return []
	return frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "parent": ["in", contacts], "link_doctype": "Customer"},
		pluck="link_name",
		limit=1,
	)


def tail(number: str | None) -> str:
	"""The last DIGITS digits of a phone number, or nothing if it has fewer. Pure."""
	digits = re.sub(r"\D", "", number or "")
	return digits[-DIGITS:] if len(digits) >= DIGITS else ""


@frappe.whitelist(methods=["POST"])
def merge(lead: str, into: Annotated[str, "The lead this one is the same as."]) -> str:
	"""Fold a duplicate lead into the one it duplicates: its comments, mail,
	calls and deals move across, and it is gone. frappe's own rename with merge."""
	if lead == into:
		frappe.throw(_("A lead cannot be merged into itself."))
	for name in (lead, into):
		frappe.get_doc("Lead", name).check_permission("write")
	frappe.get_doc("Lead", lead).check_permission("delete")
	frappe.rename_doc("Lead", lead, into, merge=True)
	return into


@frappe.whitelist(methods=["POST"])
def not_duplicate(lead: str) -> None:
	doc = frappe.get_doc("Lead", lead)
	doc.check_permission("write")
	doc.update({"one_duplicate_type": None, "one_duplicate_of": None, "one_duplicate_on": None})
	doc.save()


@frappe.whitelist(methods=["POST"])
def take(doctype: Annotated[str, "Lead or Opportunity."], name: str) -> None:
	"""Make the reader the owner of a lead or deal nobody owns."""
	from onedesk.one_crm.next import OWNER

	if doctype not in OWNER:
		frappe.throw(_("Only a lead or a deal has an owner."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if doc.get(OWNER[doctype]):
		frappe.throw(_("{0} already belongs to {1}.").format(doc.get("title") or name, doc.get(OWNER[doctype])))
	doc.set(OWNER[doctype], frappe.session.user)
	doc.save()


def assigned(todo, method=None) -> None:
	"""An Assignment Rule shares a lead or deal out by assigning it; the person
	it is given to becomes its owner, if it has none, so it is on their Home."""
	from onedesk.one_crm.next import OWNER

	if not todo.assignment_rule or todo.reference_type not in OWNER or not todo.allocated_to:
		return
	field = OWNER[todo.reference_type]
	if not frappe.db.get_value(todo.reference_type, todo.reference_name, field):
		frappe.db.set_value(todo.reference_type, todo.reference_name, field, todo.allocated_to)


def replied(doc, method=None) -> None:
	"""The first mail sent to a lead, or the first call made to one, is its
	first reply. Measured from when the lead came in."""
	if doc.doctype == "Communication":
		if doc.communication_type != "Communication" or doc.sent_or_received != "Sent":
			return
		leads = [doc.reference_name] if doc.reference_doctype == "Lead" else []
	else:
		if doc.type != "Outgoing":
			return
		leads = [row.link_name for row in doc.links if row.link_doctype == "Lead"]
	for lead in leads:
		if not frappe.db.get_value("Lead", lead, "one_first_reply_at"):
			frappe.db.set_value("Lead", lead, "one_first_reply_at", now_datetime(), update_modified=False)


def defaults() -> None:
	"""CRM Settings a new workspace starts with. On install only: erpnext writes
	both as 0 when it installs, so there is no "never written" to wait for, and
	after that they are the workspace's.

	- A deal made from a lead carries the lead's comments and mail.
	- ERPNext's own refusal of a second lead with the same email is off; the
	  rules above decide instead.
	"""
	frappe.db.set_single_value("CRM Settings", "carry_forward_communication_and_comments", 1)
	frappe.db.set_single_value("CRM Settings", "allow_lead_duplication_based_on_emails", 1)
