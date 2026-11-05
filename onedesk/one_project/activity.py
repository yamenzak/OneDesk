"""A project's history in its form's Activity, across it and its
sub-projects: the documents made for it, its tasks, the time logged on it and
the sub-projects started under it.
"""

import re
from collections import defaultdict

import frappe
from babel.lists import format_list
from frappe import _
from frappe.utils import add_days, escape_html, flt, fmt_money, get_datetime, get_fullname, getdate

from onedesk.one_project import hours, money, tree

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
ON_LINES = {**money.LINES, "Journal Entry": "Journal Entry Account"}
CURRENCY = {"Payment Entry": "paid_from_account_currency"}
SAME_SITTING = 30 * 60


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
		lambda one: (week_of(one.from_time), one.project),
	):
		logged = defaultdict(float)
		for one in group:
			logged[sheets[one.parent]["key"]] += one.hours or 0
		order = sorted(logged, key=lambda key: -logged[key])
		named = {sheets[one.parent]["key"]: sheets[one.parent] for one in group}
		first = named[order[0]]
		found.append(
			_row(
				"time",
				f"{week_of(group[0].from_time)}:{group[0].project}",
				max(one.to_time or one.from_time for one in group),
				people(first["user"], first["name"])
				if len(order) == 1
				else {"fullname": _listed([named[key]["name"] for key in order])},
				"work",
				{
					"hours": round(sum(one.hours or 0 for one in group), 2),
					"days": len({getdate(one.from_time) for one in group}),
					"people": len(order),
					"project": group[0].project,
				},
			)
		)
	return found


def _listed(names: list[str]) -> str:
	"""Names as the reader's language lists them: "A and B", "A, B and C"."""
	try:
		return format_list(names, locale=(frappe.local.lang or "en").replace("-", "_"))
	except Exception:
		return format_list(names, locale="en")


def week_of(when) -> str:
	"""The Monday of the week a time falls in. Pure."""
	day = getdate(when)
	return str(add_days(day, -day.weekday()))


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


SHOWN = 100

ICONS = {"document": "file-text", "tasks": "list-plus", "task": "circle-check", "time": "clock", "started": "folder-plus"}


def timeline(doctype: str, docname: str) -> list[dict]:
	"""additional_timeline_content for Project: what was made, submitted and
	cancelled for it and its sub-projects, the tasks added and finished, the
	time logged each week and the sub-projects started, newest first. Its
	updates come from updates.timeline, and its mail and files from frappe."""
	if not frappe.has_permission("Project", "read", doc=docname):
		return []
	projects = sorted(tree.scope(docname))
	titles = dict(frappe.get_all("Project", filters={"name": ["in", projects]}, fields=["name", "project_name"], as_list=True))
	people = _People()
	rows = [
		*_documents(projects, people),
		*_tasks(projects, people),
		*_time(projects, people),
		*(one for one in _started(projects, docname, people) if one["data"]["sub"]),
	]
	rows = sorted(rows, key=lambda one: (one["timestamp"], one["key"]), reverse=True)[:SHOWN]
	return [
		{
			"icon": "file-x" if one["data"].get("verb") == "cancelled" else ICONS[one["type"]],
			"creation": one["timestamp"],
			"content": said(one, titles.get(one["data"].get("project")) if one["data"].get("project") != docname else None),
		}
		for one in rows
	]


def _link(route: str, text: str) -> str:
	return f'<a href="{escape_html(route)}">{escape_html(text)}</a>'


def said(row: dict, where: str | None) -> str:
	"""One activity row as the sentence the timeline shows: who, what they did
	and, quieter, on what and in which sub-project."""
	data = row["data"]
	who = f"<strong>{escape_html(row['author'].get('fullname') or '')}</strong>"
	aside = []
	if row["type"] == "document":
		verb = {"created": _("created"), "submitted": _("submitted"), "cancelled": _("cancelled")}[data["verb"]]
		doctype = data["doctype"]
		what = f"{verb} {escape_html(_(doctype))} {_link(data['route'], data['name'])}"
		aside = [data.get("party"), fmt_money(data["amount"], currency=data.get("currency")) if data.get("amount") else None]
	elif row["type"] == "tasks":
		first = data["tasks"][0]
		what = (
			f"{_('added task')} {_link('/desk/task/' + first['name'], first['subject'])}"
			if data["count"] == 1
			else escape_html(_("added {0} tasks").format(data["count"]))
		)
		if data["count"] > 1:
			aside = [", ".join(one["subject"] for one in data["tasks"])]
	elif row["type"] == "task":
		what = f"{_('completed')} {_link('/desk/task/' + data['name'], data['subject'])}"
	elif row["type"] == "time":
		hours_ = _("{0} h").format(f"{flt(data['hours'], 1):g}")
		what = escape_html(_("logged {0} over {1} days").format(hours_, data["days"]) if data["days"] > 1 else _("logged {0}").format(hours_))
	else:
		what = f"{_('started sub-project')} {_link('/desk/project/' + data['name'], data['title'])}"
	aside.append(where)
	quiet = " · ".join(escape_html(str(one)) for one in aside if one)
	return f"{who} {what}" + (f' <span class="text-muted">· {quiet}</span>' if quiet else "")
