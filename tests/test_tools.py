"""What a model may ask for, and the one rule with no exception in it.

Every tool runs as the person asking. Not as Administrator with a filter bolted
on, not with `ignore_permissions`, and never through `frappe.get_all` — which
looks like `get_list` and ignores permissions, and is the single most likely way
for this rule to be undone by somebody being helpful.
"""

import ast
import json
import sys
from pathlib import Path
from typing import Annotated, Literal

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

TOOLS = tree.APP / "one_ai" / "tools.py"
PROPOSALS = tree.APP / "one_ai" / "proposals.py"
PROPOSAL = tree.APP / "one_ai" / "doctype" / "ai_proposal" / "ai_proposal.json"

#: Ways to read that do not check a permission. `get_all` is `get_list` with the
#: checks off and one letter different, which is why it is named here rather
#: than left to a reviewer's eye.
BLIND = ("get_all", "ignore_permissions", "set_user", "db.sql", "only_for('Administrator')")


def _schema():
	import importlib.util

	at = tree.APP / "one_ai" / "schema.py"
	spec = importlib.util.spec_from_file_location("onedesk_schema", at)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


schema = _schema()


def _code(path: Path) -> str:
	body = ast.parse(path.read_text(encoding="utf-8"))
	for node in ast.walk(body):
		if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
			node.body = [
				n
				for n in node.body
				if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
			]
	return ast.unparse(body)


# ------------------------------------------------------ the rule with no override


@pytest.mark.parametrize("said", BLIND)
def test_no_tool_reads_past_the_person_asking(said):
	for path in (TOOLS, PROPOSALS):
		assert said not in _code(path), (
			f"{path.name} uses {said}. Every tool runs as the session user, and this "
			"is the one rule in the module with no exception and no override."
		)


def test_a_list_is_the_one_the_browser_would_have_called():
	assert "frappe.get_list" in _code(TOOLS)


def test_nothing_in_the_tools_writes():
	"""A read runs; a create, an edit or a delete becomes a card. The writing
	happens in `proposals.apply`, in a request a person made."""
	said = _code(TOOLS)
	for writes in (".insert(", ".save(", ".delete(", ".db_set(", "set_value("):
		assert writes not in said, f"a tool calls {writes}"


def test_the_two_tuples_do_not_overlap():
	body = ast.parse(TOOLS.read_text(encoding="utf-8"))
	named = {}
	for node in body.body:
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
			for target in node.targets:
				if isinstance(target, ast.Name):
					named[target.id] = {
						e.id for e in node.value.elts if isinstance(e, ast.Name)
					}
	assert named.get("READS") and named.get("SUGGESTS")
	assert not (named["READS"] & named["SUGGESTS"])


def test_every_tool_is_a_function_a_schema_can_be_read_off():
	"""`declared()` runs at the moment a model is called. A tool missing a hint
	would raise there, which is a customer's call failing rather than a test."""
	body = ast.parse(TOOLS.read_text(encoding="utf-8"))
	functions = {n.name: n for n in body.body if isinstance(n, ast.FunctionDef)}
	named = set()
	for node in body.body:
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
			for target in node.targets:
				if isinstance(target, ast.Name) and target.id in ("READS", "SUGGESTS"):
					named |= {e.id for e in node.value.elts if isinstance(e, ast.Name)}
	assert len(named) == 7, named
	for name in named:
		fn = functions[name]
		assert ast.get_docstring(fn), f"{name} tells a model nothing about itself"
		for arg in fn.args.args:
			assert arg.annotation is not None, f"{name}({arg.arg}) has no type on it"


# ------------------------------------------------------------------- proposals


def test_a_permission_is_checked_when_it_is_suggested_and_again_when_it_is_done():
	said = _code(PROPOSALS)
	assert "frappe.has_permission" in said, "nothing checks the verb when a card is written"
	assert ".insert()" in said and ".save()" in said and ".delete()" in said
	assert "ignore_permissions" not in said


def test_an_edit_cannot_overwrite_a_change_made_after_it():
	"""A proposal carries the record's `modified` from when it was written.
	Without it, a model's diff quietly undoes a person's."""
	said = _code(PROPOSALS)
	assert "modified_then" in said and "Stale" in said


def test_nothing_nested_is_proposed():
	"""A child table on a model's say-so is a diff nobody reads before pressing
	a button."""
	assert "_plain" in _code(PROPOSALS)


def test_a_proposal_is_read_only_to_everybody():
	"""One that could be edited before applying no longer says what the model
	suggested, and the whole point of the card is that it does."""
	spec = json.loads(PROPOSAL.read_text(encoding="utf-8"))
	for row in spec["permissions"]:
		assert not row.get("write"), row["role"]
	by_role = {row["role"]: row for row in spec["permissions"]}
	assert by_role["All"].get("if_owner"), "everybody would see everybody's cards"


# --------------------------------------------------------------- the schema


def _of(fn):
	return schema.of(fn)["parameters"]


def test_a_description_comes_from_the_annotation():
	def one(x: Annotated[str, "What to look in."]) -> None:
		"""Does a thing."""

	said = _of(one)["properties"]["x"]
	assert said == {"type": "string", "description": "What to look in."}


def test_a_closed_list_is_an_enum():
	"""A model given an open string where three values are allowed will
	eventually invent a fourth."""

	def one(x: Literal["a", "b"]) -> None:
		"""Does a thing."""

	assert _of(one)["properties"]["x"] == {"type": "string", "enum": ["a", "b"]}


@pytest.mark.parametrize("hint,kind", [(str, "string"), (int, "integer"), (bool, "boolean"), (dict, "object"), (list, "array")])
def test_the_plain_types_have_names(hint, kind):
	def one(x) -> None:
		"""Does a thing."""

	one.__annotations__ = {"x": hint, "return": None}
	assert _of(one)["properties"]["x"]["type"] == kind


def test_either_way_of_saying_it_may_be_left_out():
	"""Both orders are written in practice, and only one survives a single pass."""

	def one(
		a: Annotated[dict, "A."] | None = None,
		b: "Annotated[int, 'B.'] | None" = None,
	) -> None:
		"""Does a thing."""

	said = _of(one)
	assert said["required"] == []
	assert said["properties"]["a"] == {"type": "object", "description": "A."}


def test_a_signature_this_cannot_read_is_refused_at_import():
	def one(x: set) -> None:
		"""Does a thing."""

	with pytest.raises(schema.Unreadable):
		schema.of(one)


def test_a_tool_with_no_docstring_is_refused():
	def one(x: str) -> None:
		return None

	with pytest.raises(schema.Unreadable):
		schema.of(one)


def test_only_the_first_paragraph_reaches_a_model():
	def one(x: str) -> None:
		"""What it does.

		Why it is written this way, which is for whoever maintains it.
		"""

	assert schema.of(one)["description"] == "What it does."
