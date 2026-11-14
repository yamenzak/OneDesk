"""The setup guide in the signup wizard (one/setup_center_agent.py): a
guest's question about the screen they are on, answered on OneAdmin before
any workspace exists. The model is asked through OneAdmin's own account, so
its credits are the house's (house.py), never a tenant's; each question is
limited per network address and per signup. The conversation lives in the
page: nothing is kept here but the counts that limit it. What it suggests
comes back to be taken on screen; it never saves, pays or makes a workspace
(Start.vue, start/Ask.vue)."""

import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from onedesk.one_admin import signup, site, wizard_answers

GUIDE = "setup_center"
JOB = "setup_guide"

AN_HOUR = 60 * 60
A_DAY = 24 * AN_HOUR
ASKS_AN_HOUR = 20
"""Questions from one network address in an hour."""
ASKS_A_DAY = 60
"""Questions from one network address in a day."""
ASKS_A_SIGNUP = 40
"""Questions on one signup in a day, from wherever it is answered."""
ROUNDS = 4
"""Rounds of tools a question may take: a guest's question is short."""
MOST_SAID = 600
MOST_TURNS = 10
MOST_ANSWERS = 1500
TOLD = ("field", "apps", "plan", "region", "language", "time_zone")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=ASKS_AN_HOUR, seconds=AN_HOUR, endpoint="onedesk.one_admin.wizard_ask.ask:hour")
@rate_limit(limit=ASKS_A_DAY, seconds=A_DAY, endpoint="onedesk.one_admin.wizard_ask.ask:day")
def ask(
	question: str,
	step: str | None = None,
	said: str | list | None = None,
	answers: str | dict | None = None,
	request: str | None = None,
	key: str | None = None,
) -> dict:
	"""The setup guide's answer to a question asked on a step of the
	wizard, with what it suggests for the person to take on screen."""
	from onedesk.one import setup_center_agent
	from onedesk.one_admin import faults
	from onedesk.one_ai.agents import talk

	site.require_admin()
	question = (question or "").strip()[:MOST_SAID]
	if not question:
		frappe.throw(_("Type a question first."))
	_counted(request, key)
	turns = told(question, step, _list(said), _dict(answers), setup_center_agent.who(guest=True))
	try:
		out = talk.ask(GUIDE, JOB, question, turns, reference=f"setup:{request or 'guest'}", tools=setup_center_agent.tools(guest=True), most=ROUNDS)
	except faults.Again:
		frappe.throw(_("The setup guide could not be reached. Try again in a moment."))
	except (faults.Refused, frappe.PermissionError):
		frappe.clear_messages()
		frappe.throw(_("The setup guide isn't available right now."))
	return {"answer": last_words(out), "suggestions": suggestions(out)}


def _counted(request: str | None, key: str | None) -> None:
	"""A question on a signup counts against it; a signup the key does not
	open is refused, so nobody spends another's count."""
	if not request:
		return
	asked = signup.owned(request, key)
	if not asked:
		frappe.throw(_("This signup can no longer be changed. Start again."), frappe.PermissionError)
	held = frappe.cache.make_key(f"one_setup_guide:{asked.name}")
	frappe.cache.set(held, 0, ex=A_DAY, nx=True)
	if frappe.cache.incrby(held, 1) > ASKS_A_SIGNUP:
		frappe.throw(_("That is as many questions as one signup may ask today."), frappe.RateLimitExceededError)


def told(question: str, step: str | None, said: list, answers: dict, who: str) -> list[dict]:
	"""The turns the guide is asked: who it is, the question the person is
	on and the answers given so far, the conversation on this page, then
	the question. Only words travel: a turn of the page's that claims to be
	a tool's answer is read as words. Pure."""
	on = wizard_answers.LABELS.get(_kind(step))
	where = f"The person is on the question {on} ({_kind(step)})." if on else "The person is starting the signup."
	given = {name: answers[name] for name in TOLD if answers.get(name) not in (None, "", [], {})}
	if given:
		where += " Their answers so far: " + json.dumps(given, default=str)[:MOST_ANSWERS]
	turns = [{"role": "user", "text": f"{who} {where}", "calls": [], "context": True}]
	for one in said[-MOST_TURNS:]:
		if isinstance(one, dict) and str(one.get("text") or "").strip():
			turns.append({"role": "model" if one.get("role") == "guide" else "user", "text": str(one["text"])[:MOST_SAID], "calls": []})
	turns.append({"role": "user", "text": question, "calls": []})
	return turns


def _kind(step: str | None) -> str:
	try:
		return wizard_answers.kind(step or "")
	except wizard_answers.Refused:
		return ""


def last_words(out: dict) -> str:
	"""What the guide said last. Pure."""
	said = [one for one in out.get("turns") or [] if one.get("role") == "model"]
	return (said[-1].get("text") or "").strip() if said else ""


def suggestions(out: dict) -> list[dict]:
	"""What suggest_answer offered on this question, the last for each
	setup question. Pure."""
	found = {}
	for one in out.get("turns") or []:
		said = one.get("result") if one.get("role") == "tool" and one.get("tool") == "suggest_answer" else None
		if isinstance(said, dict) and isinstance(said.get("suggestion"), dict):
			found[said["suggestion"]["question"]] = said["suggestion"]
	return list(found.values())


def _list(said) -> list:
	held = frappe.parse_json(said) if isinstance(said, str) else said
	return held if isinstance(held, list) else []


def _dict(said) -> dict:
	held = frappe.parse_json(said) if isinstance(said, str) else said
	return held if isinstance(held, dict) else {}
