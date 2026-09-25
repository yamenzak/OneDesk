"""A record's head is rows, drawn by one renderer (one/head.py,
public/js/head.js, docs/SHELL.md decision 4).

These fail when a row could read more than the record's own fields, when a
head names a measure or a verb no module registered, and when a doctype whose
head is rows still has a script of its own drawing it.
"""

import ast
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

HEAD = tree.APP / "one" / "head.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _pure(*names, **extra):
	space = {
		"re": re,
		"quote": quote,
		"cstr": lambda v: "" if v is None else str(v),
		"json": __import__("json"),
		**extra,
	}
	for node in ast.parse(HEAD.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SLOT":
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return [space[name] for name in names]


def _hook(name: str) -> list[str]:
	for node in ast.parse(HOOKS).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
			return ast.literal_eval(node.value)
	return []


def _declared(path: str) -> ast.AST:
	"""The value a hook's dotted path names, read from its module."""
	module, attr = path.rsplit(".", 1)
	source = tree.APP.parent / (module.replace(".", "/") + ".py")
	for node in ast.parse(source.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == attr:
			return node.value
	raise AssertionError(f"{path} is not declared")


def test_a_template_names_only_the_records_fields():
	slots, fill = _pure("slots", "fill")
	doc = {"name": "Dell Latitude 5440", "location": "Head Office"}
	assert slots("{{ doc.name }} at {{doc.location}}") == ["name", "location"]
	assert fill("{{ doc.name }} at {{ doc.location }}.", doc) == "Dell Latitude 5440 at Head Office."
	assert (
		fill("/desk/asset?item_code={{ doc.name }}", doc, url=True)
		== "/desk/asset?item_code=Dell%20Latitude%205440"
	)
	# Anything else is left as it is written, never read or run.
	for said in (
		"{{ frappe.session.user }}",
		"{{ doc.name.upper() }}",
		"{% for x in y %}",
		"{{ doc['name'] }}",
	):
		assert slots(said) == [] and fill(said, doc) == said


def test_a_condition_is_frappes_filters_or_nothing():
	(conditions,) = _pure("conditions")
	assert conditions("") == [] and conditions(None) == []
	assert conditions('[["docstatus", "=", 1]]') == [["docstatus", "=", 1]]
	assert conditions('{"is_stock_item": 1}') == [["is_stock_item", "=", 1]]
	try:
		conditions('"docstatus == 1"')
	except ValueError:
		pass
	else:
		raise AssertionError("a string is not a filter")


def test_counting_puts_the_records_values_into_its_filters():
	fill, conditions = _pure("fill", "conditions")
	(counting,) = _pure("counting", fill=fill, conditions=conditions)
	said = counting('[["item_code", "=", "{{ doc.name }}"], ["docstatus", "<", 2]]', {"name": "Gloves"})
	assert said == [["item_code", "=", "Gloves"], ["docstatus", "<", 2]]


def test_every_head_names_only_registered_measures_and_verbs():
	measures, verbs = set(), set()
	for path in _hook("one_measures"):
		measures |= {key.value for key in _declared(path).keys}
	for path in _hook("one_verbs"):
		verbs |= {key.value for key in _declared(path).keys}
	assert measures and verbs
	for path in _hook("one_record_heads"):
		source = tree.APP.parent / (path.rsplit(".", 1)[0].replace(".", "/") + ".py")
		for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
			if not isinstance(node, ast.Dict):
				continue
			for key, value in zip(node.keys, node.values, strict=True):
				if (
					isinstance(key, ast.Constant)
					and key.value in ("measure", "verb")
					and isinstance(value, ast.Constant)
				):
					known = measures if key.value == "measure" else verbs
					assert value.value in known, (
						f"{source.name} names {key.value} {value.value}, which nobody registered"
					)


def test_a_verb_says_whom_it_is_for_when_and_what_it_does():
	for path in _hook("one_verbs"):
		for key, verb in zip(_declared(path).keys, _declared(path).values, strict=True):
			said = {item.value for item in verb.keys}
			assert {"doctypes", "label", "when", "run"} <= said, (
				f"{key.value} is missing { ({'doctypes', 'label', 'when', 'run'} - said) }"
			)


def test_the_head_is_worked_out_on_the_server_and_drawn_once():
	assert '"onedesk.one.head.onload"' in HOOKS, "the head is sent with the record, as the reader"
	assert '"onedesk.one.head.install"' in HOOKS
	assert '"/assets/onedesk/js/head.js"' in HOOKS
	source = HEAD.read_text(encoding="utf-8")
	assert '@frappe.whitelist(methods=["POST"])\ndef run(' in source
	# A verb is checked again when it is done, not only when it is drawn.
	body = source.split("def run(", 1)[1]
	assert 'found["when"](doc)' in body and "check_permission" in body
	# A count or a sum is the reader's own list's.
	assert re.search(r"frappe\.get_list\(\s*row\.of_doctype", source) and not re.search(
		r"frappe\.get_all\(\s*row\.of_doctype", source
	)
	js = (tree.APP / "public" / "js" / "head.js").read_text(encoding="utf-8")
	assert 'frappe.ui.form.on("*"' in js and "onedesk.one.head.run" in js


def test_a_doctype_with_a_head_has_no_script_drawing_one():
	headed = set()
	for path in _hook("one_record_heads"):
		source = tree.APP.parent / (path.rsplit(".", 1)[0].replace(".", "/") + ".py")
		headed |= set(re.findall(r'"doctype": "([^"]+)"', source.read_text(encoding="utf-8")))
	headed |= {"Sales Invoice", "Purchase Invoice"}
	scripts = ast.literal_eval(
		next(
			node.value
			for node in ast.parse(HOOKS).body
			if isinstance(node, ast.Assign) and node.targets[0].id == "doctype_js"
		)
	)
	assert not headed & set(scripts), f"a script still draws the head of {sorted(headed & set(scripts))}"
	for gone in ("item.js", "asset.js", "invoice.js"):
		assert not (tree.APP / "public" / "js" / gone).exists(), gone
