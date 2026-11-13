"""Frappe's, erpnext's and hrms's own desk, kept out of a workspace's.

The boot carries One's sidebars and workspaces only, for everybody, a System
Manager included: what One shows (`shown`) is what its rails and its own
modules reach, and search, pickers and global search offer nothing else.
"""

import frappe
from frappe import _

APP = "onedesk"

FIRST = "One"

#: Modules whose work lives in another app's sidebar, so frappe's own
#: sidebar for them, which lists their doctypes raw, is never shown. Where
#: their records open is `one_module_heirs`.
UNSHELLED = ("One Sheet",)


def keep(bootinfo) -> None:
	"""`extend_bootinfo`: One's sidebars and workspaces, and nobody else's."""
	kept(bootinfo)
	bootinfo["one_shown"] = {kind: sorted(names) for kind, names in shown().items()}
	if isinstance(bootinfo.get("user"), dict):
		bootinfo["user"]["can_import"] = []
	pages = (bootinfo.get("workspaces") or {}).get("pages")
	if isinstance(pages, list):
		from onedesk.account_center import private

		held = {APP, *private.names()}
		bootinfo["one_elsewhere"] = sorted(
			page["name"].lower().replace(" ", "-")
			for page in pages
			if page.get("app") not in held and page.get("name")
		)
		bootinfo["workspaces"]["pages"] = [page for page in pages if page.get("app") in held]
		bootinfo["workspaces"]["has_create_access"] = False


def kept(said: dict) -> None:
	"""One's sidebars only, One's first, and the records they own, less the
	apps the workspace turned off (one/apps.py) and those AccessCenter puts
	the reader at no level in (one/rail.py), whose records then open in
	another app that lists them. Also what `reports.sidebars` swaps in when a
	sidebar changes."""
	sidebars = said.get("module_sidebars")
	if not isinstance(sidebars, dict):
		return
	from onedesk.account_center import private
	from onedesk.one import apps, rail

	off = set(apps.hidden()) | rail.unreached()
	held = {APP, *private.names()}
	ours = {
		name: sidebar
		for name, sidebar in sidebars.items()
		if (sidebar or {}).get("app") in held and name not in off and name not in UNSHELLED
	}
	order = sorted(ours, key=lambda name: name != FIRST)
	said["module_sidebars"] = {name: ours[name] for name in order}
	apps.trim(said["module_sidebars"])
	ours = said["module_sidebars"]
	owned = said.get("entity_module")
	if isinstance(owned, dict):
		said["entity_module"] = {entity: shell for entity, shell in owned.items() if shell in ours}
	placed(said)
	apps.rehome(said)


def placed(said: dict) -> None:
	"""Where each record opens, worked out again over One's sidebars alone.
	frappe maps every route to a sidebar on the server (`build_canonical_shells`)
	before this runs, so its map still names erpnext's and hrms's; the same
	ladder over what is left puts a Project Template in OneProject rather than in
	a sidebar the reader is not given."""
	from frappe.desk.desk_views import DeskViews
	from frappe.desk.doctype.sidebar.sidebar import build_canonical_shells

	default = ((said.get("user") or {}).get("default_workspace") or {}).get("name")
	said["canonical_shell"], said["home_shell"] = build_canonical_shells(
		said["module_sidebars"], said.get("entity_module") or {}, DeskViews(), default_workspace=default
	)
	homeless(said)
	inherited(said)


def inherited(said: dict) -> None:
	"""A record type or a report no sidebar of One's lists, of a module whose
	own sidebar is erpnext's, opens in the sidebar One keeps that module's work
	in (`one_module_heirs`), where the ladder would put it in the reader's home."""
	from frappe.desk.doctype.sidebar.sidebar import linked_entities

	heirs = frappe.get_hooks("one_module_heirs") or {}
	shells = said.get("canonical_shell") or {}
	if not heirs:
		return
	sidebars = said["module_sidebars"]
	listed = {entity for sidebar in sidebars.values() for item in sidebar.get("items") or [] for entity in linked_entities(item)}
	for kind, filters in (("DocType", {"istable": 0}), ("Report", {}), ("Page", {})):
		placed = shells.get(kind)
		if not isinstance(placed, dict):
			continue
		for name, module in frappe.get_all(
			kind, filters={"module": ["in", list(heirs)], **filters}, fields=["name", "module"], as_list=True
		):
			shell = next((one for one in heirs[module] if one in sidebars), None)
			if shell and name in placed and name not in listed:
				placed[name] = shell


def homeless(said: dict) -> None:
	"""What no rail lists and no module claims opens in One's own rail.
	frappe's ladder sends it to the reader's home, which it counts as the
	sidebar with the most entries: for anybody with an employee record that
	is OneHR, so an Email Digest opened from a bookmark came up under it."""
	from frappe.desk.doctype.sidebar.sidebar import linked_entities

	sidebars = said["module_sidebars"]
	home = said.get("home_shell")
	if "One" not in sidebars or not home or home == "One":
		return
	listed = {entity for item in sidebars[home].get("items") or [] for entity in linked_entities(item)}
	owned = said.get("entity_module") or {}
	for placed in (said.get("canonical_shell") or {}).values():
		if not isinstance(placed, dict):
			continue
		for name, shell in placed.items():
			if shell == home and name not in listed and owned.get(name) != home:
				placed[name] = "One"
	said["home_shell"] = "One"


@frappe.whitelist()
def kind_of(name: str) -> bool:
	"""Whether a desk address names a kind of record or a page. One the
	reader may not open is not in their boot, so frappe's router takes it for
	a page it cannot find; it then says No access rather than Not Found
	(outside.js)."""
	name = (name or "").strip()
	return bool(name) and bool(frappe.db.exists("DocType", name.replace("-", " ")) or frappe.db.exists("Page", name))


#: frappe's record types a picker offers though no rail lists them: what a
#: record of One's links to by the person's own choice.
PICKED = ("Country", "Currency", "Gender", "Language", "Salutation", "User", "Role")

KINDS = ("DocType", "Report", "Page", "Dashboard", "Workspace")


def shown() -> dict:
	"""What One offers somebody on its own, by kind: `shown.json`, which the
	atlas writes from what One's rails, workspaces, Homes and screens reach
	(scripts/atlas.py `shown`), and whatever the workspace's private apps
	bring. Cached until the next migrate; what a person may open is still
	their roles'."""
	return frappe.cache.get_value("one_shown", generator=_shown)


def forget() -> None:
	"""`clear_cache`: a migrate or an installed private app is read again."""
	frappe.cache.delete_value("one_shown")


def _shown() -> dict:
	import json
	import os

	from onedesk.account_center import private

	with open(os.path.join(os.path.dirname(__file__), "shown.json")) as f:
		said = json.load(f)
	out = {kind: set(said.get(kind) or ()) for kind in KINDS}
	for app in private.names():
		brought(app, out)
	return out


def brought(app: str, out: dict) -> None:
	"""What a private app adds: its rails' and workspaces' links, and its own
	modules' record types, reports, pages and dashboards."""
	import glob
	import json
	import os

	from frappe.desk.doctype.sidebar.sidebar import linked_entities

	root = frappe.get_app_path(app)
	for path in glob.glob(os.path.join(root, "*", "sidebar", "*", "*.json")):
		with open(path) as f:
			for item in json.load(f).get("items") or []:
				kind = item.get("link_type") or "DocType"
				if item.get("type") == "Link" and kind in out:
					out[kind].update(linked_entities(item))
	for path in glob.glob(os.path.join(root, "*", "workspace", "*", "*.json")):
		with open(path) as f:
			out["Workspace"].add(json.load(f).get("name"))
	modules = frappe.get_module_list(app)
	for kind, filters in (("DocType", {"istable": 0}), ("Report", {}), ("Page", {}), ("Dashboard", {})):
		out[kind].update(frappe.get_all(kind, filters={"module": ["in", modules], **filters}, pluck="name"))


def pickable() -> set:
	"""The record types a picker of record types offers: what One shows, and
	what a record of One's may link to (`PICKED`)."""
	return shown()["DocType"] | set(PICKED)


@frappe.whitelist()
def doctype_query(doctype, txt, searchfield, start, page_len, filters):
	"""`standard_queries` for DocType: a picker of record types offers One's,
	never frappe's own machinery (DocType, Module Def, Workspace...)."""
	return _among("DocType", pickable(), txt, start, page_len, filters)


@frappe.whitelist()
def report_query(doctype, txt, searchfield, start, page_len, filters):
	"""`standard_queries` for Report: the reports One shows."""
	return _among("Report", shown()["Report"], txt, start, page_len, filters)


def _among(kind: str, names: set, txt, start, page_len, filters) -> list:
	held = frappe.parse_json(filters) if isinstance(filters, str) else filters
	conditions = [[kind, "name", "in", sorted(names)]]
	if isinstance(held, dict):
		conditions += [[kind, key, *(value if isinstance(value, list) else ["=", value])] for key, value in held.items()]
	elif isinstance(held, list):
		conditions += held
	if txt:
		conditions.append([kind, "name", "like", f"%{txt}%"])
	return frappe.get_all(
		kind, filters=conditions, fields=["name"], as_list=True, order_by="name", start=start, page_length=page_len
	)


@frappe.whitelist()
def search(text: str, start: int = 0, limit: int = 20, doctype: str = ""):
	"""frappe's global search, over the record types One shows. It leaves out
	a record the reader may not read, and says so in a message each time,
	which popped a dialog on every key typed in the address box; the
	records are still left out, the messages are not kept."""
	from frappe.utils.global_search import search as theirs

	kinds = shown()["DocType"]
	said = len(frappe.local.message_log)
	found = theirs(text, start=start, limit=limit, doctype=doctype)
	del frappe.local.message_log[said:]
	return [row for row in found if row.get("doctype") in kinds]


#: Where a record stands among the search bar's answers, against frappe's
#: fuzzy scores (a record type typed from its start scores about 180 to 260,
#: one whose letters are only scattered through its name about 140 to 150).
PREFIX = 300
WITHIN = 160


def awesomebar(txt: str) -> list[dict]:
	"""`awesomebar_search`: records named like what was typed, from frappe's
	global search over the record types One shows, so typing a customer's
	name in the address box goes to the customer. A record whose name starts
	with it comes first, a record named by it (a customer, an item) before a
	document about it (their invoice), then one whose name has it; one that only says it
	somewhere is frappe's own "Search for" row."""
	typed = (txt or "").strip().lower()
	if len(typed) < 2:
		return []
	out = []
	for row in search(txt, limit=40):
		title = row.get("title") or row["name"]
		kind = row["doctype"]
		label = title if title == row["name"] else f"{title} · {row['name']}"
		said = f"{title} {row['name']}".lower()
		if typed not in said:
			continue
		index = PREFIX if title.lower().startswith(typed) else WITHIN
		if row["name"].lower().startswith(typed):
			index += 20
		out.append(
			{
				"label": f"{label} ({_(kind)})",
				"description": _said(row.get("content"), {title, row["name"]}),
				"route": ["Form", row["doctype"], row["name"]],
				"index": index,
			}
		)
	return sorted(out, key=lambda one: -one["index"])[:10]


def _said(content: str | None, known: set) -> str:
	"""A record's indexed fields as one line, less the ones that only repeat
	its title or name."""
	parts = [part.strip() for part in (content or "").split("|||")]
	kept = [part for part in parts if part and part.split(" : ", 1)[-1].strip() not in known]
	return " · ".join(kept)[:120]
