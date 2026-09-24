"""What only a model can read: a scan's pages, a photo, a recording.

A scanned PDF goes in pieces of a few pages, since a hundred-page scan in one
request is more than a model takes and more than a failure should cost. The
model writes out each page and says where a new document starts, which is
how a batch scan with no page numbers is still cut into its letters.
"""

import base64

import frappe

from onedesk.one_intake.readers import pdf

#: Pages sent in one request.
PER_PIECE = 8

PAGES = "read_pages"
SOUND = "read_sound"

MIME = {
	"pdf": "application/pdf",
	"jpg": "image/jpeg",
	"jpeg": "image/jpeg",
	"png": "image/png",
	"webp": "image/webp",
	"heic": "image/heic",
	"heif": "image/heif",
	"gif": "image/gif",
	"tif": "image/tiff",
	"tiff": "image/tiff",
	"bmp": "image/bmp",
	"mp3": "audio/mpeg",
	"m4a": "audio/mp4",
	"wav": "audio/wav",
	"ogg": "audio/ogg",
	"oga": "audio/ogg",
	"opus": "audio/ogg",
	"amr": "audio/amr",
	"aac": "audio/aac",
	"webm": "audio/webm",
	"3gp": "audio/3gpp",
}

ASK_PAGES = (
	"Write out the text of every page in the attached file, in its own language, exactly as it is written. "
	"Keep line breaks, numbers, amounts, dates, IBANs and reference numbers exactly. Do not translate, "
	"summarise or correct anything. For each page, say whether it begins a new document (a new letter, "
	"invoice, receipt or form) rather than continuing the one before. The file's first page is page {first}.\n"
	'Answer with only this JSON: {{"language": "de", "pages": [{{"page": {first}, "starts": true, "text": "..."}}]}}'
)


def see(name: str, content: bytes, ext: str, most_pages: int, reference: str) -> dict:
	"""{"pages": [...], "starts": {index, ...}, "language": ...} for a scan or a picture."""
	if ext == "pdf":
		pieces = pdf.pieces(content, PER_PIECE)
		pieces = [(first, piece) for first, piece in pieces if first < most_pages]
	else:
		pieces = [(0, content)]
	pages: list[str] = []
	starts: set[int] = set()
	language = None
	for first, piece in pieces:
		answer = _ask(PAGES, ASK_PAGES.format(first=first + 1), name, piece, MIME.get(ext, "application/pdf"), reference)
		said = _pages(answer)
		for offset, page in enumerate(said.get("pages") or []):
			index = first + offset
			while len(pages) < index:
				pages.append("")
			pages.append(str(page.get("text") or "") if isinstance(page, dict) else str(page))
			if isinstance(page, dict) and page.get("starts") and index > 0:
				starts.add(index)
		language = language or said.get("language")
	return {"pages": pages, "starts": starts, "language": language}


def hear(name: str, content: bytes, ext: str, reference: str) -> str:
	return _ask(
		SOUND,
		"Write down what is said in the attached recording, word for word, in the language spoken.",
		name,
		content,
		MIME.get(ext, "audio/mpeg"),
		reference,
	).strip()


def _ask(action: str, text: str, name: str, content: bytes, mime: str, reference: str) -> str:
	from onedesk.one_ai import run

	files = [{"name": name, "type": mime, "data": base64.b64encode(content).decode("ascii")}]
	return run.once(action, text, files=files, reference=reference) or ""


def _pages(answer: str) -> dict:
	"""The JSON asked for, or the whole answer as one page when a model
	answered in prose: the text is still the text."""
	from onedesk.one_hr.hiring import read

	said = read(answer)
	if said and isinstance(said.get("pages"), list):
		return said
	if answer and answer.strip():
		frappe.log_error(title="OneAI answered a page reading in prose", message=answer[:4000])
		return {"pages": [{"text": answer.strip()}]}
	return {"pages": []}


def credits_gone(raised: Exception) -> bool:
	return getattr(raised, "said", None) == "NotEnough" or "NotEnough" in str(raised)
