"""What OneAI can read of the agreements: their text, so a question about what
was agreed is answered from what the documents say rather than from what such
documents usually say."""

from typing import Annotated

from onedesk.one_legal import assemble
from onedesk.one_legal.documents import DOCUMENTS


def agreement(
	document: Annotated[
		str, "Which agreement: terms, aup, privacy, cookies, dpa, subprocessors, ai or licences."
	],
) -> dict:
	"""The current text of one of the agreements One runs under: the Terms of
	Service (terms), the Acceptable Use Policy (aup), the Privacy Policy
	(privacy), the Cookie Policy (cookies), the Data Processing Addendum (dpa),
	the Subprocessors list (subprocessors), the AI Addendum (ai), or the open
	source notices (licences). Use it for any question about what One does with
	data, who else receives it, what the organisation or the person agreed to,
	or what the rules are. Answer from what it returns alone, quote the part
	that answers, and say which document it is from."""
	key = (document or "").strip().lower()
	if key not in DOCUMENTS:
		return {"error": f"There is no such agreement. The agreements are: {', '.join(DOCUMENTS)}."}
	return {
		"title": DOCUMENTS[key]["title"],
		"version": assemble.version_of(key),
		"text": assemble.text_of(key),
		"read_it_at": f"/app/legal?document={key}",
		"next": "Answer from this text alone, in the person's language, and name the document. "
		"It is our own drafting, not legal advice: say so if they ask for advice.",
	}
