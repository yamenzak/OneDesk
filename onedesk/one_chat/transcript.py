"""An agent conversation's transcript: the model's turns, kept in an AI
Chat for each person and conversation or thread (answers.py), with what
is sent again of them, what is recalled of a long one, and its title. The
messages people read are Chat Messages; the transcript is what the agent
is sent."""

import json
import re

import frappe
from frappe.utils import now_datetime, strip_html_tags

from onedesk.one import registry
from onedesk.one_ai import run

KEPT = 24

#: How much of what a tool answered for an earlier question is sent again.
EARLIER_ROWS = 5
EARLIER_TEXT = 1200

#: How long a title taken from the first thing asked may be.
TITLE = 60

CHAT_TITLE = "chat_title"

CHAT_EARLIER = "chat_earlier"

#: Turns dropped past the last recollection before it is made again, so a
#: long conversation costs one short call a dozen turns, not one a turn.
RECALL_EVERY = 12

#: Characters of each old turn the recollection reads.
RECALLED_TURN = 600


def lighter(turns: list[dict]) -> list[dict]:
	"""The conversation with what tools answered for earlier questions cut
	down to a few rows and the start of each long text, saying how much was
	left out. What answers this question is sent whole."""
	asked = max(
		(at for at, one in enumerate(turns) if one.get("role") == "user" and not one.get("context")),
		default=-1,
	)
	return [
		{**one, "result": _cut(one.get("result"))} if at < asked and one.get("role") == "tool" else one
		for at, one in enumerate(turns)
	]


def whole(sent: list[dict], back: list[dict]) -> list[dict]:
	"""The run's turns with the earlier tool answers `lighter` cut put back as
	they were, so the conversation keeps every row it showed."""
	back = list(back)
	for at, one in enumerate(sent[: len(back)]):
		if one.get("role") == "tool" and back[at].get("role") == "tool" and back[at].get("id") == one.get("id"):
			back[at] = one
	return back


def _cut(said, depth: int = 0):
	if isinstance(said, list):
		kept = [_cut(one, depth + 1) for one in said[:EARLIER_ROWS]]
		return kept + ([{"left_out": len(said) - EARLIER_ROWS}] if len(said) > EARLIER_ROWS else [])
	if isinstance(said, dict) and depth < 3:
		return {key: _cut(value, depth + 1) for key, value in said.items()}
	if isinstance(said, str) and len(said) > EARLIER_TEXT:
		return said[:EARLIER_TEXT] + f"… ({len(said) - EARLIER_TEXT} more characters left out)"
	return said


def field_card(field: dict, turns: list[dict], chat: str) -> list[str]:
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
	last["cards"] = [name]
	last["wrote"] = True
	return [name]


def title(doc, turns: list[dict]) -> None:
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


def sent(doc, turns: list[dict]) -> list[dict]:
	"""The turns the model is sent: the newest `KEPT`, and what is recalled
	of those before them ahead, as frappe's Flow compacts a long chat.

	The recollection is made again only once `RECALL_EVERY` more turns have
	gone past it; until then the turns since it are sent whole."""
	if len(turns) <= KEPT:
		return turns
	upto = int(doc.get("earlier_upto") or 0)
	if upto > len(turns):
		upto = 0
	if not upto or len(turns) - upto > KEPT + RECALL_EVERY:
		until = len(turns) - KEPT
		said = _recalled(doc, doc.get("earlier") if upto else "", turns[upto:until])
		if said:
			frappe.db.set_value("AI Chat", doc.name, {"earlier": said, "earlier_upto": until}, update_modified=False)
			doc.earlier, doc.earlier_upto, upto = said, until, until
	if not upto or not doc.get("earlier"):
		return turns[-KEPT:]
	recalled = {"role": "user", "text": f"Earlier in this conversation: {doc.earlier}", "calls": [], "context": True}
	return [recalled, *turns[upto:]]


def _recalled(doc, before: str | None, turns: list[dict]) -> str:
	"""What is worth knowing of the turns, with what was recalled before."""
	said = "\n".join(
		f"{'Person' if one.get('role') == 'user' else registry.name('one_ai')}: {strip_html_tags(one.get('text') or '')[:RECALLED_TURN]}"
		for one in turns
		if one.get("role") in ("user", "model") and not one.get("context") and (one.get("text") or "").strip()
	)
	if not said:
		return before or ""
	text = (f"Recalled before: {before}\n\n" if before else "") + said
	try:
		answer = run.once(CHAT_EARLIER, text, reference=doc.name)
	except Exception:
		frappe.log_error(title="OneAI could not recall a long conversation", reference_doctype="AI Chat", reference_name=doc.name)
		return before or ""
	return strip_html_tags(answer or "").strip()[:2000] or before or ""


def turns_of(doc) -> list[dict]:
	try:
		return json.loads(doc.turns or "[]")
	except ValueError:
		return []


def keep(doc, turns: list[dict], spent: float) -> None:
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
