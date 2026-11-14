"""OneAI in the demo: what Sahara Glass wrote down for it (Knowledge), and
a conversation Layla had with it about one of those notes, so neither list
starts empty. No model is called; the answer is written as OneAI gave it."""

import frappe

from onedesk.one_admin.gateway import said
from onedesk.one_demo.people import OWNER

KNOWLEDGE = (
	(
		"Site visits",
		"",
		"<p>Site surveys are booked at least two working days ahead, Sunday to Thursday, "
		"between 8:00 and 15:00. Bayview Tower needs a gate pass, which Samir arranges.</p>",
	),
	(
		"How we quote glass",
		"Quotation",
		"<p>A quotation names each glass by thickness, type and finish, such as 10.76 mm "
		"laminated, clear. Prices are per square metre, before tax, and hold for 30 days.</p>",
	),
)

ASKED = "When can we book a site visit at Bayview Tower?"
ANSWERED = (
	"Book it at least two working days ahead, Sunday to Thursday, between 8:00 and 15:00. "
	"Bayview Tower also needs a gate pass, which Samir arranges. (Knowledge › Site visits)"
)


def run(password=None):
	for title, applies_to, body in KNOWLEDGE:
		if not frappe.db.exists("AI Knowledge", {"title": title}):
			frappe.get_doc(
				{"doctype": "AI Knowledge", "title": title, "applies_to": applies_to or None, "enabled": 1, "body": body}
			).insert(ignore_permissions=True)
	if not frappe.db.exists("AI Chat", {"owner": OWNER, "title": "Site visits at Bayview Tower"}):
		from onedesk.one_chat import transcript

		doc = frappe.get_doc({"doctype": "AI Chat", "title": "Site visits at Bayview Tower", "titled": 1})
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("AI Chat", doc.name, "owner", OWNER, update_modified=False)
		doc.reload()
		transcript.keep(doc, [said(ASKED), said(ANSWERED, role="model")], spent=0.0)
	frappe.db.commit()
