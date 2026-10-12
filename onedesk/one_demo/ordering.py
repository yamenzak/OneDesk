"""Buying for the villa. Rania asks, two suppliers price it, the cheaper on
each line gets that line's order, and Al Noor is late. Al Noor's aluminium
is agreed for the year on a blanket order, the losing quotes expire, a
credited glass order is closed, and two suppliers are scored monthly. The
demo README's ordering row tells it in full."""

from unittest import mock

import frappe
from frappe.utils import add_days, flt

from onedesk.one_demo.base import COMPANY, ago, ahead, as_user, dated, on, save, tag, today, wh

BUYER = "karim@one.test"
SITE = "rania@one.test"
VILLA = "Mansour Villa Windows and Doors"
SEALANTS = "Emirates Sealants & Fixings"
ALUMINIUM = "Al Noor Aluminium"

#: What Rania asks for: code, quantity.
ASKED = (("SIL-CLR", 80), ("FIX-ANCH", 600), ("SEAL-EPDM", 400))
#: Each supplier's price for each, in dirhams.
PRICED = {
	ALUMINIUM: {"SIL-CLR": 33.0, "FIX-ANCH": 6.2, "SEAL-EPDM": 4.4},
	SEALANTS: {"SIL-CLR": 29.5, "FIX-ANCH": 6.6, "SEAL-EPDM": 4.7},
}
EURO = "Euro Hardware Trading"
#: Profile for the stores, asked of Al Noor and Euro Hardware: code, quantity,
#: and Euro Hardware's price in euros. Al Noor has not answered yet.
STORES_ASKED = ("ALU-6063", 500, 6.2)
#: The year's price for aluminium profile, and how much is agreed.
AGREED = ("ALU-6063", 12000, 26.5)


def run(password=None):
	project = frappe.db.get_value("Project", {"project_name": VILLA})
	_expired()
	_closed()
	if not frappe.db.exists("Material Request", {"owner": SITE, "project": project, "material_request_type": "Purchase"}):
		_villa(project, password)
	if not frappe.db.exists("Blanket Order", {"supplier": ALUMINIUM, "docstatus": 1}):
		_agreed(project)
	_scored()
	_profile()
	_asking()
	from onedesk.one_inventory import tell

	tell.orders_late()


def _villa(project, password):
	from erpnext.buying.doctype.request_for_quotation.mapper import make_supplier_quotation_from_rfq
	from erpnext.buying.doctype.supplier_quotation.mapper import make_purchase_order
	from erpnext.stock.doctype.material_request.mapper import make_request_for_quotation

	site = wh("Mansour Villa Site")
	with as_user(SITE):
		request = frappe.new_doc("Material Request")
		request.material_request_type = "Purchase"
		request.company = COMPANY
		request.project = project
		dated(request, ago(10), "transaction_date")
		request.schedule_date = ago(1)
		for code, qty in ASKED:
			request.append(
				"items",
				{"item_code": code, "qty": qty, "schedule_date": ago(1), "warehouse": site, "project": project},
			)
		request = save(request, submit=True)

	with as_user(BUYER):
		rfq = make_request_for_quotation(request.name)
		dated(rfq, ago(9), "transaction_date")
		rfq.message_for_supplier = "For the Mansour villa. Please quote your best price and when you can deliver."
		for supplier in (ALUMINIUM, SEALANTS):
			rfq.append("suppliers", {"supplier": supplier, "send_email": 0})
		rfq = save(rfq, submit=True)

	quotes = {SEALANTS: _on_the_portal(rfq, password)}
	with as_user(BUYER):
		# Al Noor sends theirs by mail, and Karim types it in.
		typed = make_supplier_quotation_from_rfq(rfq.name, for_supplier=ALUMINIUM)
		dated(typed, ago(7), "transaction_date")
		typed.valid_till = ahead(20)
		for row in typed.items:
			row.rate = PRICED[ALUMINIUM][row.item_code]
		quotes[ALUMINIUM] = save(typed, submit=True)
		portal = frappe.get_doc("Supplier Quotation", quotes[SEALANTS])
		portal.valid_till = ahead(23)
		portal.save()
		portal.submit()
		quotes[SEALANTS] = portal

		# Each line goes to whoever is cheaper on it.
		cheapest = {code: min(PRICED, key=lambda one: PRICED[one][code]) for code, _qty in ASKED}
		for supplier, wanted in ((SEALANTS, ago(2)), (ALUMINIUM, ago(1))):
			order = make_purchase_order(quotes[supplier].name)
			order.items = [row for row in order.items if cheapest[row.item_code] == supplier]
			for i, row in enumerate(order.items, 1):
				row.idx = i
			dated(order, ago(6), "transaction_date")
			order.schedule_date = wanted
			order.project = project
			for row in order.items:
				row.schedule_date = wanted
				row.warehouse = site
			order = save(order, submit=True)
			if supplier == SEALANTS:
				_received(order, ago(2))


def _on_the_portal(rfq, password) -> str:
	"""Emirates Sealants' contact is invited to the portal and prices the request
	there, which makes their quote as a draft for Karim."""
	from frappe.utils.password import update_password

	from onedesk.one import portal, portal_invite

	contact = frappe.db.get_value(
		"Dynamic Link", {"link_doctype": "Supplier", "link_name": SEALANTS, "parenttype": "Contact"}, "parent"
	)
	if not frappe.db.get_value("Contact", contact, "user"):
		with as_user(BUYER), mock.patch("onedesk.one.tell.invited_to_portal"):
			portal_invite.invite_contact(contact)
	user = frappe.db.get_value("Contact", contact, "user")
	if password:
		update_password(user, password)
	rows = {row.name: {"rate": PRICED[SEALANTS][row.item_code], "qty": row.qty} for row in rfq.items}
	with as_user(user):
		quote = portal.send_quote(rfq.name, rows, "Delivered to the villa's site within four days of the order.")
	frappe.db.set_value("Supplier Quotation", quote, "transaction_date", ago(7))
	tag(frappe.get_doc("Supplier Quotation", quote))
	return quote


def _received(order, date):
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

	receipt = make_purchase_receipt(order.name)
	dated(receipt, date)
	receipt.supplier_delivery_note = "ESF-DN-3307"
	save(receipt, submit=True)


def _agreed(project):
	"""Al Noor's aluminium profile at one price from July for a year, and the
	villa's next run of profile, asked for by Samir, ordered against it."""
	from erpnext.stock.doctype.material_request.mapper import make_purchase_order

	code, qty, rate = AGREED
	start = on(7, 1)
	with as_user(BUYER):
		agreed = frappe.new_doc("Blanket Order")
		agreed.update(
			{
				"blanket_order_type": "Purchasing",
				"supplier": ALUMINIUM,
				"company": COMPANY,
				"order_no": "AN-2026-ALU",
				"order_date": start,
				"from_date": start,
				"to_date": add_days(start, 364),
				"terms": "Profile 6063 at one price for the year, delivered to the stores in lots of at least 300 metres.",
			}
		)
		agreed.append("items", {"item_code": code, "qty": qty, "rate": rate})
		agreed = save(agreed, submit=True)

		asked = frappe.db.get_value(
			"Material Request Item",
			{"project": project, "item_code": code, "docstatus": 1, "ordered_qty": 0},
			"parent",
			order_by="creation desc",
		)
		if not asked:
			return
		order = make_purchase_order(asked)
		order.supplier = ALUMINIUM
		order.items = [row for row in order.items if row.item_code == code]
		order.transaction_date = frappe.utils.today()
		for row in order.items:
			row.blanket_order = agreed.name
			row.blanket_order_rate = rate
			row.rate = rate
		order.set_missing_values()
		for row in order.items:
			row.rate = rate
		save(order, submit=True)


#: The profile's next prices: who quotes, in what currency, at what, valid how long.
QUOTED = ((ALUMINIUM, "AED", 26.0, 20), ("Euro Hardware Trading", "EUR", 6.3, 30))
#: Al Noor's own code for the profile, on the item's supplier list.
PART_NO = "AN-6063-T5"
#: Who makes the profile, and their own number for it.
MAKER = ("Schüco International", "AWS-50.100")
#: Who asks for the next run of profile.
PROFILE_ASKER = "samir@one.test"


def _profile():
	"""Aluminium profile 6063 as its Buying view shows it: Al Noor its default
	supplier with their part number, Schüco who makes it with theirs, two
	quotes still open for the next run,
	one in euros, and Samir's request for it not yet ordered."""
	code = AGREED[0]
	item = frappe.get_doc("Item", code)
	if not item.supplier_items:
		item.append("supplier_items", {"supplier": ALUMINIUM, "supplier_part_no": PART_NO})
		defaults = next((row for row in item.item_defaults if row.company == COMPANY), None)
		if defaults:
			defaults.default_supplier = ALUMINIUM
		else:
			item.append("item_defaults", {"company": COMPANY, "default_supplier": ALUMINIUM})
		item.save()
	if not frappe.db.exists("Manufacturer", MAKER[0]):
		frappe.get_doc({"doctype": "Manufacturer", "short_name": MAKER[0]}).insert()
	if not frappe.db.exists("Item Manufacturer", {"item_code": code}):
		frappe.get_doc(
			{
				"doctype": "Item Manufacturer",
				"item_code": code,
				"manufacturer": MAKER[0],
				"manufacturer_part_no": MAKER[1],
				"is_default": 1,
			}
		).insert()
	with as_user(BUYER):
		for supplier, currency, rate, days in QUOTED:
			if frappe.db.exists(
				"Supplier Quotation",
				{"supplier": supplier, "docstatus": 1, "status": "Submitted", "valid_till": [">=", today()]},
			):
				continue
			quote = frappe.new_doc("Supplier Quotation")
			quote.supplier = supplier
			quote.company = COMPANY
			quote.currency = currency
			dated(quote, ago(3), "transaction_date")
			quote.valid_till = ahead(days)
			quote.append("items", {"item_code": code, "qty": 1200, "rate": rate})
			save(quote, submit=True)
	project = frappe.db.get_value("Project", {"project_name": VILLA})
	if frappe.db.exists("Material Request Item", {"item_code": code, "docstatus": 1, "ordered_qty": 0}):
		return
	# Samir asks for the profile, as he asked for its last run.
	with as_user(PROFILE_ASKER):
		request = frappe.new_doc("Material Request")
		request.material_request_type = "Purchase"
		request.company = COMPANY
		request.project = project
		dated(request, ago(1), "transaction_date")
		request.schedule_date = ahead(10)
		request.append(
			"items",
			{"item_code": code, "qty": 400, "schedule_date": ahead(10), "project": project, "warehouse": wh("Stores")},
		)
		save(request, submit=True)


def _expired():
	"""A quote that lost holds for a month and then expires, as ERPNext marks
	it each day. The rounds bought before this step are given their month
	after they were ordered from, since ERPNext will not order from a quote
	whose Valid Till has passed by today."""
	from erpnext.buying.doctype.supplier_quotation.supplier_quotation import set_expired_status

	for name, date in frappe.get_all(
		"Supplier Quotation",
		filters={"docstatus": 1, "valid_till": ["is", "not set"]},
		fields=["name", "transaction_date"],
		as_list=True,
	):
		frappe.db.set_value("Supplier Quotation", name, "valid_till", add_days(date, 30), update_modified=False)
	set_expired_status()


def _closed():
	"""Gulf Glass credited the broken glass found after its bill on August's
	order rather than replace it, so Karim closes that order, as nothing more
	is coming. April's six broken panes are still owed."""
	from erpnext.buying.doctype.purchase_order.purchase_order import update_status

	debited = frappe.db.sql_list(
		"""select distinct item.purchase_order
		from `tabPurchase Invoice Item` item join `tabPurchase Invoice` bill on bill.name = item.parent
		where bill.docstatus = 1 and bill.is_return = 1 and item.purchase_order is not null"""
	)
	with as_user(BUYER):
		for name in debited:
			if frappe.db.get_value("Purchase Order", name, "status") not in ("Closed", "Completed"):
				update_status("Closed", name)


def _scored():
	"""Gulf Glass and Al Noor scored each month since January, on the two
	things the Inventory Check offers: delivered on time, and accepted on
	arrival."""
	from onedesk.one_inventory import ready

	ready.add_criteria()
	criteria = frappe.get_all("Supplier Scorecard Criteria", fields=["name", "max_score", "formula", "weight"])
	standings = frappe.get_all(
		"Supplier Scorecard Standing",
		fields=["standing_name", "standing_color", "min_grade", "max_grade", "warn_rfqs", "warn_pos", "prevent_rfqs", "prevent_pos"],
	)
	for supplier in ("Gulf Glass Industries", ALUMINIUM):
		if frappe.db.exists("Supplier Scorecard", supplier):
			continue
		# The suppliers were taken on in January, before the demo's first order.
		frappe.db.set_value("Supplier", supplier, "creation", f"{on(1, 2)} 09:00:00", update_modified=False)
		with as_user(BUYER):
			card = frappe.new_doc("Supplier Scorecard")
			card.supplier = supplier
			card.period = "Per Month"
			for one in standings:
				card.append("standings", dict(one))
			for one in criteria:
				card.append(
					"criteria",
					{"criteria_name": one.name, "max_score": flt(one.max_score), "formula": one.formula, "weight": flt(one.weight)},
				)
			save(card)


def _asking():
	"""Karim asks Al Noor and Euro Hardware to price profile for the stores,
	from the Quotes page. Euro Hardware answers in euros, Al Noor not yet."""
	from erpnext.buying.doctype.request_for_quotation.mapper import make_supplier_quotation_from_rfq

	from onedesk.one_inventory import quotes

	if frappe.db.exists("Request for Quotation Supplier", {"supplier": EURO}):
		return
	code, qty, rate = STORES_ASKED
	with as_user(BUYER):
		request = frappe.new_doc("Material Request")
		request.material_request_type = "Purchase"
		request.company = COMPANY
		dated(request, ago(3), "transaction_date")
		request.schedule_date = ahead(14)
		request.append("items", {"item_code": code, "qty": qty, "schedule_date": ahead(14), "warehouse": wh("Stores")})
		request = save(request, submit=True)
		asked = frappe.get_doc("Request for Quotation", quotes.ask(request.name, [ALUMINIUM, EURO], "Prices for profile for the stores, please."))
		asked.transaction_date = ago(2)
		asked.submit()
		quote = make_supplier_quotation_from_rfq(asked.name, for_supplier=EURO)
		dated(quote, ago(1), "transaction_date")
		quote.valid_till = ahead(5)
		for row in quote.items:
			row.rate = rate
		save(quote, submit=True)
