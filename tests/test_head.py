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
	measures, verbs, charts = set(), set(), set()
	for path in _hook("one_measures"):
		measures |= {key.value for key in _declared(path).keys}
	for path in _hook("one_verbs"):
		verbs |= {key.value for key in _declared(path).keys}
	for path in _hook("one_charts"):
		charts |= {key.value for key in _declared(path).keys}
	assert measures and verbs and charts
	for path in _hook("one_record_heads"):
		source = tree.APP.parent / (path.rsplit(".", 1)[0].replace(".", "/") + ".py")
		for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
			if not isinstance(node, ast.Dict):
				continue
			for key, value in zip(node.keys, node.values, strict=True):
				if (
					isinstance(key, ast.Constant)
					and key.value in ("measure", "verb", "chart")
					and isinstance(value, ast.Constant)
				):
					known = {"measure": measures, "verb": verbs, "chart": charts}[key.value]
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


def test_a_chart_says_whom_it_is_for_and_works_its_figures_out():
	for path in _hook("one_charts"):
		for key, chart in zip(_declared(path).keys, _declared(path).values, strict=True):
			said = {item.value for item in chart.keys}
			assert {"doctypes", "label", "figures"} <= said, f"{key.value} is missing some of it"


def test_a_chart_is_frappes_own_and_its_figures_the_readers():
	band = (tree.APP / "public" / "js" / "band.js").read_text(encoding="utf-8")
	assert "new frappe.Chart(" in band, "drawn by the desk's own charts, as a Dashboard Chart is"
	assert "[...chart.values]" in band, "frappe-charts works on its data in place"
	assert "disableEntryAnimation: 1" in band
	# The Number Card's pill for a change, and one hue checked on both themes.
	assert "indicator-pill-round" in band and '"--blue-400" : "--blue-500"' in band
	# Every chart's figures are read as the reader would list them.
	for module in ("one_book", "one_inventory"):
		source = (tree.APP / module / "heads.py").read_text(encoding="utf-8")
		for name in re.findall(r'"figures": (\w+)', source):
			body = source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]
			assert "frappe.get_all(" not in body or name == "life", f"{module}.{name} reads past the reader"


def test_months_and_weeks_are_counted_the_same_everywhere():
	from datetime import date

	space = {}
	exec((tree.APP / "one" / "figures.py").read_text(encoding="utf-8"), space)
	months, by_month, change = space["months"], space["by_month"], space["change"]
	assert months(date(2026, 2, 14), 3) == [date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1)]
	assert len(months(date(2026, 9, 26))) == 12
	rows = [(date(2026, 9, 3), 10), (date(2026, 9, 30), 5), (date(2025, 9, 30), 99), (None, 1)]
	assert by_month(rows, date(2026, 9, 26), 2) == [0.0, 15.0], "last September is not this one's"
	assert change(120, 100) == 20.0 and change(80, 100) == -20.0 and change(5, 0) is None
	assert space["same_day_last_year"](date(2028, 2, 29)) == date(2027, 2, 28)
	weeks, by_week = space["weeks"], space["by_week"]
	assert weeks(date(2026, 9, 26), 2) == [date(2026, 9, 14), date(2026, 9, 21)], "Mondays"
	assert by_week(
		[(date(2026, 9, 20), 3), (date(2026, 9, 21), 4), (date(2026, 9, 1), 9)], date(2026, 9, 26), 2
	) == [3.0, 4.0]


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


def test_no_form_script_draws_a_head():
	"""A pill, a headline, a band or a progress bar over a record's fields is
	its Record Head, declared in its module's heads.py and drawn by head.js.
	No form script draws one, headed doctype or not: a record that needs
	something above its fields is given a head, which the workspace can then
	customize and OneAI can read. A form script keeps what is not a head (a
	dialog that answers inside itself, a sidebar action, a field's options)."""
	scripts = ast.literal_eval(
		next(
			node.value
			for node in ast.parse(HOOKS).body
			if isinstance(node, ast.Assign) and node.targets[0].id == "doctype_js"
		)
	)
	paths = {tree.APP / path for path in scripts.values()}
	paths |= set(tree.APP.glob("*/doctype/*/*.js"))
	assert len(paths) > 20
	for path in sorted(paths):
		script = path.read_text(encoding="utf-8")
		for drawing in (
			"onedesk.band.show",
			"set_headline(",
			"set_headline_alert(",
			"dashboard.add_indicator",
			"page.set_indicator(",
			"dashboard.add_progress(",
			"onedesk.decision",
		):
			assert drawing not in script, f"{path.relative_to(tree.APP)} draws a head ({drawing}); declare a Record Head"
	for gone in ("item.js", "asset.js", "invoice.js", "decision.js", "leave_application.js", "salary_slip.js"):
		assert not (tree.APP / "public" / "js" / gone).exists(), gone
