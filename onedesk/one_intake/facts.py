"""Numbers and dates as a document wrote them, and the check that a model's
reading of them is really in the document.

A model reading a letter can invent: an amount it expected, a date one day
off, an IBAN with two digits swapped. So every amount, date, IBAN and
number it returns has to be found in the document's own text, allowing for
how it was written there ("1.234,56 €" is 1234.56). One that is not found
is dropped and the reading is marked unsure. Pure.
"""

import re
from datetime import date

#: Countries that write 03/04/2026 month first.
MONTH_FIRST = frozenset(("US", "PH", "CA", "FM", "GU", "MH", "PW"))

MONTHS = {
	"jan": 1, "january": 1, "januar": 1, "jänner": 1, "janvier": 1, "enero": 1, "gennaio": 1,
	"feb": 2, "february": 2, "februar": 2, "février": 2, "febrero": 2, "febbraio": 2,
	"mar": 3, "march": 3, "märz": 3, "maerz": 3, "mars": 3, "marzo": 3, "mär": 3,
	"apr": 4, "april": 4, "avril": 4, "abril": 4, "aprile": 4,
	"may": 5, "mai": 5, "mayo": 5, "maggio": 5,
	"jun": 6, "june": 6, "juni": 6, "juin": 6, "junio": 6, "giugno": 6,
	"jul": 7, "july": 7, "juli": 7, "juillet": 7, "julio": 7, "luglio": 7,
	"aug": 8, "august": 8, "août": 8, "agosto": 8,
	"sep": 9, "sept": 9, "september": 9, "septembre": 9, "septiembre": 9, "settembre": 9,
	"oct": 10, "okt": 10, "october": 10, "oktober": 10, "octobre": 10, "octubre": 10, "ottobre": 10,
	"nov": 11, "november": 11, "novembre": 11, "noviembre": 11,
	"dec": 12, "dez": 12, "december": 12, "dezember": 12, "décembre": 12, "diciembre": 12, "dicembre": 12,
}  # fmt: skip


# ------------------------------------------------------------------ numbers


def amounts(text: str) -> set[float]:
	"""Every amount written in a text, read both ways where a separator could
	be either: "1.234,56" and "1,234.56" are 1234.56; "84,20" is 84.2."""
	found = set()
	for token in re.findall(r"(?<![\w.,])-?\d[\d.,'   ]*\d|(?<![\w.,])\d", text or ""):
		token = re.sub(r"[ '  ]", "", token).lstrip("-")
		for value in _readings(token):
			found.add(round(value, 2))
	return found


def _readings(token: str) -> list[float]:
	"""What a written number can mean."""
	out = []
	dots, commas = token.count("."), token.count(",")
	candidates = []
	if not dots and not commas:
		candidates.append(token)
	else:
		last = max(token.rfind("."), token.rfind(","))
		decimals = len(token) - last - 1
		# the last separator as a decimal point, the others as thousands
		if decimals in (1, 2, 3):
			candidates.append(re.sub(r"[.,]", "", token[:last]) + "." + token[last + 1 :])
		# every separator as thousands
		candidates.append(re.sub(r"[.,]", "", token))
	for candidate in candidates:
		try:
			out.append(float(candidate))
		except ValueError:
			pass
	return out


def number(value) -> float | None:
	"""A model's number, whether it sent 1234.56 or "1.234,56 €"."""
	if isinstance(value, int | float) and not isinstance(value, bool):
		return float(value)
	said = re.sub(r"[^\d.,-]", "", str(value or ""))
	if not said:
		return None
	readings = _readings(said.lstrip("-"))
	if not readings:
		return None
	# A model answering in the document's own format: the decimal reading.
	best = readings[0]
	return -best if said.startswith("-") else best


def has_amount(value: float | None, text: str, found: set[float] | None = None) -> bool:
	if value is None:
		return True
	return round(abs(value), 2) in (found if found is not None else amounts(text))


# ------------------------------------------------------------------ dates


def parse_date(raw, country: str | None = None) -> date | None:
	"""A date as written in a document of this country: 03.04.2026, 3/4/26,
	2026-04-03, 3. April 2026, April 3, 2026."""
	said = str(raw or "").strip().lower()
	if not said:
		return None
	found = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", said)
	if found:
		return _date(*map(int, found.groups()))
	found = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$", said)
	if found:
		first, second, year = map(int, found.groups())
		year = year + 2000 if year < 100 else year
		if (country or "").upper() in MONTH_FIRST and "." not in said:
			first, second = second, first
		return _date(year, second, first)
	found = re.match(r"^(\d{1,2})\.?\s+([a-zäöüéû]+)\.?\s+(\d{4})$", said)
	if found and found.group(2) in MONTHS:
		return _date(int(found.group(3)), MONTHS[found.group(2)], int(found.group(1)))
	found = re.match(r"^([a-zäöüéû]+)\.?\s+(\d{1,2}),?\s+(\d{4})$", said)
	if found and found.group(1) in MONTHS:
		return _date(int(found.group(3)), MONTHS[found.group(1)], int(found.group(2)))
	return None


def _date(year: int, month: int, day: int) -> date | None:
	try:
		return date(year, month, day)
	except ValueError:
		return None


def dates(text: str, country: str | None = None) -> set[date]:
	"""Every date written in a text."""
	found = set()
	patterns = (
		r"\b\d{4}-\d{1,2}-\d{1,2}\b",
		r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
		r"\b\d{1,2}\.?\s+[A-Za-zÄÖÜäöüéû]+\.?\s+\d{4}\b",
		r"\b[A-Za-zÄÖÜäöüéû]+\.?\s+\d{1,2},?\s+\d{4}\b",
	)
	for pattern in patterns:
		for token in re.findall(pattern, text or ""):
			said = parse_date(token, country)
			if said:
				found.add(said)
	return found


# ------------------------------------------------------------------ identifiers and numbers


def compact(value) -> str:
	return re.sub(r"[^0-9a-z]", "", str(value or "").lower())


def has_code(value, text: str) -> bool:
	"""An IBAN, an invoice number or a reference is in the text, however it
	was spaced or punctuated there."""
	said = compact(value)
	return not said or said in compact(text)


# ------------------------------------------------------------------ the check

#: The most other facts kept from one document.
MOST_NOTED = 8


def totals_agree(net: float | None, tax: float | None, gross: float | None, lines: list[float] | None = None) -> bool:
	"""Net plus tax is gross, and the lines add up to the net, to the cent,
	where each is known."""
	if net is not None and tax is not None and gross is not None and abs(net + tax - gross) > 0.02:
		return False
	if lines and net is not None and abs(sum(lines) - net) > 0.05 and (gross is None or abs(sum(lines) - gross) > 0.05):
		return False
	return True


def check(reading: dict, text: str, country: str | None = None) -> tuple[dict, list[str]]:
	"""The reading with what is not in the text taken out, and a line for each
	thing taken out."""
	dropped: list[str] = []
	said_amounts = amounts(text)
	said_dates = dates(text, country)

	money = dict(reading.get("money") or {})
	for key in ("net", "tax", "gross"):
		value = number(money.get(key))
		# No tax is how a receipt without VAT reads, and it prints no 0,00.
		if value == 0:
			money[key] = 0.0 if key == "tax" else None
			continue
		if value is not None and not has_amount(value, text, said_amounts):
			dropped.append(f"{key} {value} is not in the document")
			value = None
		money[key] = value
	if money.get("iban") and not has_code(money["iban"], text):
		dropped.append(f"IBAN {money['iban']} is not in the document")
		money["iban"] = None
	if money.get("reference") and not has_code(money["reference"], text):
		dropped.append(f"payment reference {money['reference']} is not in the document")
		money["reference"] = None

	lines = []
	for line in reading.get("lines") or []:
		amount = number(line.get("amount"))
		if amount is not None and not has_amount(amount, text, said_amounts):
			dropped.append(f"line {line.get('text') or ''} {amount} is not in the document")
			continue
		lines.append({**line, "amount": amount, "qty": number(line.get("qty")), "unit_price": number(line.get("unit_price"))})
	if not totals_agree(money.get("net"), money.get("tax"), money.get("gross"), [one["amount"] for one in lines if one["amount"] is not None]):
		dropped.append("the totals do not add up")

	checked_dates = []
	for one in reading.get("dates") or []:
		when = parse_date(one.get("date"), country)
		if not when:
			# A period with no day ("within one month") is counted later, by
			# deadlines.py, from what it says.
			if one.get("about"):
				checked_dates.append({**one, "date": None, "counted": True, "found": 0})
			continue
		found = when in said_dates
		if not found and not one.get("counted"):
			dropped.append(f"{one.get('what') or 'date'} {when.isoformat()} is not in the document")
			continue
		checked_dates.append({**one, "date": when.isoformat(), "found": int(found)})

	issued = parse_date(reading.get("issued"), country)
	if issued and issued not in said_dates:
		dropped.append(f"issued {issued.isoformat()} is not in the document")
		issued = None

	number_said = reading.get("number")
	if number_said and not has_code(number_said, text):
		dropped.append(f"number {number_said} is not in the document")
		number_said = None

	references = [one for one in reading.get("references") or [] if one.get("value") and has_code(one["value"], text)]
	for one in reading.get("references") or []:
		if one not in references:
			dropped.append(f"{one.get('kind') or 'reference'} {one.get('value')} is not in the document")

	parties = []
	for party in reading.get("parties") or []:
		party = dict(party)
		for key in ("iban", "vat_id", "tax_number", "register", "document_number", "phone"):
			if party.get(key) and not has_code(party[key], text):
				dropped.append(f"{key} {party[key]} of {party.get('name') or 'a party'} is not in the document")
				party[key] = None
		if party.get("email") and party["email"].lower() not in (text or "").lower():
			dropped.append(f"email {party['email']} is not in the document")
			party["email"] = None
		parties.append(party)

	document = dict(reading.get("document") or {}) or None
	if document:
		if document.get("number") and not has_code(document["number"], text):
			dropped.append(f"document number {document['number']} is not in the document")
			document["number"] = None
		for key in ("issued", "expires"):
			when = parse_date(document.get(key), country)
			if when and when not in said_dates:
				dropped.append(f"document {key} {when.isoformat()} is not in the document")
				when = None
			document[key] = when.isoformat() if when else None

	# What else a person would look for at a glance: a booking code, a meter
	# reading, a plate. Kept only when its value is written in the document;
	# one that is not is simply left out, since nothing depends on it.
	noted = [
		{"label": " ".join(str(one.get("label") or "").split())[:60], "value": " ".join(str(one.get("value") or "").split())[:140]}
		for one in reading.get("facts") or []
		if isinstance(one, dict)
	]
	noted = [one for one in noted if one["label"] and one["value"] and has_code(one["value"], text)][:MOST_NOTED]

	return (
		{
			**reading,
			"facts": noted,
			"money": money,
			"lines": lines,
			"dates": checked_dates,
			"issued": issued.isoformat() if issued else None,
			"number": number_said,
			"references": references,
			"parties": parties,
			"document": document,
		},
		dropped,
	)
