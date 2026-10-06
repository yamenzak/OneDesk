"""Point 17: a module keeps one layout. Who is told lives in its tell.py,
what OneAI reads and offers in its ai.py (or ai_<topic>.py), its clauses in
legal.py, and the long form in its README.
These read the code."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
#: Where a module's notifications go out from.
TELL = "tell.py"
#: The door itself.
DOORS = {APP / "one" / "notify.py"}


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
	for node in ast.parse((APP / "hooks.py").read_text()).body:
		name = isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "")
		if not name or not name.startswith("one_ai_"):
			continue
		for path in {one.value for one in ast.walk(node.value) if isinstance(one, ast.Constant) and str(one.value).startswith("onedesk.")}:
			module = path.rsplit(".", 2)[-2]
			if module != "ai" and not module.startswith("ai_"):
				wrong.append(f"{name}: {path}")
	assert not wrong, wrong


def test_the_scans_would_catch_one(tmp_path):
	stray = tmp_path / "stray.py"
	stray.write_text("from onedesk.one import notify\n\ndef x():\n\tnotify.notify('A', 'b')\n")
	assert _calls(stray, "notify", ("notify", "mail")) == [4]
