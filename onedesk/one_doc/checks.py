"""OneDoc's part of the integration suite (one_demo/check.py runs it): a
document written, versioned, kept as a template, printed with a record's
fields and read as a Word file in OneCloud; a record's text written through
the record's save; and OneAI's cards on a document, asked with nothing sent
to a model."""

import json

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import DOT_PNG, check
from onedesk.one_demo.people import OWNER


@check
def a_document_is_written_in_onecloud():
	"""Layla writes a scope of works in her files. It opens with what she
	saved and keeps its page setup, takes a new name, carries a picture only
	its readers see, becomes a template another starts from, and a copy of it
	is a document of its own. Karim keeps no template until he is a Manager.
	Somebody who may not open it learns nothing of it. All undone afterwards."""
	import io

	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one_doc import api, templates

	was = getattr(frappe.local, "request", None)
	frappe.db.savepoint("doc_check")
	try:
		with as_user(OWNER):
			name = api.make("@my", "Scope check")["document"]
			api.save_document(name, "AAA=", "<h1>Scope</h1><p>Curtain wall.</p>")
			said = api.get_document(name)
			assert said["html"].startswith("<h1>Scope") and said["content"] == "AAA=" and said["can_write"], said
			assert said["trail"][-1]["id"] == "@my", "the path back is its folder"
			api.save_settings(name, json.dumps({"font_size": 17, "made_up": 1}))
			assert api.get_document(name)["settings"] == {"font_size": 17}, "only what a page may be set to"
			api.save_comments(name, "BBB=")
			assert api.get_document(name)["comments"] == "BBB="
			assert api.rename_document(name, "Scope of works check")["title"] == "Scope of works check"
			assert api.titles(json.dumps([name, "no-such-document"])) == {name: "Scope of works check"}
			assert any(one["email"] == OWNER for one in api.people()), "who may be mentioned"
			sent = EnvironBuilder(path="/api/method/onedesk.one_doc.api.add_picture", method="POST", data={"file": (io.BytesIO(DOT_PNG), "dot.png")})
			frappe.local.request = Request(sent.get_environ())
			picture = api.add_picture(name)
			assert picture["file_url"] == api.PICTURE + picture["name"]
			assert api.picture_extension(picture["name"]) == "png"
			api.picture(picture["name"])
			assert frappe.local.response["filecontent"] == DOT_PNG
			api.drop_pictures(json.dumps([picture["name"]]))
			assert not frappe.db.exists("File", picture["name"])
			api.download(name)
			assert frappe.local.response["location"] == f"/desk/document/{name}"
		with as_user("karim@one.test"):
			his = api.make("@my", "Template check")["document"]
			assert not api.get_document(his)["can_template"], "a User keeps no company templates"
			try:
				templates.save_as(his, "Not a template")
				raise AssertionError("a User kept a company template")
			except frappe.PermissionError:
				frappe.clear_messages()
			karim = frappe.get_doc("User", "karim@one.test")
			karim.flags.ignore_permissions = True
			karim.add_roles("OneDoc Manager")
			assert api.get_document(his)["can_template"], "a Manager keeps them"
			assert not frappe.has_permission(api.DOCUMENT, "read"), "keeping templates opens no document the File doesn't"
			kept = templates.save_as(his, "His template")
			assert any(one["name"] == kept["name"] for one in templates.listed()), "a template the editor offers"
			try:
				api.get_document(name)
				raise AssertionError("a Manager opened a document its File doesn't give him")
			except frappe.PermissionError:
				frappe.clear_messages()
		with as_user(OWNER):
			template = templates.save_as(name, "Scope template")
			assert any(one["name"] == template["name"] for one in templates.listed())
			started = api.make("@my", "From the template", template["name"])["document"]
			assert frappe.db.get_value(api.DOCUMENT, started, "html").startswith("<h1>Scope"), "a template's content"
			copy = frappe.get_doc({"doctype": "File", "file_url": api.URL + name, "folder": frappe.db.get_value("File", said["file"], "folder"), "file_name": "Scope copy"})
			copy.flags.ignore_permissions = True
			copy.insert()
			held = api.document_of(copy.file_url)
			assert held != name and frappe.db.get_value(api.DOCUMENT, held, "file") == copy.name, "a copy is a document of its own"
			frappe.delete_doc("File", copy.name, ignore_permissions=True)
			assert not frappe.db.exists(api.DOCUMENT, held), "and goes with its File"
		with as_user("Guest"):
			assert api.titles([name]) == {}, "a reader who can't open it isn't told its name"
			try:
				api.get_document(name)
				raise AssertionError("somebody who may not open the document opened it")
			except frappe.PermissionError:
				pass
	finally:
		frappe.local.request = was
		frappe.db.rollback(save_point="doc_check")


@check
def a_document_keeps_its_versions_and_asks_oneai():
	"""Layla's document keeps a version taken while writing and one she
	names, but not two taken within ten minutes. In the OneAI panel on the
	document, OneAI is told what it says and what she selected; it rewrites
	the selection, writes after the paragraph her cursor is in and at the
	end, each as a card; finds and reads documents, and makes a covering
	letter on a quotation from the template. A reader who may not open the
	document is not told it exists. All undone afterwards."""
	from onedesk.one_ai import proposals, tools
	from onedesk.one_doc import agent, api, versions

	frappe.db.savepoint("doc_ai_check")
	try:
		with as_user(OWNER):
			name = api.make("@my", "Minutes check")["document"]
			api.save_document(name, "AAA=", "<h1>Minutes</h1><p>Glass arrives <strong>Monday</strong> at nine.</p><p>Frames follow.</p>")
			assert versions.new_version(name, "<p>First</p>")["manual"] == 0
			assert versions.new_version(name, "<p>Second</p>") is None, "not two within ten minutes"
			assert versions.new_version(name, "<p>Second</p>", "Before review")["title"] == "Before review"
			assert [one["title"] for one in versions.listed(name)][-1] == "Before review"
			page = {"page": "document", "record": name, "selection": {"page": "document", "document": name, "text": "at nine", "block": "Frames follow."}}
			told = agent.page(page)
			assert "Glass arrives **Monday** at nine." in told and 'selected: """at nine"""' in told, told
			frappe.flags.one_ai_page = page
			try:
				for where, html in (("selection", "<p>at noon</p>"), ("after", "<p>Fixings last.</p>"), ("end", "<p>Next meeting Friday.</p>")):
					said = tools.run("write_document", {"document": name, "html": html, "where": where})
					assert not said["ran"] and said["answer"]["state"] == "Proposed", said
					proposals.apply(said["answer"]["proposal"])
			finally:
				frappe.flags.one_ai_page = None
			held = frappe.db.get_value(api.DOCUMENT, name, ["html", "content"], as_dict=True)
			assert "Glass arrives <strong>Monday</strong> at noon." in held.html, held.html
			assert "<p>Frames follow.</p><p>Fixings last.</p>" in held.html and held.html.endswith("<p>Next meeting Friday.</p>"), held.html
			assert not held.content, "the editor opens from the HTML"
			assert "Nothing is selected" in agent.write_document(name, "<p>x</p>", "selection")["error"]
			found = agent.my_documents("Minutes check")
			assert [one["document"] for one in found] == [name], found
			assert "Next meeting Friday." in agent.read_document(name)["text"]
			assert "send its words" in agent.draft_document("Empty", "<p> </p>")["error"]
			said = tools.run("draft_document", {"name": "Agenda check", "html": "<h1>Agenda</h1><p>Glass.</p>"})
			made = proposals.apply(said["answer"]["proposal"])["record"]
			assert "<h1>Agenda</h1>" in frappe.db.get_value(api.DOCUMENT, made, "html")
			quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
			said = tools.run("draft_document", {"name": "Letter check", "record_doctype": "Quotation", "record_name": quote, "template": "Quotation covering letter"})
			assert said["answer"]["state"] == "Proposed", said
			letter = proposals.apply(said["answer"]["proposal"])["record"]
			assert api.get_document(letter)["record"] == {"doctype": "Quotation", "name": quote}, "filed on the quotation"
			assert 'data-field="grand_total"' in frappe.db.get_value(api.DOCUMENT, letter, "html"), "from the template"
		with as_user("rania@one.test"):
			assert agent.my_documents("Minutes check") == [] and "error" in agent.read_document(name)
			assert agent.page({"page": "document", "record": name}) == "The reader is on a document's page in OneDoc."
			try:
				versions.listed(name)
				raise AssertionError("Rania read Layla's versions")
			except frappe.PermissionError:
				pass
	finally:
		frappe.db.rollback(save_point="doc_ai_check")


@check
def a_records_text_is_written_in_onedoc():
	"""A draft quotation's terms open as a document filed on it. What Omar
	writes there becomes the terms through the quotation's save; terms
	changed on the quotation meanwhile are not written over, and opening it
	again starts from them. A document made in the quotation's Files is
	opened by whoever may open the quotation and nobody else, and a
	submitted quotation's terms open read only. All undone afterwards."""
	from onedesk.one_doc import api, field

	frappe.db.savepoint("doc_field_check")
	try:
		quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
		with as_user("omar@one.test"):
			name = field.open_field("Quotation", quote, "terms")
			assert field.open_field("Quotation", quote, "terms") == name, "one text, one document"
			said = api.get_document(name)
			assert said["can_write"] and said["record"] == {"doctype": "Quotation", "name": quote} and said["bound"]["field"] == "terms", said
			assert not api.save_document(name, "AAA=", "<p>Payment in 30 days.</p>").get("refused")
			assert field.same(frappe.db.get_value("Quotation", quote, "terms"), "<p>Payment in 30 days.</p>"), "the terms are what was written"
			frappe.db.set_value("Quotation", quote, "terms", "<p>Changed on the form.</p>")
			refused = api.save_document(name, "BBB=", "<p>Payment in 45 days.</p>")["refused"]
			assert "changed on the record" in refused, refused
			assert field.same(frappe.db.get_value("Quotation", quote, "terms"), "<p>Changed on the form.</p>"), "and not written over"
			field.open_field("Quotation", quote, "terms")
			again = frappe.db.get_value(api.DOCUMENT, name, ["html", "content"], as_dict=True)
			assert again.html == "<p>Changed on the form.</p>" and not again.content, "it starts again from the record"
			try:
				field.open_field("Quotation", quote, "address_display")
				raise AssertionError("a text the record works out opened as a document")
			except frappe.ValidationError:
				pass
			made = api.make(f"@records/Quotation/{quote}", "Covering letter")["document"]
			assert api.get_document(made)["record"]["name"] == quote
		with as_user("mariam@one.test"):
			for one in (name, made):
				try:
					api.get_document(one)
					raise AssertionError("somebody who may not open the quotation opened its document")
				except frappe.PermissionError:
					pass
		sent = frappe.get_all("Quotation", filters={"docstatus": 1}, pluck="name", order_by="name", limit=1)
		if sent:
			with as_user(OWNER):
				assert not api.get_document(field.open_field("Quotation", sent[0], "terms"))["can_write"], "a submitted record's terms are read only"
	finally:
		frappe.db.rollback(save_point="doc_field_check")


@check
def a_document_prints_with_its_records_fields():
	"""A covering letter filed on a quotation names its customer, total and
	lines as fields; on paper they are what the quotation says, the lines a
	table, under the letter head. Page setup's header, page numbers and line
	go to the PDF renderer. The quotation's print page lists the letter, and
	its PDF is attached to the quotation. All undone afterwards."""
	from onedesk.one_doc import api, paper

	frappe.db.savepoint("doc_paper_check")
	try:
		quote = frappe.get_all("Quotation", filters={"docstatus": 0}, pluck="name", order_by="name", limit=1)[0]
		held = frappe.get_doc("Quotation", quote)
		with as_user("omar@one.test"):
			name = api.make(f"@records/Quotation/{quote}", "Covering letter check")["document"]
			offered = {one["field"]: one for one in paper.fields_of(name)}
			assert {"party_name", "grand_total", "items"} <= set(offered) and offered["items"]["table"], sorted(offered)
			html = (
				'<p>To <span data-field="party_name">Customer</span>,</p><p>Total <span data-field="grand_total">Grand Total</span></p>'
				'<p><span data-field="items">Items</span></p><p>Nobody sees <span data-field="no_such_field">this</span>.</p>'
			)
			api.save_document(name, "AAA=", html)
			filled = paper.fill(html, paper.record_of(name))
			assert frappe.utils.escape_html(held.party_name) in filled and frappe.format(held.grand_total, held.meta.get_field("grand_total"), held) in filled, filled
			assert '<table class="rows">' in filled and "<p><table" not in filled and held.items[0].item_code in filled, "the lines as a table, out of their paragraph"
			assert "Nobody sees ." in filled, "a field the record lacks prints nothing"
			assert "[Customer]" in paper.fill(html, None), "with no record, the field's name"
			api.save_settings(name, json.dumps({"print_header_left": "Sahara [x]", "print_show_pages": 1, "print_footer_separator": 1}))
			told = paper.options(name)
			assert told["header-left"] == "Sahara (x)" and "[page]" in told["footer-right"] and "footer-line" in told, told
			assert {"document": name, "title": "Covering letter check"} in paper.on_record("Quotation", quote)
			kept = paper.pdf(name, keep="record")
			assert kept["where"] == ["Quotation", quote] and frappe.db.get_value("File", kept["id"], "attached_to_name") == quote, kept
		with as_user("mariam@one.test"):
			assert paper.on_record("Quotation", quote) == [], "nor are its documents listed to whoever may not open the quotation"
	finally:
		frappe.db.rollback(save_point="doc_paper_check")


@check
def a_document_is_a_word_file_on_the_drive():
	"""On the network drive a document is "Name.docx", with its headings,
	lists, table, picture and page break; a download or a mail attachment is
	that Word file. Saved over from Word, it reads back in with a version
	kept; one with a record's fields in it is not written from Word. A Word
	file in OneCloud opens as a document and is written back into itself,
	its old content kept as a version, and a new version put in from outside
	is read in again. All undone afterwards."""
	import io

	from docx import Document

	from onedesk.one_doc import api, versions, word
	from onedesk.one_cloud import dav
	from onedesk.one_cloud import namespace as ns

	frappe.db.savepoint("doc_word_check")
	try:
		with as_user(OWNER):
			made = api.make("@my", "Word check")
			name = made["document"]
			from PIL import Image

			drawn = io.BytesIO()
			Image.new("RGB", (4, 4), "white").save(drawn, "PNG")
			picture = frappe.get_doc({"doctype": "File", "file_name": "dot.png", "content": drawn.getvalue(), "is_private": 1, "attached_to_doctype": api.DOCUMENT, "attached_to_name": name})
			picture.insert(ignore_permissions=True)
			html = (
				'<h1>Scope</h1><p style="text-align: center"><strong>Curtain</strong> wall.</p><ul><li><p>Glass</p></li><li><p>Frames</p></li></ul>'
				f'<table><tr><th>Item</th><th>Qty</th></tr><tr><td>Glass</td><td>4</td></tr></table><p><img src="{api.PICTURE}{picture.name}"></p>'
				'<div data-page-break="true"></div><p>Page two.</p>'
			)
			api.save_document(name, "AAA=", html)
			assert dav._as_file(ns.node(ns.row(made["id"])))["name"] == "Word check.docx"
			doc = Document(io.BytesIO(word.build(name)))
			said = [(one.style.name, one.text) for one in doc.paragraphs if one.text]
			assert ("Heading 1", "Scope") in said and ("List Bullet", "Glass") in said and ("Normal", "Page two.") in said, said
			assert doc.tables[0].cell(1, 0).text == "Glass" and doc.inline_shapes, "the table and the picture"
			assert doc.paragraphs[1].alignment == 1 and doc.paragraphs[1].runs[0].bold
			file = frappe.get_doc("File", made["id"])
			assert file.get_content()[:2] == b"PK" and file.file_name == "Word check.docx", "an attachment or a download is the Word file"
			file.save()
			assert frappe.db.get_value("File", made["id"], "file_name") == "Word check", "and the file keeps its name"
			saved = Document()
			saved.add_heading("Scope", 1)
			saved.add_paragraph("Changed in Word.")
			out = io.BytesIO()
			saved.save(out)
			word.write(name, out.getvalue())
			held = frappe.db.get_value(api.DOCUMENT, name, ["html", "content"], as_dict=True)
			assert "Changed in Word." in held.html and not held.content, held
			assert any(one["title"] == "Before a Word save" and "Curtain" in one["snapshot"] for one in versions.listed(name)), "a version is kept"
			api.save_document(name, "BBB=", '<p>To <span data-field="customer_name">Customer</span></p>')
			try:
				word.write(name, out.getvalue())
				raise AssertionError("a document with a record's fields was written from Word")
			except frappe.PermissionError:
				pass
			upload = frappe.get_doc({"doctype": "File", "file_name": "Letter check.docx", "content": out.getvalue(), "is_private": 1, "folder": ns.HOME})
			upload.insert()
			opened = word.open_file(upload.name)["document"]
			assert word.open_file(upload.name)["document"] == opened, "one file, one document"
			assert "Changed in Word." in api.get_document(opened)["html"] and api.get_document(opened)["word"]
			api.save_document(opened, "CCC=", "<p>Written in OneDoc.</p>")
			assert api.rename_document(opened, "Letter checked")["title"] == "Letter checked.docx", "a Word file keeps its .docx"
			word.write_back(opened)
			back = Document(io.BytesIO(frappe.get_doc("File", upload.name).get_content()))
			assert [one.text for one in back.paragraphs] == ["Written in OneDoc."], "written back into itself"
			assert frappe.db.count("Cloud File Version", {"file": upload.name}) == 1, "what it held kept as a version"
			word.file_replaced(upload.name)
			assert "Written in OneDoc." in api.get_document(opened)["html"], "a new version from outside is read in again"
			frappe.delete_doc("File", upload.name, ignore_permissions=True, force=True)
			assert not frappe.db.exists(api.DOCUMENT, opened), "and its document goes with the file"
	finally:
		frappe.db.rollback(save_point="doc_word_check")


@check
def a_word_file_is_never_saved_over_with_less():
	"""A Word file with comments opens in OneDoc saying what saving over
	it would drop, and waits: the file stays as it was until the owner
	chooses Save as Copy, which leaves it alone, or Save Over Original. A
	new version arriving while changes wait keeps them as a copy. A .docm
	never opens here, and a document of One's own saved from Word with
	comments says so when it next opens. All undone afterwards."""
	import io

	from docx import Document

	from onedesk.one_doc import api, word
	from onedesk.one_cloud import history, saving
	from onedesk.one_cloud import namespace as ns

	def letter(text: str, comment: bool = True) -> bytes:
		made = Document()
		said = made.add_paragraph(text)
		if comment:
			made.add_comment(said.runs[0], text="Check the date.", author="Huda")
		out = io.BytesIO()
		made.save(out)
		return out.getvalue()

	frappe.db.savepoint("doc_lose_check")
	try:
		with as_user(OWNER):
			upload = frappe.get_doc({"doctype": "File", "file_name": "Lease check.docx", "content": letter("Signed on Monday."), "is_private": 1, "folder": ns.HOME})
			upload.insert()
			before = upload.file_url
			opened = word.open_file(upload.name)["document"]
			said = api.get_document(opened)
			assert said["can_write"] and "comments" in (said["loses"] or ""), said["loses"]
			api.save_document(opened, "AAA=", "<p>Signed on Tuesday.</p>")
			assert "held" in word.write_back(opened), "saving over waits for a choice"
			assert frappe.db.get_value("File", upload.name, "file_url") == before and frappe.db.get_value(api.DOCUMENT, opened, "held_back")
			copy = word.write_back(opened, "copy")
			assert copy["file"] != upload.name and frappe.db.get_value("File", upload.name, "file_url") == before, "a copy leaves the file alone"
			assert frappe.db.get_value(api.DOCUMENT, opened, "file") == copy["file"], "and the document goes on in the copy"
			again = word.open_file(upload.name)["document"]
			api.save_document(again, "BBB=", "<p>Signed on Wednesday.</p>")
			assert "held" in word.write_back(again)
			replaced = frappe.get_doc({"doctype": "File", "file_name": "Lease check.docx", "content": letter("Signed on Thursday."), "is_private": 1, "folder": ns.HOME})
			replaced.insert()
			history.replace(ns.row(upload.name), replaced.name)
			kept = frappe.db.get_value(api.DOCUMENT, again, ["file", "source_kind"], as_dict=True)
			assert kept.file != upload.name and not kept.source_kind, "changes that waited are kept as a copy, not read over"
			assert frappe.db.get_value("File", kept.file, "file_name").startswith("Lease check ("), frappe.db.get_value("File", kept.file, "file_name")
			third = word.open_file(upload.name)["document"]
			api.save_document(third, "CCC=", "<p>Signed on Friday.</p>")
			word.write_back(third, "over")
			assert Document(io.BytesIO(frappe.get_doc("File", upload.name).get_content())).paragraphs[0].text == "Signed on Friday."
			assert not saving.listed(frappe.db.get_value(api.DOCUMENT, third, "would_lose")), "saved over, it is One's to keep"
			macro = frappe.get_doc({"doctype": "File", "file_name": "Macro check.docm", "content": letter("x", False), "is_private": 1, "folder": ns.HOME})
			macro.insert()
			try:
				word.open_file(macro.name)
				raise AssertionError("a .docm opened in OneDoc")
			except frappe.ValidationError:
				pass
			own = api.make("@my", "Own check")["document"]
			api.save_document(own, "DDD=", "<p>Ours.</p>")
			word.write(own, letter("From Word."))
			assert "comments" in (api.get_document(own)["dropped"] or ""), "a save from Word that left comments out says so"
			api.dismiss_dropped(own)
			assert not api.get_document(own)["dropped"]
	finally:
		frappe.db.rollback(save_point="doc_lose_check")
