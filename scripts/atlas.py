"""The atlas: every record type, report and page frappe, erpnext and hrms ship,
and ours, with where One reaches it, or the answer for why it does not.

Upstream is read once into a snapshot (docs/upstream/atlas.json) so the
guards run without a bench. One's side is read from this repository: the
rails, the workspaces, each Home's directory, every route our code opens, and
then every visible link on a form already reached, until nothing new is.

    python scripts/atlas.py --snapshot   read the bench into the snapshot
    python scripts/atlas.py --check      fail when the snapshot is not the bench's
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from functools import cache
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tree

BENCH = Path(__file__).resolve().parents[2]
APPS = ("frappe", "erpnext", "hrms")
SNAPSHOT = tree.ROOT / "docs" / "upstream" / "atlas.json"
ROLES = tree.ROOT / "docs" / "atlas-site.json"
SITE = os.environ.get("ONE_SITE", "onedesk.localhost")
FRONTEND = tree.ROOT / "frontend" / "src"

LINKS = ("Link", "Table MultiSelect")
TABLES = ("Table", "Table MultiSelect")
BRAND = re.compile(r"\b(ERPNext|Frappe|HRMS)\b")


def _doctype(data: dict, app: str) -> dict:
	fields = data.get("fields") or []
	return {
		"app": app,
		"module": data.get("module"),
		"table": int(bool(data.get("istable"))),
		"single": int(bool(data.get("issingle"))),
		"links": sorted(
			[f["fieldname"], f["options"], int(bool(f.get("hidden") or f.get("read_only")))]
			for f in fields
			if f.get("fieldtype") in LINKS and f.get("options")
		),
		"tables": sorted(
			[f["fieldname"], f["options"], int(bool(f.get("hidden")))]
			for f in fields
			if f.get("fieldtype") in TABLES and f.get("options")
		),
		"fields": sum(
			1 for f in fields if f.get("fieldtype") not in ("Section Break", "Column Break", "Tab Break")
		),
		"roles": sorted(
			{p["role"] for p in data.get("permissions") or [] if p.get("read") and not p.get("permlevel")}
		),
		"brand": sorted(
			{
				text
				for text in [data.get("description") or ""]
				+ [f.get(key) or "" for f in fields for key in ("label", "description")]
				if BRAND.search(text)
			}
		),
		"submittable": int(bool(data.get("is_submittable"))),
		"title": data.get("title_field") or "",
		"autoname": data.get("autoname") or "",
		"listed": sorted(f["fieldname"] for f in fields if f.get("in_list_view") and not f.get("hidden")),
		"labels": sorted(
			{data["name"]} | {f["label"] for f in fields if f.get("label") and not f.get("hidden")}
		),
	}


_ITEMS = re.compile(r"[\"']items[\"']\s*:\s*\[([^\]]*)\]")
_QUOTED = re.compile(r"[\"']([^\"']+)[\"']")


def _connections(folder: Path) -> list[str]:
	"""The records a form's Connections tab lists (<doctype>_dashboard.py)."""
	board = folder / f"{folder.name}_dashboard.py"
	if not board.exists():
		return []
	return sorted({name for items in _ITEMS.findall(board.read_text()) for name in _QUOTED.findall(items)})


def _read(app_dir: Path, app: str) -> dict:
	said = {"doctypes": {}, "reports": {}, "pages": {}}
	for path in sorted(app_dir.glob("*/doctype/*/*.json")):
		data = json.loads(path.read_text())
		if isinstance(data, dict) and data.get("doctype") == "DocType" and path.stem == path.parent.name:
			said["doctypes"][data["name"]] = {**_doctype(data, app), "connections": _connections(path.parent)}
	for path in sorted(app_dir.glob("*/report/*/*.json")):
		data = json.loads(path.read_text())
		if isinstance(data, dict) and data.get("doctype") == "Report" and path.stem == path.parent.name:
			said["reports"][data["name"]] = {
				"app": app,
				"module": data.get("module"),
				"ref": data.get("ref_doctype"),
				"type": data.get("report_type"),
				"roles": sorted({r["role"] for r in data.get("roles") or []}),
				"brand": [data["name"]] if BRAND.search(data["name"]) else [],
			}
	for path in sorted(app_dir.glob("*/page/*/*.json")):
		data = json.loads(path.read_text())
		if isinstance(data, dict) and data.get("doctype") == "Page" and path.stem == path.parent.name:
			title = data.get("title") or data["name"]
			said["pages"][data["name"]] = {
				"app": app,
				"module": data.get("module"),
				"title": title,
				"roles": sorted({r["role"] for r in data.get("roles") or []}),
				"brand": [title] if BRAND.search(title) else [],
			}
	return said


def _po(path: Path) -> dict:
	"""{(msgid, context): msgstr} from a .po or .pot file."""
	out, entry, key = {}, {}, None
	if not path.exists():
		return out

	def flush():
		if entry.get("msgid"):
			out[(entry["msgid"], entry.get("msgctxt") or "")] = entry.get("msgstr", "")

	for line in [*path.read_text().splitlines(), ""]:
		if not line.strip():
			flush()
			entry, key = {}, None
		elif line.startswith("#"):
			continue
		elif line.startswith(("msgid ", "msgstr ", "msgctxt ")):
			key, _, rest = line.partition(" ")
			entry[key] = json.loads(rest)
		elif line.startswith('"') and key:
			entry[key] += json.loads(line)
	return out


LANGUAGES = ("ar", "de")


def _brand(app_dir: Path) -> dict:
	"""Every sentence an app can show that names a brand, with its own Arabic
	and German: {msgid: {context, ar, de}}."""
	pot = _po(app_dir / "locale" / "main.pot")
	said = {lang: _po(app_dir / "locale" / f"{lang}.po") for lang in LANGUAGES}
	return {
		msgid: {"context": context, **{lang: said[lang].get((msgid, context), "") for lang in LANGUAGES}}
		for (msgid, context) in pot
		if BRAND.search(msgid)
	}


def snapshot() -> dict:
	"""frappe, erpnext and hrms as the bench has them."""
	out = {"doctypes": {}, "reports": {}, "pages": {}, "brand": {}, "notifications": {}}
	translated = {lang: set() for lang in LANGUAGES}
	for app in APPS:
		said = _read(BENCH / app / app, app)
		for kind in ("doctypes", "reports", "pages"):
			out[kind].update(said[kind])
		out["brand"].update(_brand(BENCH / app / app))
		for lang in LANGUAGES:
			translated[lang] |= {
				msgid for (msgid, _), text in _po(BENCH / app / app / "locale" / f"{lang}.po").items() if text
			}
		for path in sorted((BENCH / app / app).glob("*/notification/*/*.json")):
			data = json.loads(path.read_text())
			if isinstance(data, dict) and data.get("doctype") == "Notification":
				out["notifications"][data["name"]] = {
					"doctype": data.get("document_type"),
					"enabled": int(bool(data.get("enabled"))),
				}
	for meta in out["doctypes"].values():
		meta["untranslated"] = {
			lang: [label for label in meta["labels"] if label not in translated[lang]] for lang in LANGUAGES
		}
	return out


@cache
def upstream() -> dict:
	return json.loads(SNAPSHOT.read_text())


@cache
def ours() -> dict:
	return _read(tree.APP, "onedesk")


@cache
def everything() -> dict:
	both = {kind: {**upstream()[kind], **ours()[kind]} for kind in ("doctypes", "reports", "pages")}
	_customized(both["doctypes"])
	return both


def _customized(doctypes: dict) -> None:
	"""Our custom fields add links and tables; our property setters hide fields."""
	for path in tree.APP.glob("*/custom/*.json"):
		data = json.loads(path.read_text())
		meta = doctypes.get(data.get("doctype"))
		if not meta:
			continue
		for field in data.get("custom_fields") or []:
			row = [
				field["fieldname"],
				field.get("options"),
				int(bool(field.get("hidden") or field.get("read_only"))),
			]
			if field.get("fieldtype") in LINKS and field.get("options"):
				meta["links"].append(row)
			if field.get("fieldtype") in TABLES and field.get("options"):
				meta["tables"].append(row)
		hidden = {
			ps["field_name"]
			for ps in data.get("property_setters") or []
			if ps.get("property") in ("hidden", "read_only") and str(ps.get("value")) == "1"
		}
		for rows in (meta["links"], meta["tables"]):
			for row in rows:
				if row[0] in hidden:
					row[2] = 1


_SLUG = re.compile(r"/desk/([a-z0-9-]+)")
_REPORT_URL = re.compile(r"query-report/([^\"'`?#/]+)")
_ROUTED = re.compile(
	r"""(?:set_route|goTo)\(\s*["'](?:List|Form|Tree|Report|query-report)["']\s*,\s*["']([^"']+)["']"""
)
_NEW = re.compile(r"""new_doc\(\s*["']([^"']+)["']""")
_PAGE = re.compile(r"""set_route\(\s*["']([a-z0-9-]+)["']\s*\)""")
_DIRECTORY = re.compile(r"""_lt\("[^"]*"\),\s*"(DocType|Report|Page|List)",\s*"([^"]+)\"""")


def _slug(name: str) -> str:
	return name.lower().replace(" ", "-").replace("_", "-")


@cache
def named() -> dict:
	"""What One names a way into: {(kind, name): [where]}."""
	found: dict = {}

	def add(kind, name, where):
		found.setdefault((kind, name), []).append(where)

	for path in sorted(tree.APP.glob("*/sidebar/*/*.json")):
		data = json.loads(path.read_text())
		for row in data.get("items") or []:
			if row.get("type") == "Link" and row.get("link_to"):
				add(row.get("link_type") or "DocType", row["link_to"], f"{data['title']}'s rail")
	for path in sorted(tree.APP.glob("*/workspace/*/*.json")):
		data = json.loads(path.read_text())
		for row in (data.get("links") or []) + (data.get("shortcuts") or []):
			if row.get("link_to"):
				add(
					row.get("link_type") or row.get("type") or "DocType",
					row["link_to"],
					f"{data['name']} workspace",
				)
		for row in data.get("quick_lists") or []:
			if row.get("document_type"):
				add("DocType", row["document_type"], f"{data['name']} workspace")
	for path in sorted(tree.APP.rglob("*.py")):
		if "one_demo" in path.parts or "__pycache__" in path.parts:
			continue
		for kind, name in _DIRECTORY.findall(path.read_text()):
			add("DocType" if kind == "List" else kind, name, f"{path.parent.name}'s Home")
	return found


@cache
def routed() -> dict:
	"""Records our screens and scripts open by route: {(kind, name): [file]}."""
	slugs = {}
	for name in everything()["doctypes"]:
		slugs.setdefault(_slug(name), name)
	pages = {_slug(name): name for name in everything()["pages"]}
	found: dict = {}
	paths = [p for p in tree.sources() if "one_demo" not in p.parts]
	paths += [p for p in FRONTEND.rglob("*") if p.suffix in (".vue", ".js")]
	for path in paths:
		text = path.read_text(errors="ignore")
		where = str(path.relative_to(tree.ROOT))
		for slug in _SLUG.findall(text):
			if slug in slugs:
				found.setdefault(("DocType", slugs[slug]), []).append(where)
			elif slug in pages:
				found.setdefault(("Page", pages[slug]), []).append(where)
		for slug in _PAGE.findall(text):
			if slug in pages:
				found.setdefault(("Page", pages[slug]), []).append(where)
		for name in _REPORT_URL.findall(text):
			found.setdefault(("Report", unquote(name)), []).append(where)
		made = _NEW.findall(text) if path.suffix != ".py" else []
		for name in _ROUTED.findall(text) + made:
			found.setdefault(("DocType", name), []).append(where)
			found.setdefault(("Report", name), []).append(where)
	return found


@cache
def reach() -> dict:
	"""How each record type, report and page is reached:
	{(kind, name): (how, where)}. `named` and `routed` are ways in somebody
	sees; `linked`, `connected` and `related` are ways in somebody finds."""
	every = everything()
	doctypes = every["doctypes"]
	out = {}
	for (kind, name), where in named().items():
		out[(kind, name)] = ("named", sorted(set(where)))
	for (kind, name), where in routed().items():
		out.setdefault((kind, name), ("routed", sorted(set(where))))
	pages = paged()
	queue = [name for (kind, name) in out if kind == "DocType" and name in doctypes]
	while queue:
		name = queue.pop()
		meta = doctypes.get(name) or {}
		parts = [name] + [child for _, child, hidden in meta.get("tables", []) if not hidden]
		for part in parts:
			for fieldname, target, hidden in (doctypes.get(part) or {}).get("links", []):
				if hidden or target not in doctypes or ("DocType", target) in out:
					continue
				out[("DocType", target)] = ("linked", [f"{name}: {fieldname}"])
				queue.append(target)
		if name in pages:
			continue
		for target in meta.get("connections", []):
			if target in doctypes and ("DocType", target) not in out:
				out[("DocType", target)] = ("connected", [f"{name}'s Connections"])
				queue.append(target)
	for name, meta in every["reports"].items():
		ref = meta.get("ref")
		if ("Report", name) not in out and (not ref or ("DocType", ref) in out):
			out[("Report", name)] = ("related", [f"{ref}'s list" if ref else "every list"])
	return {key: value for key, value in out.items() if key[0] in KINDS and key[1] in every[KINDS[key[0]]]}


KINDS = {"DocType": "doctypes", "Report": "reports", "Page": "pages"}

SHOWN = tree.APP / "one" / "shown.json"


@cache
def shown() -> dict:
	"""What One offers somebody on its own, by kind: what a rail, a workspace
	or a Home names, what our screens open, and those record types' reports.
	What is only linked or connected is found from a record and never offered
	on its own; an answer other than `inside` takes a thing out. one/outside.py
	reads it, for search, pickers and global search."""
	every = everything()
	out = {"DocType": set(), "Report": set(), "Page": set(), "Dashboard": set(), "Workspace": set()}
	for (kind, name), (how, _where) in reach().items():
		if how in SEEN and not (kind == "DocType" and every["doctypes"][name]["table"]):
			out[kind].add(name)
	for name, meta in every["reports"].items():
		if meta.get("ref") in out["DocType"]:
			out["Report"].add(name)
	out["Dashboard"].update(name for kind, name in named() if kind == "Dashboard")
	for path in tree.APP.glob("*/workspace/*/*.json"):
		out["Workspace"].add(json.loads(path.read_text())["name"])
	for (kind, name), (answer, _why) in answers().items():
		if answer != "inside" and kind in out:
			out[kind].discard(name)
	return {kind: sorted(names) for kind, names in out.items()}


def shown_json() -> str:
	said = {"_": "generated by scripts/atlas.py through scripts/docs.py — do not edit"} | shown()
	return json.dumps(said, indent=1, ensure_ascii=False) + "\n"


@cache
def paged() -> frozenset:
	"""Records with a page of their own (one/tiers.py PAGES), which has no
	Connections tab."""
	tree_ = ast.parse((tree.APP / "one" / "tiers.py").read_text())
	for node in tree_.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "PAGES":
			return frozenset(ast.literal_eval(node.value))
	return frozenset()


@cache
def rows() -> list[dict]:
	"""Every record type (not a child table), report and page, with its reach."""
	every = everything()
	reached = reach()
	out = []
	for kind, key in KINDS.items():
		for name, meta in sorted(every[key].items()):
			if kind == "DocType" and meta["table"]:
				continue
			how = reached.get((kind, name))
			out.append(
				{"kind": kind, "name": name, "app": meta["app"], "module": meta["module"], "reach": how}
			)
	return out


@cache
def answers() -> dict:
	"""onedesk/one/atlas.py ANSWERS, read without importing the app."""
	module = ast.parse((tree.APP / "one" / "atlas.py").read_text())
	names = {}
	for node in module.body:
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
			names[node.targets[0].id] = node.value.value
	for node in module.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "ANSWERS":
			said = {}
			for key, value in zip(node.value.keys, node.value.values, strict=True):
				kind = value.elts[0]
				said[ast.literal_eval(key)] = (
					names[kind.id] if isinstance(kind, ast.Name) else kind.value,
					names[value.elts[1].id] if isinstance(value.elts[1], ast.Name) else ast.literal_eval(value.elts[1]),
				)
			return said
	return {}


@cache
def waiting() -> dict:
	"""What has neither a way in nor an answer, by app and module."""
	said = answers()
	out = {}
	for row in rows():
		if not row["reach"] and (row["kind"], row["name"]) not in said:
			out.setdefault(f"{row['app']} / {row['module']}", []).append(f"{row['kind']} {row['name']}")
	return out


EVERYBODY = ("All", "Desk User", "Employee", "Employee Self Service")
ADMINISTRATOR = "Workspace Administrator"


@cache
def givable() -> dict:
	"""{role: the app a workspace gives it with} (one/people.py APPS)."""
	module = ast.parse((tree.APP / "one" / "people.py").read_text())
	out = {role: "everybody" for role in EVERYBODY} | {ADMINISTRATOR: "the administrator"}
	for node in module.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "APPS":
			for label, _code, users, managers in ast.literal_eval(node.value):
				for role in (*users, *managers):
					out.setdefault(role, label)
	# A module everybody uses gives its User role to everybody and its Manager
	# in AccessCenter (people.with_roles), both read off its abilities.py.
	for path in sorted(tree.APP.glob("*/abilities.py")):
		said = {
			node.targets[0].id: node.value
			for node in ast.parse(path.read_text()).body
			if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
		}
		if "EVERYONE" not in said or "APP" not in said:
			continue
		everyone, app = ast.literal_eval(said["EVERYONE"]), ast.literal_eval(said["APP"])
		out.setdefault(everyone, "everybody")
		for role in ast.literal_eval(said["DEFAULTS"]) if "DEFAULTS" in said else ():
			out.setdefault(role, app)
	return out


@cache
def readers() -> dict:
	return json.loads(ROLES.read_text()) if ROLES.exists() else {"doctypes": {}, "reports": {}, "pages": {}}


def open_to(kind: str, name: str) -> list[str] | None:
	"""The apps whose people may open it; None when the site was not read."""
	said = readers()[KINDS[kind]]
	if name not in said:
		return None
	roles = said[name]
	if kind != "DocType" and not roles:
		return ["its record type's readers"]
	apps = sorted({givable()[role] for role in roles if role in givable()})
	return ["everybody"] if "everybody" in apps else apps


def _hooked() -> dict:
	"""{doctype: [what hooks.py gives it]}."""
	module = ast.parse((tree.APP / "hooks.py").read_text())
	out: dict = {}
	names = {
		"doctype_js": "form script",
		"doctype_list_js": "list script",
		"doctype_tree_js": "tree script",
		"doc_events": "events",
		"override_doctype_class": "class",
	}
	for node in module.body:
		if (
			isinstance(node, ast.Assign)
			and getattr(node.targets[0], "id", None) in names
			and isinstance(node.value, ast.Dict)
		):
			for key in node.value.keys:
				if isinstance(key, ast.Constant):
					out.setdefault(key.value, []).append(names[node.targets[0].id])
	return out


_FORM_ON = re.compile(r"""frappe\.ui\.form\.on\(\s*["']([^"']+)["']""")


@cache
def changes() -> dict:
	"""{doctype: what One changed about it}."""
	out: dict = {}
	for path in tree.APP.glob("*/custom/*.json"):
		data = json.loads(path.read_text())
		row = out.setdefault(data.get("doctype"), {})
		row["fields"] = row.get("fields", 0) + len(data.get("custom_fields") or [])
		row["setters"] = row.get("setters", 0) + len(data.get("property_setters") or [])
	for doctype, said in _hooked().items():
		out.setdefault(doctype, {}).setdefault("hooks", set()).update(said)
	for path in [*(tree.APP / "public" / "js").glob("*.js"), *(tree.APP / "public" / "js").glob("one_*/*.js")]:
		for doctype in _FORM_ON.findall(path.read_text()):
			out.setdefault(doctype, {}).setdefault("hooks", set()).add("form script")
	tiers_ = ast.parse((tree.APP / "one" / "tiers.py").read_text())
	for node in tiers_.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "HEADS":
			for doctype in ast.literal_eval(node.value):
				out.setdefault(doctype, {})["head"] = True
	for doctype in paged():
		out.setdefault(doctype, {})["page"] = True
	return out


def changed(name: str) -> str:
	row = changes().get(name) or {}
	if row.get("page"):
		return "a page of our own"
	said = []
	if row.get("head"):
		said.append("a head")
	said += sorted(row.get("hooks", ()))
	if row.get("fields"):
		said.append(f"{row['fields']} fields")
	if row.get("setters"):
		said.append(f"{row['setters']} settings")
	return ", ".join(said) or "untouched"


@cache
def _refused_modules() -> tuple:
	module = ast.parse((tree.APP / "one_studio" / "customize.py").read_text())
	for node in module.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "REFUSED_MODULES":
			return ast.literal_eval(node.value)
	return ()


def studio(name: str) -> str:
	"""Whether a workspace's OneStudio may customize it (one_studio/customize.py)."""
	meta = everything()["doctypes"][name]
	return "no" if meta["single"] or meta["module"] in _refused_modules() else "yes"


@cache
def _taught() -> str:
	return "\n".join(path.read_text() for path in tree.APP.glob("*/ai*.py"))


def ai(name: str) -> str:
	"""OneAI reads any record its reader may; `taught` where a module's ai.py
	gives it tools or knowledge of its own about this one."""
	return "taught" if f'"{name}"' in _taught() else "general"


@cache
def _made() -> frozenset:
	found = set()
	for name in ("plans.py", "money.py"):
		found |= set(
			re.findall(
				r'Action\(\s*"Create",\s*"([A-Z][\w ]+)"', (tree.APP / "one_ai" / "reading" / name).read_text()
			)
		)
	return frozenset(found)


def intake(name: str) -> str:
	return "makes it" if name in _made() else ""


SEEN = {"named": "On a rail or a Home", "routed": "Opened by our screens"}
FOUND = {
	"linked": "Through a form's link",
	"connected": "Through a form's Connections",
	"related": "Under a list's Related Reports",
}
HEADER = "<!-- generated by scripts/atlas.py through scripts/docs.py — do not edit -->\n"


def _screens_page() -> list[str]:
	lines = [
		"",
		"## Our screens",
		"",
		"Each of One's own screens, with the record types its server lists for it.",
		"**Not heard** are listed but not followed, so the screen does not change when",
		"one is saved elsewhere; **bare** are numbers printed without frappe's format;",
		"**not the company's** are listed without the reader's company, in a type that",
		"has one. `tests/guards/test_atlas.py` holds each to a count that only falls.",
		"",
		"| Screen | Lists | Not heard | Bare | Not the company's |",
		"|---|---|---|---|---|",
	]
	for one in screens():
		lines.append(
			f"| {one['screen']} (`{one['file']}`) | {', '.join(one['reads']) or '–'} | {', '.join(one['unheard']) or '–'} | {', '.join(one['bare']) or '–'} | {', '.join(one['no_company']) or '–'} |"
		)
	return lines


def _way(row: dict, said: dict) -> str:
	how = row["reach"][0] if row["reach"] else None
	if how in SEEN:
		return SEEN[how].lower()
	if how in FOUND:
		return f"{FOUND[how].lower()} ({row['reach'][1][0]})"
	if (row["kind"], row["name"]) in said:
		kind, why = said[(row["kind"], row["name"])]
		return f"{kind}: {why}"
	return "**waiting**"


def page() -> str:
	said = answers()
	by_module: dict = {}
	for row in rows():
		by_module.setdefault((row["app"], row["module"] or ""), []).append(row)
	lines = [
		HEADER,
		"# The atlas",
		"",
		"Every record type, report and page frappe, erpnext and hrms ship, and One's own, with",
		"how a person reaches it in One. Upstream is read from `docs/upstream/atlas.json`",
		"(`python scripts/atlas.py --snapshot`), One from this repository, and who may open",
		"what from the demo site (`docs/atlas-site.json`, `--site`). A way in is **seen**",
		"when a rail, a Home or one of our screens names it, **found** when only a form's",
		"link, its Connections tab or a list's Related Reports leads there. Anything with",
		"neither is answered in `onedesk/one/atlas.py`, or **waiting** for a decision;",
		"`tests/guards/test_atlas.py` holds the count waiting in each module, which only falls.",
		"",
		"For each record type: who may open it (the apps whose roles read it), what One",
		"changed (a page of our own, a head on the form, scripts, events, fields, settings),",
		"whether a workspace's OneStudio may customize it, whether OneAI was taught it or",
		"reads it with its general tools, and whether OneIntake makes it from a document;",
		"then the Passover points it can be read for: whether the demo has one, whether a",
		"document sent to a customer or supplier prints from a format of ours, whether its",
		"list says more than a number, how many of its labels are still English in Arabic",
		"and German, and what One sends about it (One's notifications and upstream's",
		"Notification records; emails upstream sends from its own code are not read).",
		"Every sentence upstream says naming ERPNext, Frappe or HRMS reads One",
		"(`onedesk/translations/`, `--brand`), but for the outside names in `OUTSIDE`.",
		"",
		"| App | Seen | Found | Answered | Waiting |",
		"|---|---|---|---|---|",
	]
	for app in ("onedesk", *APPS):
		mine = [r for (a, _), rs in by_module.items() if a == app for r in rs]
		seen = sum(1 for r in mine if r["reach"] and r["reach"][0] in SEEN)
		found = sum(1 for r in mine if r["reach"] and r["reach"][0] in FOUND)
		answered = sum(1 for r in mine if not r["reach"] and (r["kind"], r["name"]) in said)
		lines.append(f"| {app} | {seen} | {found} | {answered} | {len(mine) - seen - found - answered} |")
	lines += _screens_page()
	for (app, module), mine in sorted(by_module.items()):
		lines += ["", f"## {app} / {module or 'no module'}", ""]
		types = [r for r in mine if r["kind"] == "DocType"]
		if types:
			lines += [
				"| Record | Way in | Open to | One changed | OneStudio | OneAI | OneIntake | Demo | Print | List | Still in English | Sends |",
				"|---|---|---|---|---|---|---|---|---|---|---|---|",
			]
			for r in types:
				who = open_to("DocType", r["name"])
				shown = "not read" if who is None else (", ".join(who) or "**nobody**")
				meta = everything()["doctypes"][r["name"]]
				demo = "" if meta["single"] else ("yes" if kept(r["name"]) else "**none**")
				prints = ("ours" if printed(r["name"]) else "**theirs**") if goes_out(r["name"]) else ""
				english = ", ".join(
					f"{lang} {len(labels)}" for lang, labels in untranslated(r["name"]).items() if labels
				)
				lines.append(
					f"| {r['name']} | {_way(r, said)} | {shown} | {changed(r['name'])} | {studio(r['name'])} | {ai(r['name'])} "
					f"| {intake(r['name'])} | {demo} | {prints} | {'**only an ID**' if only_an_id(r['name']) else ''} "
					f"| {english} | {', '.join(sends(r['name']))} |"
				)
		for kind in ("Report", "Page"):
			others = [r for r in mine if r["kind"] == kind]
			if others:
				lines += [
					"",
					f"{kind}s: " + "; ".join(f"{r['name']} ({_way(r, said)})" for r in others) + ".",
				]
	return "\n".join(lines) + "\n"


PARTIES = ("Customer", "Supplier")


def kept(name: str) -> bool:
	"""Point 1: the demo has one, so a walk sees it with something in it."""
	return name in set(readers().get("kept", []))


@cache
def _our_prints() -> frozenset:
	return frozenset(
		json.loads(path.read_text()).get("doc_type") for path in tree.APP.glob("*/print_format/*/*.json")
	)


def goes_out(name: str) -> bool:
	meta = everything()["doctypes"][name]
	named = any(target in PARTIES for _, target, _ in meta["links"])
	return bool(meta.get("submittable")) and named and name not in _module_dict("NOT_SENT")


def printed(name: str) -> bool:
	"""Point 11: it prints from a format of ours."""
	return name in _our_prints() or name in _module_dict("PRINTED_AS")


@cache
def _list_setters() -> dict:
	"""{doctype: {"title": field, "listed": {field: shown}}} from our property setters."""
	out: dict = {}
	for path in tree.APP.glob("*/custom/*.json"):
		data = json.loads(path.read_text())
		for ps in data.get("property_setters") or []:
			row = out.setdefault(ps.get("doc_type") or data.get("doctype"), {"listed": {}})
			if ps.get("property") == "title_field":
				row["title"] = ps.get("value")
			elif ps.get("property") == "in_list_view":
				row["listed"][ps.get("field_name")] = str(ps.get("value")) == "1"
		for field in data.get("custom_fields") or []:
			if field.get("in_list_view"):
				out.setdefault(data.get("doctype"), {"listed": {}})["listed"][field["fieldname"]] = True
	return out


def only_an_id(name: str) -> bool:
	"""Point 5: its list says nothing but a number: no title, no column, and a
	name made by a series, a hash or a counter."""
	meta = everything()["doctypes"][name]
	ours_ = _list_setters().get(name, {"listed": {}})
	listed = {f for f in meta.get("listed", []) if ours_["listed"].get(f, True)} | {
		f for f, shown in ours_["listed"].items() if shown
	}
	title = ours_.get("title", meta.get("title"))
	naming = meta.get("autoname") or ""
	meaningful = (
		naming.startswith(("field:", "prompt", "Prompt")) or (naming == "" and not meta.get("submittable"))
	)
	return not title and not listed and not meaningful


@cache
def _our_words() -> dict:
	"""Every label One translates itself, by language: its po and its translations."""
	out = {}
	for lang in LANGUAGES:
		said = {msgid for (msgid, _), text in _po(tree.APP / "locale" / f"{lang}.po").items() if text}
		said |= {msgid for msgid, _, _ in rebranded()[lang]}
		words = WORDS / f"{lang}.csv"
		if words.exists():
			import csv

			said |= {row[0] for row in csv.reader(words.read_text().splitlines()) if row}
		out[lang] = said
	return out


def untranslated(name: str) -> dict:
	"""Point 12: the labels on its form still in English, by language. A
	label of spaces, which ERPNext gives a column break, says nothing."""
	meta = everything()["doctypes"][name]
	return {
		lang: [label for label in labels if label.strip() and label not in _our_words()[lang]]
		for lang, labels in (meta.get("untranslated") or {}).items()
	}


@cache
def _sent() -> dict:
	"""Point 10: {doctype: [what is sent about it]}: One's notify() calls, and
	upstream's own Notifications that are on."""
	out: dict = {}
	for path in tree.python():
		if "one_demo" in path.parts:
			continue
		for node in ast.walk(ast.parse(path.read_text())):
			if not isinstance(node, ast.Call):
				continue
			fn = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
			if fn != "notify" or not node.args or not isinstance(node.args[0], ast.Constant):
				continue
			for kw in node.keywords:
				if (
					kw.arg == "record"
					and isinstance(kw.value, ast.Tuple)
					and isinstance(kw.value.elts[0], ast.Constant)
				):
					out.setdefault(kw.value.elts[0].value, set()).add(node.args[0].value)
	for name, one in upstream().get("notifications", {}).items():
		if one["enabled"] and one["doctype"]:
			out.setdefault(one["doctype"], set()).add(f"{name} (theirs)")
	return {doctype: sorted(names) for doctype, names in out.items()}


def sends(name: str) -> list[str]:
	return _sent().get(name, [])


@cache
def points() -> dict:
	"""{check: {"app / module": [names]}} for every record type a person
	reaches: none in the demo, sent out on another's print, a list of bare
	numbers, and labels still in English (one entry per label and language)."""
	out = {"empty": {}, "unprinted": {}, "only_an_id": {}, "english": {}}
	every = everything()["doctypes"]
	for row in rows():
		if row["kind"] != "DocType" or not row["reach"] or every[row["name"]]["single"]:
			continue
		where, name = f"{row['app']} / {row['module']}", row["name"]
		if not kept(name):
			out["empty"].setdefault(where, []).append(name)
		if goes_out(name) and not printed(name):
			out["unprinted"].setdefault(where, []).append(name)
		if only_an_id(name):
			out["only_an_id"].setdefault(where, []).append(name)
		for lang, labels in untranslated(name).items():
			out["english"].setdefault(where, []).extend(f"{name}: {label} ({lang})" for label in labels)
	return {check: {k: v for k, v in said.items() if v} for check, said in out.items()}


_IMPORT = re.compile(r"""from\s+["'](\.{1,2}/[^"']+)["']""")
_METHOD = re.compile(r"""["'](onedesk(?:\.\w+){2,})["']""")
_FOLLOW = re.compile(r"""\b(?:follow|followList|useRecord|listenIn)\(\s*["']([^"']+)["']""")
_FOLLOW_ALL = re.compile(r"""\[([^\[\]]*)\]\.map\(\s*\(?\w*\)?\s*=>\s*(?:follow|followList)\(""")
_BARE = re.compile(
	r"\{\{\s*([\w.?]+\.(?:qty|quantity|amount|total|worth|rate|price|cost|hours|count|balance|percent))\s*\}\}"
)
READS = {"get_list", "get_all", "count", "get_count"}
WRITES = {
	"insert",
	"save",
	"submit",
	"cancel",
	"delete_doc",
	"set_value",
	"db_set",
	"new_doc",
	"rename_doc",
	"sql",
	"commit",
}


def _files(start: Path) -> list[Path]:
	"""A screen's own files: its component and what it imports, but the kit."""
	seen, queue = [], [start]
	while queue:
		path = queue.pop()
		if path in seen or not path.exists() or "kit" in path.relative_to(FRONTEND).parts:
			continue
		seen.append(path)
		for rel in _IMPORT.findall(path.read_text()):
			target = (path.parent / rel).resolve()
			for candidate in (
				target,
				target.with_suffix(".vue"),
				target.with_suffix(".js"),
				target / "index.js",
			):
				if candidate.is_file():
					queue.append(candidate)
					break
	return seen


@cache
def _module(path: Path):
	return ast.parse(path.read_text()) if path.exists() else None


_TABLE = re.compile(r"`tab([^`]+)`")


def _calls(fn: ast.AST) -> tuple[set, list, bool]:
	"""Names a function calls, the reads in it, and whether it writes."""
	names, reads, writes = set(), [], False
	for node in ast.walk(fn):
		if not isinstance(node, ast.Call):
			continue
		if isinstance(node.func, ast.Name):
			names.add(node.func.id)
		elif isinstance(node.func, ast.Attribute):
			attr = node.func.attr
			said = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else None
			if attr == "sql" and isinstance(said, str) and said.lstrip().lower().startswith("select"):
				reads += _TABLE.findall(said)
			elif attr in WRITES:
				writes = True
			if (
				attr in READS
				and node.args
				and isinstance(node.args[0], ast.Constant)
				and isinstance(node.args[0].value, str)
			):
				reads.append(node.args[0].value)
	return names, reads, writes


def method_reads(method: str) -> tuple[bool, list[tuple[str, bool]]]:
	"""(whether it only reads, [(record type, said with a company)]) for a
	whitelisted method of ours, following the functions it calls in its module."""
	parts = method.split(".")
	path = tree.ROOT.joinpath(*parts[:-1]).with_suffix(".py")
	module = _module(path)
	if module is None:
		return False, []
	source = path.read_text()
	defs = {node.name: node for node in module.body if isinstance(node, ast.FunctionDef)}
	if parts[-1] not in defs:
		return False, []
	marked = any("read_only" in ast.get_source_segment(source, d) for d in defs[parts[-1]].decorator_list)
	naming = {name for name, node in defs.items() if "company" in ast.get_source_segment(source, node)}
	queue, done, reads, writes = [parts[-1]], set(), [], False
	while queue:
		name = queue.pop()
		if name in done or name not in defs:
			continue
		done.add(name)
		called, read, wrote = _calls(defs[name])
		body = ast.get_source_segment(source, defs[name])
		with_company = "company" in body or "warehouse" in body or bool(called & naming)
		reads += [(doctype, with_company) for doctype in read]
		writes |= wrote
		queue += list(called)
	return marked or not writes, reads


@cache
def screens() -> list[dict]:
	"""Every island screen: what its server reads, what it hears change, the
	numbers it prints bare, and what it reads of a company's without one."""
	build = (tree.ROOT / "frontend" / "build-islands.mjs").read_text()
	every = everything()["doctypes"]
	parents = {}
	for name, meta in every.items():
		for _, child, _ in meta.get("tables", []):
			parents.setdefault(child, set()).add(name)
	companied = {
		name
		for name, meta in every.items()
		if any(field == "company" and target == "Company" for field, target, _ in meta["links"])
	}
	out = []
	for island, source in re.findall(r'"(onedesk\.\w+)":\s*"([^"]+)"', build):
		entry = tree.ROOT / "frontend" / source
		component = _IMPORT.findall(entry.read_text())
		start = [(entry.parent / rel).resolve() for rel in component if rel.endswith(".vue")]
		files = [path for path in _files(start[0]) if not tree.vendored(path)] if start else []
		text = "\n".join(path.read_text() for path in files)
		followed = set(_FOLLOW.findall(text))
		for listed in _FOLLOW_ALL.findall(text):
			followed |= set(re.findall(r"""["']([^"']+)["']""", listed))
		reads, unfiled = set(), set()
		for method in sorted(set(_METHOD.findall(text))):
			reader, said = method_reads(method)
			if not reader:
				continue
			for doctype, with_company in said:
				if doctype not in every:
					continue
				reads.add(doctype)
				if doctype in companied and not with_company:
					unfiled.add(doctype)
		heard = {d for d in reads if every[d]["single"] or d in followed or parents.get(d, set()) & followed}
		out.append(
			{
				"screen": island.split(".", 1)[1],
				"file": str(start[0].relative_to(tree.ROOT)) if start else source,
				"reads": sorted(reads),
				"unheard": sorted(reads - heard),
				"bare": sorted(
					shown
					for shown in set(_BARE.findall(text))
					if not re.search(
						rf"\b{shown.rsplit('.', 1)[-1]}:\s*[^,\n]*\b(?:money|count|quantity|hours|plain|format_\w+)\(",
						text,
					)
				),
				"no_company": sorted(unfiled),
			}
		)
	return out


SWAPS = (
	("Frappe Personalwesen", "OneHR"),
	("Frappe Framework-Instanz", "One"),
	("Frappe-Framework", "One"),
	("Frappe Framework", "One"),
	("إطار عمل Frappe", "One"),
	("Frappe HR", "OneHR"),
	("فرابيه", "One"),
	("فرابي", "One"),
	("Frappé", "One"),
	("HRMS", "OneHR"),
	("ERPNext", "One"),
	("Frappe", "One"),
)
SAID_BRAND = re.compile(r"ERPNext|Frappe|Frappé|HRMS|فرابي")


@cache
def _module_dict(name: str) -> dict:
	module = ast.parse((tree.APP / "one" / "atlas.py").read_text())
	for node in module.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
			return ast.literal_eval(node.value)
	return {}


def _swap(text: str, outside: dict) -> str:
	kept = {}
	for i, name in enumerate(sorted(outside, key=len, reverse=True)):
		if name in text:
			kept[f"\x00{i}\x00"] = name
			text = text.replace(name, f"\x00{i}\x00")
	for theirs, ours_ in SWAPS:
		text = text.replace(theirs, ours_)
	for mark, name in kept.items():
		text = text.replace(mark, name)
	return text


@cache
def rebranded() -> dict:
	"""{lang: [(msgid, said, context)]}: every upstream sentence that names a
	brand, as One says it in English, Arabic and German."""
	outside, said = _module_dict("OUTSIDE"), _module_dict("SAID")
	out = {"en": [], **{lang: [] for lang in LANGUAGES}}
	for msgid, theirs in sorted(upstream()["brand"].items()):
		if msgid in said:
			for lang, text in zip(("en", *LANGUAGES), said[msgid], strict=True):
				out[lang].append((msgid, text, theirs["context"]))
			continue
		en = _swap(msgid, outside)
		if en == msgid:
			continue
		out["en"].append((msgid, en, theirs["context"]))
		for lang in LANGUAGES:
			out[lang].append(
				(msgid, _swap(theirs[lang] or msgid, outside) if theirs[lang] else en, theirs["context"])
			)
	return out


TRANSLATIONS = tree.APP / "translations"
WORDS = TRANSLATIONS / "words"


@cache
def translation_files() -> dict:
	"""What onedesk/translations/<lang>.csv hold: frappe reads them after
	every app's own, so One's words win."""
	import csv
	import io

	files = {}
	for lang, rows in rebranded().items():
		buffer = io.StringIO()
		writer = csv.writer(buffer, lineterminator="\n")
		for msgid, text, context in rows:
			writer.writerow([msgid.replace("\n", "\\n"), text.replace("\n", "\\n"), context])
		words = WORDS / f"{lang}.csv"
		files[lang] = buffer.getvalue() + (words.read_text() if words.exists() else "")
	return files


def main() -> int:
	args = argparse.ArgumentParser()
	args.add_argument("--snapshot", action="store_true")
	args.add_argument("--check", action="store_true")
	args.add_argument("--brand", action="store_true")
	args.add_argument("--site", action="store_true")
	opts = args.parse_args()
	if opts.site:
		setup = os.environ.get("ONE_BENCH_ENV")
		cmd = (
			f". {setup} && " if setup else ""
		) + f"cd {BENCH.parent} && bench --site {SITE} execute onedesk.one.reach.atlas"
		run = ["su", "frappe", "-c", cmd] if os.geteuid() == 0 else ["bash", "-c", cmd]
		said = subprocess.run(run, capture_output=True, text=True, check=True).stdout
		ROLES.write_text(json.dumps(json.loads(said), sort_keys=True, indent=0) + "\n")
		print(f"wrote {ROLES.relative_to(tree.ROOT)}")
		return 0
	if opts.brand:
		TRANSLATIONS.mkdir(exist_ok=True)
		for lang, text in translation_files().items():
			(TRANSLATIONS / f"{lang}.csv").write_text(text)
		print(f"wrote {TRANSLATIONS.relative_to(tree.ROOT)}")
		return 0
	if opts.snapshot:
		SNAPSHOT.write_text(json.dumps(snapshot(), sort_keys=True, separators=(",", ":")) + "\n")
		print(f"wrote {SNAPSHOT.relative_to(tree.ROOT)}")
		return 0
	if opts.check:
		if not BENCH.exists():
			print("no bench here; the snapshot is checked where there is one")
			return 0
		if json.loads(SNAPSHOT.read_text()) != snapshot():
			print("stale: docs/upstream/atlas.json. Run `python scripts/atlas.py --snapshot`.")
			return 1
		return 0
	args.print_help()
	return 0


if __name__ == "__main__":
	sys.exit(main())
