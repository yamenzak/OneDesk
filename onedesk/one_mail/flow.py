"""A mail rule's steps (Mail Rule.steps), and what they do to one message.

A rule is steps run top to bottom on new Inbox mail: an If (conditions in
groups that nest, All or Any, with a branch for yes and one for no), an Ask
OneAI (a branch for each answer), or an action. Stop ends it and every rule
after it. All pure: rules.py gathers `facts` and does what `walk` answers.
"""

import re

from frappe import _

TEXT = ("from", "to", "subject", "text", "domain")
FLAGS = ("attachment", "starts", "outside", "holiday", "after_hours")
KINDS = ("Customer", "Supplier", "Lead", "Contact", "Employee")
OPS = ("contains", "not_contains", "is", "is_not", "starts_with", "ends_with")
ACTIONS = ("move", "read", "star", "junk", "reply", "forward", "assign", "notify", "link", "create", "stop")
CREATES = ("Lead", "Issue", "Task")
ONCE = ("conversation", "day", "week", "month")


def test(group: dict | None, facts: dict) -> bool:
	"""Whether a message meets a group of conditions. An empty group is met by
	every message, so a rule without conditions is for all mail."""
	items = (group or {}).get("items") or []
	if not items:
		return True
	results = (test(one, facts) if "items" in one else holds(one, facts) for one in items)
	return any(results) if (group or {}).get("any") else all(results)


def holds(condition: dict, facts: dict) -> bool:
	"""One condition against what is known of the message."""
	field = condition.get("field")
	if field in TEXT:
		return said(facts.get(field) or "", condition.get("op") or "contains", condition.get("value") or "")
	if field in FLAGS:
		return bool(facts.get(field)) == bool(condition.get("value", True))
	if field == "sender_is":
		kinds = set(facts.get("sender_is") or ())
		wanted = condition.get("value")
		return (wanted in kinds) != (condition.get("op") == "is_not")
	return False


def said(have: str, op: str, value: str) -> bool:
	"""A text condition, ignoring case; `value` may list several words split by
	commas, any of which will do."""
	have = have.lower()
	words = [one.strip().lower() for one in str(value).split(",") if one.strip()]
	if not words:
		return True
	if op == "contains":
		return any(one in have for one in words)
	if op == "not_contains":
		return not any(one in have for one in words)
	if op == "is":
		return have.strip() in words
	if op == "is_not":
		return have.strip() not in words
	if op == "starts_with":
		return any(have.startswith(one) for one in words)
	if op == "ends_with":
		return any(have.endswith(one) for one in words)
	return False


def walk(steps: list, facts: dict, answers: dict | None = None) -> tuple[list, bool]:
	"""The actions a message gets from a rule's steps, in order, and whether
	the rule said stop. `answers` are OneAI's, {step id: True/False for a
	question, or the label picked}; without them an Ask OneAI takes neither
	branch, which never happens since such a rule waits for OneAI (needs_ai)."""
	done = []
	for step in steps or []:
		kind = step.get("type")
		if kind == "if":
			branch = step.get("then") if test(step.get("test"), facts) else step.get("else")
			more, stopped = walk(branch, facts, answers)
			done += more
			if stopped:
				return done, True
		elif kind == "ask":
			branch = _answered(step, answers)
			more, stopped = walk(branch, facts, answers)
			done += more
			if stopped:
				return done, True
		elif kind == "stop":
			return done, True
		elif kind in ACTIONS:
			done.append(step)
	return done, False


def _answered(step: dict, answers: dict | None):
	"""The branch OneAI's answer to one Ask OneAI takes."""
	said = (answers or {}).get(step.get("id"))
	if step.get("ask") == "pick":
		for label in step.get("labels") or []:
			if said is not None and said == label.get("label"):
				return label.get("then")
		return step.get("else")
	return step.get("then") if said else step.get("else")


def asks(steps: list) -> list[dict]:
	"""Every Ask OneAI in a rule, nested ones too."""
	found = []
	for step in steps or []:
		if step.get("type") == "ask":
			found.append(step)
			for label in step.get("labels") or []:
				found += asks(label.get("then"))
		found += asks(step.get("then")) + asks(step.get("else"))
	return found


def needs_ai(steps: list) -> bool:
	"""Whether a rule waits for OneAI to have read the message."""
	return bool(asks(steps))


def topics(rule: str, steps: list) -> list[tuple[str, str]]:
	"""What OneAI is asked to read a message for, one topic each: a question
	(`rule#step`), or each label it can pick (`rule#step#n`)."""
	said = []
	for step in asks(steps):
		key = f"{rule}#{step.get('id')}"
		if step.get("ask") == "pick":
			said += [(f"{key}#{n}", one.get("about") or one.get("label")) for n, one in enumerate(step.get("labels") or [])]
		else:
			said.append((key, step.get("question") or ""))
	return [one for one in said if one[1]]


def answers_of(rule: str, steps: list, about: set) -> dict:
	"""OneAI's reading (the topics it found, see `topics`) as answers for
	`walk`: yes for a question it found, and for a pick the first label."""
	said = {}
	for step in asks(steps):
		key = f"{rule}#{step.get('id')}"
		if step.get("ask") == "pick":
			picked = next(
				(one.get("label") for n, one in enumerate(step.get("labels") or []) if f"{key}#{n}" in about), None
			)
			said[step.get("id")] = picked
		else:
			said[step.get("id")] = key in about
	return said


def actions_in(steps: list) -> list[dict]:
	"""Every action anywhere in a rule, whichever branch it is on."""
	found = []
	for step in steps or []:
		kind = step.get("type")
		if kind in ACTIONS:
			found.append(step)
		found += actions_in(step.get("then")) + actions_in(step.get("else"))
		for label in step.get("labels") or []:
			found += actions_in(label.get("then"))
	return found


def problems(steps: list) -> list[str]:
	"""What stops a rule being saved, in plain words. Empty when it can run."""
	said = []
	actions = actions_in(steps)
	if not [one for one in actions if one.get("type") != "stop"]:
		said.append(_("Add at least one action."))
	for one in actions:
		kind = one.get("type")
		if kind == "move" and not one.get("folder"):
			said.append(_("Choose the folder to move to."))
		if kind == "reply":
			if one.get("with") == "OneAI" and not (one.get("instruction") or "").strip():
				said.append(_("Write what OneAI's reply should say."))
			if one.get("with") != "OneAI" and not (one.get("text") or "").strip():
				said.append(_("Write the reply."))
			if one.get("once") and one["once"] not in ONCE:
				said.append(_("That cannot be set."))
		if kind == "forward" and not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", (one.get("to") or "").strip()):
			said.append(_("Write the address to forward to."))
		if kind in ("assign", "notify") and not one.get("user"):
			said.append(_("Choose who."))
		if kind == "create" and one.get("doctype") not in CREATES:
			said.append(_("Choose what to create."))
	for step in asks(steps):
		if step.get("ask") == "pick" and len([one for one in step.get("labels") or [] if one.get("label")]) < 2:
			said.append(_("Give OneAI at least two labels to pick from."))
		if step.get("ask") != "pick" and not (step.get("question") or "").strip():
			said.append(_("Write the question for OneAI."))
	return list(dict.fromkeys(said))


def from_fields(row: dict) -> list:
	"""A rule of the old shape (one set of conditions, one set of actions,
	About for OneAI) as steps."""
	items = [
		{"field": field, "op": "contains", "value": row.get(key)}
		for field, key in (
			("from", "from_contains"),
			("to", "to_contains"),
			("subject", "subject_contains"),
			("text", "body_contains"),
		)
		if row.get(key)
	]
	if row.get("has_attachment"):
		items.append({"field": "attachment", "value": True})
	then = []
	if row.get("move_to"):
		then.append({"type": "move", "folder": row["move_to"]})
	if row.get("mark_read"):
		then.append({"type": "read"})
	if row.get("star"):
		then.append({"type": "star"})
	if row.get("reply"):
		then.append(
			{
				"type": "reply",
				"with": row.get("reply_with") or "Text",
				"text": row.get("reply_text") or "",
				"instruction": row.get("reply_instruction") or "",
				"review": int(bool(row.get("reply_review"))),
				"once": "conversation",
			}
		)
	if row.get("stop"):
		then.append({"type": "stop"})
	test_ = {"any": (row.get("match") or "").startswith("Any"), "items": items}
	if row.get("about"):
		return [{"type": "ask", "id": "a1", "ask": "yes", "question": row["about"], "then": [{"type": "if", "id": "i1", "test": test_, "then": then, "else": []}] if items else then, "else": []}]
	return [{"type": "if", "id": "i1", "test": test_, "then": then, "else": []}]


def summary(steps: list, folders: dict | None = None, people: dict | None = None) -> tuple[str, str]:
	"""A rule in words, as its row and its approval notice say it: what it
	looks for, and what it does, branches flattened."""
	folders, people = folders or {}, people or {}
	whens, thens = [], []
	for step in steps or []:
		if step.get("type") == "if":
			whens.append(group_words(step.get("test")))
		elif step.get("type") == "ask":
			whens.append(_("OneAI: {0}").format(step.get("question") or ", ".join(one.get("label") or "" for one in step.get("labels") or [])))
	for one in actions_in(steps):
		thens.append(action_words(one, folders, people))
	return " · ".join(one for one in whens if one) or _("All mail"), " · ".join(dict.fromkeys(thens))


def group_words(group: dict | None) -> str:
	parts = [
		f"({group_words(one)})" if "items" in one else condition_words(one) for one in (group or {}).get("items") or []
	]
	return (_(" or ") if (group or {}).get("any") else " · ").join(one for one in parts if one)


def condition_words(one: dict) -> str:
	field, value = one.get("field"), one.get("value")
	names = {
		"from": _("From"),
		"to": _("To"),
		"subject": _("Subject"),
		"text": _("Text"),
		"domain": _("Sender's Domain"),
	}
	ops = {
		"contains": _("has {0}"),
		"not_contains": _("hasn't {0}"),
		"is": _("is {0}"),
		"is_not": _("isn't {0}"),
		"starts_with": _("starts with {0}"),
		"ends_with": _("ends with {0}"),
	}
	if field in names:
		return f"{names[field]} {ops.get(one.get('op') or 'contains', ops['contains']).format(value or '')}"
	flags = {
		"attachment": (_("Has Attachment"), _("No Attachment")),
		"starts": (_("Starts a Conversation"), _("Answers a Conversation")),
		"outside": (_("From Outside the Workspace"), _("From the Workspace")),
		"holiday": (_("On a Holiday"), _("Not on a Holiday")),
		"after_hours": (_("After Hours"), _("In Working Hours")),
	}
	if field in flags:
		return flags[field][0 if one.get("value", True) else 1]
	if field == "sender_is":
		return (_("Sender isn't a {0}") if one.get("op") == "is_not" else _("Sender is a {0}")).format(_(value or ""))
	return ""


def action_words(one: dict, folders: dict, people: dict) -> str:
	kind = one.get("type")
	if kind == "move":
		return _("Move to {0}").format(folders.get(one.get("folder"), one.get("folder")))
	if kind == "reply":
		return _("Reply With OneAI") if one.get("with") == "OneAI" else _("Reply")
	if kind == "forward":
		return _("Forward to {0}").format(one.get("to"))
	if kind == "assign":
		return _("Assign to {0}").format(people.get(one.get("user"), one.get("user")))
	if kind == "notify":
		return _("Tell {0}").format(people.get(one.get("user"), one.get("user")))
	if kind == "create":
		return _("Create {0}").format(_(one.get("doctype") or ""))
	return {
		"read": _("Mark as Read"),
		"star": _("Star"),
		"junk": _("Move to Junk"),
		"link": _("Link to Their Record"),
		"stop": _("Stop Here"),
	}.get(kind, "")
