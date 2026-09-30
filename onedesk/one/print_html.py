"""HTML on a workspace's printed page: a builder's HTML block, and a letter
head whose top or foot is written in HTML. docs/DESK-COVERAGE.md, stage 3.

A printed page is drawn on this site's address, where a script runs as
whoever opens it, and a PDF is drawn by a browser on the server, which fetches
whatever the page points at. And an HTML block is a Jinja template, which
frappe renders with globals that read any table (`frappe.db.sql`,
`frappe.get_all`) and fetch any address (`make_get_request`). So what a
workspace administrator writes in HTML is held to three things:

- **The template reads the record and nothing else** (`check_template`): the
  record's fields and rows (`doc.grand_total`, `{% for row in doc.items %}`),
  `doc.get_formatted(...)` and `doc.get(...)`, conditions, loops, arithmetic,
  `_()` and plain filters. It is rendered in a sandbox of its own that holds
  only those (`render`), escaping every value, never in frappe's.
- **The markup is markup for paper** (`clean`): text, headings, tables, lists,
  images and links, with scripts, forms, frames, media and event handlers
  taken out.
- **Nothing is fetched from elsewhere**: an image is this site's file or an
  inline image, and a style may not import or point off this site.

A block the workspace saves is marked `one_sandboxed`, and onedesk's copy of
frappe's HTML block macro (templates/print_format/macros/HTML.html) renders a
marked block through `render`. A block frappe or its System Managers wrote is
unmarked and renders as frappe renders it. A letter head's HTML is rendered by
frappe as it is stored (printview.get_letter_head), so it holds no template at
all and is stored already cleaned.
"""

import re

import frappe
import nh3
from frappe import _
from jinja2 import nodes
from jinja2.exceptions import TemplateError
from jinja2.sandbox import ImmutableSandboxedEnvironment

from onedesk.one_storage import store

#: The mark a workspace's saved HTML block carries.
MARK = "one_sandboxed"

#: Where this site's files are served: frappe's folders, or One's store (one_storage).
FILES = rf"(/files/|/private/files/|{re.escape(store.FETCH)}\?)"

#: A picture this site serves, or one written inline.
IMAGE = re.compile(rf"""^({FILES}[^"'<>\s]+|data:image/[a-z+.-]+;base64,[A-Za-z0-9+/=\s]+)$""", re.I)

#: What a link may open. A link is not fetched when the page is drawn.
LINK = re.compile(r"^(https?:|mailto:|tel:|#|/)", re.I)

#: What a URL in a style may point at.
STYLE_URL = re.compile(rf"""url\(\s*['"]?\s*({FILES}|data:image/)""", re.I)

#: What a printed page is made of.
TAGS = frozenset(
	(
		"a abbr address article aside b big blockquote br caption center cite code col colgroup dd "
		"del div dl dt em figcaption figure font footer h1 h2 h3 h4 h5 h6 header hr i img ins kbd li "
		"mark ol p pre q s samp section small span strike strong sub sup table tbody td tfoot th thead "
		"time tr tt u ul var"
	).split()
)

#: What those may say about themselves; a URL only where it is checked below.
ATTRIBUTES = {
	"*": {
		"align",
		"alt",
		"bgcolor",
		"border",
		"cellpadding",
		"cellspacing",
		"class",
		"color",
		"colspan",
		"dir",
		"face",
		"headers",
		"height",
		"id",
		"lang",
		"nowrap",
		"rowspan",
		"scope",
		"size",
		"span",
		"style",
		"title",
		"valign",
		"width",
	},
	"a": {"href"},
	"img": {"src"},
	"ol": {"start", "type"},
	"time": {"datetime"},
}

#: Filters a template may use: the ones that shape a value, none that marks it safe.
FILTERS = frozenset(
	(
		"abs capitalize center count d default e escape first float format int join last length lower "
		"replace reverse round sort string striptags sum title trim truncate upper wordcount"
	).split()
)

#: Tests a template may use.
TESTS = frozenset("defined undefined none number string odd even divisibleby eq ne lt gt le ge in".split())

#: What a template may call on a record or a row.
METHODS = frozenset(("get", "get_formatted"))

#: The names a template starts from.
NAMES = frozenset(("doc", "loop", "_"))

#: Everything else a template may be made of.
NODES = (
	nodes.Template,
	nodes.Output,
	nodes.TemplateData,
	nodes.Const,
	nodes.Name,
	nodes.Getattr,
	nodes.Getitem,
	nodes.Slice,
	nodes.If,
	nodes.For,
	nodes.Assign,
	nodes.CondExpr,
	nodes.Compare,
	nodes.Operand,
	nodes.And,
	nodes.Or,
	nodes.Not,
	nodes.Neg,
	nodes.Pos,
	nodes.Add,
	nodes.Sub,
	nodes.Mul,
	nodes.Div,
	nodes.FloorDiv,
	nodes.Mod,
	nodes.Concat,
	nodes.List,
	nodes.Tuple,
	nodes.Filter,
	nodes.Test,
	nodes.Call,
	nodes.Keyword,
)


def _sandbox() -> ImmutableSandboxedEnvironment:
	env = ImmutableSandboxedEnvironment(autoescape=True)
	env.filters = {key: value for key, value in env.filters.items() if key in FILTERS}
	env.tests = {key: value for key, value in env.tests.items() if key in TESTS}
	env.globals = {}
	return env


SANDBOX = _sandbox()


def check_template(text: str, where: str) -> None:
	"""Refuse a template that reaches past the record it prints."""
	try:
		tree = SANDBOX.parse(text or "")
	except TemplateError as e:
		frappe.throw(_("{0}: the template does not read: {1}").format(where, str(e)))
	named = set(NAMES) | {one.name for one in tree.find_all(nodes.Name) if one.ctx in ("store", "param")}
	for node in _walk(tree):
		refused = _refused(node, named)
		if refused:
			frappe.throw(
				_(
					"{0}: an HTML block may use the record's fields and rows, doc.get_formatted, "
					"conditions, loops and plain filters; not {1}."
				).format(where, refused)
			)


def _walk(node):
	yield node
	for child in node.iter_child_nodes():
		yield from _walk(child)


def _refused(node, named: set) -> str | None:
	if type(node) not in NODES:
		return type(node).__name__
	if isinstance(node, nodes.Name) and node.name not in named:
		return node.name
	if isinstance(node, nodes.Getattr) and node.attr.startswith("_"):
		return node.attr
	if isinstance(node, nodes.Getitem) and isinstance(node.arg, nodes.Const):
		if str(node.arg.value).startswith("_"):
			return str(node.arg.value)
	if isinstance(node, nodes.Filter) and node.name not in FILTERS:
		return f"|{node.name}"
	if isinstance(node, nodes.Test) and node.name not in TESTS:
		return f"is {node.name}"
	if isinstance(node, nodes.Call):
		if node.dyn_args or node.dyn_kwargs:
			return "*args"
		called = node.node
		if isinstance(called, nodes.Name) and called.name == "_":
			return None
		if isinstance(called, nodes.Getattr) and called.attr in METHODS:
			return None
		return "a call"
	return None


def render(text: str, doc) -> str:
	"""A workspace's HTML block, drawn for one record: its template in the
	sandbox, every value escaped, and the markup cleaned."""
	if not text:
		return ""
	try:
		check_template(text, _("HTML"))
		drawn = SANDBOX.from_string(text).render(doc=doc, _=_)
	except Exception:
		# A block that no longer reads prints nothing, as frappe's own does.
		frappe.clear_last_message()
		return ""
	return clean(drawn)


def _style_ok(value: str) -> bool:
	lowered = value.lower()
	if "<" in value or "@import" in lowered or "expression(" in lowered or "javascript:" in lowered:
		return False
	return all(STYLE_URL.match(value, found.start()) for found in re.finditer(r"url\(", value, re.I))


def _attribute(tag: str, attribute: str, value: str) -> str | None:
	if attribute == "src":
		return value if IMAGE.match(value.strip()) else None
	if attribute == "href":
		return value if LINK.match(value.strip()) else None
	if attribute == "style":
		return value if _style_ok(value) else None
	return value


#: A picture whose address was taken out, which would print as nothing.
EMPTY_IMAGE = re.compile(r"<img(?![^>]*\ssrc=)[^>]*>", re.I)


def clean(html: str) -> str:
	"""HTML as a printed page may carry it."""
	if not html:
		return html or ""
	return EMPTY_IMAGE.sub("", _cleaned(html))


def _cleaned(html: str) -> str:
	return nh3.clean(
		html,
		tags=set(TAGS),
		attributes={key: set(value) for key, value in ATTRIBUTES.items()},
		attribute_filter=_attribute,
		clean_content_tags={"script", "style"},
		strip_comments=True,
		url_schemes={"http", "https", "mailto", "tel", "data"},
	)


#: A template, wherever a letter head would carry one.
TEMPLATE = re.compile(r"\{[{%#]")


def letter_head_html(html: str | None, where: str) -> str | None:
	"""A letter head's HTML as it is stored: no template, cleaned, with each
	[icon:name] it asks for drawn (letter_heads.icons_in)."""
	if not html:
		return html
	from onedesk.one import letter_heads

	html = letter_heads.icons_in(html)
	if TEMPLATE.search(html):
		frappe.throw(_("{0}: a letter head is written as it prints, without template tags.").format(where))
	cleaned = clean(html)
	if TEMPLATE.search(cleaned):
		frappe.throw(_("{0}: a letter head is written as it prints, without template tags.").format(where))
	return cleaned


def one_html_block(html: str, doc) -> str:
	"""The HTML block macro's way in (hooks.py jinja): a marked block, drawn."""
	return render(html, doc)
