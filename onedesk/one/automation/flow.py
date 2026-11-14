"""An automation's steps (Automation.steps), and what they do to one record.

Steps run top to bottom: an If (conditions in groups that nest, All or Any,
with a branch for yes and one for no), an Ask of OneAI (a branch for each
answer), or an action block. Stop ends it and every automation after it.
All pure: the engine gathers the trigger's facts and does what `walk`
answers; `kinds` is {condition: "text", "flag" or "kind"}, from the blocks.
"""

from frappe import _

from onedesk.one import registry

OPS = ("contains", "not_contains", "is", "is_not", "starts_with", "ends_with")


def test(group: dict | None, facts: dict, kinds: dict) -> bool:
	"""Whether a record meets a group of conditions. An empty group is met by
	every record, so an automation without conditions is for all of them."""
	items = (group or {}).get("items") or []
	if not items:
		return True
	results = (test(one, facts, kinds) if "items" in one else holds(one, facts, kinds) for one in items)
	return any(results) if (group or {}).get("any") else all(results)


def holds(condition: dict, facts: dict, kinds: dict) -> bool:
	"""One condition against what is known of the record."""
	field = condition.get("field")
	kind = kinds.get(field)
	if kind == "text":
		return said(facts.get(field) or "", condition.get("op") or "contains", condition.get("value") or "")
	if kind == "flag":
		return bool(facts.get(field)) == bool(condition.get("value", True))
	if kind == "kind":
		found = set(facts.get(field) or ())
		return (condition.get("value") in found) != (condition.get("op") == "is_not")
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


def walk(steps: list, facts: dict, kinds: dict, answers: dict | None = None) -> tuple[list, bool]:
	"""The actions a record gets from an automation's steps, in order, and
	whether it said stop. `answers` are OneAI's, {step id: True/False for a
	question, or the label picked}; without them an Ask takes neither branch,
	which never happens since such an automation waits for OneAI (needs_ai)."""
	done = []
	for step in steps or []:
		kind = step.get("type")
		if kind in ("if", "ask"):
			branch = (step.get("then") if test(step.get("test"), facts, kinds) else step.get("else")) if kind == "if" else _answered(step, answers)
			more, stopped = walk(branch, facts, kinds, answers)
			done += more
			if stopped:
				return done, True
		elif kind == "stop":
			return done, True
		elif kind:
			done.append(step)
	return done, False


def _answered(step: dict, answers: dict | None):
	"""The branch OneAI's answer to one Ask takes."""
	said = (answers or {}).get(step.get("id"))
	if step.get("ask") == "pick":
		for label in step.get("labels") or []:
			if said is not None and said == label.get("label"):
				return label.get("then")
		return step.get("else")
	return step.get("then") if said else step.get("else")


def asks(steps: list) -> list[dict]:
	"""Every Ask in an automation, nested ones too."""
	found = []
	for step in steps or []:
		if step.get("type") == "ask":
			found.append(step)
			for label in step.get("labels") or []:
				found += asks(label.get("then"))
		found += asks(step.get("then")) + asks(step.get("else"))
	return found


def needs_ai(steps: list) -> bool:
	"""Whether an automation waits for OneAI to have read the record."""
	return bool(asks(steps))


def topics(name: str, steps: list) -> list[tuple[str, str]]:
	"""What OneAI is asked to read a record for, one topic each: a question
	(`automation#step`), or each label it can pick (`automation#step#n`)."""
	said = []
	for step in asks(steps):
		key = f"{name}#{step.get('id')}"
		if step.get("ask") == "pick":
			said += [(f"{key}#{n}", one.get("about") or one.get("label")) for n, one in enumerate(step.get("labels") or [])]
		else:
			said.append((key, step.get("question") or ""))
	return [one for one in said if one[1]]


def answers_of(name: str, steps: list, about: set) -> dict:
	"""OneAI's reading (the topics it found, see `topics`) as answers for
	`walk`: yes for a question it found, and for a pick the first label."""
	said = {}
	for step in asks(steps):
		key = f"{name}#{step.get('id')}"
		if step.get("ask") == "pick":
			said[step.get("id")] = next(
				(one.get("label") for n, one in enumerate(step.get("labels") or []) if f"{key}#{n}" in about), None
			)
		else:
			said[step.get("id")] = key in about
	return said


def actions_in(steps: list) -> list[dict]:
	"""Every action anywhere in an automation, Stop too, whichever branch it is on."""
	found = []
	for step in steps or []:
		if step.get("type") not in ("if", "ask"):
			found.append(step)
		found += actions_in(step.get("then")) + actions_in(step.get("else"))
		for label in step.get("labels") or []:
			found += actions_in(label.get("then"))
	return found


def conditions_in(steps: list) -> list[dict]:
	"""Every condition in an automation's Ifs, in groups and branches too."""

	def of(group):
		found = []
		for one in (group or {}).get("items") or []:
			found += of(one) if "items" in one else [one]
		return found

	found = []
	for step in steps or []:
		if step.get("type") == "if":
			found += of(step.get("test"))
		found += conditions_in(step.get("then")) + conditions_in(step.get("else"))
		for label in step.get("labels") or []:
			found += conditions_in(label.get("then"))
	return found


def problems(steps: list, kinds: dict, checks: dict) -> list[str]:
	"""What stops an automation being saved, in plain words; empty when it
	can run. `checks` is each action's own check, by its key."""
	said = []
	actions = actions_in(steps)
	if not [one for one in actions if one.get("type") != "stop"]:
		said.append(_("Add at least one action."))
	for one in actions:
		kind = one.get("type")
		if kind == "stop":
			continue
		if kind not in checks:
			said.append(_("That cannot be set."))
		elif checks[kind]:
			said += checks[kind](one)
	for one in conditions_in(steps):
		if kinds.get(one.get("field")) == "text" and not str(one.get("value") or "").strip():
			said.append(_("Write what each condition looks for."))
		if one.get("field") not in kinds:
			said.append(_("That cannot be set."))
	for step in asks(steps):
		if step.get("ask") == "pick" and len([one for one in step.get("labels") or [] if one.get("label")]) < 2:
			said.append(_("Give {0} at least two labels to pick from.").format(registry.name("one_ai")))
		if step.get("ask") != "pick" and not (step.get("question") or "").strip():
			said.append(_("Write the question for {0}.").format(registry.name("one_ai")))
	return list(dict.fromkeys(said))


def op_labels() -> list[dict]:
	"""What the builder offers for a text condition's test."""
	said = {
		"contains": _("contains"),
		"not_contains": _("doesn't contain"),
		"is": _("is"),
		"is_not": _("isn't"),
		"starts_with": _("starts with"),
		"ends_with": _("ends with"),
	}
	return [{"value": one, "label": said[one]} for one in OPS]


def op_words(op: str | None, value) -> str:
	"""A text condition's test in short: "has invoice"."""
	ops = {
		"contains": _("has {0}"),
		"not_contains": _("hasn't {0}"),
		"is": _("is {0}"),
		"is_not": _("isn't {0}"),
		"starts_with": _("starts with {0}"),
		"ends_with": _("ends with {0}"),
	}
	return ops.get(op or "contains", ops["contains"]).format(value or "")


def summary(steps: list, condition_words, action_words, everything: str) -> tuple[str, str]:
	"""An automation in words, as its row and its approval notice say it:
	what it looks for (`everything`, its trigger's words, without an If), and
	what it does, branches flattened."""
	whens, thens = [], []
	for step in steps or []:
		if step.get("type") == "if":
			whens.append(group_words(step.get("test"), condition_words))
		elif step.get("type") == "ask":
			whens.append(_("{1}: {0}").format(step.get("question") or ", ".join(one.get("label") or "" for one in step.get("labels") or []), registry.name("one_ai")))
	for one in actions_in(steps):
		thens.append(_("Stop Here") if one.get("type") == "stop" else action_words(one))
	return " · ".join(str(one) for one in whens if one) or str(everything), " · ".join(dict.fromkeys(str(one) for one in thens if one))


def group_words(group: dict | None, condition_words) -> str:
	parts = [
		f"({group_words(one, condition_words)})" if "items" in one else condition_words(one) for one in (group or {}).get("items") or []
	]
	return (_(" or ") if (group or {}).get("any") else " · ").join(one for one in parts if one)
