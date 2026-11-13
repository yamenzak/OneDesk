"""Point 1: the demo company covers every app People gives, each step is
built and written down, and the suite reads it back. These read the code."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "onedesk" / "one_demo"
TOOLS = {"__init__", "base", "build", "check", "checking", "checks", "firm", "history", "living", "manifest", "samples", "start"}


def _assigned(path: Path, name: str):
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
			return node.value
	raise AssertionError(f"{path.name} has no {name}")


def unwritten(steps, moved: dict, files: set[str], readme: str, there) -> list[str]:
	"""What is wrong with the build's steps against the step files on disk,
	where each moved step went (`there`) and the README's table. Pure."""
	out = [f"{step} moved to {path}, which is missing" for step, path in moved.items() if not there(path)]
	modules = (files - TOOLS) | set(moved)
	if set(steps) != modules:
		out.append(str(sorted(set(steps) ^ modules)))
	listed = re.findall(r"^\| (\w+) \|", readme, flags=re.M)
	if [one for one in listed if one in modules] != list(steps):
		out.append("the README's table, in build order")
	return out


def test_every_step_is_built_and_written_down():
	steps = ast.literal_eval(_assigned(DEMO / "build.py", "STEPS"))
	moved = ast.literal_eval(_assigned(DEMO / "build.py", "MOVED"))
	files = {path.stem for path in DEMO.glob("*.py")}
	readme = (DEMO / "README.md").read_text()
	found = unwritten(steps, moved, files, readme, lambda path: (ROOT / (path.replace(".", "/") + ".py")).exists())
	assert not found, found


GIVEN = "APPS = tuple(app.name for app in registry.apps() if app.roles.user)"


def ungiven(apps: set[str], people: str) -> list[str]:
	"""What people.py misses of giving every app People gives to somebody. Pure."""
	out = [] if apps and GIVEN in people else ["people.py does not give every app People gives"]
	return out + ([] if 'dict.fromkeys(APPS, "Manager")' in people else ["the owner manages every app"])


def test_every_app_people_gives_is_given_to_somebody_in_the_demo():
	from onedesk.one import registry

	apps = {app.name for app in registry.apps() if app.roles.user}
	found = ungiven(apps, (DEMO / "people.py").read_text())
	assert not found, found


def written(check: str, checks: list[str]) -> list[str]:
	"""What the check runner and the modules' checks write beyond rolling back
	and _unsent's hold on the mail queue. Pure."""
	head, _, rest = check.partition("\ndef _unsent(")
	unsent, _, tail = rest.partition("\ndef ")
	source = "\n".join([head, tail, *checks])
	out = [] if "frappe.db.rollback()" in source and "frappe.db.commit" not in source else ["a check commits or never rolls back"]
	writes = re.findall(r"frappe\.db\.(set_default|delete|set_value|sql|insert)\(\s*\"([^\"]+)\"", unsent)
	if {name for _, name in writes} != {"suspend_email_queue", "Email Queue", "Email Queue Recipient"}:
		out.append(f"_unsent writes {writes}")
	if "with _unsent():" not in check.split("\ndef run(", 1)[-1].split("\ndef ", 1)[0]:
		out.append("run is not inside _unsent")
	return out


def test_the_suite_checks_and_writes_nothing():
	"""Each check is rolled back. The one write the run makes is around itself
	(check._unsent): it holds frappe's mail queue while it runs and drops the
	mail its checks queued, which a check that commits would otherwise leave
	to be sent. It writes nothing else."""
	check = (DEMO / "check.py").read_text()
	checks = [path.read_text() for path in sorted((ROOT / "onedesk").glob("*/checks.py"))]
	assert "\n".join(checks).count("@check") >= 15
	found = written(check, checks)
	assert not found, found


def test_the_demo_rules_catch_their_examples():
	readme = "| people | who |\n| stock | what |\n"
	assert unwritten(["people", "stock"], {}, {"people", "stock", "build"}, readme, bool) == []
	assert unwritten(["stock", "people"], {}, {"people", "stock"}, readme, bool) == ["the README's table, in build order"]
	assert unwritten(["people"], {"stock": "onedesk.one_stock.demo"}, {"people"}, readme, lambda path: False)[0].startswith("stock moved")
	assert ungiven({"OneHR"}, GIVEN + '\nOWNER = dict.fromkeys(APPS, "Manager")') == []
	assert ungiven({"OneHR"}, GIVEN) == ["the owner manages every app"]
	runner = '\ndef _unsent():\n\tfrappe.db.delete("Email Queue")\n\ndef run():\n\twith _unsent():\n\t\tfrappe.db.rollback()\n'
	assert written(runner, []) == [f"_unsent writes {[('delete', 'Email Queue')]}"]
	assert "a check commits or never rolls back" in written(runner, ["frappe.db.commit()"])
