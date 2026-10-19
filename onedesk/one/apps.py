"""Apps a workspace has turned off.

An app turned off leaves the rail for everybody, and the record types only it
lists leave search and the pickers of Link and Dynamic Link fields. Nothing
is deleted or refused: its records stay, a link to one still opens it,
OneIntake still files into it, and turning it back on brings it all back.
"""

import json

import frappe
from frappe import _

KEY = "one_hidden_apps"
HOST = "onedesk"
KEPT = ("One", "OneAdmin", "One Admin")


def hidden() -> list[str]:
	"""The rail rows (Sidebar names) the workspace has turned off."""
	try:
		said = json.loads(frappe.db.get_default(KEY) or "[]")
	except ValueError:
		return []
	return [one for one in said if isinstance(one, str)]


def offered() -> list[dict]:
	"""One's own rail rows a workspace may turn off, in rail order."""
	from frappe.desk.doctype.dock.dock import get_app_dock

	off = set(hidden())
	return [
		{"name": row.get("link_to"), "title": _(row.get("title") or row.get("link_to")), "icon": row.get("icon"), "on": row.get("link_to") not in off}
		for row in get_app_dock(HOST)
		if row.get("link_type") == "Sidebar" and row.get("link_to") not in KEPT
	]


def unlisted(lists: dict[str, set], off: set) -> set:
	"""The record types only apps that are off list: what leaves search and
	the pickers. A type a visible app lists too stays. Pure."""
	gone = set().union(*(names for app, names in lists.items() if app in off)) if off else set()
	kept = set().union(*(names for app, names in lists.items() if app not in off)) if lists else set()
	return gone - kept


def _lists() -> dict[str, set]:
	"""What each of One's rail rows lists, by record type."""
	from frappe.desk.doctype.dock.dock import get_app_dock

	rail = [row.get("link_to") for row in get_app_dock(HOST) if row.get("link_type") == "Sidebar"]
	found: dict[str, set] = {name: set() for name in rail}
	for row in frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Sidebar", "parent": ["in", rail], "link_type": "DocType"},
		fields=["parent", "link_to"],
		limit=0,
	):
		found[row.parent].add(row.link_to)
	return found


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
	Dock layer) and their record types (search and the pickers)."""
	bootinfo["one_hidden"] = {"apps": hidden(), "doctypes": doctypes()}


@frappe.whitelist()
def read() -> dict:
	from onedesk.one import roles

	roles.require()
	return {"apps": offered()}


@frappe.whitelist(methods=["POST"])
def save(off: str | list) -> dict:
	"""Turn these apps off and every other back on, for the whole workspace."""
	from onedesk.one import companions, roles

	roles.require()
	off = frappe.parse_json(off) if isinstance(off, str) else off
	allowed = {one["name"] for one in offered()}
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
