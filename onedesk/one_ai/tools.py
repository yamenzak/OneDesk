"""What a model may ask for, and what it may only suggest.

Everything a person can do here a tool can do — read a list, read a record,
count, look at a type, create, edit, delete — and the difference between the
first four and the last three is the whole of this module's design:

**A read runs. A create, an edit or a delete becomes a card.** Nothing in here
writes. A write tool checks the asker's permission for the verb, writes an
`AI Proposal` and hands back its id, and the doing happens when a person presses
Apply. A tool that saved would be a tool that saves on a model's say-so, and the
failure mode is not a wrong field — it is a wrong *record*, at the end of a
chain of lookups nobody read.

**Every tool runs as the session user.** Not as Administrator with a filter
bolted on afterwards, and not with `ignore_permissions` anywhere: the same
`frappe.get_list` the browser would have called, under the same permissions, so
a model asked about somebody else's salary gets what that person would get,
which is nothing. This is the one rule in the module with no exception and no
override, and a tool that needs more than its caller has is a tool that does not
ship.

Reading the whole of Frappe this way is the point. The alternative is a
hand-written tool per doctype, which is out of date the week somebody adds a
field.
"""

import datetime
import decimal
from typing import Annotated

import frappe
from frappe.utils import strip_html_tags

from onedesk.one_ai import memory, proposals, schema

#: Fieldtypes never handed to a model, whatever the caller may see. A password
#: is a credential rather than a fact about a record, and a model that can read
#: one can put it in an answer.
NEVER_READ = ("Password",)

#: How many rows a list tool may answer with. A model given five hundred records
#: is a model given five hundred records' worth of somebody's month.
MOST = 100

#: How many links of one kind to name. Past this it is a list, not an answer.
MOST_LINKS = 20

#: How many report rows. A report is exactly the thing that answers with
#: thousands, and every one of them is a row somebody pays tokens for.
MOST_REPORT = 50


# --------------------------------------------------------------- what it reads


def list_records(
	doctype: Annotated[str, "The type of record to look in, spelled as it is on screen."],
	filters: Annotated[dict, "Field name to value. All of them have to match."] | None = None,
	fields: Annotated[list, "Which fields to answer with. Defaults to what a list shows."]
	| None = None,
	limit: Annotated[
		int, "At most this many rows. Twenty unless asked for more. To answer with a number, count instead."
	] = 20,
	order_by: Annotated[str, "A field and a direction, such as 'creation desc'."] | None = None,
) -> list:
	"""Find records of one type. Answers only with what the person asking may see.

	`frappe.get_list` and nothing else: the role, the user permissions and every
	`permission_query_conditions` hook apply exactly as they do in the browser.
	"""
	_known(doctype, filters, fields, order_by)
	return frappe.get_list(
		doctype,
		filters=filters or {},
		fields=fields or _shown(doctype),
		order_by=order_by,
		limit_page_length=min(int(limit or 20), MOST),
	)


def _known(doctype: str, filters=None, fields=None, order_by: str | None = None) -> None:
	"""Refuse a field the type does not have, naming the ones it does.

	frappe answers an unknown field with "You do not have permission to access
	field", which is true of no field at all and reads to a model as "this
	cannot be done" — so it stops, where told the real names it would have
	tried again. The list is what describe_type would say, cut to what can be
	filtered on.
	"""
	_type(doctype)
	meta = frappe.get_meta(doctype)
	named = []
	if isinstance(filters, dict):
		named += list(filters)
	elif isinstance(filters, list):
		named += [one[-3] for one in filters if isinstance(one, list | tuple) and len(one) >= 3]
	named += [one for one in fields or [] if isinstance(one, str) and one.isidentifier()]
	if order_by:
		named.append(order_by.split()[0].split(".")[-1].strip("`"))
	unknown = [one for one in named if not meta.has_field(one) and one not in frappe.model.default_fields]
	if unknown:
		frappe.throw(
			f"{doctype} has no field {', '.join(unknown)}. Its fields: {', '.join(proposals.fields_of(meta))}, "
			"plus name, owner, creation and modified."
		)
	# A link filtered on a record that does not exist matches nothing, and an
	# empty answer reads to a model as "there are none" — "Annual" for a leave
	# type called "Annual Leave". A read changes nothing, so the one record it
	# plainly meant is used; anything less plain is said, with the values there
	# are, and the model left to choose.
	for field, value in (filters or {}).items() if isinstance(filters, dict) else ():
		df = meta.get_field(field)
		if df and df.fieldtype == "Link" and isinstance(value, str) and value and not frappe.db.exists(df.options, value):
			try:
				there = frappe.get_list(df.options, pluck="name", limit_page_length=200)
			except frappe.PermissionError:
				there = []
			meant = _meant(value, there)
			if meant:
				filters[field] = meant
				continue
			frappe.throw(f"There is no {df.options} called {value!r}. There are: {', '.join(map(str, there[:20]))}.")


def _type(doctype: str, name: str | None = None) -> str:
	"""The type a record really is, when the model named one that is not.

	A small model reads "HR-EXP-2026-00004" and asks for the type "HR-EXP";
	frappe answers with a module import error that reads to it as "deleted".
	With an id to go on, frappe's own search says what it is — used when
	exactly one record the reader may see has that id — and otherwise the
	model is told there is no such type and where to look.
	"""
	if doctype and frappe.db.exists("DocType", doctype):
		return doctype
	if name:
		found = [one["doctype"] for one in search_everywhere(name) if one["name"] == name]
		if len(set(found)) == 1:
			return found[0]
	frappe.throw(
		f"There is no type called {doctype!r}. Use search_everywhere to find what a record is, "
		"or the type's name as it is on screen."
	)


def _meant(said: str, there: list) -> str | None:
	"""The one value `said` plainly names: the same ignoring case, or the only
	one that contains it."""
	low = said.strip().lower()
	same = [one for one in there if str(one).lower() == low]
	if len(same) == 1:
		return same[0]
	holding = [one for one in there if low and low in str(one).lower()]
	return holding[0] if len(holding) == 1 else None


def read_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
) -> dict:
	"""Read one record in full, if the person asking may see it."""
	doctype = _type(doctype, name)
	held = frappe.get_doc(doctype, name)
	held.check_permission("read")
	return _without_secrets(doctype, held.as_dict())


def count_records(
	doctype: Annotated[str, "The type of record to count."],
	filters: Annotated[dict, "Field name to value. All of them have to match."] | None = None,
) -> int:
	"""Count records of one type, counting only what the person asking may see."""
	_known(doctype, filters)
	return len(
		frappe.get_list(
			doctype, filters=filters or {}, fields=["name"], limit_page_length=0
		)
	)


def describe_type(
	doctype: Annotated[str, "The type of record to describe."],
) -> dict:
	"""The fields one type of record has: which are required, what each may
	hold, and which the system fills in itself. Read it before suggesting a new
	record of a type whose fields are not already known."""
	if not frappe.has_permission(doctype, ptype="read"):
		frappe.throw(
			frappe._("You may not read {0}.").format(doctype), frappe.PermissionError
		)
	return {"doctype": doctype, "fields": _fields(frappe.get_meta(doctype))}


LAYOUT = proposals.LAYOUT


def _fields(meta, depth: int = 0) -> list[dict]:
	"""A type's fields as a model needs them to fill a form in.

	Hidden fields are left out — that is how a workspace takes a field away,
	Company among them — and so is anything the reader may not see. A field
	the system fills (read only, or fetched from a link) is said to be, so the
	model neither asks for it nor invents it.
	"""
	said = []
	for f in meta.fields:
		if f.fieldtype in LAYOUT or f.fieldtype in NEVER_READ or f.hidden:
			continue
		one = {"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype}
		if f.reqd:
			one["required"] = True
		if f.mandatory_depends_on:
			one["required_when"] = f.mandatory_depends_on
		if f.depends_on:
			one["shown_when"] = f.depends_on
		if f.read_only or f.fetch_from:
			one["filled_by_the_system"] = True
		if f.default not in (None, ""):
			one["default"] = f.default
		if f.fieldtype == "Select":
			one["options"] = [o for o in (f.options or "").split("\n") if o]
		elif f.fieldtype in ("Link", "Dynamic Link"):
			one["links_to"] = f.options
		elif f.fieldtype in frappe.model.table_fields and depth == 0:
			one["rows"] = _fields(frappe.get_meta(f.options), depth + 1)
		if f.description:
			one["description"] = strip_html_tags(f.description)[:200]
		said.append(one)
	return said


# ------------------------------------------------------ what it may only suggest


def create_record(
	doctype: Annotated[str, "The type of record to create."],
	values: Annotated[dict, "Field name to value."],
	why: Annotated[str, "One sentence on what this is for."] | None = None,
) -> dict:
	"""Suggest creating a record. Nothing is created until a person approves it."""
	return _card(proposals.propose("Create", doctype, changes=values, why=why))


def edit_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	changes: Annotated[dict, "Field name to new value. Only the fields that change."],
	why: Annotated[str, "One sentence on what this is for."] | None = None,
) -> dict:
	"""Suggest changing a record. Nothing changes until a person approves it."""
	return _card(proposals.propose("Edit", doctype, changes=changes, record=name, why=why))


def move_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	action: Annotated[str, "One of the actions what_can_happen listed for this record."],
	why: Annotated[str, "One sentence on why."] | None = None,
) -> dict:
	"""Suggest moving a record through its workflow. Nothing moves until a person approves it.

	Approving runs the workflow's own transition, so the role it is allowed to
	and the log entry it writes are the workflow's, not ours.
	"""
	return _card(proposals.propose("Move", doctype, changes={"action": action}, record=name, why=why))


def delete_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	why: Annotated[str, "One sentence on why."] | None = None,
) -> dict:
	"""Suggest deleting a record. Nothing is deleted until a person approves it."""
	return _card(proposals.propose("Delete", doctype, record=name, why=why))


#: What runs when a model asks for it.
def search_everywhere(
	text: Annotated[str, "Words to look for: a name, a code, a phrase."],
	doctype: Annotated[str, "Only this type of record, if known."] | None = None,
) -> list:
	"""Search every kind of record at once, the way the desk's search bar does.
	Use it when you do not know what type something is — "Omar", "the Dubai
	office", "INV-0042" — then read what it finds."""
	from frappe.utils.global_search import search

	# frappe's own search: the workspace's Global Search Settings say which
	# types are indexed, and every hit is checked with has_permission on the
	# record itself before it is answered, so nothing the reader may not open
	# is named.
	found = search(text or "", limit=MOST_FOUND, doctype=doctype or "")
	return [
		{
			"doctype": one.doctype,
			"name": one.name,
			"title": one.get("title") or one.name,
			"matched": " ".join(str(one.content or "").replace("|||", "·").split())[:200],
		}
		for one in found
	]


#: How many hits `search_everywhere` answers with.
MOST_FOUND = 10


def find_records(
	doctype: Annotated[str, "The type of record to search in."],
	text: Annotated[str, "What to search for — a name, a code, part of a title."],
	limit: Annotated[int, "At most this many matches."] = 10,
) -> list:
	"""Find records by what they are called, rather than by an exact field value.

	This is the tool for turning "Apple" into a supplier's id. Frappe's own link
	search is what a person gets typing into a Link field, including whatever
	`search_fields` the doctype declares, so a model using it finds what a
	person would have found.
	"""
	from frappe.desk.search import search_widget

	if not frappe.has_permission(doctype, ptype="read"):
		frappe.throw(frappe._("You may not read {0}.").format(doctype), frappe.PermissionError)

	found = search_widget(
		doctype=doctype, txt=text or "", page_length=min(int(limit or 10), MOST)
	)
	return [
		{"name": row[0], "label": " — ".join(str(cell) for cell in row[1:] if cell)}
		for row in (found or [])
	]


def what_links_here(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
) -> dict:
	"""What else in the workspace points at this record.

	The question behind "can I delete this" and behind "what happened to that
	order". Frappe already knows — every Link field is an edge — so the answer
	is read rather than guessed at from what a model remembers about ERPNext.
	"""
	from frappe.desk.form.linked_with import get as linked

	if not frappe.has_permission(doctype, doc=name, ptype="read"):
		frappe.throw(frappe._("You may not read {0} {1}.").format(doctype, name), frappe.PermissionError)

	found = linked(doctype=doctype, docname=name) or {}
	said = {}
	for kind, rows in found.items():
		# v17 answers {"docs": [...], "hidden_count": n} per type — n being the
		# ones the reader may not see, said as a number and never as names.
		hidden = rows.get("hidden_count", 0) if isinstance(rows, dict) else 0
		rows = rows.get("docs", []) if isinstance(rows, dict) else rows
		names = [row.get("name") for row in rows or [] if isinstance(row, dict)][:MOST_LINKS]
		if names or hidden:
			said[kind] = {"names": names, "not_visible_to_the_reader": hidden} if hidden else names
	return said


def what_can_happen(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
) -> dict:
	"""Where this record can go next, if it is under a workflow.

	A record in a workflow has exactly the moves its workflow allows, to the
	roles it allows them to. Reading them is how a suggestion can be one of
	them rather than a guess at what the buttons say.
	"""
	from frappe.model.workflow import get_transitions

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	# Most doctypes have no workflow, and "this one has none" is an answer a
	# model can use. Asking frappe for the transitions of a doctype without one
	# raises, which would come back as a refusal and read like a permission.
	state = _state_field(doctype)
	if not state:
		return {"doctype": doctype, "name": name, "state": None, "workflow": False, "can": []}

	moves = get_transitions(doc) or []
	return {
		"doctype": doctype,
		"name": name,
		"state": doc.get(state),
		"workflow": True,
		"can": [{"action": one.get("action"), "to": one.get("next_state")} for one in moves],
	}


def run_report(
	report: Annotated[str, "The report's name, as it is on screen."],
	filters: Annotated[dict, "The report's own filters, by fieldname."] | None = None,
	limit: Annotated[int, "At most this many rows of the answer."] = 20,
) -> dict:
	"""Run one of the workspace's own reports and answer with its rows.

	A report is an answer somebody already wrote down and tested — running it
	beats a model inventing an aggregation over rows it listed. The rows are
	capped because a report is exactly the thing that answers with thousands.
	"""
	from frappe.desk.query_report import run as ran

	if not frappe.has_permission("Report", doc=report, ptype="read"):
		frappe.throw(frappe._("You may not run {0}.").format(report), frappe.PermissionError)

	out = ran(report_name=report, filters=filters or {}, are_default_filters=False) or {}
	rows = out.get("result") or []
	kept = min(int(limit or 20), MOST_REPORT)
	return {
		"report": report,
		"columns": [_column(one) for one in (out.get("columns") or [])],
		"rows": rows[:kept],
		"more": max(len(rows) - kept, 0),
	}


def _state_field(doctype: str) -> str | None:
	name = frappe.db.get_value("Workflow", {"document_type": doctype, "is_active": 1}, "workflow_state_field")
	return name or None


def _column(one) -> str:
	if isinstance(one, dict):
		return one.get("label") or one.get("fieldname") or ""
	return str(one)


READS = (
	list_records,
	read_record,
	count_records,
	describe_type,
	find_records,
	search_everywhere,
	what_links_here,
	what_can_happen,
	run_report,
	memory.about_record,
	memory.recall,
	memory.search_my_chats,
)

#: What becomes a card instead. Named separately rather than flagged, because a
#: tool moving from one tuple to the other is a line in a diff somebody reviews.
SUGGESTS = (create_record, edit_record, delete_record, move_record)

#: What runs at once although it writes: only the asker's own memory, which no
#: one else reads and they can undo from the line it leaves in the chat. A card
#: asking them to approve "Omar is our CFO", which they just said, was a card
#: nobody wanted.
KEEPS = (memory.remember,)

BY_NAME = {fn.__name__: fn for fn in READS + SUGGESTS}


def hooked() -> tuple[tuple, tuple]:
	"""The tools a module adds, as reads and as suggestions.

	Named in `hooks.py` under `one_ai_reads` and `one_ai_suggests`, so a module
	owns what OneAI can do in it — OneHR's live in `one_hr/ai.py` — and the two
	lists stay two lists for the reason these tuples do. The rules are the same:
	a read runs as the person asking, and a suggestion writes a card.
	"""
	reads = tuple(frappe.get_attr(path) for path in frappe.get_hooks("one_ai_reads") or [])
	suggests = tuple(frappe.get_attr(path) for path in frappe.get_hooks("one_ai_suggests") or [])
	return reads, suggests


def _every() -> tuple[tuple, tuple]:
	"""What runs now (reads, and keeping a memory) and what becomes a card."""
	reads, suggests = hooked()
	return READS + KEEPS + reads, SUGGESTS + suggests


def declared() -> list[dict]:
	"""Every tool, as a provider's function declaration."""
	reads, suggests = _every()
	return [schema.of(fn) for fn in reads + suggests]


def run(name: str, args: dict | None = None) -> dict:
	"""Call one tool as the person asking, and say whether it happened.

	`ran` is the thing a model has to be told: a read happened and here is the
	answer; a write did not happen and here is the card somebody has to approve.
	"""
	reads, suggests = _every()
	fn = {one.__name__: one for one in reads + suggests}.get(name)
	if not fn:
		frappe.throw(frappe._("{0} is not a tool.").format(name))
	answer = fn(**(args or {}))
	return {"tool": name, "ran": fn in reads, "answer": _plain(answer)}


def _plain(said):
	"""The answer, in types JSON has.

	A row out of the database carries `date`, `datetime` and `Decimal`, and the
	result of a tool goes back to the model over HTTP — so a date left as a date
	is not a display problem, it is the round that fails to serialise.
	"""
	if isinstance(said, dict):
		return {key: _plain(value) for key, value in said.items()}
	if isinstance(said, (list, tuple)):
		return [_plain(one) for one in said]
	if isinstance(said, (datetime.datetime, datetime.date, datetime.time, datetime.timedelta)):
		return str(said)
	if isinstance(said, decimal.Decimal):
		return float(said)
	return said


def _card(proposal: str) -> dict:
	return {
		"proposal": proposal,
		"state": "Proposed",
		"said": frappe._("Suggested. It happens when somebody approves it."),
	}


def _shown(doctype: str) -> list[str]:
	"""What a list of this type shows, which is what somebody would have seen."""
	meta = frappe.get_meta(doctype)
	fields = ["name"] + [f.fieldname for f in meta.fields if f.in_list_view and f.fieldtype not in NEVER_READ]
	if meta.title_field and meta.title_field not in fields:
		fields.append(meta.title_field)
	return fields


def _without_secrets(doctype: str, said: dict) -> dict:
	secret = {f.fieldname for f in frappe.get_meta(doctype).fields if f.fieldtype in NEVER_READ}
	return {key: value for key, value in said.items() if key not in secret}
