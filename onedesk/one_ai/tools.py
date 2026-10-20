"""What a model may ask for, and what it may only suggest.

A read runs. A create, an edit or a delete becomes a card. Every tool runs as
the session user.
"""

import datetime
import decimal
from typing import Annotated

import frappe
from frappe.utils import strip_html_tags

from onedesk.one_ai import guide, kind, memory, proposals, schema

NEVER_READ = ("Password",)

MOST = 100

MOST_LINKS = 20

MOST_REPORT = 50

FILTERS = (
	"Field name to value; all of them have to match. A value may be [operator, value] for anything but "
	'equal: {"grand_total": [">", 1000]}, {"posting_date": ["between", ["2026-01-01", "2026-03-31"]]}, '
	'{"status": ["in", ["Open", "Overdue"]]}, {"customer_name": ["like", "%glass%"]}, '
	'{"email_id": ["is", "set"]}.'
)


def list_records(
	doctype: Annotated[str, "The type of record to look in, spelled as it is on screen."],
	filters: Annotated[dict, FILTERS] | None = None,
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
	if fields and all(isinstance(one, str) and one.isidentifier() for one in fields):
		title = frappe.get_meta(doctype).title_field
		fields = list(dict.fromkeys(["name", *([title] if title else []), *fields]))
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
			f"{doctype} has no field {', '.join(unknown)}. Its fields: {', '.join(kind.fields_of(meta))}, "
			"plus name, owner, creation and modified."
		)
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
	filters: Annotated[dict, FILTERS] | None = None,
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
	return kind.describe(doctype)


LAYOUT = proposals.LAYOUT


POINTING = (
	"A value may point at a record another card of this conversation will make, before it exists: "
	"give @ and that card's id, such as @PROP-26-000042. Approving this card approves that one first."
)


def create_record(
	doctype: Annotated[str, "The type of record to create."],
	values: Annotated[dict, "Field name to value. " + POINTING],
	why: Annotated[str, "One sentence on what this is for."] | None = None,
) -> dict:
	"""Suggest creating a record. Nothing is created until a person approves it.
	To make several records that belong together (a customer, then a quotation
	for them, then a task to follow it up) in one step, use create_records."""
	return _card(proposals.propose("Create", doctype, changes=values, why=why))


def create_records(
	records: Annotated[
		list[dict],
		"The records, in the order they are made. Each is {\"ref\": a short name of your own, "
		"\"doctype\": the type, \"values\": field name to value, \"why\": one sentence}. A value may be "
		"@ and an earlier record's ref, to point at the record that one makes; or @ and a card id from "
		"before.",
	],
) -> dict:
	"""Suggest several records that belong together, in one step: a new
	customer and a quotation for them, a project with its first tasks, a
	supplier with their first order. Each becomes a card; approving one
	approves the cards it points at first, and the person can approve them
	all at once. Stops at the first record that cannot be suggested, keeping
	the cards made before it, and says what is wrong with that one."""
	made, cards = {}, []
	for at, one in enumerate(records or []):
		if not isinstance(one, dict) or not one.get("doctype"):
			frappe.throw(f"Record {at + 1} has no doctype. Each record is {{ref, doctype, values, why}}.")
		ref = str(one.get("ref") or at + 1)
		values = {
			key: (made.get(value[1:], value) if isinstance(value, str) and value.startswith("@") else value)
			for key, value in (one.get("values") or {}).items()
		}
		values = {
			key: (
				[
					{
						field: (made.get(cell[1:], cell) if isinstance(cell, str) and cell.startswith("@") else cell)
						for field, cell in row.items()
					}
					if isinstance(row, dict)
					else row
					for row in value
				]
				if isinstance(value, list)
				else value
			)
			for key, value in values.items()
		}
		try:
			card = proposals.propose("Create", one["doctype"], changes=values, why=one.get("why"))
		except Exception as refused:
			if not cards:
				raise
			frappe.clear_last_message()
			return {
				"cards": cards,
				"error": f"Record {ref} ({one['doctype']}) was not suggested: "
				+ frappe.utils.strip_html(str(refused)).strip()
				+ " The cards before it stand; suggest this one again with create_record, pointing at them.",
			}
		made[ref] = f"@{card}"
		cards.append({"ref": ref, "proposal": card, "use_as": f"@{card}"})
	return {
		"cards": cards,
		"state": "Proposed",
		"said": frappe._("Suggested. They happen when somebody approves them."),
	}


def edit_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	changes: Annotated[dict, "Field name to new value. Only the fields that change. " + POINTING],
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


def about_field(
	doctype: Annotated[str, "The type of record, such as HR Settings."],
	fieldname: Annotated[str, "The field's name, or its label as on screen."],
	name: Annotated[str, "The record's id, when it is not a settings page."] | None = None,
) -> dict:
	"""Everything about one field: what it is for, what it holds now, what it
	may hold, what it shows beside, and — for a field that points at other
	records — how many there are to choose from, so setting it up can start
	with the record it needs. Use it to explain a field or to help fill it."""
	doctype = _type(doctype)
	meta = frappe.get_meta(doctype)
	labels = [f for f in meta.fields if f.label and f.fieldtype not in LAYOUT]
	df = meta.get_field(fieldname) or meta.get_field(frappe.scrub(fieldname or ""))
	if not df:
		match = _meant(fieldname or "", [f.label for f in labels])
		df = next((f for f in labels if f.label == match), None)
	if not df:
		frappe.throw(f"{doctype} has no field {fieldname!r}. Its fields: {', '.join(kind.fields_of(meta))}.")
	record = doctype if meta.issingle else name
	held = frappe.get_doc(doctype, record) if record else None
	if held:
		held.check_permission("read")

	said = {
		"doctype": doctype,
		"fieldname": df.fieldname,
		"label": df.label,
		"type": df.fieldtype,
		"what_it_is_for": strip_html_tags(df.description or "") or None,
		"now": held.get(df.fieldname) if held else None,
		"default": df.default or None,
		"required": bool(df.reqd),
		"shown_when": df.depends_on or None,
	}
	if df.fieldtype == "Select":
		said["options"] = [one for one in (df.options or "").split("\n") if one]
	if df.fieldtype == "Link" and df.options:
		there = frappe.get_list(df.options, pluck="name", limit_page_length=11)
		said["points_at"] = {
			"doctype": df.options,
			"how_many": len(there) if len(there) <= 10 else "more than 10",
			"some": there[:10],
			"a_new_one_needs": [f for f in kind.fields_of(frappe.get_meta(df.options), most=40) if "required" in f],
		}
	return said


def search_everywhere(
	text: Annotated[str, "Words to look for: a name, a code, a phrase."],
	doctype: Annotated[str, "Only this type of record, if known."] | None = None,
) -> list:
	"""Search every kind of record at once, the way the desk's search bar does.
	Use it when you do not know what type something is — "Omar", "the Dubai
	office", "INV-0042" — then read what it finds."""
	from frappe.utils.global_search import search

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


MOST_FOUND = 10


def find_by_meaning(
	question: Annotated[str, "What to look for, in the person's own words: \"the quote for the glass on the Marina tower\"."],
	kinds: Annotated[
		list[str],
		"Only these: Reading for documents and scans, Communication for mail, or a type of record such as Customer.",
	]
	| None = None,
) -> list:
	"""Find documents, mail and records by what they mean rather than the exact
	words: the passages closest to the question, each with where it came from.
	Answer from the passages and name each one you used; use it when the
	person describes something rather than naming it."""
	from onedesk.one_ai import index

	out = []
	for hit in index.nearest(question, kinds or None, 8):
		out.append(
			{
				"kind": hit["source_doctype"],
				"id": hit["source_name"],
				"title": hit.get("title"),
				"passage": (hit.get("text") or "")[:1200],
				"closeness": hit["score"],
			}
		)
	return out


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
	for linked_type, rows in found.items():
		hidden = rows.get("hidden_count", 0) if isinstance(rows, dict) else 0
		rows = rows.get("docs", []) if isinstance(rows, dict) else rows
		names = [row.get("name") for row in rows or [] if isinstance(row, dict)][:MOST_LINKS]
		if names or hidden:
			said[linked_type] = {"names": names, "not_visible_to_the_reader": hidden} if hidden else names
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
	"""Run one of the workspace's own reports and answer with its rows, and the
	totals the report shows above them.

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
	said = {
		"report": report,
		"columns": [_column(one) for one in (out.get("columns") or [])],
		"rows": rows[:kept],
		"more": max(len(rows) - kept, 0),
	}
	summary = [
		{"label": one.get("label"), "value": one.get("value")}
		for one in out.get("report_summary") or []
		if isinstance(one, dict) and one.get("label")
	]
	if summary:
		said["summary"] = summary
	if out.get("message"):
		said["note"] = strip_html_tags(str(out["message"])).strip()[:500]
	return said


def _state_field(doctype: str) -> str | None:
	name = frappe.db.get_value("Workflow", {"document_type": doctype, "is_active": 1}, "workflow_state_field")
	return name or None


def _column(one) -> str:
	if isinstance(one, dict):
		return one.get("label") or one.get("fieldname") or ""
	return str(one)


def more_tools(
	groups: Annotated[list[str], "The groups to be given, by name, from the list in this tool's description."],
) -> dict:
	"""Be given more tools: what you have are those for the page the person is
	on and for what they asked. If what they ask needs something else One
	does, ask for its group here, and its tools are yours from the next step.
	Never say something cannot be done before asking for the group it would
	be in. The groups:"""
	from onedesk.one_ai import groups as grouped

	wanted = [str(one).strip().lower() for one in groups or []]
	known = [one for one in wanted if one in grouped.GROUPS and (one != "console" or grouped._console())]
	unknown = [one for one in wanted if one not in known]
	return {
		"given": known,
		"tools": [tool for one in known for tool in grouped.GROUPS[one]["tools"]],
		**({"unknown": unknown, "error": "There are no groups called " + ", ".join(unknown)} if unknown else {}),
	}


READS = (
	list_records,
	read_record,
	count_records,
	describe_type,
	find_records,
	find_by_meaning,
	search_everywhere,
	about_field,
	what_links_here,
	what_can_happen,
	run_report,
	memory.about_record,
	memory.recall,
	memory.search_my_chats,
	guide.how_to,
	more_tools,
)

SUGGESTS = (create_record, create_records, edit_record, delete_record, move_record)

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
	"""What runs now (reads, and keeping a memory, and the tools a run was
	handed for itself, such as OneIntake's) and what becomes a card."""
	reads, suggests = hooked()
	own = tuple((frappe.flags.get("one_ai_tools") or {}).values())
	return READS + KEEPS + reads + own, SUGGESTS + suggests


def declared_only(names: list[str]) -> list[dict]:
	"""These tools and no others, as a provider's function declarations."""
	reads, suggests = _every()
	known = {fn.__name__: fn for fn in reads + suggests}
	return [schema.of(known[name]) for name in names if name in known]


def _unshown(tool: str | None) -> tuple:
	fn = next((one for one in sum(_every(), ()) if one.__name__ == tool), None)
	return getattr(fn, "unshown", ()) if fn else ()


def shown_args(tool: str | None, args: dict | None) -> dict:
	"""A call's arguments as a person may see them and a chat keeps them: a
	tool's `unshown` ones, such as an extension's code, left out."""
	hidden = _unshown(tool)
	return {key: ("…" if key in hidden else value) for key, value in (args or {}).items()}


def shown_result(tool: str | None, result):
	"""What a tool answered, as a chat keeps it: the same `unshown` keys left
	out, so code a tool hands the model is read in the run and kept nowhere."""
	hidden = _unshown(tool)
	if not hidden or not isinstance(result, dict):
		return result
	return {key: ("…" if key in hidden else value) for key, value in result.items()}


def declared(given: list[str] | None = None) -> list[dict]:
	"""The tools a request is given, as a provider's function declarations:
	every one, or the core and the groups `given` (one_ai/groups.py), in a
	fixed order so a provider's cache keeps what it has, with `more_tools`
	saying what else there is."""
	from onedesk.one_ai import groups

	reads, suggests = _every()
	every = reads + suggests
	if given is None:
		return [schema.of(fn) for fn in every if fn is not more_tools]
	order = {name: at for at, name in enumerate(given)}
	kept = [fn for fn in every if fn.__name__ in groups.CORE or groups.of(fn.__name__) in order]
	kept.sort(key=lambda fn: -1 if fn.__name__ in groups.CORE else order[groups.of(fn.__name__)])
	out = [schema.of(fn) for fn in kept]
	for one in out:
		if one["name"] == "more_tools":
			one["description"] += "\n" + groups.catalogue(given)
	return out


def action_of(name: str | None) -> str | None:
	"""The action a tool asks to be run under, when it is not whichever is
	running: a tool a small model gets wrong names a stronger one (Print
	Design), and the loop hands the conversation to it."""
	reads, suggests = _every()
	fn = {one.__name__: one for one in reads + suggests}.get(name or "")
	return getattr(fn, "action", None)


def named(name: str | None):
	"""The tool called `name`, if there is one."""
	reads, suggests = _every()
	return {one.__name__: one for one in reads + suggests}.get(name or "")


def names() -> list[str]:
	reads, suggests = _every()
	return [one.__name__ for one in reads + suggests]


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
		"use_as": f"@{proposal}",
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
