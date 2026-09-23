"""Who sees a project: its members.

ERPNext lets every Projects User read every project. A workspace running a
villa for one customer and a website for another does not want the window
fitter reading the website's budget, so a project's **Users** decide:

- a **Projects Manager** sees every project;
- anybody else who works in projects sees a project they made, one they run
  (**Project Manager**), one they are listed on, and one with **nobody
  listed** — a project nobody has closed is
  open to everybody who works in projects, which is also what every project
  was before this;
- members of a project see what is under it (sub-projects; `under`).

The same rule decides a project's tasks (one_task/access.py): a task in a
project is seen by whoever may see the project, and by its own people always.

**Being listed is ERPNext's own share.** Their Project already shares itself
with each person on Users and takes the share back when they are removed, so a
member opens the project through frappe's share as well as through this rule.

**A workspace with no outgoing mail can still add a member.** ERPNext mails an
invitation to each new member while the project saves, and frappe refuses to
queue mail with no outgoing account — so the save failed, and nobody could be
added at all. Where there is no account the invitation is marked as sent
(`invite`); the member has their access either way.

Only somebody holding Projects User is narrowed here. Twenty other roles have
Select on Project so a sales order or an invoice can name one; they pick from
a list and never open the project, and narrowing their list would break their
forms, not protect the project.
"""

import frappe

#: Who sees every project.
MANAGERS = ("Projects Manager",)

#: The role whose view of projects this narrows.
WORKER = "Projects User"


def manages(user: str) -> bool:
	return user == "Administrator" or bool(set(MANAGERS) & set(frappe.get_roles(user)))


def narrowed(user: str) -> bool:
	"""Whether this person's list of projects is their own rather than all."""
	return not manages(user) and WORKER in frappe.get_roles(user)


def visible(user: str) -> set[str]:
	"""The projects this person may see by the rule above. Kept for the request."""
	kept = getattr(frappe.local, "one_projects_seen", None)
	if kept is None:
		kept = frappe.local.one_projects_seen = {}
	if user not in kept:
		listed = set(frappe.get_all("Project User", filters={"parenttype": "Project"}, pluck="parent", distinct=True))
		member = set(frappe.get_all("Project User", filters={"parenttype": "Project", "user": user}, pluck="parent"))
		owned = set(frappe.get_all("Project", filters={"owner": user}, pluck="name"))
		owned |= set(frappe.get_all("Project", filters={"one_manager": user}, pluck="name"))
		unlisted = set(frappe.get_all("Project", pluck="name")) - listed
		kept[user] = under(member | owned | unlisted)
	return kept[user]


def under(projects: set[str]) -> set[str]:
	"""The projects and everything below them (one_project/tree.py)."""
	from onedesk.one_project import tree

	return tree.below(projects, tree.parents())


def forget(doc=None, method=None) -> None:
	"""Project on_update and on_trash: who sees what may have changed."""
	frappe.local.one_projects_seen = {}


def sees(project: str, user: str) -> bool:
	return manages(user) or project in visible(user)


def allowed(doc, ptype=None, user=None, debug=False) -> bool:
	user = user or frappe.session.user
	if not narrowed(user) or doc.is_new():
		return True
	return doc.name in visible(user)


def query(user=None, doctype=None) -> str:
	user = user or frappe.session.user
	if not narrowed(user):
		return ""
	return f"`tabProject`.`name` in ({names(visible(user))})"


def names(projects: set[str]) -> str:
	"""A set of names as an SQL list, never empty."""
	return ", ".join(frappe.db.escape(one) for one in sorted(projects)) or "''"


def invite(doc, method=None) -> None:
	"""Project before_validate: no invitation to send where no mail can go."""
	if frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
		return
	for row in doc.get("users") or []:
		row.welcome_email_sent = 1
