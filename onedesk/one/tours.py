"""A module's tours (docs/READY.md, mechanism 10), one for each area of its
screen, declared in its own `tour.py` as `TOURS`: a key, the `data-tour` mark
that says the area is on screen (`at`), and steps, each pointing at a mark.
An area's tour runs on frappe's driver the first time somebody opens it, and
again from the tour button in the module's foot, which takes the one of the
area on screen."""

import importlib

import frappe
from frappe import _

from onedesk.one import ready, versions

SEEN = "one_toured_{}_{}"


def _tours(module: str) -> list[dict]:
	try:
		return importlib.import_module(f"onedesk.{ready.MODULES[module]['folder']}.tour").TOURS
	except (KeyError, ModuleNotFoundError):
		return []


def _seen(module: str, key: str) -> bool:
	return frappe.defaults.get_user_default(SEEN.format(ready.MODULES[module]["folder"], key)) == "1"


def unseen() -> list[str]:
	"""The areas whose tour the reader hasn't taken, as `Module:key`, for the boot."""
	return [f"{module}:{one['key']}" for module in ready.MODULES if versions.offered(module) for one in _tours(module) if not _seen(module, one["key"])]


@frappe.whitelist()
def tour(module: str) -> list[dict]:
	"""A module's tours, each with its steps in the reader's language."""
	if module not in ready.MODULES or not versions.offered(module):
		frappe.throw(_("{0} has no tour.").format(module))
	return [
		{
			"key": one["key"],
			"at": one["at"],
			"steps": [
				{"target": step["target"], "title": str(step["title"]), "text": str(step["text"]), "side": step.get("side", "bottom")}
				for step in one["steps"]
			],
		}
		for one in _tours(module)
	]


@frappe.whitelist(methods=["POST"])
def seen(module: str, key: str) -> None:
	"""The reader took an area's tour, or closed it: it doesn't start on its own again."""
	if module in ready.MODULES and key in {one["key"] for one in _tours(module)}:
		frappe.defaults.set_user_default(SEEN.format(ready.MODULES[module]["folder"], key), "1")
