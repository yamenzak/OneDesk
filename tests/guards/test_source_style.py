"""Comments earn their place, and nothing dead ships (point 17).

A comment says why in a line or two; a docstring says what a file or function
is for. The long form is the module README's, under Under the hood.
"""

import ast
import re
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

LONGEST_BLOCK = 3

LONGEST_DOCSTRING = 8

DENSEST = 0.40


def _python_comment_runs(path: Path) -> list[int]:
	runs, current, last = [], 0, -2
	with path.open("rb") as handle:
		for token in tokenize.tokenize(handle.readline):
			if token.type != tokenize.COMMENT:
				continue
			current = current + 1 if token.start[0] == last + 1 else 1
			last = token.start[0]
			runs.append(current)
	return runs


def _may_hold_a_block(text: str) -> bool:
	"""Whether more than LONGEST_BLOCK lines in a row hold a `#`, which a
	block of comments needs: a file without is not tokenized."""
	run = 0
	for line in text.split("\n"):
		run = run + 1 if "#" in line else 0
		if run > LONGEST_BLOCK:
			return True
	return False


def test_no_comment_block_is_an_essay():
	long_ones = []
	for path in tree.scoped(tree.python()):
		if _may_hold_a_block(tree.text(path)) and max(_python_comment_runs(path), default=0) > LONGEST_BLOCK:
			long_ones.append(str(path.relative_to(tree.ROOT)))
	assert not long_ones, (
		f"comment blocks over {LONGEST_BLOCK} lines in {long_ones} — "
		"say why in a line or two, and put the long form in the commit message"
	)


def _long_docstrings(path: Path) -> list[str]:
	out = []
	for node in tree.walked(path):
		if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
			doc = ast.get_docstring(node, clean=False)
			if doc and doc.count("\n") + 1 > LONGEST_DOCSTRING:
				out.append(getattr(node, "name", "module"))
	return out


def test_no_docstring_is_an_essay():
	long_ones = [
		f"{path.relative_to(tree.ROOT)}: {name}" for path in tree.scoped(tree.python()) for name in _long_docstrings(path)
	]
	assert not long_ones, (
		f"docstrings over {LONGEST_DOCSTRING} lines in {long_ones}: say what it is for, "
		"and put the rest in the module's README under Under the hood"
	)


def _comment_and_code(text: str) -> tuple[int, int]:
	"""The lines that are a comment and the lines that are code. Pure."""
	lines = text.splitlines()
	comments = sum(1 for line in lines if line.lstrip().startswith("#"))
	code = sum(1 for line in lines if line.strip() and not line.lstrip().startswith("#"))
	return comments, code


def test_no_file_is_mostly_comment():
	dense = []
	for path in tree.scoped(tree.python()):
		comments, code = _comment_and_code(tree.text(path))
		if code and comments / code > DENSEST:
			dense.append(f"{path.relative_to(tree.ROOT)} ({comments}/{code})")
	assert not dense, f"more comment than code: {dense}"


def _unused(text: str) -> set[str]:
	"""The names a source imports and never uses. Pure."""
	nodes = tree.nodes(text)
	imported = {
		(alias.asname or alias.name).split(".")[0]
		for node in nodes
		if isinstance(node, ast.Import | ast.ImportFrom)
		for alias in node.names
		if alias.name != "*"
	}
	used = {n.id for n in nodes if isinstance(n, ast.Name)} | {n.attr for n in nodes if isinstance(n, ast.Attribute)}
	used |= set(re.findall(r"\b(\w+)\.", text))
	return {name for name in imported - used if name}


def test_nothing_is_imported_and_unused():
	"""Ruff's F401 is off for the app; this covers the scripts and tests."""
	unused = [f"{path.relative_to(tree.ROOT)}: {name}" for path in tree.scoped(tree.python()) for name in _unused(tree.text(path))]
	assert not unused, f"imported and never used: {unused}"


def test_the_comment_and_import_rules_catch_their_examples():
	comments, code = _comment_and_code("# one\n# two\nx = 1\n")
	assert comments / code > DENSEST
	assert _comment_and_code("# why\nx = 1\ny = 2\nz = 3\n") == (1, 3)
	assert _unused("import json\nimport os\nos.getcwd()\n") == {"json"}
	assert _unused("from pathlib import Path\nPath('.')\n") == set()


def test_the_essay_scan_would_catch_one(tmp_path):
	essay = tmp_path / "essay.py"
	essay.write_text("\n".join(f"# line {i}" for i in range(LONGEST_BLOCK + 2)) + "\nx = 1\n")
	assert max(_python_comment_runs(essay)) > LONGEST_BLOCK and _may_hold_a_block(essay.read_text())

	fine = tmp_path / "fine.py"
	fine.write_text("# why this is here\nx = 1\n")
	assert max(_python_comment_runs(fine)) == 1

	lecture = tmp_path / "lecture.py"
	lecture.write_text('"""' + "\n".join(f"line {i}" for i in range(LONGEST_DOCSTRING + 1)) + '"""\n')
	assert _long_docstrings(lecture) == ["module"] and _long_docstrings(fine) == []


LINTED = ("onedesk/one_project", "onedesk/one_demo")


def _ruff_finds(ruff: str, paths, cwd: Path) -> str:
	"""What ruff says of these paths, or nothing when they lint clean."""
	import subprocess

	found = subprocess.run([ruff, "check", "--quiet", *map(str, paths)], cwd=cwd, capture_output=True, text=True)
	return found.stdout[-3000:] or "ruff failed" if found.returncode else ""


def test_a_closed_module_lints_clean():
	import shutil

	import pytest

	ruff = shutil.which("ruff")
	if not ruff:
		pytest.skip("ruff isn't installed here")
	said = _ruff_finds(ruff, LINTED, tree.ROOT)
	assert not said, said


def test_the_lint_rule_catches_its_example(tmp_path):
	import shutil

	import pytest

	ruff = shutil.which("ruff")
	if not ruff:
		pytest.skip("ruff isn't installed here")
	(tmp_path / "bad.py").write_text("def f(:\n")
	(tmp_path / "good.py").write_text("x = 1\n")
	assert _ruff_finds(ruff, ["bad.py"], tmp_path)
	assert not _ruff_finds(ruff, ["good.py"], tmp_path)


PARSES = """
const vm = require("vm");
const fs = require("fs");
const wrapper = ["exports", "require", "module", "__filename", "__dirname"];
for (const file of JSON.parse(fs.readFileSync(0, "utf8"))) {
	try {
		vm.compileFunction(fs.readFileSync(file, "utf8"), wrapper, { filename: file });
	} catch {
		console.log(file);
	}
}
"""
"""Each script compiled as node --check compiles it, in one process; a file
that fails here is asked of node --check itself, which also tries it as a
module."""


def _broken(node: str, scripts: list[Path]) -> list[Path]:
	import json
	import subprocess

	doubtful = subprocess.run([node, "-e", PARSES], input=json.dumps([str(p) for p in scripts]), capture_output=True, text=True, check=True)
	return [Path(one) for one in doubtful.stdout.splitlines() if subprocess.run([node, "--check", one], capture_output=True).returncode]


def test_every_desk_script_parses():
	"""A desk script that does not parse kills its whole form or report."""
	import shutil

	import pytest

	node = shutil.which("node")
	if not node:
		pytest.skip("node isn't installed here")
	skip = ("node_modules", "dist", "frontend")
	scripts = [p for p in tree.scoped((tree.ROOT / "onedesk").rglob("*.js")) if not set(p.parts) & set(skip)]
	broken = [str(p.relative_to(tree.ROOT)) for p in _broken(node, scripts)]
	assert not broken, broken


def test_the_parse_check_catches_a_broken_script(tmp_path):
	import shutil

	import pytest

	node = shutil.which("node")
	if not node:
		pytest.skip("node isn't installed here")
	broken, fine, module = tmp_path / "broken.js", tmp_path / "fine.js", tmp_path / "module.js"
	broken.write_text("frappe.ui.form.on('Note', {\n\trefresh(frm) {\n});\n")
	fine.write_text("frappe.ui.form.on('Note', { refresh(frm) { return frm; } });\n")
	module.write_text("import { a } from './a.js';\nexport const b = a;\n")
	assert _broken(node, [broken, fine, module]) == [broken]
