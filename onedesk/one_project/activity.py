"""A project's history, across it and its sub-projects: the documents made
for it, its tasks, the time logged on it, the team's updates, files added,
and the sub-projects started under it.

The Activity view puts these beside frappe's own timeline of the project,
which keeps its comments, its emails and the changes to its fields (Project
tracks its changes, `custom/project.json`). Each row here is one of
frappe's ActivityTimeline rows (`type`, `key`, `timestamp`, `author`,
`data`), with a `kind`: `money` for documents, `work` for the rest.

A document shows when it was made, submitted and cancelled, read from the
Version frappe keeps of it, or from the document itself where its type keeps
none. Tasks added in one day are one row, as are a person's hours in a day
and the files somebody added in a day.
"""

import re
from collections import defaultdict
from typing import Annotated

import frappe
from frappe.utils import get_datetime, get_fullname, getdate

from onedesk.one_project import hours, money, tree

#: The documents a project has, and on each its party and its amount.
DOCUMENTS = {
	"Quotation": ("customer_name", "grand_total"),
	"Sales Order": ("customer_name", "grand_total"),
	"Delivery Note": ("customer_name", "grand_total"),
	"Sales Invoice": ("customer_name", "grand_total"),
	"Material Request": (None, None),
	"Request for Quotation": (None, None),
	"Supplier Quotation": ("supplier_name", "grand_total"),
	"Purchase Order": ("supplier_name", "grand_total"),
	"Purchase Receipt": ("supplier_name", "grand_total"),
	"Purchase Invoice": ("supplier_name", "grand_total"),
	"Payment Entry": ("party_name", "paid_amount"),
	"Journal Entry": (None, "total_debit"),
	"Expense Claim": ("employee_name", "total_claimed_amount"),
	"Stock Entry": (None, "total_outgoing_value"),
}
#: Documents that may name the project on their lines only.
ON_LINES = {**money.LINES, "Journal Entry": "Journal Entry Account"}
#: Where an amount's currency is, when it isn't the company's.
CURRENCY = {"Payment Entry": "paid_from_account_currency"}
#: How many rows a page holds.
PAGE = 60
#: A draft submitted this soon by whoever made it is one row, not two.
SAME_SITTING = 30 * 60
#: A file is a photo by its name.
PHOTO = re.compile(r"\.(jpe?g|png|gif|webp|heic|avif)$", re.I)


@frappe.whitelist()
@frappe.read_only()
def activity(
	project: Annotated[str, "The project."],
	before: Annotated[str | None, "Only what happened before this time, for the next page."] = None,
) -> dict:
	"""A page of the project's history, newest first."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	projects = sorted(tree.below({project}, tree.parents()))
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", projects]}, fields=["name", "project_name"], as_list=True
		)
	)
	people = _People()
	rows = [
		*_documents(projects, people),
		*_tasks(projects, people),
		*_time(projects, people),
		*_updates(projects, people),
		*_files(projects, people),
		*_started(projects, project, people),
	]
	for row in rows:
		where = row["data"].get("project")
		row["data"]["sub_project"] = titles.get(where) if where and where != project else None
	shown, more = page(rows, before)
	return {"activities": shown, "more": more}


def page(rows: list[dict], before: str | None, size: int = PAGE) -> tuple[list[dict], bool]:
	"""The newest `size` rows before `before`, and whether older ones are
	left. Pure."""
	rows = sorted(
		(one for one in rows if not before or one["timestamp"] < before),
		key=lambda one: (one["timestamp"], one["key"]),
		reverse=True,
	)
	return rows[:size], len(rows) > size


def events(doc: dict, moves: list[tuple]) -> list[tuple]:
	"""What happened to one document, as (verb, when, who): made, submitted,
	cancelled. `moves` are its Versions that changed its docstatus, as (when,
	who, docstatus). Without them, a submitted or cancelled document is taken
	to have been so when it was last changed. A draft submitted in the same
	sitting by whoever made it is one row. Pure."""
	said = [("created", str(doc["creation"]), doc["owner"])]
	for when, who, to in sorted(moves):
		said.append(("submitted" if to == 1 else "cancelled", str(when), who))
	if doc["docstatus"] and not any(
		one[0] == ("submitted" if doc["docstatus"] == 1 else "cancelled") for one in said
	):
		said.append(
			("submitted" if doc["docstatus"] == 1 else "cancelled", str(doc["modified"]), doc["modified_by"])
		)
	submitted = next((one for one in said if one[0] == "submitted"), None)
	if (
		submitted
		and submitted[2] == doc["owner"]
		and (get_datetime(submitted[1]) - get_datetime(said[0][1])).total_seconds() <= SAME_SITTING
	):
		said.pop(0)
	return said


def moved(data: str) -> int | None:
	"""The docstatus a Version moved its document to, if it did. Pure."""
	found = re.search(r'\["docstatus",\s*\d,\s*(\d)\]', data or "")
	return int(found.group(1)) if found else None


def grouped(rows: list[dict], key) -> list[list[dict]]:
	"""Rows grouped by `key`, each group in the order the rows came. Pure."""
	groups = defaultdict(list)
	for one in rows:
		groups[key(one)].append(one)
	return list(groups.values())


class _People:
	"""Who did something, as the timeline shows them, looked up once each."""

	def __init__(self):
		self.known = {}

	def __call__(self, user: str | None, name: str | None = None) -> dict:
		if not user:
			return {"fullname": name or ""}
		if user not in self.known:
			image = frappe.db.get_value("User", user, "user_image")
			self.known[user] = {"email": user, "name": user, "fullname": get_fullname(user), "image": image}
		return self.known[user]


def _row(type_: str, key: str, when, author: dict, kind: str, data: dict) -> dict:
	return {
		"type": type_,
		"key": f"{type_}:{key}",
		"timestamp": str(when)[:19],
		"author": author,
		"kind": kind,
		"data": data,
	}


def _documents(projects: list[str], people: _People) -> list[dict]:
	found = []
	for doctype, (party, amount) in DOCUMENTS.items():
		if not frappe.has_permission(doctype, "read"):
			continue
		meta = frappe.get_meta(doctype)
		names = set()
		if meta.has_field("project"):
			names |= set(frappe.get_list(doctype, filters={"project": ["in", projects]}, pluck="name"))
		if doctype in ON_LINES:
			names |= set(
				frappe.get_all(
					ON_LINES[doctype],
					filters={"project": ["in", projects], "parenttype": doctype},
					pluck="parent",
				)
			)
		if not names:
			continue
		fields = ["name", "owner", "creation", "modified", "modified_by", "docstatus", "company"]
		fields += [
			one for one in (party, amount, CURRENCY.get(doctype, "currency")) if one and meta.has_field(one)
		]
		if meta.has_field("project"):
			fields.append("project")
		docs = frappe.get_list(doctype, filters={"name": ["in", list(names)]}, fields=fields)
		moves = defaultdict(list)
		for version in frappe.get_all(
			"Version",
			filters={
				"ref_doctype": doctype,
				"docname": ["in", [one.name for one in docs]],
				"data": ["like", '%"docstatus"%'],
			},
			fields=["docname", "owner", "creation", "data"],
		):
			to = moved(version.data)
			if to:
				moves[version.docname].append((version.creation, version.owner, to))
		for doc in docs:
			data = {
				"doctype": doctype,
				"name": doc.name,
				"party": doc.get(party) if party else None,
				"amount": doc.get(amount) if amount else None,
				"currency": doc.get(CURRENCY.get(doctype, "currency"))
				or frappe.get_cached_value("Company", doc.company, "default_currency"),
				"project": doc.get("project"),
				"route": f"/desk/{frappe.scrub(doctype).replace('_', '-')}/{doc.name}",
			}
			for verb, when, who in events(doc, moves.get(doc.name, [])):
				found.append(
					_row(
						"document",
						f"{doctype}:{doc.name}:{verb}",
						when,
						people(who),
						"money",
						{**data, "verb": verb},
					)
				)
	return found


def _tasks(projects: list[str], people: _People) -> list[dict]:
	tasks = frappe.get_list(
		"Task",
		filters={"project": ["in", projects]},
		fields=[
			"name",
			"subject",
			"project",
			"owner",
			"creation",
			"status",
			"completed_on",
			"completed_by",
			"modified",
			"modified_by",
		],
		order_by="creation asc",
		limit_page_length=0,
	)
	found = []
	for group in grouped(tasks, lambda one: (one.owner, one.project, getdate(one.creation))):
		first = group[-1]
		found.append(
			_row(
				"tasks",
				f"{first.name}:{len(group)}",
				max(one.creation for one in group),
				people(first.owner),
				"work",
				{
					"count": len(group),
					"tasks": [{"name": one.name, "subject": one.subject} for one in group[:3]],
					"project": first.project,
				},
			)
		)
	for one in tasks:
		if one.status != "Completed" or not one.completed_on:
			continue
		when = (
			one.modified
			if getdate(one.modified) == getdate(one.completed_on)
			else f"{one.completed_on} 00:00:00"
		)
		found.append(
			_row(
				"task",
				f"{one.name}:done",
				when,
				people(one.completed_by or one.modified_by),
				"work",
				{"name": one.name, "subject": one.subject, "project": one.project},
			)
		)
	return found


def _time(projects: list[str], people: _People) -> list[dict]:
	rows = frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters=[["Timesheet Detail", "project", "in", projects], ["Timesheet", "docstatus", "<", 2]],
		fields=["parent", "hours", "from_time", "to_time", "project"],
		limit_page_length=0,
	)
	sheets = hours.whose({one.parent for one in rows})
	found = []
	for group in grouped(
		[one for one in rows if one.from_time and sheets.get(one.parent)],
		lambda one: (sheets[one.parent]["key"], getdate(one.from_time), one.project),
	):
		sheet = sheets[group[0].parent]
		found.append(
			_row(
				"time",
				f"{sheet['key']}:{getdate(group[0].from_time)}:{group[0].project}",
				max(one.to_time or one.from_time for one in group),
				people(sheet["user"], sheet["name"]),
				"work",
				{"hours": round(sum(one.hours or 0 for one in group), 2), "project": group[0].project},
			)
		)
	return found


def _updates(projects: list[str], people: _People) -> list[dict]:
	from onedesk.one_project.ai import plain

	asked = dict(
		frappe.get_all(
			"Project Update", filters={"project": ["in", projects]}, fields=["name", "project"], as_list=True
		)
	)
	if not asked:
		return []
	return [
		_row(
			"update",
			one.name,
			one.modified,
			people(one.user),
			"work",
			{"text": plain(one.project_status)[:600], "health": one.one_health, "project": asked[one.parent]},
		)
		for one in frappe.get_all(
			"Project User",
			filters={
				"parenttype": "Project Update",
				"parent": ["in", list(asked)],
				"project_status": ["is", "set"],
			},
			fields=["name", "parent", "user", "project_status", "one_health", "modified"],
		)
	]


def _files(projects: list[str], people: _People) -> list[dict]:
	logs = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Project",
			"reference_name": ["in", projects],
			"comment_type": ["in", ["Attachment", "Attachment Removed"]],
		},
		fields=["name", "owner", "creation", "comment_type", "content", "reference_name"],
		order_by="creation asc",
	)
	found = []
	for group in grouped(
		logs, lambda one: (one.owner, one.reference_name, one.comment_type, getdate(one.creation))
	):
		named = [re.sub(r"<[^>]+>", "", one.content or "").strip() for one in group]
		found.append(
			_row(
				"files",
				f"{group[0].name}:{len(group)}",
				max(one.creation for one in group),
				people(group[0].owner),
				"work",
				{
					"count": len(group),
					"removed": group[0].comment_type == "Attachment Removed",
					"photos": all(PHOTO.search(one) for one in named),
					"names": named[:3],
					"project": group[0].reference_name,
				},
			)
		)
	return found


def _started(projects: list[str], project: str, people: _People) -> list[dict]:
	return [
		_row(
			"started",
			one.name,
			one.creation,
			people(one.owner),
			"work",
			{"name": one.name, "title": one.project_name, "project": one.name, "sub": one.name != project},
		)
		for one in frappe.get_all(
			"Project",
			filters={"name": ["in", projects]},
			fields=["name", "project_name", "owner", "creation"],
		)
	]
