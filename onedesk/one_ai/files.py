"""A file somebody dropped on the panel, and what a model may be handed of it.

The file is an ordinary attachment on the `AI Chat` row, so it has an owner, a
permission and a place in the workspace rather than living inside a conversation
nobody can find again. What travels to the model is its bytes, base64'd, because
the account cannot read a workspace's disk — the same reason a tool runs here
and not there.

**Only the newest turn's files carry their bytes.** The conversation is sent
whole every round, so a 3 MB attachment on a five-round run is fifteen megabytes
of HTTP for one question. Older files stay in the transcript by name, which is
what a person reads them as anyway.
"""

import base64
import mimetypes

import frappe

#: Per file. Gemini takes about 20 MB in a request and the conversation goes
#: with it, so this is well under what the provider would refuse — the limit
#: that matters is what a round costs, not what the API allows.
MOST_BYTES = 4 * 1024 * 1024

#: Per turn. Three is a covering letter and two invoices; ten is a folder, and a
#: folder is a thing to ask about one at a time.
MOST_FILES = 3

@frappe.whitelist()
def attached(chat: str) -> list[dict]:
	"""What is on this conversation, for the panel to show."""
	frappe.get_doc("AI Chat", chat).check_permission("read")
	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": "AI Chat", "attached_to_name": chat},
		fields=["name", "file_name", "file_url", "file_size"],
		order_by="creation",
	)


def described(urls: list[str]) -> list[dict]:
	"""What a turn records about its files: enough to show, not the bytes."""
	said = []
	for url in (urls or [])[:MOST_FILES]:
		held = _held(url)
		said.append(
			{
				"file": held.name,
				"name": held.file_name,
				"url": held.file_url,
				"type": kind(held.file_name),
				"size": held.file_size or 0,
			}
		)
	return said


def carried(turns: list[dict]) -> list[dict]:
	"""The conversation, with bytes on the newest turn that has any.

	Read here, as the person asking, so a file they may not open is a file the
	model is never handed.
	"""
	at = next(
		(i for i in range(len(turns) - 1, -1, -1) if (turns[i] or {}).get("files")),
		None,
	)
	if at is None:
		return turns

	said = [dict(one) for one in turns]
	said[at]["files"] = [{**one, "data": _bytes(one["url"])} for one in said[at]["files"]]
	return said


def kind(name: str) -> str:
	return mimetypes.guess_type(name or "")[0] or "application/octet-stream"


def _held(url: str):
	held = frappe.get_doc("File", {"file_url": url})
	held.check_permission("read")
	if (held.file_size or 0) > MOST_BYTES:
		frappe.throw(
			frappe._("{0} is larger than {1} MB, which is as much as one question may carry.").format(
				held.file_name, MOST_BYTES // (1024 * 1024)
			)
		)
	return held


def _bytes(url: str) -> str:
	held = _held(url)
	content = held.get_content()
	if isinstance(content, str):
		content = content.encode("utf-8")
	return base64.b64encode(content).decode("ascii")


def uploaded(named: str | None, person: str | None = None) -> str | None:
	"""The file on this turn a record is made from: a CV, a business card.

	The model names the file as it pictures it — "Layla Nasser CV.pdf" for
	layla-nasser-cv.pdf — so it is matched as a person would: the name given,
	then the file whose name holds the person's, then the closest name,
	and the only file when there is one.
	"""
	import difflib

	dropped = frappe.flags.get("one_ai_files") or []
	if len(dropped) == 1:
		return dropped[0]

	def plain(text: str) -> str:
		return "".join(ch for ch in (text or "").lower() if ch.isalnum())

	stems = {url: plain(url.rsplit("/", 1)[-1].rsplit(".", 1)[0]) for url in dropped}
	for said in (named, person):
		want = plain((said or "").rsplit(".", 1)[0])
		if not want:
			continue
		held = [url for url, stem in stems.items() if want in stem or stem in want]
		if len(held) == 1:
			return held[0]
	words = [plain(one) for one in (person or "").split() if len(one) > 1]
	held = [url for url, stem in stems.items() if words and all(word in stem for word in words)]
	if len(held) == 1:
		return held[0]
	near = difflib.get_close_matches(plain(named or person or ""), list(stems.values()), n=1, cutoff=0.5)
	return next((url for url, stem in stems.items() if near and stem == near[0]), None)
