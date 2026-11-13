"""Point 17: a module keeps one layout. Who is told lives in its tell.py,
what OneAI reads and offers in its agent.py (or ai_<topic>.py), the rights it
gives roles in access.py, its clauses in trust.py, and the long form in its
README.
These read the code."""

import ast
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import tree  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
TELL = "tell.py"
ACCESS = "access.py"
DOORS = {APP / "one" / "notify.py", APP / "one" / "roles.py"}
WRITERS = ("add_permission", "update_permission_property")


def _python():
	return [path for path in sorted(APP.rglob("*.py")) if path not in DOORS]


def _calls(path: Path, owner: str, names: tuple[str, ...]) -> list[int]:
	return [
		node.lineno
		for node in ast.walk(ast.parse(path.read_text()))
		if isinstance(node, ast.Call)
		and isinstance(node.func, ast.Attribute)
		and node.func.attr in names
		and isinstance(node.func.value, ast.Name)
		and node.func.value.id == owner
	]


def test_notifications_go_out_from_tell():
	outside = [
		f"{path.relative_to(ROOT)}:{line}"
		for path in _python()
		if path.name != TELL and APP / "notifications" not in path.parents
		for line in _calls(path, "notify", ("notify", "mail"))
	]
	assert not outside, outside


def test_oneai_hooks_point_at_ai_files():
	wrong = []
	for node in ast.parse(tree.hooks()).body:
		name = isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "")
		if not name or not name.startswith("one_ai_"):
			continue
		for path in {one.value for one in ast.walk(node.value) if isinstance(one, ast.Constant) and str(one.value).startswith("onedesk.")}:
			module = path.rsplit(".", 2)[-2]
			if module != "agent" and not module.startswith("ai_"):
				wrong.append(f"{name}: {path}")
	assert not wrong, wrong


def _writes(path: Path) -> list[int]:
	return [
		node.lineno
		for node in ast.walk(ast.parse(path.read_text()))
		if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) in WRITERS
	]


def test_roles_are_given_in_access():
	outside = [
		f"{path.relative_to(ROOT)}:{line}"
		for path in _python()
		if path.name != ACCESS
		for line in _calls(path, "roles", ("give", "grant", "raise_once", "open_page")) + _writes(path)
	]
	assert not outside, outside


def test_the_scans_would_catch_one(tmp_path):
	stray = tmp_path / "stray.py"
	stray.write_text("from onedesk.one import notify\n\ndef x():\n\tnotify.notify('A', 'b')\n")
	assert _calls(stray, "notify", ("notify", "mail")) == [4]
	stray.write_text("from frappe.permissions import add_permission\n\ndef x():\n\tadd_permission('Note', 'A', 0)\n")
	assert _writes(stray) == [4]
