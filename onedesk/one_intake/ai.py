"""What OneAI may ask of Intake: documents found by what is written in them."""

import re
from typing import Annotated

import frappe

from onedesk.one_intake.search import BEFORE, SKIP, WIDTH, file_route, files_of, messages_of, root_of, snippet

MOST_FOUND = 10


def find_documents(
	words: Annotated[str, "Words the document would contain. Include the words in the document's own language as well as the reader's: Nebenkostenabrechnung for a heating bill, فاتورة for an invoice."],
	kind: Annotated[str, "Only this kind of document: Invoice, Receipt, Reminder, Contract, Letter, Payslip, Sick Note and so on."] | None = None,
	party: Annotated[str, "Only documents from or about this supplier, customer, person or company."] | None = None,
	since: Annotated[str, "Only documents dated on or after this day, YYYY-MM-DD."] | None = None,
	until: Annotated[str, "Only documents dated on or before this day, YYYY-MM-DD."] | None = None,
) -> dict:
	"""Find documents and messages by what is written in them: letters,
	invoices, receipts, contracts, scans and mail. Answers each with what it
	is, who it is from, its date, number and amount, one sentence about it,
	the passage that matched and a link to open it. Only what the reader may
	open is found. For a question about amounts, add up the amounts found
	rather than quoting a passage."""
	asked = [word for word in re.findall(r"\w{3,}", (words or "").lower()) if word not in SKIP][:12]
	conditions, values = ["state in ('Read', 'Understood')", "name not in (select part_of from `tabReading` where ifnull(part_of, '') != '')"], {}
	if asked:
		conditions.append("match(title, text) against (%(q)s in boolean mode)")
		values["q"] = " ".join(f"{word}*" for word in asked)
	if kind:
		conditions.append("kind = %(kind)s")
		values["kind"] = kind
	if since:
		conditions.append("issued_on >= %(since)s")
		values["since"] = since
	if until:
		conditions.append("issued_on <= %(until)s")
		values["until"] = until
	if party:
		conditions.append("name in (select parent from `tabReading Party` where party_name like %(party)s or matched_name like %(party)s)")
		values["party"] = f"%{party}%"
	if len(conditions) == 2:
		return {"documents": [], "said": "Say some words, a kind, a party or dates to look for."}
	score = "match(title, text) against (%(q)s in boolean mode)" if asked else "0"
	rows = frappe.db.sql(
		f"""select name, title, kind, number, issued_on, gross, currency, summary, part, part_of, message_id,
			source_doctype, source_name, `key`, {score} as score,
			substring(text, greatest(1, locate(%(first)s, text) - %(before)s), %(width)s) as snippet
		from `tabReading` where {" and ".join(conditions)}
		order by score desc, issued_on desc limit 60""",
		{**values, "first": asked[0] if asked else "", "before": BEFORE, "width": WIDTH},
		as_dict=True,
	)
	out = []
	for row in rows:
		top = root_of(row)
		files = [one for one in files_of({**top, "name": row.name}) if one.get("attached_to_doctype") != "Communication"]
		messages = messages_of(top)
		if not files and not messages:
			continue
		party_name = frappe.db.get_value("Reading Party", {"parent": row.name, "role": ["in", ("Sender", "Holder", "Paid To")]}, "party_name")
		out.append(
			{
				"title": row.title,
				"kind": row.kind,
				"from": party_name,
				"date": str(row.issued_on) if row.issued_on else None,
				"number": row.number,
				"amount": row.gross,
				"currency": row.currency,
				"about": row.summary,
				"passage": snippet(row.snippet) if asked else None,
				"link": file_route(files[0]) if files else f"/app/onemail?thread={frappe.db.get_value('Communication', messages[0], 'one_thread') or messages[0]}",
			}
		)
		if len(out) >= MOST_FOUND:
			break
	return {"documents": out}


def page(said: dict) -> str | None:
	"""The sentence the model is told on Ready to Submit and in the inbox."""
	if said.get("page") == "intake":
		box = "Done, what OneAI filed by itself" if said.get("box") == "done" else "Waiting, what OneAI suggested and waits for a person"
		reading = (said.get("record") or "").strip()
		opened = (
			f" The document {reading} is open beside it, with what was read from it and each thing done or suggested; "
			f'read_record on Reading "{reading}" reads it.'
			if reading and frappe.db.exists("Reading", reading)
			else ""
		)
		return (
			f"The reader is in OneIntake's inbox, on {box}: one line per document that arrived by mail, scan or "
			f"upload, newest first.{opened} find_by_meaning with Reading finds a document by what it says. How "
			"OneIntake works is in its documentation (how_to)."
		)
	if said.get("page") != "ready-to-submit":
		return None
	return (
		"The reader is on Ready to Submit, which lists the drafts OneAI made from bills, receipts and payment "
		"advices that the reader may submit, where the facts checked out, the party is known and the total "
		"matches the document; a draft that disagrees with its order or looks like a duplicate shows in red. "
		"Each is submitted from its own page. list_records on Purchase Invoice with docstatus 0 reads the "
		"drafts. How OneIntake works is in its documentation (how_to)."
	)
