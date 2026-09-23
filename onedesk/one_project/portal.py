"""What a customer sees of their projects, on ERPNext's portal.

ERPNext's portal lists a customer's projects at /project and shows one at
/projects?project=…, to anybody listed under **Portal Users** on the Customer.
Two things stopped any customer getting there:

- **Invite as User** on a customer's Contact makes the login and never lists
  it under the Customer's Portal Users, which is the only thing their portal
  reads (`get_customers_suppliers`), so the customer was refused their own
  projects. `invited` lists it (Contact on_update).
- A website user signing in was sent to One's desk, which they cannot open,
  because One's entry on the apps screen did not refuse them
  (onedesk.check_app_permission).

And one thing that stopped a customer seeing a project once there: ERPNext's
project page (templates/pages/projects.py) checks the reader's role
permissions, which a customer has none of, so it refused every customer. It
also showed who in the team each task is assigned to, and a New Task button
that let a customer add tasks to the team's project. One's own page takes its
place at the same address (www/projects.py, since frappe renders the last app's
page for a route): what a customer asks of a project — how far along it is,
when it ends, the milestones, the sub-projects, the work and its state, and
their order and invoices (`view`). Nothing of the team's: no names, no hours,
no updates.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from onedesk.one_project import overview, tree

#: What a task is called on the customer's page, by its status.
SHOWN = {
	"Open": (lambda: _("To Do"), "gray"),
	"Working": (lambda: _("In Progress"), "blue"),
	"Pending Review": (lambda: _("In Review"), "orange"),
	"Completed": (lambda: _("Done"), "green"),
}


def invited(doc, method=None) -> None:
	"""Contact on_update: a contact's login is a portal user of each customer
	the contact is for."""
	if not doc.user or frappe.db.get_value("User", doc.user, "user_type") != "Website User":
		return
	for link in doc.links or []:
		if link.link_doctype != "Customer":
			continue
		if frappe.db.exists("Portal User", {"parenttype": "Customer", "parent": link.link_name, "user": doc.user}):
			continue
		customer = frappe.get_doc("Customer", link.link_name)
		customer.append("portal_users", {"user": doc.user})
		customer.flags.ignore_permissions = True
		customer.save()


def view(project: str) -> dict:
	"""What the customer's page for a project shows. Raises when the reader
	may not see it. Progress is the whole tree the customer sees, since a
	villa's progress is its windows' and its handrails'."""
	doc = frappe.get_doc("Project", project)
	if not may_see(doc):
		raise frappe.PermissionError
	tasks = frappe.get_all(
		"Task",
		filters={"project": project, "status": ["in", list(SHOWN)]},
		fields=["name", "subject", "status", "exp_end_date", "exp_start_date", "is_milestone", "parent_task", "lft"],
		order_by="lft asc",
	)
	of = tree.parents()
	theirs = [
		one
		for one in tree.below({project}, of)
		if one == project or frappe.db.get_value("Project", one, "customer") == doc.customer
	]
	counted = frappe.get_all("Task", filters={"project": ["in", theirs], "status": ["in", list(SHOWN)]}, pluck="status")
	done = sum(1 for one in counted if one == "Completed")
	for one in tasks:
		label, one.colour = SHOWN[one.status]
		one.shown = label()
		one.due = one.exp_end_date or one.exp_start_date
		one.late = bool(one.due and one.status != "Completed" and getdate(one.due) < getdate(nowdate()))
	under = tree.children(of).get(project, [])
	return {
		"doc": doc,
		"parent": frappe.db.get_value("Project", doc.get(tree.PARENT), ["name", "project_name"], as_dict=True)
		if doc.get(tree.PARENT) and may_see(frappe.get_doc("Project", doc.get(tree.PARENT)))
		else None,
		"share": overview.share(done, len(counted)) if counted else round(flt(doc.percent_complete)),
		"done": done,
		"total": len(counted),
		"days_left": overview.days_left(doc.expected_end_date, nowdate(), doc.status == "Completed"),
		"milestones": [one for one in tasks if one.is_milestone],
		"tasks": [one for one in tasks if not one.is_milestone],
		"projects": [
			one
			for one in frappe.get_all(
				"Project",
				filters={"name": ["in", under], "customer": doc.customer, "status": ["!=", "Cancelled"]},
				fields=["name", "project_name", "status", "percent_complete", "expected_end_date"],
				order_by="creation asc",
			)
		]
		if under
		else [],
		"order": frappe.db.get_value(
			"Sales Order", {"name": doc.sales_order, "docstatus": 1}, ["name", "grand_total", "currency"], as_dict=True
		)
		if doc.sales_order
		else None,
		"invoices": frappe.get_all(
			"Sales Invoice",
			filters={"project": project, "docstatus": 1, "customer": doc.customer},
			fields=["name", "posting_date", "grand_total", "outstanding_amount", "currency", "status"],
			order_by="posting_date desc",
		),
	}


def may_see(doc) -> bool:
	"""A customer's portal user sees their customer's projects; anybody else
	whoever may read it in the desk."""
	from frappe.utils.user import is_website_user

	if not is_website_user():
		return bool(frappe.has_permission("Project", "read", doc))
	if not doc.customer:
		return False
	from erpnext.controllers.website_list_for_contact import has_website_permission

	return bool(has_website_permission(doc, "read", frappe.session.user))


def when(days: int | None) -> str | None:
	"""A project's end, said to its customer. Pure but for translation."""
	if days is None:
		return None
	if days < 0:
		return _("{0} days late").format(-days)
	if days == 0:
		return _("Due today")
	return _("In {0} days").format(days)
