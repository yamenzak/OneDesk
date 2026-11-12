"""A presentation on the network drive as a .pptx (one_slide/drive.py, one_storage/dav.py)."""

import io

from pptx import Presentation
from pptx.util import Inches

from onedesk.one_slide import drive
from onedesk.one_slide import from_powerpoint as fp
from onedesk.one_slide.powerpoint import MASTER
from onedesk.one_storage import dav


def _saved() -> bytes:
	deck = Presentation()
	slide = deck.slides.add_slide(deck.slide_layouts[6])
	logo = slide.shapes.add_textbox(Inches(0), Inches(0), Inches(2), Inches(1))
	logo.text_frame.text, logo.name = "Logo", MASTER + "abc"
	slide.shapes.add_textbox(Inches(1), Inches(2), Inches(4), Inches(1)).text_frame.text = "Changed in PowerPoint"
	out = io.BytesIO()
	deck.save(out)
	return out.getvalue()


def said(slides: list[dict]) -> list[str]:
	return [one["content"] for one in slides[0]["elements"]]


def test_the_masters_shapes_are_left_to_the_master():
	_w, _h, slides, lost = fp.read(_saved(), lambda name, blob: "/files/x.png", mastered=True)
	assert len(said(slides)) == 1 and "Changed in PowerPoint" in said(slides)[0] and lost == []
	_w, _h, slides, _lost = fp.read(_saved(), lambda name, blob: "/files/x.png")
	assert len(said(slides)) == 2, "a deck with no master keeps every shape"


def test_a_presentation_is_a_powerpoint_file_on_the_drive():
	node = {"id": "f1", "name": "Quarterly review", "presentation": "p1"}
	assert dav._as_file(node)["name"] == "Quarterly review.pptx"
	assert dav._as_file({**node, "name": "Deck.PPTX"})["name"] == "Deck.PPTX"
	assert dav._as_file({"id": "f2", "name": "Plain.pptx"})["name"] == "Plain.pptx", "an office file is its own bytes"


def test_the_slides_that_lost_something_are_kept_in_order():
	assert drive.lost_words([4, 2, 4]) == "2, 4"
	assert drive.lost_words([]) == ""
