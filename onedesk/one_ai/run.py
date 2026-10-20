"""Asking the account to run an action, from the workspace that wants it.

Which model the workspace picked and what it asked to have added travel with the
call. The instruction is the account's, and every decision is admin's.
"""

import json
import re

import frappe

from onedesk.one import account, roles


ROUNDS = 8


def ask(
	action: str,
	text: str,
	reference: str | None = None,
	turns: list[dict] | None = None,
	heard=None,
	expects: str | None = None,
	chose: dict | None = None,
	groups: list[str] | None = None,
	pinned: str | None = None,
	only: list[str] | None = None,
	nudges: bool = True,
) -> dict:
	"""Run one action, looking things up for the model where it asks.

	`pinned` is the model the person picked for this conversation, and it wins.
	`heard` is told each thing as it happens: a round starting, a tool it ran.
	`only` offers these tools and no others; `nudges` off leaves out what a
	conversation presses a model for, for a run nobody is reading.
	"""
	from onedesk.one import apps
	from onedesk.one_ai import tools as surface

	apps.refuse_ai()
	chose = chose if chose is not None else mine(action)
	if pinned:
		chose = {**chose, "model": pinned}
	given = list(groups) if groups is not None else None
	offered = surface.declared_only(only) if only is not None else surface.declared(given)
	turns = list(turns) if turns else None
	spent, rounds, cards = 0.0, 0, []
	asked: dict[str, dict] = {}
	nudged = reminded = pressed = mended = handed = doubted = looked = False
	tooled = _tooled(action)
	mend = None
	called: set[str] = set()

	tell = heard or (lambda step: None)

	while True:
		tell({"thinking": rounds})
		last = turns is not None and _spoken(turns) >= ROUNDS - 1
		if last:
			turns = [*turns, {"role": "user", "text": LAST, "calls": [], "context": True}]
		out = account.ask(
			"onedesk.one_admin.proxy.ai_run",
			action=action,
			text=text,
			model=chose.get("model") or None,
			extra=chose.get("extra") or None,
			reference=reference,
			turns=turns,
			tools=offered,
		)
		spent += float(out.get("credits") or 0)
		more = rounds < ROUNDS and not last
		wanted = {surface.action_of(want.get("tool")) for want in out.get("wants") or []} - {None, action}
		if wanted and not handed and rounds < ROUNDS:
			handed = True
			action = sorted(wanted)[0]
			chose = {**mine(action), **({"model": pinned} if pinned else {})}
			tooled = _tooled(action)
			tell({"handed": action})
			rounds += 1
			continue
		if nudges and out.get("done") and not reminded and _unkept(text, called) and more:
			reminded = True
			turns = [*out["turns"], {"role": "user", "text": KEEP_IT.format(text), "calls": [], "context": True}]
			rounds += 1
			continue
		if (
			out.get("done")
			and expects
			and expects not in called
			and not pressed
			and not _asks(out)
			and more
		):
			pressed = True
			turns = [*out["turns"], {"role": "user", "text": CALL_IT.format(expects), "calls": [], "context": True}]
			rounds += 1
			continue
		if out.get("done") and mend and not mended and more:
			mended = True
			turns = [*_unsaid(out["turns"]), {"role": "user", "text": MEND_IT.format(mend), "calls": [], "context": True}]
			rounds += 1
			continue
		if out.get("done") and mend and mended and not nudged and more:
			nudged = True
			turns = [*_unsaid(out["turns"]), {"role": "user", "text": GAVE_UP.format(mend), "calls": [], "context": True}]
			rounds += 1
			continue
		if nudges and out.get("done") and tooled and not cards and not doubted and more and _claimed(out):
			doubted = True
			said = OFFERED if _offered(out) else CLAIMED
			turns = [*out["turns"], {"role": "user", "text": said, "calls": [], "context": True}]
			rounds += 1
			continue
		if (
			nudges
			and out.get("done")
			and tooled
			and not looked
			and not cards
			and "more_tools" not in called
			and more
			and _cannot(out)
			and not _asks(out)
		):
			looked = True
			turns = [*out["turns"], {"role": "user", "text": SEEK, "calls": [], "context": True}]
			rounds += 1
			continue
		if nudges and out.get("done") and tooled and not called and not doubted and more and _figured(out) and not _asks(out):
			doubted = True
			turns = [*out["turns"], {"role": "user", "text": LOOK, "calls": [], "context": True}]
			rounds += 1
			continue
		if nudges and out.get("done") and _silent(out, cards) and not nudged and more:
			nudged = True
			said = NUDGE if _used(out) else ANSWER
			turns = [*out["turns"], {"role": "user", "text": said, "calls": [], "context": True}]
			rounds += 1
			continue
		if out.get("done") or rounds >= ROUNDS or last:
			return {
				**out,
				"credits": round(spent, 6),
				"rounds": rounds + 1,
				"proposals": cards,
				"groups": given,
			}

		turns = out["turns"]
		for want in out.get("wants") or []:
			called.add(want.get("tool"))
			key = json.dumps([want.get("tool"), want.get("args") or {}], sort_keys=True, default=str)
			if key in asked:
				answer = {
					"ran": asked[key].get("ran"),
					"error": "This exact call was already made and answered above. Do not repeat it: "
					"answer the person with what you have, or try something different.",
				}
			else:
				answer = asked[key] = _tried(want)
			made = _cards(answer)
			said = answer.get("answer")
			if given is not None and want.get("tool") == "more_tools" and isinstance(said, dict):
				given += [one for one in said.get("given") or [] if one not in given]
				offered = surface.declared(given)
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
					"result": _answer(answer),
					"ran": bool(answer.get("ran")),
					"card": made[0] if made else None,
					**({"cards": made} if len(made) > 1 else {}),
				}
			)
		frappe.db.commit()
		rounds += 1


def _answer(answer: dict):
	"""What the tool said, in the shape a model should read it in.

	A refusal is `{"error": ...}` — one key, so a model that has been told it
	may not see something can say exactly that. Everything else is the tool's
	own answer: rows for a read, the card for a write.
	"""
	if answer.get("error"):
		return {"error": answer["error"]}
	return answer.get("answer")


def _cards(answer: dict) -> list[str]:
	"""The proposals a write tool just parked, if that is what this was: one,
	or several from create_records.

	A read tool answers with rows, which is a list, so this asks the shape
	rather than the tool's name — a tool added later that parks a proposal
	turns up here without this function being edited.
	"""
	said = (answer or {}).get("answer")
	if not isinstance(said, dict):
		return []
	if said.get("proposal"):
		return [said["proposal"]]
	return [one["proposal"] for one in said.get("cards") or [] if isinstance(one, dict) and one.get("proposal")]


NUDGE = "Now answer the question in one or two sentences from what the tools returned."

ANSWER = "Answer the person: do what they asked with a tool, or say why it cannot be done."

LAST = (
	"This is the last step. Do not call another tool: answer the person now with what you have, "
	"and say plainly what is not done."
)


def _spoken(turns: list[dict]) -> int:
	"""The model's turns since the person last said something, counted as the
	account counts them."""
	asked = max(
		(at for at, one in enumerate(turns) if one.get("role") == "user" and not one.get("context")),
		default=-1,
	)
	return sum(1 for one in turns[asked + 1 :] if one.get("role") == "model")


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


def _unsaid(turns: list[dict]) -> list[dict]:
	"""The turns with the model's last words taken back: what it said about a
	call it is now asked to mend is not what the person should read."""
	turns = list(turns)
	if turns and turns[-1].get("role") == "model":
		turns[-1] = {**turns[-1], "text": ""}
	return turns


def _unkept(text: str | None, called: set[str]) -> bool:
	"""Asked to remember, and nothing was kept."""
	return bool(text and REMEMBER.search(text)) and "remember" not in called


CLAIMED = (
	"You described something to make, but you did not call the tool that makes it, so nothing has been "
	"suggested. If the person asked for it, call that tool now. Otherwise say plainly that nothing was made."
)

OFFERED = (
	"You offered to make it instead of making it. The person asked for it, so make it now with the tool "
	"that makes it: nothing runs until they approve the card. Only if it cannot be made, say why."
)

SEEK = (
	"You said you cannot, without looking at every tool there is. Call more_tools to see every group, "
	"take the one that fits and do what was asked with it. Only if none fits, say plainly what cannot be done."
)

_CANNOT = re.compile(
	r"\b(i (?:cannot|can't|can ?not|am unable|am not able)|i do(?:n't| not) have (?:a|the|any) tool"
	r"|there is no tool|no tool (?:to|for|that))\b|kann ich nicht|nicht möglich|لا أستطيع|لا يمكنني",
	re.IGNORECASE,
)


def _cannot(out: dict) -> bool:
	"""The model's answer says it cannot do what was asked."""
	return bool(_CANNOT.search(_last_words(out)))


LOOK = (
	"You answered with a figure without looking anything up. Look it up with a tool, "
	"then answer from what the tool returns."
)

_SUGGESTED = re.compile(
	r"\b(i(?:'ve| have| can| will|'ll)? (?:suggest(?:ed)?|propose[sd]?|drafted|added|created|made|written|wrote)"
	r"|approv\w* (?:the|this) card|the card)\b|```|vorgeschlagen|\bkarte\b|اقترحت|البطاقة",
	re.I,
)
_DIGIT = re.compile(r"[0-9\u0660-\u0669\u06f0-\u06f9]")


def _tooled(action: str) -> bool:
	return bool(frappe.db.get_value("AI Action", action, "may_use_tools"))


def _last_words(out: dict) -> str:
	said = [one for one in out.get("turns") or [] if one.get("role") == "model"]
	return (said[-1].get("text") or "") if said else ""


def _claimed(out: dict) -> bool:
	"""The model's answer says a card was made, or offers to make one."""
	return bool(_SUGGESTED.search(_last_words(out))) or _offered(out)


_OFFERS = re.compile(
	r"\bi (?:can|could)(?:,? however,?)? (?:write|create|make|set up|build|add|suggest|propose) (?:an?|the) \w",
	re.I,
)


def _offered(out: dict) -> bool:
	"""The model's answer offers to make something rather than making it."""
	return bool(_OFFERS.search(_last_words(out)))


def _figured(out: dict) -> bool:
	"""The model's answer carries a figure."""
	return bool(_DIGIT.search(_last_words(out)))


def _asks(out: dict) -> bool:
	"""The model's last words end by asking the person something: "Which
	field do you mean?" A question is the end of a sentence, so the last one
	is enough."""
	said = [one for one in out.get("turns") or [] if one.get("role") == "model"]
	text = (said[-1].get("text") or "").strip() if said else ""
	return bool(text) and text.rstrip(" *_)\"'").endswith("?")


def _silent(out: dict, cards: list) -> bool:
	"""A finished run that leaves the reader nothing: no words, no card."""
	if cards:
		return False
	said = [one for one in out.get("turns") or [] if one.get("role") == "model"]
	return not (said and (said[-1].get("text") or "").strip())


def _used(out: dict) -> bool:
	"""Whether the run called a tool."""
	return any(one.get("role") == "tool" for one in out.get("turns") or [])


def _tried(want: dict) -> dict:
	"""Run one tool the model asked for, and answer either way.

	A refusal is an answer. Raising here would end the run with a traceback
	where the model was one sentence away from saying "I cannot see that".
	"""
	from onedesk.one_ai import heal
	from onedesk.one_ai import tools as surface

	tool, args = want.get("tool"), want.get("args") or {}
	if not isinstance(args, dict):
		return {"tool": tool, "ran": False, "error": "The arguments have to be an object of name to value."}
	fn = surface.named(tool)
	if not fn:
		return {"tool": tool, "ran": False, "error": heal.unknown(tool, surface.names())}
	try:
		return surface.run(tool, args)
	except Exception as raised:
		frappe.clear_last_message()
		frappe.local.message_log = []
		return {"tool": tool, "ran": False, "error": heal.said(raised, tool, args, fn)}


def once(action: str, text: str, files: list[dict] | None = None, reference: str | None = None) -> str:
	"""One call, no tools and no loop: what a background job asks.

	The chat's loop is for a model that looks things up as the person asking.
	A job that has already gathered everything the model needs — a CV and the
	opening it was sent to — has nobody to look things up as, so it hands the
	lot over in one turn and takes the words back. `files` carry their bytes,
	base64'd, the shape `files.carried` makes.
	"""
	from onedesk.one import apps

	apps.refuse_ai()
	chose = mine(action)
	out = account.ask(
		"onedesk.one_admin.proxy.ai_run",
		action=action,
		text=text,
		model=chose.get("model") or None,
		extra=chose.get("extra") or None,
		reference=reference,
		turns=[{"role": "user", "text": text, "calls": [], "files": files or []}],
		tools=None,
	)
	return (out or {}).get("said") or ""


def mine(action: str) -> dict:
	"""What this workspace has chosen for an action, if anything."""
	held = frappe.db.get_value(
		"AI Action Setting", {"action": action}, ["model", "extra"], as_dict=True
	)
	return dict(held or {})


@frappe.whitelist()
def models(needs: str) -> list[dict]:
	"""The models this workspace may pick, asked of the account.

	Whitelisted so a settings screen can fill a picker. It says nothing about
	prices or credits — only which names may be chosen.
	"""
	roles.require()
	return account.ask("onedesk.one_admin.proxy.ai_models", needs=needs) or []


@frappe.whitelist()
def models_for(needs: str | list) -> dict:
	"""The models for several capabilities at once, for the Actions list."""
	roles.require()
	return account.ask("onedesk.one_admin.proxy.ai_models_for", needs=frappe.parse_json(needs) or []) or {}


@frappe.whitelist(methods=["POST"])
def set_action(
	action: str,
	model: str | None = None,
	extra: str | None = None,
	modified: str | None = None,
	people_choose: int | str | None = None,
) -> dict:
	"""What one action runs on and what is added to it, saved as the desk would
	save it: refused when somebody else changed it since it was opened."""
	roles.require()
	name = frappe.db.get_value("AI Action Setting", {"action": action}, "name")
	held = frappe.get_doc("AI Action Setting", name) if name else frappe.new_doc("AI Action Setting")
	if name and modified and str(held.modified) != str(modified):
		frappe.throw(
			frappe._("{0} changed this since you opened it. Close it and open it again.").format(
				frappe.utils.get_fullname(held.modified_by)
			),
			frappe.TimestampMismatchError,
		)
	was = {"model": held.model or "", "extra": held.extra or "", "people_choose": bool(held.people_choose)}
	held.action = action
	held.model = model or None
	held.extra = extra or ""
	if people_choose is not None:
		held.people_choose = frappe.utils.cint(people_choose)
	held.save() if name else held.insert()
	_told(action, was, {"model": held.model or "", "extra": held.extra or "", "people_choose": bool(held.people_choose)})
	return {"name": held.name, "modified": str(held.modified)}


@frappe.whitelist(methods=["POST"])
def reset_action(action: str) -> dict:
	"""Back to what One picked: the default model and nothing added."""
	roles.require()
	name = frappe.db.get_value("AI Action Setting", {"action": action}, "name")
	if not name:
		return {}
	held = frappe.get_doc("AI Action Setting", name)
	was = {"model": held.model or "", "extra": held.extra or "", "people_choose": bool(held.people_choose)}
	held.delete()
	_told(action, was, {"model": "", "extra": ""})
	return {}


def _told(action: str, was: dict, now: dict) -> None:
	"""Every other administrator hears what changed, and an open Actions page
	redraws."""
	from onedesk.one.account import _administrators
	from onedesk.one_ai import tell

	people = _administrators()
	for user in people:
		frappe.publish_realtime("one_oneai", {"action": action}, user=user, after_commit=True)
	changed = []
	if was["model"] != now["model"]:
		named = frappe.db.get_value("AI Action Setting", {"action": action}, "model") and now["model"]
		changed.append(
			frappe._("the model to {0}").format(_model_name(named)) if named else frappe._("the model back to the default")
		)
	if was["extra"] != now["extra"]:
		changed.append(frappe._("the added instructions") if now["extra"] else frappe._("the added instructions, to none"))
	if was.get("people_choose", False) != now.get("people_choose", False):
		changed.append(
			frappe._("who picks the model, to everybody")
			if now.get("people_choose")
			else frappe._("who picks the model, to administrators only")
		)
	others = [one for one in people if one != frappe.session.user]
	if not changed or not others:
		return
	label = frappe.db.get_value("AI Action", action, "label") or action
	tell.action_changed(others, label, changed)


def _model_name(name: str) -> str:
	"""A model as a person would name it: the catalogue's label made readable."""
	from onedesk.one_admin import makers

	return makers.pretty(name.split(":", 1)[-1].rsplit("/", 1)[-1])


@frappe.whitelist(methods=["POST"])
def try_it(action: str, text: str, model: str | None = None, extra: str | None = None) -> dict:
	"""Run an action from the settings screen, with the model and the added
	instructions as they stand in the dialog, saved or not.

	Charged like any other call, because a preview that is not charged is a
	preview of something else; the dialog says so before it runs.
	"""
	roles.require()
	return ask(action, text, reference=frappe.session.user, chose={"model": model or None, "extra": extra or None})


@frappe.whitelist()
def tools() -> list[dict]:
	"""Every tool, as a provider's function declaration.

	Whitelisted so the tenant can hand the list to the account with a call. The
	account never calls a tool: the tools run here, as the person asking, which
	is the only place their permissions mean anything.
	"""
	from onedesk.one_ai import tools as surface

	return surface.declared()


@frappe.whitelist()
def use(tool: str, args: dict | None = None) -> dict:
	"""Call one tool as whoever is signed in.

	Not `allow_guest`, not as Administrator, and with no `ignore_permissions`
	anywhere beneath it — see `one_ai/tools.py`.
	"""
	from onedesk.one_ai import tools as surface

	if isinstance(args, str):
		args = frappe.parse_json(args)
	return surface.run(tool, args or {})


@frappe.whitelist()
def waiting() -> list[dict]:
	"""What a model has suggested and nobody has answered yet."""
	from onedesk.one_ai import proposals

	return proposals.mine()


@frappe.whitelist()
def apply(proposal: str) -> dict:
	"""Do what was suggested, as the person pressing the button."""
	from onedesk.one_ai import proposals

	return proposals.apply(proposal)


@frappe.whitelist(methods=["POST"])
def apply_all(proposals: list | str) -> list[dict]:
	"""Approve the cards one answer suggested, in the order it suggested them."""
	from onedesk.one_ai import proposals as suggested

	named = frappe.parse_json(proposals) if isinstance(proposals, str) else proposals
	return suggested.apply_all([str(one) for one in named or []][:50])


@frappe.whitelist()
def refuse(proposal: str) -> dict:
	from onedesk.one_ai import proposals

	return proposals.refuse(proposal)


@frappe.whitelist()
def took(proposal: str) -> dict:
	"""A suggested change applied into the open form, for the person to save."""
	from onedesk.one_ai import touch

	return touch.took(proposal)


@frappe.whitelist()
def landed(proposal: str, record: str) -> dict:
	"""A change taken into a new document, now that the document has a name."""
	from onedesk.one_ai import touch

	return touch.landed(proposal, record)
