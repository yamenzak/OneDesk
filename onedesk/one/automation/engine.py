"""Automations run here: a trigger's own code calls `run` with the record a
run is about and what is known of it (its facts), and each action is done
by its block, its module's own function (kinds.py). Nothing here needs
OneAI: an automation with no Ask and no OneAI block runs without it."""

import frappe

from onedesk.one.automation import flow, kinds


def kinds_of(trigger: str) -> dict:
	"""{condition: its kind} for a trigger's conditions, as flow tests them."""
	return {one.key: one.kind for one in kinds.conditions(trigger)}


def steps_of(row) -> list:
	said = frappe.parse_json(row.steps) if isinstance(row.steps, str) else row.steps
	return said if isinstance(said, list) else []


def listed(trigger: str, scope: str, by_meaning: bool = False) -> list:
	"""A scope's automations of one trigger that are on, in order: those
	that run as it fires, or only those that wait for OneAI's reading
	(flow.needs_ai)."""
	return [
		row
		for row in frappe.get_all(
			"Automation",
			filters={"trigger": trigger, "scope": scope, "enabled": 1},
			fields=["name", "title", "steps", "owner"],
			order_by="priority asc, creation asc",
		)
		if flow.needs_ai(steps_of(row)) == by_meaning
	]


def run(trigger: str, scope: str, name: str, facts: dict, context: dict | None = None, about: set | None = None) -> list[str]:
	"""A scope's automations, in order, on one record, until one says stop.
	As the trigger fires `about` is None and only those without an Ask run;
	OneAI's reading runs those with one, `about` being the topics it found
	(flow.topics). Answers the automations that did something."""
	done = []
	known = kinds_of(trigger)
	context = {**(context or {}), "trigger": trigger, "doctype": kinds.trigger(trigger).doctype}
	for row in listed(trigger, scope, about is not None):
		steps = steps_of(row)
		answers = flow.answers_of(row.name, steps, about) if about is not None else None
		todo, stopped = flow.walk(steps, facts, known, answers)
		if todo:
			perform(row, name, todo, context)
			done.append(row.name)
		if stopped:
			break
	return done


def perform(row, name: str, todo: list, context: dict) -> None:
	"""What an automation's steps said to do with one record, in order, each
	by its block. Each is tried on its own: one that fails is logged and the
	rest still happen."""
	for step in todo:
		block = kinds.action(step.get("type"))
		try:
			if not block:
				raise KeyError(step.get("type"))
			block.run(row, name, step, context)
		except Exception:
			frappe.log_error(title=f"The automation {row.title or row.name} could not {step.get('type')}")


def topics(trigger: str, scope: str) -> list[tuple[str, str]]:
	"""Everything a scope's automations ask OneAI of a new record (flow.topics),
	for its reading."""
	return [one for row in listed(trigger, scope, True) for one in flow.topics(row.name, steps_of(row))]


def problems(trigger: str, steps: list) -> list[str]:
	"""What keeps steps from being saved for a trigger, in plain words."""
	offered = {one.key: one.check for one in kinds.actions(trigger)}
	return flow.problems(steps, kinds_of(trigger), offered)


def summary(trigger: str, steps: list, offers: dict | None = None) -> tuple[str, str]:
	"""An automation in words: what it looks for, and what it does."""
	known = {one.key: one for one in kinds.conditions(trigger)}

	def condition(one: dict) -> str:
		block = known.get(one.get("field"))
		if not block:
			return ""
		if block.words:
			return block.words(one)
		if block.kind == "flag":
			return frappe._(block.label if one.get("value", True) else block.no)
		return f"{frappe._(block.label)} {flow.op_words(one.get('op'), one.get('value'))}"

	def action(one: dict) -> str:
		block = kinds.action(one.get("type"))
		if not block:
			return ""
		return block.words(one, offers or {}) if block.words else frappe._(block.label)

	return flow.summary(steps, condition, action, frappe._(kinds.trigger(trigger).everything))
