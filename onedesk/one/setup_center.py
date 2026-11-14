"""SetupCenter (docs/run/RUN.md, P4.7): every app's setup steps, done and
waiting, from the steps each app declares in its setup.py
(one/setup_steps.py). A step with fields is the same form the setup wizard
and the setup job fill; one without is done on its app's settings tab, then
marked done. Installing an app in Apps opens it here, on that app."""

from typing import Annotated

import frappe
from frappe import _

from onedesk.one import registry, setup_steps

CENTRES = {"account_center": "account"}
"""The centre an app's steps open when the app is itself a centre; every
other app's open its ControlCenter."""


def sections(declared: list[tuple[str, dict]], off: set[str], may, done) -> list[dict]:
	"""Each app that is on and has a step the reader may do, in the order the
	steps are declared (the rail's), its steps each saying whether it is done,
	and how many wait. `may` and `done` take the app and the step. Pure."""
	found: dict[str, list[dict]] = {}
	for module, step in declared:
		if module in off or not may(module, step):
			continue
		found.setdefault(module, []).append(
			{
				"key": step["key"],
				"title": str(step["title"]),
				"about": str(step["about"]),
				"tab": step.get("tab"),
				"fields": setup_steps.fields(step, required=True) if step.get("fields") and step.get("save") else [],
				"done": int(bool(done(module, step))),
			}
		)
	return [{"app": module, "steps": steps, "waiting": sum(1 for one in steps if not one["done"])} for module, steps in found.items()]


def _off() -> set[str]:
	"""The apps turned off in Apps, or left out of the plan, by name."""
	from onedesk.one import apps

	hidden = set(apps.hidden())
	return {one.name for one in registry.apps() if one.sidebar and one.sidebar in hidden}


@frappe.whitelist()
@frappe.read_only()
def load() -> dict:
	"""The apps whose steps the reader may do, each with its steps and the
	centre they open."""
	said = sections(setup_steps.declared(), _off(), lambda module, step: setup_steps.may(module, step), setup_steps.done)
	for one in said:
		one["center"] = CENTRES.get(registry.by_name(one["app"]).id, "settings")
	return {"apps": said}


def _step(module: str, key: str) -> dict:
	step = next((one for name, one in setup_steps.declared() if name == module and one["key"] == key), None)
	if not step or not setup_steps.may(module, step):
		frappe.throw(_("Your role doesn't allow changing this."), frappe.PermissionError)
	return step


@frappe.whitelist(methods=["POST"])
def save(
	module: Annotated[str, "The app, by name."],
	key: Annotated[str, "The step's key."],
	values: Annotated[str | dict, "The step's fields, by fieldname."],
) -> dict:
	"""A step's form saved through the step's own save, as the wizard and
	the setup job save it, and the step marked done."""
	step = _step(module, key)
	if not step.get("fields") or not step.get("save"):
		frappe.throw(_("There is nothing to save here."))
	given = frappe.parse_json(values) or {}
	step["save"]({field["fieldname"]: given.get(field["fieldname"]) for field in step["fields"]})
	setup_steps.mark(module, step)
	return load()


@frappe.whitelist(methods=["POST"])
def finish(
	module: Annotated[str, "The app, by name."],
	key: Annotated[str, "The step's key."],
) -> dict:
	"""A step marked done by somebody who may do it."""
	setup_steps.mark(module, _step(module, key))
	return load()


def reaches(user: str | None = None) -> bool:
	"""Whether the reader may do any app's step, so SetupCenter's row is on
	their rail and its setup guide answers them."""
	return any(setup_steps.may(module, step, user) for module, step in setup_steps.declared())
