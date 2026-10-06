"""Who sees a project: its members.

ERPNext lets every Projects User read every project. A workspace running a
villa for one customer and a website for another does not want the window
fitter reading the website's budget, so a project's **Users** decide:

- a **Projects Manager** sees every project, and so do the books (an
  **Accounts User** or **Accounts Manager**), who invoice every project's time
  and progress;
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

**A member can be taken off.** ERPNext takes back a removed member's share in
a way only a System Manager may, so the save failed for everybody in a
workspace; `unlist` takes it back first.

**A member is told in ours.** ERPNext mails an invitation to each new member
while the project saves: English mail outside the hub, which also failed the
save where the workspace has no outgoing mail. `invite` marks it sent, and
tell.py tells the member as Added to Project instead.

Only somebody holding Projects User is narrowed here. Twenty other roles have
Select on Project so a sales order or an invoice can name one; they pick from
a list and never open the project, and narrowing their list would break their
forms, not protect the project.
"""

import frappe

#: Who sees every project.
MANAGERS = ("Projects Manager",)

#: Who sees every project without running them: the books.
BOOKS = ("Accounts User", "Accounts Manager")

#: The role whose view of projects this narrows.
WORKER = "Projects User"


def manages(user: str) -> bool:
	return user == "Administrator" or bool(set(MANAGERS) & set(frappe.get_roles(user)))


def narrowed(user: str) -> bool:
	"""Whether this person's list of projects is their own rather than all."""
	held = set(frappe.get_roles(user))
	return not manages(user) and WORKER in held and not held & set(BOOKS)


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
	"""Project before_validate: ERPNext's invitation is never sent. A member is
	told in ours, Added to Project (tell.py), in their language and as they
	chose; ERPNext's is English mail outside the hub, and fails the save where
	no mail can go."""
	for row in doc.get("users") or []:
		row.welcome_email_sent = 1


def unlist(doc, method=None) -> None:
	"""Project before_validate: a member taken off loses ERPNext's share here.
	ERPNext takes it back with frappe's `share.remove`, which deletes the
	DocShare as the person saving and needs System Manager's delete on it, so
	nobody in a workspace could take a member off a project. Whoever may save
	the project may say who is on it; ERPNext then finds nothing left to take
	back."""
	before = doc.get_doc_before_save()
	if not before:
		return
	gone = {row.user for row in before.get("users") or []} - {row.user for row in doc.get("users") or []}
	for user in gone:
		for share in frappe.get_all(
			"DocShare",
			filters={"share_doctype": "Project", "share_name": doc.name, "user": user},
			pluck="name",
		):
			frappe.delete_doc("DocShare", share, ignore_permissions=True)


def nobody(doc, method=None) -> None:
	"""Project before_validate: Administrator runs no project. The manager
	defaults to whoever makes it, and a project made by a script, a patch or
	OneAI working for nobody was otherwise run by a person nobody can ask, or
	even see (frappe hides Administrator from everyone else)."""
	if doc.get("one_manager") in ("Administrator", "Guest"):
		doc.one_manager = None
