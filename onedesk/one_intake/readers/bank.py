"""Bank statements read as data: ISO 20022 CAMT.053 and SWIFT MT940.

Each line of a statement is a fact the bank already wrote down: the date,
the amount, who paid or was paid, their IBAN and the reference. Pure.
"""

import re
from decimal import Decimal, InvalidOperation

from onedesk.one_intake.readers import markup as m


def camt(content: bytes) -> dict | None:
	"""A CAMT.053 (or .052) statement, or None when this is not one."""
	root = m.root(content)
	if root is None or m.local(root.tag) != "Document":
		return None
	wrapper = m.either(m.find(root, "BkToCstmrStmt"), m.find(root, "BkToCstmrAcctRpt"))
	statement = m.either(m.find(wrapper, "Stmt"), m.find(wrapper, "Rpt"))
	if statement is None:
		return None
	balances = {}
	for balance in m.children(statement, "Bal"):
		code = m.text(balance, "Tp/CdOrPrtry/Cd")
		balances[code] = _signed(m.text(balance, "Amt"), m.text(balance, "CdtDbtInd"))
	entries = []
	for entry in m.children(statement, "Ntry"):
		credit = (m.text(entry, "CdtDbtInd") or "") == "CRDT"
		detail = m.find(entry, "NtryDtls/TxDtls")
		# The other side: who paid us on a credit, whom we paid on a debit.
		side = "Dbtr" if credit else "Cdtr"
		parties = m.find(detail, "RltdPties")
		entries.append(
			{
				"date": m.text(entry, "BookgDt/Dt") or (m.text(entry, "BookgDt/DtTm") or "")[:10] or None,
				"value_date": m.text(entry, "ValDt/Dt"),
				"amount": _signed(m.text(entry, "Amt"), m.text(entry, "CdtDbtInd")),
				"currency": m.attribute(entry, "Amt", "Ccy"),
				"party": m.text(parties, f"{side}/Nm") or m.text(parties, f"{side}/Pty/Nm"),
				"party_iban": _compact(m.text(parties, f"{side}Acct/Id/IBAN")),
				"reference": m.text(detail, "Refs/EndToEndId"),
				"text": " ".join(
					one.text.strip() for one in m.find_all(detail, "RmtInf/Ustrd") if one.text
				)
				or m.text(entry, "AddtlNtryInf"),
			}
		)
	return {
		"format": "CAMT",
		"account_iban": _compact(m.text(statement, "Acct/Id/IBAN")),
		"currency": m.text(statement, "Acct/Ccy"),
		"opening": balances.get("OPBD") or balances.get("PRCD"),
		"closing": balances.get("CLBD"),
		"from": (m.text(statement, "FrToDt/FrDtTm") or "")[:10] or None,
		"to": (m.text(statement, "FrToDt/ToDtTm") or "")[:10] or None,
		"entries": entries,
	}


#: `:61:` — value date, optional entry date, C/D (R for a reversal), amount.
LINE = re.compile(r"^(\d{6})(\d{4})?(R?[CD])[A-Z]?([\d,]+)")

#: German `:86:` sub-fields: ?20–?29 the purpose, ?32/?33 the name, ?31 the
#: account or IBAN, ?38 the IBAN.
SUBFIELD = re.compile(r"\?(\d{2})")


def mt940(text: str) -> dict | None:
	"""An MT940 statement, or None when this is not one."""
	if ":20:" not in text or ":61:" not in text:
		return None
	fields = _fields(text)
	opening = closing = None
	account = None
	entries, currency = [], None
	for tag, value in fields:
		if tag == "25":
			account = value.strip()
		elif tag.startswith("60"):
			opening, currency = _balance(value)
		elif tag.startswith("62"):
			closing, _currency = _balance(value)
		elif tag == "61":
			found = LINE.match(value)
			if not found:
				continue
			day, _entry, sign, amount = found.groups()
			entries.append(
				{
					"date": _yymmdd(day),
					"amount": _signed(amount.replace(",", "."), "DBIT" if sign.endswith("D") else "CRDT"),
					"currency": currency,
				}
			)
		elif tag == "86" and entries:
			entries[-1].update(_purpose(value))
	return {
		"format": "MT940",
		"account_iban": _compact(account) if account and account[:2].isalpha() else None,
		"account": account,
		"currency": currency,
		"opening": opening,
		"closing": closing,
		"entries": entries,
	}


def described(statement: dict) -> str:
	said = [
		f"Bank statement {statement.get('account_iban') or statement.get('account') or ''}".strip(),
		f"Opening {statement.get('opening')}, closing {statement.get('closing')} {statement.get('currency') or ''}",
	]
	for entry in statement.get("entries") or []:
		said.append(
			f"{entry.get('date')} {entry.get('amount')} {entry.get('party') or ''} "
			f"{entry.get('party_iban') or ''} {entry.get('text') or ''}".strip()
		)
	return "\n".join(said)


def _fields(text: str) -> list[tuple[str, str]]:
	"""Each `:tag:` with its value, continuation lines joined."""
	out = []
	for line in text.replace("\r", "").split("\n"):
		found = re.match(r"^:(\d{2}[A-Z]?):(.*)$", line)
		if found:
			out.append([found.group(1), found.group(2)])
		elif out and line.strip() and line.strip() != "-":
			out[-1][1] += "\n" + line
	return [tuple(one) for one in out]


def _balance(value: str) -> tuple[float | None, str | None]:
	found = re.match(r"^([CD])(\d{6})([A-Z]{3})([\d,]+)", value.strip())
	if not found:
		return None, None
	sign, _day, currency, amount = found.groups()
	return _signed(amount.replace(",", "."), "DBIT" if sign == "D" else "CRDT"), currency


def _purpose(value: str) -> dict:
	joined = value.replace("\n", "")
	if "?" not in joined:
		return {"text": " ".join(joined.split())}
	parts = SUBFIELD.split(joined)[1:]
	sub = {}
	for code, said in zip(parts[::2], parts[1::2]):
		sub.setdefault(code, []).append(said)
	purpose = "".join("".join(sub.get(str(code), [])) for code in range(20, 30))
	iban = "".join(sub.get("38", [])) or next(
		(one for one in sub.get("31", []) if one[:2].isalpha()), None
	)
	return {
		"party": " ".join("".join("".join(sub.get(code, [])) for code in ("32", "33")).split()) or None,
		"party_iban": _compact(iban),
		"text": " ".join(purpose.split()) or None,
	}


def _yymmdd(value: str) -> str:
	return f"20{value[:2]}-{value[2:4]}-{value[4:6]}"


def _signed(amount: str | None, indicator: str | None) -> float | None:
	try:
		number = float(Decimal((amount or "").strip()))
	except (InvalidOperation, ValueError):
		return None
	return -number if (indicator or "").upper() == "DBIT" else number


def _compact(value: str | None) -> str | None:
	return "".join(value.split()).upper() if value else None
