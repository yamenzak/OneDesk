"""OneRegistry: every app, centre and engine of One, read from the
manifest.py in its own folder (docs/run/RUN.md, OneRegistry). Pure, so
hooks.py, the guards and the scripts read it without a site.

`apps()` in the rail's order, `parts()` (centres inside another's folder), `centres()`,
`get(id)`, `name(id)`, `names()`, `filled(text)` for `{one_doc}`,
`by_name(name)`, `of_module(module)`, and `moved()`, renamed folders."""

import ast
import importlib
import re
from functools import cache
from pathlib import Path

from onedesk.one.registry import credits, features
from onedesk.one.registry.model import CENTRE_KEYS, COUNTRY, KINDS, REGIONS, UI, App

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
def parts() -> tuple[App, ...]:
	"""The centres and engines that live inside another app's folder
	(ControlCenter in One's, OneOS in OneCloud's), each an App in its
	folder's manifest.py `PARTS`. Their names are code as an app's are;
	their module, Help, versions and roles are their folder's app's, so they
	are not in apps()."""
	found = []
	for path in sorted(FOLDERS.glob("*/manifest.py")):
		found += getattr(importlib.import_module(f"onedesk.{path.parent.name}.manifest"), "PARTS", ())
	_check_parts(found, apps())
	return tuple(found)


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
	for one in (*apps(), *parts()):
		if one.id == id:
			return one
	raise KeyError(id)


def name(id: str) -> str:
	return get(id).name


@cache
def names() -> dict[str, str]:
	"""Every app's, centre's and engine's name by its id, its parts' too."""
	return {one.id: one.name for one in (*apps(), *parts())}


SLOT = re.compile(r"\{([a-z][a-z_]*)\}")


def filled(text: str) -> str:
	"""Words that name an app as `{one_doc}` (a Help page, a version, a
	notification's text) with its name put in; any other braces are left as
	they are. Pure."""
	known = names()
	return SLOT.sub(lambda found: known.get(found.group(1), found.group(0)), text or "")


def by_name(name: str) -> App:
	for one in (*apps(), *parts()):
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
			if needed == one.id:
				raise Invalid(f"{where}: needs itself")
		if one.kept is not None:
			_check_kept(one.kept, where)
		_check_market(one, where, FOLDERS / one.id)
		if features.unknown(one.plan):
			raise Invalid(f"{where}: plan names {features.unknown(one.plan)[0]!r}, which is not one of {features.IDS}")
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


def _check_kept(kept, where: str) -> None:
	"""A Kept says why in words, and from when as record types: the rule
	is the reason (docs/run/RUN.md, Decisions), so none goes without one."""
	if not isinstance(kept.why, str) or not kept.why.strip():
		raise Invalid(f"{where}: kept says why the app can't be turned off")
	if not isinstance(kept.when, tuple) or not all(isinstance(one, str) and one for one in kept.when):
		raise Invalid(f"{where}: kept's when is a tuple of record types")


MEDIA = (".png", ".webp", ".gif", ".mp4")
"""What a picture (.png, .webp) or a clip (.gif, .mp4) in an app's media/ may be."""
FEWEST_MEDIA, MOST_MEDIA = 3, 6


def _check_market(one: App, where: str, folder: Path) -> None:
	"""What OneMarketplace shows a buyer: a pitch in words, what it brings
	as a few lines of words, the credits it uses by known kinds, and none or
	3 to 6 pictures and clips that are in its folder's media/."""
	if not isinstance(one.pitch, str):
		raise Invalid(f"{where}: pitch is words")
	if not isinstance(one.brings, tuple) or not all(isinstance(line, str) and line.strip() for line in one.brings):
		raise Invalid(f"{where}: brings is a tuple of lines of words")
	if not isinstance(one.credits, tuple) or credits.unknown(one.credits):
		raise Invalid(f"{where}: credits names {credits.unknown(one.credits or ())[:1]}, which is not one of {credits.IDS}")
	if not isinstance(one.media, tuple) or not all(isinstance(name, str) for name in one.media):
		raise Invalid(f"{where}: media is a tuple of file names")
	if one.media and not FEWEST_MEDIA <= len(one.media) <= MOST_MEDIA:
		raise Invalid(f"{where}: media lists {len(one.media)}; an app shows {FEWEST_MEDIA} to {MOST_MEDIA} pictures and clips, or none")
	for name in one.media:
		if Path(name).suffix.lower() not in MEDIA or Path(name).name != name:
			raise Invalid(f"{where}: media {name!r} is a file name ending in one of {MEDIA}")
	for name in one.media:
		if not (folder / "media" / name).is_file():
			raise Invalid(f"{where}: media {name!r} is not in {one.id}/media/")


def _check_parts(found: list, apps: tuple[App, ...]) -> None:
	taken = {one.id: one.name for one in apps}
	for one in found:
		if not isinstance(one, App) or one.kind not in KINDS or not one.name:
			raise Invalid(f"a part must be an App with a name and a kind of {KINDS}: {one!r}")
		if one.id in taken or one.name in taken.values():
			raise Invalid(f"the part {one.id} ({one.name}) has the id or the name of another")
		taken[one.id] = one.name
	keys = [one.centre.key for one in (*apps, *found) if one.centre]
	if sorted(keys) != sorted(CENTRE_KEYS):
		raise Invalid(f"the centres' keys are {sorted(keys)}, not {sorted(CENTRE_KEYS)}")


def centres() -> tuple[App, ...]:
	"""Every centre that opens in OneInterface's frame, in CENTRE_KEYS' order."""
	found = {one.centre.key: one for one in (*apps(), *parts()) if one.centre}
	return tuple(found[key] for key in CENTRE_KEYS)
