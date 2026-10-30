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
			api.media(poster[len(api.MEDIA):])
			assert frappe.local.response.status_code == 200
			frappe.local.response = frappe._dict()
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
			assert not frappe.has_permission(api.PRESENTATION, "read"), "keeping templates opens no presentation the File doesn't"
			template = templates.save_as(name, "Review template")
			assert any(one["name"] == template["name"] for one in api.listed()), "a template OneCloud offers"
			assert any(one["name"] == template["name"] for one in api.get_templates()), "a template the editor takes layouts from"
			started = api.make("@my", "From the template", template["name"])["presentation"]
			assert len(api.get(started)["slides"]) == len(api.get(name)["slides"]), "a template is copied whole"
			from PIL import Image

			drawn = io.BytesIO()
			Image.new("RGB", (16, 9), "white").save(drawn, "PNG")
			page = "data:image/png;base64," + base64.b64encode(drawn.getvalue()).decode()
			made = paper.pdf(name, json.dumps([page, page]))
			assert made["file_name"].endswith(".pdf") and frappe.get_doc("File", made["name"]).get_content().startswith(b"%PDF"), made
			api.visited("Presentation", name)
			api.download(name)
			assert frappe.local.response["location"] == f"/desk/presentation/{name}"
		with as_user(OWNER):
			theirs = api.save_base64_image(dot, DEMO, "poster")
			quote = frappe.get_all("Quotation", pluck="name", limit=1)[0]
			on_record = api.make(f"@records/Quotation/{quote}", "Quotation slides")["presentation"]
			assert api.get(on_record)["record"] == {"doctype": "Quotation", "name": quote}, "filed on the record"
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
