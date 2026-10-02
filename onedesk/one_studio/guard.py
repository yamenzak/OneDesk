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

#: The names a server extension's code finds already there: frappe's
#: safe_exec globals and RestrictedPython's builtins, as get_safe_globals()
#: answered on frappe develop (Oct 2026), and print, which RestrictedPython
#: turns into its own collector. Anything else the code reads it must have
#: set itself, or it runs into a NameError on every save.
IN_THE_SANDBOX = frozenset(
	"""
	ArithmeticError AssertionError AttributeError BaseException Exception IndexError KeyError
	LookupError NameError NotImplementedError OverflowError RuntimeError StopIteration TypeError
	ValueError ZeroDivisionError Ellipsis False None True _ abs all any as_json bool bytes callable
	chr complex dict divmod enumerate float frappe hash hex id int isinstance issubclass json len
	list log max min oct ord orjson pow print range repr round scrub set slice sorted str sum tuple
	zip doc
	""".split()
)

#: frappe.utils' own, which a writer reaches for bare: what to say instead.
UTILS = frozenset(
	"""
	add_days add_months add_to_date add_years cint cstr date_diff flt fmt_money format_date
	format_datetime getdate get_datetime get_first_day get_last_day month_diff now now_datetime
	nowdate nowtime today time_diff time_diff_in_hours time_diff_in_seconds rounded money_in_words
	in_words get_time pretty_date strip_html escape_html
	""".split()
)

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

#: When a scheduled server extension runs: frappe's scheduler, which has no
#: record of its own to hand it, as Administrator. "On a Schedule" takes a
#: cron line (extensions.cron_refused).
SCHEDULED = ("Every Hour", "Every Day", "Every Week", "Every Month", "On a Schedule")

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


def _defined(tree) -> None:
	"""Refuse a name the code reads that neither the sandbox nor the code
	itself gives it, before it runs into a NameError on every save."""
	own = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
			own.add(node.id)
		elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
			if isinstance(node, ast.FunctionDef):
				own.add(node.name)
			arguments = node.args
			for arg in arguments.posonlyargs + arguments.args + arguments.kwonlyargs:
				own.add(arg.arg)
			for arg in (arguments.vararg, arguments.kwarg):
				if arg:
					own.add(arg.arg)
		elif isinstance(node, ast.ExceptHandler) and node.name:
			own.add(node.name)
	for node in ast.walk(tree):
		if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
			if node.id in own or node.id in IN_THE_SANDBOX:
				continue
			if node.id in UTILS:
				raise Refused(
					f"It uses {node.id} on its own, which is not there: write frappe.utils.{node.id}."
				)
			raise Refused(
				f"It uses {node.id}, which is not there in a server extension and is not set by the code."
			)


def on_server(code: str, doctype: str, site: Site, event: str | None = None) -> set:
	"""Refuse server code that reaches past what it may; return every kind of
	record it names, the record's own included."""
	try:
		tree = ast.parse(code or "", mode="exec")
	except SyntaxError as error:
		raise Refused(f"It is not Python: {error.msg} on line {error.lineno}.") from None
	touched = {doctype}
	words = set()
	# doc.add_comment("Comment", …) names a comment's type, not the kind.
	said = {
		id(node.args[0])
		for node in ast.walk(tree)
		if isinstance(node, ast.Call)
		and isinstance(node.func, ast.Attribute)
		and node.func.attr == "add_comment"
		and node.args
	}
	_defined(tree)
	if event in SCHEDULED and any(
		isinstance(node, ast.Name) and node.id == "doc" for node in ast.walk(tree)
	):
		raise Refused(
			"It uses doc, which a scheduled extension does not have: it runs on its own, so find the "
			f'records it works on with frappe.get_list("{doctype}", filters=…, pluck="name") and frappe.get_doc.'
		)
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
			if node.attr == "is_new" and (event or "").startswith("After"):
				# Measured: frappe has saved the record by After Insert, so
				# is_new() is already false there and the code under it never ran.
				raise Refused(
					f"It asks doc.is_new() {event}, when the record is already saved and it is never true: "
					"After Insert runs only for a new record, so it needs no check."
				)
			words.add(node.attr)
		if isinstance(node, ast.Name):
			if node.id in REFUSED_NAMES or (node.id.startswith("_") and node.id != "_"):
				raise Refused(f"It uses {node.id}, which no extension may.")
			words.add(node.id)
		if isinstance(node, ast.keyword) and node.arg in REFUSED_KEYWORDS:
			raise Refused(f"It sets {node.arg}, which no extension may.")
		if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in said:
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


#: What screen code may ask the server, all of it reading, all of it as the
#: person whose screen it is: frappe answers these with that person's own
#: permissions, so a lookup shows them nothing they could not open.
LOOKUPS = ("get_value", "get_list", "count", "exists")

_DB = re.compile(r"frappe\.db\.([A-Za-z_]+)")

#: Text the person is shown, __("Domain"): a label, not the kind of that name.
_SAID = re.compile(r"""\b__\(\s*(["'`])[^"'`\n]*\1""")


def on_screen(code: str, doctype: str, site: Site) -> set:
	"""Refuse screen code that does more than change the form, look things up
	as the person, and speak to them; return the kinds it names."""
	text = code or ""
	for needle, why in REFUSED_ON_SCREEN:
		if needle in text:
			raise Refused(f"It {why} ({needle.rstrip('(')}), which an extension on the screen may not.")
	for called in _DB.findall(text):
		if called not in LOOKUPS:
			raise Refused(
				f"It calls frappe.db.{called}, which changes or reaches past what the person sees; "
				f"on the screen only {', '.join('frappe.db.' + one for one in LOOKUPS)} may be used."
			)
	# A page extension on OneMail or OneCalendar names no kind of its own: it
	# sees only what its page hands it.
	touched = {doctype} if doctype else set()
	words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
	for quoted in re.findall(r"""["'`]([^"'`\n]{1,140})["'`]""", _SAID.sub("__(", text)):
		words.add(quoted)
		if quoted in site.doctypes:
			touched.add(quoted)
	_kinds(touched, site)
	_fields(words, touched, site)
	return touched


#: What it listens for: an event, or the place and its event as
#: places.py names them ("conversation" or "onemail.conversation").
_LISTENS = re.compile(r"""\bone\.on\(\s*["'`]([A-Za-z_.]+)["'`]""")


def on_page(code: str, page: str, events: set, doctype: str, site: Site) -> set:
	"""Refuse page code that listens for what its page does not have
	(`events`, from places.py), and everything screen code may not do.
	Return the kinds it names."""
	heard = {one.rsplit(".", 1)[-1] for one in _LISTENS.findall(code or "")}
	if not heard:
		first = sorted(events)[0] if events else "<event>"
		raise Refused(
			f'It does not listen for anything: write one.on("{first}", (data, page) => {{ ... }}), '
			f"with one of {page}'s events: {', '.join(sorted(events))}."
		)
	strange = sorted(heard - set(events))
	if strange:
		raise Refused(f"It listens for {', '.join(strange)}, which {page} does not have; it has {', '.join(sorted(events))}.")
	return on_screen(code, doctype, site)


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

#: A scheduled one has no record: its error is written down under its name
#: alone, and a message it means stops only that run.
WRAPPED_SCHEDULED = """# Written by OneAI in OneStudio. Change it by asking OneAI.
try:
{body}
except Exception:
	frappe.log_error(title={title})
"""


def wrapped(name: str, code: str, scheduled: bool = False) -> str:
	body = "\n".join(f"\t{line}" if line.strip() else "" for line in (code or "pass").splitlines())
	held = WRAPPED_SCHEDULED if scheduled else WRAPPED
	return held.format(title=repr(f"{TITLE}{name}"), body=body or "\tpass")


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
