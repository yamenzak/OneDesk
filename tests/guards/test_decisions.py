"""Point 15: an answer is the answer given. frappe puts back any field the
person may not write at its level, and the approver a record names often
holds no HR role, so a Reject saved plainly came back as unanswered and the
submit read it as a yes. These read the code."""

import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import tree  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HR = ROOT / "onedesk" / "one_hr"
HOOKS = tree.hooks()


DECISION = HR / "decision.py"


def _answers():
	"""Every record One's own Approve and Reject answer, by decision.answer."""
	for path in HR.glob("*.py"):
		for doctype in re.findall(r'decision\.answer\(\s*"([^"]+)"', path.read_text()):
			yield path, doctype


def carries(decision: str) -> bool:
	"""Whether decision.answer carries the verdict rather than setting it plainly. Pure."""
	body = decision[decision.index("def answer(") :].split("\n\n\n")[0]
	return "carry(doc, field, verdict)" in body and not re.search(r"doc\.(status|approval_status) = verdict", body)


def test_every_answer_carries_its_verdict_through_the_save():
	assert len({doctype for _, doctype in _answers()}) >= 3
	assert carries(DECISION.read_text())


def kept_again(doctype: str, hooks: str, read) -> bool:
	"""Whether the record's before_validate hook is decision.kept or calls it;
	`read` gives a hook module's source by its dotted name. Pure but for `read`."""
	block = hooks[hooks.index(f'\t"{doctype}": {{') :].split("\n\t}")[0].split("},")[0]
	validate = re.search(r'"before_validate": "([\w.]+)"', block)
	if not validate:
		return False
	module, fn = validate.group(1).rsplit(".", 1)
	if module.endswith("decision") and fn == "kept":
		return True
	source = read(module)
	return "decision.kept(doc)" in source[source.index(f"def {fn}(") :].split("\n\n\n")[0]


def test_every_answered_record_sets_the_verdict_again_before_it_validates():
	for _, doctype in _answers():
		assert kept_again(doctype, HOOKS, lambda module: (ROOT / (module.replace(".", "/") + ".py")).read_text()), doctype


def test_the_decision_rules_catch_their_examples():
	assert carries("def answer(doc, field, verdict):\n\tcarry(doc, field, verdict)\n")
	assert not carries("def answer(doc, field, verdict):\n\tdoc.status = verdict\n")
	hooks = '\t"Leave Application": {\n\t\t"before_validate": "onedesk.one_hr.away.held",\n\t},\n\t"Expense Claim": {\n\t},'
	held = "def held(doc, method=None):\n\tdecision.kept(doc)\n"
	assert kept_again("Leave Application", hooks, lambda module: held)
	assert not kept_again("Leave Application", hooks, lambda module: "def held(doc, method=None):\n\tpass\n")
	assert not kept_again("Expense Claim", hooks, lambda module: held)
