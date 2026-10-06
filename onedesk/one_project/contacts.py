"""Who outside the company is on a project, and as what: the subcontractor
and the suppliers before anything is ordered from them, the consultants,
the architect, the engineer, the client's representative, the authority.

Each is a row of the project's **Contacts** (Project Contact): a **Role**, the
**Supplier** or, for anyone who isn't one, the **Company**, a frappe
**Contact** with their email and phone, and a **Note**. The Team view lists
them under **Contacts**, and Suppliers lists the suppliers among them
(`contacts`). Adding one is changing the project (`save`, `remove`); the
Contact is linked to the project too, as frappe links a contact to any
record, so the project is among the contact's own links.
"""

from typing import Annotated

import frappe
from frappe import _

#: The roles a contact has on a project, in the order they're offered.
ROLES = (
	"Subcontractor",
	"Supplier",
	"Consultant",
	"Architect",
	"Engineer",
	"Client's Representative",
	"Authority",
	"Other",
)
#: The roles the Suppliers view lists.
SUPPLYING = ("Subcontractor", "Supplier")


@frappe.whitelist()
@frappe.read_only()
def contacts(project: Annotated[str, "The project."]) -> dict:
	"""The project's contacts, and whether the reader may change them."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("read")
	# The person as the Contact has them now, the mobile when there's no phone.
	people = {
		one.name: one
		for one in frappe.get_all(
			"Contact",
			filters={
				"name": ["in", [one.contact for one in doc.get("one_contacts") or [] if one.contact] or [""]]
			},
			fields=["name", "full_name", "email_id", "phone", "mobile_no", "image"],
		)
	}
	suppliers = dict(
		frappe.get_all(
			"Supplier",
			filters={
				"name": [
					"in",
					[one.supplier for one in doc.get("one_contacts") or [] if one.supplier] or [""],
				]
			},
			fields=["name", "supplier_name"],
			as_list=True,
		)
	)
	logos = dict(
		frappe.get_all(
			"Supplier",
			filters={"name": ["in", list(suppliers) or [""]]},
			fields=["name", "image"],
			as_list=True,
		)
	)
	return {
		"contacts": [
			{
				"row": one.name,
				"role": one.role,
				"supplier": one.supplier,
				"organisation": one.organisation,
				"company": suppliers.get(one.supplier) or one.supplier or one.organisation,
				"contact": one.contact,
				"person": _person(people.get(one.contact), "full_name") or one.contact,
				"email": _person(people.get(one.contact), "email_id") or one.email,
				"phone": _person(people.get(one.contact), "phone", "mobile_no") or one.phone,
				# The person's picture, else their company's logo.
				"image": _person(people.get(one.contact), "image") or logos.get(one.supplier),
				"note": one.note,
			}
			for one in doc.get("one_contacts") or []
		],
		"can_change": bool(doc.has_permission("write")),
		"roles": list(ROLES),
	}


def _person(person: dict | None, *fields: str) -> str | None:
	"""The first of `fields` the Contact has, or nothing without one."""
	return next((person.get(one) for one in fields if person and person.get(one)), None)


@frappe.whitelist(methods=["POST"])
def save(
	project: Annotated[str, "The project."],
	role: Annotated[str, "What they are on the project."],
	supplier: Annotated[str | None, "The supplier, when they're one."] = None,
	organisation: Annotated[str | None, "Their company, when it isn't a supplier."] = None,
	contact: Annotated[str | None, "The person, a Contact."] = None,
	note: Annotated[str | None, "A few words on them."] = None,
	row: Annotated[str | None, "The contact to change; a new one when left out."] = None,
) -> dict:
	"""Add a contact to the project, or change one."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	if role not in ROLES:
		frappe.throw(_("Pick the role."))
	values = {
		"role": role,
		"supplier": supplier or None,
		"organisation": organisation or None,
		"contact": contact or None,
		"note": note or None,
	}
	found = next((one for one in doc.get("one_contacts") or [] if one.name == row), None) if row else None
	if found:
		found.update(values)
	else:
		doc.append("one_contacts", values)
	doc.save()
	return contacts(project)


def held(doc, method=None) -> None:
	"""Project validate: each contact names somebody, and one who is a
	supplier has no other company, however the rows are written (the page,
	the form's table, an import)."""
	for row in doc.get("one_contacts") or []:
		if not (row.supplier or row.organisation or row.contact):
			frappe.throw(_("Give the supplier, the company or the contact."))
		if row.supplier:
			row.organisation = None


def link_all(doc, method=None) -> None:
	"""Project on_update: every contact on the project names it among its
	links."""
	for row in doc.get("one_contacts") or []:
		if row.contact:
			linked(row.contact, doc.name)


@frappe.whitelist(methods=["POST"])
def remove(project: Annotated[str, "The project."], row: Annotated[str, "The contact to take off."]) -> dict:
	"""Remove a contact from the project. The Contact itself stays."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	doc.set("one_contacts", [one for one in doc.get("one_contacts") or [] if one.name != row])
	doc.save()
	return contacts(project)


def linked(contact: str, project: str) -> None:
	"""The contact names the project among its links, as frappe links a
	contact to a customer or supplier."""
	person = frappe.get_doc("Contact", contact)
	if any(one.link_doctype == "Project" and one.link_name == project for one in person.links):
		return
	if not person.has_permission("write"):
		return
	person.append("links", {"link_doctype": "Project", "link_name": project})
	person.save()
