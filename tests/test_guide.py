"""OneAI answers "how do I…" from the modules' own READMEs, and only the part
of each written for the people using it."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

GUIDE = tree.APP / "one_ai" / "guide.py"


def _pure():
	space = {"re": __import__("re")}
	for node in ast.parse(GUIDE.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "BACKSTAGE":
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in ("split", "ranked"):
			exec(ast.unparse(node), space)
	return space


README = """# OneHR

Intro line.

## Clocking in

Press the dot in the rail.

### Attendance settings

Allow Employees to Check In Themselves.

## Leave

Approve or Reject.

## Under the hood

`clock.py` writes the check-in.
"""


def test_a_readme_is_split_by_heading_and_stops_under_the_hood():
	said = _pure()["split"](README)
	paths = [one["path"] for one in said]
	assert paths == ["OneHR", "OneHR › Clocking in", "OneHR › Clocking in › Attendance settings", "OneHR › Leave"]
	assert not any("clock.py" in one["text"] for one in said)


def test_a_heading_outranks_a_mention():
	space = _pure()
	found = space["ranked"](space["split"](README), ["leave"])
	assert found[0]["path"] == "OneHR › Leave"
	assert space["ranked"](space["split"](README), ["payroll"]) == []


def test_every_module_readme_has_something_for_its_readers():
	for readme in sorted(tree.APP.glob("*/README.md")):
		text = readme.read_text(encoding="utf-8")
		assert text.startswith("# "), f"{readme} has no title"
		above = text.split("## Under the hood", 1)[0]
		assert above.count("\n## ") >= 3, f"{readme} says little to the people using it"


def test_how_to_is_a_read():
	tools = (tree.APP / "one_ai" / "tools.py").read_text(encoding="utf-8")
	reads = tools[tools.index("READS = (") : tools.index("SUGGESTS = (")]
	assert "guide.how_to" in reads


def test_the_words_every_question_has_are_not_matched():
	source = GUIDE.read_text(encoding="utf-8")
	assert "if word not in ASKING" in source
	space = {}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "ASKING":
			exec(ast.unparse(node), space)
	assert {"how", "the", "who", "can"} <= space["ASKING"]
