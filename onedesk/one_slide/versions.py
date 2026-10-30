"""A presentation's history. Before a save writes over slides, what they were
is kept, at most every ten minutes; a version can also be kept by name, and
going back to one is itself kept first, so it can be undone. AGENTS.md, History.
"""

import json
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from onedesk.one_slide import api

VERSION = "Presentation Version"

#: How long a stretch of work one unnamed version stands for.
EVERY = timedelta(minutes=10)

#: Unnamed versions kept per presentation; named ones are all kept.
KEPT = 100

#: What a version holds of each slide.
SLIDE = ("client_id", "background", "elements", "transition", "transition_duration", "fade_unmatched_elements", "advance_after")


def _snapshot(name: str) -> str:
	doc = frappe.get_doc(api.PRESENTATION, name)
	return json.dumps([{key: row.get(key) for key in SLIDE} for row in doc.slides])


def _keep(name: str, title: str | None = None) -> str:
	made = frappe.get_doc({"doctype": VERSION, "presentation": name, "title": title or "", "slides": _snapshot(name)})
	made.flags.ignore_permissions = True
	made.insert()
	_trim(name)
	return made.name


def before_saving(name: str) -> None:
	"""save_slides calls this before it writes: what the slides were, kept
	unless the last unnamed version is under ten minutes old."""
	last = frappe.get_all(VERSION, filters={"presentation": name, "title": ""}, fields=["creation"], order_by="creation desc", limit=1)
	if last and now_datetime() - get_datetime(last[0].creation) < EVERY:
		return
	_keep(name)


def _trim(name: str) -> None:
	unnamed = frappe.get_all(VERSION, filters={"presentation": name, "title": ""}, pluck="name", order_by="creation desc")
	for old in unnamed[KEPT:]:
		frappe.delete_doc(VERSION, old, ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def keep(name: str, title: str) -> dict:
	"""The slides as they are now, kept under a name."""
	api._may(name, "write")
	title = api._titled(title)
	if not title:
		frappe.throw(_("A version needs a name."))
	return {"name": _keep(name, title)}


@frappe.whitelist()
@frappe.read_only()
def listed(name: str) -> list[dict]:
	"""The presentation's versions, newest first, with who made each and how many slides it had."""
	api._may(name, "read")
	out = []
	for one in frappe.get_all(VERSION, filters={"presentation": name}, fields=["name", "title", "owner", "creation", "slides"], order_by="creation desc"):
		out.append(
			{
				"name": one.name,
				"title": one.title,
				"by": frappe.utils.get_fullname(one.owner),
				"at": str(one.creation),
				"slides": len(json.loads(one.slides or "[]")),
			}
		)
	return out


@frappe.whitelist(methods=["POST"])
def restore(name: str, version: str) -> dict:
	"""Back to a version. What the slides were just before is kept first."""
	api._may(name, "write")
	held = frappe.db.get_value(VERSION, version, ["presentation", "slides"], as_dict=True)
	if not held or held.presentation != name:
		frappe.throw(_("That version is not of this presentation."), frappe.DoesNotExistError)
	_keep(name, _("Before going back"))
	doc = frappe.get_doc(api.PRESENTATION, name)
	doc.set("slides", json.loads(held.slides or "[]"))
	doc.save(ignore_permissions=True)
	return {"modified": str(doc.modified)}


def forget(name: str) -> None:
	for one in frappe.get_all(VERSION, filters={"presentation": name}, pluck="name"):
		frappe.delete_doc(VERSION, one, ignore_permissions=True)
