"""What the panel offers when it opens, for the page it opens on.

Each module owns its own, under `one_ai_suggestions` in `hooks.py`, and a
suggestion is offered only to somebody who holds the verb it names.
"""

import frappe
from frappe import _lt

EVERYWHERE = {
	"Form": [{"label": _lt("Summarise this"), "ask": _lt("Summarise this record in a few lines.")}],
	"List": [{"label": _lt("What stands out here?"), "ask": _lt("What stands out in this list?")}],
}

MOST = 4


SETTINGS = [
	{
		"label": _lt("Help me set this up"),
		"ask": _lt(
			"Go through these settings with me: which ones matter for a company like ours, what each "
			"is set to now, and what you would change. Suggest the changes."
		),
		"can": "write",
	},
]


def for_page(page: dict | None) -> list[dict]:
	"""A doctype's suggestions on its list or record, a workspace's on its home,
	a desk page's on that page.

	A workspace is keyed `workspace:<name>` and each of its suggestions names the
	doctype its permission is checked on, since a home page has none of its own.
	"""
	page = page or {}
	workspace = (page.get("workspace") or "").strip()
	doctype = (page.get("doctype") or "").strip()
	desk = (page.get("page") or "").strip()
	if desk:
		section = (page.get("section") or "").strip()
		key, view = f"page:{desk}/{section}" if section else f"page:{desk}", "Page"
	elif workspace:
		key, view = f"workspace:{workspace}", ""
	elif not doctype and (page.get("report") or page.get("view")) and frappe.db.exists("Report", page.get("report") or page.get("view")):
		key, view = f"report:{page.get('report') or page['view']}", "Report"
	elif doctype and frappe.db.exists("DocType", doctype):
		key, view = doctype, "Form" if page.get("name") else "List"
	else:
		return []

	offered = []
	for path in frappe.get_hooks("one_ai_suggestions") or []:
		offered += frappe.get_attr(path).get(key, [])
	if view == "Form" and doctype and frappe.get_meta(doctype).issingle:
		offered += SETTINGS
	offered += EVERYWHERE.get(view, [])

	said = []
	for one in offered:
		on = one.get("doctype") or doctype
		if one.get("can") and not (on and frappe.has_permission(on, ptype=one["can"])):
			continue
		if one.get("view") and one["view"] != view:
			continue
		if "record" in one and bool((page.get("record") or "").strip()) != one["record"]:
			continue
		if one.get("when") and not _holds(on, page.get("name") or page.get("record"), one["when"]):
			continue
		if one.get("run"):
			said.append(
				{
					"label": str(one["label"]),
					"run": one["run"],
					"arg": one["arg"],
					"said": str(one.get("said") or frappe._("Done.")),
				}
			)
			continue
		said.append(
			{
				"label": str(one["label"]),
				"ask": str(one["ask"]),
				"file": bool(one.get("file")),
				"fill": bool(one.get("fill")),
			}
		)
	return said[:MOST]


def expected(text: str | None) -> str | None:
	"""The tool a suggestion's question exists to call, if it was one.

	A suggestion names it as `expects`; the run asks for that call once if the
	answer came without it. Matched on the words sent, since that is what the
	panel sends — a question typed by hand expects nothing.
	"""
	said = (text or "").strip()
	if not said:
		return None
	for path in frappe.get_hooks("one_ai_suggestions") or []:
		for offered in frappe.get_attr(path).values():
			for one in offered:
				asked = str(one.get("ask", "")).strip()
				if not one.get("expects") or not asked:
					continue
				if said == asked or (one.get("fill") and said.startswith(asked)):
					return one["expects"]
	return None


def _holds(doctype: str | None, name: str | None, when: dict) -> bool:
	"""Whether the open record's fields have one of the values `when` names."""
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return False
	if not frappe.has_permission(doctype, "read", doc=name):
		return False
	held = frappe.db.get_value(doctype, name, list(when), as_dict=True) or {}
	return all(held.get(field) in values for field, values in when.items())
