"""One conversation with OneAI, and the page it was had on.

Kept rather than held in a tab, because a chat that dies when the tab does is
one nobody starts anything long in. The store is `AI Chat`: a title, when it was
last said to, what it has cost, and the turns — the same turns the gateway
speaks, because the conversation *is* the turns and a second shape beside them
is a second shape to keep in step.

**The page is a pointer, not a payload.** What travels is the route: the
doctype, the record's id, which view. Not the record's values — the model has
`read_record` for that, and that runs as whoever is signed in, so a pointer at
something the reader may not see buys nothing. It also keeps a conversation
honest over time: the context of the third message is where they were for the
third message, not where they are now.
"""

import json
import re

import frappe
from frappe.utils import now_datetime

from onedesk.one_ai import run

#: The action the panel runs. Named here rather than typed at each call so the
#: fixture is the one place its instruction lives.
CHAT = "chat"

#: How much of a conversation goes back to the model. Older turns are dropped
#: from what is *sent*, never from what is stored: the panel still shows the
#: whole thing, and a run is billed per round on what it was given.
KEPT = 24

#: How long a title taken from the first thing asked may be.
TITLE = 60

#: How many records one lookup draws before it says how many more there were.
#: Three is a glance; ten is a list somebody has to scroll past the answer.
CARDS = 3

#: Fields on one card. Enough to recognise the record, not enough to replace it.
FIELDS = 6

#: Fields on each of several. A list is for picking one out, not for reading.
BRIEF = 2

#: Fieldtypes that are not a line on a card — markup, layout, and the long ones
#: that would push the answer off the screen.
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

#: Turns nobody reads on screen. The page pointer is one of these — it is said
#: to the model, and showing it would be showing somebody their own address bar.
QUIET = ("context",)


@frappe.whitelist()
def chats(limit: int = 20) -> list[dict]:
	"""This reader's conversations, most recently said to first."""
	return frappe.get_list(
		"AI Chat",
		fields=["name", "title", "last_said_on", "spent"],
		order_by="last_said_on desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def opened(chat: str | None = None) -> dict:
	"""One conversation, or an empty one that has not been stored yet."""
	if not chat:
		return {"name": None, "title": None, "said": [], "spent": 0.0, **_model()}
	doc = frappe.get_doc("AI Chat", chat)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"title": doc.title,
		"said": shown(_turns(doc)),
		"spent": doc.spent or 0.0,
		**_model(doc),
	}


@frappe.whitelist()
def start() -> dict:
	"""An empty conversation, so a file has something to be attached to.

	A file belongs to the chat it was dropped on, and frappe attaches to a row
	that exists — so the row is made when the paperclip is pressed rather than
	when the question is sent.
	"""
	doc = frappe.get_doc({"doctype": "AI Chat", "title": frappe._("New conversation")}).insert()
	return {"name": doc.name, "title": doc.title, "said": [], "spent": 0.0, **_model(doc)}


@frappe.whitelist()
def say(
	text: str,
	chat: str | None = None,
	page: dict | str | None = None,
	files: list | str | None = None,
) -> dict:
	"""Say one thing, run the loop, and keep what came back.

	The whole conversation is stored before the answer is asked for, so a run
	that fails leaves the question in the chat rather than losing it.
	"""
	text = (text or "").strip()
	attached = frappe.parse_json(files) if isinstance(files, str) else (files or [])
	if not text and not attached:
		frappe.throw(frappe._("Nothing was asked."))

	doc = _chat(chat, text or (attached and attached[0]) or "")
	turns = _turns(doc)
	# A chat started by the paperclip was saved before anything was asked, under
	# a placeholder; its first question is still what names it.
	if not turns and text:
		doc.title = text[:TITLE]
	turns.extend(_asked(text, page, attached))
	_keep(doc, turns, spent=0.0)

	out = _ran(doc, text, turns)
	turns = turns[: -min(KEPT, len(turns))] + list(out.get("turns") or [])
	doc.model = out.get("model") or doc.model
	_keep(doc, turns, spent=float(out.get("credits") or 0))

	return {
		"name": doc.name,
		"title": doc.title,
		"said": shown(turns),
		"spent": doc.spent or 0.0,
		"credits": out.get("credits"),
		"rounds": out.get("rounds"),
		"proposals": out.get("proposals") or [],
		**_model(doc),
	}


@frappe.whitelist()
def cards(names: list[str] | str) -> list[dict]:
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
		fields=["name", "kind", "for_doctype", "record", "state", "why", "changes", "applied_doc"],
		limit_page_length=50,
	)
	return [{**row, "shown": _suggests(row)} for row in found]


def _suggests(row: dict) -> dict:
	"""A suggestion drawn as the record it is about.

	The same card a lookup draws, so approving a change and reading a record
	look like one thing rather than two — the fields are what is being proposed,
	which for a change is only what changes.
	"""
	doctype = row.get("for_doctype") or ""
	fields = []
	try:
		changes = frappe.parse_json(row.get("changes") or "{}") or {}
	except Exception:
		changes = {}

	meta = frappe.get_meta(doctype) if doctype and frappe.db.exists("DocType", doctype) else None
	labels = {field.fieldname: field.label or field.fieldname for field in (meta.fields if meta else [])}
	for field, value in list(changes.items())[:FIELDS]:
		fields.append(
			{
				"label": frappe._(labels.get(field, field)),
				"value": value if isinstance(value, str) else json.dumps(value),
			}
		)

	return {
		"doctype": doctype,
		"name": row.get("record") or "",
		"title": "",
		"fields": fields,
	}


def _ran(doc, text: str, turns: list[dict]) -> dict:
	"""The run, with the failure said in words somebody can act on.

	A fault out of the account carries an endpoint and a status, which is the
	right thing in a log and the wrong thing in a panel. `Again` is transient
	and the answer is to press the button again; `Refused` already reads as a
	sentence and is passed through; anything else is a bug and keeps its own
	traceback.
	"""
	from onedesk.one_admin import faults

	try:
		from onedesk.one_ai import files as carrying

		return run.ask(
			CHAT, text, reference=doc.name, turns=carrying.carried(turns[-KEPT:])
		)
	except faults.Again:
		frappe.throw(
			frappe._("OneAI could not be reached just now. The question is still here — try again."),
			title=frappe._("Not answered"),
		)
	except faults.Refused as raised:
		frappe.throw(frappe.utils.strip_html(str(raised)), title=frappe._("Not answered"))


@frappe.whitelist()
def rename(chat: str, title: str) -> dict:
	doc = frappe.get_doc("AI Chat", chat)
	doc.check_permission("write")
	doc.title = (title or "").strip()[:TITLE] or doc.title
	doc.save()
	return {"name": doc.name, "title": doc.title}


@frappe.whitelist()
def forget(chat: str) -> dict:
	"""Delete one conversation. The cards it suggested are not deleted with it."""
	doc = frappe.get_doc("AI Chat", chat)
	doc.check_permission("delete")
	doc.delete()
	return {"forgotten": chat}


def shown(turns: list[dict]) -> list[dict]:
	"""The conversation as a person reads it.

	Tool results are folded into the model's turn that asked for them, because
	"it looked something up" is one event on screen and three in the transcript.
	"""
	ran: dict[str, dict] = {}
	for one in turns:
		if one.get("role") == "tool":
			ran[str(one.get("id") or one.get("tool"))] = one

	said = []
	for one in turns:
		role = one.get("role")
		if role == "tool" or any(one.get(quiet) for quiet in QUIET):
			continue
		looked = [
			_looked(call, ran.get(str(call.get("id") or call.get("tool"))))
			for call in one.get("calls") or []
		]
		said.append(
			{
				"role": "model" if role == "model" else "you",
				"text": one.get("text") or "",
				"files": [
					{key: value for key, value in file.items() if key != "data"}
					for file in one.get("files") or []
				],
				"looked": looked,
				"cards": [card for card in (look["card"] for look in looked) if card],
			}
		)
	return said


def _looked(call: dict, result: dict | None) -> dict:
	"""One thing it did, from the call and the turn that answered it.

	`ran` and `card` are read off the turn rather than out of the answer: the
	answer is the tool's own and is what the provider is sent, and the
	bookkeeping is beside it.
	"""
	said = result or {}
	answered = said.get("result")
	rows, more = _records(call, answered)
	return {
		"tool": call.get("tool"),
		"args": call.get("args") or {},
		"ran": bool(said.get("ran")),
		"error": answered.get("error") if isinstance(answered, dict) else None,
		"card": said.get("card"),
		"records": rows,
		"more": more,
		"count": answered if isinstance(answered, int) else None,
	}


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

	# One record gets the full card; several get two fields each, because a list
	# drawn at full height is a list the answer sits below the bottom of.
	most = FIELDS if len(found) == 1 else BRIEF
	return [_drawn(doctype, row, most) for row in found[:CARDS]], max(len(found) - CARDS, 0)


def _drawn(doctype: str, row: dict, most: int = FIELDS) -> dict:
	"""One record as a card: what it is, what it is called, and a few fields."""
	meta = frappe.get_meta(doctype)
	titled = meta.title_field and row.get(meta.title_field)
	skip = {"name", "doctype", "idx", "owner", meta.title_field}

	fields = []
	for field in meta.fields:
		if field.fieldname in skip or field.fieldname not in row:
			continue
		value = row.get(field.fieldname)
		if value in (None, "", 0) or field.fieldtype in NOT_ON_A_CARD:
			continue
		fields.append({"label": frappe._(field.label or field.fieldname), "value": str(value)})
		if len(fields) >= most:
			break

	return {
		"doctype": doctype,
		"name": row.get("name"),
		"title": str(titled or row.get("name") or ""),
		"fields": fields,
	}


def _asked(text: str, page: dict | str | None, attached: list | None = None) -> list[dict]:
	"""The reader's turn, the page they were on, and what they dropped on it."""
	from onedesk.one_ai import files as carrying

	where = _page(page)
	turns = []
	if where:
		turns.append({"role": "user", "text": where, "calls": [], "context": True})
	turns.append(
		{
			"role": "user",
			"text": text,
			"calls": [],
			# Named and sized, never the bytes: a conversation row holding a
			# base64 of every attachment it ever carried is a row that grows
			# until it cannot be read.
			"files": carrying.described(attached or []),
		}
	)
	return turns


def _page(page: dict | str | None) -> str:
	"""Where the reader is, in one sentence, from what the browser said it is.

	Nothing here is trusted: it names a record, and every tool that could then
	read that record checks the reader's own permission before it answers.
	"""
	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	if not isinstance(page, dict):
		return ""

	doctype = (page.get("doctype") or "").strip()
	record = (page.get("name") or "").strip()
	view = (page.get("view") or "").strip()
	if doctype and record:
		return f"The reader is looking at the {doctype} record {record}."
	if doctype:
		filters = page.get("filters")
		narrowed = f", narrowed to {json.dumps(filters)}" if filters else ""
		return f"The reader is looking at a {view or 'list'} of {doctype}{narrowed}."
	return f"The reader is on the {view} page." if view else ""


def _chat(chat: str | None, text: str):
	if chat:
		doc = frappe.get_doc("AI Chat", chat)
		doc.check_permission("write")
		return doc
	return frappe.get_doc({"doctype": "AI Chat", "title": text[:TITLE]}).insert()


def _model(doc=None) -> dict:
	"""Which model answers here, and where somebody allowed to could change it.

	The one the last answer came from, if there was one; then what the workspace
	picked for the chat action; then nothing, and the panel says the default is
	answering. It is shown and not chosen, because the model is the workspace's
	choice per action — so for whoever administers the workspace it opens that
	setting, and for everybody else it is a label.
	"""
	said = (doc and doc.get("model")) or run.mine(CHAT).get("model") or ""
	from onedesk.one import roles

	settable = roles.administers() and frappe.db.exists("AI Action Setting", CHAT)
	return {"model": named(said), "model_at": CHAT if settable else None}


def named(model: str) -> str:
	"""A catalogue id as a person reads it.

	The account files a model under its provider, a colon, and for Workers AI a
	path; the last piece is the model's own name, and the only part that fits a
	pill.
	"""
	return re.split(r"[:/]", model or "")[-1]


def _turns(doc) -> list[dict]:
	try:
		return json.loads(doc.turns or "[]")
	except ValueError:
		# A conversation that will not parse is not one to throw somebody's next
		# question away over; it starts again and the row keeps what it had.
		return []


def _keep(doc, turns: list[dict], spent: float) -> None:
	doc.turns = json.dumps(turns)
	doc.last_said_on = now_datetime()
	doc.spent = round((doc.spent or 0) + spent, 6)
	doc.save()
	frappe.db.commit()
