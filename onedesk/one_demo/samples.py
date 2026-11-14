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
	"""One sample through Intake as it arrives: the Reading Action rows it made,
	and any model call the sample does not answer. Kept, it stays in the demo
	as Intake left it; otherwise each commit is only a savepoint."""
	spec = _dated(json.loads(path.read_text()))
	content = path.with_name(spec["file"]).read_bytes()
	if spec.get("unpaid", {}).get("now"):
		content = content.replace(spec["unpaid"]["written_as"].encode(), spec["unpaid"]["now"].encode())
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
		from onedesk.one_ai.reading import matters

		for name in readings:
			matters.act_now(name)
	made = frappe.get_all(
		"Reading Action",
		filters={"reading": ["in", readings or [""]]},
		fields=["kind", "level", "target_doctype", "target_name", "after", "why"],
		order_by="creation asc",
	)
	return Handled(made, unanswered)


def _dated(spec: dict) -> dict:
	"""A sample that pays an invoice pays the customer's oldest one still
	unpaid, which moves with the day the demo is built: the invoice it was
	written about is put right in the model's answers, and `handle` puts it
	right in what arrives."""
	asked = spec.get("unpaid")
	if not asked:
		return spec
	now = frappe.get_all(
		"Sales Invoice",
		filters={"customer": asked["customer"], "docstatus": 1, "outstanding_amount": [">", 0]},
		order_by="posting_date asc, name asc",
		pluck="name",
		limit=1,
	)
	if not now:
		return spec
	said = json.loads(json.dumps({key: value for key, value in spec.items() if key != "unpaid"}).replace(asked["written_as"], now[0]))
	return {**said, "unpaid": {**asked, "now": now[0]}}


def found(path: Path) -> Handled | None:
	"""What a sample the demo kept made, read back: the Reading Action rows of
	its readings. None when it never arrived."""
	readings = readings_of(path)
	if not readings:
		return Handled([], []) if message_of(path) else None
	made = frappe.get_all(
		"Reading Action",
		filters={"reading": ["in", readings]},
		fields=["kind", "level", "target_doctype", "target_name", "after", "why"],
		order_by="creation asc",
	)
	return Handled(made, [])


def readings_of(path: Path) -> list[str]:
	"""The readings a sample made in the demo, found by the keys Intake gives
	them (one_ai/reading/pipeline.py): a mail by its Message-ID, a file and each
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


def message_of(path: Path) -> dict | None:
	"""The message a mail sample became in the demo, with what OneMail made
	of its risk (one_mail/held.py), found by its Message-ID. None for a file,
	or a mail that never arrived."""
	from email import message_from_bytes

	spec = json.loads(path.read_text())
	if not spec["file"].endswith(".eml"):
		return None
	said = (message_from_bytes(path.with_name(spec["file"]).read_bytes()).get("Message-ID") or "").strip()
	return frappe.db.get_value(
		"Communication",
		{"message_id": ["in", [said, said.strip("<>")]], "communication_medium": "Email"},
		["name", "one_risk", "one_held", "one_risks"],
		as_dict=True,
	)


def risk_unmet(spec: dict, message: dict | None) -> list[str]:
	"""What a mail sample says OneMail makes of its risk and it did not:
	held or let through, warned or not, which domain it imitates, and every
	signal it must give."""
	want = spec.get("mail")
	if not want:
		return []
	if not message:
		return ["it never arrived"]
	from onedesk.one_mail import held

	said = held.said_of(message) or {}
	found = {one.get("why") for one in (frappe.parse_json(message.get("one_risks") or "{}") or {}).get("found") or []}
	out = []
	if bool(said.get("held")) != bool(want.get("held")):
		out.append(f"held is {bool(said.get('held'))}, not {bool(want.get('held'))}, at {message.get('one_risk')}")
	if bool(said) != bool(want.get("warned")):
		out.append(f"warned is {bool(said)}, not {bool(want.get('warned'))}, at {message.get('one_risk')}")
	if want.get("imitates") and said.get("imitates") != want["imitates"]:
		out.append(f"imitates {said.get('imitates')}, not {want['imitates']}")
	out += [f"no {why} signal: {sorted(found)}" for why in want.get("why") or [] if why not in found]
	if not want.get("why") and found:
		out.append(f"signals {sorted(found)} on a clean message")
	return out


def done_by(stem: str, app: str) -> list[dict]:
	"""What an app's agent did with a sample the demo kept, as its Reading
	Action rows (one_ai/agents/work.py), for each module's check of its agent."""
	from onedesk.one.registry import agents

	path = next(one for one in samples() if one.stem == stem)
	return frappe.get_all(
		"Reading Action",
		filters={"reading": ["in", readings_of(path) or [""]], "agent": agents.email(app)},
		fields=["name", "kind", "level", "target_doctype", "target_name", "agent_action", "agent_level", "why", "on_behalf_of"],
	)


def unmet(path: Path, handled: Handled) -> list[str]:
	"""What a sample says Intake makes and it did not, and what Intake asked
	that the sample does not answer."""
	made = handled.made
	out = [f"no answer for {action}" for action in dict.fromkeys(handled.unanswered)]
	spec = json.loads(path.read_text())
	out += risk_unmet(spec, message_of(path))
	read = frappe.get_all("Reading", filters={"name": ["in", readings_of(path) or [""]]}, fields=["verdict", "state"])
	if spec.get("verdict") and spec["verdict"] not in {one.verdict for one in read}:
		out.append(f"not read as {spec['verdict']}: {sorted({one.verdict or '' for one in read})}")
	for state in spec.get("states") or []:
		if state not in {one.state for one in read}:
			out.append(f"nothing left {state}: {sorted({one.state or '' for one in read})}")
	for want in spec.get("makes") or []:
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
	from onedesk.one_ai.reading import pipeline
	from onedesk.one_demo import intake
	from onedesk.one_demo.base import as_user
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
	refused and noted, since Intake may carry on without it; the check for
	an attack on OneAI (reading/guard.py) is safe unless the sample says."""
	from onedesk.one_ai.reading import guard


	def once(action, text, files=None, reference=None):
		if action == guard.JOB:
			return answers.get(action) or "safe"
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

	def read(action, state, asked, reference=None, on=None):
		"""A reading model (Clef, Clairic) answers from the sample; one with no
		answer is a model that can't answer, so the talk model is asked."""
		if action not in answers:
			raise RuntimeError(f"{sample} has no reading model's answer for {action}")
		return {"answers": answers[action]}

	with (
		patch("onedesk.one_ai.run.once", once),
		patch("onedesk.one_ai.run.read", read),
		patch("onedesk.one_ai.reading.pipeline.later", lambda *a, **k: None),
	):
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
