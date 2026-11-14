"""An agent answering a person (docs/ARC-AI.md, OneChat): Una, or an app's
agent, with its own tools and no others, a round at a time through the
account (run.turn), reading as the person who asked and writing through
the agents' door at its levels. It runs here, beside the tools and the
person's session: the account holds the model and the Worker holds none.
one_ai/AGENTS.md, How an agent answers."""

import hashlib
import json
import re
from typing import Annotated

import frappe

from onedesk.one.registry import agents
from onedesk.one_ai import run

ROUNDS = 8

SHARED = (
	"list_records",
	"read_record",
	"count_records",
	"describe_type",
	"find_records",
	"find_by_meaning",
	"search_everywhere",
	"about_field",
	"what_links_here",
	"what_can_happen",
	"run_report",
	"about_record",
	"recall",
	"search_my_chats",
	"how_to",
	"remember",
)
"""The reads every agent has: the workspace's records as the person may
read them, its Help, and the person's own memory and conversations."""

FOR_THE_PERSON = ("create_record", "create_records", "edit_record", "move_record")
"""The shared suggestions Una makes as cards for the person asking, since
she has no user to act as; an app agent makes and changes records through
its door (`create_record`, `edit_record` below) and moves them by card."""

LAST = (
	"This is the last step. Do not call another tool: answer the person now with what you have, "
	"and say plainly what is not done."
)

NUDGE = "Now answer the question in one or two sentences from what the tools returned."

ANSWER = "Answer the person: do what they asked with a tool, or say why it cannot be done."

CALL_IT = "Now call {0} with what you just wrote. Do not answer in the chat."

MEND_IT = (
	"The call to {0} did not hold. Mend what its answer says and call {0} again. Do not answer in the chat, "
	"and do not tell them about the error."
)

GAVE_UP = (
	"The call to {0} still did not go through, so nothing was made. Say so in one sentence, without the "
	"error, and offer something simpler they could ask for."
)

KEEP_IT = (
	"The person just said: \"{0}\". Call remember now with the lasting fact in those words — "
	"not anything already remembered — then answer in one sentence."
)

REMEMBER = re.compile(
	r"\b(remember|keep in mind|don'?t forget|do not forget|make a note|merk|vergiss nicht)\b"
	r"|(?:^|[.!?]\s+)note that\b|تذك|احفظ|لا تنس",
	re.IGNORECASE,
)


def tools_of(app: str | None) -> tuple[tuple, tuple]:
	"""An agent's own tools, as (reads, suggestions): the shared reads, then
	what its app declares; for Una (None) what the workspace and every app
	with no agent declare, and `ask_agent`; for a centre's agent, which
	holds no role, only what its own file offers (its `tools`)."""
	from onedesk.one_ai import tools as surface
	from onedesk.one_ai.ai_web import offered

	if agents.is_centred(app):
		from onedesk.one_ai.agents import levels

		return levels.home(app).tools(guest=False)

	own = surface.READS + surface.KEEPS + surface.SUGGESTS
	shared = tuple(fn for fn in own if fn.__name__ in SHARED)
	reads = tuple(fn for fn in _hooked("one_ai_reads", app) if offered(fn))
	suggests = _hooked("one_ai_suggests", app)
	if app:
		return shared + reads, (create_record, edit_record, surface.move_record) + suggests
	return shared + reads + (ask_agent,), tuple(fn for fn in own if fn.__name__ in FOR_THE_PERSON) + suggests


def _hooked(hook: str, app: str | None) -> tuple:
	"""The tools a hook lists that are this agent's: an app's own, or for
	Una those of an app with no agent, and the console's only on One's own."""
	from onedesk.one_admin import site

	out = []
	for path in frappe.get_hooks(hook) or []:
		folder = path.split(".")[1]
		if (folder == app) if app else not agents.get(folder) and (folder != "one_admin" or site.is_admin()):
			out.append(frappe.get_attr(path))
	return tuple(out)


def who(app: str | None) -> str:
	"""Who is answering, as the model is told it first."""
	from onedesk.one import registry
	from onedesk.one_ai.agents import users

	if agents.is_centred(app):
		from onedesk.one_ai.agents import levels

		return levels.home(app).who(guest=False)
	if not app:
		return (
			"You are Una, who people in this workspace talk to first. You answer from its records and do what "
			"no department's agent does; a department's work is its agent's, so hand it over with ask_agent "
			"and tell the person what it said."
		)
	one = registry.get(app)
	return (
		f"You are {users.full_name(agents.get(app))}, the agent of {one.name}: {one.line}. You work in "
		f"{one.name} alone. For anything outside it, say that Una or that app's agent does it."
	)


def ask(
	app: str | None,
	action: str,
	text: str,
	turns: list[dict],
	reference: str | None = None,
	heard=None,
	expects: str | None = None,
	tools: tuple[tuple, tuple] | None = None,
	most: int = ROUNDS,
) -> dict:
	"""The agent's answer to the last of `turns`, looking things up with its
	tools where the model asks; `tools` gives a job's own instead, and
	`most` fewer rounds where a guest asks. `heard`
	is told each step: a round starting, a tool it ran. Refused while the
	agent is stopped or over its month (workspace.py)."""
	from onedesk.one_ai import schema
	from onedesk.one_ai import tools as surface
	from onedesk.one_ai.agents import workspace

	if app:
		workspace.refuse(app)
	reads, suggests = tools if tools is not None else tools_of(app)
	known = {fn.__name__: fn for fn in reads + suggests}
	offered = [schema.of(fn) for fn in known.values()]
	for one in offered:
		if one["name"] == "ask_agent":
			one["description"] += "\n" + catalogue()
	tell = heard or (lambda step: None)
	turns, spent, cards, asked, called = list(turns), 0.0, [], {}, set()
	nudged = pressed = handed = reminded = mended = gave_up = False
	mend = None
	was = frappe.flags.one_agent
	frappe.flags.one_agent = app
	try:
		for rounds in range(most + 1):
			tell({"thinking": rounds})
			last = rounds == most or _spoken(turns) >= most - 1
			if last:
				turns = [*turns, _context(LAST)]
			out = run.turn(action, text, turns, offered, reference=reference, agent=app)
			spent += float(out.get("credits") or 0)
			more = not last
			wanted = {getattr(known.get(want.get("tool")), "action", None) for want in out.get("wants") or []} - {None, action}
			if wanted and not handed and more:
				handed, action = True, sorted(wanted)[0]
				tell({"handed": action})
				continue
			if out.get("done") and mend and not gave_up and more:
				turns = [*_unsaid(out["turns"]), _context((GAVE_UP if mended else MEND_IT).format(mend))]
				gave_up, mended = mended, True
				continue
			if out.get("done") and "remember" in known and REMEMBER.search(text or "") and "remember" not in called and not reminded and more:
				reminded = True
				turns = [*out["turns"], _context(KEEP_IT.format(text))]
				continue
			if out.get("done") and expects and expects not in called and not pressed and not _asks(out) and more:
				pressed = True
				turns = [*out["turns"], _context(CALL_IT.format(expects))]
				continue
			if out.get("done") and _silent(out, cards) and not nudged and more:
				nudged = True
				turns = [*out["turns"], _context(NUDGE if _used(out) else ANSWER)]
				continue
			if out.get("done") or last:
				return {**out, "credits": round(spent, 6), "rounds": rounds + 1, "proposals": cards, "agent": app}
			turns = out["turns"]
			for want in out.get("wants") or []:
				called.add(want.get("tool"))
				key = json.dumps([want.get("tool"), want.get("args") or {}], sort_keys=True, default=str)
				if key in asked:
					answer = {"ran": asked[key].get("ran"), "error": "This exact call was already made and answered above. Answer with what you have, or try something different."}
				else:
					answer = asked[key] = _tried(known, reads, want, app)
				made = _cards(answer)
				said = answer.get("answer")
				if isinstance(said, dict) and said.get("mend"):
					mend = said["mend"]
				elif want.get("tool") == mend and not answer.get("error"):
					mend = None
				tell({"tool": want.get("tool"), "args": surface.shown_args(want.get("tool"), want.get("args")), "ran": bool(answer.get("ran"))})
				cards += made
				turns.append(
					{
						"role": "tool",
						"id": want.get("id"),
						"tool": want.get("tool"),
						"result": {"error": answer["error"]} if answer.get("error") else answer.get("answer"),
						"ran": bool(answer.get("ran")),
						"card": made[0] if made else None,
						**({"cards": made} if len(made) > 1 else {}),
					}
				)
			frappe.db.commit()
	finally:
		frappe.flags.one_agent = was


def _context(text: str) -> dict:
	return {"role": "user", "text": text, "calls": [], "context": True}


def _unsaid(turns: list[dict]) -> list[dict]:
	"""The turns with the model's last words taken back: what it said about
	a call it is now asked to mend is not what the person should read."""
	turns = list(turns)
	if turns and turns[-1].get("role") == "model":
		turns[-1] = {**turns[-1], "text": ""}
	return turns


def _tried(known: dict, reads: tuple, want: dict, app: str | None) -> dict:
	"""Run one tool the model asked for, and answer either way: a refusal is
	an answer the model can say, where a traceback would end the run."""
	from onedesk.one_ai import heal
	from onedesk.one_ai import tools as surface

	tool, args = want.get("tool"), want.get("args") or {}
	if not isinstance(args, dict):
		return {"tool": tool, "ran": False, "error": "The arguments have to be an object of name to value."}
	fn = known.get(tool)
	if not fn:
		return {"tool": tool, "ran": False, "error": heal.unknown(tool, list(known))}
	refused = _not_its(app, tool, args)
	if refused:
		return {"tool": tool, "ran": False, "error": refused}
	try:
		return {"tool": tool, "ran": fn in reads, "answer": surface._plain(fn(**args))}
	except Exception as raised:
		frappe.clear_last_message()
		frappe.local.message_log = []
		return {"tool": tool, "ran": False, "error": heal.said(raised, tool, args, fn)}


def _not_its(app: str | None, tool: str | None, args: dict) -> str | None:
	"""Why a shared read is not this agent's to make: a record type its own
	roles may not read, though the person may (docs/ARC-AI.md, both may)."""
	agent = agents.get(app) if app else None
	doctype = args.get("doctype") if tool in SHARED else None
	if not agent or not isinstance(doctype, str) or not frappe.db.exists("DocType", doctype):
		return None
	if frappe.has_permission(doctype, "read", user=agent.email):
		return None
	return f"{doctype} is not this agent's to read. Say that Una or the agent of the app it belongs to answers it."


def _cards(answer: dict) -> list[str]:
	"""The AI Proposals a suggestion just made: one, or several from
	create_records or an agent Una asked. Read off the answer's shape, so a
	new suggestion turns up here unnamed."""
	said = (answer or {}).get("answer")
	if not isinstance(said, dict):
		return []
	if said.get("proposal"):
		return [said["proposal"]]
	return [one["proposal"] for one in said.get("cards") or [] if isinstance(one, dict) and one.get("proposal")]


def _spoken(turns: list[dict]) -> int:
	"""The model's turns since the person last said something, counted as the
	account counts them."""
	asked = max((at for at, one in enumerate(turns) if one.get("role") == "user" and not one.get("context")), default=-1)
	return sum(1 for one in turns[asked + 1 :] if one.get("role") == "model")


def _last_words(out: dict) -> str:
	said = [one for one in out.get("turns") or [] if one.get("role") == "model"]
	return (said[-1].get("text") or "").strip() if said else ""


def _asks(out: dict) -> bool:
	"""The model's last words end by asking the person something."""
	text = _last_words(out)
	return bool(text) and text.rstrip(" *_)\"'").endswith("?")


def _silent(out: dict, cards: list) -> bool:
	"""A finished run that leaves the reader nothing: no words, no card."""
	return not cards and not _last_words(out)


def _used(out: dict) -> bool:
	return any(one.get("role") == "tool" for one in out.get("turns") or [])


def catalogue() -> str:
	"""The agents Una may hand work to: those the person may reach."""
	from onedesk.one import registry
	from onedesk.one_ai.agents import users
	from onedesk.one_chat import agents as members

	return "\n".join(
		f"{one.app}: {users.full_name(one)}, {registry.get(one.app).line}" for one in agents.listed() if members.reaches(one.app)
	)


def ask_agent(
	agent: Annotated[str, "The agent's id, from the list in this tool's description."],
	question: Annotated[str, "What it should answer or do, whole: it does not see this conversation."],
) -> dict:
	"""Hand a department's work to its agent and take back its answer, to
	tell the person. What it suggests waits as cards for the person. The
	agents:"""
	from onedesk.one_ai import here
	from onedesk.one_chat import agents as members

	if not agents.get(agent) or not members.reaches(agent):
		frappe.throw(f"There is no agent {agent!r} this person may reach. Pick one from the list.")
	out = ask(agent, "chat", question, here.asked(question, None, who=who(agent)))
	return {
		"agent": agent,
		"answer": _last_words(out),
		"cards": [{"proposal": one} for one in out.get("proposals") or []],
	}


def create_record(
	doctype: Annotated[str, "The type of record to create."],
	values: Annotated[dict, "Field name to value."],
	why: Annotated[str, "One sentence on what this is for."] | None = None,
) -> dict:
	"""Make a record, as far as your level for it goes: made, made as a
	draft, or a card for the person who asked to approve. Say which."""
	from onedesk.one_ai.reading import act

	return _through("create_record", act.Action("Create", doctype, values=values or {}, why=why or ""))


def edit_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	changes: Annotated[dict, "Field name to new value. Only the fields that change."],
	why: Annotated[str, "One sentence on what this is for."] | None = None,
) -> dict:
	"""Change a record, as far as your level for it goes: changed, or a
	card for the person who asked to approve. Say which."""
	from onedesk.one_ai.reading import act

	return _through("edit_record", act.Action("Update", doctype, name, values=changes or {}, why=why or ""))


def _through(name: str, action) -> dict:
	"""One write of the answering agent through its door, as the person
	who asked, keyed by the conversation so asking twice makes it once."""
	from onedesk.one_ai.agents import door

	app = frappe.flags.one_agent
	said = json.dumps([action.kind, action.doctype, action.name, action.values], sort_keys=True, default=str)
	action.key = f"talk|{frappe.flags.one_ai_chat or ''}|{hashlib.md5(said.encode()).hexdigest()[:12]}"
	made = door.act_for(app, name, action, asked_by=frappe.session.user)
	row = frappe.db.get_value("Reading Action", made, ["level", "target_name", "why"], as_dict=True) if made else None
	if not row:
		return {"state": "Not done", "why": "It already holds that."}
	return {
		"state": {"Done": "Done", "Proposed": "Waiting for the person to approve its card", "Refused": "Refused"}.get(row.level, row.level),
		"record": row.target_name,
		**({"why": row.why} if row.why else {}),
	}
