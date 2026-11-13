"""The guard registry holds together. Every guard runs somewhere real in
tests/guards, and so does the proof that it catches its example where it has
one; every test in tests/guards is a rule or a rule's proof, so none checks
something no point owns; every point of the standard has a guard, a look or
says which is coming, and no id is used twice."""

import ast
import re
from pathlib import Path

from tests.guards.registry import GUARDS, PLANNED, POINTS

ROOT = Path(__file__).resolve().parents[2]


def _tests_in(path: Path) -> set[str]:
	return {node.name for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}


def _real(guard, runs: str) -> None:
	file, name = runs.split("::")
	assert file.startswith("tests/guards/"), f"{guard.id} lives outside tests/guards"
	assert (ROOT / file).exists(), guard.id
	assert name in _tests_in(ROOT / file), f"{guard.id}: {runs}"


def test_every_guard_runs_somewhere_real():
	for guard in GUARDS:
		if guard.proof:
			_real(guard, guard.proof)
		if guard.runs.startswith("cmd: "):
			script = guard.runs.split()[2]
			assert (ROOT / script).exists(), guard.id
			continue
		_real(guard, guard.runs)


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
	example = type(GUARDS[0])("x", 1, "x", "tests/guards/a.py::test_a", "tests/guards/a.py::test_b")
	assert unplaced({"tests/guards/a.py::test_a", "tests/guards/a.py::test_b", "tests/guards/a.py::test_c"}, [example]) == {
		"tests/guards/a.py::test_c"
	}


def test_every_point_has_a_guard_a_look_or_says_which_is_coming():
	guarded = {guard.point for guard in GUARDS}
	for number, point in POINTS.items():
		assert number in guarded or point.look or number in PLANNED, point.title
	assert set(PLANNED) <= set(POINTS)


def test_ids_are_unique_and_points_real():
	ids = [guard.id for guard in GUARDS]
	assert len(ids) == len(set(ids))
	assert all(guard.point in POINTS and guard.what for guard in GUARDS)


def test_the_points_are_the_standards():
	"""docs/STANDARD.md heads each point as standard.py names it, in its
	order and under its group, and says how a point with a look is held."""
	said = (ROOT / "docs" / "STANDARD.md").read_text()
	heads = re.findall(r"^### (\d+)\. (.+)$", said, re.M)
	assert heads == [(str(number), point.title) for number, point in POINTS.items()]
	for number, point in POINTS.items():
		section = said.split(f"### {number}. ", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
		before = said.split(f"\n### {number}. ", 1)[0]
		assert re.findall(r"^## (.+)$", before, re.M)[-1] == point.group, f"{point.title} sits under {point.group}"
		assert "Held by" in section, point.title
		assert not point.look or "look" in section.split("Held by", 1)[1], f"{point.title}: say it has a look"
