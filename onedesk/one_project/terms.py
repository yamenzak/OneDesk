"""A project's payment terms and terms and conditions, carried onto every
quotation, order and invoice made for it.

Both are ERPNext's own, held on the project and started from the customer's,
a template's or the company's. The README's terms.py says more.
"""

import frappe
from erpnext.accounts.party import get_due_date_from_template, get_payment_terms_template

#: The selling documents a project's terms are carried onto.
SELLING = ("Quotation", "Sales Order", "Sales Invoice")


def of(project: str) -> tuple[str | None, str | None, str | None]:
	"""A project's payment terms and terms and conditions, each its own or,
	left empty, the nearest project above it's: a sub-project is billed as
	the job it is part of. With the project they come from when that is not
	this one."""
	from onedesk.one_project import tree

	found = [None, None]
	source = None
	for one in tree.above(project, tree.parents()):
		payment_terms, terms = frappe.db.get_value("Project", one, ["one_payment_terms", "one_terms"]) or (None, None)
		if not found[0] and payment_terms:
			found[0] = payment_terms
			source = source or (one if one != project else None)
		if not found[1] and terms:
			found[1] = terms
		if all(found):
			break
	return found[0], found[1], source


def defaults(customer: str | None = None, template: str | None = None, company: str | None = None) -> dict:
	"""What a new project for `customer` starts with: the customer's own payment
	terms before a template's, a template's before the company's, and the
	template's wording before the company's. Retention comes from the template,
	when the workspace holds retention."""
	from onedesk.one_project.retention import on
	company = company or frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	preset = (
		frappe.db.get_value(
			"Project Template",
			template,
			["one_payment_terms", "one_terms", "one_retention", "one_retention_handover"],
			as_dict=True,
		)
		if template
		else None
	) or frappe._dict()
	own = get_payment_terms_template(customer, "Customer", company) if customer else None
	found = frappe.db.get_value("Company", company, ["payment_terms", "default_selling_terms"], as_dict=True) or {}
	return {
		"payment_terms": own or preset.one_payment_terms or found.get("payment_terms"),
		"terms": preset.one_terms or found.get("default_selling_terms"),
		"retention": (preset.one_retention or 0) if on() else 0,
		"retention_handover": (preset.one_retention_handover or 0) if on() else 0,
	}


def started(doc, method=None) -> None:
	"""Project before_validate, once its kind is known: a new project starts
	with what `defaults` gives, however it is made (the form, a Sales Order's
	Create › Project, Data Import). What the New Project dialog asked for is
	kept as it was answered (`flags.one_terms_given`). An internal project
	bills nobody, so it starts with none."""
	from onedesk.one_project import kinds

	if not doc.is_new() or doc.flags.get("one_terms_given") or doc.get("one_kind") == kinds.INTERNAL:
		return
	agreed = defaults(doc.get("customer"), doc.get("project_template"), doc.get("company"))
	doc.one_payment_terms = doc.get("one_payment_terms") or agreed["payment_terms"]
	doc.one_terms = doc.get("one_terms") or agreed["terms"]
	if doc.get("one_kind") == kinds.FIXED and not doc.get("one_retention") and agreed["retention"]:
		doc.one_retention = agreed["retention"]
		doc.one_retention_handover = agreed["retention_handover"]


def give(doc, payment_terms: str | None, terms: str | None) -> None:
	"""Put the terms on a document not saved yet: the template, which ERPNext
	turns into the payment schedule, and the wording, written out for the
	document as ERPNext's form writes it."""
	if payment_terms and doc.meta.has_field("payment_terms_template"):
		doc.payment_terms_template = payment_terms
		doc.set("payment_schedule", [])
		posting = doc.get("posting_date") or doc.get("transaction_date")
		if posting and doc.meta.has_field("due_date"):
			# ERPNext dates an invoice by the party's terms, not the ones on it.
			doc.due_date = get_due_date_from_template(payment_terms, posting, doc.get("bill_date"))
	if terms and doc.meta.has_field("tc_name"):
		from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_and_conditions

		doc.tc_name = terms
		doc.terms = get_terms_and_conditions(terms, doc.as_dict())


def carried(doc, method=None) -> None:
	"""before_insert on a quotation, order or invoice: one for a project starts
	with the project's terms, and one made from an order with the order's,
	unless somebody picked others than the party's own."""
	project = doc.get("project")
	if not project:
		return
	source = _source(doc)
	if source:
		want = frappe.db.get_value(
			source[0], source[1], ["payment_terms_template", "tc_name"], as_dict=True
		) or frappe._dict()
		payment_terms, terms = want.payment_terms_template, want.tc_name
	elif doc.doctype in SELLING:
		payment_terms, terms, _from = of(project)
	else:
		# The project's terms are agreed with its customer, not its suppliers.
		return
	party = _party(doc)
	own = get_payment_terms_template(party[1], party[0], doc.get("company")) if party else None
	if doc.get("ignore_default_payment_terms_template") or doc.get("payment_terms_template") not in (None, "", own):
		payment_terms = None
	picked = doc.get("tc_name")
	if picked and picked != _default_terms(doc):
		# Chosen on the document, or carried from what it is made from.
		terms = None
	give(doc, payment_terms, terms if terms != picked else None)


def _source(doc) -> tuple[str, str] | None:
	"""The order or quotation a document is made from, when all its lines are."""
	links = {
		"Sales Invoice": ("Sales Order", "sales_order"),
		"Sales Order": ("Quotation", "prevdoc_docname"),
		"Purchase Invoice": ("Purchase Order", "purchase_order"),
	}.get(doc.doctype)
	if not links:
		return None
	named = {row.get(links[1]) for row in doc.get("items") or []}
	if len(named) != 1 or None in named or "" in named:
		return None
	return links[0], named.pop()


def _party(doc) -> tuple[str, str] | None:
	if doc.doctype == "Quotation":
		return (doc.quotation_to, doc.party_name) if doc.get("party_name") else None
	if doc.get("customer"):
		return "Customer", doc.customer
	if doc.get("supplier"):
		return "Supplier", doc.supplier
	return None


def _default_terms(doc) -> str | None:
	return frappe.db.get_value("Company", doc.get("company"), "default_selling_terms") if doc.get("company") else None
