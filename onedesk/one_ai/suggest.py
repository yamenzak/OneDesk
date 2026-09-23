"""What the panel offers when it opens, for the page it opens on.

Not buttons on every screen: the panel is already one press away from all of
them, and a form carrying an AI button per feature is a form nobody reads. So
the panel opens on "What would you like to do?" and offers the few things that
make sense here — a receipt on an expense claim, a summary on a record.

Each module owns its own, named in `hooks.py` under `one_ai_suggestions` as a
dict of doctype to suggestions. A suggestion is offered only to somebody who
holds the verb it names on that doctype, because offering to make a claim to a
person who cannot make one is offering a refusal.
"""

import frappe

#: Offered on any record and any list, before a module's own.
EVERYWHERE = {
	"Form": [{"label": "Summarise this", "ask": "Summarise this record in a few lines."}],
	"List": [{"label": "What stands out here?", "ask": "What stands out in this list?"}],
}

#: A panel offering more than this is a menu, not a suggestion.
MOST = 4


def for_page(page: dict | None) -> list[dict]:
	page = page or {}
	doctype = (page.get("doctype") or "").strip()
	view = "Form" if page.get("name") else ("List" if doctype else "")
	if not doctype or not frappe.db.exists("DocType", doctype):
		return []

	offered = []
	for path in frappe.get_hooks("one_ai_suggestions") or []:
		offered += frappe.get_attr(path).get(doctype, [])
	offered += EVERYWHERE.get(view, [])

	said = []
	for one in offered:
		if one.get("can") and not frappe.has_permission(doctype, ptype=one["can"]):
			continue
		said.append({"label": frappe._(one["label"]), "ask": one["ask"], "file": bool(one.get("file"))})
	return said[:MOST]
