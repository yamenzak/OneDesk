"""How an agent answers in a conversation: the person's message goes on
the conversation's transcript (transcript.py), and the agent asked answers
it in the background, as the person who asked, with its own tools
(one_ai/agents/talk.py); what it said is posted where it was asked, in the
asker's thread. Una answers for herself and hands a department's work to
its agent. AGENTS.md, How an agent answers."""

import json

import frappe
from frappe import _

from onedesk.one_chat import agents, channels, messages, transcript

CHAT = "chat"
"""The job an agent's answer runs as, on the account (one_ai/jobs.py)."""

RUN_TIMEOUT = 600

RUN_KEPT = 900


def held(channel: str, thread: str | None, user: str) -> str | None:
	"""The AI Chat this person's questions in a conversation or thread go on."""
	found = frappe.get_all(
		"Chat Message",
		filters={"channel": channel, "thread": thread or ("is", "not set"), "sender": user, "ai_chat": ("is", "set")},
		pluck="ai_chat",
		order_by="creation desc",
		limit=1,
	)
	if found:
		return found[0]
	if not thread:
		return frappe.db.get_value("Chat Channel", {"name": channel, "kind": channels.AGENT, "owner": user}, "ai_chat")
	return None


def ready(channel, thread: str | None) -> str | None:
	"""Refuses before anything is posted when OneAI is off or the agent is
	still answering this person here; answers the transcript to go on."""
	from onedesk.one import apps, registry

	if not apps.ai_on():
		frappe.throw(_("{0} is turned off for this workspace.").format(registry.name("one_ai")))
	kept = held(channel.name, thread, frappe.session.user)
	if kept and running(kept):
		frappe.throw(_("Still answering the last question."), title=_("Not yet"))
	return kept


def ask(message, channel, agent: str, kept: str | None, page=None, field=None) -> str:
	"""Put the message on the transcript and start the agent's answer;
	answers the run to follow. The question is kept before the answer is
	asked for, so a run that fails leaves it there."""
	from onedesk.one_ai import here, touch
	from onedesk.one_ai.agents import talk

	text = (message.text or "").strip()
	writing = touch.target(field)
	urls = [one["file_url"] for one in messages.files_of(message)]
	doc = frappe.get_doc("AI Chat", kept) if kept else frappe.get_doc({"doctype": "AI Chat", "title": (text or (urls and urls[0]) or _("New conversation"))[: transcript.TITLE]}).insert()
	turns = transcript.turns_of(doc)
	if not turns and writing:
		doc.title = f"{_(writing['label'])} — {text}"[: transcript.TITLE]
	turns.extend(here.asked(text, page, urls, writing, who=talk.who(app_of(agent))))
	transcript.keep(doc, turns, spent=0.0)
	message.db_set({"ai_chat": doc.name, "asks": agent}, update_modified=False)
	if channel.kind == channels.AGENT and not channel.ai_chat:
		frappe.db.set_value("Chat Channel", channel.name, "ai_chat", doc.name, update_modified=False)
	run = frappe.generate_hash(length=12)
	_tell(run, doc.name, {"started": True})
	frappe.enqueue(
		f"{__name__}.answer",
		queue="default",
		timeout=RUN_TIMEOUT,
		enqueue_after_commit=True,
		chat=doc.name,
		agent=agent,
		text=text,
		field=writing,
		run=run,
		page=page,
	)
	return run


def app_of(agent: str | None) -> str | None:
	"""The app whose agent answers; None for Una."""
	return None if not agent or agent == agents.UNA else agent


def answer(chat: str, agent: str, text: str, field: dict | None, run: str, page=None) -> None:
	"""The agent's answer, in the background, as the person who asked:
	frappe starts a job as whoever enqueued it, so every read still runs
	with their permissions. Each step is told to their browser; the answer
	is kept on the transcript and posted into the conversation."""
	from onedesk.one import registry

	doc = frappe.get_doc("AI Chat", chat)
	turns = transcript.turns_of(doc)
	try:
		out = _asked(doc, agent, text, turns, lambda step: _tell(run, chat, step), page)
		turns = turns[: -min(transcript.KEPT, len(turns))] + transcript.whole(turns[-transcript.KEPT :], list(out.get("turns") or []))
		if field:
			transcript.field_card(field, turns, doc.name)
		doc.model = out.get("model") or doc.model
		transcript.keep(doc, turns, spent=float(out.get("credits") or 0))
		posted(doc, turns)
		_tell(run, chat, {"done": True, "credits": out.get("credits"), "rounds": out.get("rounds")})
		transcript.title(doc, turns)
	except frappe.ValidationError as raised:
		frappe.db.rollback()
		said = frappe.utils.strip_html(str(raised))
		if _providers(said):
			frappe.log_error(title="OneAI provider refused", message=said, reference_doctype="AI Chat", reference_name=chat)
			said = _("{0} could not answer. Try again in a moment.").format(registry.name("one_ai"))
		_tell(run, chat, {"failed": said})
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="OneAI run failed", reference_doctype="AI Chat", reference_name=chat)
		_tell(run, chat, {"failed": _("That did not go through.")})


def _asked(doc, agent: str, text: str, turns: list[dict], heard, page) -> dict:
	"""The agent's run, with a fault said in words somebody can act on:
	`Again` is transient, so the question stays to be asked again;
	`Refused` already reads as a sentence; anything else keeps its own
	traceback."""
	from onedesk.one import registry
	from onedesk.one_admin import faults
	from onedesk.one_ai import files as carrying
	from onedesk.one_ai import here, suggest
	from onedesk.one_ai.agents import talk

	newest = next((one for one in reversed(turns) if one.get("role") == "user" and not one.get("context")), {})
	frappe.flags.one_ai_files = [one["url"] for one in newest.get("files") or [] if one.get("url")]
	frappe.flags.one_ai_chat = doc.name
	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	frappe.flags.one_ai_page = page if isinstance(page, dict) else None
	try:
		return talk.ask(
			app_of(agent),
			CHAT,
			text,
			carrying.carried(transcript.lighter(transcript.sent(doc, turns))),
			reference=doc.name,
			heard=heard,
			expects=suggest.expected(text) or here.expects_edit(turns),
		)
	except faults.Again:
		frappe.throw(
			_("{0} could not be reached. The question is still here — try again.").format(registry.name("one_ai")),
			title=_("Not answered"),
		)
	except faults.Refused as raised:
		frappe.throw(frappe.utils.strip_html(str(raised)), title=_("Not answered"))


def _providers(said: str) -> bool:
	"""A provider's own error, passed back through the account: its JSON, its
	validation messages, the gateway's call named in it. Pure."""
	return any(mark in (said or "") for mark in ("AiError", "proxy.ai_run", '"object":"error"', "validation error"))


def progress(run: str) -> dict:
	"""Where a run has got to, for a browser that missed the messages: a
	socket that dropped or a tab that slept asks here. Only the person
	whose run it is."""
	state = frappe.cache.get_value(_key(run)) or {}
	if state.get("user") != frappe.session.user:
		return {}
	return state


def _key(run: str) -> str:
	return f"one_ai_run:{run}"


def running(chat: str) -> bool:
	return bool(frappe.cache.get_value(f"one_ai_busy:{chat}"))


def _tell(run: str, chat: str, step: dict) -> None:
	"""One step of a run: kept for a browser that asks, and sent to the one
	listening."""
	from onedesk.one_ai import drawn

	state = frappe.cache.get_value(_key(run)) or {"user": frappe.session.user, "chat": chat, "steps": []}
	if step.get("tool"):
		state["steps"].append(drawn.look_of({"tool": step["tool"], "args": step.get("args")}, {"ran": step.get("ran")}))
	for end in ("done", "failed"):
		if end in step:
			state[end] = step[end]
	frappe.cache.set_value(_key(run), state, expires_in_sec=RUN_KEPT)
	busy = f"one_ai_busy:{chat}"
	if step.get("done") or step.get("failed"):
		frappe.cache.delete_value(busy)
	else:
		frappe.cache.set_value(busy, run, expires_in_sec=RUN_TIMEOUT)
	frappe.publish_realtime("one_ai_run", {"run": run, "chat": chat, **step}, user=state["user"], after_commit=False)


def answered(turns: list[dict]) -> list[dict]:
	"""What the agent said since the person's last question, as the panel
	reads it (drawn.shown). Pure but for shown's lookups."""
	from onedesk.one_ai import drawn

	said = drawn.shown(turns)
	last = max((at for at, one in enumerate(said) if one["role"] == "you"), default=-1)
	return [one for one in said[last + 1 :] if one["role"] == "model"]


def posted(doc, turns: list[dict]) -> None:
	"""The agent's answer, posted where it was asked."""
	asked = frappe.get_all(
		"Chat Message",
		filters={"ai_chat": doc.name, "asks": ("is", "set")},
		fields=["name", "channel", "thread", "asks"],
		order_by="creation desc",
		limit=1,
	)
	if not asked:
		return
	asked = asked[0]
	channel = frappe.get_doc("Chat Channel", asked.channel)
	thread = asked.thread or (asked.name if channel.kind == channels.CHANNEL else None)
	for one in answered(turns):
		parts = {key: one.get(key) for key in ("looked", "remembered", "cards", "files") if one.get(key)}
		messages.post(
			channel,
			one.get("text") or "",
			thread=thread,
			sender=agents.user_of(asked.asks) or "",
			agent=asked.asks,
			ai_chat=doc.name,
			parts=json.dumps(parts, default=str) if parts else None,
		)
	if channel.kind == channels.AGENT and doc.title and doc.title != channel.title:
		frappe.db.set_value("Chat Channel", channel.name, "title", doc.title[: channels.TITLE], update_modified=False)
