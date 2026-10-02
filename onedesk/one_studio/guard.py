"""What an extension's code may do, read before it is ever kept.

An extension is code OneAI writes, and nobody else. An administrator could
still ask OneAI for code that reaches past what they may do, so this reads
the code itself, as a second line after the review (review.py), and refuses
what no explanation would excuse. Pure: what it needs from the site comes in
as `Site`.

**On the server** an extension is a Server Script on a record event, run in
frappe's sandbox as whoever saved the record. The sandbox already refuses
imports, files and the private parts of objects; this refuses the rest of
what it leaves open:

- writing past permissions: `db_set`, `db.set_value`, `ignore_permissions`,
  frappe's flags, deleting or renaming another record;
- reading past them: raw SQL, `get_all` (frappe's `get_list` checks), a
  password, and any field the administrator may not read;
- reaching outside: requests, mail, jobs, other scripts and whitelisted
  methods;
- naming a kind of record they cannot open, or frappe's or One's own, and
  naming one any way but as plain text, so every kind it touches is known.

**On the screen** an extension is a Client Script, which runs in the browser
of everybody who opens the form. It may change the form and speak to the
person; it may not call the server, store or send anything, or write markup.
"""

import ast
import json
import re
from dataclasses import dataclass, field

#: Attributes an extension never touches on the server.
REFUSED_ATTRIBUTES = frozenset(
	{
		"sql",
		"set_value",
		"db_set",
		"db_insert",
		"db_update",
		"commit",
		"rollback",
		"after_commit",
		"before_commit",
		"add_index",
		"sendmail",
		"enqueue",
		"is_job_queued",
		"call",
		"make_get_request",
		"make_post_request",
		"make_put_request",
		"make_patch_request",
		"make_delete_request",
		"delete_doc",
		"rename_doc",
		"get_all",
		"run_script",
		"render_template",
		"qb",
		"flags",
		"ignore_permissions",
		"set_user",
		"form_dict",
		"request",
		"get_hooks",
		"get_password",
		"get_decrypted_password",
		"get_print",
		"attach_print",
		"get_mapped_doc",
		"copy_doc",
		"socketio_port",
		"csrf_token",
	}
)

#: Attributes frappe's own sandbox refuses (safe_exec.UNSAFE_ATTRIBUTES) that
#: a writer reaches for anyway: caught here, with what to do instead, rather
#: than at the first save.
UNSAFE_IN_FRAPPE = frozenset({"format", "format_map"})

#: Names an extension never uses on the server.
REFUSED_NAMES = frozenset(
	{
		"FrappeClient",
		"run_script",
		"args",
		"get_visible_columns",
		"exec",
		"eval",
		"compile",
		"globals",
		"locals",
		"vars",
		"getattr",
		"setattr",
		"delattr",
	}
)

#: Keyword arguments that lift frappe's checks.
REFUSED_KEYWORDS = frozenset({"ignore_permissions", "ignore_links", "ignore_validate", "for_update"})

#: Calls whose first argument names a kind of record.
NAMES_A_KIND = frozenset(
	{
		"get_doc",
		"new_doc",
		"get_cached_doc",
		"get_last_doc",
		"get_list",
		"get_value",
		"get_single_value",
		"exists",
		"count",
		"get_meta",
	}
)

#: What a screen extension never writes, as it appears in JavaScript.
REFUSED_ON_SCREEN = (
	("fetch(", "calls the network"),
	("XMLHttpRequest", "calls the network"),
	("WebSocket", "calls the network"),
	("EventSource", "calls the network"),
	("sendBeacon", "calls the network"),
	("$.ajax", "calls the network"),
	("$.get", "calls the network"),
	("$.post", "calls the network"),
	("frappe.call", "calls the server"),
	("frappe.xcall", "calls the server"),
	("frappe.db.", "calls the server"),
	("frappe.client", "calls the server"),
	("frappe.model.with_doc", "calls the server"),
	("eval(", "runs text as code"),
	("Function(", "runs text as code"),
	("import(", "loads code"),
	("<script", "writes markup"),
	("innerHTML", "writes markup"),
	("outerHTML", "writes markup"),
	("insertAdjacentHTML", "writes markup"),
	("document.write", "writes markup"),
	(".html(", "writes markup"),
	("document.cookie", "reads the session"),
	("csrf_token", "reads the session"),
	("localStorage", "stores in the browser"),
	("sessionStorage", "stores in the browser"),
	("indexedDB", "stores in the browser"),
	("postMessage", "talks to another page"),
	("window.open", "opens another page"),
	("location.href", "leaves the page"),
	("location.assign", "leaves the page"),
	("location.replace", "leaves the page"),
	('setTimeout("', "runs text as code"),
	("setTimeout('", "runs text as code"),
	("setInterval", "runs on a timer"),
)

#: The record events a server extension may run on.
EVENTS = (
	"Before Insert",
	"Before Validate",
	"Before Save",
	"After Insert",
	"After Save",
	"Before Submit",
	"After Submit",
	"Before Cancel",
	"After Cancel",
	"Before Save (Submitted Document)",
	"After Save (Submitted Document)",
	"Before Delete",
	"After Delete",
)

#: The views a screen extension may run on.
VIEWS = ("Form", "List")


@dataclass
class Site:
	"""What the guard needs to know: the kinds the administrator may open
	and, for each, the fields they may not read."""

	kinds: set = field(default_factory=set)
	unseen: dict = field(default_factory=dict)
	doctypes: set = field(default_factory=set)

	def hidden(self, doctype: str) -> set:
		return set(self.unseen.get(doctype) or ())


class Refused(Exception):
	"""The code does something an extension may not. Its text says what."""


def _dotted(node) -> str:
	parts = []
	while isinstance(node, ast.Attribute):
		parts.append(node.attr)
		node = node.value
	if isinstance(node, ast.Name):
		parts.append(node.id)
	return ".".join(reversed(parts))


def on_server(code: str, doctype: str, site: Site) -> set:
	"""Refuse server code that reaches past what it may; return every kind of
	record it names, the record's own included."""
	try:
		tree = ast.parse(code or "", mode="exec")
	except SyntaxError as error:
		raise Refused(f"It is not Python: {error.msg} on line {error.lineno}.") from None
	touched = {doctype}
	words = set()
	for node in ast.walk(tree):
		if isinstance(node, (ast.Import, ast.ImportFrom)):
			raise Refused("It imports a module.")
		if isinstance(node, ast.Attribute):
			if node.attr in UNSAFE_IN_FRAPPE:
				raise Refused(
					f"It uses {node.attr}, which frappe's sandbox refuses: build the text with an f-string or + instead."
				)
			if node.attr in REFUSED_ATTRIBUTES or node.attr.startswith("_"):
				raise Refused(f"It uses {node.attr}, which no extension may.")
			words.add(node.attr)
		if isinstance(node, ast.Name):
			if node.id in REFUSED_NAMES or (node.id.startswith("_") and node.id != "_"):
				raise Refused(f"It uses {node.id}, which no extension may.")
			words.add(node.id)
		if isinstance(node, ast.keyword) and node.arg in REFUSED_KEYWORDS:
			raise Refused(f"It sets {node.arg}, which no extension may.")
		if isinstance(node, ast.Constant) and isinstance(node.value, str):
			words.add(node.value)
			if node.value in site.doctypes:
				touched.add(node.value)
		if isinstance(node, ast.Call):
			name = _dotted(node.func).rsplit(".", 1)[-1]
			if name in NAMES_A_KIND and _dotted(node.func).startswith("frappe"):
				first = node.args[0] if node.args else None
				if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
					raise Refused(f"It calls {name} without naming the kind of record as plain text.")
				touched.add(first.value)
	_kinds(touched, site)
	_fields(words, touched, site)
	return touched


def on_screen(code: str, doctype: str, site: Site) -> set:
	"""Refuse screen code that does more than change the form and speak to
	the person; return the kinds it names."""
	text = code or ""
	for needle, why in REFUSED_ON_SCREEN:
		if needle in text:
			raise Refused(f"It {why} ({needle.rstrip('(')}), which an extension on the screen may not.")
	touched = {doctype}
	words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
	for quoted in re.findall(r"""["'`]([^"'`\n]{1,140})["'`]""", text):
		words.add(quoted)
		if quoted in site.doctypes:
			touched.add(quoted)
	_kinds(touched, site)
	_fields(words, touched, site)
	return touched


def _kinds(touched: set, site: Site) -> None:
	for doctype in sorted(touched):
		if doctype not in site.kinds:
			raise Refused(f"It touches {doctype}, which is not a kind of record you may open here.")


def _fields(words: set, touched: set, site: Site) -> None:
	for doctype in sorted(touched):
		hidden = sorted(site.hidden(doctype) & words)
		if hidden:
			raise Refused(f"It reads {', '.join(hidden)} on {doctype}, which you may not read.")


#: What an extension's errors are written down under, then its name.
TITLE = "OneStudio: "

#: How every server extension is run: an error in it is written down and the
#: record still saves, while a message it means to stop the save with still does.
WRAPPED = """# Written by OneAI in OneStudio. Change it by asking OneAI.
try:
{body}
except frappe.ValidationError:
	raise
except Exception:
	frappe.log_error(title={title}, reference_doctype=doc.doctype, reference_name=doc.name)
"""


def wrapped(name: str, code: str) -> str:
	body = "\n".join(f"\t{line}" if line.strip() else "" for line in (code or "pass").splitlines())
	return WRAPPED.format(title=repr(f"{TITLE}{name}"), body=body or "\tpass")


#: How every screen extension is run, the same as on the server: each handler
#: it gives `frappe.ui.form.on` runs inside a `try`, a `frappe.throw` it means
#: still stops the save, and anything else it trips on is written down
#: (extensions.tripped) and the form goes on. Its `frappe` is frappe's own,
#: with those two wrapped; everything else is frappe's.
WRAPPED_ON_SCREEN = """// Written by OneAI in OneStudio. Change it by asking OneAI.
(function () {{
	const extension = {name};
	const tripped = (error, frm) => {{
		if (error && error.one_studio_meant) throw error;
		console.error(error);
		frappe
			.xcall("onedesk.one_studio.extensions.tripped", {{
				extension,
				record: (frm && frm.docname) || null,
				message: String((error && error.message) || error).slice(0, 500),
				stack: String((error && error.stack) || "").slice(0, 2000),
			}})
			.catch(() => {{}});
	}};
	const guarded = (handler) => (...args) => {{
		try {{
			const out = handler(...args);
			if (out && typeof out.catch === "function") out.catch((error) => tripped(error, args[0]));
			return out;
		}} catch (error) {{
			tripped(error, args[0]);
		}}
	}};
	const form = Object.create(frappe.ui.form);
	form.on = form.on_change = (doctype, fieldname, handler) => {{
		if (typeof handler === "function") return frappe.ui.form.on(doctype, fieldname, guarded(handler));
		const handlers = {{}};
		for (const [key, one] of Object.entries(fieldname || {{}}))
			handlers[key] = typeof one === "function" ? guarded(one) : one;
		return frappe.ui.form.on(doctype, handlers);
	}};
	const ui = Object.create(frappe.ui);
	ui.form = form;
	const scoped = Object.create(frappe);
	scoped.ui = ui;
	scoped.throw = (...args) => {{
		try {{
			frappe.throw(...args);
		}} catch (error) {{
			error.one_studio_meant = true;
			throw error;
		}}
	}};
	(function (frappe) {{
		try {{
{body}
		}} catch (error) {{
			tripped(error);
		}}
	}})(scoped);
}})();
"""


def wrapped_on_screen(name: str, code: str) -> str:
	"""A screen extension as frappe's Client Script runs it. Pure."""
	body = "\n".join(f"\t\t\t{line}" if line.strip() else "" for line in (code or "").splitlines())
	return WRAPPED_ON_SCREEN.format(name=json.dumps(name), body=body)
