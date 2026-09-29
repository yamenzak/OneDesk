"""The agreements, for somebody who has no account yet.

`/start` asks a person to agree to the Terms of Service and the Privacy Policy
before they pay, and a person cannot agree to what they cannot read. Inside a
workspace the documents are read in OneLegal's own page, which needs a sign-in;
this is the same text, rendered by the same `assemble.render`, for a guest.

On every site rather than the admin site alone: the text is the same
everywhere, and a workspace's sign-in page may link to it too. What is recorded
as agreed is still the acceptance in One (one_legal/gate.py); reading here
records nothing.
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
