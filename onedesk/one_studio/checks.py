"""Whether an extension's code would work, read before it is kept.

guard.py says what an extension may do; this says whether what it does is
there. A model writing frappe code invents a field name, or names a handler
frappe never calls, and the code passes every review and then does nothing,
or runs into an error on every save. So the names the code uses are read
against the record's own fields, and what is wrong comes back to OneAI in
words it can mend from, with the fields that are there.

Pure: what it knows of the site comes in as `fields`, a function from a kind
of record to its field names (None for a kind it cannot say).
"""

import ast
import difflib
import re

from onedesk.one_studio.guard import Refused

#: Lines of code past which an extension is refused as more than one thing.
#: The longest that passed in the evals was 40; a person asking for one
#: change gets a short one.
LONGEST = 120

#: What every record has besides its fields, and what a server extension
#: calls on `doc` (frappe's Document).
ON_EVERY_RECORD = frozenset(
	"""
	name doctype owner creation modified modified_by docstatus idx parent parentfield parenttype
	amended_from get set append extend update is_new has_value_changed get_doc_before_save as_dict
	as_json get_formatted insert save submit cancel reload add_comment get_title meta
	check_permission has_permission get_url precision notify_update run_method remove
	get_value
	""".split()
)

#: What frappe's form calls on a handler by name, besides a field's change
#: (frappe/public/js/frappe/form, Oct 2026).
FORM_EVENTS = frozenset(
	"""
	setup before_load onload onload_post_render refresh render_complete validate before_save
	after_save before_submit on_submit before_cancel after_cancel before_discard after_discard
	before_workflow_action after_workflow_action timeline_refresh dashboard_update on_hide
	on_tab_change form_render rename
	""".split()
)

#: What a child table's handler is called: `items_add`, `before_items_remove`.
_TABLE_EVENT = re.compile(r"^(?:before_)?(\w+?)_(?:add|remove|move|delete|on_form_rendered)$")


def length(code: str) -> None:
	"""Refuse code too long to be one change. Pure."""
	lines = [
		line
		for line in (code or "").splitlines()
		if line.strip() and not line.strip().startswith(("#", "//", "*", "/*"))
	]
	if len(lines) > LONGEST:
		raise Refused(
			f"It is {len(lines)} lines, more than one extension should be (at most {LONGEST}). "
			"Write the shortest code that does what was asked, and nothing it was not asked for."
		)


def _nearest(name: str, known: set) -> str:
	close = difflib.get_close_matches(name, sorted(known), n=3, cutoff=0.6)
	if close:
		return f" Did you mean {', '.join(close)}?"
	plain = sorted(one for one in known if one not in ON_EVERY_RECORD)
	shown = ", ".join(plain[:40])
	return f" Its fields: {shown}{'…' if len(plain) > 40 else ''}."


def _field(name: str, doctype: str, known: set | None, said: str) -> None:
	"""Refuse `name` unless `doctype` has it; `said` is what the code does with
	it, as the refusal says it. Pure."""
	if known is None or name in known or name in ON_EVERY_RECORD:
		return
	raise Refused(f"It {said}, but a {doctype} has no field {name}.{_nearest(name, known)}")


def _text(node) -> str | None:
	return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _texts(node) -> list:
	if isinstance(node, (ast.List, ast.Tuple)):
		return [one for one in (_text(item) for item in node.elts) if one]
	one = _text(node)
	return [one] if one else []


def on_server(code: str, doctype: str | None, fields) -> None:
	"""Refuse server code that names a field its record does not have: on
	`doc`, and in the fields and filters of a lookup on another kind. Pure."""
	length(code)
	tree = ast.parse(code or "", mode="exec")
	own = fields(doctype) if doctype else None
	for node in ast.walk(tree):
		if (
			doctype
			and isinstance(node, ast.Attribute)
			and isinstance(node.value, ast.Name)
			and node.value.id == "doc"
		):
			_field(node.attr, doctype, own, f"uses doc.{node.attr}")
		if not isinstance(node, ast.Call):
			continue
		func = node.func
		called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
		# doc.get("x"), doc.set("x", …), doc.append("items", …)
		if (
			doctype
			and isinstance(func, ast.Attribute)
			and isinstance(func.value, ast.Name)
			and func.value.id == "doc"
			and called in ("get", "set", "append", "has_value_changed")
			and node.args
		):
			name = _text(node.args[0])
			if name:
				_field(name, doctype, own, f'calls doc.{called}("{name}")')
		# frappe.get_list("Lead", fields=[…], filters={…}), frappe.db.get_value("Lead", name, "field")
		if called in ("get_list", "get_all", "get_value", "count", "get_single_value") and node.args:
			kind = _text(node.args[0])
			known = fields(kind) if kind else None
			if not kind or known is None:
				continue
			named = []
			if called == "get_value" and len(node.args) > 2:
				named += _texts(node.args[2])
			for keyword in node.keywords:
				if keyword.arg in ("fields", "fieldname", "pluck", "order_by"):
					named += [one.split(" ")[0] for one in _texts(keyword.value)]
				if keyword.arg == "filters" and isinstance(keyword.value, ast.Dict):
					named += [one for one in (_text(key) for key in keyword.value.keys if key) if one]
			if called in ("get_list", "get_all", "count") and len(node.args) > 1 and isinstance(node.args[1], ast.Dict):
				named += [one for one in (_text(key) for key in node.args[1].keys if key) if one]
			for name in named:
				if name in ("*", "count(*)") or "(" in name or " as " in name:
					continue
				_field(name, kind, known, f"asks {kind} for {name}")


#: frappe.ui.form.on("Customer", { … }) and frappe.ui.form.on("Customer", "field", fn)
_FORM_ON = re.compile(r"""frappe\.ui\.form\.on\(\s*(["'])([^"']+)\1\s*,\s*""")

#: What screen code names a field by, on the record the form shows.
_SCREEN_FIELD = (
	(re.compile(r"""\bfrm\.doc\.([A-Za-z_][A-Za-z0-9_]*)"""), "uses frm.doc.{0}"),
	(re.compile(r"""\bfrm\.fields_dict\.([A-Za-z_][A-Za-z0-9_]*)"""), "uses frm.fields_dict.{0}"),
	(re.compile(r"""\bfrm\.fields_dict\[\s*["']([^"']+)["']"""), 'uses frm.fields_dict["{0}"]'),
	(
		re.compile(
			r"""\bfrm\.(?:set_value|toggle_display|toggle_reqd|toggle_enable|set_df_property|set_query|"""
			r"""get_field|refresh_field|add_fetch)\(\s*["']([^"']+)["']"""
		),
		'names the field "{0}"',
	),
)

#: The same with a list of fields: frm.toggle_display(["a", "b"], …)
_SCREEN_FIELDS = re.compile(
	r"""\bfrm\.(?:toggle_display|toggle_reqd|toggle_enable|set_df_property)\(\s*\[([^\]]*)\]"""
)


def _object_keys(code: str, start: int) -> list:
	"""The keys of the object literal at `start` (its `{`), at its own depth:
	`refresh(frm) {`, `territory: function`, `"items_add": (frm) =>`. Skips
	strings, template literals and comments. Pure."""
	keys, depth, i, n = [], 0, start, len(code)
	expect_key = False
	while i < n:
		c = code[i]
		if c in "\"'`":
			end = i + 1
			while end < n and code[end] != c:
				end += 2 if code[end] == "\\" else 1
			if depth == 1 and expect_key:
				rest = code[end + 1 :].lstrip()
				if rest.startswith(":") or rest.startswith("("):
					keys.append(code[i + 1 : end])
				expect_key = False
			i = end + 1
			continue
		if code.startswith("//", i):
			i = code.find("\n", i)
			i = n if i < 0 else i
			continue
		if code.startswith("/*", i):
			i = code.find("*/", i)
			i = n if i < 0 else i + 2
			continue
		if c in "{[(":
			depth += 1
			if depth == 1:
				expect_key = True
		elif c in "}])":
			depth -= 1
			if depth == 0:
				return keys
		elif c == "," and depth == 1:
			expect_key = True
		elif depth == 1 and expect_key and (c.isalpha() or c == "_"):
			match = re.match(r"(?:async\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*([:(])", code[i:])
			if match:
				keys.append(match.group(1))
				i += match.end() - 1
			expect_key = False
			continue
		elif depth == 1 and expect_key and not c.isspace():
			expect_key = False
		i += 1
	return keys


def _handler(key: str, kind: str, known: set | None) -> None:
	if known is None or key in FORM_EVENTS or key in known:
		return
	# items_add is handled on the child's kind (frappe.ui.form.on("Sales
	# Invoice Item", {items_add})) and named after the parent's table, which
	# the child cannot say: its shape is enough.
	if _TABLE_EVENT.match(key):
		return
	raise Refused(
		f'It handles {key} on {kind}, which frappe never calls: a handler is named after a field of '
		f"{kind}, when it changes, or a form event such as refresh, onload, validate or before_save."
		f"{_nearest(key, known)}"
	)


def on_screen(code: str, doctype: str | None, view: str | None, fields) -> None:
	"""Refuse screen code that names a field the form does not have, or a
	handler frappe never calls. Pure."""
	length(code)
	text = code or ""
	for found in _FORM_ON.finditer(text):
		kind = found.group(2)
		known = fields(kind)
		after = found.end()
		if after < len(text) and text[after] == "{":
			for key in _object_keys(text, after):
				_handler(key, kind, known)
		else:
			# frappe.ui.form.on("Customer", "territory", fn)
			named = re.match(r"""(["'])([^"']+)\1""", text[after:])
			if named:
				_handler(named.group(2), kind, known)
	if not doctype or view not in (None, "Form"):
		return
	own = fields(doctype)
	for pattern, how in _SCREEN_FIELD:
		for name in pattern.findall(text):
			_field(name, doctype, own, how.format(name))
	for listed in _SCREEN_FIELDS.findall(text):
		for name in re.findall(r"""["']([^"']+)["']""", listed):
			_field(name, doctype, own, f'names the field "{name}"')
