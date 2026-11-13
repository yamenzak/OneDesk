"""The guard registry holds together. Every guard runs somewhere real in
tests/guards, and so does the proof that it catches its example; every rule
has that proof or says why it cannot; every test in tests/guards is a rule or
a rule's proof, so none checks something no point owns; every point of the
standard has a guard, a look or says which is coming, and no id is used
twice."""

import ast
import re
from pathlib import Path

from onedesk.one.standard import Point
from tests.guards.registry import GUARDS, PLANNED, POINTS, Guard

ROOT = Path(__file__).resolve().parents[2]


def _tests_in(path: Path) -> set[str]:
	return {node.name for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}


def unreal(guards, tests: dict[str, set[str]], scripts: set[str]) -> list[str]:
	"""The guards whose rule or proof names a test that is not there, given
	each test file's tests and the scripts that exist. Pure."""
	out = []
	for guard in guards:
		for runs in filter(None, (guard.runs, guard.proof)):
			if runs.startswith("cmd: "):
				if runs.split()[2] not in scripts:
					out.append(f"{guard.id}: {runs}")
				continue
			file, name = runs.split("::")
			if not file.startswith("tests/guards/") or name not in tests.get(file, set()):
				out.append(f"{guard.id}: {runs}")
	return out


def test_every_guard_runs_somewhere_real():
	files = {runs.split("::")[0] for guard in GUARDS for runs in (guard.runs, guard.proof) if "::" in runs}
	tests = {file: _tests_in(ROOT / file) for file in files if (ROOT / file).exists()}
	scripts = {runs.split()[2] for guard in GUARDS for runs in (guard.runs, guard.proof) if runs.startswith("cmd: ") and (ROOT / runs.split()[2]).exists()}
	assert not unreal(GUARDS, tests, scripts)


def test_a_guard_naming_what_is_not_there_is_caught():
	tests = {"tests/guards/test_a.py": {"test_a", "test_b"}}
	good = Guard("good", 1, "x", "tests/guards/test_a.py::test_a", "tests/guards/test_a.py::test_b")
	command = Guard("command", 1, "x", "cmd: python3 scripts/a.py --check", "tests/guards/test_a.py::test_b")
	gone = Guard("gone", 1, "x", "tests/guards/test_a.py::test_c")
	outside = Guard("outside", 1, "x", "tests/test_a.py::test_a")
	proof_gone = Guard("proof-gone", 1, "x", "tests/guards/test_a.py::test_a", "tests/guards/test_b.py::test_a")
	script_gone = Guard("script-gone", 1, "x", "cmd: python3 scripts/b.py --check")
	found = unreal([good, command, gone, outside, proof_gone, script_gone], tests, {"scripts/a.py"})
	assert [line.split(":")[0] for line in found] == ["gone", "outside", "proof-gone", "script-gone"]


def unproven(guards) -> list[str]:
	"""The guards with neither a proof that they catch their example nor a
	word on why they cannot have one. Pure."""
	return [guard.id for guard in guards if not guard.proof and not guard.why.strip()]


def test_every_rule_has_a_proof_or_says_why_not():
	assert not unproven(GUARDS), "write the test that feeds each a bad example, or say why it cannot have one: " + ", ".join(unproven(GUARDS))


def test_a_rule_with_no_proof_and_no_why_is_caught():
	proved = Guard("proved", 1, "x", "tests/guards/a.py::test_a", "tests/guards/a.py::test_b")
	said = Guard("said", 1, "x", "tests/guards/a.py::test_a", why="it compares two generated files")
	bare = Guard("bare", 1, "x", "tests/guards/a.py::test_a")
	blank = Guard("blank", 1, "x", "tests/guards/a.py::test_a", why=" ")
	assert unproven([proved, said, bare, blank]) == ["bare", "blank"]


def unplaced(tests: set[str], guards) -> set[str]:
	"""The tests that are neither a guard's rule nor its proof. Pure."""
	return tests - {guard.runs for guard in guards} - {guard.proof for guard in guards}


def test_every_guard_test_is_a_rule_or_its_proof():
	tests = {
		f"tests/guards/{path.name}::{name}"
		for path in sorted((ROOT / "tests" / "guards").glob("test_*.py"))
		for name in _tests_in(path)
		if name.startswith("test_")
	}
	assert not unplaced(tests, GUARDS), "register these in tests/guards/registry.py under the point they serve: " + ", ".join(
		sorted(unplaced(tests, GUARDS))
	)


def test_a_test_no_rule_owns_is_caught():
	example = Guard("x", 1, "x", "tests/guards/a.py::test_a", "tests/guards/a.py::test_b")
	assert unplaced({"tests/guards/a.py::test_a", "tests/guards/a.py::test_b", "tests/guards/a.py::test_c"}, [example]) == {
		"tests/guards/a.py::test_c"
	}


def unheld(guards, points: dict, planned: dict) -> list[str]:
	"""The points with no guard, no look and nothing planned, and anything
	planned for a point the standard does not have. Pure."""
	guarded = {guard.point for guard in guards}
	out = [point.title for number, point in points.items() if number not in guarded and not point.look and number not in planned]
	return out + [f"planned for {number}" for number in planned if number not in points]


def test_every_point_has_a_guard_a_look_or_says_which_is_coming():
	assert not unheld(GUARDS, POINTS, PLANNED)


def clashes(guards, points: dict) -> list[str]:
	"""Ids used twice, and guards naming no real point or saying nothing. Pure."""
	ids = [guard.id for guard in guards]
	out = sorted({one for one in ids if ids.count(one) > 1})
	return out + [guard.id for guard in guards if guard.point not in points or not guard.what]


def test_ids_are_unique_and_points_real():
	assert not clashes(GUARDS, POINTS)


def _points(*looks: str) -> dict:
	return {number: Point(number, f"p{number}", f"Point {number}", "Group", look=look) for number, look in enumerate(looks, 1)}


def test_a_point_unheld_or_an_id_twice_is_caught():
	points = _points("", "", "a look")
	guards = [Guard("a", 1, "x", "t"), Guard("a", 9, "x", "t"), Guard("b", 1, "", "t")]
	assert unheld(guards, points, {}) == ["Point 2"]
	assert unheld(guards, points, {2: "coming", 7: "coming"}) == ["planned for 7"]
	assert clashes(guards, points) == ["a", "a", "b"]


def misheaded(said: str, points: dict) -> list[str]:
	"""Where docs/STANDARD.md heads a point other than standard.py names it,
	puts it under another group, or does not say how it is held. Pure."""
	heads = re.findall(r"^### (\d+)\. (.+)$", said, re.M)
	if heads != [(str(number), point.title) for number, point in points.items()]:
		return ["the headings are not the points, in their order"]
	out = []
	for number, point in points.items():
		section = said.split(f"### {number}. ", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
		before = said.split(f"\n### {number}. ", 1)[0]
		if re.findall(r"^## (.+)$", before, re.M)[-1] != point.group:
			out.append(f"{point.title} sits under another group than {point.group}")
		if "Held by" not in section:
			out.append(f"{point.title} does not say what holds it")
		elif point.look and "look" not in section.split("Held by", 1)[1]:
			out.append(f"{point.title}: say it has a look")
	return out


def test_the_points_are_the_standards():
	"""docs/STANDARD.md heads each point as standard.py names it, in its
	order and under its group, and says how a point with a look is held."""
	assert not misheaded((ROOT / "docs" / "STANDARD.md").read_text(), POINTS)


def test_a_standard_out_of_step_is_caught():
	points = _points("", "a look")
	good = "## Group\n\n### 1. Point 1\n\nHeld by a rule.\n\n### 2. Point 2\n\nHeld by a look.\n"
	assert misheaded(good, points) == []
	assert misheaded(good.replace("### 2. Point 2", "### 2. Point Two"), points) == ["the headings are not the points, in their order"]
	assert misheaded(good.replace("Held by a look.", "Held by a rule."), points) == ["Point 2: say it has a look"]
	assert misheaded(good.replace("Held by a rule.", "Kept."), points) == ["Point 1 does not say what holds it"]
	assert misheaded("## Other\n\n" + good.split("\n\n", 1)[1], points)[0] == "Point 1 sits under another group than Group"
