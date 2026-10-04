"""A link reads as its title to whoever may pick it.

frappe shows a person's name in place of their address in every link to a User
(`show_title_field_in_link`), and fetches a title it does not have yet through
`frappe.desk.search.get_link_title`, which asks for read permission. Most people
in a workspace may pick a colleague in a link (select) without reading their
User record, so every Report View with a person in it raised "Not permitted"
once per person, and a person who may never be read (Administrator) raised it
for everyone.

The title is what the link's own search already showed them, so it is given to
anyone who may select or read the record. Anyone else gets the name back, as
frappe does for a doctype with no title, and no error.
"""

import frappe


@frappe.whitelist()
def get_link_title(doctype: str, docname: str | int):
	meta = frappe.get_meta(doctype)
	if not (meta.show_title_field_in_link and meta.title_field):
		return docname
	try:
		doc = frappe.get_lazy_doc(doctype, docname)
	except frappe.DoesNotExistError:
		frappe.clear_last_message()
		return docname
	if not any(frappe.has_permission(doctype, ptype, doc) for ptype in ("select", "read")):
		return docname
	return doc.get(meta.title_field) or docname
