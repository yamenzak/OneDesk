"""OneRegistry (onedesk/one/registry): every folder's manifest loads, what
hooks.py builds from it points at code that is there, and a manifest that
says something wrong is refused by name."""

import ast
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onedesk.one import registry  # noqa: E402
from onedesk.one.registry import hooks  # noqa: E402

FOLDERS = sorted(
	path.parent.name
	for path in (ROOT / "onedesk").glob("*/__init__.py")
	if (path.parent.name == "one" or path.parent.name.startswith("one_") or path.parent.name.endswith("_center")) and path.parent.name not in registry.moved()
)


def test_every_folder_has_a_manifest():
	assert sorted(one.id for one in registry.apps()) == FOLDERS


def test_a_folder_kept_after_a_rename_is_not_an_app():
	for old, now in registry.moved().items():
		modules = (ROOT / "onedesk" / "modules.txt").read_text().splitlines()
		assert old not in {one.strip().lower().replace(" ", "_") for one in modules}, old
		assert [path.name for path in (ROOT / "onedesk" / old).iterdir() if path.name != "__pycache__"] == ["__init__.py"], old
		assert (ROOT / now.replace(".", "/") / "manifest.py").exists(), now


def test_names_are_read_from_the_manifest():
	assert registry.name("one_book") == "OneBook" and registry.by_name("OneBook").id == "one_book"
	assert registry.of_module("Stock").id == "one_inventory"


def _defined(dotted: str) -> bool:
	"""Whether a dotted path is a module of ours, or a name a module of ours
	defines at its top level."""
	parts = dotted.split(".")
	for cut in range(len(parts), 0, -1):
		path = ROOT.joinpath(*parts[:cut]).with_suffix(".py")
		if path.exists():
			rest = parts[cut:]
			if not rest:
				return True
			names = {
				getattr(node, "name", None) or getattr(getattr(node, "targets", [None])[0], "id", None)
				for node in ast.parse(path.read_text(encoding="utf-8")).body
			}
			return len(rest) == 1 and rest[0] in names
	return False


@pytest.mark.parametrize("name", [*hooks.CONVENTIONS, "one_record_tabs", "one_homes", "one_deck_rows"])
def test_every_entry_a_hook_is_given_is_there(name):
	missing = [entry for entry in hooks.hook(name) if not _defined(entry)]
	assert hooks.hook(name) and not missing, missing


def test_every_settle_step_is_there():
	steps = hooks.settles(install=True)
	assert len(steps) > 40 and not [one for one in steps if not _defined(one)]
	assert set(hooks.settles(install=False)) < set(steps), "install-only steps run at install alone"


def test_one_settles_first_and_what_reads_everything_last():
	steps = hooks.settles(install=True)
	assert steps[0] == "onedesk.one.roles.ensure"
	assert steps[-1] == "onedesk.one.companions.apply"


@pytest.mark.parametrize(
	"change, said",
	[
		({"kind": "widget"}, "kind"),
		({"ui": "pretty"}, "ui"),
		({"needs": ("one_nowhere",)}, "needs"),
		({"countries": {"AE": "maybe"}}, "countries"),
		({"owns": ("Stock",)}, "owns"),
		({"name": "OneMail"}, "name"),
	],
)
def test_a_wrong_manifest_is_refused_by_name(change, said):
	apps = list(registry.apps())
	book = next(one for one in apps if one.id == "one_book")
	apps[apps.index(book)] = replace(book, **change)
	with pytest.raises(registry.Invalid, match=said):
		registry._check(apps)


def test_every_mark_is_drawn():
	"""A manifest's mark is a file in brand/, which scripts/icons.py makes
	into the Custom Icon the rail and the marks draw."""
	missing = [f"{one.id}: {one.mark}" for one in registry.apps() if one.mark and not (ROOT / "brand" / f"{one.mark}.svg").exists()]
	assert not missing, missing


def test_the_dock_and_the_module_list_are_the_registrys():
	"""The Dock fixture and modules.txt are written by scripts/docs.py from
	the manifests; docs.py --check fails when either drifts."""
	import json

	rows = json.loads((ROOT / "onedesk" / "dock" / "onedesk" / "onedesk.json").read_text())["items"]
	assert [row["title"] for row in rows] == [one.name for one in registry.apps() if one.rail is not None]
	listed = (ROOT / "onedesk" / "modules.txt").read_text().split()
	assert " ".join(listed) == " ".join(one.module for one in registry.apps() if one.module)


ALLOWED = {
	"onedesk/one_admin/setup.py": "Cloudflare token names, which share apps' names",
	"onedesk/one_ai/groups.py": "the tool group of each app's records, until P8 gives each app its agent",
	"onedesk/one_ai/yours.py": "the marks drawn beside a reading; P2.11 turns names into ids",
}
"""Where a literal may still name two apps, and why."""


def _named_twice(path: Path, names: set) -> list[int]:
	lines = []
	for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
		elts = node.elts if isinstance(node, ast.List | ast.Tuple | ast.Set) else node.keys if isinstance(node, ast.Dict) else None
		said = [one.value for one in elts or () if isinstance(one, ast.Constant) and isinstance(one.value, str)]
		if sum(one in names for one in said) >= 2:
			lines.append(node.lineno)
	return lines


def _apps_named() -> set:
	return ({one.name for one in registry.apps()} | {one.id for one in registry.apps()}) - {"one", "One", "Demo"}


def test_no_list_of_apps_is_typed_outside_the_registry():
	"""A list, tuple, set or dict that names two apps, by name or folder, is a
	second copy of the registry. Manifests, tests, checks, patches and the
	demo's data may; ALLOWED says why the rest may."""
	names = _apps_named()
	found = {}
	for path in sorted((ROOT / "onedesk").rglob("*.py")):
		where = str(path.relative_to(ROOT))
		if path.name in ("manifest.py", "checks.py") or {"tests", "patches", "one_demo"} & set(path.parts) or where in ALLOWED:
			continue
		lines = _named_twice(path, names)
		if lines:
			found[where] = lines
	assert not found, f"say it in the apps' manifests instead (onedesk/one/registry): {found}"


def test_the_list_guard_catches_its_example(tmp_path):
	example = tmp_path / "example.py"
	example.write_text('APPS = ("OneBook", "OneHR")\n')
	assert _named_twice(example, _apps_named()) == [1]


def test_each_page_is_a_region_of_the_app_whose_folder_holds_it():
	"""How an app's screens are made is declared (`ui`): a native app is
	frappe's own lists and forms but for its regions, so every page of ours is
	a region in the manifest of the folder it lives in, and no other's."""
	for path in sorted((ROOT / "onedesk").glob("*/page/*/*.json")):
		owner = registry.get(path.parts[-4])
		assert path.parent.name.replace("_", "-") in {one.name for one in owner.regions}, f"{owner.id}/manifest.py: no region for page {path.parent.name}"
	assert all(one.ui != "none" for one in registry.apps() if one.kind == "app")
