"""The Intake samples in tests/samples/intake, run against the demo company.
Nothing is kept: the suite rolls each sample back.
"""

import json
import re
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

ROOT = Path(frappe.get_app_path("onedesk")).parent / "tests" / "samples" / "intake"

#: An auditor's answer a sample may give as a word: every action shown is right.
RIGHT = "right"


def samples() -> list[Path]:
	return sorted(ROOT.glob("*/*.json"))


def handle(path: Path) -> list[dict]:
	"""One sample through Intake as it arrives: the Intake Action rows it made."""
	spec = json.loads(path.read_text())
	content = path.with_name(spec["file"]).read_bytes()
	started = now_datetime()
	with _answered(path.name, spec.get("answers") or {}), _unkept():
		_arrive(spec["file"], content)
		readings = frappe.get_all(
			"Reading",
			filters={"creation": [">=", started], "state": "Understood"},
			order_by="creation asc",
			pluck="name",
		)
		from onedesk.one_intake import matters

		for name in readings:
			matters.act_now(name)
	return frappe.get_all(
		"Intake Action",
		filters={"reading": ["in", readings or [""]]},
		fields=["kind", "level", "target_doctype", "target_name", "after", "why"],
		order_by="creation asc",
	)


def unmet(path: Path, made: list[dict]) -> list[str]:
	"""What a sample says Intake makes and it did not."""
	out = []
	for want in json.loads(path.read_text()).get("makes") or []:
		found = [
			one
			for one in made
			if one.target_doctype == want["doctype"]
			and one.kind == want.get("kind", "Create")
			and one.level == want.get("level", "Done")
		]
		if not found:
			out.append(f"no {want.get('kind', 'Create')} {want['doctype']} ({want.get('level', 'Done')})")
			continue
		values = want.get("values") or {}
		if values and not any(_holds(one, values) for one in found):
			out.append(f"{want['doctype']} without {values}")
	return out


def _holds(row, values: dict) -> bool:
	if row.target_name and frappe.db.exists(row.target_doctype, row.target_name):
		held = frappe.db.get_value(row.target_doctype, row.target_name, list(values), as_dict=True)
	else:
		held = json.loads(row.after or "{}")
	return all(str(held.get(key) or "") == str(value) for key, value in values.items())


def _arrive(name: str, content: bytes) -> None:
	from onedesk.one_demo import intake
	from onedesk.one_demo.base import as_user
	from onedesk.one_intake import pipeline
	from onedesk.one_mail import inbound

	if name.endswith(".eml"):
		made = inbound.Arrival(content, frappe.get_doc("Email Account", intake.mailbox())).process()
		pipeline.read_mail(made.name)
		return
	with as_user(intake.ACCOUNTS):
		doc = frappe.get_doc({"doctype": "File", "file_name": name, "folder": intake.folder(), "content": content, "is_private": 1})
		doc.insert()
	pipeline.read_file(doc.name)


@contextmanager
def _answered(sample: str, answers: dict):
	"""Every model call answered from the sample, and one it has no answer for
	refused, so a sample says everything Intake asked about it."""

	def once(action, text, files=None, reference=None):
		said = answers.get(action)
		if said == RIGHT:
			ids = re.findall(r'"id": "([^"]+)"', text)
			said = {"actions": [{"id": one, "verdict": "right", "why": "As the document says."} for one in ids]}
		if said is None:
			raise AssertionError(f"{sample} has no answer for {action}")
		return json.dumps(said)

	with patch("onedesk.one_ai.run.once", once), patch("onedesk.one_intake.pipeline.later", lambda *a, **k: None):
		yield


@contextmanager
def _unkept():
	"""Intake commits as it goes. Here each commit is a savepoint inside the
	sample, and a rollback of its own goes back to its last commit."""
	db = frappe.db
	commit, rollback = db.commit, db.rollback
	db.savepoint("intake_commit")
	db.commit = lambda *a, **k: db.savepoint("intake_commit")
	db.rollback = lambda *a, save_point=None, **k: rollback(save_point=save_point or "intake_commit")
	try:
		yield
	finally:
		db.commit, db.rollback = commit, rollback
