"""A module's setup steps (docs/READY.md, mechanism 9): each ready module's
STEPS in its setup.py, a key, a title, what it is for, the ability it needs,
the settings tab that does it and how to tell it's done. A step with fields
is a wizard slide and a SetupCenter form, both from `fields`; the rest wait
in SetupCenter (one/setup_center.py) until done."""

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
		slides.append(
			{
				"name": f"one_{prefix.rstrip('_')}",
				"module": module,
				"title": str(step["title"]),
				"help": " ".join([str(step["about"]), _("You can leave this for later.")] if step.get("later", True) else [str(step["about"])]),
				"fields": fields(step, prefix, required=not step.get("later", True)),
			}
		)
	from onedesk.trust_center import services

	asked = services.for_wizard()
	return slides + ([asked] if asked else [])


def fields(step: dict, prefix: str = "", required: bool = False) -> list[dict]:
	"""A step's fields as a form takes them, its words in the reader's
	language and each name after `prefix`: the wizard's slide and
	SetupCenter's form are this one declaration. A field is required where
	`required` and the field says so (by default it does), but a Check,
	which is never empty."""
	out = []
	for field in step.get("fields") or []:
		one = {key: (str(value) if key in ("label", "description") else value) for key, value in field.items()}
		one["fieldname"] = prefix + field["fieldname"]
		one["reqd"] = int(required and bool(field.get("reqd", 1)) and field.get("fieldtype") != "Check")
		out.append(one)
	return out


def mark(module: str, step: dict) -> None:
	"""A step written down as done."""
	frappe.db.set_default(_flag(module, step), "1")


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
		save(module, step, values)
	from onedesk.trust_center import services

	services.from_wizard(args)


def save(module: str, step: dict, values: dict) -> bool:
	"""A step saved from its values (the wizard's, or the setup job's) and
	marked done; one given nothing stays a to-do, and one that fails is
	logged and left for later rather than undoing the setup. Whether it
	was saved."""
	if all(value in (None, "", []) for value in values.values()):
		return False
	frappe.db.savepoint("one_setup_step")
	try:
		step["save"](values)
		mark(module, step)
	except Exception:
		frappe.db.rollback(save_point="one_setup_step")
		frappe.log_error(f"setup step: {module} {step['key']}")
		return False
	return True


def may(module: str, step: dict) -> bool:
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
	done: a module's settings start with Getting Started, which opens
	SetupCenter, while one waits, and Apps opens SetupCenter on an app just
	turned on that has steps."""
	out = {}
	for module, step in declared():
		if not may(module, step):
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

