"""Telling people about a project (one_project/notifications.py).

**Added to a project.** ERPNext mails each new member its own "Project
Collaboration Invitation", in English, outside the hub. `members.invite`
marks that mail sent, and `added` tells them in ours: on the bell, and by
email or push as they chose, in their language.

**Made its manager.** Nobody was told. `added` tells the new manager too.

**At risk.** Health is somebody's judgement that a project is in trouble
before any figure says so. `health` tells its manager and members when it is
marked At Risk or Off Track; whoever marked it already knows.
"""

import frappe
from frappe.utils import formatdate, get_fullname

from onedesk.one import notify

#: The health worth telling people about.
WORSE = ("At Risk", "Off Track")


def changed(doc, method=None) -> None:
	"""Project on_update: who was added, who now runs it, and how it is going."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch:
		return
	before = doc.get_doc_before_save()
	added(doc, before)
	health(doc, before)


def added(doc, before) -> None:
	was = {row.user for row in (before.get("users") or [])} if before else set()
	new = sorted({row.user for row in doc.get("users") or []} - was - {"Administrator", "Guest"})
	facts = _facts(doc)
	if new:
		notify.notify("Added to Project", new, record=("Project", doc.name), **facts)
	manager = doc.get("one_manager")
	if (
		manager
		and manager != (before.get("one_manager") if before else None)
		and manager not in ("Administrator", "Guest")
	):
		notify.notify("Made Project Manager", manager, record=("Project", doc.name), **facts)


def health(doc, before) -> None:
	said = doc.get("one_health")
	if said not in WORSE or not before or before.get("one_health") == said:
		return
	people = {row.user for row in doc.get("users") or []} | {doc.get("one_manager")}
	people = sorted(one for one in people if one and one not in ("Administrator", "Guest"))
	if people:
		notify.notify("Project Health", people, record=("Project", doc.name), health=said, **_facts(doc))


def _facts(doc) -> dict:
	"""Who did it, the project, and its customer and end date, each led by a
	dot so either may be left out: " · Mansour & Sons · 3 Nov 2026"."""
	return {
		"who": get_fullname(frappe.session.user),
		"project": doc.project_name,
		"customer": f" · {doc.customer}" if doc.get("customer") else "",
		"due": f" · {formatdate(doc.expected_end_date)}" if doc.get("expected_end_date") else "",
	}
