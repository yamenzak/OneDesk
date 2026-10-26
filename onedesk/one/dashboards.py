"""Dashboards: frappe's own dashboards, each under the app it is about, for
whoever works in that app. The page is the island `onedesk.dashboards` on
the page `dashboards`; how a dashboard finds its app is in One's AGENTS.md,
under dashboards.py."""

from collections import Counter

import frappe
from frappe import _

from onedesk.one import roles

HERE = "Made Here"


def _apps() -> dict[str, str]:
	"""The apps the reader works in, by their rail's module, and the ones the
	workspace turned off left out."""
	from onedesk.one import apps
	from onedesk.one_studio import reports

	off = set(apps.hidden())
	return {one["module"]: one["label"] for one in reports.places() if one["label"] not in off}


def _listed() -> dict[str, str]:
	"""Each dashboard an app's rail lists, by the module of that rail: One's
	own rails and the site's layer OneStudio places them in."""
	from frappe.desk.doctype.custom_sidebar.custom_sidebar import SITE_LAYER

	found = {}
	for row in frappe.get_all(
		"Sidebar Item",
		filters={"link_type": "Dashboard", "parenttype": ["in", ("Sidebar", "Custom Sidebar")]},
		fields=["parent", "parenttype", "link_to"],
		ignore_permissions=True,
	):
		if row.parenttype == "Sidebar":
			if frappe.db.get_value("Sidebar", row.parent, "app") == "onedesk":
				found.setdefault(row.link_to, frappe.db.get_value("Sidebar", row.parent, "module"))
		elif frappe.db.get_value("Custom Sidebar", row.parent, "user") == SITE_LAYER:
			found.setdefault(row.link_to, frappe.db.get_value("Custom Sidebar", row.parent, "module"))
	return found


def _counted(names: list[str]) -> dict[str, dict]:
	"""What each dashboard is made of: the kinds of record its charts and
	numbers count, in order, and how many of each it has."""
	made = {name: {"charts": 0, "cards": 0, "kinds": []} for name in names}
	if not names:
		return made
	for link, doctype, field in (
		("Dashboard Chart Link", "Dashboard Chart", "chart"),
		("Number Card Link", "Number Card", "card"),
	):
		rows = frappe.get_all(
			link, filters={"parent": ["in", names]}, fields=["parent", field], order_by="idx asc"
		)
		kinds = {
			one.name: one.document_type
			for one in frappe.get_all(
				doctype,
				filters={"name": ["in", list({row[field] for row in rows})]},
				fields=["name", "document_type"],
			)
		}
		for row in rows:
			made[row.parent]["charts" if field == "chart" else "cards"] += 1
			if kinds.get(row[field]):
				made[row.parent]["kinds"].append(kinds[row[field]])
	return made


@frappe.whitelist(methods=["GET"])
@frappe.read_only()
def read() -> dict:
	"""Every dashboard the reader may read, under the app it is about."""
	from onedesk.one_studio import reports

	mine = _apps()
	listed = _listed()
	rows = frappe.get_list(
		"Dashboard", fields=["name", "is_standard", "owner", "modified"], order_by="name asc", limit=500
	)
	made = _counted([one.name for one in rows])
	readable = {}
	said = []
	for one in rows:
		kinds = made[one.name]["kinds"]
		seen = [kind for kind in kinds if readable.setdefault(kind, frappe.has_permission(kind, "read"))]
		if kinds and not seen:
			continue
		if not one.is_standard:
			app = HERE
		else:
			counted = Counter(module for module in map(reports._module, seen) if module)
			module = listed.get(one.name) or (counted.most_common(1)[0][0] if counted else None)
			app = mine.get(module)
			if not app:
				continue
		said.append(
			{
				"name": one.name,
				"title": _(one.name),
				"app": app,
				"charts": made[one.name]["charts"],
				"cards": made[one.name]["cards"],
				"by": frappe.utils.get_fullname(one.owner) if not one.is_standard else None,
			}
		)
	order = list(dict.fromkeys(mine.values())) + [HERE]
	return {
		"rows": sorted(
			said,
			key=lambda one: (order.index(one["app"]) if one["app"] in order else len(order), one["title"]),
		),
		"here": _(HERE),
		"makes": roles.administers(),
	}
