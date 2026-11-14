"""Whether a sender's domain imitates one the workspace knows: its own, a
mailbox's, or a customer's, supplier's or employee's. A domain imitates
another when it reads the same once letters that look alike are taken as
one (homoglyphs, punycode, `rn` for `m`, a hyphen), when one letter is
added, dropped, changed or two swapped, when only the ending differs, or
when it starts with the other and goes on (`gulfglass.ae.pay-now.com`).
Pure, but for `known`."""

import frappe

from onedesk.one_ai.reading.identifiers import PROVIDERS

SHORTEST = 4
CLOSE_FROM = 5
KEPT_FOR = 600
CACHE = "one_mail_known_domains"

SECOND_LEVEL = frozenset(("co", "com", "net", "org", "gov", "ac", "edu", "ltd", "plc"))

LOOKS_LIKE = {
	"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ԁ": "d",
	"һ": "h", "ӏ": "l", "ѕ": "s", "ԛ": "q", "ԝ": "w", "ɡ": "g", "ո": "n", "ս": "u", "ο": "o", "α": "a",
	"ν": "v", "ι": "i", "κ": "k", "ρ": "p", "τ": "t", "ε": "e", "υ": "u", "χ": "x", "ı": "i", "ł": "l",
	"0": "o", "1": "l", "3": "e", "5": "s", "à": "a", "á": "a", "â": "a", "ä": "a", "å": "a", "è": "e",
	"é": "e", "ê": "e", "ë": "e", "ì": "i", "í": "i", "î": "i", "ï": "i", "ò": "o", "ó": "o", "ô": "o",
	"ö": "o", "ù": "u", "ú": "u", "û": "u", "ü": "u", "ç": "c", "ñ": "n", "ý": "y",
}  # fmt: skip

PAIRS = (("rn", "m"), ("vv", "w"), ("cl", "d"), ("i", "l"))


def unicode_of(domain: str) -> str:
	"""A domain with its punycode labels (`xn--`) read as the letters they
	stand for. Pure."""
	out = []
	for label in (domain or "").lower().strip(".").split("."):
		if label.startswith("xn--"):
			try:
				label = label.encode("ascii").decode("idna")
			except (UnicodeError, ValueError):
				pass
		out.append(label)
	return ".".join(out)


def split(domain: str) -> tuple[str, str]:
	"""A domain as its name and its ending: `gulfglass.co.uk` as
	(`gulfglass`, `co.uk`), `mail.gulfglass.ae` as (`gulfglass`, `ae`).
	Pure."""
	labels = (domain or "").lower().strip(".").split(".")
	if len(labels) < 2:
		return labels[0] if labels else "", ""
	ending = 2 if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in SECOND_LEVEL else 1
	return labels[-ending - 1], ".".join(labels[-ending:])


def skeleton(name: str) -> str:
	"""A name with every letter that looks like another taken as that one,
	and hyphens dropped. Pure."""
	text = "".join(LOOKS_LIKE.get(one, one) for one in unicode_of(name).replace("-", ""))
	for pair, one in PAIRS:
		text = text.replace(pair, one)
	return text


def distance(a: str, b: str) -> int:
	"""Edits from one to the other, a swap of two letters side by side
	counting as one (optimal string alignment). Pure."""
	if a == b:
		return 0
	if abs(len(a) - len(b)) > 1:
		return 2
	before, row = None, list(range(len(b) + 1))
	for i, x in enumerate(a, 1):
		now = [i] + [0] * len(b)
		for j, y in enumerate(b, 1):
			now[j] = min(row[j] + 1, now[j - 1] + 1, row[j - 1] + (x != y))
			if before and i > 1 and j > 1 and x == b[j - 2] and a[i - 2] == y:
				now[j] = min(now[j], before[j - 2] + 1)
		before, row = row, now
	return row[-1]


def imitates(domain: str, known) -> str | None:
	"""The known domain a sender's domain imitates, or None when it is one
	of them, under one, or like none. Pure."""
	domain = (domain or "").lower().strip(".")
	if not domain or "." not in domain:
		return None
	known = sorted({one.lower().strip(".") for one in known if one and "." in one})
	if any(domain == one or domain.endswith("." + one) for one in known):
		return None
	name, _ending = split(domain)
	shape = skeleton(name)
	for one in known:
		if domain.startswith(one + "."):
			return one
	for one in known:
		theirs, _ = split(one)
		if len(theirs) < SHORTEST:
			continue
		if shape == skeleton(theirs):
			return one
	for one in known:
		theirs, _ = split(one)
		if len(theirs) >= CLOSE_FROM and distance(shape, skeleton(theirs)) == 1:
			return one
	return None


def foreign(domain: str) -> bool:
	"""Whether a domain is written in punycode, letters of another alphabet.
	Pure."""
	return any(label.startswith("xn--") for label in (domain or "").lower().split("."))


def known() -> set[str]:
	"""The domains the workspace knows: the company's own (its mail domain,
	its mailboxes' and every Email Domain), each company's website and
	address, and the addresses and websites of its customers, suppliers and
	employees. Mail providers such as gmail.com are nobody's. Kept for ten
	minutes."""
	said = frappe.cache.get_value(CACHE)
	if said is not None:
		return set(said)
	from onedesk.one_mail import addresses
	from onedesk.one_mail.faces import domain_of

	found = set(addresses.company_domains())
	found |= {addresses.domain_of(one) for one in frappe.get_all("Email Account", pluck="email_id") if one}
	for doctype, fields in (
		("Company", ("email", "website")),
		("Customer", ("email_id", "website")),
		("Supplier", ("email_id", "website")),
		("Employee", ("company_email", "prefered_email")),
	):
		present = [one for one in fields if frappe.get_meta(doctype).has_field(one)]
		for row in frappe.get_all(doctype, fields=present) if present else []:
			found |= {domain_of(value) for value in row.values() if value}
	parties = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "link_doctype": ("in", ("Customer", "Supplier", "Employee"))},
		pluck="parent",
	)
	if parties:
		found |= {
			addresses.domain_of(one)
			for one in frappe.get_all("Contact Email", filters={"parent": ("in", list(set(parties)))}, pluck="email_id")
			if one
		}
	found = {one for one in found if one and one not in PROVIDERS}
	frappe.cache.set_value(CACHE, sorted(found), expires_in_sec=KEPT_FOR)
	return found
