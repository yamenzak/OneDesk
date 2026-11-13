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


def test_every_answer_carries_its_verdict_through_the_save():
	assert len({doctype for _, doctype in _answers()}) >= 3
	source = DECISION.read_text()
	body = source[source.index("def answer(") :].split("\n\n\n")[0]
	assert "carry(doc, field, verdict)" in body
	assert not re.search(r"doc\.(status|approval_status) = verdict", body)


def test_every_answered_record_sets_the_verdict_again_before_it_validates():
	for _, doctype in _answers():
		hooks = HOOKS[HOOKS.index(f'\t"{doctype}": {{') :].split("\n\t}")[0].split("},")[0]
		validate = re.search(r'"before_validate": "([\w.]+)"', hooks)
		assert validate, doctype
		module, fn = validate.group(1).rsplit(".", 1)
		if module.endswith("decision") and fn == "kept":
			continue
		source = (ROOT / (module.replace(".", "/") + ".py")).read_text()
		assert "decision.kept(doc)" in source[source.index(f"def {fn}(") :].split("\n\n\n")[0], doctype
