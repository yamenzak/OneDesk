"""AutomationCenter (docs/ARC-AI.md, AutomationCenter): every automation the
reader keeps or asks for, by what starts it and where it runs, and what its
builder offers. Each trigger's app keeps its own automations (Trigger.keeps,
one/automation/kinds.py): who changes them, who asks for them and who
approves, as its own screens said before, so this file decides nothing."""

import frappe
from frappe import _

from onedesk.one import registry
from onedesk.one.automation import engine, flow, kinds


@frappe.whitelist()
def places() -> list[dict]:
	"""Each trigger with the places it runs whose automations the reader keeps
	or asks for (a mailbox), each with how many it has."""
	frappe.has_permission("Automation", "read", throw=True)
	said = []
	for one in kinds.triggers():
		scopes = one.keeper("scopes")()
		if not scopes:
			continue
		counts = dict(
			frappe.get_all(
				"Automation",
				filters={"trigger": one.key, "scope": ["in", [place["scope"] for place in scopes]]},
				fields=["scope", {"COUNT": "*", "as": "count"}],
				group_by="scope",
				as_list=True,
			)
		)
		said.append({"trigger": one.key, "label": _(one.label), "icon": one.icon, "runs": _(one.runs).format(registry.name("one_ai")), "scopes": [{**place, "count": counts.get(place["scope"], 0)} for place in scopes]})
	return said


@frappe.whitelist()
def automations(trigger: str, scope: str) -> dict:
	"""One place's automations in the order they run, with what each looks for
	and does, whether the reader changes them or asks for them."""
	return kinds.trigger(trigger).keeper("listed")(scope)


def _param(one, offers: dict) -> dict:
	options = (offers.get(one.options) or []) if isinstance(one.options, str) else [{"value": value, "label": _(label)} for value, label in one.options]
	return {
		"key": one.key,
		"label": registry.filled(_(one.label)),
		"type": one.type,
		"options": options,
		"default": one.default,
		"shown": [[key, list(values)] for key, values in one.shown],
		"description": registry.filled(_(one.description)) if one.description else "",
		"placeholder": one.placeholder,
		"needed": int(one.needed),
	}


@frappe.whitelist()
def blocks(trigger: str, scope: str) -> dict:
	"""What the builder offers in one place: what starts it, the conditions an
	If may ask with the tests a text one takes, the actions with what each
	asks and its choices, the automations a new one may start from, and
	whether OneAI may read there (an Ask, a reply it writes, an agent) and
	reads what arrives (an Ask runs)."""
	held = kinds.trigger(trigger)
	offers = dict(held.keeper("offers")(scope))
	offered = [one for one in kinds.actions(trigger) if not one.ai or offers.get("ai")]
	for one in offered:
		if one.offers:
			offers.update(one.offers())
	return {
		"trigger": {"key": held.key, "label": _(held.label), "icon": held.icon, "where": offers.get("where") or offers.get("email") or scope, "reads": int(held.reads)},
		"conditions": [
			{"key": one.key, "label": _(one.label), "kind": one.kind, "no": _(one.no) if one.no else "", "options": [{"value": value, "label": _(value)} for value in one.options]}
			for one in kinds.conditions(trigger)
		],
		"ops": flow.op_labels(),
		"actions": [
			{"key": one.key, "label": _(one.label), "icon": one.icon, "group": _(one.group) if one.group else "", "ai": int(one.ai), "params": [_param(param, offers) for param in one.params]}
			for one in offered
		],
		"starters": held.starters(offers) if held.starters else [],
		"ai": int(bool(offers.get("ai"))),
		"reads": int(bool(offers.get("reads"))),
		"unread": offers.get("unread") or "",
	}


@frappe.whitelist()
def automation(name: str) -> dict:
	"""One automation as its builder opens it, for whoever may read it."""
	doc = frappe.get_doc("Automation", name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"title": doc.title,
		"trigger": doc.trigger,
		"scope": doc.scope,
		"enabled": doc.enabled,
		"priority": doc.priority,
		"steps": engine.steps_of(doc),
		"requested_by": doc.requested_by,
		"requested_by_name": frappe.utils.get_fullname(doc.requested_by) if doc.requested_by else None,
	}


@frappe.whitelist(methods=["POST"])
def problems(trigger: str, steps: list | str) -> list[str]:
	"""What keeps the builder's steps from being saved, in plain words."""
	return engine.problems(trigger, frappe.parse_json(steps) if isinstance(steps, str) else steps)


@frappe.whitelist(methods=["POST"])
def save(trigger: str, scope: str, values: dict | str, name: str | None = None) -> str:
	"""Make or change an automation, as its trigger's app says: outright, or
	asked for and waiting for whoever may approve it."""
	return kinds.trigger(trigger).keeper("save")(scope, values, name)


def _kept(doc, what: str):
	return kinds.trigger(doc.trigger).keeper(what)


@frappe.whitelist(methods=["POST"])
def enable(name: str, enabled: int = 1) -> None:
	"""Turn an automation on or off, where the reader changes its place's."""
	doc = frappe.get_doc("Automation", name)
	doc.check_permission("read")
	_kept(doc, "enable")(name, enabled)


@frappe.whitelist(methods=["POST"])
def delete(name: str) -> None:
	"""Delete an automation: whoever changes its place's, or whoever asked for
	it while it waits."""
	doc = frappe.get_doc("Automation", name)
	doc.check_permission("read")
	_kept(doc, "delete")(name)


@frappe.whitelist(methods=["POST"])
def decide(name: str, approve: int = 1) -> None:
	"""Approve an automation somebody asked for, which turns it on, or decline
	it, which deletes it."""
	doc = frappe.get_doc("Automation", name)
	doc.check_permission("read")
	_kept(doc, "decide")(name, approve)
