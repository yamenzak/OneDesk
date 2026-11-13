"""Combine into PDF: pictures and PDFs, in the order chosen, as one PDF."""

import io

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from onedesk.one_cloud import pdf


def _picture(mode="RGB", size=(300, 200), fmt="PNG", **saved) -> bytes:
	out = io.BytesIO()
	Image.new(mode, size, (200, 100, 50, 128) if mode == "RGBA" else "blue").save(out, fmt, **saved)
	return out.getvalue()


def test_a_file_is_a_pdf_a_picture_or_neither():
	assert pdf.kind_of("Scan.PDF") == "pdf"
	assert pdf.kind_of("receipt.jpeg") == "picture"
	assert pdf.kind_of("notes.txt") is None
	assert pdf.kind_of("pdf") is None


def test_a_picture_becomes_a_page_its_own_size():
	page = PdfReader(io.BytesIO(pdf.picture_page(_picture(size=(600, 300), fmt="JPEG", dpi=(300, 300))))).pages[0]
	assert [round(float(x)) for x in page.mediabox[2:]] == [144, 72]


def test_pictures_and_pdfs_join_in_order():
	two = io.BytesIO()
	writer = PdfWriter()
	writer.add_blank_page(100, 100)
	writer.add_blank_page(100, 100)
	writer.write(two)
	joined = PdfReader(io.BytesIO(pdf.joined([("picture", _picture("RGBA"), "a.png"), ("pdf", two.getvalue(), "b.pdf")])))
	assert len(joined.pages) == 3
	assert round(float(joined.pages[1].mediabox[2])) == 100


def test_a_file_that_is_not_what_it_says_is_named():
	with pytest.raises(pdf.Unreadable) as said:
		pdf.joined([("pdf", b"not a pdf", "x.pdf")])
	assert said.value.name == "x.pdf" and not said.value.locked


def test_a_locked_pdf_is_named_as_locked():
	locked = io.BytesIO()
	writer = PdfWriter()
	writer.add_blank_page(100, 100)
	writer.encrypt("secret")
	writer.write(locked)
	with pytest.raises(pdf.Unreadable) as said:
		pdf.joined([("pdf", locked.getvalue(), "locked.pdf")])
	assert said.value.locked
