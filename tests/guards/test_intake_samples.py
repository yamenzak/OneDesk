"""Point 14: every record Intake can make has a real sample that makes it,
and every sample is whole. The demo suite runs them
(`every_intake_sample_left_what_it_should`). These read the files."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402

SAMPLES = ROOT / "tests" / "samples" / "intake"
PLANNERS = ("plans.py", "money.py")


def _samples() -> list[Path]:
	return sorted(SAMPLES.glob("*/*.json"))


def _made() -> set[str]:
	found = set()
	for name in PLANNERS:
		found |= set(re.findall(r'Action\(\s*"Create",\s*"([A-Z][\w ]+)"', (APP / "one_intake" / name).read_text()))
	return found


def _actions() -> set[str]:
	source = "\n".join(path.read_text() for path in (APP / "one_intake").glob("*.py"))
	return set(re.findall(r'"(intake_\w+)"', source))


def test_every_record_intake_makes_has_a_sample():
	covered = {want["doctype"] for path in _samples() for want in json.loads(path.read_text())["makes"]}
	assert _made(), "no planner found"
	assert _made() <= covered, sorted(_made() - covered)


def test_every_sample_is_whole():
	actions = _actions()
	assert _samples(), "there are no Intake samples"
	for path in _samples():
		spec = json.loads(path.read_text())
		assert (APP / path.parent.name).is_dir(), f"{path.parent.name} is not a module"
		assert path.with_name(spec["file"]).exists(), f"{path.name} has no {spec['file']}"
		assert spec["makes"], f"{path.name} says nothing it makes"
		assert set(spec.get("answers") or {}) <= actions, f"{path.name} answers what Intake never asks"
		for want in spec["makes"]:
			assert want.get("level", "Done") in ("Done", "Proposed"), f"{path.name}: {want}"


def test_the_suite_runs_every_sample():
	source = tree.suite()
	assert "def every_intake_sample_left_what_it_should" in source and "samples.samples()" in source
