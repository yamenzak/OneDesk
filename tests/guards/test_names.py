"""Names are code (docs/run/RUN.md, rules of the road; docs/STANDARD.md,
point 13). An app's, a centre's or an engine's name is typed once, in its
manifest, and everything people read takes it from the registry: Python
`_("Edit in {0}").format(registry.name("one_doc"))`, desk JS
`__("Edit in {0}", [onedesk.names.of("one_doc")])`, an island's kit
`name("one_doc")`, a Help page, a version or a notification's words
`{one_doc}`, and a synced label written by scripts/docs.py
(onedesk/one/registry/labels.py).

The rule reads what people read: in Python the text given to `_()` or `_lt()`,
every text of a module's notifications.py, and a text that is only a name; in
desk JS and an island the text given to `__()`, a text that is only a name,
and an island's template; in synced JSON a label, title, description,
heading, subject, message or content; and Help pages. A name is each manifest's coined `name` (OneDoc, TrustCenter),
and "One" alone mid-sentence ("by One", "your One account"). Manifests,
generated files, tests and checks, translations, patches, old versions
(updates/) and the plans in docs/ are history or the place a name is typed,
and are not read.

What was typed when the rule arrived is in names_allowed.py, a count per
file that only falls."""

import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402

from onedesk.one import registry  # noqa: E402
from onedesk.one.registry import labels  # noqa: E402
from tests.guards import names_allowed  # noqa: E402

COINED = re.compile(r"[A-Z][a-z]+[A-Z]\w*")
NAMES = sorted((one.name for one in registry.apps() if COINED.fullmatch(one.name)), key=len, reverse=True)
NAMED = re.compile(r"(?<![\w./-])(" + "|".join(NAMES) + r")(?![\w-])")
ONE = re.compile(r"(?<=[a-z] )One(?![\w-])(?! [A-Z])")
BARE = set(NAMES)
WORD_CALLS = {"_", "_lt"}
JSON_KEYS = {"label", "title", "description", "subject", "message", "content", "html", "heading", "intro", "response"}
SKIP = re.compile(
	r"(^|/)(tests?|patches|updates|locale|translations|node_modules|dist|brand)/|manifest\.py$|(^|/)checks?\.py$"
)
GENERATED = {"dock/onedesk/onedesk.json", "modules.txt"}


def named(text: str) -> int:
	return len(NAMED.findall(text or "")) + len(ONE.findall(text or ""))


def _docstrings(tree_: ast.AST) -> set[int]:
	found = set()
	for node in ast.walk(tree_):
		body = getattr(node, "body", None)
		for one in body if isinstance(body, list) else []:
			if isinstance(one, ast.Expr) and isinstance(one.value, ast.Constant):
				found.add(id(one.value))
	return found


def _called(node: ast.Call) -> str:
	return getattr(node.func, "id", None) or getattr(node.func, "attr", "")


def in_python(file: str, source: str) -> int:
	parsed = ast.parse(source)
	docs, words = _docstrings(parsed), set()
	for node in ast.walk(parsed):
		if isinstance(node, ast.Call) and _called(node) in WORD_CALLS and node.args:
			words.add(id(node.args[0]))
	told = file.endswith("notifications.py")
	count = 0
	for node in ast.walk(parsed):
		if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or id(node) in docs:
			continue
		if id(node) in words or told:
			count += named(node.value)
		elif node.value in BARE:
			count += 1
	return count


WORD_JS = re.compile(r"""\b__\(\s*(["'`])((?:\\.|(?!\1).)*)\1""", re.S)
BARE_JS = re.compile(r"""(["'`])(""" + "|".join(sorted(BARE, key=len, reverse=True)) + r""")\1""")


REMARKS = re.compile(r"^[ \t]*//[^\n]*|/\*.*?\*/|<!--.*?-->", re.M | re.S)


def in_script(source: str) -> int:
	source = REMARKS.sub("", source)
	return sum(named(found.group(2)) for found in WORD_JS.finditer(source)) + len(BARE_JS.findall(source))


TEMPLATE = re.compile(r"<template>(.*)</template>", re.S)


def in_island(source: str) -> int:
	count = in_script(source)
	found = TEMPLATE.search(REMARKS.sub("", source))
	if found:
		text = re.sub(r"\{\{.*?\}\}", " ", re.sub(r"<[^>]*>", " ", found.group(1)), flags=re.S)
		count += named(text)
	return count


def in_json(file: str, source: str) -> int:
	try:
		record = json.loads(source)
	except ValueError:
		return 0
	written = set()
	for one in labels.named(tree.APP):
		if one.file == file and isinstance(record, dict):
			written.add((id(labels.holder(record, one)), one.field))

	def walk(value) -> int:
		if isinstance(value, dict):
			return sum(
				named(inner) if isinstance(inner, str) and key in JSON_KEYS and (id(value), key) not in written else walk(inner)
				for key, inner in value.items()
			)
		if isinstance(value, list):
			return sum(walk(inner) for inner in value)
		return 0

	return walk(record)


def in_markdown(file: str, source: str) -> int:
	return named(source) if "/help/" in file else 0


READERS = {".py": lambda file, text: in_python(file, text), ".js": lambda _f, text: in_script(text)}
READERS |= {".vue": lambda _f, text: in_island(text), ".json": in_json, ".md": in_markdown}


def typed(files: dict[str, str]) -> Counter:
	"""Each file's names typed where people read them, by its path under
	the app (onedesk/) or the frontend (frontend/)."""
	found = Counter()
	for file, text in files.items():
		reader = READERS.get(Path(file).suffix)
		if reader and not SKIP.search(file) and file not in GENERATED:
			count = reader(file, text)
			if count:
				found[file] = count
	return found


def sources() -> dict[str, str]:
	found = {}
	for base, prefix in ((tree.APP, ""), (ROOT / "frontend" / "src", "frontend/src/")):
		for path in sorted(base.rglob("*")):
			if path.suffix in READERS and path.is_file() and not any(part in tree.SKIP_DIRS for part in path.parts):
				if prefix and tree.vendored(path):
					continue
				found[prefix + str(path.relative_to(base))] = path.read_text(encoding="utf-8")
	return found


def test_no_name_is_typed_where_people_read_it():
	found, allowed = typed(sources()), names_allowed.ALLOWED
	over = {file: (count, allowed.get(file, 0)) for file, count in found.items() if count > allowed.get(file, 0)}
	assert not over, "a name typed where people read it, rather than read from the registry: " + ", ".join(
		f"{file} has {count} (allowed {was})" for file, (count, was) in sorted(over.items())
	)
	fell = {file: found.get(file, 0) for file, was in allowed.items() if found.get(file, 0) < was}
	assert not fell, "fewer names typed than names_allowed.py allows; lower it: " + ", ".join(
		f"{file}: {count}" for file, count in sorted(fell.items())
	)


EXAMPLE = {
	"one_example/api.py": (
		'from frappe import _\n\nAPP = "OneDoc"\n\n\ndef said():\n'
		'\t"""OneDoc\'s words, which a docstring may name."""\n'
		'\treturn _("Edit in OneDoc"), _("Sent by One"), _("Edit in {0}")\n'
	),
	"one_example/notifications.py": 'TYPES = [{"name": "Shared", "about": "When OneCloud shares a file."}]\n',
	"public/js/one_example/menu.js": 'const label = __("Open in OneSheet");\nconst app = "OneCloud";\nconst ok = __("Open in {0}", [onedesk.names.of("one_sheet")]);\n',
	"frontend/src/example/Page.vue": '<template><h1>Welcome to OneMail</h1><p>{{ __("Edit in {0}", [name("one_doc")]) }}</p></template>\n',
	"one_example/doctype/thing/thing.json": '{"fields": [{"label": "OneAI reads it", "fieldname": "OneAI"}]}\n',
	"one_example/help/start.md": "# Start\n\nOpen {one_cloud}, then OneMail.\n",
	"one_example/tests/test_api.py": '_("Edit in OneDoc")\n',
}


def test_the_names_rule_catches_its_example():
	assert typed(EXAMPLE) == {
		"one_example/api.py": 3,
		"one_example/notifications.py": 1,
		"public/js/one_example/menu.js": 2,
		"frontend/src/example/Page.vue": 1,
		"one_example/doctype/thing/thing.json": 1,
		"one_example/help/start.md": 1,
	}
