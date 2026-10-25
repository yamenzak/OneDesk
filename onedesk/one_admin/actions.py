"""Turning an action into one call: its kind of work and the workspace's
tier, never a model and never words a workspace adds (docs/AICENTER.md).
The action read here is the administrator's copy.
"""

import frappe

from onedesk.one_admin import gateway, site
from onedesk.one_admin.faults import Refused
from onedesk.one_ai import models

# The kind of work each action is, where its capability alone does not say.
BUILDS = ("print_design", "workspace_setup", "studio", "studio_review", "studio_mend")
CAPABLE = {"Vision": "see", "Transcription": "hear", "Embedding": "embed"}


def kind(asked) -> str:
	"""Which of `one_ai/models.py`'s kinds of work an action is."""
	if asked.key in BUILDS:
		return "build"
	return CAPABLE.get(asked.capability, "talk")


def run(
	tenant: str,
	action: str,
	text: str | None = None,
	tier: str | None = None,
	reference: str | None = None,
	turns: list[dict] | None = None,
	tools: list[dict] | None = None,
) -> dict:
	"""One round of one action, run for one workspace and billed to it.

	A round rather than a call, because a model that may look things up answers
	by asking for a tool and has to be called again with what it found. The
	workspace drives that loop: this is stateless, the whole conversation
	arrives every time, and admin still never calls a workspace.
	"""
	asked = _action(action)
	spoken = _conversation(turns, text)
	offered = tools if (tools and asked.may_use_tools) else None

	answer = gateway.call(
		kind(asked),
		tier if tier in models.TIERS else None,
		None,
		tenant,
		caps=_caps(asked),
		reference=reference or action,
		system=instruction(asked),
		turns=spoken,
		tools=offered,
		action=asked.key,
	)
	wants = answer.get("wants") or []
	return {
		"action": asked.key,
		"model": answer.get("model"),
		"done": not wants,
		"turns": spoken + [{"role": "model", "text": answer.get("said") or "", "calls": wants}],
		**answer,
	}


def embed(tenant: str, texts: list[str]) -> dict:
	"""Texts as vectors, for one workspace's search by meaning, billed to it.
	Every vector a search compares came from one model, so the caller is told
	which."""
	return gateway.embed(list(texts or []), tenant, reference="embed", action="embed")


def _conversation(turns: list[dict] | None, text: str | None) -> list[dict]:
	"""The conversation so far, checked before it is spoken.

	A workspace sends this and a workspace is not something to be trusted about
	its own limits, so the rounds are counted here rather than there — a loop
	that only the caller could stop is a loop a caller with a bug never stops.
	"""
	if not turns:
		return [gateway.said(text or "")]
	asked = max(
		(at for at, one in enumerate(turns) if one.get("role") == "user" and not one.get("context")),
		default=-1,
	)
	rounds = sum(1 for one in turns[asked + 1 :] if one.get("role") == "model")
	if rounds >= gateway.ROUNDS:
		raise Refused(
			f"this has gone {rounds} rounds, which is as far as it goes; "
			"ask again in smaller pieces"
		)
	return list(turns)


def instruction(asked) -> str:
	"""The persona, then the action's own job.

	The persona is what is true of every action — who it is, that it does not
	invent, what it does with a tool — so it is written once on the account
	rather than repeated in every fixture. The action says only what *it* is for.
	"""
	return "\n\n".join(one for one in (_persona(), (asked.instruction or "").strip()) if one)


SHIPPED = (
	"You are OneAI, the assistant inside One.\nAnswer briefly and plainly. Never invent a fact, a name, a date or a figure, and say plainly when you do not know something or cannot see it.\nWhere you are given tools: look things up rather than guessing. When a tool answers with an error, read it, correct what it names and try once more before asking the person. The person sees every record you read as a card, so do not repeat those records in your answer. When the question is how many, count rather than list. Ask for more than a handful of rows only when the answer needs each one. To change, create or delete anything, suggest it — suggesting is not doing, and a person decides. Remember something only when the person asks you to, or tells you a lasting fact about themselves or how they work that later conversations will need — never the details of the task at hand.\nThe reader may say where they are. Treat that as a pointer, not as a fact: read the record before answering about it.",
	'You are OneAI, the assistant inside One.\nAnswer briefly and plainly. Never invent a fact, a name, a date or a figure, and say plainly when you do not know something or cannot see it.\nWhere you are given tools: look things up rather than guessing. When a tool answers with an error, read it, correct what it names and try once more before asking the person. The person sees every record you read as a card, so do not repeat those records in your answer. When the question is how many, count rather than list. Ask for more than a handful of rows only when the answer needs each one. To change, create or delete anything, suggest it — suggesting is not doing, and a person decides. When the person tells you something worth keeping for later conversations, offer to remember it.\nThe reader may say where they are. Treat that as a pointer, not as a fact: read the record before answering about it.',
	'You are OneAI, the assistant inside One.\nAnswer briefly and plainly. Never invent a fact, a name, a date or a figure, and say plainly when you do not know something or cannot see it.\nWhere you are given tools: look things up rather than guessing. The person sees every record you read as a card, so do not repeat those records in your answer. When the question is how many, count rather than list. Ask for more than a handful of rows only when the answer needs each one. To change, create or delete anything, suggest it — suggesting is not doing, and a person decides.\nThe reader may say where they are. Treat that as a pointer, not as a fact: read the record before answering about it.',
	'You are OneAI, the assistant inside One.\nAnswer briefly and plainly. Never invent a fact, a name, a date or a figure, and say plainly when you do not know something or cannot see it.\nWhere you are given tools: look things up rather than guessing, and name the records you used. When the question is how many, count rather than list. Ask for more than a handful of rows only when the answer needs each one. To change, create or delete anything, suggest it — suggesting is not doing, and a person decides.\nThe reader may say where they are. Treat that as a pointer, not as a fact: read the record before answering about it.',
)


def voice() -> None:
	"""Put the persona on the account if nobody has written one, and move an
	unedited one on to the current default.

	A Single that already exists does not pick up a field's default, so a
	migrate that adds the field leaves it empty — and an empty persona is every
	action losing the rules it stopped carrying. The text is read from the
	field's own default rather than repeated here, so there is one copy of it.
	"""
	if not site.is_admin():
		return
	settings = frappe.get_doc("One Admin Settings")
	now = frappe.get_meta("One Admin Settings").get_field("persona").default or ""
	held = (settings.persona or "").strip()
	if held and (held == now.strip() or held not in {one.strip() for one in SHIPPED}):
		return
	settings.persona = now
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.db.commit()


def _persona() -> str:
	return (frappe.get_cached_doc("One Admin Settings").persona or "").strip()


def _action(key: str):
	asked = frappe.db.exists("AI Action", key)
	if not asked:
		raise Refused(f"{key} is not an action this account knows")
	asked = frappe.get_cached_doc("AI Action", key)
	if not asked.enabled:
		raise Refused(f"{asked.label} is switched off")
	return asked


def _caps(asked) -> dict:
	caps = {"output_tokens": asked.max_output_tokens or 0}
	if asked.max_input_tokens:
		caps["input_tokens"] = asked.max_input_tokens
	return caps
