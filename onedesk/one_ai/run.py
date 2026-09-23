"""Asking the account to run an action, from the workspace that wants it.

Two things travel with the call and neither is the instruction: which model this
workspace picked, and what it asked to have added. The instruction itself is the
account's, read from its own copy of the fixture, and there is nothing a
workspace can send that replaces it.

Everything here is one round trip and no decision. Whether the action exists,
whether the model may answer it, whether there are credits — all of that is
admin's, for the same reason a workspace cannot sign its own upload URL.
"""

import json
import re

import frappe

from onedesk.one import account, roles


#: As many rounds as the workspace will drive. The account counts them too and
#: refuses past its own limit — this one is only so a workspace with a bug stops
#: on its own side rather than being stopped.
ROUNDS = 5


def ask(
	action: str,
	text: str,
	reference: str | None = None,
	turns: list[dict] | None = None,
	heard=None,
	expects: str | None = None,
) -> dict:
	"""Run one action, looking things up for the model where it asks.

	`heard` is told each thing as it happens — a round starting, a tool it ran
	— so a panel watching a background run can say what it is doing rather
	than that it is busy.

	The loop is here rather than on the account, and that is the whole shape of
	this: the model is on the account and the records are here, the account
	never calls a workspace, and a tool means nothing unless it runs as whoever
	is signed in. So the workspace asks, is told what the model wants, looks it
	up with its own permissions, and asks again.

	A tool that refuses comes back as a result saying so rather than as an
	exception. A model told "you may not see that" can say so; a model told
	nothing at all writes something plausible instead.
	"""
	from onedesk.one_ai import tools as surface

	chose = mine(action)
	offered = surface.declared()
	# A conversation carried in from a panel arrives with the new turn already
	# on the end of it; a bare `text` is the first thing anybody said.
	turns = list(turns) if turns else None
	spent, rounds, cards = 0.0, 0, []
	asked: dict[str, dict] = {}
	nudged = reminded = pressed = False
	called: set[str] = set()

	tell = heard or (lambda step: None)

	while True:
		tell({"thinking": rounds})
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
		if out.get("done") and not reminded and _unkept(text, called) and rounds < ROUNDS:
			# "I will remember that" with no call behind it is a promise a
			# small model makes and does not keep. Asked for the call, it makes it.
			reminded = True
			turns = [*out["turns"], {"role": "user", "text": KEEP_IT.format(text), "calls": [], "context": True}]
			rounds += 1
			continue
		if out.get("done") and expects and expects not in called and not pressed and rounds < ROUNDS:
			# A suggestion that exists to make a card — "Draft my feedback" —
			# answered with the draft in the chat and no card. Asked for the
			# call it was for, with what it just wrote.
			pressed = True
			turns = [*out["turns"], {"role": "user", "text": CALL_IT.format(expects), "calls": [], "context": True}]
			rounds += 1
			continue
		if out.get("done") and _silent(out, cards) and not nudged and rounds < ROUNDS:
			# Gemini answers the round after a tool result with nothing, which
			# is "done" when a card said it and a blank panel when none did.
			# Asked once, in a turn the reader never sees, it says the answer.
			nudged = True
			turns = [*out["turns"], {"role": "user", "text": NUDGE, "calls": [], "context": True}]
			rounds += 1
			continue
		if out.get("done") or rounds >= ROUNDS:
			return {**out, "credits": round(spent, 6), "rounds": rounds + 1, "proposals": cards}

		turns = out["turns"]
		for want in out.get("wants") or []:
			called.add(want.get("tool"))
			key = json.dumps([want.get("tool"), want.get("args") or {}], sort_keys=True, default=str)
			if key in asked:
				# The same call again: a small model given an empty answer asks
				# the identical question until the round limit ends the run with
				# nothing said. Told so, it answers with what it has.
				answer = {
					"ran": asked[key].get("ran"),
					"error": "This exact call was already made and answered above. Do not repeat it: "
					"answer the person with what you have, or try something different.",
				}
			else:
				answer = asked[key] = _tried(want)
			card = _card(answer)
			tell({"tool": want.get("tool"), "args": want.get("args") or {}, "ran": bool(answer.get("ran"))})
			if card:
				cards.append(card)
			turns.append(
				{
					"role": "tool",
					"id": want.get("id"),
					"tool": want.get("tool"),
					# What the tool answered, and nothing else. The bookkeeping
					# sits beside it rather than inside it, because `result` is
					# the only part a provider is sent — and a model handed
					# `{"tool": ..., "ran": ..., "answer": [...]}` quotes the
					# wrapper back at the reader as if it were the answer.
					"result": _answer(answer),
					"ran": bool(answer.get("ran")),
					"card": card,
				}
			)
		# What this round parked is somebody's to answer, and a round that fails
		# after it should not take it away. Committed here rather than at the end
		# of the request, which on a run with five model calls in it is minutes
		# off — and a transaction held open across all of them is a transaction
		# holding locks across all of them.
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


def _card(answer: dict) -> str | None:
	"""The proposal a write tool just parked, if that is what this was.

	A read tool answers with rows, which is a list, so this asks the shape
	rather than the tool's name — a tool added later that parks a proposal
	turns up here without this function being edited.
	"""
	said = (answer or {}).get("answer")
	return said.get("proposal") if isinstance(said, dict) else None


#: Said to a model that looked things up and then said nothing.
NUDGE = "Now answer the question in one or two sentences from what the tools returned."


#: Said to a model that answered a suggestion without making its card.
CALL_IT = "Now call {0} with what you just wrote. Do not answer in the chat."


#: Said to a model that was asked to remember something and did not.
KEEP_IT = (
	"The person just said: \"{0}\". Call remember now with the lasting fact in those words — "
	"not anything already remembered — then answer in one sentence."
)

#: How a person asks to be remembered, in the languages a workspace reads.
REMEMBER = re.compile(
	r"\b(remember|keep in mind|don'?t forget|do not forget|make a note|note that|merk|vergiss nicht)\b|تذك|احفظ|لا تنس",
	re.IGNORECASE,
)


def _unkept(text: str | None, called: set[str]) -> bool:
	"""Asked to remember, and nothing was kept."""
	return bool(text and REMEMBER.search(text)) and "remember" not in called


def _silent(out: dict, cards: list) -> bool:
	"""A finished run that leaves the reader nothing: no words, no card."""
	if cards:
		return False
	said = [one for one in out.get("turns") or [] if one.get("role") == "model"]
	used = any(one.get("role") == "tool" for one in out.get("turns") or [])
	return used and not (said and (said[-1].get("text") or "").strip())


def _tried(want: dict) -> dict:
	"""Run one tool the model asked for, and answer either way.

	A refusal is an answer. Raising here would end the run with a traceback
	where the model was one sentence away from saying "I cannot see that".
	"""
	from onedesk.one_ai import tools as surface

	try:
		return surface.run(want.get("tool"), want.get("args") or {})
	except Exception as raised:
		frappe.clear_last_message()
		# Stripped, because frappe writes its refusals with markup in them and
		# this text is read by a model that may quote it back to a person.
		said = frappe.utils.strip_html(str(raised)).strip()
		return {"tool": want.get("tool"), "ran": False, "error": said[:500]}


def once(action: str, text: str, files: list[dict] | None = None, reference: str | None = None) -> str:
	"""One call, no tools and no loop: what a background job asks.

	The chat's loop is for a model that looks things up as the person asking.
	A job that has already gathered everything the model needs — a CV and the
	opening it was sent to — has nobody to look things up as, so it hands the
	lot over in one turn and takes the words back. `files` carry their bytes,
	base64'd, the shape `files.carried` makes.
	"""
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
def try_it(action: str, text: str) -> dict:
	"""Run an action from the settings screen, so a change can be looked at.

	Charged like any other call, because a preview that is not charged is a
	preview of something else.
	"""
	roles.require()
	return ask(action, text, reference=frappe.session.user)


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
