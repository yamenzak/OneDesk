"""What OneAI does with a document before any agent works, and what every
agent's planner shares: who a document is from or about, a supplier who
billed and has no record, the records a document names filed with it, and
what it teaches its parties. Each module's agent makes the rest from its own
planner.py (one_ai/agents/work.py). Pure."""

from onedesk.one_ai.reading.act import Action
from onedesk.one_ai.reading.identity import CERTAIN

REAL = ("Action", "Information", "", None)

COUNTERPART = {"CV": ("Holder", "Sender"), "Identity Document": ("Holder",), "Sick Note": ("Patient", "Holder", "Sender")}

PERSONAL = ("Personal", "Medical", "Pay", "Legal")


def counterpart(reading: dict) -> dict | None:
	"""The party a document is from or about, as far as making a record goes."""
	roles = COUNTERPART.get(reading.get("kind") or "", ("Sender",))
	for role in roles:
		for one in reading.get("parties") or []:
			if one.get("role") == role and not one.get("ours"):
				return one
	return None


def known(party: dict) -> bool:
	"""Whether the counterpart already has a record. A person is known only by
	something of their own, since a mail domain they share says which
	organisation they are with and not who they are."""
	if not party.get("matched_name"):
		return False
	return not party.get("is_person") or (party.get("score") or 0) >= CERTAIN


def strong(party: dict) -> bool:
	"""Whether a party is identified by more than its name."""
	return any(party.get(key) for key in ("vat_id", "tax_number", "iban", "register")) or bool(party.get("org_domain"))


def _name(party: dict) -> str:
	return (party.get("party_name") or "").strip()


def _split(full: str) -> tuple[str, str]:
	parts = (full or "").strip().split()
	if not parts:
		return "", ""
	return parts[0], " ".join(parts[1:])


def real(reading: dict, ctx: dict) -> bool:
	return reading.get("verdict") in REAL and not ctx.get("history") and reading.get("change") != "Nothing New"


def supplier(reading: dict, ctx: dict) -> list[Action]:
	"""A supplier who billed the company and has no record yet, known by more
	than their name. Who sent a bill is part of reading it, so OneAI makes
	the supplier before any agent works."""
	if not real(reading, ctx) or ctx.get("direction") == "Sent":
		return []
	kind = reading.get("kind") or ""
	party = counterpart(reading)
	if not party or known(party):
		return []
	name = _name(party)
	billed = kind in ("Invoice", "Credit Note") or (kind == "Receipt" and not ctx.get("sender_is_colleague"))
	if not (billed and name and strong(party)):
		return []
	return [
		Action(
			"Create",
			"Supplier",
			values={k: v for k, v in {"supplier_name": name, "supplier_group": ctx.get("supplier_group"), "supplier_type": "Company", "tax_id": party.get("vat_id") or party.get("tax_number"), "country": ctx.get("country_of", {}).get(name)}.items() if v},
			key="party|supplier",
			why=ctx.get("why_made") or "",
			confidence=(reading.get("confidence") or 100) / 100,
		)
	]


def referred(reading: dict, ctx: dict) -> list[Action]:
	"""The message or file filed with every record the document names by
	number: an order it confirms, an invoice it chases. A number is not a
	guess, so these are sure."""
	if not real(reading, ctx) or not ctx.get("carrier"):
		return []
	return [
		Action("Link", doctype, name, dict(ctx["carrier"]), key=f"link|{doctype}|{name}", sure=True)
		for doctype, name in ctx.get("referred") or []
	]


LEARNS = {
	"Supplier": {"vat_id": "tax_id", "website": "website"},
	"Customer": {"vat_id": "tax_id", "website": "website"},
	"Lead": {"website": "website", "phone": "phone"},
}


def enrich(reading: dict, ctx: dict) -> list[Action]:
	"""Every document teaches its parties something (onedesk/one_ai/reading/README.md §9). An
	empty field is filled and gets the field badge; one holding something
	else keeps it and the new value is proposed beside it, which the door
	decides from what the record says now. A phone the sender's contact does
	not have yet is added to it."""
	if not real(reading, ctx) or ctx.get("direction") == "Sent":
		return []
	out: list[Action] = []
	for one in reading.get("parties") or []:
		doctype, name = one.get("matched_doctype"), one.get("matched_name")
		if not name or one.get("ours") or (one.get("score") or 0) < 0.9 or doctype not in LEARNS:
			continue
		values = {field: one.get(key) for key, field in LEARNS[doctype].items() if one.get(key)}
		if values:
			out.append(Action("Update", doctype, name, values, key=f"enrich|{doctype}|{name}"))
	phone = next((one.get("phone") for one in reading.get("parties") or [] if one.get("role") == "Sender" and one.get("phone")), None)
	if phone and ctx.get("sender_contact") and phone not in (ctx.get("sender_contact_phones") or []):
		out.append(Action("Add", "Contact", ctx["sender_contact"], {"table": "phone_nos", "row": {"phone": phone}}, key=f"enrich|phone|{phone}"))
	return out
