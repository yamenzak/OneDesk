"""The portal a workspace's customers and suppliers sign in to.

Frappe draws it: Portal Settings lists what each role sees (erpnext's
Quotations, Orders and Invoices for a customer; Requests for Quotation and
Purchase Orders for a supplier), frappe's `portal` page lists a kind of
record through the kind's own `get_list_context`, and a row template draws
each row. One's look replaces the templates only (www/portal.html and the row
templates under templates/includes); what is listed, and for whom, stays
erpnext's and frappe's.

The page's Python is frappe's own when it lists a kind of record (its
ListPage asks for frappe's module by name), so what the template needs beyond
frappe's context comes from the Jinja methods here.
"""

import frappe
from frappe import _, _lt
from frappe.website.utils import get_portal_sidebar_items

#: Portal Settings rows One has no use for: Issue has no place in One, and a
#: Material Request is the workspace's own, not something a customer raises.
OFF = ("/issues", "/material-requests")

#: Portal Settings rows renamed in plain words: erpnext names a supplier's tabs
#: after its doctypes.
TITLES = {"/rfq": "Quote Requests", "/supplier-quotations": "Quotes"}

#: The same titles, for translation: the rows hold the English, and a tab's
#: title is translated as it is drawn.
SAID = (_lt("Quote Requests"), _lt("Quotes"))

#: erpnext's indicator colours, as the portal's pills draw them.
TONES = {"green": "green", "blue": "blue", "orange": "orange", "yellow": "orange", "red": "red"}

#: How many of a kind the home counts before it says "100+".
COUNTED = 100

#: The states of a kind that wait on the reader, and how the home says so.
WAITING = {
	"Sales Invoice": (("Unpaid", "Overdue", "Partly Paid"), lambda n: _("{0} to pay").format(n)),
	"Purchase Order": (("To Receive and Bill", "To Receive"), lambda n: _("{0} to deliver").format(n)),
}


def one_portal_tabs() -> list[dict]:
	"""The portal's tabs, from Portal Settings by the reader's roles, the one
	being read marked."""
	request = getattr(frappe.local, "request", None)
	here = "/" + (request.path.strip("/").split("/")[0] if request else "")
	return [
		{"title": _(item.get("title")), "route": item.get("route"), "current": item.get("route") == here}
		for item in get_portal_sidebar_items()
		if item.get("route")
	]


def one_portal_tone(colour: str | None) -> str:
	"""The pill an erpnext indicator colour is drawn as."""
	return TONES.get((colour or "").strip(), "gray")


def one_portal_home() -> list[dict]:
	"""What the reader has, a row a tab with anything in it: how many of each
	kind are theirs, read the way the tab's own list reads them, and how many
	wait on them (WAITING)."""
	from frappe.www.list import get_list_data_for_context

	rows = []
	for item in get_portal_sidebar_items():
		doctype = item.get("reference_doctype")
		if not doctype:
			continue
		try:
			found = get_list_data_for_context(None, doctype, limit=COUNTED + 1)
		except frappe.PermissionError:
			continue
		if not found:
			continue
		states, say = WAITING.get(doctype, ((), None))
		waiting = sum(
			1
			for one in found
			if (one.get("status") if isinstance(one, dict) else getattr(one, "status", None)) in states
		)
		rows.append(
			{
				"title": _(item.get("title")),
				"route": item.get("route"),
				"count": f"{COUNTED}+" if len(found) > COUNTED else str(len(found)),
				"waiting": say(waiting) if waiting else "",
			}
		)
	return rows


#: Who a contact's login may be a portal user of.
PARTIES = ("Customer", "Supplier")


def invited(doc, method=None) -> None:
	"""Contact on_update: a contact's login is a portal user of each customer
	and supplier the contact is for, which is what erpnext's lists read. Its
	own Invite as User makes the login and stops there."""
	if not doc.user or frappe.db.get_value("User", doc.user, "user_type") != "Website User":
		return
	for link in doc.links or []:
		if link.link_doctype not in PARTIES:
			continue
		if frappe.db.exists(
			"Portal User", {"parenttype": link.link_doctype, "parent": link.link_name, "user": doc.user}
		):
			continue
		party = frappe.get_doc(link.link_doctype, link.link_name)
		party.append("portal_users", {"user": doc.user})
		party.flags.ignore_permissions = True
		party.save()


def settle() -> None:
	"""Turn off the Portal Settings rows One has no use for (OFF) and name the
	supplier's tabs plainly (TITLES). An administrator who turns one back on
	keeps it until the next install."""
	for route in OFF:
		frappe.db.set_value("Portal Menu Item", {"parent": "Portal Settings", "route": route}, "enabled", 0)
	for route, title in TITLES.items():
		frappe.db.set_value("Portal Menu Item", {"parent": "Portal Settings", "route": route}, "title", title)
	frappe.cache.delete_key("portal_menu_items")
