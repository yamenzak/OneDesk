"""OneSlide's part of the integration suite (one_demo/check.py runs it): a
presentation made, saved, versioned, kept as a template, printed and copied in
OneCloud, with a stale save and a pasted script refused; and OneAI's slides,
pictures and video, asked with the gateway mocked so nothing is billed."""

import json

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import DOT_PNG, check
from onedesk.one_demo.people import OWNER


@check
def oneslide_keeps_a_presentation_in_onecloud():
	"""Karim makes, saves, renames, re-themes, versions and prints a
	presentation, and keeps it as a template once he is a Manager; a stale
	save is refused, a pasted script is gone, a pasted slide brings its
	picture, a copy is its own, one is filed on a quotation, and somebody who
	may not open it learns nothing (one_slide/AGENTS.md)."""
	import base64
	import io
	import struct

	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one_demo.slide import NAME as DEMO
	from onedesk.one_slide import api, paper, play, templates, versions

	dot = "data:image/png;base64," + base64.b64encode(DOT_PNG).decode()
	was = getattr(frappe.local, "request", None)
	frappe.db.savepoint("slide_check")
	try:
		with as_user("karim@one.test"):
			assert any(one["name"] for one in api.get_templates()), "the themes"
			assert api.listed() == [] or all(one["title"] for one in api.listed())
			made = api.make("@my", "Quarterly review check")
			name = made["presentation"]
			assert api.presentation_of(made["url"]) == name
			deck = api.get(name)
			assert deck["can_write"] and len(deck["slides"]) == 1 and deck["theme"] == api.LIGHT, deck
			assert api.get_editor_access(name) == "edit"
			row = {key: deck["slides"][0][key] for key in api.SLIDE_FIELDS if key in deck["slides"][0]}
			bad = [
				{"id": "x1", "type": "text", "content": "<p>Hello<script>alert(1)</script></p>"},
				{"id": "x2", "type": "shape", "shapeType": "star", "css": "color: red; background: url(x); position: fixed",
				 "blur": 500, "fade": {"to": "#00ff00ff", "angle": 450}, "name": "<b>Badge</b>", "hidden": 1},
				{"id": "x3", "type": "shape", "shapeType": "blockArrow", "fade": {"to": "javascript:x"}, "css": "a{"},
			]
			fade = "linear-gradient(90deg, #ffffffff, #000000ff)"
			api.save_slides(name, json.dumps([{**row, "background": fade, "elements": json.dumps(bad)}]), deck["modified"])
			slide = api.get(name)["slides"][0]
			kept = json.loads(slide["elements"])
			assert "script" not in kept[0]["content"] and "Hello" in kept[0]["content"], kept
			assert kept[1]["css"] == "color: red" and kept[1]["blur"] == 100 and kept[1]["fade"]["angle"] == 90, kept
			assert kept[1]["name"] == "Badge" and kept[1]["hidden"] is True, kept
			assert not {"fade", "css", "blur", "name", "hidden"} & set(kept[2]), kept
			assert slide["background"] == fade, slide["background"]
			assert play.background("url(x)") == "" and play.background("linear-gradient(9deg, red, url(x))") == ""
			# a presentation of its own size: made A4, then 4:3, then back by its version
			from onedesk.one_slide import resize

			a4 = api.make("@my", "A4 check", width=794, height=1123)["presentation"]
			assert api.frame(a4) == (794, 1123) and resize.size(10, 99999) == (200, 4000)
			title = json.loads(api.get(a4)["slides"][0]["elements"])[0]
			assert round(title["left"]) == 397 and "font-size: 49.62px" in title["content"], title
			# guides: kept clean, moved with the size, and never an edit to the slides
			from onedesk.one_slide import guides

			odd = [{"axis": "x", "at": 397}, {"axis": "y", "at": 2000}, {"axis": "z", "at": 1}, {"id": "m", "axis": "y", "at": "40"}]
			kept_at = frappe.db.get_value("Presentation", a4, "modified")
			assert [(one["axis"], one["at"]) for one in guides.keep(a4, json.dumps(odd))] == [("x", 397.0), ("y", 40.0)]
			assert str(frappe.db.get_value("Presentation", a4, "modified")) == str(kept_at), "a guide is not an edit"
			assert len(guides.cleaned([{"axis": "x", "at": 1}] * 99, (960, 540))) == guides.MOST
			assert resize.resize(a4, 960, 720) == {"width": 960, "height": 720} and api.frame(a4) == (960, 720)
			moved = json.loads(frappe.db.get_value("Presentation", a4, "guides"))
			assert [one["at"] for one in moved] == [480.0, 25.6], moved
			before = [one for one in versions.listed(a4) if one["title"] == "Before changing the size"]
			assert before, versions.listed(a4)
			versions.restore(a4, before[0]["name"])
			assert api.frame(a4) == (794, 1123), "going back puts the size back"
			try:
				api.save_slides(name, json.dumps([row]), deck["modified"])
				raise AssertionError("a save built on an older version is refused")
			except frappe.TimestampMismatchError:
				frappe.clear_messages()
			assert api.update_title(name, "Quarterly review")["base_modified"]
			assert api.rename_presentation(name, "Quarterly review final")["title"] == "Quarterly review final"
			dark = next(one["name"] for one in api.get_templates() if one["title"] == "Dark")
			assert api.update_theme(name, dark)["modified"] and api.get(name)["theme"] == dark
			poster = api.save_base64_image(dot, name, "poster")
			assert poster.startswith(api.MEDIA), poster
			frappe.local.request = Request(EnvironBuilder(path="/api/method/onedesk.one_slide.api.media", method="GET").get_environ())
			assert api.media(poster[len(api.MEDIA):]).status_code == 200
			assert api.save_presentation_thumbnail(name, "data:image/webp;base64," + base64.b64encode(b"RIFF....WEBP").decode()).startswith(api.MEDIA)
			sent = EnvironBuilder(path="/api/method/onedesk.one_slide.api.upload", method="POST", data={"file": (io.BytesIO(DOT_PNG), "dot.png"), "docname": name})
			frappe.local.request = Request(sent.get_environ())
			frappe.form_dict.docname = name
			upload = api.upload()
			assert upload["file_url"] == api.MEDIA + upload["name"]
			assert api.get_webp_doc(name, json.dumps(upload))["name"] == upload["name"]
			slide = api.update_slide_attachments(name, json.dumps({"elements": json.dumps([{"id": "a", "type": "text", "content": "<p>Hi</p>"}])}))
			assert json.loads(slide["elements"])[0]["id"] != "a", "a pasted slide's elements get new ids"
			kept = versions.keep(name, "Before the review")["name"]
			assert [one["title"] for one in versions.listed(name) if one["name"] == kept] == ["Before the review"]
			api.update_title(name, "Changed after keeping")
			versions.restore(name, kept)
			assert any(one["title"] == "Before going back" for one in versions.listed(name)), "going back is kept first, so it can be undone"
			assert not api.get(name)["can_template"], "a User keeps no company templates"
			try:
				templates.save_as(name, "Not a template")
				raise AssertionError("a User kept a company template")
			except frappe.PermissionError:
				frappe.clear_messages()
			karim = frappe.get_doc("User", "karim@one.test")
			karim.flags.ignore_permissions = True
			karim.add_roles("OneSlide Manager")
			assert api.get(name)["can_template"], "a Manager keeps them"
			# fonts: a file of the company's own, read by its own name, offered and served at our address
			from onedesk.one_slide import fonts

			assert fonts.named("Cairo Bold.ttf") == ("Cairo", 700, "normal") and fonts.named("MyBrand-BoldItalic.woff2") == ("MyBrand", 700, "italic")
			said = "Brand Sans".encode("utf-16-be")
			table = struct.pack(">HHH", 0, 1, 18) + struct.pack(">HHHHHH", 3, 1, 0x409, 1, len(said), 0) + said
			sfnt = struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0) + struct.pack(">4sIII", b"name", 0, 28, len(table)) + table
			assert fonts._family_in(sfnt) == "Brand Sans"
			frappe.local.request = Request(EnvironBuilder(path="/api/method/onedesk.one_slide.fonts.upload", method="POST", data={"file": (io.BytesIO(sfnt), "brand.ttf")}).get_environ())
			offered = fonts.upload()
			assert {"family": "Brand Sans", "faces": [{"weight": 400, "style": "normal"}]} in offered["yours"], offered["yours"]
			assert any(one["group"] == "arabic" and one["family"] == "Cairo" for one in offered["shipped"])
			face = next(one for one in fonts.faces() if one["family"] == "Brand Sans")
			assert f"font-family: 'Brand Sans'; src: url('/api/method/onedesk.one_slide.fonts.face?id={face['file']}" in fonts.stylesheet()
			served = fonts.face(face["file"])
			assert served.get_data() == sfnt and "immutable" in served.headers["Cache-Control"]
			assert not offered["google"] and fonts.google_search("cairo") == [], "Google is not asked while the service is off"
			assert fonts.library()["yours"] == offered["yours"] and "Brand Sans" in fonts.css().get_data(as_text=True)
			try:
				fonts.google_add("Cairo")
				raise AssertionError("a family is added from Google while the service is off")
			except frappe.ValidationError:
				frappe.clear_messages()
			assert not frappe.has_permission(api.PRESENTATION, "read"), "keeping templates opens no presentation the File doesn't"
			# a master: made once, opened with the presentation's own access, drawn under every slide
			from onedesk.one_slide import layouts, master

			mine = master.edit(name)
			assert master.edit(name) == mine and api.get(mine)["master_of"] == name, "one master, opened as the presentation is"
			number = {"id": "n1", "type": "text", "field": "number", "content": "<p><span style=\"font-size: 14px\">#</span></p>"}
			plate = api.get(mine)
			api.save_slides(mine, json.dumps([{"client_id": plate["slides"][0]["client_id"], "elements": json.dumps([number])}]), str(plate["modified"]))
			assert [one["id"] for one in api.get(name)["master"]] == ["n1"], api.get(name)["master"]
			played = play.for_screen(name, 10)
			assert played[0]["slide"]["elements"][0]["id"] == "master-n1" and ">1<" in played[0]["slide"]["elements"][0]["content"], played[0]
			assert master._worded("<p><b>a</b> <i>b</i></p>", "7") == "<p><b>7</b><i></i></p>", master._worded("<p><b>a</b> <i>b</i></p>", "7")
			template = templates.save_as(name, "Review template")
			assert any(one["name"] == template["name"] for one in api.listed()), "a template OneCloud offers"
			assert any(one["name"] == template["name"] for one in api.get_templates()), "a template the editor takes layouts from"
			started = api.make("@my", "From the template", template["name"])["presentation"]
			assert len(api.get(started)["slides"]) == len(api.get(name)["slides"]), "a template is copied whole"
			assert [one["id"] for one in api.get(started)["master"]] == ["n1"], "a template's master comes with it"
			# linked layouts: the template's new look comes into the slide, its words stay
			first = api.get(started)["slides"][0]
			assert first["layout"] == f"{template['name']}:{frappe.db.get_value(api.SLIDE, {'parent': template['name'], 'idx': 1}, 'client_id')}", first["layout"]
			own = json.loads(first["elements"])
			said = next(one for one in own if one.get("type") == "text")
			said["content"] = "<p>Our words</p>"
			api.save_slides(started, json.dumps([{"client_id": first["client_id"], "layout": first["layout"], "elements": json.dumps(own)}]), str(api.get(started)["modified"]))
			look = frappe.get_doc(api.PRESENTATION, template["name"])
			drawn = json.loads(look.slides[0].elements)
			source = next(one for one in drawn if one["id"] == said["from"])
			source.update(left=7, content='<p style="text-align: right"><span style="font-size: 50px">Old</span></p>')
			look.slides[0].elements = json.dumps(drawn)
			look.save(ignore_permissions=True)
			assert layouts.restyle(started) == {"restyled": 1}
			now = next(one for one in json.loads(api.get(started)["slides"][0]["elements"]) if one["id"] == said["id"])
			assert now["left"] == 7 and now["content"] == '<p style="text-align: right"><span style="font-size: 50px">Our words</span></p>', now
			assert layouts.restyle(started) == {"restyled": 0}, "a slide that looks like its layout is left alone"
			from PIL import Image

			drawn = io.BytesIO()
			Image.new("RGB", (16, 9), "white").save(drawn, "PNG")
			page = "data:image/png;base64," + base64.b64encode(drawn.getvalue()).decode()
			made = paper.pdf(name, json.dumps([page, page]))
			assert made["file_name"].endswith(".pdf") and frappe.get_doc("File", made["name"]).get_content().startswith(b"%PDF"), made
			# speaker notes: kept with the slide and its versions, and printed as words under it
			deck = api.get(name)
			first = {key: deck["slides"][0][key] for key in api.SLIDE_FIELDS if key in deck["slides"][0]}
			said = "Thank the client first.\nاشكر العميل أولاً."
			api.save_slides(name, json.dumps([{**first, "notes": said}]), str(deck["modified"]))
			assert api.get(name)["slides"][0]["notes"] == said
			assert '"notes": "Thank the client first.' in json.dumps(json.loads(versions._snapshot(name)), ensure_ascii=False)
			noted = paper.pdf(name, json.dumps([page]), notes=1)
			from pypdf import PdfReader

			words = " ".join(PdfReader(io.BytesIO(frappe.get_doc("File", noted["name"]).get_content())).pages[0].extract_text().split())
			assert noted["file_name"].endswith("with notes.pdf") and "Thank the client first." in words, (noted, words)
			# the decks One ships and the slide library: built in the business's colour, kept by a manager
			from onedesk.one_slide import decks, library

			assert [one["name"] for one in api.listed()][:5] == list(decks.NAMES.values())
			pitch = api.make("@my", "Pitch check", decks.NAMES["pitch"])["presentation"]
			opened = api.get(pitch)
			assert len(opened["slides"]) == len(decks.DECKS["pitch"]) and opened["slides"][2]["background"] == decks.brand()["colour"], opened["slides"][2]
			assert opened["slides"][0]["layout"] == f"{decks.NAMES['pitch']}:{decks.NAMES['pitch']}-1"
			assert layouts.restyle(pitch) == {"restyled": 0}, "a fresh deck already looks like its layouts"
			shelves = library.shelves()
			assert [one["kind"] for one in shelves["one"]] == list(decks.KINDS) and shelves["may_keep"]
			kept = library.keep(pitch, opened["slides"][1]["client_id"], "agenda")
			assert [one["kind"] for one in kept["yours"]] == ["agenda"], kept["yours"]
			assert library.held() not in [one["name"] for one in api.get_templates()], "the shelf is no theme"
			assert library.forget(kept["yours"][0]["client_id"])["yours"] == []
			# PowerPoint: PowerPoint's own pieces, read back, and the slide that lost an effect named
			from pptx import Presentation as Deck

			from onedesk.one_slide import powerpoint

			assert powerpoint.rgb("#FF000000") is None and powerpoint.rgb("rgb(1, 2, 3)") == (1, 2, 3)
			drawn = [
				{"id": "t", "type": "text", "left": 10, "top": 10, "width": 400, "zIndex": 1, "content": '<p style="text-align: right"><span style="font-size: 40px; color: #FF0000FF"><strong>Bold</strong> words</span></p><ul><li><p>one</p></li></ul>'},
				{"id": "s", "type": "shape", "shapeType": "star", "left": 500, "top": 10, "width": 100, "height": 100, "zIndex": 2, "fillColor": "#3366FFFF", "fade": {"to": "#00FF00FF", "angle": 90}},
				{"id": "l", "type": "shape", "shapeType": "line", "left": 10, "top": 300, "width": 200, "height": 2, "strokeWidth": 2, "strokeColor": "#000000FF", "zIndex": 3},
				{"id": "p", "type": "image", "src": dot, "left": 10, "top": 400, "width": 40, "height": 40, "zIndex": 4},
				{"id": "h", "type": "text", "hidden": True, "content": "<p>Hidden</p>"},
			]
			effects = [{"id": "b", "type": "shape", "shapeType": "rectangle", "left": 0, "top": 0, "width": 50, "height": 50, "blur": 4}]
			deck = api.get(name)
			plain = {key: deck["slides"][0][key] for key in api.SLIDE_FIELDS if key in deck["slides"][0]}
			api.save_slides(name, json.dumps([{**plain, "elements": json.dumps(drawn), "notes": "Say this."}, {"client_id": "pp-2", "elements": json.dumps(effects)}]), str(deck["modified"]))
			made = powerpoint.export(name)
			assert made["file_name"].endswith(".pptx") and made["lost"] == [2], made
			opened = Deck(io.BytesIO(frappe.get_doc("File", made["name"]).get_content()))
			shapes = list(opened.slides[0].shapes)
			names = [shape.shape_type for shape in shapes]
			said = next(shape.text_frame for shape in shapes if shape.has_text_frame and "Bold" in shape.text_frame.text)
			assert len(shapes) == 4 + len(api.get(name)["master"]), names
			assert said.paragraphs[0].runs[0].text == "Bold" and said.paragraphs[0].runs[0].font.bold and said.paragraphs[1].runs[0].text.endswith("one"), said.text
			assert opened.slides[0].notes_slide.notes_text_frame.text == "Say this."
			assert opened.slide_width == api.frame(name)[0] * powerpoint.EMU
			api.visited("Presentation", name)
			api.download(name)
			assert frappe.local.response["location"] == f"/desk/presentation/{name}"
		with as_user(OWNER):
			theirs = api.save_base64_image(dot, DEMO, "poster")
			quote = frappe.get_all("Quotation", pluck="name", limit=1)[0]
			on_record = api.make(f"@records/Quotation/{quote}", "Quotation slides")["presentation"]
			assert api.get(on_record)["record"] == {"doctype": "Quotation", "name": quote}, "filed on the record"
			# data from records: chips filled as the reader may see them, on the TV and in PowerPoint too, frozen, and one for each
			from onedesk.one_slide import data, play

			assert data.chips(["<p>{this.name} {theirs.1.name}</p>", None]) == {("this", "name"), ("theirs", "1.name")}
			assert data.fill("<p>{a.b} {c.d}</p>", {"a.b": "<x>"}) == "<p>&lt;x&gt; {c.d}</p>"
			assert data.tabled("<tr><th>Head</th></tr><tr><td>{l.1.name}</td></tr><tr><td>{l.2.name}</td></tr>", {"l.1.name": "A", "l.2.name": ""}) == "<tr><th>Head</th></tr><tr><td>A</td></tr>"
			assert [one["key"] for one in data.cleaned([{"kind": "this", "key": "this"}, {"kind": "odd", "key": "x"}, {"kind": "list", "key": "this"}])] == ["this"]
			assert any(one["fieldname"] == "party_name" for one in data.fields("Quotation"))
			party = frappe.db.get_value("Quotation", quote, "party_name")
			data.save_sources(on_record, [{"kind": "this", "key": "this", "doctype": "Quotation"}, {"kind": "list", "key": "theirs", "doctype": "Quotation", "filters": [["party_name", "=", "{this.party_name}"]], "limit": 5}])
			deck = api.get(on_record)
			words = "<p>{this.name} for {this.party_name}: {theirs.count}</p>"
			plain = {key: deck["slides"][0][key] for key in api.SLIDE_FIELDS if key in deck["slides"][0]}
			api.save_slides(on_record, json.dumps([{**plain, "elements": json.dumps([{"id": "d", "type": "text", "left": 10, "top": 10, "width": 600, "content": words}])}]), str(deck["modified"]))
			count = str(min(frappe.db.count("Quotation", {"party_name": party}), 5))
			said = data.values(on_record)
			assert said["values"]["this.name"] == quote and said["values"]["theirs.count"] == count and ["Quotation", quote] in said["watch"], said
			assert api.get(on_record)["data"]["values"] == said["values"], "the first paint is filled"
			shown = next(one["content"] for one in play.for_screen(on_record, 8)[0]["slide"]["elements"] if one.get("id") == "d")
			assert quote in shown and "{" not in shown, shown
			made = powerpoint.export(on_record)
			assert quote in Deck(io.BytesIO(frappe.get_doc("File", made["name"]).get_content())).slides[0].shapes[-1].text_frame.text
			other = frappe.get_all("Quotation", filters={"name": ["!=", quote]}, pluck="name", limit=1)[0]
			assert data.for_each(on_record, [other]) == {"queued": 1}
			data.made_for_each(on_record, "Quotation slides", "Quotation", [other], OWNER)
			filed = frappe.get_all("File", filters={"attached_to_doctype": "Quotation", "attached_to_name": other, "file_name": ["like", "Quotation slides%"]}, pluck="file_url")
			copied = api.presentation_of(filed[0]) if filed else None
			assert copied and copied != on_record and data.values(copied)["values"]["this.name"] == other, "a copy reads its own record"
			assert data.freeze(on_record) == {"frozen": len(said["values"])}
			kept = json.loads(api.get(on_record)["slides"][0]["elements"])[0]["content"]
			assert quote in kept and "{this." not in kept, kept
		with as_user("karim@one.test"):
			pasted = api.get_updated_json(name, json.dumps([{"id": "p", "type": "image", "src": theirs}]))
			assert pasted[0]["src"].startswith(api.MEDIA) and pasted[0]["src"] != theirs, "the picture is copied onto this presentation"
			file = api.get(name)["file"]
			copy = frappe.get_doc({"doctype": "File", "file_url": api.URL + name, "folder": frappe.db.get_value("File", file, "folder"), "file_name": "Quarterly copy"})
			copy.flags.ignore_permissions = True
			copy.insert()
			held = api.presentation_of(copy.file_url)
			assert held and held != name and frappe.db.get_value(api.PRESENTATION, held, "file") == copy.name, "a copy is a presentation of its own"
		with as_user("omar@one.test"):
			assert api.get_editor_access(name) == "none"
			try:
				api.get(name)
				raise AssertionError("somebody who may not open it reads it")
			except frappe.PermissionError:
				frappe.clear_messages()
		frappe.delete_doc("File", file, ignore_permissions=True)
		assert not frappe.db.exists(api.PRESENTATION, name), "the presentation goes with its File"
	finally:
		frappe.local.request = was
		frappe.db.rollback(save_point="slide_check")


@check
def oneai_makes_slides_and_pictures():
	"""Karim asks OneAI for a designed slide, a picture on it and a video,
	and a picture in a document. The design comes back as the editor's own
	elements, the pictures are kept on what they were made for, the video
	arrives on a slide of its own and he is told. OneAI is pretended."""
	import base64
	from unittest import mock

	from onedesk.one_doc import api as doc_api
	from onedesk.one_slide import ai, api, convert

	designed = json.dumps({
		"background": "#102030", "background2": "#405060", "angle": 90,
		"blocks": [
			{"kind": "text", "text": "Open\nhouse", "x": 6, "y": 8, "w": 60, "h": 20, "size": 120, "upper": 1, "fill": "#ffffff22", "padding": 20},
			{"kind": "shape", "shape": "arrow", "x": 6, "y": 60, "w": 30, "h": 20, "fill": "#ff8800", "fill2": "#ffcc00", "shadow_colour": "#00000066"},
			{"kind": "qr", "link": "https://example.com/visit", "x": 80, "y": 70, "w": 14, "h": 25},
			{"kind": "image", "src": "javascript:alert(1)", "x": 0, "y": 0, "w": 10, "h": 10},
		],
	})
	png = base64.b64encode(DOT_PNG).decode()
	told = []
	frappe.db.savepoint("oneai_slide_check")
	try:
		with mock.patch("onedesk.one.apps.ai_on", return_value=True), mock.patch(
			"onedesk.one_ai.run.once", return_value=f"```json\n{designed}\n```"
		), mock.patch("onedesk.one_ai.run.make", return_value={"data": png, "mime": "image/png"}), mock.patch(
			"onedesk.one_ai.run.begin", return_value="ticket"
		), mock.patch("onedesk.one_ai.run.collect", return_value={"done": True, "data": base64.b64encode(b"video").decode(), "mime": "video/mp4"}), mock.patch(
			"onedesk.one_slide.ai.time.sleep"
		), mock.patch("onedesk.one.notify.notify", side_effect=lambda kind, to, **said: told.append((kind, to, said["what"]))):
			with as_user("karim@one.test"):
				name = api.make("@my", "OneAI check")["presentation"]
				slide = ai.design(name, "An open house on Saturday")
				kinds = [(one["type"], one.get("shapeType")) for one in slide["elements"]]
				assert kinds == [("text", None), ("shape", "blockArrow"), ("image", None), ("image", None)], kinds
				assert slide["background"] == "linear-gradient(90deg, #102030FF, #405060FF)", slide["background"]
				words = slide["elements"][0]
				assert "OPEN" in words["content"] and "HOUSE" in words["content"] and "background" in words["css"], words
				assert slide["elements"][1]["fade"]["to"] == "#FFCC00FF" and slide["elements"][1]["shadowOpacity"] == 40
				assert slide["elements"][2]["src"].startswith("data:image/svg+xml;base64,"), "a QR code is a picture of one"
				assert slide["elements"][3]["src"] == "", "an address that is not ours is dropped"
				made = ai.picture(name, "A tower at dusk")
				assert made["file_url"].startswith(api.MEDIA) and frappe.db.get_value("File", made["name"], "attached_to_name") == name
				before = len(api.get(name)["slides"])
				assert ai.video(name, "Waves on a glass facade")["begun"]
				ai.made_later(name, "Waves on a glass facade", "karim@one.test")
				slides = api.get(name)["slides"]
				video = json.loads(slides[-1]["elements"])[0]
				assert len(slides) == before + 1 and video["type"] == "video" and video["src"].startswith(api.MEDIA), video
				assert told == [("Video Made for a Presentation", ["karim@one.test"], "Waves on a glass facade")], told
				document = doc_api.make("@my", "Picture check")["document"]
				picture = doc_api.make_picture(document, "A floor plan")
				assert picture["file_url"].startswith(doc_api.PICTURE), picture
			portrait = convert.slide({"orientation": "Portrait", "blocks": [{"kind": "shape", "x": 0, "y": 0, "w": 100, "h": 100}]})
			box = portrait["elements"][0]
			assert box["width"] == 303.75 and box["left"] == 328.12, "a portrait design stands in the middle"
			tall = convert.slide({"blocks": [{"kind": "shape", "x": 0, "y": 0, "w": 100, "h": 50}]}, 540, 960)["elements"][0]
			assert (tall["width"], tall["height"]) == (540, 480), "a design fills a presentation standing up"
		from onedesk.one_slide import play

		still, held = [{"type": "text"}], [{"type": "video", "length": 12.5}, {"type": "video", "length": 30, "loop": True}]
		assert play.length(still, "", 8) == 8 and play.length(still, "5", 8) == 5, "a still slide waits its Advance, else the row's"
		assert play.length(held, "", 8) == 12.5 and play.length(held, "3", 8) == 15.5, "a video that does not loop is watched first"
		assert play.length(still, "0.5", 0) == 2, "no slide is shorter than two seconds"
		assert play._transition("Magic Move") == "fade" and play._transition("Slide In") == "slide"
		with mock.patch("onedesk.one.apps.ai_on", return_value=False):
			try:
				ai.design(name, "Anything")
				raise AssertionError("OneAI turned off still designs")
			except Exception as refused:
				assert "turned off" in str(refused), refused
				frappe.clear_messages()
	finally:
		frappe.db.rollback(save_point="oneai_slide_check")
