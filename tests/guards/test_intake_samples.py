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
		found |= set(re.findall(r'Action\(\s*"Create",\s*"([A-Z][\w ]+)"', (APP / "one_ai" / "reading" / name).read_text()))
	return found


def _actions() -> set[str]:
	source = "\n".join(path.read_text() for path in (APP / "one_ai" / "reading").glob("*.py"))
	return set(re.findall(r'"(intake_\w+)"', source))


def unsampled(made: set[str], specs: list[dict]) -> list[str]:
	"""The record types Intake makes that no sample makes. Pure."""
	return sorted(made - {want["doctype"] for spec in specs for want in spec["makes"]})


def test_every_record_intake_makes_has_a_sample():
	assert _made(), "no planner found"
	missing = unsampled(_made(), [json.loads(path.read_text()) for path in _samples()])
	assert not missing, missing


def unwhole(name: str, spec: dict, module: bool, file: bool, actions: set[str]) -> list[str]:
	"""What a sample lacks: a module of its folder's name, its file, what it
	makes or is, answers Intake asks, and levels it knows. Pure."""
	out = [] if module else [f"{name}'s folder is not a module"]
	out += [] if file else [f"{name} has no {spec['file']}"]
	out += [] if spec["makes"] or spec.get("verdict") or spec.get("states") or spec.get("mail") else [f"{name} says nothing it makes or is"]
	out += [] if set(spec.get("answers") or {}) <= actions else [f"{name} answers what Intake never asks"]
	return out + [f"{name}: {want}" for want in spec["makes"] if want.get("level", "Done") not in ("Done", "Proposed")]


def test_every_sample_is_whole():
	actions = _actions()
	assert _samples(), "there are no Intake samples"
	for path in _samples():
		spec = json.loads(path.read_text())
		found = unwhole(path.name, spec, (APP / path.parent.name).is_dir(), path.with_name(spec["file"]).exists(), actions)
		assert not found, found


def runs_the_samples(suite: str) -> bool:
	return "def every_intake_sample_left_what_it_should" in suite and "samples.samples()" in suite


def test_the_suite_runs_every_sample():
	assert runs_the_samples(tree.suite())


def test_the_sample_rules_catch_their_examples():
	spec = {"file": "bill.pdf", "makes": [{"doctype": "Purchase Invoice", "level": "Maybe"}], "answers": {"intake_who": 1}}
	assert unsampled({"Purchase Invoice", "Lead"}, [spec]) == ["Lead"]
	found = unwhole("bill.json", spec, False, False, set())
	assert len(found) == 4 and "says nothing" not in " ".join(found)
	assert unwhole("bill.json", {**spec, "makes": [{"doctype": "Lead"}]}, True, True, {"intake_who"}) == []
	assert unwhole("mail.json", {"file": "mail.eml", "makes": [], "mail": {"held": True}}, True, True, set()) == []
	assert not runs_the_samples("def every_intake_sample_left_what_it_should():\n\tpass\n")
