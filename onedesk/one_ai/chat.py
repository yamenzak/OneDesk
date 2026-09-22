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
		return {"name": None, "title": None, "said": [], "spent": 0.0}
	doc = frappe.get_doc("AI Chat", chat)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"title": doc.title,
		"said": shown(_turns(doc)),
		"spent": doc.spent or 0.0,
	}


@frappe.whitelist()
def say(text: str, chat: str | None = None, page: dict | str | None = None) -> dict:
	"""Say one thing, run the loop, and keep what came back.

	The whole conversation is stored before the answer is asked for, so a run
	that fails leaves the question in the chat rather than losing it.
	"""
	text = (text or "").strip()
	if not text:
		frappe.throw(frappe._("Nothing was asked."))

	doc = _chat(chat, text)
	turns = _turns(doc)
	turns.extend(_asked(text, page))
	_keep(doc, turns, spent=0.0)

	out = run.ask(CHAT, text, reference=doc.name, turns=turns[-KEPT:])
	turns = turns[: -min(KEPT, len(turns))] + list(out.get("turns") or [])
	_keep(doc, turns, spent=float(out.get("credits") or 0))

	return {
		"name": doc.name,
		"title": doc.title,
		"said": shown(turns),
		"spent": doc.spent or 0.0,
		"credits": out.get("credits"),
		"rounds": out.get("rounds"),
		"proposals": out.get("proposals") or [],
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
	return frappe.get_list(
		"AI Proposal",
		filters={"name": ["in", list(named)[:50]]},
		fields=["name", "kind", "for_doctype", "record", "state", "why", "changes", "applied_doc"],
		limit_page_length=50,
	)


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
	return {
		"tool": call.get("tool"),
		"args": call.get("args") or {},
		"ran": bool(said.get("ran")),
		"error": answered.get("error") if isinstance(answered, dict) else None,
		"card": said.get("card"),
	}


def _asked(text: str, page: dict | str | None) -> list[dict]:
	"""The reader's turn, and the page they were on when they said it."""
	where = _page(page)
	turns = []
	if where:
		turns.append({"role": "user", "text": where, "calls": [], "context": True})
	turns.append({"role": "user", "text": text, "calls": []})
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
