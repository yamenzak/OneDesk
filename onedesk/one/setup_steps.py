"""A module's setup steps (docs/READY.md, mechanism 9).

A ready module declares its steps in its own `setup.py` as STEPS: each a
key, a title, what it is for, the ability it needs, the module's settings
tab that does it, and how to tell it's done. A step with fields is a slide
of the setup wizard; one left empty there, or with no fields, is a to-do
on Getting Started in the module's settings until it is done.
"""

import importlib

import frappe
from frappe import _

from onedesk.one import ready

FLAG = "one_setup_{}_{}"


def declared() -> list[tuple[str, dict]]:
	"""(module, step) for every ready module's steps, in order."""
	found = []
	for module, spec in ready.MODULES.items():
		try:
			steps = importlib.import_module(f"onedesk.{spec['folder']}.setup").STEPS
		except ModuleNotFoundError:
			continue
		found += [(module, step) for step in steps]
	return found


def _flag(module: str, step: dict) -> str:
	return FLAG.format(ready.MODULES[module]["folder"], step["key"])


def done(module: str, step: dict) -> bool:
	"""Done when the step says so (`done`), or once it was saved or marked
	done."""
	if step.get("done") and step["done"]():
		return True
	return frappe.db.get_default(_flag(module, step)) == "1"


def _prefix(module: str, step: dict) -> str:
	return f"{ready.MODULES[module]['folder']}_{step['key']}_"


def for_wizard() -> list[dict]:
	"""The wizard's slides for the steps with fields, decided when the
	wizard is built; their fields named for the module and step."""
	if frappe.is_setup_complete():
		return []
	slides = []
	for module, step in declared():
		if not step.get("fields"):
			continue
		prefix = _prefix(module, step)
		fields = []
		for field in step["fields"]:
			one = {key: (str(value) if key in ("label", "description") else value) for key, value in field.items()}
			one["fieldname"] = prefix + field["fieldname"]
			one["reqd"] = int(not step.get("later", True) and bool(field.get("reqd", 1)))
			fields.append(one)
		slides.append(
			{
				"name": f"one_{prefix.rstrip('_')}",
				"module": module,
				"title": str(step["title"]),
				"help": " ".join([str(step["about"]), _("You can leave this for later.")] if step.get("later", True) else [str(step["about"])]),
				"fields": fields,
			}
		)
	from onedesk.one_legal import services

	asked = services.for_wizard()
	return slides + ([asked] if asked else [])


def apply(args=None) -> None:
	"""A setup wizard task: each step with fields saved from what was given,
	as one that was left empty stays a to-do. A step that fails is logged and
	left for later rather than undoing the setup."""
	args = args or {}
	for module, step in declared():
		if not step.get("fields"):
			continue
		prefix = _prefix(module, step)
		values = {field["fieldname"]: args.get(prefix + field["fieldname"]) for field in step["fields"]}
		if all(value in (None, "", []) for value in values.values()):
			continue
		frappe.db.savepoint("one_setup_step")
		try:
			step["save"](values)
			frappe.db.set_default(_flag(module, step), "1")
		except Exception:
			frappe.db.rollback(save_point="one_setup_step")
			frappe.log_error(f"setup step: {module} {step['key']}")
	from onedesk.one_legal import services

	services.from_wizard(args)


def _may(module: str, step: dict) -> bool:
	from onedesk.one import rights, roles

	if roles.administers():
		return True
	declared_abilities = rights.of_app(module)
	if not declared_abilities or not step.get("needs"):
		return False
	ability = rights.ability(module, step["needs"])
	return rights.held(declared_abilities.DOCTYPE, ability["all"])


def for_boot() -> dict:
	"""{module: [step, ...]} the reader may do, each saying whether it is
	done, for Getting Started in the module's settings."""
	out = {}
	for module, step in declared():
		if not _may(module, step):
			continue
		out.setdefault(module, []).append(
			{
				"key": step["key"],
				"title": str(step["title"]),
				"about": str(step["about"]),
				"tab": step.get("tab"),
				"done": int(done(module, step)),
			}
		)
	return out


@frappe.whitelist(methods=["POST"])
def finish(module: str, key: str) -> dict:
	"""A step marked done by somebody who may do it, from Getting Started."""
	step = next((one for name, one in declared() if name == module and one["key"] == key), None)
	if not step or not _may(module, step):
		frappe.throw(_("That cannot be set."))
	frappe.db.set_default(_flag(module, step), "1")
	return for_boot().get(module, [])
