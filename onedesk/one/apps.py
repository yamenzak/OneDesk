"""Apps a workspace has turned off, OneAI and its reading among them.

An app turned off leaves the rail, search and the pickers for everybody, and
nothing is deleted or refused. OneAI off refuses every model call and turns
OneAI off with it. The rest is in one/README.md, under Apps.
"""

import json

import frappe
from frappe import _, _lt

KEY = "one_hidden_apps"
HOST = "onedesk"
KEPT = ("One", "OneAdmin", "One Admin")
AI = "OneAI"
INTAKE = "Reading"
NEEDS = {INTAKE: AI}
SECTIONS = (AI, INTAKE)
ICONS = {AI: "oneai", INTAKE: "oneintake"}
MEMORY = {"link_to": "settings", "route_options": {"section": "memory"}}
# What reading shows in One's sidebar, which goes when reading is off.
READS = (
	{"link_to": "intake"},
	{"link_to": "Ready to Submit"},
	{"link_to": "Deadlines"},
	{"link_to": "Spending"},
	{"link_to": "settings", "route_options": {"section": "reads"}},
)
# What the Apps screen calls the switches that are not apps.
LABELS = {INTAKE: _lt("Reading")}


def hidden() -> list[str]:
	"""The rail rows (Sidebar names) the workspace has turned off."""
	try:
		said = json.loads(frappe.db.get_default(KEY) or "[]")
	except ValueError:
		return []
	off = [one for one in said if isinstance(one, str)]
	return off + [one for one, needs in NEEDS.items() if needs in off and one not in off]


def ai_on() -> bool:
	"""Whether OneAI may be asked anything in this workspace."""
	return AI not in hidden()


def intake_on() -> bool:
	"""Whether OneAI reads: it needs OneAI too."""
	return INTAKE not in hidden()


def refuse_ai() -> None:
	"""Every model call goes through run.ask or run.once, which ask this
	first. A Refused is what their callers already handle."""
	if not ai_on():
		from onedesk.one_admin import faults

		raise faults.Refused(_("OneAI is turned off for this workspace."))


def offered() -> list[dict]:
	"""One's own rail rows a workspace may turn off, in rail order, then the
	private apps it has (always on), then OneAI and its reading."""
	from frappe.desk.doctype.dock.dock import get_app_dock

	from onedesk.one import private
	from onedesk.one.settings import APP_SAID

	off = set(hidden())
	theirs = private.rail()
	rail = [
		{
			"name": row.get("link_to"),
			"title": _(row.get("title") or row.get("link_to")),
			"said": str(APP_SAID.get(row.get("link_to"), "")),
			"icon": row.get("icon"),
			"on": row.get("link_to") not in off,
		}
		for row in get_app_dock(HOST)
		if row.get("link_type") == "Sidebar" and row.get("link_to") not in KEPT and row.get("link_to") not in theirs
	]
	return rail + private.offered() + [
		{
			"name": name,
			"title": str(LABELS.get(name, name)),
			"said": str(APP_SAID.get(name, "")),
			"icon": ICONS[name],
			"on": name not in off,
			"needs": NEEDS.get(name),
		}
		for name in SECTIONS
	]


def unlisted(lists: dict[str, set], off: set) -> set:
	"""The record types only apps that are off list: what leaves search and
	the pickers. A type a visible app lists too stays. Pure."""
	gone = set().union(*(names for app, names in lists.items() if app in off)) if off else set()
	kept = set().union(*(names for app, names in lists.items() if app not in off)) if lists else set()
	return gone - kept


def _lists() -> dict[str, set]:
	"""What each of One's rail rows lists, by record type, and what One's
	OneAI and its reading sections list, as theirs."""
	from frappe.desk.doctype.dock.dock import get_app_dock

	rail = [row.get("link_to") for row in get_app_dock(HOST) if row.get("link_type") == "Sidebar"]
	found: dict[str, set] = {name: set() for name in (*rail, *SECTIONS)}
	section = None
	for row in frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Sidebar", "parent": ["in", rail]},
		fields=["parent", "type", "label", "link_type", "link_to"],
		order_by="parent asc, idx asc",
		limit=0,
	):
		if row.type == "Section Break":
			section = row.label if row.parent == "One" and row.label in SECTIONS else None
			continue
		if row.link_type == "DocType":
			found[section or row.parent].add(row.link_to)
	return found


def _where(item: dict) -> tuple:
	said = item.get("route_options") or None
	if isinstance(said, str):
		try:
			said = json.loads(said)
		except ValueError:
			pass
	return item.get("link_to"), json.dumps(said, sort_keys=True)


def sectioned(items: list[dict], off: set) -> tuple[list[dict], set]:
	"""One's sidebar without OneAI's section when it is off, and without what
	reading shows (Documents, its reports, What OneAI Reads) when reading is,
	and where each link they held went, so another sidebar can lose it too
	(OneBook's Ready to Submit, OneCalendar's Deadlines). Pure."""
	reading = {_where(one) for one in READS} if INTAKE in off else set()
	gone, kept, section = set(), [], None
	for item in items:
		if item.get("type") == "Section Break":
			section = item.get("label") if item.get("label") in off else None
		if section or _where(item) in reading:
			if item.get("link_to"):
				gone.add(_where(item))
			continue
		kept.append(item)
	if AI in off:
		kept = [item for item in kept if _where(item) != _where(MEMORY)]
	return kept, gone


def trim(sidebars: dict) -> None:
	"""`outside.kept`: OneAI's section and what reading shows, turned off,
	leave One's sidebar, and their links every other."""
	off = {name for name in SECTIONS if name in hidden()}
	if not off or not isinstance(sidebars, dict):
		return
	one = sidebars.get("One") or {}
	one_items, gone = sectioned(one.get("items") or [], off)
	if one:
		one["items"] = one_items
	for name, sidebar in sidebars.items():
		if name == "One" or not isinstance(sidebar, dict):
			continue
		sidebar["items"] = [item for item in sidebar.get("items") or [] if _where(item) not in gone]


def doctypes() -> list[str]:
	off = set(hidden())
	return sorted(unlisted(_lists(), off)) if off else []


def rehome(said: dict) -> None:
	"""A record type only apps turned off list opens on One's Home, rather
	than in whichever app frappe's ladder falls to (`outside.kept`)."""
	shells = (said.get("canonical_shell") or {}).get("DocType")
	if not isinstance(shells, dict) or "One" not in (said.get("module_sidebars") or {}):
		return
	for name in doctypes():
		shells[name] = "One"


def boot(bootinfo) -> None:
	"""What the desk hides: the apps (the rail does it through the site's
	Dock layer) and their record types (search and the pickers), and whether
	OneAI and its reading are on."""
	bootinfo["one_hidden"] = {"apps": hidden(), "doctypes": doctypes(), "ai": ai_on(), "intake": intake_on()}


@frappe.whitelist()
def read() -> dict:
	from onedesk.one import private, roles

	roles.require()
	return {"apps": offered() + private.waiting()}


@frappe.whitelist(methods=["POST"])
def save(off: str | list) -> dict:
	"""Turn these apps off and every other back on, for the whole workspace."""
	from onedesk.one import companions, roles

	roles.require()
	off = frappe.parse_json(off) if isinstance(off, str) else off
	off = list(off or [])
	off += [one for one, needs in NEEDS.items() if needs in off and one not in off]
	allowed = {one["name"] for one in offered() if not one.get("kept")}
	unknown = [one for one in off or [] if one not in allowed]
	if unknown:
		frappe.throw(_("{0} can't be turned off.").format(", ".join(unknown)))
	frappe.db.set_default(KEY, json.dumps(sorted(set(off or []))))
	companions.layer()
	frappe.clear_cache()
	frappe.publish_realtime("one_apps", after_commit=True)
	return {"apps": offered()}


@frappe.whitelist()
def search_link(
	doctype: str,
	txt: str,
	query: str | None = None,
	filters: str | dict | list | None = None,
	page_length: int = 10,
	searchfield: str | None = None,
	reference_doctype: str | None = None,
	ignore_user_permissions: bool = False,
	*,
	link_fieldname: str | None = None,
):
	"""frappe's search_link, as every Link field's picker calls it, without
	the record types of apps turned off when it's picking a DocType: the type
	of a Dynamic Link, and every other Link to DocType."""
	from frappe.desk.search import search_link as frappes

	gone = doctypes() if doctype == "DocType" and not query else []
	if gone:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		if isinstance(filters, dict):
			filters = {**filters, "name": ["not in", gone]} if "name" not in filters else filters
		else:
			filters = [*(filters or []), ["DocType", "name", "not in", gone]]
	return frappes(
		doctype,
		txt,
		query,
		filters=filters,
		page_length=page_length,
		searchfield=searchfield,
		reference_doctype=reference_doctype,
		ignore_user_permissions=ignore_user_permissions,
		link_fieldname=link_fieldname,
	)
