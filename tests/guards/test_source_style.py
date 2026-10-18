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


def test_no_comment_block_is_an_essay():
	long_ones = []
	for path in tree.python():
		if max(_python_comment_runs(path), default=0) > LONGEST_BLOCK:
			long_ones.append(str(path.relative_to(tree.ROOT)))
	assert not long_ones, (
		f"comment blocks over {LONGEST_BLOCK} lines in {long_ones} — "
		"say why in a line or two, and put the long form in the commit message"
	)


def _long_docstrings(path: Path) -> list[str]:
	out = []
	for node in ast.walk(ast.parse(path.read_text())):
		if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
			doc = ast.get_docstring(node, clean=False)
			if doc and doc.count("\n") + 1 > LONGEST_DOCSTRING:
				out.append(getattr(node, "name", "module"))
	return out


def test_no_docstring_is_an_essay():
	long_ones = [
		f"{path.relative_to(tree.ROOT)}: {name}" for path in tree.python() for name in _long_docstrings(path)
	]
	assert not long_ones, (
		f"docstrings over {LONGEST_DOCSTRING} lines in {long_ones}: say what it is for, "
		"and put the rest in the module's README under Under the hood"
	)


def test_no_file_is_mostly_comment():
	dense = []
	for path in tree.python():
		lines = path.read_text().splitlines()
		comments = sum(1 for line in lines if line.lstrip().startswith("#"))
		code = sum(1 for line in lines if line.strip() and not line.lstrip().startswith("#"))
		if code and comments / code > DENSEST:
			dense.append(f"{path.relative_to(tree.ROOT)} ({comments}/{code})")
	assert not dense, f"more comment than code: {dense}"


def test_nothing_is_imported_and_unused():
	"""Ruff's F401 is off for the app; this covers the scripts and tests."""
	unused = []
	for path in tree.python():
		text = path.read_text()
		module = ast.parse(text)
		imported = {
			(alias.asname or alias.name).split(".")[0]
			for node in ast.walk(module)
			if isinstance(node, ast.Import | ast.ImportFrom)
			for alias in node.names
			if alias.name != "*"
		}
		used = {n.id for n in ast.walk(module) if isinstance(n, ast.Name)} | {
			n.attr for n in ast.walk(module) if isinstance(n, ast.Attribute)
		}
		used |= set(re.findall(r"\b(\w+)\.", text))
		unused += [
			f"{path.relative_to(tree.ROOT)}: {name}" for name in imported - used if name
		]
	assert not unused, f"imported and never used: {unused}"


def test_the_essay_scan_would_catch_one(tmp_path):
	essay = tmp_path / "essay.py"
	essay.write_text("\n".join(f"# line {i}" for i in range(LONGEST_BLOCK + 2)) + "\nx = 1\n")
	assert max(_python_comment_runs(essay)) > LONGEST_BLOCK

	fine = tmp_path / "fine.py"
	fine.write_text("# why this is here\nx = 1\n")
	assert max(_python_comment_runs(fine)) == 1

	lecture = tmp_path / "lecture.py"
	lecture.write_text('"""' + "\n".join(f"line {i}" for i in range(LONGEST_DOCSTRING + 1)) + '"""\n')
	assert _long_docstrings(lecture) == ["module"] and _long_docstrings(fine) == []


LINTED = ("onedesk/one_project", "onedesk/one_demo")


def test_a_closed_module_lints_clean():
	import shutil
	import subprocess

	import pytest

	ruff = shutil.which("ruff")
	if not ruff:
		pytest.skip("ruff isn't installed here")
	found = subprocess.run([ruff, "check", "--quiet", *LINTED], cwd=tree.ROOT, capture_output=True, text=True)
	assert found.returncode == 0, found.stdout[-3000:]
