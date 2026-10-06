"""The guard registry holds together: every guard runs somewhere real, every
point has a guard or says which is coming, and no id is used twice."""

import ast
from pathlib import Path

from tests.guards.registry import GUARDS, PLANNED, POINTS

ROOT = Path(__file__).resolve().parents[2]


def _tests_in(path: Path) -> set[str]:
	return {node.name for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}


def test_every_guard_runs_somewhere_real():
	for guard in GUARDS:
		if guard.runs.startswith("cmd: "):
			script = guard.runs.split()[2]
			assert (ROOT / script).exists(), guard.id
			continue
		file, name = guard.runs.split("::")
		assert (ROOT / file).exists(), guard.id
		assert name in _tests_in(ROOT / file), guard.id


def test_every_point_has_a_guard_or_says_which_is_coming():
	guarded = {guard.point for guard in GUARDS}
	for point in POINTS:
		assert point in guarded or point in PLANNED, point
	assert set(PLANNED) <= set(POINTS)


def test_ids_are_unique_and_points_real():
	ids = [guard.id for guard in GUARDS]
	assert len(ids) == len(set(ids))
	assert all(guard.point in POINTS and guard.what for guard in GUARDS)


def test_the_points_are_the_passovers():
	passover = (ROOT / "docs" / "PASSOVER.md").read_text()
	for number, name in POINTS.items():
		assert f"{number}. **{name}" in passover, name
