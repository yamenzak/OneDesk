"""The agreements, for somebody who has no account yet: the same text as
TrustCenter's own page, rendered by the same `assemble.render`, for a guest.
Reading here records nothing.
"""

import frappe

from onedesk.trust_center import assemble
from onedesk.trust_center.documents import DOCUMENTS

no_cache = 1
sitemap = 0


def get_context(context):
	key = frappe.form_dict.get("document")
	if key and key not in DOCUMENTS:
		raise frappe.DoesNotExistError

	context.no_cache = 1
	said = frappe._
	context.documents = [
		{"key": one, "title": said(it["title"]), "summary": said(it["summary"])}
		for one, it in DOCUMENTS.items()
	]
	context.shown = assemble.render(key) if key else None
	context.title = said(DOCUMENTS[key]["title"]) if key else frappe._("Agreements")
	return context
