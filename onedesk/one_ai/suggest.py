"""What the panel offers when it opens, for the page it opens on.

Not buttons on every screen: the panel is already one press away from all of
them, and a form carrying an AI button per feature is a form nobody reads. So
the panel opens on "What would you like to do?" and offers the few things that
make sense here — a receipt on an expense claim, a summary on a record. That
includes the things OneAI does without a conversation, like reading an
applicant's CV again: a suggestion with `run` calls that method on the open
record, and the panel says what is happening. No OneAI button goes on a page.

Each module owns its own, named in `hooks.py` under `one_ai_suggestions` as a
dict of doctype to suggestions. A suggestion is offered only to somebody who
holds the verb it names on that doctype, because offering to make a claim to a
person who cannot make one is offering a refusal.
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
		# And for a record in one state only: "why did this job fail?" on a
		# job that did not fail is a question with no answer. `when` is
		# {field: [values]}, read from the record the panel is open on.
		if one.get("when") and not _holds(on, page.get("name"), one["when"]):
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
		# Labels and questions are `_lt`, so each is in the reader's language:
		# the question is what the panel shows as theirs, and what it sends.
		# `fill` puts the question in the panel's box to be finished by the
		# reader ("Draft a reply that says: …") rather than asking it at once.
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
	held = frappe.db.get_value(doctype, name, list(when), as_dict=True) or {}
	return all(held.get(field) in values for field, values in when.items())
