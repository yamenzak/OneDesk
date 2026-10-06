"""What the panel offers when it opens, for the page it opens on.

Each module owns its own, under `one_ai_suggestions` in `hooks.py`, and a
suggestion is offered only to somebody who holds the verb it names.
"""

import frappe
from frappe import _lt

#: Offered on any record and any list, before a module's own.
EVERYWHERE = {
	"Form": [{"label": _lt("Summarise this"), "ask": _lt("Summarise this record in a few lines.")}],
	"List": [{"label": _lt("What stands out here?"), "ask": _lt("What stands out in this list?")}],
}

#: A panel offering more than this is a menu, not a suggestion.
MOST = 4


#: What any settings page offers, whatever module it belongs to.
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
		# A desk page, and the part of it that is open: `page:settings/profile`.
		section = (page.get("section") or "").strip()
		key, view = f"page:{desk}/{section}" if section else f"page:{desk}", "Page"
	elif workspace:
		key, view = f"workspace:{workspace}", ""
	elif not doctype and page.get("view") and frappe.db.exists("Report", page.get("view")):
		# A report: the panel names it by `view` (oneai.js), with no doctype.
		key, view = f"report:{page['view']}", "Report"
	elif doctype and frappe.db.exists("DocType", doctype):
		key, view = doctype, "Form" if page.get("name") else "List"
	else:
		return []

	offered = []
	for path in frappe.get_hooks("one_ai_suggestions") or []:
		offered += frappe.get_attr(path).get(key, [])
	# A settings page — frappe's Single — has one more: setting it up at all.
	if view == "Form" and doctype and frappe.get_meta(doctype).issingle:
		offered += SETTINGS
	offered += EVERYWHERE.get(view, [])

	said = []
	for one in offered:
		on = one.get("doctype") or doctype
		if one.get("can") and not (on and frappe.has_permission(on, ptype=one["can"])):
			continue
		# A suggestion may be for the list or for one record: "add to this
		# opening" on the list of openings has no opening to add to.
		if one.get("view") and one["view"] != view:
			continue
		# And a page open on a record or not: "add a field to this form" on
		# a page with no form open has no form to add it to.
		if "record" in one and bool((page.get("record") or "").strip()) != one["record"]:
			continue
		# And for a record in one state only. `when` is {field: [values]}, read from
		# the record the panel is open on, which a desk page names as `record`.
		if one.get("when") and not _holds(on, page.get("name") or page.get("record"), one["when"]):
			continue
		if one.get("run"):
			# Something to do rather than something to ask: a job run on the
			# record the panel is open on, with no model call in between.
			# `said` is what the panel answers with while it runs.
			said.append(
				{
					"label": str(one["label"]),
					"run": one["run"],
					"arg": one["arg"],
					"said": str(one.get("said") or frappe._("Done.")),
				}
			)
			continue
		# Labels and questions are `_lt`, so each is in the reader's language. `fill`
		# puts the question in the panel's box for the reader to finish.
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
				# A question the reader finished is theirs from where it stops.
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
