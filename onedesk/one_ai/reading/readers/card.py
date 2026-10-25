"""vCards and iCalendar files: a person, and an appointment.

Both are lines of `NAME;PARAM=x:value`, folded at 75 characters. Read here
rather than with vobject so the reading can be checked without a site. Pure.
"""

import re


def lines(text: str) -> list[tuple[str, dict, str]]:
	"""Each content line as (name, parameters, value), folds undone."""
	unfolded = re.sub(r"\r?\n[ \t]", "", text or "")
	out = []
	for line in unfolded.splitlines():
		head, colon, value = line.partition(":")
		if not colon:
			continue
		name, *params = head.split(";")
		parameters = {}
		for param in params:
			key, _eq, said = param.partition("=")
			parameters[key.upper()] = said.strip('"')
		out.append((name.split(".")[-1].upper(), parameters, _unescaped(value)))
	return out


def vcards(text: str) -> list[dict]:
	cards, current = [], None
	for name, params, value in lines(text):
		if name == "BEGIN" and value.upper() == "VCARD":
			current = {"emails": [], "phones": [], "addresses": [], "websites": []}
		elif name == "END" and current is not None:
			cards.append({key: said for key, said in current.items() if said})
			current = None
		elif current is None:
			continue
		elif name == "FN":
			current["name"] = value
		elif name == "N" and not current.get("name"):
			family, given, *_rest = (value.split(";") + ["", ""])[:3]
			current["name"] = " ".join(part for part in (given, family) if part)
		elif name == "ORG":
			current["organisation"] = value.replace(";", ", ").strip(", ")
		elif name == "TITLE":
			current["position"] = value
		elif name == "EMAIL":
			current["emails"].append(value.lower())
		elif name == "TEL":
			current["phones"].append(value)
		elif name == "URL":
			current["websites"].append(value)
		elif name == "ADR":
			_box, _extended, street, city, region, postcode, country = (value.split(";") + [""] * 7)[:7]
			current["addresses"].append(
				{key: said for key, said in (("street", street), ("city", city), ("region", region), ("postcode", postcode), ("country", country)) if said}
			)
		elif name == "NOTE":
			current["note"] = value
	return cards


def events(text: str) -> list[dict]:
	found, current = [], None
	for name, params, value in lines(text):
		if name == "BEGIN" and value.upper() == "VEVENT":
			current = {}
		elif name == "END" and value.upper() == "VEVENT" and current is not None:
			found.append(current)
			current = None
		elif current is None:
			continue
		elif name in ("SUMMARY", "LOCATION", "DESCRIPTION", "UID", "STATUS"):
			current[name.lower()] = value
		elif name in ("DTSTART", "DTEND"):
			current["starts" if name == "DTSTART" else "ends"] = _when(value)
			if params.get("TZID"):
				current["time_zone"] = params["TZID"]
		elif name == "ORGANIZER":
			current["organiser"] = value.lower().replace("mailto:", "")
		elif name == "ATTENDEE":
			current.setdefault("attendees", []).append(value.lower().replace("mailto:", ""))
	return found


def described(cards: list[dict], found_events: list[dict]) -> str:
	said = []
	for card in cards:
		said.append(
			" · ".join(
				str(bit)
				for bit in (
					card.get("name"),
					card.get("position"),
					card.get("organisation"),
					*card.get("emails", []),
					*card.get("phones", []),
					*card.get("websites", []),
				)
				if bit
			)
		)
	for event in found_events:
		said.append(
			f"{event.get('summary') or ''} {event.get('starts') or ''} – {event.get('ends') or ''} "
			f"{event.get('location') or ''}".strip()
		)
	return "\n".join(said)


def _when(value: str) -> str | None:
	"""`20261012T093000Z`, `20261012T093000` or `20261012` as ISO."""
	found = re.match(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?(Z)?)?$", value.strip())
	if not found:
		return None
	year, month, day, hour, minute, second, utc = found.groups()
	if hour is None:
		return f"{year}-{month}-{day}"
	return f"{year}-{month}-{day} {hour}:{minute}:{second or '00'}{'Z' if utc else ''}"


def _unescaped(value: str) -> str:
	return value.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\").strip()
