"""The Intake samples in tests/samples/intake, run against the demo company.
Nothing is kept: the suite rolls each sample back.
"""

import json
import re
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

ROOT = Path(frappe.get_app_path("onedesk")).parent / "tests" / "samples" / "intake"

RIGHT = "right"
FIRST = "first"


class Handled(NamedTuple):
	made: list[dict]
	unanswered: list[str]


def samples() -> list[Path]:
	return sorted(ROOT.glob("*/*.json"))


def handle(path: Path, kept: bool = False) -> Handled:
	"""One sample through Intake as it arrives: the Intake Action rows it made,
	and any model call the sample does not answer. Kept, it stays in the demo
	as Intake left it; otherwise each commit is only a savepoint."""
	spec = json.loads(path.read_text())
	content = path.with_name(spec["file"]).read_bytes()
	started = now_datetime()
	unanswered = []
	with _answered(path.name, spec.get("answers") or {}, unanswered), (nullcontext() if kept else unkept()):
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
	made = frappe.get_all(
		"Intake Action",
		filters={"reading": ["in", readings or [""]]},
		fields=["kind", "level", "target_doctype", "target_name", "after", "why"],
		order_by="creation asc",
	)
	return Handled(made, unanswered)


def found(path: Path) -> Handled | None:
	"""What a sample the demo kept made, read back: the Intake Action rows of
	its readings. None when it never arrived."""
	readings = readings_of(path)
	if not readings:
		return None
	made = frappe.get_all(
		"Intake Action",
		filters={"reading": ["in", readings]},
		fields=["kind", "level", "target_doctype", "target_name", "after", "why"],
		order_by="creation asc",
	)
	return Handled(made, [])


def readings_of(path: Path) -> list[str]:
	"""The readings a sample made in the demo, found by the keys Intake gives
	them (one_intake/pipeline.py): a mail by its Message-ID, a file and each
	attachment by its content. Their parts too."""
	from email import message_from_bytes
	from hashlib import md5

	spec = json.loads(path.read_text())
	content = path.with_name(spec["file"]).read_bytes()
	if spec["file"].endswith(".eml"):
		mail = message_from_bytes(content)
		said = (mail.get("Message-ID") or "").strip()
		keys = {f"mail-{md5(one.encode()).hexdigest()}" for one in (said, said.strip("<>")) if one}
		keys |= {md5(part.get_payload(decode=True)).hexdigest() for part in mail.walk() if part.get_filename()}
	else:
		keys = {md5(content).hexdigest()}
	top = frappe.get_all("Reading", filters={"key": ["in", list(keys)]}, pluck="name")
	if not top:
		return []
	return [*top, *frappe.get_all("Reading", filters={"part_of": ["in", top]}, pluck="name")]


def unmet(path: Path, handled: Handled) -> list[str]:
	"""What a sample says Intake makes and it did not, and what Intake asked
	that the sample does not answer."""
	made = handled.made
	out = [f"no answer for {action}" for action in dict.fromkeys(handled.unanswered)]
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
def _answered(sample: str, answers: dict, unanswered: list):
	"""Every model call answered from the sample. One it has no answer for is
	refused and noted, since Intake may carry on without it."""

	def once(action, text, files=None, reference=None):
		said = answers.get(action)
		if said == RIGHT or (isinstance(said, dict) and "wrong" in said):
			ids = re.findall(r'"id": "([^"]+)"', text)
			verdict, why = ("right", "As the document says.") if said == RIGHT else ("wrong", said["wrong"])
			said = {"actions": [{"id": one, "verdict": verdict, "why": why} for one in ids]}
		elif said == FIRST:
			shown = re.findall(r"^- (\S+): ", text, flags=re.M)
			said = {"matter": shown[0] if shown else None}
		if said is None:
			unanswered.append(action)
			raise AssertionError(f"{sample} has no answer for {action}")
		return json.dumps(said)

	with patch("onedesk.one_ai.run.once", once), patch("onedesk.one_intake.pipeline.later", lambda *a, **k: None):
		yield


@contextmanager
def unkept():
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
