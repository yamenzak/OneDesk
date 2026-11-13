"""OnePortal's part of the integration suite (one_demo/check.py runs it): a
contact invited and a supplier answering a quote request, each reader finding
only their own, a customer answering quotations, a record hidden from one
contact, and a link that opens one record for somebody without an account."""

import frappe
from frappe.utils import add_days, getdate, now_datetime, today

from onedesk.one_demo.base import COMPANY, as_user
from onedesk.one_demo.checking import VILLA, check
from onedesk.one_demo.people import OWNER


def _party_contact(doctype: str) -> str:
	"""A contact of one of the demo's customers or suppliers, with an address."""
	for link in frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "link_doctype": doctype}, fields=["parent", "link_name"]):
		if frappe.db.get_value("Contact", link.parent, "email_id") and not frappe.db.get_value("Contact", link.parent, "user"):
			return link.parent
	raise AssertionError(f"no {doctype} contact with an address")


@check
def a_supplier_is_invited_to_the_portal_and_answers_a_quote_request():
	"""Karim invites a supplier's contact to the portal, sends the invitation
	again, and the contact opens the link and is taken to set a password.
	The login is a portal one with the supplier's role. Somebody in the
	workspace is not invited, and Rania, who does not manage suppliers, may
	not invite anybody. Karim asks the supplier for a quote and the supplier prices it on the
	portal, which makes the supplier quotation. Karim takes the login away
	and gives it back, and the taken login's link no longer works. Somebody
	outside the supplier cannot answer it."""
	from unittest import mock

	from onedesk.one import outside
	from onedesk.account_center import invite
	from onedesk.one_inventory import portal as buying_portal
	from onedesk.one_portal import invite as portal_invite

	contact = _party_contact("Supplier")
	supplier = frappe.db.get_value("Dynamic Link", {"parent": contact, "link_doctype": "Supplier"}, "link_name")
	email = frappe.db.get_value("Contact", contact, "email_id")
	links = []
	with as_user("karim@one.test"), mock.patch("onedesk.one.tell.invited_to_portal", side_effect=lambda *a, **kw: links.append(kw["link"])):
		assert portal_invite.state(contact)["may"]
		assert portal_invite.invite_contact(contact)["status"] == "invited"
		portal_invite.invite_again(contact)
	user = frappe.db.get_value("Contact", contact, "user")
	assert frappe.db.get_value("User", user, "user_type") == "Website User" and "Supplier" in frappe.get_roles(user)
	with as_user(OWNER):
		ours = frappe.get_doc({"doctype": "Contact", "first_name": "Rania", "email_ids": [{"email_id": "rania@one.test", "is_primary": 1}], "links": [{"link_doctype": "Supplier", "link_name": supplier}]}).insert()
		try:
			portal_invite.invite_contact(ours.name)
			raise AssertionError("somebody in the workspace was invited to the portal")
		except frappe.ValidationError as refused:
			assert "is someone in the workspace" in str(refused)
	with as_user("rania@one.test"):
		try:
			portal_invite.invite_contact(contact)
			raise AssertionError("Rania, who does not manage the supplier, invited its contact")
		except frappe.PermissionError:
			pass
	frappe.set_user("Guest")
	invite.accept(links[0].split("key=")[1])
	assert frappe.local.response["type"] != "redirect" or "update-password" not in frappe.local.response.get("location", ""), "an old link still worked"
	invite.accept(links[-1].split("key=")[1])
	assert "update-password" in frappe.local.response["location"]

	item = frappe.db.get_value("Purchase Order Item", {}, ["item_code", "uom", "warehouse"], as_dict=True)
	with as_user("karim@one.test"):
		rfq = frappe.get_doc(
			{
				"doctype": "Request for Quotation",
				"company": COMPANY,
				"transaction_date": today(),
				"message_for_supplier": "Please quote for next month's delivery.",
				"suppliers": [{"supplier": supplier, "contact": contact, "email_id": email, "send_email": 0}],
				"items": [{"item_code": item.item_code, "qty": 40, "uom": item.uom, "conversion_factor": 1, "warehouse": item.warehouse, "schedule_date": add_days(today(), 30)}],
			}
		).insert()
		rfq.submit()
	with as_user(user):
		priced = {rfq.items[0].name: {"rate": 120, "qty": 40, "discount": 10}}
		said = buying_portal.quote_preview(rfq.name, priced)
		assert said["rows"][rfq.items[0].name]["discount"] and said["total"], said
		answered = buying_portal.send_quote(rfq.name, priced, "Delivered in two lots.")
		assert frappe.db.get_value("Supplier Quotation", answered, "supplier") == supplier
		assert frappe.db.get_value("Supplier Quotation", answered, "contact_person") == frappe.db.get_value("Contact", {"user": user}, "name"), "the quote is theirs"
		row = frappe.db.get_value(
			"Supplier Quotation Item", {"parent": answered}, ["price_list_rate", "discount_percentage", "rate"], as_dict=True
		)
		assert (row.price_list_rate, row.discount_percentage, row.rate) == (120, 10, 108), row
		sent = frappe.get_doc("Supplier Quotation", answered)
		assert said["net"] == frappe.utils.fmt_money(sent.net_total, currency=sent.currency), (said["net"], sent.net_total)
	with as_user("rania@one.test"):
		try:
			buying_portal.send_quote(rfq.name, {rfq.items[0].name: {"rate": 1, "qty": 40}})
			raise AssertionError("somebody outside the supplier answered its quote request")
		except frappe.PermissionError:
			pass
		assert outside.kind_of("project") is not None
	with as_user("karim@one.test"):
		assert portal_invite.revoke(contact)["status"] == "revoked"
		assert frappe.db.get_value("User", user, "enabled") == 0
	frappe.set_user("Guest")
	frappe.local.response.pop("location", None)
	invite.accept(links[-1].split("key=")[1])
	assert "update-password" not in (frappe.local.response.get("location") or ""), "a revoked login's link still worked"
	with as_user("karim@one.test"):
		with mock.patch("onedesk.one.tell.invited_to_portal"):
			portal_invite.restore(contact)
		assert frappe.db.get_value("User", user, "enabled") == 1


@check
def a_customer_and_a_supplier_find_their_own_on_the_portal():
	"""Khalid, Mansour & Sons' contact, opens the portal (frontend/portal):
	Home counts what he has, his invoices list, one opens with its total and
	a PDF, and another customer's refuses him. His villa's page, his profile,
	Your Data and Apps answer. Rami, Emirates Sealants' contact, opens a quote
	request sent to his supplier with the rows he prices."""
	import onedesk.one_project.portal
	from onedesk.one_inventory import portal as buying_portal
	from onedesk.one_portal import portal

	khalid, rami = "khalid@mansour.example", "sales@emiratessealants.example"
	theirs = frappe.db.get_value("Sales Invoice", {"customer": "Mansour & Sons", "docstatus": 1}, "name")
	others = frappe.db.get_value("Sales Invoice", {"customer": ("!=", "Mansour & Sons"), "docstatus": 1}, "name")
	with as_user(khalid):
		assert portal.reads()
		said = portal.home()
		home = {one["path"]: one for one in said["tiles"]}
		assert "invoices" in home and int(home["invoices"]["count"]) >= 1, home
		assert any(one["to"].startswith("invoices/") for one in said["asks"]), said["asks"]
		assert home["invoices"]["figure"], home["invoices"]
		listed = portal.rows("invoices")
		assert listed["doctype"] == "Sales Invoice" and theirs in {one["name"] for one in listed["rows"]}, listed
		said = portal.record("invoices", theirs)
		assert said["name"] == theirs and said["totals"], said
		assert said["summary"]["value"] and [one["label"] for one in said["steps"]] == ["Issued", "Paid"], said["steps"]
		assert any(one["to"].startswith("orders/") for one in said["related"]), "the order the bill came from"
		paid = portal.rows("invoices", state=listed["rows"][0]["status"])
		assert paid["rows"] and {one["status"] for one in paid["rows"]} == {listed["rows"][0]["status"]}
		assert any("download_pdf" in (one["href"] or "") for one in said["actions"]), said["actions"]
		try:
			portal.record("invoices", others)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a customer opened another customer's invoice")
		try:
			portal.rows("purchase-orders")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a customer listed a supplier's tab")
		assert onedesk.one_project.portal.page(VILLA)["title"]
		form = portal.form("profile")
		assert form["doc"]["name"] == khalid and form["fields"], form
		assert set(portal.your_data()) == {"copy", "deletion", "password"}
		assert isinstance(portal.apps(), list)
	supplier = frappe.db.get_value("Portal User", {"user": rami, "parenttype": "Supplier"}, "parent")
	sent = frappe.db.get_value("Request for Quotation Supplier", {"supplier": supplier, "docstatus": 1}, "parent")
	with as_user(rami):
		said = buying_portal.rfq(sent)
		assert said["rows"] and said["money"]["symbol"], said
		assert "rfq" in {one["path"] for one in portal.home()["tiles"]}


@check
def a_customer_accepts_one_quotation_and_declines_another_on_the_portal():
	"""Khalid has two open quotations. He accepts one, needed by the end of
	next month with his order number: erpnext makes the order from it, a
	draft for whoever made the quotation to check, who is told. He declines
	the other with a reason: erpnext sets it lost with it, and they are told.
	Neither can be answered twice, and another customer's can't be at all."""
	from unittest import mock

	from onedesk.one_crm import portal as selling_portal
	from onedesk.one_portal import portal

	khalid = "khalid@mansour.example"
	base = frappe.get_doc("Quotation", frappe.get_all("Quotation", filters={"party_name": "Mansour & Sons", "docstatus": 1}, pluck="name", limit=1)[0])
	opened = []
	for _one in range(2):
		new = frappe.copy_doc(base)
		new.transaction_date, new.valid_till, new.payment_schedule = today(), add_days(today(), 30), []
		for row in new.items:
			row.ordered_qty = 0
		new.insert(ignore_permissions=True)
		new.submit()
		opened.append(new.name)
	taken, turned = opened
	with as_user(khalid):
		assert portal.record("quotations", taken)["answer"]
		assert taken in {one["to"].split("/")[-1] for one in portal.home()["asks"]}, "an open quotation asks for an answer"
		with mock.patch("onedesk.one_crm.tell.quotation_accepted") as told:
			order = selling_portal.accept_quote("quotations", taken, add_days(today(), 45), "MS-PO-4471")
		assert told.called
		said = frappe.db.get_value("Sales Order", order, ["docstatus", "customer", "delivery_date", "po_no"], as_dict=True)
		assert frappe.db.get_value("Sales Order", order, "contact_person") == frappe.db.get_value("Contact", {"user": khalid}, "name"), "the order is his"
		assert (said.docstatus, said.customer, str(said.delivery_date), said.po_no) == (0, "Mansour & Sons", add_days(today(), 45), "MS-PO-4471"), said
		page = portal.record("quotations", taken)
		assert not page["answer"] and page["status"] == "Accepted", page["status"]
		try:
			selling_portal.accept_quote("quotations", taken, add_days(today(), 45))
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a quotation was accepted twice")
		with mock.patch("onedesk.one_crm.tell.quotation_declined") as told:
			selling_portal.decline_quote("quotations", turned, "Another supplier came in lower.")
		assert told.called
		assert frappe.db.get_value("Quotation", turned, ["status", "order_lost_reason"]) == ("Lost", "Another supplier came in lower.")
		assert portal.record("quotations", turned)["status"] == "Declined"
	other = frappe.get_all("Quotation", filters={"party_name": ("!=", "Mansour & Sons"), "docstatus": 1, "status": "Open"}, pluck="name", limit=1)
	if other:
		with as_user(khalid):
			try:
				selling_portal.decline_quote("quotations", other[0])
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("a customer declined another customer's quotation")


@check
def a_record_hidden_from_a_portal_contact_is_gone_for_them():
	"""Mansour & Sons' invoices are all Khalid's to see until one is unticked
	for him in its Portal dialog: then it neither lists nor opens for him, on
	the portal, erpnext's pages or a PDF, and the rest still do. Ticked again,
	it is back. A quote request unticked for Rami is gone for him the same
	way, and only a record's own contacts can be unticked."""
	from onedesk.one_portal import portal
	from onedesk.one_portal import share as portal_share

	khalid, rami = "khalid@mansour.example", "sales@emiratessealants.example"
	invoices = frappe.get_all("Sales Invoice", filters={"customer": "Mansour & Sons", "docstatus": 1}, pluck="name", order_by="name")
	assert len(invoices) > 1, invoices
	his, other = invoices[0], invoices[1]

	def listed(user, kind):
		frappe.local.flags.pop("one_portal_contacts", None)
		with as_user(user):
			return {one["name"] for one in portal.rows(kind)["rows"]}

	contact = frappe.db.get_value("Contact", {"user": khalid}, "name")
	assert listed(khalid, "invoices") >= {his, other}, "the whole company's, by default"
	said = portal_share.set_access("Sales Invoice", other, frappe.as_json([contact]))
	assert [one["sees"] for one in said["groups"][0]["people"] if one["contact"] == contact] == [False]
	assert his in listed(khalid, "invoices") and other not in listed(khalid, "invoices")
	with as_user(khalid):
		assert portal.record("invoices", his)["name"] == his
		assert not frappe.has_website_permission(frappe.get_doc("Sales Invoice", other)), "the PDF and erpnext's page refuse it too"
		try:
			portal.record("invoices", other)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a record unticked for a contact opened for them")
	portal_share.set_access("Sales Invoice", other, "[]")
	assert other in listed(khalid, "invoices")

	row = frappe.db.get_value("Request for Quotation Supplier", {"supplier": "Emirates Sealants & Fixings", "docstatus": 1}, ["parent"], as_dict=True)
	theirs = frappe.db.get_value("Contact", {"user": rami}, "name")
	portal_share.set_access("Request for Quotation", row.parent, frappe.as_json([theirs]))
	assert row.parent not in listed(rami, "rfq")
	portal_share.set_access("Request for Quotation", row.parent, "[]")
	assert row.parent in listed(rami, "rfq")
	try:
		portal_share.set_access("Sales Invoice", his, frappe.as_json([theirs]))
	except frappe.ValidationError:
		pass
	else:
		raise AssertionError("a record was hidden from somebody else's contact")
	frappe.local.flags.pop("one_portal_contacts", None)


@check
def a_link_opens_a_record_for_somebody_without_an_account_and_answers_once():
	"""Omar sends Khalid a link to an open quotation: anybody holding it sees
	the quotation without signing in, accepts it once with their name, and
	then only reads it. Karim sends Rami a link to a quote request, which
	prices and sends a quote as Emirates Sealants' once. A link mailed again
	goes to the same person; rotated, the old one stops and a new one opens;
	revoked or past its day, it opens nothing, and a guess opens nothing."""
	from unittest import mock

	from onedesk.one_portal import share as portal_share

	base = frappe.get_doc("Quotation", frappe.get_all("Quotation", filters={"party_name": "Mansour & Sons", "docstatus": 1}, pluck="name", limit=1)[0])
	quote = frappe.copy_doc(base)
	quote.transaction_date, quote.valid_till, quote.payment_schedule = today(), add_days(today(), 10), []
	for row in quote.items:
		row.ordered_qty = 0
	quote.insert(ignore_permissions=True)
	quote.submit()
	khalid = frappe.db.get_value("Contact", {"user": "khalid@mansour.example"}, "name")
	with as_user("omar@one.test"):
		said = portal_share.access("Quotation", quote.name)
		assert said["may"] and khalid in {one["contact"] for one in said["groups"][0]["reachable"]}
		with mock.patch("onedesk.one.tell.portal_link") as told:
			made = portal_share.make_link("Quotation", quote.name, contact=khalid, send=1)
		assert told.call_args.args[0] == "khalid@mansour.example" and told.call_args.kwargs["until"]
	token = answered = made["url"].rsplit("/", 1)[-1]
	link = frappe.get_doc("Portal Link", made["links"][0]["name"])
	assert getdate(link.expires_on) == getdate(quote.valid_till), "a quotation's link lasts as long as it does"
	assert link.token_hash != token and len(token) == 40, "only the token's hash is looked up"

	with as_user("Guest"):
		page = portal_share.link_view(token)
		assert page["kind"] == "record" and page["page"]["answer"] and "link_pdf" in page["page"]["actions"][0]["href"]
		try:
			portal_share.link_accept(token, add_days(today(), 20), by="")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a link was answered by nobody")
		with mock.patch("onedesk.one_crm.tell.quotation_accepted"):
			order = portal_share.link_accept(token, add_days(today(), 20), "MS-PO-9", by="Khalid Mansour")
		assert frappe.db.get_value("Sales Order", order, "contact_person") == khalid
		assert not portal_share.link_view(token)["page"]["answer"]
		assert portal_share.link_view(token)["answered"]["by"] == "Khalid Mansour"
		try:
			portal_share.link_decline(token, by="Khalid Mansour")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a link was answered twice")

	rfq = frappe.copy_doc(frappe.get_doc("Request for Quotation", frappe.db.get_value("Request for Quotation Supplier", {"supplier": "Emirates Sealants & Fixings", "docstatus": 1}, "parent")))
	rfq.transaction_date, rfq.schedule_date = today(), add_days(today(), 14)
	rfq.suppliers = [one for one in rfq.suppliers if one.supplier == "Emirates Sealants & Fixings"]
	for one in rfq.items:
		one.schedule_date = rfq.schedule_date
	rfq.insert(ignore_permissions=True)
	rfq.submit()
	with as_user("karim@one.test"):
		made = portal_share.make_link("Request for Quotation", rfq.name, email="quotes@emiratessealants.example")
	token = made["url"].rsplit("/", 1)[-1]
	rows = {one.name: {"qty": one.qty, "rate": 20, "discount": 10} for one in rfq.items}
	with as_user("Guest"):
		assert portal_share.link_view(token)["page"]["open"]
		assert portal_share.link_preview(token, frappe.as_json(rows))["total"]
		with mock.patch("onedesk.one_inventory.tell.quote_received"):
			sent = portal_share.link_send(token, frappe.as_json(rows), "Two weeks", by="Rami Haddad")
		assert not portal_share.link_view(token)["page"]["open"]
	assert frappe.db.get_value("Supplier Quotation", sent, ["supplier", "docstatus"]) == ("Emirates Sealants & Fixings", 0)

	with as_user("karim@one.test"):
		name = made["links"][0]["name"]
		with mock.patch("onedesk.one.tell.portal_link") as told:
			try:
				portal_share.mail_link(name)
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("an answered link was mailed again")
		again = portal_share.make_link("Request for Quotation", rfq.name, email="quotes@emiratessealants.example")
		old = again["url"].rsplit("/", 1)[-1]
		twice = portal_share.make_link("Request for Quotation", rfq.name, email="quotes@emiratessealants.example")
		assert twice["url"] == again["url"], "a second link for the same person is the one they have"
		with mock.patch("onedesk.one.tell.portal_link") as told:
			portal_share.mail_link(again["links"][0]["name"])
		assert told.called
		rotated = portal_share.rotate_link(again["links"][0]["name"])
		new = rotated["url"].rsplit("/", 1)[-1]
		states = [one["state"] for one in portal_share.revoke_link(rotated["links"][0]["name"])]
		assert states.count("revoked") == 2, states
	with as_user("Guest"), mock.patch("frappe.utils.print_format.download_pdf") as printed:
		portal_share.link_pdf(answered)
	frappe.flags.ignore_print_permissions = False
	assert printed.call_args.args[:2] == ("Quotation", quote.name), "an answered link still prints"
	frappe.db.set_value("Portal Link", link.name, "expires_on", add_days(now_datetime(), -1))
	with as_user("Guest"):
		for gone in (old, new, answered, "0" * 40, ""):
			try:
				portal_share.link_view(gone)
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("a revoked, expired or guessed link opened")
	with as_user("khalid@mansour.example"):
		try:
			portal_share.access("Quotation", quote.name)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a portal reader opened a record's Portal dialog")


@check
def a_customer_sees_each_part_of_a_bill_and_the_addresses_kept_for_them():
	"""Khalid's invoice paid in three parts says each part still to pay with
	its own date, not the last part's alone. His Addresses lists the billing
	address the workspace keeps for Mansour & Sons, which he can read but not
	open to change, and his timesheets come newest first."""
	import onedesk.one_project.portal  # noqa: F401
	from onedesk.one_portal import portal

	khalid = "khalid@mansour.example"
	parted = next(
		(
			one
			for one in frappe.get_all("Sales Invoice", filters={"customer": "Mansour & Sons", "docstatus": 1, "outstanding_amount": (">", 0)}, pluck="name")
			if frappe.db.count("Payment Schedule", {"parent": one, "outstanding": (">", 0)}) > 1
		),
		None,
	)
	kept = frappe.db.get_value("Dynamic Link", {"parenttype": "Address", "link_doctype": "Customer", "link_name": "Mansour & Sons"}, "parent")
	with as_user(khalid):
		if parted:
			facts = [one["label"] for one in portal.record("invoices", parted)["facts"]]
			parts = frappe.db.count("Payment Schedule", {"parent": parted, "outstanding": (">", 0)})
			assert sum(1 for one in facts if one.startswith("Due ")) == parts and "Due" not in facts, facts
		addresses = {one["name"]: one for one in portal.rows("addresses")["rows"]}
		assert kept in addresses and not addresses[kept]["to"], addresses
		days = [frappe.db.get_value("Timesheet", one["name"], "start_date") for one in portal.rows("timesheets")["rows"]]
		assert days == sorted(days, reverse=True), days
