"""Mail: a message's own words, and the message somebody forwarded inside it.

A forward's sender is the colleague who pressed Forward, and the document is
what they forwarded. So a forward is unwrapped to the original: its sender,
its date, its subject and its words, whether it was forwarded inline or
attached as a message of its own. Pure.
"""

import email
import email.policy
import email.utils
import html
import re

#: The line a mail client writes above what it forwards or quotes, in the
#: languages people here write in.
MARKER = re.compile(
	r"^\s*(?:-{2,}|_{2,})\s*(?:forwarded message|weitergeleitete nachricht|original message|"
	r"ursprüngliche nachricht|message transféré|message d'origine|mensaje reenviado|mensaje original|"
	r"messaggio inoltrato|messaggio originale|doorgestuurd bericht|oorspronkelijk bericht|"
	r"iletilen ileti|الرسالة المعاد توجيهها|الرسالة الأصلية)\s*(?:-{2,}|_{2,})?\s*$"
	r"|^\s*begin forwarded message:\s*$|^\s*anfang der weitergeleiteten nachricht:\s*$",
	re.IGNORECASE | re.MULTILINE,
)

#: Outlook forwards with no marker line, only a header block.
OUTLOOK = re.compile(r"^\s*(?:from|von|de|da|van)\s*:\s*.+\n\s*(?:sent|gesendet|envoyé|enviado|inviato|verzonden|date|datum)\s*:", re.IGNORECASE | re.MULTILINE)

HEADERS = {
	"from": ("from", "von", "de", "da", "van", "من"),
	"date": ("date", "datum", "sent", "gesendet", "envoyé", "enviado", "inviato", "verzonden", "fecha", "التاريخ"),
	"subject": ("subject", "betreff", "objet", "asunto", "oggetto", "onderwerp", "konu", "الموضوع"),
	"to": ("to", "an", "à", "a", "para", "aan", "إلى"),
	"cc": ("cc",),
}


def message(content: bytes) -> dict:
	"""An .eml file as its parts: headers, words and attachments."""
	parsed = email.message_from_bytes(content, policy=email.policy.default)
	return parts(parsed)


def parts(parsed) -> dict:
	text_body = html_body = None
	attachments = []
	for part in parsed.walk():
		if part.is_multipart() and part.get_content_type() != "message/rfc822":
			continue
		kind = part.get_content_type()
		disposition = part.get_content_disposition()
		if kind == "message/rfc822":
			inner = part.get_payload(0) if part.is_multipart() else None
			if inner is not None:
				attachments.append(
					{"name": (inner.get("subject") or "message") + ".eml", "type": kind, "content": inner.as_bytes()}
				)
			continue
		if disposition == "attachment" or (disposition == "inline" and part.get_filename()):
			attachments.append(
				{
					"name": part.get_filename() or "attachment",
					"type": kind,
					"content": part.get_payload(decode=True) or b"",
					"inline_id": (part.get("Content-ID") or "").strip("<>") or None,
				}
			)
		elif kind == "text/plain" and text_body is None:
			text_body = part.get_content()
		elif kind == "text/html" and html_body is None:
			html_body = part.get_content()
	sender = email.utils.parseaddr(str(parsed.get("from") or ""))
	return {
		"subject": str(parsed.get("subject") or ""),
		"from_name": sender[0] or None,
		"from_email": sender[1].lower() or None,
		"to": str(parsed.get("to") or ""),
		"cc": str(parsed.get("cc") or ""),
		"date": str(parsed.get("date") or "") or None,
		"message_id": (str(parsed.get("message-id") or "").strip().strip("<>")) or None,
		"text": text_body if text_body and text_body.strip() else plain(html_body or ""),
		"attachments": attachments,
	}


def plain(markup: str) -> str:
	"""HTML as the words a person reads: blocks on their own lines, no styles,
	no scripts, entities decoded."""
	text = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", "", markup or "")
	text = re.sub(r"(?i)<br\s*/?>", "\n", text)
	text = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|table|blockquote)>", "\n", text)
	text = re.sub(r"(?i)</t[dh]>", "\t", text)
	text = re.sub(r"<[^>]+>", "", text)
	text = html.unescape(text).replace("\xa0", " ")
	lines = [" ".join(line.split()) for line in text.split("\n")]
	return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def unwrap(text: str, depth: int = 0) -> dict | None:
	"""The message forwarded inside this text, the innermost when forwards are
	nested, or None when nothing was forwarded. `note` is what the person who
	forwarded it wrote above it."""
	found = min(
		(one for one in (MARKER.search(text or ""), OUTLOOK.search(text or "")) if one),
		key=lambda one: one.start(),
		default=None,
	)
	if not found or depth > 8:
		return None
	start = found.end() if MARKER.match(found.group(0)) else found.start()
	headers, body = _header_block(text[start:])
	if not headers.get("from") and not headers.get("subject"):
		return None
	name, address = _address(headers.get("from") or "")
	original = {
		"note": text[: found.start()].strip(),
		"from_name": name,
		"from_email": address,
		"date": headers.get("date"),
		"subject": headers.get("subject"),
		"to": headers.get("to"),
		"text": body.strip(),
	}
	deeper = unwrap(original["text"], depth + 1)
	if deeper:
		deeper["note"] = original["note"]
		return deeper
	return original


def _header_block(text: str) -> tuple[dict, str]:
	"""The `From:`/`Subject:` lines at the top of a forwarded message, and what
	follows them."""
	lines = text.lstrip("\n").split("\n")
	headers, index = {}, 0
	for index, line in enumerate(lines):
		stripped = line.strip().lstrip(">").strip().replace("*", "")
		if not stripped:
			if headers:
				break
			continue
		key, _colon, value = stripped.partition(":")
		named = next((field for field, words in HEADERS.items() if key.strip().lower() in words), None)
		if not _colon or not named:
			if headers:
				break
			continue
		headers.setdefault(named, value.strip())
	else:
		index = len(lines)
	body = "\n".join(line[1:] if line.startswith(">") else line for line in lines[index:])
	return headers, body


def _address(said: str) -> tuple[str | None, str | None]:
	"""`Name <a@b>`, `Name [mailto:a@b]`, `"Name" a@b` or a bare address."""
	said = said.replace("[mailto:", "<").replace("]", ">")
	name, address = email.utils.parseaddr(said)
	if "@" not in address:
		found = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", said)
		address = found.group(0) if found else ""
		name = said.replace(address, "").strip(" <>\"'") if address else said.strip()
	return (name.strip("\"' ") or None), (address.lower() or None)
