"""OneAI never names the software One is built on.

The model repeats what it reads, so nothing it reads may say Frappe, ERPNext
or HRMS, or call a kind of record a DocType: not a tool's description (the
first paragraph of its docstring and every `Annotated` note), not the help a
tool hands back, not the persona or an action's instruction, and not the part
of a guide `how_to` answers from (above `## Under the hood`). Code an action
writes may still call `frappe.db.get_value`; a sentence about it may not say
"frappe checks it". docs/READY.md, Speaks.
"""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

UNDERNEATH = re.compile(r"(?i:\b(erpnext|hrms)\b|\bfrappe\b(?![.\w(]))|\bDocTypes?\b")

GENERIC = ("one_ai/tools.py", "one_ai/memory.py", "one_ai/guide.py")


def _hooked() -> dict[str, set[str]]:
	"""Each module file with a tool in it, and the tools it holds."""
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	out: dict[str, set[str]] = {}
	for key in ("one_ai_reads", "one_ai_suggests"):
		block = re.search(key + r"\s*=\s*\[(.*?)\n\]", hooks, re.S).group(1)
		for path in re.findall(r'"onedesk\.([\w.]+)"', block):
			module, name = path.rsplit(".", 1)
			out.setdefault(module.replace(".", "/") + ".py", set()).add(name)
	tools = ast.parse((tree.APP / "one_ai" / "tools.py").read_text(encoding="utf-8"))
	for node in tools.body:
		if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
			out.setdefault("one_ai/tools.py", set()).add(node.name)
	for where in GENERIC[1:]:
		body = ast.parse((tree.APP / where).read_text(encoding="utf-8"))
		out.setdefault(where, set()).update(
			node.name
			for node in body.body
			if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
		)
	return out


def _strings(node, constants: dict) -> list[str]:
	"""Every piece of text in an annotation, constants read through."""
	said = []
	for one in ast.walk(node):
		if isinstance(one, ast.Constant) and isinstance(one.value, str):
			said.append(one.value)
		elif isinstance(one, ast.Name) and one.id in constants:
			said.append(constants[one.id])
	return said


def _constants(body: ast.Module) -> dict[str, str]:
	out = {}
	for node in body.body:
		if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
			try:
				value = ast.literal_eval(node.value)
			except Exception:
				continue
			if isinstance(value, str):
				out[node.targets[0].id] = value
	return out


def test_no_tool_says_it():
	found = []
	for where, names in _hooked().items():
		body = ast.parse((tree.APP / where).read_text(encoding="utf-8"))
		constants = _constants(body)
		for node in body.body:
			if not isinstance(node, ast.FunctionDef) or node.name not in names:
				continue
			told = (ast.get_docstring(node) or "").split("\n\n")[0]
			said = [told] + [
				s
				for arg in node.args.args + node.args.kwonlyargs
				if arg.annotation
				for s in _strings(arg.annotation, constants)
			]
			for text in said:
				hit = UNDERNEATH.search(text)
				if hit:
					found.append(f"{where}:{node.name}: …{text[max(hit.start() - 40, 0) : hit.end() + 40]}…")
	assert not found, "a tool tells the model what One is built on:\n" + "\n".join(found)


def test_no_help_a_tool_hands_back_says_it():
	"""The module-level text a tool returns as it is (a format's how-to, a
	template's rules) is read by the model like a description."""
	found = []
	for where in _hooked():
		body = ast.parse((tree.APP / where).read_text(encoding="utf-8"))
		for name, text in _constants(body).items():
			if name.isupper() and name.endswith(("HELP", "HOW", "SAID", "TOLD")):
				hit = UNDERNEATH.search(text)
				if hit:
					found.append(f"{where}:{name}: …{text[max(hit.start() - 40, 0) : hit.end() + 40]}…")
	assert not found, "\n".join(found)


def test_neither_the_persona_nor_an_action_says_it():
	settings = json.loads(
		(tree.APP / "one_admin" / "doctype" / "one_admin_settings" / "one_admin_settings.json").read_text(
			encoding="utf-8"
		)
	)
	persona = next(f for f in settings["fields"] if f["fieldname"] == "persona")["default"]
	assert not UNDERNEATH.search(persona)
	assert "never name the software" in persona
	for row in json.loads((tree.APP / "fixtures" / "ai_action.json").read_text(encoding="utf-8")):
		hit = UNDERNEATH.search(row.get("instruction") or "")
		assert not hit, f"{row['name']}: …{row['instruction'][max(hit.start() - 40, 0) : hit.end() + 40]}…"


def test_no_guide_it_answers_from_says_it():
	found = []
	for readme in sorted(tree.APP.glob("*/README.md")):
		told = readme.read_text(encoding="utf-8").split("## Under the hood")[0]
		for n, line in enumerate(told.splitlines(), 1):
			if UNDERNEATH.search(line):
				found.append(f"{readme.relative_to(tree.APP)}:{n}: {line.strip()[:120]}")
	assert not found, "how_to reads these to the model:\n" + "\n".join(found)
