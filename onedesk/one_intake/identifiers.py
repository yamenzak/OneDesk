"""Identifiers written one way, so the same one is recognised however it was typed.

"DE 123 456 789", "de123456789" and "DE123456789" are one VAT id; an IBAN with
spaces and without is one account; "0221 123456" in Cologne is +49221123456.
Each kind has one canonical form, and a value that is not a valid one of its
kind (an IBAN whose check digits fail) is not an identifier at all. Pure;
phonenumbers is used where it is installed.
"""

import re

EMAIL, DOMAIN, PHONE, VAT, TAX, IBAN, REGISTER, DOCUMENT = (
	"Email", "Domain", "Phone", "VAT ID", "Tax Number", "IBAN", "Register Number", "Document Number",
)  # fmt: skip
KINDS = (EMAIL, DOMAIN, PHONE, VAT, TAX, IBAN, REGISTER, DOCUMENT)

#: Read as its domain: a website is stored as the Domain it names.
WEBSITE = "Website"

#: Held by one company only, and never shared: one of these matching is a match.
STRONG = frozenset((VAT, TAX, IBAN, REGISTER, DOCUMENT))

#: Domains that are somebody's mail provider rather than their organisation.
PROVIDERS = frozenset(
	(
		"gmail.com", "googlemail.com", "outlook.com", "outlook.de", "hotmail.com", "hotmail.de", "live.com",
		"live.de", "msn.com", "yahoo.com", "yahoo.de", "ymail.com", "icloud.com", "me.com", "mac.com", "aol.com",
		"gmx.net", "gmx.de", "gmx.com", "gmx.at", "gmx.ch", "web.de", "t-online.de", "freenet.de", "posteo.de",
		"mailbox.org", "proton.me", "protonmail.com", "pm.me", "mail.ru", "yandex.com", "yandex.ru", "zoho.com",
		"fastmail.com", "hey.com", "tutanota.com", "tuta.io", "qq.com", "163.com",
	)
)  # fmt: skip

#: Country calling codes, for a national number when phonenumbers is absent.
CALLING = {"DE": "49", "AT": "43", "CH": "41", "NL": "31", "BE": "32", "FR": "33", "IT": "39", "ES": "34",
	"GB": "44", "IE": "353", "US": "1", "CA": "1", "AE": "971", "SA": "966", "QA": "974", "KW": "965",
	"BH": "973", "OM": "968", "EG": "20", "JO": "962", "LB": "961", "SY": "963", "IQ": "964", "TR": "90",
	"PL": "48", "DK": "45", "SE": "46", "NO": "47"}  # fmt: skip

#: How long each country's IBAN is, for the countries a workspace here meets.
IBAN_LENGTH = {"DE": 22, "AT": 20, "CH": 21, "NL": 18, "BE": 16, "FR": 27, "IT": 27, "ES": 24, "GB": 22,
	"IE": 22, "LU": 20, "PL": 28, "DK": 18, "SE": 24, "NO": 15, "FI": 18, "PT": 25, "GR": 27, "AE": 23,
	"SA": 24, "QA": 29, "KW": 30, "BH": 22, "JO": 30, "LB": 28, "EG": 29, "TR": 26, "CZ": 24, "HU": 28,
	"LI": 21, "MC": 27, "SI": 19, "SK": 24, "HR": 21, "RO": 24, "BG": 22, "EE": 20, "LV": 21, "LT": 20}  # fmt: skip

EMAIL_SHAPE = re.compile(r"^[a-z0-9._%+'-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$")
VAT_SHAPE = re.compile(r"^(?:[A-Z]{2}|EL)[0-9A-Z]{8,12}$")


def email(raw: str | None) -> str | None:
	said = (raw or "").strip().strip("<>").lower()
	said = said[7:] if said.startswith("mailto:") else said
	return said if EMAIL_SHAPE.match(said) else None


def domain(raw: str | None) -> str | None:
	"""The domain of an address or a website, without `www.`."""
	said = (raw or "").strip().lower()
	if not said:
		return None
	if "@" in said and "/" not in said:
		host = said.rsplit("@", 1)[1]
	else:
		host = re.sub(r"^[a-z]+://", "", said).split("/")[0].split(":")[0]
	host = host.strip(".")
	host = host[4:] if host.startswith("www.") else host
	return host if re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", host) else None


def organisation_domain(raw: str | None) -> str | None:
	"""A domain that says which organisation, which a mail provider's does not."""
	found = domain(raw)
	return found if found and found not in PROVIDERS else None


def phone(raw: str | None, country: str | None = "DE") -> str | None:
	"""E.164: +49221123456."""
	said = (raw or "").strip()
	if not re.search(r"\d", said):
		return None
	try:
		import phonenumbers

		parsed = phonenumbers.parse(said, (country or "DE").upper())
		if phonenumbers.is_possible_number(parsed):
			return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
		return None
	except ImportError:
		pass
	except Exception:
		return None
	digits = re.sub(r"\D", "", said)
	if said.startswith("+"):
		number = digits
	elif digits.startswith("00"):
		number = digits[2:]
	elif digits.startswith("0") and (country or "").upper() in CALLING:
		number = CALLING[country.upper()] + digits[1:]
	else:
		return None
	return f"+{number}" if 8 <= len(number) <= 15 else None


def iban(raw: str | None) -> str | None:
	"""A valid IBAN, compact and upper case, or None: the check digits are
	checked, so a mistyped one is not somebody else's account."""
	said = re.sub(r"[\s-]", "", raw or "").upper()
	if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$", said):
		return None
	expected = IBAN_LENGTH.get(said[:2])
	if expected and len(said) != expected:
		return None
	moved = said[4:] + said[:4]
	number = "".join(str(int(ch, 36)) for ch in moved)
	return said if int(number) % 97 == 1 else None


def vat(raw: str | None) -> str | None:
	said = re.sub(r"[\s.\-/]", "", raw or "").upper()
	return said if VAT_SHAPE.match(said) and any(ch.isdigit() for ch in said[2:]) else None


def tax_number(raw: str | None) -> str | None:
	"""A national tax number (Steuernummer, TRN) as its digits."""
	digits = re.sub(r"\D", "", raw or "")
	return digits if 9 <= len(digits) <= 15 else None


def register(raw: str | None) -> str | None:
	"""A commercial register number: HRB 12345 is HRB12345."""
	said = re.sub(r"[\s.]", "", raw or "").upper()
	return said if re.match(r"^(HRA|HRB|GNR|PR|VR|FN|CHE)[0-9A-Z]{3,12}$", said) else None


def document(raw: str | None) -> str | None:
	"""A passport, ID or permit number, as letters and digits."""
	said = re.sub(r"[^0-9A-Za-z]", "", raw or "").upper()
	return said if 5 <= len(said) <= 20 and any(ch.isdigit() for ch in said) else None


def website(raw: str | None) -> str | None:
	return domain(raw) if raw and ("." in raw) and "@" not in raw else None


def tax_kind(raw: str | None) -> str | None:
	"""Whether ERPNext's one `tax_id` field holds a VAT id or a tax number."""
	if vat(raw):
		return VAT
	if tax_number(raw):
		return TAX
	return None


CANONICAL = {
	EMAIL: email,
	DOMAIN: organisation_domain,
	PHONE: phone,
	VAT: vat,
	TAX: tax_number,
	IBAN: iban,
	REGISTER: register,
	DOCUMENT: document,
}


def canonical(kind: str, raw, country: str | None = "DE") -> str | None:
	if kind == PHONE:
		return phone(raw, country)
	if kind == "Tax ID":
		kind = tax_kind(raw)
	return CANONICAL[kind](raw) if kind in CANONICAL else None


def found(pairs, country: str | None = "DE") -> list[tuple[str, str]]:
	"""(kind, raw) pairs as distinct canonical (kind, value) pairs, the
	unreadable dropped. An email also says its organisation's domain, and a
	website its domain."""
	out = []
	for kind, raw in pairs:
		if kind == "Tax ID":
			kind = tax_kind(raw)
		elif kind == WEBSITE:
			kind, raw = DOMAIN, website(raw)
		if not kind:
			continue
		value = canonical(kind, raw, country)
		if not value:
			continue
		out.append((kind, value))
		if kind == EMAIL:
			company = organisation_domain(value)
			if company:
				out.append((DOMAIN, company))
	return list(dict.fromkeys(out))
