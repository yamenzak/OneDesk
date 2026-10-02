"""Whether every link in a space's rail opens for the people the space is for.

A space's rail links to erpnext's, hrms's and frappe's kinds of record, and
each of those decides for itself who may open it. Many open only for frappe's
System Manager, which nobody on a workspace is given (roles.py), so a link
can be in the rail and refuse everybody who sees it. This reads every rail
against the roles People hands out for its app (settings.APPS): a link
opens if the app's User or Manager roles, or a role everybody holds, may
read it. Each space's `access.py` gives what is missing.

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
	asks for a page of that name)."""
	for sidebar in (sidebars or {}).values():
		items = sidebar.get("items")
		if not items:
			continue
		kept = []
		for item in items:
			kind = kind_of(item.get("url")) if item.get("link_type") == "URL" else None
			if kind and not frappe.has_permission(kind, "read"):
				continue
			kept.append(item)
		sidebar["items"] = kept
