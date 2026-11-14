"""AutomationCenter's blocks (docs/ARC-AI.md, AutomationCenter): what an
automation starts on, what it checks and what it does, each declared by the
module that owns it in its own `blocks.py` as `BLOCKS` and found through
the `one_automation_blocks` hook the registry builds. An automation writes
nothing of its own: every action is its module's own function, so it can do
no more than that module's own screens let its owner do."""

from collections.abc import Callable
from dataclasses import dataclass

import frappe
from frappe import _

STRUCTURE = ("if", "ask", "stop")
"""The steps every automation has, whatever starts it: an If, an Ask (of
OneAI, on a trigger whose reading answers it) and Stop. Every other step
is an action block."""


@dataclass(frozen=True)
class Trigger:
	"""What an automation starts on: `scope` is the record type one belongs
	to (the mailbox), `doctype` what each run is about (the message), and
	`keeps` the module's functions that keep its automations, as its own
	screens did (one/AGENTS.md, AutomationCenter, says each)."""

	key: str
	label: str
	icon: str
	scope: str
	doctype: str
	module: str
	keeps: dict
	everything: str
	reads: bool = False
	starters: Callable | None = None

	def keeper(self, what: str) -> Callable:
		return frappe.get_attr(f"onedesk.{self.module}.{self.keeps[what]}")


@dataclass(frozen=True)
class Condition:
	"""One thing an If can ask of what a trigger knows (its facts): `kind`
	is "text" (contains, is, starts with…), "flag" (yes or no, `label` its
	words for yes and `no` for no) or "kind" (is or isn't one of `options`).
	`words(condition)` says one in short where "From has invoice" will not do."""

	key: str
	label: str
	kind: str
	trigger: str
	no: str = ""
	options: tuple = ()
	words: Callable | None = None


@dataclass(frozen=True)
class Param:
	"""One thing an action asks: "text", "long", "email", "switch" or
	"choice", whose `options` are (value, label) pairs or the name of an
	offer (the mailbox's folders, its people, the agents). `shown` names
	another param and the values it must have for this one to be asked."""

	key: str
	label: str
	type: str
	options: tuple | str = ()
	default: object = None
	shown: tuple = ()
	description: str = ""
	placeholder: str = ""
	needed: bool = True


@dataclass(frozen=True)
class Action:
	"""One thing an automation does: `run(automation, name, step, context)`,
	its module's own function on the record a run is about. `triggers` it
	is offered on, every one when empty; `check(step)` says what keeps it
	from being saved, in plain words; `words(step, offers)` says it in short;
	`ai`, it needs OneAI, so it is offered only where OneAI may read; `offers`
	adds named choices of its own (the agents)."""

	key: str
	label: str
	icon: str
	run: Callable
	group: str = ""
	triggers: tuple = ()
	params: tuple = ()
	check: Callable | None = None
	words: Callable | None = None
	ai: bool = False
	offers: Callable | None = None


def declared() -> list:
	"""Every block every module declares, in the rail's order."""
	cache = getattr(frappe.local, "one_automation_blocks", None)
	if cache is not None:
		return cache
	found = []
	for path in frappe.get_hooks("one_automation_blocks"):
		found += list(frappe.get_attr(path))
	keys = [(type(one).__name__, one.key) for one in found if not isinstance(one, Condition)]
	twice = sorted({key for key in keys if keys.count(key) > 1})
	if twice:
		frappe.throw(_("Two modules declare the block {0}.").format(twice[0][1]))
	frappe.local.one_automation_blocks = found
	return found


def triggers() -> list[Trigger]:
	return [one for one in declared() if isinstance(one, Trigger)]


def trigger(key: str) -> Trigger:
	found = next((one for one in triggers() if one.key == key), None)
	if not found:
		frappe.throw(_("Nothing starts an automation as {0}.").format(key))
	return found


def conditions(key: str) -> list[Condition]:
	return [one for one in declared() if isinstance(one, Condition) and one.trigger == key]


def actions(key: str) -> list[Action]:
	return [one for one in declared() if isinstance(one, Action) and (not one.triggers or key in one.triggers)]


def action(key: str) -> Action | None:
	return next((one for one in declared() if isinstance(one, Action) and one.key == key), None)
