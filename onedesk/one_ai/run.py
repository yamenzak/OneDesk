"""Asking the account to run an action, from the workspace that wants it.

Two things travel with the call and neither is the instruction: which model this
workspace picked, and what it asked to have added. The instruction itself is the
account's, read from its own copy of the fixture, and there is nothing a
workspace can send that replaces it.

Everything here is one round trip and no decision. Whether the action exists,
whether the model may answer it, whether there are credits — all of that is
admin's, for the same reason a workspace cannot sign its own upload URL.
"""

import frappe

from onedesk.one import account


#: As many rounds as the workspace will drive. The account counts them too and
#: refuses past its own limit — this one is only so a workspace with a bug stops
#: on its own side rather than being stopped.
ROUNDS = 5


def ask(
	action: str,
	text: str,
	reference: str | None = None,
	turns: list[dict] | None = None,
) -> dict:
	"""Run one action, looking things up for the model where it asks.

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

	while True:
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
		if out.get("done") or rounds >= ROUNDS:
			return {**out, "credits": round(spent, 6), "rounds": rounds + 1, "proposals": cards}

		turns = out["turns"]
		for want in out.get("wants") or []:
			answer = _tried(want)
			card = _card(answer)
			if card:
				cards.append(card)
			turns.append(
				{"role": "tool", "id": want.get("id"), "tool": want.get("tool"), "result": answer}
			)
		# What this round parked is somebody's to answer, and a round that fails
		# after it should not take it away. Committed here rather than at the end
		# of the request, which on a run with five model calls in it is minutes
		# off — and a transaction held open across all of them is a transaction
		# holding locks across all of them.
		frappe.db.commit()
		rounds += 1


def _card(answer: dict) -> str | None:
	"""The proposal a write tool just parked, if that is what this was.

	A read tool answers with rows, which is a list, so this asks the shape
	rather than the tool's name — a tool added later that parks a proposal
	turns up here without this function being edited.
	"""
	said = (answer or {}).get("answer")
	return said.get("proposal") if isinstance(said, dict) else None


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
	frappe.only_for("System Manager")
	return account.ask("onedesk.one_admin.proxy.ai_models", needs=needs) or []


@frappe.whitelist()
def try_it(action: str, text: str) -> dict:
	"""Run an action from the settings screen, so a change can be looked at.

	Charged like any other call, because a preview that is not charged is a
	preview of something else.
	"""
	frappe.only_for("System Manager")
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
