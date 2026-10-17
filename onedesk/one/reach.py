"""Whether every link in a space's rail opens for the people the space is for.

    bench --site <site> execute onedesk.one.reach.check

prints what does not open, and nothing else when everything does.
"""

import glob
import json
import os
import re

import frappe

#: Roles every person on the desk holds.
EVERYBODY = ("All", "Desk User")


def _readers(doctype: str) -> set:
	source = "Custom DocPerm" if frappe.db.exists("Custom DocPerm", {"parent": doctype}) else "DocPerm"
	return set(frappe.get_all(source, {"parent": doctype, "read": 1, "permlevel": 0}, pluck="role"))


def unreachable() -> list[dict]:
	"""Every rail link to a kind of record its app's roles cannot open."""
	from onedesk.one.settings import APPS

	app = os.path.dirname(os.path.dirname(__file__))
	out = []
	for label, code, users, managers in APPS:
		for path in glob.glob(os.path.join(app, "*", "sidebar", code, f"{code}.json")):
			with open(path) as f:
				items = json.load(f).get("items", [])
			for item in items:
				doctype = item.get("link_to")
				if item.get("link_type") != "DocType" or not doctype:
					continue
				if not frappe.db.exists("DocType", doctype):
					out.append(
						{"app": label, "link": item.get("label"), "doctype": doctype, "why": "no such kind"}
					)
					continue
				if not _readers(doctype) & {*users, *managers, *EVERYBODY}:
					out.append(
						{
							"app": label,
							"link": item.get("label"),
							"doctype": doctype,
							"why": "its roles cannot read it",
						}
					)
	return out


def check() -> None:
	for one in unreachable():
		print(f"{one['app']} › {one['link']} ({one['doctype']}): {one['why']}")


#: A rail link written as an address into a kind of record's views, such as
#: OneCRM's Pipeline, /desk/opportunity/view/kanban/Pipeline.
_INTO = re.compile(r"^/desk/([a-z0-9-]+)(?:/|$|\?)")


def kind_of(url: str | None) -> str | None:
	"""The kind of record a rail address opens, or None for a page. Reads the
	database."""
	found = _INTO.match(url or "")
	if not found:
		return None
	return frappe.db.get_value("DocType", {"name": found.group(1).replace("-", " ")}, "name", cache=True)


def unopened(sidebars: dict | None) -> None:
	"""Boot: a rail link written as an address is not in the rail of somebody
	who may not read the kind it opens. frappe leaves out a DocType link a
	person cannot read, but takes an address as it is: OneCRM's Pipeline,
	shown to an administrator with no sales role, opened on "No permission for
	Page" (frappe's router, not finding Opportunity among what they may read,
	asks for a page of that name). Nor is a country's own screen where no
	company is in that country (one/countries.py)."""
	from onedesk.one import countries

	here = countries.ours()
	for sidebar in (sidebars or {}).values():
		items = sidebar.get("items")
		if not items:
			continue
		kept = []
		for item in items:
			kind = kind_of(item.get("url")) if item.get("link_type") == "URL" else None
			if kind and not frappe.has_permission(kind, "read"):
				continue
			# A country's own screen, where no company is in that country.
			if not countries.shown(item.get("link_to") or "", here):
				continue
			kept.append(item)
		sidebar["items"] = kept


def _allowed(field: str, name: str) -> list[str]:
	"""Who may open a report or a page: its Custom Role, which replaces its
	own roles, or those."""
	from frappe.core.doctype.custom_role.custom_role import get_custom_allowed_roles

	return sorted(
		get_custom_allowed_roles(field, name)
		or frappe.get_all("Has Role", {"parent": name, "parenttype": field.title()}, pluck="role")
	)


def atlas() -> dict:
	"""Who may read each record type, report and page on this site, with every
	grant One makes applied, and which record types it has any of, for
	scripts/atlas.py --site."""
	doctypes = {}
	for name in frappe.get_all("DocType", filters={"istable": 0}, pluck="name"):
		doctypes[name] = sorted(_readers(name))
	reports = {
		name: _allowed("report", name) for name in frappe.get_all("Report", filters={"is_standard": "Yes"}, pluck="name")
	}
	pages = {name: _allowed("page", name) for name in frappe.get_all("Page", pluck="name")}
	# What the demo keeps at least one of, so a walk sees each with something in it.
	kept = sorted(
		name
		for name in doctypes
		if not frappe.get_meta(name).issingle
		and not frappe.get_meta(name).is_virtual
		and frappe.db.count(name, cache=False)
	)
	return {"doctypes": doctypes, "reports": reports, "pages": pages, "kept": kept}
