"""PDFs: the words on each page, the e-invoice inside, and pieces a model can see.

A PDF with a text layer is read here for nothing. One without (a scan) is
handed to a vision model in pieces small enough to send. pypdf is imported
when a PDF needs it, so the decisions around it stay checkable without it.
"""

import io

#: A page with fewer characters than this has no text layer worth the name:
#: a scan with a stamp, a page number or a barcode read as letters.
WORDY = 25

#: Fewer than this is a blank page, which says nothing either way.
BLANK = 6

#: What ZUGFeRD, Factur-X and XRechnung call the invoice they embed.
EMBEDDED = ("factur-x.xml", "zugferd-invoice.xml", "xrechnung.xml", "zugferd.xml")


class Locked(Exception):
	"""A PDF that needs a password we do not have."""


def _reader(content: bytes, password: str | None = None):
	from pypdf import PdfReader

	reader = PdfReader(io.BytesIO(content), strict=False)
	if reader.is_encrypted and not reader.decrypt(password or ""):
		raise Locked
	return reader


def pages(content: bytes, password: str | None = None, most: int | None = None) -> list[str]:
	"""The text of each page, empty where a page has none."""
	reader = _reader(content, password)
	out = []
	for page in reader.pages[:most] if most else reader.pages:
		try:
			out.append(page.extract_text() or "")
		except Exception:
			out.append("")
	return out


def count(content: bytes, password: str | None = None) -> int:
	return len(_reader(content, password).pages)


def embedded(content: bytes, password: str | None = None) -> bytes | None:
	"""The e-invoice XML a hybrid PDF carries, if it carries one."""
	try:
		attachments = _reader(content, password).attachments
	except Locked:
		raise
	except Exception:
		return None
	for name, held in attachments.items():
		if name.lower() in EMBEDDED or name.lower().endswith(".xml"):
			return held[0] if held else None
	return None


def has_text(texts: list[str]) -> bool:
	"""Whether a PDF's text layer is its content, or a scan's leftovers. Blank
	pages (separators, empty backs) are left out of the count. Pure."""
	sizes = [len("".join(text.split())) for text in texts]
	written = [size for size in sizes if size >= BLANK]
	if not written:
		return False
	return sum(1 for size in written if size >= WORDY) >= max(1, round(len(written) * 0.6))


def pieces(content: bytes, per_piece: int, password: str | None = None) -> list[tuple[int, bytes]]:
	"""The PDF in pieces of `per_piece` pages, each as (first page, bytes)."""
	from pypdf import PdfWriter

	reader = _reader(content, password)
	out = []
	for first in range(0, len(reader.pages), per_piece):
		writer = PdfWriter()
		for page in reader.pages[first : first + per_piece]:
			writer.add_page(page)
		buffer = io.BytesIO()
		writer.write(buffer)
		out.append((first, buffer.getvalue()))
	return out


def cut(content: bytes, pages: list[int], password: str | None = None) -> bytes:
	"""Only these pages of a PDF, as a PDF of their own."""
	from pypdf import PdfWriter

	reader = _reader(content, password)
	writer = PdfWriter()
	for index in pages:
		if 0 <= index < len(reader.pages):
			writer.add_page(reader.pages[index])
	buffer = io.BytesIO()
	writer.write(buffer)
	return buffer.getvalue()
