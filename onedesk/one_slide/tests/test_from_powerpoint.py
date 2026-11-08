"""A PowerPoint file read as the editor's slides (one_slide/from_powerpoint.py)."""

import io

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.util import Inches, Pt

from onedesk.one_slide import from_powerpoint as fp


def _deck() -> bytes:
	deck = Presentation()
	title = deck.slides.add_slide(deck.slide_layouts[0])
	title.shapes.title.text = "Quarterly review"
	slide = deck.slides.add_slide(deck.slide_layouts[6])
	run = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text_frame.paragraphs[0].add_run()
	run.text, run.font.bold, run.font.size, run.font.color.rgb = "Bold red", True, Pt(30), RGBColor(255, 0, 0)
	box = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(5), Inches(1), Inches(2), Inches(2))
	box.fill.solid()
	box.fill.fore_color.theme_color = MSO_THEME_COLOR.ACCENT_1
	box.text_frame.text = "In a circle"
	picture = io.BytesIO()
	Image.new("RGB", (60, 40), "green").save(picture, "PNG")
	picture.seek(0)
	slide.shapes.add_picture(picture, Inches(1), Inches(4), Inches(2))
	slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0), Inches(0), Inches(1), Inches(1))
	data = CategoryChartData()
	data.categories = ["a"]
	data.add_series("s", (1,))
	slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(6), Inches(5), Inches(2), Inches(1), data)
	slide.notes_slide.notes_text_frame.text = "Say hello"
	out = io.BytesIO()
	deck.save(out)
	return out.getvalue()


def test_a_deck_is_read_as_its_slides():
	kept = []
	width, height, slides, lost = fp.read(_deck(), lambda name, blob: kept.append(name) or "/files/kept.png")
	assert (width, height) == (960, 720)
	assert len(slides) == 2 and lost == [2], "the chart has nothing like it"
	assert "Quarterly review" in slides[0]["elements"][0]["content"]
	drawn = {one["type"] + one.get("shapeType", ""): one for one in slides[1]["elements"]}
	assert '<strong>Bold red</strong>' in drawn["text"]["content"] and "font-size: 40px; color: #FF0000" in drawn["text"]["content"]
	assert drawn["shapeoval"]["fillColor"] == "#4F81BDFF", "a theme colour is the theme's"
	assert "color: #FFFFFF" in drawn["shapeoval"]["content"] and "text-align: center" in drawn["shapeoval"]["content"]
	assert drawn["image"]["src"] == "/files/kept.png" and kept == ["Picture 3.png"]
	assert drawn["shapeline"]["rotation"] == 45 and round(drawn["shapeline"]["width"]) == 136
	assert slides[1]["notes"] == "Say hello"
	assert [one["zIndex"] for one in slides[1]["elements"]] == [1, 2, 3, 4]


def test_a_list_paragraph_is_a_list_item():
	deck = Presentation()
	frame = deck.slides.add_slide(deck.slide_layouts[6]).shapes.add_textbox(0, 0, Inches(2), Inches(1)).text_frame
	frame.text = "a point"
	frame.paragraphs[0]._p.get_or_add_pPr().append(frame.paragraphs[0]._p.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar", {"char": "•"}))
	assert fp.words(frame, 18, {}) == '<ul><li><p><span style="font-size: 24px">a point</span></p></li></ul>'
