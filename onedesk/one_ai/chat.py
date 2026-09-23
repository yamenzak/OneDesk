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
from frappe.utils import now_datetime, strip_html_tags

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

#: A run is five rounds at most, each a model call of up to a minute and the
#: tools between them. Past this the job is stopped and the chat is free again.
RUN_TIMEOUT = 600

#: How long a finished run's steps are kept for a browser that missed them.
RUN_KEPT = 900

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
		# A run still going, so a panel closed and opened again picks it back up.
		"running": frappe.cache.get_value(f"one_ai_busy:{doc.name}"),
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
	field: dict | str | None = None,
) -> dict:
	"""Say one thing, and start the run that answers it.

	The whole conversation is stored before the answer is asked for, so a run
	that fails leaves the question in the chat rather than losing it. The run
	itself is a background job: a generation takes between two and forty
	seconds, and a web worker held for that is a worker answering nobody else.
	The browser is handed a run id and told each step as it happens.
	"""
	from onedesk.one_ai import touch

	text = (text or "").strip()
	writing = touch.target(field)
	attached = frappe.parse_json(files) if isinstance(files, str) else (files or [])
	if not text and not attached:
		frappe.throw(frappe._("Nothing was asked."))

	doc = _chat(chat, text or (attached and attached[0]) or "")
	if _running(doc.name):
		frappe.throw(frappe._("Still answering the last question."), title=frappe._("Not yet"))
	turns = _turns(doc)
	# A chat started by the paperclip was saved before anything was asked, under
	# a placeholder; its first question is still what names it.
	if not turns and text:
		doc.title = text[:TITLE]
	# "Improve it" names nothing in a list of conversations; the field does.
	if not turns and writing:
		label = writing["label"]
		doc.title = f"{frappe._(label)} — {text}"[:TITLE]
	turns.extend(_asked(text, page, attached, writing))
	_keep(doc, turns, spent=0.0)

	run_id = frappe.generate_hash(length=12)
	_tell(run_id, doc.name, {"started": True})
	frappe.enqueue(
		"onedesk.one_ai.chat.answer",
		queue="default",
		timeout=RUN_TIMEOUT,
		enqueue_after_commit=True,
		chat=doc.name,
		text=text,
		field=writing,
		run_id=run_id,
	)

	return {
		"name": doc.name,
		"title": doc.title,
		"said": shown(turns),
		"spent": doc.spent or 0.0,
		"run": run_id,
		**_model(doc),
	}


def answer(chat: str, text: str, field: dict | None, run_id: str) -> None:
	"""The run, in the background, as the person who asked.

	frappe starts a job as whoever enqueued it, so every tool the model calls
	still runs with that person's permissions — nothing about the rule changes
	by moving it off the request. Each step is told to their browser; the
	answer is kept on the conversation, which is where the panel reads it from
	whether or not it heard the last message.
	"""
	doc = frappe.get_doc("AI Chat", chat)
	turns = _turns(doc)
	heard = lambda step: _tell(run_id, chat, step)  # noqa: E731
	try:
		out = _ran(doc, text, turns, heard)
		turns = turns[: -min(KEPT, len(turns))] + list(out.get("turns") or [])
		if field:
			_field_card(field, turns, doc.name)
		doc.model = out.get("model") or doc.model
		_keep(doc, turns, spent=float(out.get("credits") or 0))
		_tell(run_id, chat, {"done": True, "credits": out.get("credits"), "rounds": out.get("rounds")})
	except frappe.ValidationError as raised:
		# `_ran` has already put a fault into words somebody can act on.
		frappe.db.rollback()
		_tell(run_id, chat, {"failed": frappe.utils.strip_html(str(raised))})
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="OneAI run failed", reference_doctype="AI Chat", reference_name=chat)
		_tell(run_id, chat, {"failed": frappe._("That did not go through.")})


@frappe.whitelist()
def progress(run: str) -> dict:
	"""Where a run has got to, for a browser that missed the messages.

	Realtime is the fast path, not the only one: a socket that dropped, or a
	tab that slept, asks here instead. Only the person whose run it is.
	"""
	state = frappe.cache.get_value(_key(run)) or {}
	if state.get("user") != frappe.session.user:
		return {}
	return state


def _key(run: str) -> str:
	return f"one_ai_run:{run}"


def _running(chat: str) -> bool:
	return bool(frappe.cache.get_value(f"one_ai_busy:{chat}"))


def _tell(run: str, chat: str, step: dict) -> None:
	"""One step of a run: kept for a browser that asks, and sent to the one listening."""
	state = frappe.cache.get_value(_key(run)) or {"user": frappe.session.user, "chat": chat, "steps": []}
	if step.get("tool"):
		state["steps"].append(_looked({"tool": step["tool"], "args": step.get("args")}, {"ran": step.get("ran")}))
	for end in ("done", "failed"):
		if end in step:
			state[end] = step[end]
	frappe.cache.set_value(_key(run), state, expires_in_sec=RUN_KEPT)

	busy = f"one_ai_busy:{chat}"
	if step.get("done") or step.get("failed"):
		frappe.cache.delete_value(busy)
	else:
		frappe.cache.set_value(busy, run, expires_in_sec=RUN_TIMEOUT)

	frappe.publish_realtime(
		"one_ai_run", {"run": run, "chat": chat, **step}, user=state["user"], after_commit=False
	)


@frappe.whitelist()
def suggestions(page: dict | str | None = None) -> list[dict]:
	"""What the panel offers on this page. See one_ai/suggest.py."""
	from onedesk.one_ai import suggest

	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	return suggest.for_page(page if isinstance(page, dict) else None)


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
	links = {f.fieldname: f.options for f in (meta.fields if meta else []) if f.fieldtype == "Link"}
	# In the form's own order: stored JSON comes back alphabetical, which put
	# "Asked For On" on the card and pushed "To Date" off it.
	place = {name: at for at, name in enumerate(labels)}
	ordered = sorted(changes.items(), key=lambda one: place.get(one[0], len(place)))
	tables = {f.fieldname: f.options for f in (meta.fields if meta else []) if f.fieldtype in frappe.model.table_fields}
	for field, value in ordered[:FIELDS]:
		if field in tables and isinstance(value, list):
			fields.append({"label": frappe._(labels.get(field, field)), "rows": _card_rows(tables[field], value)})
			continue
		fields.append(
			{
				"label": frappe._(labels.get(field, field)),
				# A Text Editor's value is markup; the card is text. A link is
				# the record's title — "Rania Sabbagh", not HR-EMP-00001.
				"value": _titled(links[field], value) if field in links and value else _card_value(value),
			}
		)

	return {
		"doctype": doctype,
		"name": row.get("record") or "",
		"title": "",
		"fields": fields,
	}


def _ran(doc, text: str, turns: list[dict], heard=None) -> dict:
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

		# What the person just dropped on the panel, for a tool that attaches
		# what it read to what it suggests — a receipt to its claim.
		# Only this question's: a receipt dropped three questions ago is not
		# evidence for whatever is being asked now.
		newest = next(
			(one for one in reversed(turns) if one.get("role") == "user" and not one.get("context")), {}
		)
		frappe.flags.one_ai_files = [one["url"] for one in newest.get("files") or [] if one.get("url")]
		return run.ask(
			CHAT, text, reference=doc.name, turns=carrying.carried(turns[-KEPT:]), heard=heard
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
				# A field's new text is the card beneath it; printed above it too,
				# it is the same paragraph twice.
				"text": "" if one.get("wrote") else (one.get("text") or ""),
				"files": [
					{key: value for key, value in file.items() if key != "data"}
					for file in one.get("files") or []
				],
				"looked": looked,
				"cards": [card for card in (look["card"] for look in looked) if card]
				+ list(one.get("cards") or []),
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


def _titled(doctype: str, name) -> str:
	"""A linked record by its title, where the reader may see it and it has one."""
	try:
		meta = frappe.get_meta(doctype)
		if meta.title_field and frappe.has_permission(doctype, "read", doc=str(name)):
			return str(frappe.db.get_value(doctype, name, meta.title_field) or name)
	except Exception:
		# A link to a doctype that is gone, or a record the reader cannot open:
		# the id is still true, and still what the card should say.
		pass
	return str(name)


def _card_rows(doctype: str, rows: list) -> list[dict]:
	"""A child table's rows as a card draws them: what the row is, its amount
	on the right, and the kind and date underneath — rather than every value in
	a line joined by dots."""
	meta = frappe.get_meta(doctype)
	kinds = {f.fieldname: f.fieldtype for f in meta.fields}
	drawn = []
	for row in rows:
		if not isinstance(row, dict):
			continue
		main, side, notes = [], "", []
		for field, value in row.items():
			if value in (None, ""):
				continue
			kind = kinds.get(field)
			if kind in ("Currency", "Float", "Int", "Percent") and not side:
				side = frappe.utils.fmt_money(value) if kind == "Currency" else f"{value:g}"
			elif kind in ("Link", "Select", "Date", "Datetime"):
				notes.append(str(value))
			else:
				main.append(strip_html_tags(str(value)).strip())
		drawn.append({"main": " ".join(main) or (notes.pop(0) if notes else ""), "side": side, "notes": notes})
	return drawn


def _card_value(value) -> str:
	"""A proposed value as a person reads it on a card.

	Text as text, and a child table as its rows, one a line — every row a
	suggestion carries is on the card, because the rows are what is approved.
	"""
	if isinstance(value, str):
		return strip_html_tags(value).strip()
	if isinstance(value, list):
		return "\n".join(
			" · ".join(str(one) for one in row.values() if one not in (None, ""))
			for row in value
			if isinstance(row, dict)
		)
	return json.dumps(value)


def _asked(
	text: str, page: dict | str | None, attached: list | None = None, field: dict | None = None
) -> list[dict]:
	"""The reader's turn, the page they were on, and what they dropped on it.

	A field being written replaces the page: it already says which record, and
	"the reader is looking at X" beside "the reader is writing X's notes" is the
	same sentence twice.
	"""
	from onedesk.one_ai import files as carrying
	from onedesk.one_ai import touch

	where = touch.told(field) if field else _page(page)
	# The model has no clock: asked for "Friday off" it books a Friday from its
	# training data. Today goes into every turn, not once per conversation, so a
	# chat picked up tomorrow still counts from the right day.
	where = " ".join(one for one in (_today(), where) if one)
	turns = [{"role": "user", "text": where, "calls": [], "context": True}]
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


def _today() -> str:
	"""Today in the site's own timezone, weekday first, as a person says it."""
	today = frappe.utils.getdate(frappe.utils.nowdate())
	return f"Today is {today.strftime('%A')} {today.day} {today.strftime('%B %Y')} ({today.isoformat()})."


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


def _field_card(field: dict, turns: list[dict], chat: str) -> list[str]:
	"""The answer to a field's question, as a suggestion for that field.

	An Edit like any other, so it is the same card and the same Apply. Put on
	the model's own last turn, so the card sits where the answer would have.
	"""
	from onedesk.one_ai import proposals, touch

	last = next((one for one in reversed(turns) if one.get("role") == "model"), None)
	said = (last or {}).get("text") or ""
	if not said.strip() or (last or {}).get("calls"):
		return []
	name = proposals.propose(
		"Edit",
		field["doctype"],
		{field["fieldname"]: touch.written(field, said)},
		record=field["name"] or None,
		reference=chat,
	)
	# Marked on the turn itself, which `say` keeps straight after this.
	last["cards"] = [name]
	last["wrote"] = True
	return [name]


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
