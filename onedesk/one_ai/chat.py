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

#: Tools whose calls are not drawn in the conversation at all.
QUIET_TOOLS = ("remember",)


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
	doc = frappe.get_doc(
		{"doctype": "AI Chat", "title": frappe._("New conversation"), "chosen_model": _usual()}
	).insert()
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
		page=page,
	)

	return {
		"name": doc.name,
		"title": doc.title,
		"said": shown(turns),
		"spent": doc.spent or 0.0,
		"run": run_id,
		**_model(doc),
	}


def answer(chat: str, text: str, field: dict | None, run_id: str, page: dict | str | None = None) -> None:
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
		out = _ran(doc, text, turns, heard, page)
		turns = turns[: -min(KEPT, len(turns))] + list(out.get("turns") or [])
		if field:
			_field_card(field, turns, doc.name)
		doc.model = out.get("model") or doc.model
		_keep(doc, turns, spent=float(out.get("credits") or 0))
		_tell(run_id, chat, {"done": True, "credits": out.get("credits"), "rounds": out.get("rounds")})
		_title(doc, turns)
	except frappe.ValidationError as raised:
		# `_ran` has already put a fault into words somebody can act on, unless
		# it is the provider's own, which is written for us, not for them.
		frappe.db.rollback()
		said = frappe.utils.strip_html(str(raised))
		if _providers(said):
			frappe.log_error(
				title="OneAI provider refused", message=said, reference_doctype="AI Chat", reference_name=chat
			)
			said = frappe._("OneAI could not answer just now. Try again in a moment.")
		_tell(run_id, chat, {"failed": said})
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="OneAI run failed", reference_doctype="AI Chat", reference_name=chat)
		_tell(run_id, chat, {"failed": frappe._("That did not go through.")})


def _providers(said: str) -> bool:
	"""A provider's own error, passed back through the account: its JSON, its
	validation messages, the gateway's call named in it. Pure."""
	return any(
		mark in (said or "") for mark in ("AiError", "proxy.ai_run", '"object":"error"', "validation error")
	)


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
		state["steps"].append(
			_looked({"tool": step["tool"], "args": step.get("args")}, {"ran": step.get("ran")})
		)
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
		fields=["name", "kind", "for_doctype", "record", "state", "why", "changes", "was", "applied_doc"],
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
		# What approving it changes, one line each, as the tool said it: the
		# page's whole state underneath is not a diff anybody reads.
		head = changes.get("letter_head") or {}
		return {
			"doctype": doctype,
			"name": (row.get("record") or "") if row.get("kind") == "Holidays" else "",
			"title": changes.get("title") or "" if row.get("kind") == "Setup" else "",
			# Where a Setup card's report, dashboard, level or person opens once approved.
			"route": changes.get("route") if row.get("kind") == "Setup" else None,
			"what": changes.get("what") if row.get("kind") == "Setup" else None,
			# A format or a letter head it draws is shown as the page, before Approve.
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
		# The reply as it will be sent, to be read before it opens to send.
		return {
			"doctype": doctype,
			"name": changes.get("subject") or "",
			"title": "",
			"fields": [{"label": frappe._("Reply"), "value": str(changes.get("text") or "")}],
		}

	if row.get("kind") == "Signature":
		# The signature as it will read, a line each.
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
	# A name typed for a kind whose name a person types (one_ai/kind.py), first.
	labels = {"__newname": "Name", **labels}
	known = {field.fieldname: field for field in (meta.fields if meta else [])}
	# In the form's own order: stored JSON comes back alphabetical, which put
	# "Asked For On" on the card and pushed "To Date" off it.
	place = {name: at for at, name in enumerate(labels)}
	ordered = sorted(changes.items(), key=lambda one: place.get(one[0], len(place)))
	tables = {
		f.fieldname: f.options
		for f in (meta.fields if meta else [])
		if f.fieldtype in frappe.model.table_fields
	}
	# Every field, not the first six: approving a card approves all of it, and
	# a card setting twenty settings had shown six. The panel folds the rest.
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
			"value": _formatted(known[field], value, changes) if field in known else _card_value(value),
		}
		if row.get("kind") == "Edit" and field in was:
			# A change reads as one: what it holds now, and what it would hold.
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


def _ran(doc, text: str, turns: list[dict], heard=None, page: dict | str | None = None) -> dict:
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
		frappe.flags.one_ai_chat = doc.name  # so searching past chats skips this one
		from onedesk.one_ai import groups, suggest

		if isinstance(page, str):
			page = frappe.parse_json(page) if page.strip() else None
		return run.ask(
			CHAT,
			text,
			reference=doc.name,
			turns=carrying.carried(turns[-KEPT:]),
			heard=heard,
			expects=suggest.expected(text) or _expects_edit(turns),
			groups=groups.chosen(text, page, turns),
			pinned=_pinned(doc),
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
	# Named by its person, so OneAI does not name it again.
	doc.titled = 1
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
	# Each call is answered by the tool turns straight after the turn that
	# made it, in order. Not by id: Gemini's id is the tool's name, so matched
	# by id every earlier call to a tool showed the last answer it gave.
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
			seen = set()  # a new question: its answer draws its own records
		looked = [
			_looked(call, _answering(call, answers.get(at) or [], n))
			for n, call in enumerate(one.get("calls") or [])
			# Keeping a memory is housekeeping, not something to read about in
			# the conversation; the memory list is where it is seen and undone.
			if call.get("tool") not in QUIET_TOOLS
		]
		# A record read twice while answering one question is one card.
		for look in looked:
			fresh = [
				rec for rec in look.get("records") or [] if (rec.get("doctype"), rec.get("name")) not in seen
			]
			seen |= {(rec.get("doctype"), rec.get("name")) for rec in fresh}
			look["records"] = fresh
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
				# What it kept this turn: not drawn as a lookup, but said in one
				# quiet line with Undo, so a person knows it kept anything at all.
				"remembered": _remembered(one, answers.get(at) or []),
				"cards": [card for card in (look["card"] for look in looked) if card]
				+ list(one.get("cards") or []),
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


def _looked(call: dict, result: dict | None) -> dict:
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
	said = str(error).split(". ", 1)[0].strip()
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

	# One record gets the full card; several get two fields each, because a list
	# drawn at full height is a list the answer sits below the bottom of.
	most = FIELDS if len(found) == 1 else BRIEF
	return [_drawn(doctype, row, most) for row in found[:CARDS]], max(len(found) - CARDS, 0)


#: How many records a list of them carries. The panel shows three and the rest
#: behind "Show more"; past this, the list itself is the place to read them.
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
		drawn = _drawn(doctype, row, 1)
		told = (drawn["fields"] or [{}])[0]
		rows.append(
			{"name": drawn["name"], "title": drawn["title"], "meta": told.get("value"), "meta_label": told.get("label")}
		)
	filters = (call.get("args") or {}).get("filters")
	return {
		"doctype": doctype,
		"total": len(found),
		"rows": rows,
		# A list it read with filters opens on the same filters.
		"filters": filters if isinstance(filters, dict) else None,
	}


def _drawn(doctype: str, row: dict, most: int = FIELDS) -> dict:
	"""One record as a card: what it is, what it is called, and a few fields."""
	meta = frappe.get_meta(doctype)
	titled = meta.title_field and row.get(meta.title_field)
	skip = {"name", "doctype", "idx", "owner", meta.title_field}

	fields = []
	for field in meta.fields:
		if field.fieldname in skip or field.fieldname not in row:
			continue
		# What the form hides, the card hides — Company among them — and the
		# naming series is how an id is made, not something about the record.
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


#: Kept as the text they are: frappe's formatter turns their newlines into <br>.
AS_TEXT = {"Data", "Small Text", "Text", "Long Text", "Text Editor", "HTML Editor", "Markdown Editor", "Code"}


def _formatted(df, value, doc: dict | None = None) -> str:
	"""A value as the form would show it: frappe's own formatter, so a date is
	in the site's date format and money carries its currency. A link is its
	record's title, and text stays text."""
	if value in (None, ""):
		return ""
	if df.fieldtype == "Link" and df.options:
		return _titled(df.options, value)
	if df.fieldtype == "Check":
		# A setting is on or off; a record's box is yes or no.
		if df.parent and frappe.get_meta(df.parent).issingle:
			return frappe._("On") if frappe.utils.cint(value) else frappe._("Off")
		return frappe._("Yes") if frappe.utils.cint(value) else frappe._("No")
	if df.fieldtype in ("Attach", "Attach Image"):
		return str(value).rsplit("/", 1)[-1]  # the file's name, not where it is kept
	if df.fieldtype in AS_TEXT or isinstance(value, (list, dict)):
		return _card_value(value)
	from frappe.utils.formatters import format_value

	return strip_html_tags(str(format_value(value, df, doc=frappe._dict(doc or {})))).strip()


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
			kind = df.fieldtype if df else None
			shown = _formatted(df, value, {**row, **(parent or {})}) if df else str(value)
			if kind in ("Currency", "Float", "Int", "Percent") and not side:
				side = shown
			elif kind in ("Link", "Select", "Date", "Datetime"):
				notes.append(shown)
			else:
				main.append(shown)
		drawn.append(
			{"main": " ".join(main) or (notes.pop(0) if notes else ""), "side": side, "notes": notes}
		)
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
	from onedesk.one_ai import memory

	where = " ".join(
		one for one in (_today(), _workspace(), _reader(), where, memory.told(_doctype(page))) if one
	)
	turns = [{"role": "user", "text": where, "calls": [], "context": True}]
	about = _field_asked(page)
	if about:
		# Kept on the turn so the run knows a change card is what this is for.
		turns[0]["about"] = about
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


def _workspace() -> str:
	"""The facts about this workspace a question can turn on: whose it is, its
	money, its clock — and whatever a module adds through `one_ai_workspace`,
	OneHR's weekly offs among them. A model that did not know Friday is off here
	booked it as a working day."""
	company = frappe.defaults.get_global_default("company")
	currency = frappe.defaults.get_global_default("currency")
	zone = frappe.db.get_single_value("System Settings", "time_zone")
	said = [
		"This workspace"
		+ (f" is {company}'s" if company else "")
		+ (f"; its money is {currency}" if currency else "")
		+ (f"; its clock is {zone}" if zone else "")
		+ "."
	]
	for path in frappe.get_hooks("one_ai_workspace"):
		one = frappe.get_attr(path)()
		if one:
			said.append(one)
	return " ".join(said)


def _doctype(page: dict | str | None) -> str | None:
	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	if not isinstance(page, dict):
		return None
	return (page.get("doctype") or "").strip() or None


def _reader() -> str:
	"""Who is asking, so "my" and "me" are somebody.

	Without it a model asked for "my leave" filters on a field it invents with
	the value "me". A module that knows more about the reader — OneHR, their
	employee record — says it through the `one_ai_reader` hook.
	"""
	user = frappe.session.user
	said = [f"The reader is {frappe.utils.get_fullname(user)} ({user})."]
	language = frappe.db.get_value("User", user, "language") or frappe.db.get_single_value(
		"System Settings", "language"
	)
	if language and language != "en":
		called = frappe.db.get_value("Language", language, "language_name") or language
		said.append(f"They read {called}: answer in {called} unless they write in another language.")
	for path in frappe.get_hooks("one_ai_reader"):
		one = frappe.get_attr(path)()
		if one:
			said.append(one)
	return " ".join(said)


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
		said = f"The reader is looking at the {doctype} record {record}.{_brief(doctype, record)}{_fields_said(doctype)}"
		return said + _about(doctype, record, (page.get("field") or "").strip())
	if doctype:
		filters = page.get("filters")
		narrowed = f", narrowed to {json.dumps(filters)}" if filters else ""
		return f"The reader is looking at a {view or 'list'} of {doctype}{narrowed}.{_fields_said(doctype)}"
	if page.get("page"):
		# A desk page has no record to name, so the module it belongs to says
		# what it is. Only the page's name comes from the browser.
		for path in frappe.get_hooks("one_ai_page"):
			said = frappe.get_attr(path)(page)
			if said:
				return said
		return f"The reader is on the {(page.get('label') or page['page'])} page."
	return f"The reader is on the {view} page." if view else ""


def _brief(doctype: str, name: str) -> str:
	"""The record's main fields, as its card would show them, so a question
	about it starts from what it says — a CV's fit was being judged against a
	job opening the model had not read."""
	try:
		if not frappe.has_permission(doctype, "read", doc=name):
			return ""
		doc = frappe.get_doc(doctype, name)
		# A field above the reader's level is not theirs to be told about,
		# here any more than on the form.
		doc.apply_fieldlevel_read_permissions()
		row = doc.as_dict()
	except Exception:
		return ""
	drawn = _drawn(doctype, row, most=BRIEF_FIELDS)
	said = "; ".join(f"{one['label']}: {one['value']}" for one in drawn["fields"] if one.get("value"))
	# The long text a card leaves off is often what the record is about — a job
	# opening's description — so the first one is said, shortened.
	meta = frappe.get_meta(doctype)
	prose = next(
		(
			_card_value(row.get(f.fieldname))
			for f in meta.fields
			if f.fieldtype in ("Text Editor", "Small Text", "Text", "Long Text")
			and not f.hidden
			and row.get(f.fieldname)
		),
		"",
	)
	title = drawn.get("title") if drawn.get("title") != name else ""
	parts = [f"“{title}”" if title else "", said, prose[:BRIEF_PROSE]]
	told = ". ".join(one.rstrip(".") for one in parts if one)
	return f" It says: {told[:BRIEF_SAID]}." if told else ""


#: How much of the record on screen the context turn carries.
BRIEF_SAID = 700
BRIEF_FIELDS = 8
BRIEF_PROSE = 300


def _expects_edit(turns: list[dict]) -> str | None:
	"""A question asked from a field's own mark is answered with a change to
	it — or with "it is right as it is", which the edit refuses as no change."""
	newest = next((one for one in reversed(turns) if one.get("context")), {})
	return "edit_record" if newest.get("about") else None


def _field_asked(page) -> str | None:
	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	return ((page or {}).get("field") or "").strip() or None if isinstance(page, dict) else None


def _about(doctype: str, record: str, fieldname: str) -> str:
	"""The one field a question is about, handed over with the question: what
	it is for, what it holds, and what it may hold. Asked for by the mark beside
	a settings field, whose question a small model otherwise answered from the
	field list alone — "no change suggested" for an empty template field with
	the obvious template sitting there."""
	if not fieldname:
		return ""
	from onedesk.one_ai import tools

	try:
		said = tools.about_field(doctype, fieldname, record)
	except Exception:
		return ""
	return f" The question is about this field: {json.dumps(said, default=str)}"


def _fields_said(doctype: str) -> str:
	"""The type's fields, told up front: a model that has them uses them, and
	one that has to ask for them first guesses instead — "due_date" on a ToDo
	whose field is "date"."""
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return ""
	from onedesk.one_ai.kind import fields_of

	return f" {doctype}'s fields: {', '.join(fields_of(frappe.get_meta(doctype), most=40))}."


def _chat(chat: str | None, text: str):
	if chat:
		doc = frappe.get_doc("AI Chat", chat)
		doc.check_permission("write")
		return doc
	return frappe.get_doc({"doctype": "AI Chat", "title": text[:TITLE], "chosen_model": _usual()}).insert()


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
	"""Which model answers here, whether the reader may pick another, and where
	an administrator changes what everybody gets.

	The one the last answer came from, if there was one; then the one the
	person picked; then what the workspace picked for the chat action; then
	nothing, and the panel says the default is answering.
	"""
	from onedesk.one import roles

	chosen = (doc and doc.get("chosen_model")) or (None if doc else _usual())
	said = (doc and doc.get("model")) or chosen or run.mine(CHAT).get("model") or ""
	settable = roles.administers() and frappe.db.exists("AI Action Setting", CHAT)
	return {
		"model": named(said),
		"model_id": said,
		"chosen_model": chosen or "",
		"may_choose": may_choose(),
		"model_at": CHAT if settable else None,
	}


def named(model: str) -> str:
	"""A catalogue id as a person reads it: `google-ai-studio:gemini-2.5-flash`
	as Gemini 2.5 Flash."""
	return run._model_name(model) if model else ""


#: How long the models a panel offers are kept. The account's catalogue
#: changes when a provider adds or withdraws one, which is rare.
MODELS_KEPT = 600


def may_choose() -> bool:
	"""Whether the reader may pick the model for their own conversations:
	administrators always, everybody else when the workspace lets them."""
	from onedesk.one import roles

	return bool(roles.administers() or frappe.db.get_value("AI Action Setting", {"action": CHAT}, "people_choose"))


@frappe.whitelist()
def models() -> dict:
	"""The models the reader may pick for the panel, and which they picked.

	Only the names, their makers and their logos: what a model costs is the
	administrator's to weigh, in the workspace's OneAI settings. Kept for ten minutes per
	workspace, because the panel asks whenever its menu opens."""
	from onedesk.one import account
	from onedesk.one_ai import logos

	if not may_choose():
		return {"models": [], "chosen": "", "usual": ""}
	key = "one_ai_chat_models"
	offered = frappe.cache.get_value(key)
	if offered is None:
		needs = frappe.db.get_value("AI Action", CHAT, "capability") or "Text Generation"
		said = account.ask("onedesk.one_admin.proxy.ai_models_for", needs=[needs]) or {}
		offered = [
			{
				"name": one["name"],
				"label": one.get("label") or named(one["name"]),
				"maker": one.get("maker") or "",
				"logo": logos.url(one.get("logo_domain")),
				"default": bool(one.get("default")),
			}
			for one in said.get(needs) or []
		]
		frappe.cache.set_value(key, offered, expires_in_sec=MODELS_KEPT)
	workspace = run.mine(CHAT).get("model") or next((one["name"] for one in offered if one["default"]), "")
	return {"models": offered, "chosen": _usual(), "usual": workspace}


@frappe.whitelist(methods=["POST"])
def choose_model(model: str | None = None, chat: str | None = None) -> dict:
	"""Pick the model for a conversation, and for the reader's next ones;
	nothing goes back to the workspace's own choice. Refused for somebody the
	workspace does not let choose, and for a model it does not offer."""
	if not may_choose():
		frappe.throw(frappe._("Only an administrator picks the model here."), frappe.PermissionError)
	model = (model or "").strip()
	if model and model not in {one["name"] for one in models()["models"]}:
		frappe.throw(frappe._("That model is not offered."), title=frappe._("Not changed"))
	frappe.defaults.set_default(USUAL, model, frappe.session.user)
	if not chat:
		return _model()
	doc = frappe.get_doc("AI Chat", chat)
	doc.check_permission("write")
	doc.chosen_model = model or None
	# The pill says what answers next, not what answered last.
	doc.model = model or None
	doc.save()
	return _model(doc)


#: The reader's default for where they keep their pick.
USUAL = "one_ai_chat_model"


def _usual() -> str:
	"""The model the reader picked last, for a conversation they start; empty
	for the workspace's own choice, or when they may no longer choose."""
	return (frappe.defaults.get_user_default(USUAL) or "") if may_choose() else ""


def _pinned(doc) -> str | None:
	"""The model this conversation runs on, when its person picked one and
	still may."""
	return (doc.get("chosen_model") or None) if may_choose() else None


def _title(doc, turns: list[dict]) -> None:
	"""Name a conversation after its first answer, as a person would name a
	folder, unless its person already named it. Said to the panel as it lands.
	A title that fails leaves the first words of the question, which is what
	the conversation was called before."""
	if doc.get("titled"):
		return
	asked = [one for one in turns if one.get("role") == "user" and not one.get("context")]
	if len(asked) != 1:
		return
	answered = next((one.get("text") for one in reversed(turns) if one.get("role") == "model" and one.get("text")), "")
	try:
		said = run.once(CHAT_TITLE, f"{asked[0].get('text') or ''}\n\n{(answered or '')[:600]}", reference=doc.name)
	except Exception:
		frappe.log_error(title="OneAI could not title a conversation", reference_doctype="AI Chat", reference_name=doc.name)
		return
	title = re.sub(r"\s+", " ", strip_html_tags(said or "")).strip().strip("\"'.").strip()[:TITLE]
	if not title:
		return
	frappe.db.set_value("AI Chat", doc.name, {"title": title, "titled": 1}, update_modified=False)
	frappe.publish_realtime("one_ai_title", {"chat": doc.name, "title": title}, user=doc.owner, after_commit=True)


#: The action that names a conversation (fixtures/ai_action.json).
CHAT_TITLE = "chat_title"


def _turns(doc) -> list[dict]:
	try:
		return json.loads(doc.turns or "[]")
	except ValueError:
		# A conversation that will not parse is not one to throw somebody's next
		# question away over; it starts again and the row keeps what it had.
		return []


def _keep(doc, turns: list[dict], spent: float) -> None:
	from onedesk.one_ai import tools

	for turn in turns:
		for call in turn.get("calls") or []:
			call["args"] = tools.shown_args(call.get("tool"), call.get("args"))
		if turn.get("role") == "tool":
			turn["result"] = tools.shown_result(turn.get("tool"), turn.get("result"))
	doc.turns = json.dumps(turns)
	doc.last_said_on = now_datetime()
	doc.spent = round((doc.spent or 0) + spent, 6)
	doc.save()
	frappe.db.commit()
