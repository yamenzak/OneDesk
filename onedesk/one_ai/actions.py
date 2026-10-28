"""OneAI's actions: a button that does one thing in place, such as Write My
Bio, rather than a question for the panel. Each app declares its own in its
ai.py as ACTIONS and names them in hooks.py (`one_ai_actions`), so AICenter
finds every app's without knowing them; an administrator turns any of them
off there, and then its button is gone and the server refuses it."""

import json

import frappe
from frappe import _

KEY = "one_ai_actions_off"


def declared() -> dict[str, dict]:
	"""Every action an app declares, by key: label, about and module."""
	found = {}
	for path in frappe.get_hooks("one_ai_actions") or []:
		for one in frappe.get_attr(path):
			found[one["key"]] = one
	return found


def off() -> set[str]:
	try:
		return set(json.loads(frappe.db.get_default(KEY) or "[]"))
	except ValueError:
		return set()


def on(key: str) -> bool:
	from onedesk.one import apps

	return apps.ai_on() and key in declared() and key not in off()


def refuse(key: str) -> None:
	"""Every action asks this before it runs."""
	if not on(key):
		frappe.throw(_("This OneAI action is turned off for this workspace."), frappe.PermissionError)


def for_boot() -> dict[str, int]:
	"""Each action and whether it is on, for the buttons to draw or not."""
	shut = off()
	return {key: int(key not in shut) for key in declared()}


def of(module: str) -> list[dict]:
	"""A module's actions, as AICenter draws them."""
	shut = off()
	return [
		{"key": key, "label": str(one["label"]), "about": str(one["about"]), "on": int(key not in shut)}
		for key, one in declared().items()
		if one["module"] == module
	]


def modules() -> list[str]:
	return list(dict.fromkeys(one["module"] for one in declared().values()))


@frappe.whitelist(methods=["POST"])
def switch(key: str, on: int | str) -> dict:
	"""AICenter: one action on or off for the whole workspace."""
	from onedesk.one import roles

	roles.require()
	if key not in declared():
		frappe.throw(_("{0} is not one of OneAI's actions.").format(key))
	shut = off()
	if frappe.utils.cint(on):
		shut.discard(key)
	else:
		shut.add(key)
	frappe.db.set_default(KEY, json.dumps(sorted(shut)))
	return for_boot()
