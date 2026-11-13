"""OneGuard's rules for exploitable code in One's own Python (docs/STANDARD.md,
points 2 and 18). Each reads the source, names what it finds as
`folder/file.py:function`, and is proven on an example it must catch.

What was there when a rule arrived is in its allowance (oneguard_allowed.py),
each with why it is safe or "to fix". A rule fails on anything new, and on an
allowance that no longer happens, so the count only falls.

What counts as a permission check (`_checks`): frappe's own (`has_permission`,
`check_permission`, `only_for`, `get_list`, `get_doc(..., check_permission=True)`,
a save, insert, submit or cancel, which frappe checks, `delete_doc`), a raised
`PermissionError`, `frappe.get_roles`, one of frappe's, erpnext's or hrms's own
endpoints that checks (`CHECKED_UPSTREAM`), anything scoped to
`frappe.session.user`, or a call to a function of ours that does any of these,
however deep.
"""

import ast
import functools
import math
import re
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree  # noqa: E402

from tests.guards import oneguard_allowed as allowed  # noqa: E402

CHECKS = {"has_permission", "check_permission", "only_for", "has_website_permission", "throw_permission_error", "get_list"}
FRAPPE_HELD = {"insert", "save", "submit", "cancel"}
CHECKED_UPSTREAM = {"getdoc", "get_docinfo", "search_link", "search_widget", "get_communications", "get_project_tasks"}
UPSTREAM = ("frappe.", "erpnext.", "hrms.")
READS = {
	"frappe.get_all",
	"frappe.get_doc",
	"frappe.get_cached_doc",
	"frappe.get_last_doc",
	"frappe.get_single",
	"frappe.get_value",
	"frappe.get_cached_value",
	"frappe.get_single_value",
	"frappe.set_value",
}
NOT_RECORDS = {"commit", "rollback", "savepoint", "release_savepoint", "escape", "after_commit", "before_commit", "after_rollback"}
DB_WRITES = {
	"set_value",
	"delete",
	"insert",
	"set_single_value",
	"set_default",
	"truncate",
	"bulk_insert",
	"bulk_update",
	"multisql",
}
WRITES = {
	"frappe.delete_doc",
	"frappe.set_value",
	"frappe.rename_doc",
	"frappe.defaults.set_user_default",
	"frappe.defaults.set_global_default",
	"frappe.defaults.clear_user_default",
}
SENDS = {"frappe.enqueue", "frappe.enqueue_doc", "frappe.sendmail"}
DOC_WRITES = {"insert", "save", "submit", "cancel", "db_set", "db_insert", "db_update", "add_comment"}
SQL_WRITES = ("insert", "update", "delete", "replace", "alter", "create", "drop", "truncate")
SAFE_WRAPS = {"int", "cint", "flt", "float", "len", "escape", "bool", "str_to_int"}
WHOLE = {"get_doc", "get_cached_doc", "get_last_doc", "new_doc", "get_single"}
SECRET_GIVEN = re.compile(
	r"(?:secret|token|api_?key|password|passwd|private_?key|access_?key|signing_?key)\w*[\"']?\s*(?::|=)\s*[\"'](?P<value>[^\"'\s]{20,})[\"']",
	re.I,
)
SECRET_TAIL = re.compile(r"[:=]\s*[\"'][^\"'\s]{20,}[\"']")
"""What every SECRET_GIVEN ends with, found far faster: a file without it is
not read for SECRET_GIVEN."""
SECRET_SHAPES = re.compile(
	r"(?<![\w-])("
	r"sk_(?:live|test)_[0-9A-Za-z]{16,}"
	r"|rk_(?:live|test)_[0-9A-Za-z]{16,}"
	r"|whsec_[0-9A-Za-z]{20,}"
	r"|gh[pousr]_[0-9A-Za-z]{30,}"
	r"|github_pat_[0-9A-Za-z_]{40,}"
	r"|xox[abprs]-[0-9A-Za-z-]{10,}"
	r"|AKIA[0-9A-Z]{16}"
	r"|AIza[0-9A-Za-z_-]{35}"
	r"|sk-ant-[0-9A-Za-z_-]{20,}"
	r"|sk-(?:proj-)?[0-9A-Za-z]{32,}"
	r"|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
	r"|Bearer [0-9A-Za-z._~+/-]{24,}=*"
	r")"
)
SECRET_SUFFIXES = {".py", ".js", ".ts", ".vue", ".json", ".sh", ".toml", ".yml", ".yaml", ".md", ".html", ".txt", ".cfg", ".ini"}


def _walk(node) -> tuple:
	"""ast.walk, at about twice its speed, as a tuple."""
	found = [node]
	for one in found:
		for field in one._fields:
			value = getattr(one, field, None)
			if isinstance(value, list):
				found += [item for item in value if isinstance(item, ast.AST)]
			elif isinstance(value, ast.AST):
				found.append(value)
	return tuple(found)


def dotted(node) -> str:
	if isinstance(node, ast.Attribute):
		head = dotted(node.value)
		return f"{head}.{node.attr}" if head else ""
	if isinstance(node, ast.Name):
		return node.id
	return ""


def called(call: ast.Call) -> str:
	return dotted(call.func) or (call.func.attr if isinstance(call.func, ast.Attribute) else "")


def _kw(call: ast.Call, name: str):
	return next((one.value for one in call.keywords if one.arg == name), None)


def _true(node) -> bool:
	return node is not None and not (isinstance(node, ast.Constant) and not node.value)


class Function(NamedTuple):
	module: str
	file: str
	name: str
	node: ast.FunctionDef
	method: bool
	nodes: tuple

	@property
	def key(self) -> str:
		return f"{self.file}:{self.name}"


class Code:
	"""The app's Python, indexed by module and function, with each call to a
	function of ours resolved through the module's imports."""

	def __init__(self, sources: dict[str, str]):
		self.functions: dict[tuple[str, str], Function] = {}
		self.imports: dict[str, dict[str, str]] = {}
		self.trees: dict[str, ast.Module] = {}
		for file, source in sources.items():
			module, package = _module(file)
			body = tree.syntax(source)
			self.trees[file] = body
			walked = []
			for node in body.body:
				if isinstance(node, ast.FunctionDef):
					nodes = _walk(node)
					self.functions[(module, node.name)] = Function(module, file, node.name, node, False, nodes)
					walked += nodes
				elif isinstance(node, ast.ClassDef):
					for one in node.body:
						nodes = _walk(one)
						walked += nodes
						if isinstance(one, ast.FunctionDef):
							name = f"{node.name}.{one.name}"
							self.functions[(module, name)] = Function(module, file, name, one, True, nodes)
				else:
					walked += _walk(node)
			self.imports[module] = self._imports(walked, package)
		self.calls = {key: self._calls(one) for key, one in self.functions.items()}

	@classmethod
	@functools.cache
	def of_app(cls) -> "Code":
		"""The app's Python, or in a change-mode run (scripts/tree.py) the
		changed files and every file of ours they import, however deep, so
		each of their calls resolves as it does in the whole app."""
		files = {
			str(path.relative_to(tree.APP)): path
			for path in tree.python()
			if "tests" not in path.relative_to(tree.APP).parts and not path.name.startswith("test_")
		}
		if tree.whole():
			return cls({file: tree.text(path) for file, path in files.items()})
		by_module = {_module(file)[0]: file for file in files}
		todo = [file for file, path in files.items() if tree.judged(path)]
		seen = set(todo)
		while todo:
			file = todo.pop()
			for one in _imported(tree.text(files[file]), _module(file)[1]):
				if by_module.get(one, file) not in seen:
					seen.add(by_module[one])
					todo.append(by_module[one])
		return cls({file: tree.text(files[file]) for file in sorted(seen)})

	@staticmethod
	def _imports(nodes: list, package: str) -> dict[str, str]:
		found = {}
		for node in nodes:
			if isinstance(node, ast.ImportFrom):
				base = node.module or ""
				if node.level:
					parts = package.split(".")
					parts = parts[: len(parts) - (node.level - 1)] if node.level > 1 else parts
					base = ".".join([*parts, *([node.module] if node.module else [])])
				for one in node.names:
					found[one.asname or one.name] = f"{base}.{one.name}"
			elif isinstance(node, ast.Import):
				for one in node.names:
					found[one.asname or one.name.split(".")[0]] = one.name if one.asname else one.name.split(".")[0]
		return found

	def target(self, module: str, call: ast.Call) -> str:
		"""Where a call goes, as a dotted path, through the module's imports."""
		func = call.func
		if isinstance(func, ast.Name):
			return self.imports[module].get(func.id) or (f"{module}.{func.id}" if (module, func.id) in self.functions else func.id)
		if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in self.imports[module]:
			return f"{self.imports[module][func.value.id]}.{func.attr}"
		return called(call)

	def _calls(self, function: Function) -> set[tuple[str, str]]:
		found = set()
		for call in function.nodes:
			if isinstance(call, ast.Call):
				module, _, name = self.target(function.module, call).rpartition(".")
				if (module, name) in self.functions and (module, name) != (function.module, function.name):
					found.add((module, name))
		return found

	def closure(self, direct, depth: int | None = None) -> dict[tuple[str, str], bool]:
		"""Whether each function, or one of ours it calls (up to `depth` calls
		down, or however deep), does what `direct` looks for."""
		held = {key: direct(one) for key, one in self.functions.items()}
		moved, steps = True, 0
		while moved and (depth is None or steps < depth):
			moved, steps = False, steps + 1
			before = dict(held)
			for key, calls in self.calls.items():
				if not before[key] and any(before[one] for one in calls):
					held[key] = moved = True
		return held

	def whitelisted(self, function: Function) -> ast.expr | None:
		for one in function.node.decorator_list:
			if "whitelist" in dotted(one.func if isinstance(one, ast.Call) else one):
				return one
		return None

	@staticmethod
	def guest(decorator) -> bool:
		return isinstance(decorator, ast.Call) and _true(_kw(decorator, "allow_guest"))

	def methods(self, function: Function, decorator) -> set[str]:
		said = _kw(decorator, "methods") if isinstance(decorator, ast.Call) else None
		if said is None:
			return {"GET", "POST"}
		if isinstance(said, ast.Name):
			said = next(
				(
					node.value
					for node in self.trees[function.file].body
					if isinstance(node, ast.Assign) and any(dotted(one) == said.id for one in node.targets)
				),
				said,
			)
		if isinstance(said, ast.Constant):
			return {said.value}
		if isinstance(said, (ast.List, ast.Tuple, ast.Set)):
			return {one.value for one in said.elts if isinstance(one, ast.Constant)}
		return {"GET", "POST"}


def _checks(code: Code, function: Function) -> bool:
	for node in function.nodes:
		if isinstance(node, ast.Raise) and node.exc is not None and "PermissionError" in ast.unparse(node.exc):
			return True
		if isinstance(node, ast.Attribute) and dotted(node) == "frappe.session.user":
			return True
		if not isinstance(node, ast.Call):
			continue
		name = called(node)
		target = code.target(function.module, node)
		if name.rsplit(".", 1)[-1] in CHECKS or name == "frappe.get_roles" or _true(_kw(node, "check_permission")):
			return True
		if target.startswith(UPSTREAM) and target.rsplit(".", 1)[-1] in CHECKED_UPSTREAM:
			return True
		if isinstance(node.func, ast.Attribute) and node.func.attr in FRAPPE_HELD and not node.args and _kw(node, "ignore_permissions") is None:
			return True
		if name == "frappe.delete_doc" and _kw(node, "ignore_permissions") is None:
			return True
	return False


def _reads(function: Function) -> bool:
	for node in function.nodes:
		if isinstance(node, ast.Assign) and any("ignore_permissions" in ast.unparse(one) for one in node.targets):
			return True
		if not isinstance(node, ast.Call):
			continue
		name = called(node)
		if name.startswith("frappe.db.") and name.rsplit(".", 1)[-1] not in NOT_RECORDS:
			return True
		if name.startswith("frappe.qb."):
			return True
		if name in READS and not (name == "frappe.get_doc" and len(node.args) == 1 and isinstance(node.args[0], ast.Dict)):
			return True
		if _true(_kw(node, "ignore_permissions")):
			return True
	return False


def _sends(function: Function) -> bool:
	return any(isinstance(node, ast.Call) and called(node) in SENDS for node in function.nodes)


def _writes(function: Function) -> bool:
	for node in function.nodes:
		if not isinstance(node, ast.Call):
			continue
		name = called(node)
		if name.startswith("frappe.db.") and name.rsplit(".", 1)[-1] in DB_WRITES or name in WRITES:
			return True
		if name == "frappe.db.sql" and node.args and _literal(node.args[0]).lstrip().lower().startswith(SQL_WRITES):
			return True
		if (
			isinstance(node.func, ast.Attribute)
			and node.func.attr in DOC_WRITES
			and not name.startswith("frappe.cache")
			and not (node.func.attr in FRAPPE_HELD and node.args)
		):
			return True
	return False


def _literal(node) -> str:
	if isinstance(node, ast.Constant) and isinstance(node.value, str):
		return node.value
	if isinstance(node, ast.JoinedStr):
		return "".join(one.value for one in node.values if isinstance(one, ast.Constant))
	return ""


def unchecked(code: Code) -> set[str]:
	"""Rule 1: a whitelisted function, not for guests, that reads or writes
	records past frappe's own checks and checks nothing on the way."""
	reads, checks = code.closure(_reads), code.closure(lambda one: _checks(code, one))
	return {
		one.key
		for key, one in code.functions.items()
		if not one.method
		and (decorator := code.whitelisted(one)) is not None
		and not code.guest(decorator)
		and reads[key]
		and not checks[key]
	}


def written_by_get(code: Code) -> set[str]:
	"""Rule 2: a whitelisted function that changes data and still answers a GET:
	it writes, or a helper of ours two calls down writes, or it sends mail or
	starts a job itself."""
	writes = code.closure(_writes, depth=2)
	return {
		one.key
		for key, one in code.functions.items()
		if (decorator := code.whitelisted(one)) is not None
		and (writes[key] or _sends(one))
		and "GET" in code.methods(one, decorator)
	}


def _inputs(function: Function) -> set[str]:
	arguments = function.node.args
	every = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg]
	return {one.arg for one in every if one is not None and one.arg not in ("self", "cls")}


def _input_in(node, inputs: set[str]) -> bool:
	"""An expression put into a query that carries an input, unless it is
	cast to a number, escaped, only builds placeholders, or picks between
	two texts of its own."""
	if isinstance(node, ast.IfExp):
		return _input_in(node.body, inputs) or _input_in(node.orelse, inputs)
	if isinstance(node, ast.Call) and called(node).rsplit(".", 1)[-1] in SAFE_WRAPS:
		return False
	if any(isinstance(one, ast.Constant) and isinstance(one.value, str) and re.search(r"%(\(\w+\))?s", one.value) for one in ast.walk(node)):
		return False
	for one in ast.walk(node):
		if isinstance(one, ast.Name) and one.id in inputs:
			return True
		if dotted(one).startswith(("frappe.form_dict", "frappe.request", "frappe.local.form_dict")):
			return True
	return False


def _built(node, inputs: set[str]) -> bool:
	if isinstance(node, ast.JoinedStr):
		return any(isinstance(one, ast.FormattedValue) and _input_in(one.value, inputs) for one in node.values)
	if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and _literal(node.left):
		return _input_in(node.right, inputs)
	if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
		return _built(node.left, inputs) or _built(node.right, inputs) or any(
			_input_in(one, inputs) for one in (node.left, node.right) if not _literal(one) and not isinstance(one, (ast.BinOp, ast.JoinedStr))
		)
	if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format" and _literal(node.func.value):
		return any(_input_in(one, inputs) for one in [*node.args, *(one.value for one in node.keywords)])
	return False


def _tainted(function: Function, inputs: set[str]) -> set[str]:
	"""The function's variables that hold a string built from its inputs."""
	held = set()
	moved = True
	while moved:
		moved = False
		known = inputs | held
		for node in function.nodes:
			if isinstance(node, ast.Assign) and _built(node.value, known):
				for one in node.targets:
					if isinstance(one, ast.Name) and one.id not in held:
						held.add(one.id)
						moved = True
			if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id not in held:
				if _built(node.value, known) or (isinstance(node.op, ast.Add) and _input_in(node.value, known) and not _literal(node.value)):
					held.add(node.target.id)
					moved = True
	return held


def sql_from_input(code: Code) -> set[str]:
	"""Rule 3: a query whose text is built from a function's input or the
	request, rather than passed as parameters."""
	found = set()
	for one in code.functions.values():
		inputs = _inputs(one)
		tainted = _tainted(one, inputs)
		for node in one.nodes:
			if not (isinstance(node, ast.Call) and called(node).rsplit(".", 1)[-1] in ("sql", "multisql") and node.args):
				continue
			query = node.args[0]
			if _built(query, inputs | tainted) or (isinstance(query, ast.Name) and query.id in tainted):
				found.add(one.key)
	return found


def _entropy(text: str) -> float:
	return -sum(text.count(one) / len(text) * math.log2(text.count(one) / len(text)) for one in set(text))


def _looks_secret(value) -> bool:
	return (
		isinstance(value, str)
		and len(value) >= 20
		and not re.search(r"\s|\{|%\(|^https?://|^/|\.(py|js|json|html|css|svg|png)$", value)
		and _entropy(value) > 3.6
		and sum(one.isdigit() for one in value) >= 2
		and any(one.isalpha() for one in value)
	)


def secrets(sources: dict[str, str]) -> set[str]:
	"""Rule 4: a key or token typed into the code, by its known shape or as a
	high-entropy literal given to a name that says secret. Answers
	`file:function` (or `file:line` outside any function, or where the file is
	not Python), never the value."""
	found = set()
	for file, source in sources.items():
		given = SECRET_GIVEN.finditer(source) if SECRET_TAIL.search(source) else ()
		for match in (*SECRET_SHAPES.finditer(source), *given):
			if match.re is SECRET_SHAPES or _looks_secret(match.group("value")):
				line = source.count(chr(10), 0, match.start()) + 1
				found.add(f"{file}:{_function_at(file, source, line) or line}")
	return found


def _function_at(file: str, source: str, line: int) -> str | None:
	"""The innermost function a line of a Python file sits in, or None."""
	if not file.endswith(".py"):
		return None
	try:
		nodes = tree.nodes(source)
	except SyntaxError:
		return None
	held = [
		node for node in nodes
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.lineno <= line <= (node.end_lineno or node.lineno)
	]
	return max(held, key=lambda node: node.lineno).name if held else None


def _secret_sources() -> dict[str, str]:
	roots = (tree.APP, tree.ROOT / "scripts", tree.ROOT / "deploy", tree.ROOT / "frontend" / "src")
	found = {}
	for root in roots:
		for path in sorted(root.rglob("*")):
			parts = path.parts[len(tree.ROOT.parts) :]
			if (
				tree.judged(path)
				and path.is_file()
				and path.suffix in SECRET_SUFFIXES
				and not any(part in tree.SKIP_DIRS or part == "tests" for part in parts)
				and not path.name.startswith("test_")
				and not tree.vendored(path)
			):
				found[str(path.relative_to(tree.ROOT))] = path.read_text(encoding="utf-8", errors="ignore")
	return found


def _docs(function: Function) -> set[str]:
	return {
		target.id
		for one in function.nodes
		if isinstance(one, ast.Assign) and isinstance(one.value, ast.Call) and called(one.value).rsplit(".", 1)[-1] in WHOLE
		for target in one.targets
		if isinstance(target, ast.Name)
	}


def _whole(code: Code, function: Function, node, docs: set[str], giving: set[tuple[str, str]]) -> bool:
	"""An expression that hands over a record's every field: the record
	itself, its `as_dict()`, `fields=["*"]`, `select *`, or a function of ours
	that gives one."""
	if isinstance(node, ast.Name):
		return node.id in docs
	if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
		return any(_whole(code, function, one, docs, giving) for one in node.elts)
	if isinstance(node, ast.Dict):
		return any(_whole(code, function, one, docs, giving) for one in node.values)
	if isinstance(node, ast.Starred):
		return _whole(code, function, node.value, docs, giving)
	if isinstance(node, ast.IfExp):
		return any(_whole(code, function, one, docs, giving) for one in (node.body, node.orelse))
	if isinstance(node, ast.BoolOp):
		return any(_whole(code, function, one, docs, giving) for one in node.values)
	if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
		return _whole(code, function, node.elt, docs, giving)
	if isinstance(node, ast.DictComp):
		return _whole(code, function, node.value, docs, giving)
	if not isinstance(node, ast.Call):
		return False
	name = called(node).rsplit(".", 1)[-1]
	module, _, local = code.target(function.module, node).rpartition(".")
	fields = _kw(node, "fields") or (node.args[2] if name in ("get_value", "get_cached_value") and len(node.args) > 2 else None)
	return (
		(name in WHOLE and bool(docs is not PAGE))
		or (name == "as_dict" and isinstance(node.func, ast.Attribute) and not node.args)
		or (fields is not None and "'*'" in ast.unparse(fields))
		or (name == "sql" and bool(node.args) and re.search(r"select\s+(\w+\.)?\*", _literal(node.args[0]), re.I) is not None)
		or (module, local) in giving
		or any(_whole(code, function, one, PAGE, set()) for one in [*node.args, *(one.value for one in node.keywords)])
	)


PAGE: set[str] = set()
"""A page's context goes to its template, which names what it shows: there
only `as_dict()`, `*` and `select *` hand over every field."""


def _gives_whole(code: Code, function: Function, giving: set[tuple[str, str]]) -> bool:
	docs = _docs(function)
	for node in function.nodes:
		if isinstance(node, ast.Return) and node.value is not None and _whole(code, function, node.value, docs, giving):
			return True
		if (
			function.name == "get_context"
			and isinstance(node, (ast.Assign, ast.AugAssign))
			and any(dotted(one).startswith("context") for one in ([node.target] if isinstance(node, ast.AugAssign) else node.targets))
			and _whole(code, function, node.value, PAGE, giving)
		):
			return True
	return False


def says_too_much(code: Code) -> set[str]:
	"""Rule 5: a function a guest reaches (`allow_guest=True`, or a www page's
	`get_context`) that hands over a record without naming its fields."""
	giving: set[tuple[str, str]] = set()
	moved = True
	while moved:
		more = {key for key, one in code.functions.items() if key not in giving and _gives_whole(code, one, giving)}
		giving |= more
		moved = bool(more)
	return {
		one.key
		for key, one in code.functions.items()
		if key in giving
		and (
			((decorator := code.whitelisted(one)) is not None and code.guest(decorator))
			or (one.name == "get_context" and one.file.startswith("www/"))
		)
	}


def _module(file: str) -> tuple[str, str]:
	"""The dotted module of a file under onedesk/, and the package its
	relative imports start from."""
	module = ".".join(("onedesk", *Path(file).with_suffix("").parts)).removesuffix(".__init__")
	return module, module if file.endswith("__init__.py") else module.rsplit(".", 1)[0]


IMPORT_FROM = re.compile(r"\bfrom\s+(\.*[\w.]*)\s+import\s+(\([^)]*\)|[^\n]*)")
IMPORT = re.compile(r"^\s*import\s+([\w., ]+)", re.M)


def _imported(source: str, package: str) -> set[str]:
	"""Every dotted module a source may import, found by its text rather than
	its tree, and so never fewer than it imports: each `from` base with each
	name under it, relative ones resolved from `package`."""
	found = set()
	for base, names in IMPORT_FROM.findall(source):
		dots = len(base) - len(base.lstrip("."))
		if dots:
			parts = package.split(".")
			base = ".".join([*parts[: len(parts) - (dots - 1)], *([base[dots:]] if base[dots:] else [])])
		found.add(base)
		found.update(f"{base}.{name.split()[0]}" for name in names.strip("()").replace("\n", " ").split(",") if name.split())
	for names in IMPORT.findall(source):
		for name in names.split(","):
			parts = name.split()[0].split(".") if name.split() else []
			found.update(".".join(parts[:end]) for end in range(1, len(parts) + 1))
	return found


def _held(rule: str, found: set[str], allowance: dict[str, str], hint: str, base: Path = tree.APP) -> None:
	"""Every finding allowed and every allowance found, of the files this run
	judges (scripts/tree.py, judged): all of them under `--all`."""
	found = {one for one in found if tree.judged(base / one.split(":")[0])}
	allowance = {one: why for one, why in allowance.items() if tree.judged(base / one.split(":")[0])}
	new = sorted(found - set(allowance))
	gone = sorted(set(allowance) - found)
	assert not new, f"{rule}: {new}. {hint}"
	assert not gone, f"{rule}: {gone} no longer happen; take them out of oneguard_allowed.py so the count stays down"
	assert all(why.strip() for why in allowance.values()), f"{rule}: every allowance says why it is safe or 'to fix'"


def _example(source: str, file: str = "one_example/api.py") -> Code:
	return Code({file: source, "one/roles.py": ROLES_EXAMPLE})


ROLES_EXAMPLE = '''
import frappe

def require(role):
	if role not in frappe.get_roles():
		raise frappe.PermissionError
'''


UNCHECKED_EXAMPLE = '''
import frappe
from onedesk.one import roles

@frappe.whitelist()
def salary(employee):
	return frappe.db.get_value("Salary Slip", {"employee": employee}, "net_pay")

@frappe.whitelist()
def held(employee):
	roles.require("HR Manager")
	return frappe.db.get_value("Salary Slip", {"employee": employee}, "net_pay")

@frappe.whitelist()
def checked(name):
	doc = frappe.get_doc("Salary Slip", name)
	doc.check_permission("read")
	return doc.net_pay

@frappe.whitelist()
def listed():
	return frappe.get_list("Salary Slip", fields=["name"])

@frappe.whitelist()
def mine():
	return frappe.get_all("ToDo", filters={"allocated_to": frappe.session.user}, fields=["name"])

@frappe.whitelist(allow_guest=True)
def public():
	return frappe.db.get_value("Website Settings", None, "app_name")
'''


def test_a_whitelisted_function_checks_permission():
	_held(
		"unchecked",
		unchecked(Code.of_app()),
		allowed.UNCHECKED,
		"A whitelisted function reads or writes records with nothing checking who asks: check the record "
		"(`doc.check_permission(\"read\")`, `frappe.has_permission`), read through `frappe.get_list`, gate on a role "
		"(`roles.require`, `frappe.only_for`), or scope it to `frappe.session.user`.",
	)


def test_the_unchecked_rule_catches_its_example():
	assert unchecked(_example(UNCHECKED_EXAMPLE)) == {"one_example/api.py:salary"}


GET_EXAMPLE = '''
import frappe

def _close(name):
	frappe.db.set_value("ToDo", name, "status", "Closed")

@frappe.whitelist()
def close(name):
	_close(name)

@frappe.whitelist(methods=["GET"])
def rename(name, title):
	doc = frappe.get_doc("ToDo", name)
	doc.description = title
	doc.save()

@frappe.whitelist(methods=["POST"])
def close_posted(name):
	_close(name)

@frappe.whitelist()
def read(name):
	return frappe.db.get_value("ToDo", name, "status")

class ToDo:
	@frappe.whitelist()
	def finish(self):
		self.db_set("status", "Closed")
'''


def test_a_write_is_post_only():
	_held(
		"get-writes",
		written_by_get(Code.of_app()),
		allowed.GET_WRITES,
		"A whitelisted function that changes data answers a GET, which a link or an image can make for a signed-in "
		'person: say `@frappe.whitelist(methods=["POST"])`.',
	)


def test_the_get_writes_rule_catches_its_example():
	assert written_by_get(_example(GET_EXAMPLE)) == {
		"one_example/api.py:close",
		"one_example/api.py:rename",
		"one_example/api.py:ToDo.finish",
	}


SQL_EXAMPLE = '''
import frappe

def by_name(name):
	return frappe.db.sql(f"select status from tabToDo where name = '{name}'")

def by_owner(owner):
	return frappe.db.sql("select name from tabToDo where owner = '%s'" % owner)

def by_word(word):
	query = "select name from tabToDo where description like '%" + word + "%'"
	return frappe.db.sql(query)

def by_request():
	return frappe.db.sql("select name from tabToDo where name = '{0}'".format(frappe.form_dict.name))

def built_up(status):
	query = "select name from tabToDo"
	query += f" where status = '{status}'"
	return frappe.db.sql(query)

def safe(name, names, limit, locking):
	frappe.db.sql("select status from tabToDo where name = %s" + (" for update" if locking else ""), name)
	frappe.db.sql(f"select name from tabToDo where name in ({', '.join(['%s'] * len(names))})", names)
	return frappe.db.sql(f"select name from tabToDo limit {int(limit)}")
'''


def test_sql_takes_its_values_as_parameters():
	_held(
		"sql-from-input",
		sql_from_input(Code.of_app()),
		allowed.SQL_FROM_INPUT,
		"A query's text is built from a function's input or the request: pass values as parameters "
		'(`frappe.db.sql("... where name = %s", name)`), or use `frappe.qb`.',
	)


def test_the_sql_rule_catches_its_example():
	assert sql_from_input(_example(SQL_EXAMPLE)) == {
		f"one_example/api.py:{one}" for one in ("by_name", "by_owner", "by_word", "by_request", "built_up")
	}


def _secret_example() -> dict[str, str]:
	shaped = "sk_" + "live_" + "4eC39HqLyjWDarjtT1zdp7dc"
	keyed = "Zq" + "8vT2xLm9Rk4wPb7Nc3Yh6Dj1Fs5Gu0Ae"
	return {
		"one_example/stripe.py": f'import frappe\n\nKEY = "{shaped}"\n',
		"one_example/hook.py": f'import frappe\n\nSIGNING_SECRET = "{keyed}"\nLABEL = "Signing secret"\nHASH = "{keyed}"\n',
		"one_example/client.js": f'const headers = {{ Authorization: "Bearer {keyed}" }};\n',
	}


def test_no_secret_is_in_the_code():
	_held(
		"secret-in-code",
		secrets(_secret_sources()),
		allowed.SECRETS,
		"A key or token is typed into the code (the line is named, never the value): move it to the site's config or a "
		"Password field, read it with `frappe.conf` or `get_password`, and rotate it, since git keeps it.",
		tree.ROOT,
	)


def test_the_secret_rule_catches_its_example():
	assert secrets(_secret_example()) == {"one_example/stripe.py:3", "one_example/hook.py:3", "one_example/client.js:1"}


GUEST_EXAMPLE = '''
import frappe

def _offer(name):
	return frappe.get_doc("Job Opening", name).as_dict()

@frappe.whitelist(allow_guest=True)
def opening(name):
	return _offer(name)

@frappe.whitelist(allow_guest=True)
def openings():
	return frappe.get_all("Job Opening", fields=["*"])

@frappe.whitelist(allow_guest=True)
def doc(name):
	job = frappe.get_doc("Job Opening", name)
	return job

@frappe.whitelist(allow_guest=True)
def named(name):
	return frappe.db.get_value("Job Opening", name, ["job_title", "description"], as_dict=True)

@frappe.whitelist()
def signed_in(name):
	return frappe.get_doc("Job Opening", name).as_dict()
'''

PAGE_EXAMPLE = '''
import frappe

def get_context(context):
	context.job = frappe.get_doc("Job Opening", frappe.form_dict.name).as_dict()
'''


def test_a_guest_is_given_only_named_fields():
	_held(
		"guest-says-too-much",
		says_too_much(Code.of_app()),
		allowed.GUEST_WHOLE,
		"A guest is handed a whole record (a doc, `as_dict()`, `fields=[\"*\"]`): name the fields a guest may see, "
		"`frappe.db.get_value(doctype, name, [\"title\", ...], as_dict=True)`.",
	)


def test_the_guest_rule_catches_its_example():
	found = says_too_much(Code({"one_example/api.py": GUEST_EXAMPLE, "www/job.py": PAGE_EXAMPLE}))
	assert found == {
		"one_example/api.py:opening",
		"one_example/api.py:openings",
		"one_example/api.py:doc",
		"www/job.py:get_context",
	}
