"""What OneCRM's sales assistant makes of what OneAI read (docs/ARC-AI.md,
The agents): a customer who ordered and a lead who asked, the people who
wrote as Contacts, an order as a draft Sales Order, extra work as a draft
Quotation, and a contract as ERPNext's Contract. Pure: each answers
actions, which the agents' door takes."""

from datetime import timedelta

from frappe.utils import getdate

from onedesk.one_ai.reading import deadlines
from onedesk.one_ai.reading.act import Action as _Action
from onedesk.one_ai.reading.money import Action, _real
from onedesk.one_ai.reading.plans import _name, _split, counterpart, known, real


def customer_or_lead(reading: dict, ctx: dict) -> list[_Action]:
	"""Who ordered, as a Customer (from their lead, where they were one), and
	who asked, as a Lead: whoever the document needs and nobody has made."""
	if not real(reading, ctx) or ctx.get("direction") == "Sent":
		return []
	kind = reading.get("kind") or ""
	party = counterpart(reading)
	why = ctx.get("why_made") or ""
	if kind == "Order" and party and ctx.get("sender_lead") and party.get("matched_doctype") in (None, "Lead"):
		return [_Action("Create", "Customer", values={"lead": ctx["sender_lead"]}, key="party|customer", flow="onedesk.one_ai.reading.planning.customer_from_lead", why=why, as_person=True)]
	if not party or known(party):
		return []
	name = _name(party)
	if kind == "Order" and name:
		person = bool(party.get("is_person"))
		return [
			_Action(
				"Create",
				"Customer",
				values={k: v for k, v in {"customer_name": name, "customer_group": ctx.get("customer_group"), "territory": ctx.get("territory"), "customer_type": "Individual" if person else "Company"}.items() if v},
				key="party|customer",
				why=why,
			)
		]
	if kind == "Inquiry" and (party.get("email") or ctx.get("sender_email")):
		first, last = _split(party.get("person_name") or (name if party.get("is_person") else ctx.get("sender_name") or ""))
		values = {
			"first_name": first or (party.get("email") or ctx.get("sender_email")).split("@")[0],
			"last_name": last,
			"company_name": None if party.get("is_person") else name,
			"email_id": party.get("email") or ctx.get("sender_email"),
			"phone": party.get("phone"),
			"request_type": "Product Enquiry",
		}
		return [_Action("Create", "Lead", values={k: v for k, v in values.items() if v}, key="party|lead", why=why)]
	return []


def contact(reading: dict, ctx: dict) -> list[_Action]:
	"""The person who wrote, as a Contact: made once, only for real mail
	from outside, and a bare one Frappe made from an address completed
	rather than duplicated."""
	email = ctx.get("sender_email")
	if not real(reading, ctx) or ctx.get("direction") != "Received" or not email or ctx.get("sender_is_colleague"):
		return []
	first, last = _split(ctx.get("sender_name") or "")
	party = ctx.get("sender_party")
	links = [{"link_doctype": party[0], "link_name": party[1]}] if party and party[0] in ("Supplier", "Customer", "Lead", "Prospect") else []
	held = ctx.get("sender_contact")
	if not held:
		values = {"first_name": first or email.split("@")[0], "last_name": last, "email_ids": [{"email_id": email, "is_primary": 1}], "links": links}
		if ctx.get("sender_company"):
			values["company_name"] = ctx["sender_company"]
		return [_Action("Create", "Contact", values={k: v for k, v in values.items() if v}, key="contact")]
	out = []
	if ctx.get("sender_contact_bare") and first:
		out.append(_Action("Update", "Contact", held, {k: v for k, v in {"first_name": first, "last_name": last}.items() if v}, key="contact|name", over=("first_name",)))
	for link in links:
		if (link["link_doctype"], link["link_name"]) not in {tuple(one) for one in ctx.get("sender_contact_links") or []}:
			out.append(_Action("Add", "Contact", held, {"table": "links", "row": link}, key=f"contact|link|{link['link_name']}"))
	return out


def people(reading: dict, ctx: dict) -> list[_Action]:
	"""Everyone else in a message who can be reached, as a Contact: one that
	holds their address or number is completed (the other one added, their
	organisation linked), and nobody is made twice."""
	if not real(reading, ctx):
		return []
	out = []
	for one in ctx.get("people") or []:
		key = one.get("email") or one.get("phone")
		link = {"link_doctype": one["org"][0], "link_name": one["org"][1]} if one.get("org") else None
		if not one.get("contact"):
			first, last = _split(one.get("name") or "")
			values = {
				"first_name": first or (one.get("email") or "").split("@")[0] or one.get("phone"),
				"last_name": last,
				"email_ids": [{"email_id": one["email"], "is_primary": 1}] if one.get("email") else [],
				"phone_nos": [{"phone": one["phone"], "is_primary_phone": 1}] if one.get("phone") else [],
				"links": [link] if link else [],
				"designation": one.get("job_title"),
				"company_name": one.get("company"),
			}
			out.append(_Action("Create", "Contact", values={k: v for k, v in values.items() if v}, key=f"contact|{key}"))
			continue
		held = one["contact"]
		if one.get("email") and one["email"] not in (one.get("emails") or []):
			out.append(_Action("Add", "Contact", held, {"table": "email_ids", "row": {"email_id": one["email"]}}, key=f"contact|{held}|{one['email']}"))
		if one.get("phone") and one["phone"] not in (one.get("phones") or []):
			out.append(_Action("Add", "Contact", held, {"table": "phone_nos", "row": {"phone": one["phone"]}}, key=f"contact|{held}|{one['phone']}"))
		if link and tuple(link.values()) not in {tuple(pair) for pair in one.get("links") or []}:
			out.append(_Action("Add", "Contact", held, {"table": "links", "row": link}, key=f"contact|{held}|{link['link_name']}"))
	return out


DELIVERY_DAYS = 7


def sales_order(reading: dict, ctx: dict) -> list[Action]:
	"""An order from a customer, as a draft Sales Order. Lines that match no
	item make it a proposal, since a Sales Order row needs one."""
	if not _real(reading, ctx) or reading.get("kind") != "Order" or not ctx.get("customer"):
		return []
	items = ctx.get("customer_items") or {}
	source = reading.get("lines") or []
	rows = [
		{"item_code": items[index], "qty": float(one.get("qty") or 1), **({"rate": float(one["unit_price"])} if one.get("unit_price") is not None else {})}
		for index, one in enumerate(source)
		if items.get(index)
	]
	when = next((str(one["date"]) for one in reading.get("dates") or [] if one.get("what") in ("Due", "Deadline") and one.get("date")), None)
	values = {
		"customer": ctx["customer"],
		"transaction_date": ctx["today"],
		"delivery_date": when or str(getdate(ctx["today"]) + timedelta(days=DELIVERY_DAYS)),
		"po_no": reading.get("number"),
		"po_date": reading.get("issued_on"),
		"currency": reading.get("currency"),
		"items": rows,
	}
	missing = len(rows) < len(source) or not rows
	return [
		Action(
			"Create",
			"Sales Order",
			values={key: value for key, value in values.items() if value},
			key="books|order",
			propose=missing,
			why=ctx["said"]["unmatched"] if missing else "",
			propose_on_error=True,
		)
	]


def extra_work(reading: dict, ctx: dict) -> list[Action]:
	"""A customer asking for work beyond what they ordered, as a draft
	Quotation for Extra Work on their project it names, which becomes a
	sub-project once ordered (one_project/billing.py `ordered`). Lines that
	match no item make it a proposal, as for an order."""
	if not _real(reading, ctx) or reading.get("kind") != "Change Request" or not ctx.get("customer") or not ctx.get("project"):
		return []
	items = ctx.get("customer_items") or {}
	source = reading.get("lines") or []
	rows = [
		{"item_code": items[index], "qty": float(one.get("qty") or 1), **({"rate": float(one["unit_price"])} if one.get("unit_price") is not None else {})}
		for index, one in enumerate(source)
		if items.get(index)
	]
	values = {
		"quotation_to": "Customer",
		"party_name": ctx["customer"],
		"transaction_date": ctx["today"],
		"project": ctx["project"],
		"one_extra_work": 1,
		"items": rows,
	}
	missing = len(rows) < len(source) or not rows
	return [
		Action(
			"Create",
			"Quotation",
			values={key: value for key, value in values.items() if value},
			key="books|extra",
			propose=missing,
			why=ctx["said"]["unmatched"] if missing else "",
			propose_on_error=True,
		)
	]


def contract(reading: dict, ctx: dict) -> list[Action]:
	"""A contract with a customer or supplier, as ERPNext's Contract."""
	party = ctx.get("contract_party")
	if not _real(reading, ctx) or reading.get("kind") != "Contract" or not party:
		return []
	dates = {one.get("what"): str(one.get("date")) for one in reading.get("dates") or [] if one.get("date")}
	end = dates.get("Valid Until") or dates.get("Period End")
	notice = deadlines.period(reading.get("notice_period"))
	cancel_by = str(deadlines.before(getdate(end), *notice)) if end and notice else None
	values = {
		"party_type": party[0],
		"party_name": party[1],
		"start_date": dates.get("Valid From") or dates.get("Period Start") or reading.get("issued_on") or ctx["today"],
		"end_date": end,
		"one_notice_period": reading.get("notice_period"),
		"one_cancel_by": cancel_by,
		"contract_terms": reading.get("summary") if reading.get("sensitivity") in (None, "", "Ordinary") else ctx["said"]["see_document"],
	}
	out = [Action("Create", "Contract", values={k: v for k, v in values.items() if v}, key="books|contract")]
	if cancel_by:
		remind = str(max(getdate(cancel_by) - timedelta(days=30), getdate(ctx["today"])))
		out.append(
			_Action(
				"Create",
				"Task",
				values={"subject": ctx["said"]["decide_cancel"].format(party[1], cancel_by), "exp_end_date": remind, "one_about_doctype": party[0], "one_about": party[1], "assign_to": ctx.get("person")},
				key="task|contract",
				flow="onedesk.one_ai.reading.planning.make_task",
				sure=True,
			)
		)
	return out
