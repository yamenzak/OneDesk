"""What an agent looked up and suggested, drawn for the person reading its
answer: the records a tool read as cards or one list under the answer, and
each AI Proposal as the record it would make or change. The panel and
OneChat read it (one_chat/answers.py, panel.py); nothing here asks a model
or writes a record."""

import json
import re

import frappe
from frappe.utils import strip_html_tags

from onedesk.one_ai import kind


CARDS = 3

FIELDS = 6

BRIEF = 2

NOT_ON_A_CARD = (
	"Text Editor",
	"HTML",
	"HTML Editor",
	"Markdown Editor",
	"Code",
	"Section Break",
	"Column Break",
	"Tab Break",
	"Table",
	"Table MultiSelect",
	"Password",
)

QUIET = ("context",)

QUIET_TOOLS = ("remember",)


def suggested(names: list[str] | str) -> list[dict]:
	"""The suggestions a conversation named, as they stand now.

	Read rather than stored with the turn, because a card is answered after the
	conversation moved on and a copy kept in the transcript would go on saying
	Proposed for ever. `get_list`, so a card that is not the reader's own is not
	in the answer at all.
	"""
	named = frappe.parse_json(names) if isinstance(names, str) else (names or [])
	if not named:
		return []
	found = frappe.get_list(
		"AI Proposal",
		filters={"name": ["in", list(named)[:50]]},
		fields=["name", "kind", "for_doctype", "record", "state", "why", "said", "changes", "was", "applied_doc"],
		limit_page_length=50,
	)
	return [{**row, "shown": _suggests(row)} for row in found]


def _suggests(row: dict) -> dict:
	"""A suggestion drawn as the record it is about.

	The same card a lookup draws, so approving a change and reading a record
	look like one thing rather than two — the fields are what is being proposed,
	which for a change is only what changes.
	"""
	from onedesk.one_ai import proposals

	doctype = row.get("for_doctype") or ""
	fields = []
	try:
		changes = frappe.parse_json(row.get("changes") or "{}") or {}
	except Exception:
		changes = {}

	if row.get("kind") in ("Customize", "Holidays", "Numbering", "Printing", "Approval", "Setup"):
		head = changes.get("letter_head") or {}
		return {
			"doctype": doctype,
			"name": (row.get("record") or "") if row.get("kind") == "Holidays" else "",
			"title": changes.get("title") or "" if row.get("kind") == "Setup" else "",
			"route": changes.get("route") if row.get("kind") == "Setup" else None,
			"what": changes.get("what") if row.get("kind") == "Setup" else None,
			"page": row.get("kind") == "Printing"
			and bool(changes.get("format") or head.get("content") or head.get("footer") or head.get("image")),
			"format": (changes.get("format") or {}).get("name") or "",
			"fields": [
				{"label": str(one.get("label") or ""), "value": str(one.get("value") or "")}
				for one in (changes.get("summary") or [])[: proposals.MOST_FIELDS]
				if isinstance(one, dict)
			],
		}

	if row.get("kind") == "Reply":
		return {
			"doctype": doctype,
			"name": changes.get("subject") or "",
			"title": "",
			"fields": [{"label": frappe._("Reply"), "value": str(changes.get("text") or "")}],
		}

	if row.get("kind") == "Mail":
		return {
			"doctype": doctype,
			"name": row.get("record") or "",
			"title": "",
			"fields": [
				{"label": frappe._("To"), "value": str(changes.get("recipients") or "")},
				{"label": frappe._("Subject"), "value": str(changes.get("subject") or "")},
				{"label": frappe._("Mail"), "value": str(changes.get("text") or "")},
			],
		}

	if row.get("kind") == "Update":
		return {
			"doctype": doctype,
			"name": frappe.db.get_value("Project", row.get("record"), "project_name") or row.get("record") or "",
			"title": "",
			"fields": [{"label": frappe._("Update"), "value": str(changes.get("text") or "")}],
		}

	if row.get("kind") == "Signature":
		from frappe.utils import strip_html

		text = re.sub(r"<\s*/?(br|p|div|li)\b[^>]*>", "\n", str(changes.get("signature") or ""), flags=re.I)
		return {
			"doctype": doctype,
			"name": row.get("record") or "",
			"title": "",
			"fields": [{"label": frappe._("Signature"), "value": strip_html(text).strip()}],
		}

	meta = frappe.get_meta(doctype) if doctype and frappe.db.exists("DocType", doctype) else None
	labels = {field.fieldname: field.label or field.fieldname for field in (meta.fields if meta else [])}
	labels = {"__newname": "Name", **labels}
	known = {field.fieldname: field for field in (meta.fields if meta else [])}
	place = {name: at for at, name in enumerate(labels)}
	ordered = sorted(changes.items(), key=lambda one: place.get(one[0], len(place)))
	tables = {
		f.fieldname: f.options
		for f in (meta.fields if meta else [])
		if f.fieldtype in frappe.model.table_fields
	}
	try:
		was = frappe.parse_json(row.get("was") or "{}") or {}
	except Exception:
		was = {}
	for field, value in ordered[: proposals.MOST_FIELDS]:
		if field in tables and isinstance(value, list):
			fields.append(
				{
					"label": frappe._(labels.get(field, field)),
					"rows": _card_rows(tables[field], value, changes),
				}
			)
			continue
		drawn = {
			"fieldname": field,
			"label": frappe._(labels.get(field, field)),
			"value": _formatted(known[field], value, changes) if field in known else as_text(value),
		}
		if row.get("kind") == "Edit" and field in was:
			held = was.get(field)
			drawn["was"] = (
				_formatted(known[field], held, was) if field in known and held not in (None, "") else ""
			)
		fields.append(drawn)

	return {
		"doctype": doctype,
		"name": row.get("record") or "",
		"title": "",
		"fields": fields,
	}


def shown(turns: list[dict]) -> list[dict]:
	"""The conversation as a person reads it.

	Tool results are folded into the model's turn that asked for them, because
	"it looked something up" is one event on screen and three in the transcript.
	"""
	answers: dict[int, list[dict]] = {}
	for at, one in enumerate(turns):
		if one.get("role") == "model" and one.get("calls"):
			after = []
			for later in turns[at + 1 :]:
				if later.get("role") != "tool":
					break
				after.append(later)
			answers[at] = after

	said = []
	seen: set = set()
	for at, one in enumerate(turns):
		role = one.get("role")
		if role == "tool" or any(one.get(quiet) for quiet in QUIET):
			continue
		if role != "model":
			seen = set()
		looked = [
			look_of(call, _answering(call, answers.get(at) or [], n))
			for n, call in enumerate(one.get("calls") or [])
			if call.get("tool") not in QUIET_TOOLS
		]
		for look in looked:
			fresh = [
				rec for rec in look.get("records") or [] if (rec.get("doctype"), rec.get("name")) not in seen
			]
			seen |= {(rec.get("doctype"), rec.get("name")) for rec in fresh}
			look["records"] = fresh
		said.append(
			{
				"role": "model" if role == "model" else "you",
				"text": "" if one.get("wrote") else (one.get("text") or ""),
				"files": [
					{key: value for key, value in file.items() if key != "data"}
					for file in one.get("files") or []
				],
				"looked": looked,
				"remembered": _remembered(one, answers.get(at) or []),
				"cards": [card for look in looked for card in look["cards"]] + list(one.get("cards") or []),
			}
		)
	return _answer_first(said)


def _answer_first(said: list[dict]) -> list[dict]:
	"""What a turn looked up, moved under the answer it led to.

	A model asks for a tool in one turn and answers in the next, so drawn as
	stored the records came first and the answer below them, off the bottom
	of a phone. The answer is what was asked for; what it read is the
	evidence, underneath."""
	out: list[dict] = []
	carried: dict | None = None
	for one in said:
		if one["role"] != "model":
			if carried:
				out.append(carried)
			carried = None
			out.append(one)
			continue
		if carried:
			one = {
				**one,
				"looked": carried["looked"] + one["looked"],
				"remembered": carried["remembered"] + one["remembered"],
				"cards": carried["cards"] + one["cards"],
				"files": carried["files"] + one["files"],
			}
			carried = None
		if not one["text"] and (one["looked"] or one["remembered"] or one["cards"]):
			carried = one
			continue
		out.append(one)
	if carried:
		out.append(carried)
	return out


def _remembered(turn: dict, after: list[dict]) -> list[dict]:
	"""The memories a model turn kept or changed, from its remember calls."""
	kept = []
	for n, call in enumerate(turn.get("calls") or []):
		if call.get("tool") != "remember":
			continue
		answered = (_answering(call, after, n) or {}).get("result")
		if isinstance(answered, dict) and answered.get("state") in ("remembered", "updated"):
			if frappe.db.exists("AI Memory", answered.get("memory")):
				kept.append({"memory": answered["memory"], "fact": answered.get("fact")})
	return kept


def _answering(call: dict, after: list[dict], n: int) -> dict | None:
	"""The tool turn that answered the nth call of a model turn: the nth one
	after it, when it is that tool's; otherwise the first of that tool's."""
	if n < len(after) and after[n].get("tool") == call.get("tool"):
		return after[n]
	return next((one for one in after if one.get("tool") == call.get("tool")), None)


def look_of(call: dict, result: dict | None) -> dict:
	"""One thing it did, from the call and the turn that answered it.

	`ran` and `card` are read off the turn rather than out of the answer: the
	answer is the tool's own and is what the provider is sent, and the
	bookkeeping is beside it.
	"""
	said = result or {}
	answered = said.get("result")
	rows, more = _records(call, answered)
	found = _found(call, answered)
	if found:
		rows, more = [], 0
	return {
		"tool": call.get("tool"),
		"args": call.get("args") or {},
		"ran": bool(said.get("ran")),
		"error": _first(answered.get("error")) if isinstance(answered, dict) else None,
		"card": said.get("card"),
		"cards": list(said.get("cards") or ([said["card"]] if said.get("card") else [])),
		"records": rows,
		"more": more,
		"found": found,
		"count": answered if isinstance(answered, int) else None,
	}


def _first(error) -> str | None:
	"""A tool's refusal as the reader sees it: its first sentence. The rest —
	the fields a type has, the values there are — is written for the model."""
	if not error:
		return None
	said = re.sub(r"^\w+(Error|Exception): ", "", str(error).split("\nWhat to do:", 1)[0])
	said = said.split(". ", 1)[0].strip()
	return said if said.endswith(".") else said + "."


def _records(call: dict, answered) -> tuple[list[dict], int]:
	"""What it read, drawn as records rather than described in a sentence.

	A record somebody is looking at is worth seeing: the type, what it is
	called, and a few fields. The drawing is done here rather than in the panel
	because labelling a field needs the doctype's meta, and the panel having to
	fetch meta for every type a conversation touches is a round trip per
	answer.
	"""
	doctype = ((call.get("args") or {}).get("doctype") or "").strip()
	if not doctype or not frappe.db.exists("DocType", doctype):
		return [], 0

	if isinstance(answered, dict) and answered.get("name"):
		found = [answered]
	elif isinstance(answered, list):
		found = [row for row in answered if isinstance(row, dict)]
	else:
		return [], 0

	most = FIELDS if len(found) == 1 else BRIEF
	return [card_of(doctype, row, most) for row in found[:CARDS]], max(len(found) - CARDS, 0)


LISTED = 10


def _found(call: dict, answered) -> dict | None:
	"""Several records read at once, as one list: a line each with what it is
	called and the one value that tells it apart, rather than a card each.

	Measured on a phone: four customers drawn as four cards filled the panel
	twice over and pushed the answer below them. A list reads at a glance and
	leaves the answer in sight; one record still gets its card."""
	doctype = ((call.get("args") or {}).get("doctype") or "").strip()
	if not isinstance(answered, list) or not doctype or not frappe.db.exists("DocType", doctype):
		return None
	found = [row for row in answered if isinstance(row, dict) and row.get("name")]
	if len(found) < 2:
		return None
	rows = []
	for row in found[:LISTED]:
		drawn = card_of(doctype, row, 1)
		told = (drawn["fields"] or [{}])[0]
		rows.append(
			{"name": drawn["name"], "title": drawn["title"], "meta": told.get("value"), "meta_label": told.get("label")}
		)
	filters = (call.get("args") or {}).get("filters")
	return {
		"doctype": doctype,
		"total": len(found),
		"rows": rows,
		"filters": filters if isinstance(filters, dict) else None,
	}


def card_of(doctype: str, row: dict, most: int = FIELDS) -> dict:
	"""One record as a card: what it is, what it is called, and a few fields."""
	meta = frappe.get_meta(doctype)
	titled = meta.title_field and row.get(meta.title_field)
	skip = {"name", "doctype", "idx", "owner", meta.title_field}

	fields = []
	for field in meta.fields:
		if field.fieldname in skip or field.fieldname not in row:
			continue
		if field.hidden or field.fieldname == "naming_series":
			continue
		value = row.get(field.fieldname)
		if value in (None, "", 0) or field.fieldtype in NOT_ON_A_CARD:
			continue
		fields.append(
			{"label": frappe._(field.label or field.fieldname), "value": _formatted(field, value, row)}
		)
		if len(fields) >= most:
			break

	return {
		"doctype": doctype,
		"name": row.get("name"),
		"title": str(titled or row.get("name") or ""),
		"fields": fields,
	}


AS_TEXT = {"Data", "Small Text", "Text", "Long Text", "Text Editor", "HTML Editor", "Markdown Editor", "Code"}


def _formatted(df, value, doc: dict | None = None) -> str:
	"""A value as the form would show it: frappe's own formatter, so a date is
	in the site's date format and money carries its currency. A link is its
	record's title, and text stays text."""
	if value in (None, ""):
		return ""
	if isinstance(value, str) and kind.REF.match(value):
		return _pointed(value)
	if df.fieldtype == "Link" and df.options:
		return _titled(df.options, value)
	if df.fieldtype == "Check":
		if df.parent and frappe.get_meta(df.parent).issingle:
			return frappe._("On") if frappe.utils.cint(value) else frappe._("Off")
		return frappe._("Yes") if frappe.utils.cint(value) else frappe._("No")
	if df.fieldtype in ("Attach", "Attach Image"):
		return str(value).rsplit("/", 1)[-1]
	if df.fieldtype in AS_TEXT or isinstance(value, (list, dict)):
		return as_text(value)
	from frappe.utils.formatters import format_value

	return strip_html_tags(str(format_value(value, df, doc=frappe._dict(doc or {})))).strip()


def _pointed(value: str) -> str:
	"""A value that points at another card: what that card makes, or, once it
	is approved, the record it made."""
	card = kind.REF.match(value).group(1)
	held = frappe.db.get_value("AI Proposal", card, ["said", "state", "applied_doc", "for_doctype"], as_dict=True)
	if not held:
		return value
	if held.state == "Applied" and held.applied_doc:
		return _titled(held.for_doctype, held.applied_doc)
	return frappe._("{0}, from the card above").format(held.said)


def _titled(doctype: str, name) -> str:
	"""A linked record by its title, where the reader may see it and it has one."""
	try:
		meta = frappe.get_meta(doctype)
		if meta.title_field and frappe.has_permission(doctype, "read", doc=str(name)):
			return str(frappe.db.get_value(doctype, name, meta.title_field) or name)
	except Exception:
		pass
	return str(name)


def _card_rows(doctype: str, rows: list, parent: dict | None = None) -> list[dict]:
	"""A child table's rows as a card draws them: what the row is, its amount
	on the right, and the kind and date underneath — rather than every value in
	a line joined by dots."""
	meta = frappe.get_meta(doctype)
	drawn = []
	for row in rows:
		if not isinstance(row, dict):
			continue
		main, side, notes = [], "", []
		for field, value in row.items():
			if value in (None, ""):
				continue
			df = meta.get_field(field)
			fieldtype = df.fieldtype if df else None
			shown = _formatted(df, value, {**row, **(parent or {})}) if df else str(value)
			if fieldtype in ("Currency", "Float", "Int", "Percent") and not side:
				side = shown
			elif fieldtype in ("Link", "Select", "Date", "Datetime"):
				notes.append(shown)
			else:
				main.append(shown)
		drawn.append(
			{"main": " ".join(main) or (notes.pop(0) if notes else ""), "side": side, "notes": notes}
		)
	return drawn


def as_text(value) -> str:
	"""A proposed value as a person reads it on a card.

	Text as text, and a child table as its rows, one a line — every row a
	suggestion carries is on the card, because the rows are what is approved.
	"""
	if isinstance(value, str) and kind.REF.match(value):
		return _pointed(value)
	if isinstance(value, str):
		return strip_html_tags(value).strip()
	if isinstance(value, list):
		return "\n".join(
			" · ".join(as_text(one) if isinstance(one, str) else str(one) for one in row.values() if one not in (None, ""))
			for row in value
			if isinstance(row, dict)
		)
	return json.dumps(value)
