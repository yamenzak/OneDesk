"""The agreements, for somebody who has no account yet: the same text as
OneLegal's own page, rendered by the same `assemble.render`, for a guest.
Reading here records nothing.
"""

import frappe

from onedesk.one_legal import assemble
from onedesk.one_legal.documents import DOCUMENTS

no_cache = 1
sitemap = 0


def get_context(context):
	key = frappe.form_dict.get("document")
	if key and key not in DOCUMENTS:
		raise frappe.DoesNotExistError

	context.no_cache = 1
	# In the reader's language: the titles and summaries are marked in
	# one_legal/gate.py (SHOWN), the text itself stays English. Called by
	# another name so the string extractor does not read `it["title"]` as one.
	said = frappe._
	context.documents = [
		{"key": one, "title": said(it["title"]), "summary": said(it["summary"])}
		for one, it in DOCUMENTS.items()
	]
	context.shown = assemble.render(key) if key else None
	context.title = said(DOCUMENTS[key]["title"]) if key else frappe._("Agreements")
	return context
