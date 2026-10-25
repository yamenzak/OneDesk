"""Point 1: the demo company covers every app People gives, each step is
built and written down, and the suite reads it back. These read the code."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "onedesk" / "one_demo"
TOOLS = {"__init__", "base", "build", "check", "history", "samples"}


def _assigned(path: Path, name: str):
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
			return node.value
	raise AssertionError(f"{path.name} has no {name}")


def test_every_step_is_built_and_written_down():
	steps = ast.literal_eval(_assigned(DEMO / "build.py", "STEPS"))
	moved = ast.literal_eval(_assigned(DEMO / "build.py", "MOVED"))
	for step, path in moved.items():
		assert (ROOT / (path.replace(".", "/") + ".py")).exists(), f"{step} moved to {path}, which is missing"
	modules = ({path.stem for path in DEMO.glob("*.py")} - TOOLS) | set(moved)
	assert set(steps) == modules, sorted(set(steps) ^ modules)
	readme = (DEMO / "README.md").read_text()
	listed = re.findall(r"^\| (\w+) \|", readme, flags=re.M)
	assert [one for one in listed if one in modules] == list(steps), "the README's table, in build order"


def test_every_app_people_gives_is_given_to_somebody_in_the_demo():
	source = (ROOT / "onedesk" / "one" / "settings.py").read_text()
	apps = set(re.findall(r'^\t\("(One\w+)", "one\w+",', source, flags=re.M))
	people = ast.literal_eval(_assigned(DEMO / "people.py", "APPS"))
	assert apps and apps <= set(people), sorted(apps - set(people))


def test_the_suite_checks_and_writes_nothing():
	source = "\n".join(path.read_text() for path in [DEMO / "check.py", *sorted((ROOT / "onedesk").glob("*/checks.py"))])
	assert source.count("@check") >= 15
	assert "frappe.db.rollback()" in source and "frappe.db.commit" not in source
