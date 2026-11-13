"""The release build's template site: the last release's migrated, or a new
one installed. build.sh keeps the template in the Actions cache with the
commit that made it, and migrates it when migrating gives what installing
would. `why` prints what stops that between two commits, one reason a line,
and nothing when the old template may be migrated. `stale` prints the
standard records whose files changed, which `unstamp` (in the bench's
Python, from its sites folder) marks old so the migrate imports each again
whatever its file's `modified` says. `restore` (in Pilot's Python) makes the
old template a site of the new bench, as the box's agent makes a spare.

Installing and migrating part on what frappe's migrate never undoes or
never runs: a hook that runs only at install (after_sync but not
after_migrate, after_install, before_install, after_app_install), the
code those hooks run, a record whose file is gone and that no migrate
reaps, a fixture or customization taken out of its file, a value frappe
keeps from the site when it imports a record again, a customization file
not synced on migrate, a module taken out of modules.txt, and the upstream
commits. Patches run on migrate and are meant to give a workspace what a
new one has, so a new patch is no reason; nor is a field taken out of a
DocType, which leaves a column nothing reads, as on every workspace; nor
the setup wizard, which runs on the workspace after it is claimed."""

import ast
import json
import subprocess
import sys
from pathlib import Path

IMPORTED = {
	"permission_type",
	"doctype",
	"page",
	"report",
	"dashboard_chart_source",
	"print_format",
	"web_page",
	"website_theme",
	"web_form",
	"web_template",
	"notification",
	"print_style",
	"workspace",
	"workspace_sidebar",
	"sidebar",
	"onboarding_step",
	"module_onboarding",
	"form_tour",
	"client_script",
	"server_script",
	"custom_field",
	"property_setter",
	"letter_head",
	"dashboard chart",
	"number card",
}
APP_ROOTED = {"dock", "sidebar"}
UNDER_DOCTYPE = {"doctype_layout", "list_filter", "kanban_board"}
REAPED = {"doctype", "page", "report", "notification", "workspace", "sidebar", "dock", "dashboard", "list_filter", "kanban_board"}
KEPT_FROM_THE_SITE = {
	"Report": ("disabled", "prepared_report", "add_total_row"),
	"Print Format": ("disabled",),
	"Notification": ("enabled",),
	"Print Style": ("disabled",),
	"Module Onboarding": ("is_complete",),
	"Onboarding Step": ("is_complete", "is_skipped"),
	"Workspace": ("is_hidden",),
}
INSTALL_ONLY = ("required_apps", "before_install", "after_install", "before_app_install", "after_app_install")
CUSTOMIZED = {
	"custom_fields": ("dt", "fieldname"),
	"property_setters": ("doc_type", "field_name", "row_name", "property"),
	"links": ("parent", "link_doctype", "link_fieldname"),
}
UNSTAMPED = "2000-01-01 00:00:00"


def kind(path: str) -> tuple[str, str] | None:
	"""What a path in the app is to a site, as frappe's install and migrate
	read it: ("standard", folder), ("fixture", ""), ("custom", ""),
	("modules", "") or ("hooks", ""); None for anything no site holds. Pure."""
	parts = path.split("/")
	if parts[0] != "onedesk" or not path.endswith((".json", ".txt", ".py")):
		return None
	if path == "onedesk/hooks.py" or (len(parts) == 3 and parts[2] == "manifest.py"):
		return "hooks", ""
	if path == "onedesk/modules.txt":
		return "modules", ""
	if not path.endswith(".json"):
		return None
	if len(parts) == 3 and parts[1] == "fixtures":
		return "fixture", ""
	if len(parts) == 4 and parts[2] == "custom":
		return "custom", ""
	if len(parts) == 4 and parts[1] in APP_ROOTED and parts[3] == f"{parts[2]}.json":
		return "standard", parts[1]
	if len(parts) == 5 and parts[4] == f"{parts[3]}.json":
		if parts[2] in IMPORTED:
			return "standard", parts[2]
		if parts[2] == f"{parts[1]}_dashboard":
			return "standard", "dashboard"
	if len(parts) == 6 and parts[2] == "doctype" and parts[4] in UNDER_DOCTYPE:
		return "standard", parts[4]
	if len(parts) == 4 and parts[2] == "doctype_settings_map":
		return "standard", "doctype_settings_map"
	return None


def _json(text: str | None):
	try:
		return json.loads(text) if text else None
	except ValueError:
		return None


def _records(text: str | None) -> list[dict]:
	held = _json(text)
	held = held if isinstance(held, list) else [held] if isinstance(held, dict) else []
	return [one for one in held if isinstance(one, dict) and one.get("doctype")]


def _key(record: dict) -> tuple:
	return record.get("doctype"), record.get("name")


def hooks(source: str | None) -> dict[str, str]:
	"""Each name hooks.py sets at its top, as its expression's ast dump, so
	two can be compared without running either. Pure."""
	found = {}
	for node in ast.parse(source or "").body:
		if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
			found[node.targets[0].id] = ast.dump(node.value)
	return found


def settled(read, install: bool) -> list[str] | None:
	"""after_sync (install) or after_migrate as the registry builds them: each
	manifest's `settle` steps, for each folder modules.txt names, read without
	running anything; None when a manifest can't be read. Pure but for `read`."""
	paths = []
	for module in (read("onedesk/modules.txt") or "").split("\n"):
		folder = module.strip().lower().replace(" ", "_")
		if not folder:
			continue
		text = read(f"onedesk/{folder}/manifest.py")
		if text is None:
			continue
		try:
			tree = ast.parse(text)
		except SyntaxError:
			return None
		for call in ast.walk(tree):
			if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "Settle" and call.args:
				said = {one.arg: ast.literal_eval(one.value) for one in call.keywords}
				if install or not said.get("install_only"):
					paths.append(f"onedesk.{folder}.{ast.literal_eval(call.args[0])}")
	return paths


def listed(source: str | None, name: str, read=None) -> list | None:
	"""A hook's list, read without running hooks.py: a plain list or string,
	or the registry's settle steps where hooks.py builds after_sync and
	after_migrate from the manifests (given `read`); None otherwise. Pure but
	for `read`."""
	for node in ast.parse(source or "").body:
		if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
			if read is not None and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", None) == "settles":
				return settled(read, install=any(one.arg == "install" and getattr(one.value, "value", False) for one in node.value.keywords))
			try:
				value = ast.literal_eval(node.value)
			except (ValueError, TypeError, SyntaxError):
				return None
			return [value] if isinstance(value, str) else value if isinstance(value, list) else None
	return []


def at_install(source: str | None, read=None) -> list[str] | None:
	"""Every dotted path hooks.py runs at install and never on migrate:
	after_sync less after_migrate, and the install hooks. None when one of
	them cannot be read. Pure but for `read`."""
	held = {name: listed(source, name, read) for name in ("after_sync", "after_migrate", *INSTALL_ONLY[1:])}
	if any(value is None for value in held.values()):
		return None
	paths = [one for one in held["after_sync"] if one not in held["after_migrate"]]
	for name in INSTALL_ONLY[1:]:
		paths += held[name]
	return [one for one in paths if isinstance(one, str)]


def module_file(dotted: str, read) -> str | None:
	"""The file a module of the app lives in, by `read` (path to text or None)."""
	path = "/".join(dotted.split("."))
	for one in (f"{path}.py", f"{path}/__init__.py"):
		if read(one) is not None:
			return one
	return None


def _parsed(dotted: str, read) -> ast.Module | None:
	found = module_file(dotted, read) if dotted.startswith("onedesk") else None
	try:
		return ast.parse(read(found)) if found else None
	except SyntaxError:
		return None


def _defined(tree: ast.Module) -> dict[str, ast.AST]:
	held = {}
	for node in tree.body:
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
			held[node.name] = node
		elif isinstance(node, ast.Assign | ast.AnnAssign):
			for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
				for name in ast.walk(target):
					if isinstance(name, ast.Name):
						held[name.id] = node
	return held


def _imported(nodes) -> dict[str, tuple[str, str | None]]:
	held = {}
	for node in nodes:
		if isinstance(node, ast.ImportFrom) and node.module and not node.level:
			for alias in node.names:
				held[alias.asname or alias.name] = (node.module, alias.name)
		elif isinstance(node, ast.Import):
			for alias in node.names:
				held[alias.asname or alias.name.split(".")[0]] = (alias.name if alias.asname else alias.name.split(".")[0], None)
	return held


def _bare(node: ast.AST) -> str:
	"""A definition as ast dumps it, without its docstrings, which OneAI
	reads and no install does. Pure."""
	node = ast.parse(ast.unparse(node)).body[0]
	for one in ast.walk(node):
		body = getattr(one, "body", None)
		if isinstance(one, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
			one.body = body[1:] or [ast.Pass()]
	return ast.dump(node)


def _admin_only(node: ast.AST) -> bool:
	"""A function that returns at once off the admin site (`if not
	site.is_admin() ...: return`), which the template never is. Pure."""
	if not isinstance(node, ast.FunctionDef):
		return False
	body = [one for one in node.body if not (isinstance(one, ast.Expr) and isinstance(one.value, ast.Constant))]
	if not body or not isinstance(body[0], ast.If) or not all(isinstance(one, ast.Return) for one in body[0].body):
		return False
	test = body[0].test
	first = test.values[0] if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or) else test
	return (
		isinstance(first, ast.UnaryOp)
		and isinstance(first.op, ast.Not)
		and isinstance(first.operand, ast.Call)
		and isinstance(first.operand.func, ast.Attribute)
		and first.operand.func.attr == "is_admin"
	)


def fingerprint(paths: list[str], read) -> dict[str, str]:
	"""What install-time code runs, by `read`: each definition of the app the
	dotted functions `paths` reach, through the names they use in their own
	module and the ones they import, as its ast without docstrings. A
	function that returns off the admin site counts as that alone."""
	todo = [tuple(one.rsplit(".", 1)) for one in paths if "." in one]
	held: dict[str, str] = {}
	while todo:
		module, name = todo.pop()
		tree = _parsed(module, read)
		if tree is None:
			continue
		node = _defined(tree).get(name)
		if node is None:
			if _parsed(f"{module}.{name}", read) is not None:
				held.setdefault(f"{module}.{name}", "a module")
			continue
		if f"{module}.{name}" in held:
			continue
		if _admin_only(node):
			held[f"{module}.{name}"] = "off the admin site, nothing"
			continue
		held[f"{module}.{name}"] = _bare(node)
		local = _defined(tree)
		names = {**_imported(tree.body), **_imported(ast.walk(node))}
		for one in ast.walk(node):
			if isinstance(one, ast.Attribute) and isinstance(one.value, ast.Name) and one.value.id in names:
				source, attr = names[one.value.id]
				base = source if attr is None else f"{source}.{attr}"
				if _parsed(base, read) is not None:
					todo.append((base, one.attr))
			if isinstance(one, ast.Name):
				if one.id in names:
					source, attr = names[one.id]
					if attr is not None:
						todo.append((source, attr))
				elif one.id in local and one.id != name:
					todo.append((module, one.id))
	return held


def _hooks_reasons(before: str | None, after: str | None, read_before=None, read_after=None) -> list[str]:
	wrong = []
	was, now = hooks(before), hooks(after)
	for name in INSTALL_ONLY:
		if was.get(name) != now.get(name):
			wrong.append(f"onedesk/hooks.py: {name} changed, and it is read only at install")
	old, new = at_install(before, read_before), at_install(after, read_after)
	if old is None or new is None:
		return [*wrong, "onedesk/hooks.py: after_sync, after_migrate or an install hook is not a plain list"]
	ran = set((listed(before, "after_sync", read_before) or []) + (listed(before, "after_migrate", read_before) or []))
	runs = set((listed(after, "after_sync", read_after) or []) + (listed(after, "after_migrate", read_after) or []))
	added = sorted(set(new) - set(old) - ran)
	if added:
		wrong.append(f"onedesk/hooks.py: {', '.join(added)} runs only at install, and the old template never ran it")
	gone = sorted(ran - runs)
	if gone:
		wrong.append(f"onedesk/hooks.py: {', '.join(gone)} no longer runs, and what it did stays on the old template")
	return wrong


def _lines(text: str | None) -> set[str]:
	return {line.strip() for line in (text or "").splitlines() if line.strip()}


def _modules_reasons(before: str | None, after: str | None) -> list[str]:
	gone = sorted(_lines(before) - _lines(after))
	return [f"onedesk/modules.txt: {', '.join(gone)} left, and migrate keeps a Module Def"] if gone else []


def _customized(text: str | None) -> set[tuple]:
	held = _json(text)
	if not isinstance(held, dict):
		return set()
	return {(part, *(row.get(field) for field in fields)) for part, fields in CUSTOMIZED.items() for row in held.get(part) or [] if isinstance(row, dict)}


def _custom_reasons(paths: list[str], before, after) -> list[str]:
	wrong = []
	for path in paths:
		held = _json(after(path))
		if after(path) is not None and not (isinstance(held, dict) and held.get("sync_on_migrate")):
			wrong.append(f"{path}: has no sync_on_migrate, so only an install reads it")
	gone = set().union(*(_customized(before(path)) for path in paths)) - set().union(*(_customized(after(path)) for path in paths))
	return wrong + [f"{part} {' '.join(str(one) for one in key if one)}: taken out of custom/, and migrate leaves it on the site" for part, *key in sorted(gone, key=str)]


def _held(paths: list[str], read, first_only: bool = False) -> dict[tuple, dict]:
	held = {}
	for path in paths:
		records = _records(read(path))
		for record in records[:1] if first_only else records:
			held[_key(record)] = record
	return held


def _records_reasons(fixtures: list[str], standard: list[tuple[str, str]], before, after) -> list[str]:
	every = [path for path, _folder in standard]
	unreaped = [path for path, folder in standard if folder not in REAPED]
	new = {**_held(fixtures, after), **_held(every, after, True)}
	was = {**_held(fixtures, before), **_held(every, before, True)}
	gone = set({**_held(fixtures, before), **_held(unreaped, before, True)}) - set(new)
	wrong = [f"{doctype} {name}: its file is gone or holds it no longer, and migrate leaves it on the site" for doctype, name in sorted(gone, key=str)]
	for key, record in new.items():
		moved = [one for one in KEPT_FROM_THE_SITE.get(record["doctype"], ()) if key in was and was[key].get(one) != record.get(one)]
		if moved:
			wrong.append(f"{record['doctype']} {record.get('name')}: its {', '.join(moved)} changed, and frappe keeps the site's own when it imports it again")
	return wrong


def reasons(changes: list[tuple[str, str]], before, after) -> list[str]:
	"""Why the template made at one commit cannot be migrated to give what a
	new install at another would: empty when it can. `changes` is git's
	name-status between them without renames (status, path); `before` and
	`after` read a path at each commit (text, or None when it is not there).
	A record or a customization that moves to another file is no reason.
	Pure over its arguments."""
	wrong = []
	touched = {path for _status, path in changes}
	found = {path: kind(path) for path in touched}
	if "upstream.json" in touched:
		wrong.append("upstream.json changed: frappe, erpnext and hrms are other commits")
	if "onedesk/hooks.py" in touched or any(found[path] == ("hooks", "") for path in touched):
		wrong += _hooks_reasons(before("onedesk/hooks.py"), after("onedesk/hooks.py"), before, after)
	if "onedesk/modules.txt" in touched:
		wrong += _modules_reasons(before("onedesk/modules.txt"), after("onedesk/modules.txt"))
	wrong += _custom_reasons(sorted(path for path, one in found.items() if one == ("custom", "")), before, after)
	fixtures = sorted(path for path, one in found.items() if one == ("fixture", ""))
	standard = sorted((path, one[1]) for path, one in found.items() if one and one[0] == "standard")
	wrong += _records_reasons(fixtures, standard, before, after)
	if any(path.endswith(".py") for path in touched):
		old, new = (at_install(read("onedesk/hooks.py"), read) for read in (before, after))
		if old is not None and new is not None:
			was, now = fingerprint(old, before), fingerprint(new, after)
			moved = sorted(name for name in set(was) | set(now) if was.get(name) != now.get(name))
			wrong += [f"{name}: changed, and it runs only at install" for name in moved]
	return wrong


def stale(changes: list[tuple[str, str]], after) -> list[list[str]]:
	"""The standard records, but DocTypes, whose files were added or changed:
	migrate imports one only when its file's `modified` is newer than the
	site's, which a hook writing to it, or a file changed without moving it,
	defeats. A DocType is imported by its file's hash instead. Pure."""
	held = []
	for status, path in changes:
		found = kind(path)
		if status == "D" or not found or found[0] != "standard" or found[1] == "doctype":
			continue
		for record in _records(after(path))[:1]:
			if record.get("name") and record["doctype"] != "DocType":
				held.append([record["doctype"], record["name"]])
	return held


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=False)


def _between(repo: str, old: str, new: str):
	for sha in (old, new):
		if _git(repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode:
			return None
	listed_changes = _git(repo, "diff", "--name-status", "--no-renames", old, new, "--", "onedesk", "upstream.json").stdout
	changes = [tuple(line.split("\t", 1)) for line in listed_changes.splitlines() if "\t" in line]

	def at(sha):
		def read(path):
			shown = _git(repo, "show", f"{sha}:{path}")
			return shown.stdout if shown.returncode == 0 else None

		return read

	return [(status[:1], path) for status, path in changes], at(old), at(new)


def why(repo: str, old: str, new: str) -> list[str]:
	found = _between(repo, old, new)
	if found is None:
		return [f"the commit the kept template was made at, {old}, is not in this checkout"]
	return reasons(*found)


def unstamp(site: str, listed_file: str) -> None:
	"""Each record `stale` listed dated 2000, so the migrate after imports it
	from its file. Run from the bench's sites folder, in its Python."""
	import frappe

	held = json.loads(Path(listed_file).read_text())
	frappe.init(site, sites_path=".")
	frappe.connect()
	try:
		for doctype, name in held:
			if frappe.db.table_exists(doctype):
				frappe.db.sql(f"update `tab{doctype}` set modified = %s where name = %s", (UNSTAMPED, name))
		frappe.db.commit()
	finally:
		frappe.destroy()
	print(f"template: {len(held)} records to import again")


def restore(bench: str, site: str, kept: str, password: str) -> None:
	"""The kept template, unpacked in `kept`, made `site` of the bench: its
	database, its files and its config under the bench's own database
	settings, as the box's agent makes a spare (agent.py `spare`)."""
	import shutil

	from pilot.core.bench import Bench
	from pilot.core.site import Site
	from pilot.core.site.apps import SiteApps
	from pilot.core.site.commands import SiteCommands

	unpacked = Path(kept)
	reach = SiteCommands.db_args
	SiteCommands.db_args = lambda self, db_type: [*reach(self, db_type), "--source-sql", str(unpacked / "database.sql.gz")]
	made = Site.provision(Bench(Path(bench)), site, [], password)
	SiteCommands.db_args = reach
	SiteApps(made).restore_installed_apps_copy()
	for part in ("public/files", "private/files"):
		shutil.copytree(unpacked / part, made.path / part, dirs_exist_ok=True)
	config = made.path / "site_config.json"
	config.write_text(json.dumps({**json.loads((unpacked / "site_config.json").read_text()), **json.loads(config.read_text())}, indent=1))
	shutil.rmtree(unpacked)


if __name__ == "__main__":
	command, *given = sys.argv[1:]
	if command == "why":
		print("\n".join(why(*given)))
	elif command == "stale":
		found = _between(*given)
		print(json.dumps(stale(found[0], found[2]) if found else []))
	elif command == "unstamp":
		unstamp(*given)
	else:
		restore(*given)
