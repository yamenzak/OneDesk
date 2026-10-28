"""Who sees a project: its members."""

from contextlib import contextmanager

import frappe
from frappe import _

BOOKS = ("Accounts User", "Accounts Manager")

WORKER = "Projects User"


def manages(user: str) -> bool:
	"""Whether this person sees every project: OneProject's See Every Project
	(abilities.py), a OneProject Manager's."""
	from onedesk.one import rights

	return rights.held("Project", "project_every", user)


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


def enabled(doc, method=None) -> None:
	"""Project validate: somebody new among its members is a user who can sign
	in, however they were added (Team, the desk form, an import). Somebody
	disabled later stays listed."""
	before = doc.get_doc_before_save()
	had = {row.user for row in before.get("users") or []} if before else set()
	for row in doc.get("users") or []:
		if row.user and row.user not in had and not frappe.db.exists("User", {"name": row.user, "enabled": 1}):
			frappe.throw(_("{0} can't sign in, so can't join the project.").format(row.user))


def join(project: str, user: str) -> bool:
	"""Make somebody a member of the project, whoever is saving. ERPNext then
	shares it with them, and Added to Project tells them (tell.py). False
	when they're a member already or aren't a user who can sign in."""
	if not user or user in ("Administrator", "Guest"):
		return False
	if not frappe.db.exists("User", {"name": user, "enabled": 1}):
		return False
	if frappe.db.exists("Project User", {"parenttype": "Project", "parent": project, "user": user}):
		return False
	doc = frappe.get_doc("Project", project)
	doc.append("users", {"user": user})
	doc.flags.ignore_permissions = True
	if frappe.has_permission("Project", "share", doc=project):
		doc.save()
	else:
		with _as_administrator():
			doc.save()
	forget()
	return True


@contextmanager
def _as_administrator():
	"""Save as Administrator, then give the request its own session back."""
	session = frappe.local.session
	held, asked = dict(session), frappe.local.form_dict
	frappe.flags.one_acting_for = frappe.session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.flags.one_acting_for = None
		session.clear()
		session.update(held)
		frappe.local.form_dict = asked
		frappe.local.role_permissions = {}
		frappe.local.user_perms = None


def _stays_out(project: str | None, user: str | None) -> bool:
	"""Whether somebody given work on the project can't open the project."""
	return bool(project and user) and not sees(project, user)


def assigned(doc, method=None) -> None:
	"""ToDo after_insert: a task given to somebody who can't open its project
	makes them a member, as frappe shares a record with whoever is assigned
	it. They're told in Added to Project; whoever assigned it, here."""
	if doc.reference_type != "Task" or doc.status == "Cancelled":
		return
	project = frappe.db.get_value("Task", doc.reference_name, "project")
	if not _stays_out(project, doc.allocated_to) or not join(project, doc.allocated_to):
		return
	frappe.msgprint(
		_("{0} was added to {1}.").format(
			frappe.utils.get_fullname(doc.allocated_to), frappe.db.get_value("Project", project, "project_name")
		),
		alert=True,
	)


def shared(doc, method=None) -> None:
	"""DocShare after_insert: on a project, sharing is membership, so whoever
	it's shared with joins it (the sidebar's Share is Add Member there)."""
	if doc.share_doctype == "Project" and doc.user and not doc.everyone:
		join(doc.share_name, doc.user)


@frappe.whitelist()
@frappe.read_only()
def joins(project: str, user: str) -> str | None:
	"""Who joins the project if given a task on it, by name: nobody when
	they can open it already."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	if not _stays_out(project, user) or not frappe.db.exists("User", {"name": user, "enabled": 1}):
		return None
	return frappe.utils.get_fullname(user)


@frappe.whitelist()
@frappe.read_only()
def unseen(project: str, content: str) -> dict:
	"""Who a comment mentions that can't open the project, for the page to
	ask whether to add them before it's posted (frappe tells them of the
	mention, but gives them no way in)."""
	from frappe.desk.notifications import extract_mentions

	frappe.has_permission("Project", "read", doc=project, throw=True)
	people = [user for user in dict.fromkeys(extract_mentions(content) or []) if _stays_out(project, user)]
	people = [user for user in people if frappe.db.exists("User", {"name": user, "enabled": 1})]
	return {
		"people": [{"user": user, "name": frappe.utils.get_fullname(user)} for user in people],
		"can_add": bool(frappe.has_permission("Project", "write", doc=project)),
	}


@frappe.whitelist(methods=["POST"])
def let_in(project: str, users: list | str) -> None:
	"""Add the people a comment mentions to the project."""
	frappe.has_permission("Project", "write", doc=project, throw=True)
	for user in frappe.parse_json(users) or []:
		join(project, user)
