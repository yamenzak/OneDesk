"""What OneAI knows beyond the record in front of it.

Three kinds, kept apart because they have three different owners:

- **the records themselves**, read live. `about_record` is everything the
  form's own sidebar knows about one record — its fields, what links to it,
  its comments, mail, changes, assignments and files — through the same
  frappe functions the sidebar calls, so it is never a copy that went stale
  and never more than the reader may open;
- **a person's own memory** (`AI Memory`), short facts somebody told OneAI to
  keep. Private to them like their conversations, kept at once and quietly —
  it is what they just said — and seen and deleted in the memory list. The
  same fact twice is one memory, and a correction replaces what it corrects;
- **the workspace's knowledge** (`AI Knowledge`), what an administrator
  wrote down for everybody: a policy, a glossary, how things are done here.

And a fourth that is not stored at all: the reader's own past conversations,
searched rather than summarised into anything.

None of it is pasted into every turn. A few memories and the knowledge for
the type on screen are; everything else is a tool the model calls, because
whatever is sent is paid for on every message.
"""

from typing import Annotated

import frappe
from frappe.utils import strip_html_tags


#: How many of a person's memories ride along on every turn, newest first.
#: Past this, `recall` finds the rest.
TOLD = 8

#: How much of one piece of knowledge rides along when its type is on screen.
KNOWLEDGE_TOLD = 600

#: How many of each kind of activity `about_record` reads.
ACTIVITY = 8

#: How much of a past conversation `search_my_chats` quotes around a match.
AROUND = 160


# ------------------------------------------------------------------- reads


def about_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
) -> dict:
	"""Everything known about one record: its fields, what links to it, its
	comments, emails, recent changes, who it is assigned to, its files, and
	anything the reader or the workspace wrote down about it. Use this when
	asked about a particular record rather than reading it field by field."""
	from frappe.desk.form import load

	from onedesk.one_ai import tools

	doctype = tools._type(doctype, name)
	record = tools.read_record(doctype, name)  # checks read permission
	# The sidebar's own function, which fills frappe.response rather than
	# returning; read it off and put the response back as it was.
	held = frappe.response.pop("docinfo", None)
	load.get_docinfo(doctype=doctype, name=name)
	info = frappe.response.pop("docinfo", None) or {}
	if held is not None:
		frappe.response["docinfo"] = held

	return {
		**{key: value for key, value in record.items() if value not in (None, "", [], 0)},
		"activity": {
			"comments": [
				{"by": one.get("owner"), "on": str(one.get("creation")), "said": _text(one.get("content"))}
				for one in (info.get("comments") or [])[-ACTIVITY:]
			],
			"emails": [
				{
					"subject": one.get("subject"),
					"from": one.get("sender"),
					"on": str(one.get("communication_date") or one.get("creation")),
					"said": _text(one.get("content"))[:300],
				}
				for one in (info.get("communications") or [])[:ACTIVITY]
			],
			"changes": [_changed(one) for one in (info.get("versions") or [])[:ACTIVITY]],
			"assigned_to": [one.get("owner") for one in info.get("assignments") or []],
			"files": [one.get("file_name") for one in info.get("attachments") or []],
			"tags": info.get("tags") or "",
		},
		"links_here": tools.what_links_here(doctype, name),
		"remembered": _remembered(doctype, name),
		"knowledge": _knowledge(doctype),
	}


def recall(
	text: Annotated[str, "Words to look for: a name, a subject, a term."],
) -> dict:
	"""Search what the reader asked OneAI to remember and what this workspace
	wrote down for OneAI — policies, a glossary, how things are done here."""
	words = _words(text)
	mine = frappe.get_list(
		"AI Memory",
		filters={"owner": frappe.session.user},
		or_filters=[["fact", "like", f"%{one}%"] for one in words],
		fields=["fact", "about_doctype", "about_name", "modified"],
		order_by="modified desc",
		limit_page_length=20,
	)
	known = frappe.get_list(
		"AI Knowledge",
		filters={"enabled": 1},
		or_filters=[f for one in words for f in (["title", "like", f"%{one}%"], ["body", "like", f"%{one}%"])],
		fields=["title", "applies_to", "body"],
		limit_page_length=5,
	)
	return {
		"remembered": [
			{"fact": one.fact, "about": f"{one.about_doctype} {one.about_name}".strip() or None} for one in mine
		],
		"knowledge": [{"title": one.title, "applies_to": one.applies_to, "text": _text(one.body)} for one in known],
	}


def search_my_chats(
	text: Annotated[str, "Words to look for in the reader's earlier conversations."],
) -> list:
	"""Search the reader's own earlier conversations with OneAI, newest first —
	for "what did we say about…" or "last time you told me…"."""
	words = _words(text)
	found = frappe.get_list(
		"AI Chat",
		filters={"owner": frappe.session.user},
		or_filters=[[field, "like", f"%{one}%"] for one in words for field in ("title", "turns")],
		fields=["name", "title", "last_said_on", "turns"],
		order_by="last_said_on desc",
		limit_page_length=30,
	)
	# Ranked by how many of the words were actually said — not the page
	# pointers and remembered facts every turn opens with, which would match
	# every conversation — and never the conversation asking.
	now = frappe.flags.one_ai_chat
	scored = []
	for one in found:
		said = _said(one.turns)
		hits = sum(word in said.lower() for word in words)
		if hits and one.name != now:
			scored.append((hits, one, said))
	scored.sort(key=lambda row: -row[0])
	return [
		{"chat": one.name, "title": one.title, "on": str(one.last_said_on), "said": _around(said, words)}
		for _hits, one, said in scored[:5]
	]


#: Words too common to search on.
COMMON = {"what", "when", "where", "which", "about", "before", "with", "that", "this", "have", "said", "tell", "told", "from"}


def _words(text: str) -> list[str]:
	"""The words worth searching on, shortened to a stem so "calling" finds
	"call"."""
	words = []
	for one in (text or "").lower().split():
		one = "".join(ch for ch in one if ch.isalnum())
		if len(one) < 3 or one in COMMON:
			continue
		for ending in ("ing", "ed", "es", "s"):
			if one.endswith(ending) and len(one) - len(ending) >= 3:
				one = one[: -len(ending)]
				break
		words.append(one)
	return words[:6] or [(text or "").strip().lower()]


# ------------------------------------------------------------- suggestions


def remember(
	fact: Annotated[str, "One short lasting fact, in a sentence, e.g. 'Omar Haddad is our finance lead.'"],
	replaces: Annotated[str, "The remembered fact this corrects, as you were told it, if it corrects one."]
	| None = None,
	about_doctype: Annotated[str, "The type of record it is about, if it is about one."] | None = None,
	about_name: Annotated[str, "That record's id."] | None = None,
) -> dict:
	"""Keep a fact for later conversations. Only when the person asks you to
	remember something, or tells you a lasting fact about themselves, their
	work or how they like things done that later conversations will need.
	Never the details of the task at hand, anything a record already holds,
	anything you worked out yourself, or something you already remember."""
	said = " ".join((fact or "").split())[:500]
	if not said:
		frappe.throw("Say the fact to keep.")
	mine = frappe.get_list(
		"AI Memory",
		filters={"owner": frappe.session.user},
		fields=["name", "fact"],
		order_by="modified desc",
		limit_page_length=MOST_KEPT,
	)
	# The same fact again is not a second memory; a correction replaces the
	# one it corrects, and a fact that says more replaces the one it grew from.
	for one in mine:
		if _same(said, one.fact) or (replaces and _same(replaces, one.fact)):
			if _plain(said) == _plain(one.fact) or _plain(said) in _plain(one.fact):
				return {"memory": one.name, "fact": one.fact, "state": "already remembered"}
			frappe.db.set_value("AI Memory", one.name, "fact", said)
			return {"memory": one.name, "fact": said, "state": "updated"}

	values = {"doctype": "AI Memory", "fact": said}
	if about_doctype and about_name and _names(said, about_doctype, about_name):
		values.update({"about_doctype": about_doctype, "about_name": about_name})
	kept = frappe.get_doc(values).insert()
	# Past the cap the oldest goes: a memory nobody has touched in two hundred
	# newer ones is the one least likely to be missed.
	for old in mine[MOST_KEPT - 1 :]:
		frappe.delete_doc("AI Memory", old.name)
	return {"memory": kept.name, "fact": said, "state": "remembered"}


#: How many memories one person keeps.
MOST_KEPT = 200


def _plain(text: str) -> str:
	return " ".join("".join(ch for ch in (text or "").lower() if ch.isalnum() or ch.isspace()).split())


def _same(one: str, other: str) -> bool:
	"""Whether two facts are the same fact: equal, one inside the other, or
	worded nearly alike."""
	import difflib

	a, b = _plain(one), _plain(other)
	if not a or not b:
		return False
	return a == b or a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= SAME


#: How alike two facts' words have to be to count as one fact.
SAME = 0.8


# ---------------------------------------------------------- the context turn


def told(doctype: str | None = None) -> str:
	"""What rides along on every turn: the reader's newest memories, and what
	the workspace wrote down for the type on screen. Empty when there is none."""
	said = []
	mine = frappe.get_list(
		"AI Memory",
		filters={"owner": frappe.session.user},
		fields=["fact"],
		order_by="modified desc",
		limit_page_length=TOLD,
	)
	if mine:
		# Worded as what is already known, not as a request: "the reader asked
		# you to remember X" read to a small model as being asked again.
		said.append("Already remembered from earlier conversations: " + " ".join(one.fact.strip() for one in mine))
	for one in _knowledge(doctype) if doctype else []:
		said.append(f"This workspace's note on {doctype}, \"{one['title']}\": {one['text'][:KNOWLEDGE_TOLD]}")
	return " ".join(said)


# ------------------------------------------------------------------ helpers
#
# Every read of AI Memory names the owner as well as relying on the doctype's
# if-owner rule: Administrator is not held by if-owner, and a memory read into
# somebody else's conversation is the one leak this module must not have.


def _names(fact: str, doctype: str, name: str) -> bool:
	"""Whether the record a memory is tied to is the one the fact is about.

	A small model asked to remember "Omar is our finance lead" tied it to the
	reader's own employee record — the one it had been told about. A fact that
	does not name the record's title or id is kept, and kept untied.
	"""
	if not frappe.db.exists("DocType", doctype) or not frappe.db.exists(doctype, name):
		return False
	title_field = frappe.get_meta(doctype).title_field
	title = frappe.db.get_value(doctype, name, title_field) if title_field else None
	said = fact.lower()
	return str(name).lower() in said or bool(title and str(title).lower() in said)


def _remembered(doctype: str, name: str) -> list[str]:
	return frappe.get_list(
		"AI Memory",
		filters={"owner": frappe.session.user, "about_doctype": doctype, "about_name": name},
		pluck="fact",
		limit_page_length=10,
	)


def _knowledge(doctype: str) -> list[dict]:
	found = frappe.get_list(
		"AI Knowledge",
		filters={"enabled": 1, "applies_to": doctype},
		fields=["title", "body"],
		limit_page_length=3,
	)
	return [{"title": one.title, "text": _text(one.body)} for one in found]


def _text(html) -> str:
	return " ".join(strip_html_tags(str(html or "")).split())


def _changed(version: dict) -> dict:
	"""One Version row as who changed which fields when."""
	try:
		data = frappe.parse_json(version.get("data") or "{}")
	except Exception:
		data = {}
	return {
		"by": version.get("owner"),
		"on": str(version.get("creation")),
		"fields": [one[0] for one in (data.get("changed") or [])][:10],
		"rows_added": len(data.get("added") or []),
	}


def _said(turns: str | None) -> str:
	"""What was actually said in a stored conversation: the person's turns and
	the answers, not the page pointers and tool rows around them."""
	try:
		said = [
			one.get("text") or ""
			for one in frappe.parse_json(turns or "[]")
			if one.get("role") in ("user", "model") and not one.get("context")
		]
	except Exception:
		said = []
	return " ".join(" ".join(said).split())


def _around(said: str, words: list[str]) -> str:
	"""The words either side of the first match."""
	low = said.lower()
	at = min((low.find(one) for one in words if one in low), default=-1)
	if at < 0:
		return said[: AROUND * 2]
	return said[max(at - AROUND, 0) : at + AROUND * 2]
