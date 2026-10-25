"""A module's tour (docs/READY.md, mechanism 10): the steps it declares in
its own `tour.py`, each pointing at a `data-tour` mark on its screen, run on
frappe's driver the first time somebody opens the module, and again from
HelpCenter."""

import importlib

import frappe
from frappe import _

from onedesk.one import ready

SEEN = "one_toured_{}"


def _steps(module: str) -> list[dict]:
	try:
		return importlib.import_module(f"onedesk.{ready.MODULES[module]['folder']}.tour").STEPS
	except (KeyError, ModuleNotFoundError):
		return []


def unseen() -> list[str]:
	"""The modules with a tour the reader hasn't taken, for the boot."""
	return [
		module
		for module, spec in ready.MODULES.items()
		if _steps(module) and frappe.defaults.get_user_default(SEEN.format(spec["folder"])) != "1"
	]


@frappe.whitelist()
def tour(module: str) -> list[dict]:
	"""A module's steps, in the reader's language."""
	if module not in ready.MODULES:
		frappe.throw(_("{0} has no tour.").format(module))
	return [
		{"target": step["target"], "title": str(step["title"]), "text": str(step["text"]), "side": step.get("side", "bottom")}
		for step in _steps(module)
	]


@frappe.whitelist(methods=["POST"])
def seen(module: str) -> None:
	"""The reader took the tour, or closed it: it doesn't start on its own again."""
	if module in ready.MODULES:
		frappe.defaults.set_user_default(SEEN.format(ready.MODULES[module]["folder"]), "1")
