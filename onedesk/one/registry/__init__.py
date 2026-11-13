"""OneRegistry: every app, centre and engine of One, read from the
manifest.py in its own folder (docs/run/RUN.md, OneRegistry). Pure, so
hooks.py, the guards and the scripts read it without a site.

`apps()` in the rail's order, `get(id)`, `name(id)` (the only place a name is
typed), `names()` and `filled(text)` for words that name an app as `{one_doc}`,
`by_name(name)`, `of_module(module)`, and `moved()`, the folders kept one
release after a rename."""

import ast
import importlib
import re
from functools import cache
from pathlib import Path

from onedesk.one.registry.model import COUNTRY, KINDS, REGIONS, UI, App

FOLDERS = Path(__file__).resolve().parents[2]


class Invalid(ValueError):
	"""A manifest that says something the registry can't hold; the message
	names the manifest and the field."""


@cache
def apps() -> tuple[App, ...]:
	found = [_read(path.parent.name) for path in sorted(FOLDERS.glob("*/manifest.py"))]
	_check(found)
	return tuple(sorted(found, key=lambda one: (one.rail is None, one.rail or 0, one.id)))


@cache
def moved() -> dict[str, str]:
	"""Each folder that is only an old name kept one release, read from the
	`MOVED_TO` its __init__.py declares, and the package it now names. Such a
	folder is not an app and has no manifest."""
	found = {}
	for path in sorted(FOLDERS.glob("*/__init__.py")):
		for node in ast.parse(path.read_text(encoding="utf-8")).body:
			if isinstance(node, ast.Assign) and [getattr(one, "id", None) for one in node.targets] == ["MOVED_TO"]:
				found[path.parent.name] = node.value.value
	return found


def get(id: str) -> App:
	for one in apps():
		if one.id == id:
			return one
	raise KeyError(id)


def name(id: str) -> str:
	return get(id).name


@cache
def names() -> dict[str, str]:
	"""Every app's, centre's and engine's name by its id."""
	return {one.id: one.name for one in apps()}


SLOT = re.compile(r"\{([a-z][a-z_]*)\}")


def filled(text: str) -> str:
	"""Words that name an app as `{one_doc}` (a Help page, a version, a
	notification's text) with its name put in; any other braces are left as
	they are. Pure."""
	known = names()
	return SLOT.sub(lambda found: known.get(found.group(1), found.group(0)), text or "")


def by_name(name: str) -> App:
	for one in apps():
		if one.name == name:
			return one
	raise KeyError(name)


def of_module(module: str) -> App | None:
	"""The app a Frappe module's records are reached in: the one that owns it
	(one of frappe's, ERPNext's or HRMS's, or a folder still reached inside
	another, as the editors are inside OneCloud), else the folder whose
	module it is."""
	return next((one for one in apps() if module in one.owns), None) or next(
		(one for one in apps() if module == one.module), None
	)


def _read(folder: str) -> App:
	declared = getattr(importlib.import_module(f"onedesk.{folder}.manifest"), "APP", None)
	if not isinstance(declared, App):
		raise Invalid(f"{folder}/manifest.py: APP must be an App")
	if declared.id != folder:
		raise Invalid(f"{folder}/manifest.py: id is {declared.id!r}, the folder is {folder!r}")
	return declared


def _check(found: list[App]) -> None:
	ids = {one.id for one in found}
	seen: dict[str, str] = {}
	owners: dict[str, str] = {}
	for one in found:
		where = f"{one.id}/manifest.py"
		if one.kind not in KINDS:
			raise Invalid(f"{where}: kind {one.kind!r} is not one of {KINDS}")
		if one.ui not in UI:
			raise Invalid(f"{where}: ui {one.ui!r} is not one of {UI}")
		if not one.name or (not one.module and one.kind != "engine"):
			raise Invalid(f"{where}: a name is required, and a module unless it is an engine")
		for needed in one.needs:
			if needed not in ids:
				raise Invalid(f"{where}: needs {needed!r}, which has no manifest")
		for country, state in one.countries.items():
			if state not in COUNTRY:
				raise Invalid(f"{where}: countries[{country!r}] is {state!r}, not one of {COUNTRY}")
		if one.kind == "app" and one.ui == "none":
			raise Invalid(f"{where}: an app says how its screens are made (ui)")
		for region in one.regions:
			if region.kind not in REGIONS:
				raise Invalid(f"{where}: a region's kind is one of {REGIONS}, not {region.kind!r}")
		for module in one.owns:
			if module in owners:
				raise Invalid(f"{where}: owns {module!r}, which {owners[module]} owns already")
			owners[module] = one.id
		if one.module:
			if one.module in seen:
				raise Invalid(f"{where}: module {one.module!r} is already {seen[one.module]}'s")
			seen[one.module] = one.id
		twins = [other.id for other in found if other.id != one.id and other.name == one.name]
		if twins:
			raise Invalid(f"{where}: the name {one.name!r} is also {twins[0]}'s")
