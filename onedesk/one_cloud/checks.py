"""OneCloud's part of the integration suite (one_demo/check.py runs it):
a file edited in OneOS and the editors under one lease, the drive's locks,
office files that open where nothing is lost, the site team's library,
files shared out and asked for, and who may open each."""

import base64
import io
import json
from unittest import mock

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import VILLA, _asked, _cookies, _unasked, check
from onedesk.one_demo.people import OWNER


class _Server:
	"""A server folder held in memory, standing in for SFTP or WebDAV."""

	def __init__(self, held: dict):
		self.held = held

	def close(self):
		pass

	def list(self, path: str) -> list[dict]:
		path = path.strip("/")
		inside = [key for key in self.held if key.rsplit("/", 1)[0] == path or (not path and "/" not in key)]
		return [{"name": key.rsplit("/", 1)[-1], "folder": self.held[key] is None, "size": len(self.held[key] or b""), "modified": None} for key in inside]

	def read(self, path: str) -> bytes:
		return self.held[path.strip("/")]

	def write(self, path: str, content: bytes) -> None:
		self.held[path.strip("/")] = content

	def make_folder(self, path: str) -> None:
		self.held[path.strip("/")] = None

	def rename(self, path: str, to: str) -> None:
		self.held[to.strip("/")] = self.held.pop(path.strip("/"))

	def remove(self, path: str, folder: bool) -> None:
		self.held.pop(path.strip("/"))


@check
def onecloud_a_letter_is_edited_in_oneos():
	"""Samir opens a letter in OneOS from the Projects library and it is his
	alone: Rania, who may change it too, is told he has it, and Yousef, who
	only reads, opens a copy in his own files instead. The container fetches
	the letter and saves a version as Samir through the two sealed addresses,
	which open nothing else, and OneAdmin's stop lets the lease go and tells
	him why."""
	from urllib.parse import parse_qs, urlparse

	from werkzeug.exceptions import Forbidden

	from onedesk.one_demo import storage as demo
	from onedesk.one_cloud import api, history, oneos, upload

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	asked, answers = [], {}

	def admin(endpoint, **said):
		asked.append((endpoint.rsplit(".", 1)[-1], said))
		if endpoint.endswith("oneos_start"):
			return {"session": f"session{len(asked):04d}", "url": f"https://os.example.com/s/session{len(asked):04d}?t=1.x", "state": "Starting"}
		return answers.get(endpoint.rsplit(".", 1)[-1], {"url": "https://r2.example.com/letter"})

	def sealed(url):
		return {key: one[0] for key, one in parse_qs(urlparse(url).query).items()}

	with mock.patch("onedesk.one.account.ask", side_effect=admin), mock.patch("onedesk.one.account.configured", return_value=True), mock.patch("onedesk.one_cloud.oneos.offered", return_value={"credits_an_hour": 3}), mock.patch("frappe.publish_realtime") as told:
		with as_user(demo.PM):
			letter = upload._place(root, None, {"file_name": "Villa handover.odt", "content": b"handover v1"})["id"]
			opened = oneos.start(letter)
			assert opened["url"].startswith("https://os.example.com/s/") and asked[-1][0] == "oneos_start"
			assert next(one for one in api.listing(root)["items"] if one["id"] == letter)["oneos"] == {"by": frappe.utils.get_fullname(demo.PM), "mine": True}
			again = oneos.start(letter)
			assert asked[-1][1]["again"] == opened["url"].split("/s/")[1].split("?")[0] and again["node"] == letter, "his own session is opened again, not a second"
		start = next(said for endpoint, said in asked if endpoint == "oneos_start")
		with as_user("rania@one.test"):
			assert oneos.start(letter)["held"]["by"] == frappe.utils.get_fullname(demo.PM)
		with as_user("yousef@one.test"):
			assert oneos.start(letter)["held"]["readonly"]
			copy = oneos.start(letter, copy=1)
			assert copy["node"] != letter and frappe.db.get_value("File", copy["node"], "one_lease_user") == "yousef@one.test"
			oneos.close(copy["node"])
			assert asked[-1][0] == "oneos_stop" and not frappe.db.get_value("File", copy["node"], "one_lease_user")
		down, up = sealed(start["file_url"]), sealed(start["save_url"])
		oneos.file(**down)
		for key in ("type", "filecontent", "filename", "display_content_as"):
			frappe.local.response.pop(key, None)
		try:
			_asked(data=b"handover v2")
			assert oneos.save(**up) == {"saved": True}
			_asked(data=b"handover v2")
			assert oneos.save(**up) == {"saved": False}, "the same content is not a version"
			for wrong in ({**down}, {**up, "f": copy["node"]}, {**up, "e": str(int(up["e"]) + 1)}):
				try:
					oneos.save(**wrong)
					raise AssertionError("a sealed address saved what it was not made for")
				except Forbidden:
					pass
		finally:
			_unasked()
		assert len(history.versions(letter)) == 1 and frappe.db.get_value("File", letter, "modified_by") == demo.PM
		answers["oneos_state"] = {"state": "Stopped", "stop_reason": "Idle"}
		with mock.patch("onedesk.one_cloud.tell.oneos_closed") as closed:
			oneos.stopped(frappe.db.get_value("File", letter, "one_lease_session"))
		assert not frappe.db.get_value("File", letter, "one_lease_user")
		assert any(call.args[0] == "onecloud_oneos" and call.args[1].get("why") == "Idle" for call in told.call_args_list)
		assert closed.call_args.args[:2] == (demo.PM, letter)
	for name in (letter, copy["node"]):
		frappe.delete_doc("File", name, ignore_permissions=True, force=True)


@check
def onecloud_one_lease_keeps_oneos_and_the_editors_apart():
	"""Rania has a letter open in OneDoc, so Samir's Open in OneOS tells
	him she is editing it there. Once her editor leaves, his session has it
	alone: her OneDoc opens it read-only saying he is editing it in OneOS,
	refuses her save, and no version of it is restored under him. Saves from
	his session are one version. All undone afterwards."""
	from urllib.parse import parse_qs, urlparse

	from docx import Document

	from onedesk.one_demo import storage as demo
	from onedesk.one_doc import api as writing
	from onedesk.one_doc import word
	from onedesk.one_sheet import live
	from onedesk.one_cloud import history, lease, oneos, upload

	def letter(text: str) -> bytes:
		made = Document()
		made.add_paragraph(text)
		out = io.BytesIO()
		made.save(out)
		return out.getvalue()

	def admin(endpoint, **said):
		return {"session": "lease-check", "url": "https://os.example.com/s/lease-check?t=1.x", "state": "Running"} if endpoint.endswith("oneos_start") else {}

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	samir, rania = frappe.utils.get_fullname(demo.PM), "rania@one.test"
	frappe.db.savepoint("lease_check")
	try:
		with mock.patch("onedesk.one.account.ask", side_effect=admin) as asked, mock.patch("onedesk.one_cloud.oneos.offered", return_value={"credits_an_hour": 3}), mock.patch("frappe.publish_realtime"):
			with as_user(demo.PM):
				file = upload._place(root, None, {"file_name": "Handover check.docx", "content": letter("Keys on Monday.")})["id"]
				first = upload._place(root, None, {"file_name": "Handover check.docx", "content": letter("Keys on Tuesday.")}, replace=1)
				assert first["id"] == file and len(history.versions(file)) == 1
			with as_user(rania):
				document = word.open_file(file)["document"]
				assert live.admit("document", document, sid="lease-check")["write"]
				live.here(json.dumps([["document", document]]), sid="lease-check")
				assert lease.of(file)["mode"] == "live" and lease.of(file)["live"][0]["app"] == "OneDoc"
			with as_user(demo.PM):
				held = oneos.start(file)["held"]
				assert held["by"] == frappe.utils.get_fullname(rania) and held["where"] == "OneDoc", held
			with as_user(rania):
				live.leave("document", document, sid="lease-check")
			with as_user(demo.PM):
				assert oneos.start(file)["url"], "alone once nobody is in it live"
			start = next(call.kwargs for call in asked.call_args_list if call.args[0].endswith("oneos_start"))
			with as_user(rania):
				said = writing.get_document(document)
				assert not said["can_write"] and said["notice"] == f"{samir} is editing this in OneOS.", said["notice"]
				assert not live.admit("document", document, sid="lease-check")["write"]
				live.leave("document", document, sid="lease-check")
				for refused in (lambda: writing.save_document(document, "AAA=", "<p>Keys on Friday.</p>"), lambda: history.restore(file, history.versions(file)[0]["name"])):
					try:
						refused()
						raise AssertionError("changed under the OneOS session")
					except (frappe.ValidationError, frappe.PermissionError):
						frappe.clear_last_message()
				assert lease.of(file)["alone"] == {"by": samir, "kind": lease.ONEOS, "mine": False}
			up = {key: one[0] for key, one in parse_qs(urlparse(start["save_url"]).query).items()}
			try:
				for text in ("Keys on Wednesday.", "Keys on Thursday."):
					_asked(data=letter(text))
					assert oneos.save(**up) == {"saved": True}
			finally:
				_unasked()
			assert len(history.versions(file)) == 2, "two saves in one session are one version, beside the one before it"
			with as_user(demo.PM):
				oneos.close(file)
			assert not lease.blocking(file)
	finally:
		frappe.db.rollback(save_point="lease_check")


@check
def onecloud_a_document_of_ones_own_is_edited_in_oneos():
	"""Samir's handover note is a document of One's own. While Rania writes
	in it in OneDoc, his Edit in OneOS tells him so; once she leaves,
	OneOS gets it as a Word file, his save comes back into the document with
	what it said before kept as "Before a OneOS save", the header Word gave
	it is noted as dropped, and Rania's OneDoc reads while he has it. A
	document with a record's fields is refused. All undone afterwards."""
	from urllib.parse import parse_qs, urlparse

	from docx import Document

	from onedesk.one_demo import storage as demo
	from onedesk.one_doc import api as writing
	from onedesk.one_doc import versions
	from onedesk.one_sheet import live
	from onedesk.one_cloud import lease, oneos, opening

	def note(text: str) -> bytes:
		made = Document()
		made.add_paragraph(text)
		made.sections[0].header.paragraphs[0].text = "Mansour Villa"
		out = io.BytesIO()
		made.save(out)
		return out.getvalue()

	def admin(endpoint, **said):
		return {"session": "own-check", "url": "https://os.example.com/s/own-check?t=1.x", "state": "Running"} if endpoint.endswith("oneos_start") else {}

	def sealed(url):
		return {key: one[0] for key, one in parse_qs(urlparse(url).query).items()}

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	samir, rania = frappe.utils.get_fullname(demo.PM), "rania@one.test"
	frappe.db.savepoint("own_oneos_check")
	try:
		with mock.patch("onedesk.one.account.ask", side_effect=admin) as asked, mock.patch("onedesk.one_cloud.oneos.offered", return_value={"credits_an_hour": 3}), mock.patch("frappe.publish_realtime"):
			with as_user(demo.PM):
				document = writing.make(root, "Handover note")["document"]
				frappe.db.set_value(writing.DOCUMENT, document, "html", "<p>Keys on Monday.</p>")
				file = writing._may(document)["name"]
			with as_user(rania):
				assert live.admit("document", document, sid="own-check")["write"]
			with as_user(demo.PM):
				held = oneos.start(file)["held"]
				assert held["by"] == frappe.utils.get_fullname(rania) and held["where"] == "OneDoc", held
			with as_user(rania):
				live.leave("document", document, sid="own-check")
			with as_user(demo.PM):
				opened = oneos.start(file)
				assert opened["url"] and opened["name"] == "Handover note.docx", opened
			start = next(call.kwargs for call in asked.call_args_list if call.args[0].endswith("oneos_start"))
			assert start["file_name"] == "Handover note.docx"
			with as_user(rania):
				said = writing.get_document(document)
				assert not said["can_write"] and said["notice"] == f"{samir} is editing this in OneOS.", said["notice"]
			oneos.file(**sealed(start["file_url"]))
			sent = frappe.local.response.pop("filecontent")
			for key in ("type", "filename", "display_content_as"):
				frappe.local.response.pop(key, None)
			assert sent.startswith(b"PK") and "Keys on Monday." in Document(io.BytesIO(sent)).paragraphs[0].text
			up = sealed(start["save_url"])
			try:
				_asked(data=sent)
				assert oneos.save(**up) == {"saved": False}, "the file as it was sent is not a save"
				friday = note("Keys on Friday.")
				_asked(data=friday)
				assert oneos.save(**up) == {"saved": True}
				_asked(data=friday)
				assert oneos.save(**up) == {"saved": False}, "the same save twice is one"
			finally:
				_unasked()
			held = frappe.db.get_value(writing.DOCUMENT, document, ["html", "outside_dropped", "modified_by"], as_dict=True)
			assert "Keys on Friday." in held.html and held.modified_by == demo.PM, held
			with as_user(demo.PM):
				kept = [one for one in versions.listed(document) if one["title"] == "Before a OneOS save"]
			assert len(kept) == 1 and "Keys on Monday." in kept[0]["snapshot"], kept
			assert json.loads(held.outside_dropped)["what"] == ["headers_and_footers"], held.outside_dropped
			with as_user(demo.PM):
				assert writing.get_document(document)["dropped"].startswith(f"{samir} saved this in OneOS on ")
				opening.download(file)
				assert frappe.local.response.pop("filename") == "Handover note.docx"
				assert "Keys on Friday." in Document(io.BytesIO(frappe.local.response.pop("filecontent"))).paragraphs[0].text
				frappe.local.response.pop("type", None)
				oneos.close(file)
			assert not lease.blocking(file)
			with as_user(demo.PM):
				frappe.db.set_value(writing.DOCUMENT, document, "html", '<p>Dear <span data-field="customer_name">Customer</span></p>')
				try:
					oneos.start(file)
					raise AssertionError("a document with a record's fields went to OneOS")
				except frappe.ValidationError:
					frappe.clear_last_message()
	finally:
		frappe.db.rollback(save_point="own_oneos_check")


LOCKINFO = (
	b'<?xml version="1.0" encoding="utf-8"?><D:lockinfo xmlns:D="DAV:"><D:lockscope><D:exclusive/></D:lockscope>'
	b"<D:locktype><D:write/></D:locktype><D:owner><D:href>RANIA-PC/rania</D:href></D:owner></D:lockinfo>"
)


DISCOVERY = b'<?xml version="1.0"?><D:propfind xmlns:D="DAV:"><D:prop><D:lockdiscovery/></D:prop></D:propfind>'


@check
def onecloud_the_drives_locks_join_the_lease():
	"""Rania's Word lock is the file's lease: Samir's Word and drive save are
	refused naming her, her saves are one version, Word's and the Mac's safe
	saves keep the same File and lease. Unlocked, Samir saving from an older
	version, or with an old If-Match, gets "(Samir's copy)" beside it. While
	Samir is live in OneDoc her Word is refused naming him; deleting it
	in OneCloud while she has it tells her. All undone afterwards."""
	from urllib.parse import quote

	from docx import Document

	from onedesk.one_demo import storage as demo
	from onedesk.one_doc import word
	from onedesk.one_sheet import live
	from onedesk.one_cloud import api, dav, history, lease, upload

	def letter(text: str) -> bytes:
		made = Document()
		made.add_paragraph(text)
		out = io.BytesIO()
		made.save(out)
		return out.getvalue()

	def said(content: bytes) -> str:
		return Document(io.BytesIO(content)).paragraphs[0].text

	def drive(method: str, path: str, body: bytes = b"", **headers) -> tuple[int, dict, bytes]:
		_asked(path=dav.MOUNT + quote(path), method=method, data=body, headers={key.replace("_", "-"): value for key, value in headers.items()})
		answer = dav.serve()
		out = b"".join(answer.response)
		dav._forget()
		return answer.status_code, answer.headers, out

	def holds(path: str, token: str) -> str:
		return f"<{quote(path)}> (<{token}>)"

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	rania, taken = "rania@one.test", []
	frappe.db.savepoint("drive_lock_check")
	try:
		with mock.patch("frappe.publish_realtime"), mock.patch("onedesk.one_cloud.tell.deleted_while_open") as told:
			with as_user(demo.PM):
				file = upload._place(root, None, {"file_name": "Drive check.docx", "content": letter("Keys on Monday.")})["id"]
				path = dav.path_of(file)
				folder = path.rsplit("/", 1)[0]
			with as_user(rania):
				status, headers, _out = drive("LOCK", path, LOCKINFO, Timeout="Second-600", Depth="0", Content_Type="text/xml")
				assert status == 200, status
				token = headers["Lock-Token"].strip("<>")
				taken.append(token)
				alone = lease.alone_of(file)
				assert (alone.one_lease_user, alone.one_lease_kind, alone.one_lease_lock) == (rania, lease.DAV, token), alone
				left = (get_datetime(alone.one_lease_until) - now_datetime()).total_seconds()
				assert 590 < left <= 600, left
			with as_user(demo.PM):
				assert drive("LOCK", path, LOCKINFO, Timeout="Second-600", Depth="0")[0] == 423, "a second Word opens it read-only"
				assert b"RANIA-PC" in drive("PROPFIND", path, DISCOVERY, Depth="0")[2], "and is told whose it is"
				assert drive("PUT", path, letter("Samir's keys."))[0] == 423
				assert lease.of(file)["alone"] == {"by": frappe.utils.get_fullname(rania), "kind": lease.DAV, "mine": False}
			with as_user(rania):
				before = len(history.versions(file))
				for text in ("Keys on Tuesday.", "Keys on Wednesday."):
					assert drive("PUT", path, letter(text), If=holds(path, token))[0] == 204
				assert len(history.versions(file)) == before + 1, "saves under one lock are one version"
				assert drive("LOCK", path, Timeout="Second-3600", If=holds(path, token))[0] == 200
				assert get_datetime(lease.alone_of(file).one_lease_until) > add_to_date(now_datetime(), minutes=59), "a refresh renews the lease"

				aside, temp = f"{folder}/~WRL0001.tmp", f"{folder}/~WRD0000.tmp"
				assert drive("PUT", temp, letter("Keys on Thursday."))[0] == 201
				assert drive("MOVE", path, Destination=dav.MOUNT + quote(aside), Overwrite="F", If=holds(path, token))[0] in (201, 204)
				assert drive("MOVE", temp, Destination=dav.MOUNT + quote(path), Overwrite="F")[0] in (201, 204)
				assert drive("DELETE", aside)[0] == 204
				assert frappe.db.get_value("File", file, ["file_name", "one_deleted"]) == ("Drive check.docx", 0)
				assert said(drive("GET", path)[2]) == "Keys on Thursday.", "Word's safe save is a save of the same file"
				assert not frappe.get_all("File", filters={"file_name": ["like", "~WR%"]}, limit=1), "and leaves nothing behind"
				assert lease.alone_of(file).one_lease_lock == token, "the lease followed the file"

				side = path + ".sb-2f1c-Qx"
				assert drive("PUT", side, letter("Keys on Friday."))[0] == 201
				assert drive("MOVE", side, Destination=dav.MOUNT + quote(path), Overwrite="T", If=holds(path, token))[0] in (201, 204)
				assert said(drive("GET", path)[2]) == "Keys on Friday." and not frappe.get_all("File", filters={"file_name": ["like", "%.sb-%"]}, limit=1)
				assert drive("UNLOCK", path, Lock_Token=f"<{token}>")[0] == 204
				assert not lease.blocking(file), "UNLOCK lets the lease go"

			with as_user(demo.PM):
				drive("GET", path)
			with as_user(rania):
				assert drive("PUT", path, letter("Keys on Saturday."))[0] == 204
			with as_user(demo.PM):
				assert drive("PUT", path, letter("Keys on Sunday."))[0] == 204
				assert drive("PUT", path, letter("Keys on Sunday evening."))[0] == 204
				assert said(drive("GET", path)[2]) == "Keys on Saturday.", "an older copy never lands over hers"
				copy = frappe.db.get_value("File", {"folder": root, "file_name": "Drive check (Samir's copy).docx"})
				assert copy and len(history.versions(copy)) == 1, "his copy beside it, his next save into it"
				etag = drive("HEAD", path)[1]["ETag"]
			with as_user(rania):
				upload._place(root, None, {"file_name": "Drive check.docx", "content": letter("Keys on Monday again.")}, replace=1)
			with as_user(demo.PM):
				assert drive("PUT", path, letter("Keys from an old phone."), If_Match=etag)[0] == 204
				assert said(drive("GET", path)[2]) == "Keys on Monday again."
				assert frappe.db.count("File", {"folder": root, "file_name": ["like", "Drive check (Samir's copy)%"]}) == 1, "into the same copy"

			with as_user(demo.PM):
				document = word.open_file(file)["document"]
				assert live.admit("document", document, sid="drive-check")["write"]
			with as_user(rania):
				assert drive("LOCK", path, LOCKINFO, Timeout="Second-600", Depth="0")[0] == 423
				named = drive("PROPFIND", path, DISCOVERY, Depth="0")[2].decode()
				assert frappe.utils.get_fullname(demo.PM) in named and "OneDoc" in named, named
			with as_user(demo.PM):
				live.leave("document", document, sid="drive-check")

			with as_user(rania):
				status, headers, _out = drive("LOCK", path, LOCKINFO, Timeout="Second-600", Depth="0")
				assert status == 200
				taken.append(headers["Lock-Token"].strip("<>"))
			with as_user(demo.PM):
				assert drive("DELETE", path)[0] == 423, "not from his drive while her Word has it"
				api.delete([file])
				assert frappe.db.get_value("File", file, "one_deleted") == 1, "from OneCloud, to the Recycle Bin"
				assert told.call_args.args[0] == [rania], told.call_args
	finally:
		_unasked()
		locks = dav._app().lock_manager.storage
		for token in taken:
			locks.delete(token)
		frappe.db.rollback(save_point="drive_lock_check")


@check
def onecloud_an_office_file_opens_where_nothing_is_lost():
	"""Samir's plain workbook opens in OneSheet, but one with comments
	asks first, naming them, and is read once for that version: the listing
	says so after. A macro workbook is copied into One as a workbook of its
	own, the file left as it was. While OneOS is off, Edit in OneOS is
	refused. All undone afterwards."""
	from openpyxl import Workbook

	from onedesk.one_demo import storage as demo
	from onedesk.one_sheet import api as sheets
	from onedesk.one_cloud import api, opening, oneos, upload

	def book(chart: bool = False) -> bytes:
		from openpyxl.chart import BarChart, Reference

		made = Workbook()
		made.active["A1"] = "Rent"
		made.active["B1"] = 1200
		if chart:
			drawn = BarChart()
			drawn.add_data(Reference(made.active, min_col=2, min_row=1, max_row=1))
			made.active.add_chart(drawn, "D2")
		out = io.BytesIO()
		made.save(out)
		return out.getvalue()

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	frappe.db.savepoint("opening_check")
	try:
		with mock.patch("frappe.publish_realtime"), as_user(demo.PM):
			plain = upload._place(root, None, {"file_name": "Rent check.xlsx", "content": book()})["id"]
			noted = upload._place(root, None, {"file_name": "Rent notes check.xlsx", "content": book(chart=True)})["id"]
			assert opening.weigh(plain)["loses"] == []
			said = opening.weigh(noted)
			assert said["loses"] == ["charts"] and said["said"] == "This file has charts OneSheet can't keep.", said
			row = next(one for one in api.listing(root)["items"] if one["id"] == noted)
			assert row["office"] == {"edit": "workbook", "make": None, "copy": None, "loses": ["charts"]}, row["office"]
			macros = upload._place(root, None, {"file_name": "Rent model check.xlsm", "content": book()})["id"]
			before = api._content(api._item(macros))
			made = opening.one_copy(macros)
			assert made["name"] == "Rent model check" and not frappe.db.get_value(sheets.WORKBOOK, made["workbook"], "source_kind")
			assert "Rent" in json.dumps(sheets.get_sheet(made["workbook"])["sheets_data"]), "the copy has the file's cells"
			assert api._content(api._item(macros)) == before, "the file stays as it was"
			with mock.patch("onedesk.one_cloud.oneos.offered", return_value=None):
				try:
					oneos.start(plain)
					raise AssertionError("OneOS started while it is off")
				except frappe.ValidationError:
					frappe.clear_last_message()
	finally:
		frappe.db.rollback(save_point="opening_check")


@check
def onecloud_office_files_wait_to_open_in_oneos():
	"""Every office file the demo wrote is where its owner left it, opens in
	OneOS for them and reads back as what it says it is: the Word files as
	paragraphs, the workbooks with their formulas, the deck with its slides and
	the export with its rows. Whoever it was shared with may read it, and only
	those given edit may change it."""
	import csv

	from docx import Document
	from openpyxl import load_workbook
	from pptx import Presentation

	from onedesk.one_demo import office as demo
	from onedesk.one_cloud import api, oneos
	from onedesk.one_cloud import namespace as ns

	for one in demo.files():
		node = demo.found(one)
		assert node, f"{one['name']} is not in {one['owner']}'s files"
		item = ns.row(node)
		assert oneos.opens(item.file_name), item.file_name
		folder = ns.row(item.folder)
		assert folder and folder.file_name == one["folder"], f"{one['name']} is in {folder and folder.file_name}"
		with as_user(one["owner"]):
			oneos._openable(node)
			content = api._content(item)
		kind = item.file_name.rsplit(".", 1)[-1]
		if kind == "docx":
			assert len([para for para in Document(io.BytesIO(content)).paragraphs if para.text.strip()]) >= 5, item.file_name
		elif kind == "xlsx":
			book = load_workbook(io.BytesIO(content))
			assert any(isinstance(cell.value, str) and cell.value.startswith("=") for sheet in book for row in sheet.iter_rows() for cell in row), item.file_name
		elif kind == "pptx":
			assert len(Presentation(io.BytesIO(content)).slides) >= 4, item.file_name
		else:
			rows = list(csv.reader(io.StringIO(content.decode())))
			assert rows[0][0] == "Item code" and len(rows) > 1, item.file_name
		for user, edit in one["shared"].items():
			assert ns.may(item, "read", user=user), f"{user} cannot read {one['name']}"
			assert ns.may(item, "write", user=user) == bool(edit), f"{user} {'cannot' if edit else 'can'} change {one['name']}"
	budget = next(one for one in demo.files() if one["name"] == demo.budget_name())
	assert not ns.may(ns.row(demo.found(budget)), "read", user="nadia@one.test"), "Huda's budget is not open to everybody"


@check
def onecloud_the_site_team_works_in_its_library():
	"""Samir's Projects library as the crew uses it: listed, searched and
	found by its path, a folder made, renamed and moved about, a file copied,
	attached to the villa, bound with its copy into one PDF, starred and put back
	to its first version, coloured, shared
	and unshared, deleted and restored, and the bin emptied. Yousef only
	reads it. What OneAI says about a file and who sees it, and a drive
	answering for Samir."""
	from pypdf import PdfReader, PdfWriter

	from onedesk.one_demo import storage as demo
	from PIL import Image

	from onedesk.one_cloud import agent, api, dav, history, library, made, office, pdf, share, upload
	from onedesk.one_cloud import namespace as ns

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	drawing = frappe.db.get_value("File", {"folder": root, "file_name": demo.ELEVATIONS})
	notes = frappe.db.get_value("File", {"owner": demo.PM, "file_name": demo.NOTES})
	with as_user(demo.PM):
		assert demo.ELEVATIONS in {one["name"] for one in api.listing(root)["items"]}
		assert drawing in {one["id"] for one in api.listing(ns.ROOT, search="elevations", everywhere=1)["items"]}
		assert any(one["id"] == root for one in api.folders(ns.LIBRARIES))
		assert api.resolve(f"Libraries/{demo.LIBRARY}") == root
		assert {one["user"] for one in library.members(root)["members"]} >= {"rania@one.test", "yousef@one.test"}
		folder = api.make_folder(root, "Site photos")["id"]
		folder = api.rename(folder, "Villa site photos")["id"]
		assert api.text(notes)["text"].strip() == demo.NOTES_SAID and not api.text(notes)["cut"]
		api.content(notes)
		assert frappe.local.response.type == "binary" and frappe.local.response.filecontent.decode().strip() == demo.NOTES_SAID
		for key in ("type", "filecontent", "filename"):
			frappe.local.response.pop(key, None)
		assert api.color([folder], "green") == [folder]
		assert next(one for one in api.listing(root)["items"] if one["id"] == folder)["color"] == "green"
		assert api.color([drawing], "red") == [] and not frappe.db.get_value("File", drawing, "one_color")
		try:
			api.color([folder], "orange")
			raise AssertionError("a colour nobody offered was kept")
		except frappe.ValidationError:
			pass
		copied = api.copy([drawing], folder)
		assert frappe.db.get_value("File", copied[0], "file_name") == demo.ELEVATIONS
		bound = pdf.combine([drawing, copied[0]], folder, "Elevations bound")
		pages = len(PdfReader(io.BytesIO(api._content(api._item(drawing)))).pages)
		assert bound["name"] == "Elevations bound.pdf"
		assert len(PdfReader(io.BytesIO(api._content(api._item(bound["id"])))).pages) == 2 * pages
		try:
			pdf.combine([drawing, notes], folder)
			raise AssertionError("a text file was put into a PDF")
		except frappe.ValidationError:
			pass
		dot = io.BytesIO()
		Image.new("RGB", (4, 4), "blue").save(dot, "PNG")
		making = {"picture": {"data": base64.b64encode(dot.getvalue()).decode(), "mime": "image/png"}, "speech": {"data": base64.b64encode(b"\0\0" * 800).decode(), "mime": "audio/L16;rate=16000"}}
		asked = []
		with mock.patch("onedesk.one_ai.run.make", side_effect=lambda job, text, reference=None, voice=None: asked.append((job, voice)) or making[reference.split()[-1]]), mock.patch("onedesk.one.apps.refuse_ai"), mock.patch("frappe.enqueue") as later:
			assert made.create("picture", folder, "A site at dawn", shape="wide")["name"] == "A site at dawn.png"
			assert made.create("speech", folder, "Gates open at seven.", voice="Puck", name="Gates")["name"] == "Gates.wav"
			assert made.create("music", folder, "Calm piano") == {"begun": True} and later.call_args.kwargs["kind"] == "music"
		assert asked == [("cloud_picture", None), ("cloud_voice", "Puck")]
		letter = upload._place(folder, None, {"file_name": "Site letter.rtf", "content": rb"{\rtf1 Site letter}"})["id"]
		plain = io.BytesIO()
		blank = PdfWriter()
		blank.add_blank_page(100, 100)
		blank.write(plain)
		sent = []
		frappe.cache.delete_value(f"one_cloud_office:{frappe.db.get_value('File', letter, 'content_hash')}")
		with mock.patch("onedesk.one.account.ask", side_effect=lambda endpoint, **said: sent.append((endpoint, said["name"])) or {"data": base64.b64encode(plain.getvalue()).decode(), "credits": 1}):
			office.preview(letter)
			assert frappe.local.response.filecontent.startswith(b"%PDF") and frappe.local.response.filename == "Site letter.pdf"
			for key in ("type", "filecontent", "filename"):
				frappe.local.response.pop(key, None)
			assert office.to_pdf(letter)["name"] == "Site letter.pdf"
		assert sent == [("onedesk.one_admin.proxy.office_convert", "Site letter.rtf")], "the second is the day's kept preview"
		frappe.cache.delete_value(f"one_cloud_office:{frappe.db.get_value('File', letter, 'content_hash')}")
		office.preview(letter)
		for key in ("type", "filecontent", "filename"):
			frappe.local.response.pop(key, None)
		assert len(sent) == 1, "a version's preview is kept with it, so viewing it again is free"
		assert next(one for one in api.listing(folder)["items"] if one["id"] == letter)["office"] == {"previewed": True}
		try:
			office.to_pdf(notes)
			raise AssertionError("a text file went to the office containers")
		except frappe.ValidationError:
			pass
		with as_user("yousef@one.test"):
			try:
				made.create("picture", folder, "Anything")
				raise AssertionError("a reader made a file in the library")
			except frappe.PermissionError:
				pass
		api.move(copied, ns.home())
		assert frappe.db.get_value("File", copied[0], "folder") == ns.home()
		attached = api.attach([drawing], "Project", VILLA)
		assert frappe.db.get_value("File", attached[0]["name"], "attached_to_name") == VILLA
		history.star([drawing])
		assert drawing in {one["id"] for one in api.listing(ns.STARRED)["items"]}
		history.star([drawing], 0)
		versions = history.versions(drawing)
		assert len(versions) == 1 and history.activity(drawing)["versions"]
		was = frappe.db.get_value("File", drawing, "file_url")
		history.restore(drawing, versions[0]["name"])
		assert frappe.db.get_value("File", drawing, "file_url") == versions[0]["url"]
		assert was in {one["url"] for one in history.versions(drawing)}
		assert {one["user"] for one in share.people(notes)["people"]} >= {"rania@one.test"}
		share.set_edit(notes, "rania@one.test", 1)
		share.unshare(notes, "rania@one.test")
		assert "rania@one.test" not in {one["user"] for one in share.people(notes)["people"]}
		share.share([notes], ["rania@one.test", "tariq@one.test"])
		assert {one["user"] for one in share.people(notes)["people"]} >= {"rania@one.test", "tariq@one.test"}
		api.delete([folder])
		assert frappe.db.get_value("File", folder, "one_deleted") == 1
		api.restore([folder])
		api.delete([folder])
		api.purge([folder])
		assert not frappe.db.exists("File", folder)
		api.delete(copied)
		api.empty_bin()
		assert not frappe.db.exists("File", copied[0])
		library.add(root, ["nadia@one.test"], "Reader")
		library.remove(root, "nadia@one.test")
		workshop = library.make("Workshop")["id"]
		assert frappe.db.get_value("File", workshop, "one_library") == 1

		seen = agent.open_file(drawing)
		assert seen.get("name") == demo.ELEVATIONS or demo.ELEVATIONS in str(seen)
		assert "Rania Sabbagh" in str(agent.who_can_see(drawing))
		biggest = agent.largest_files()
		assert demo.ELEVATIONS in {one["name"] for one in biggest["largest"]} and biggest["mine_bytes"] > 0

		address = dav.address(ns.MY)
		assert address["user_name"] == demo.PM
		kept = dav.passwords()
		assert [one.label for one in kept] == ["Office laptop"]
		made = dav.make_password("Home desktop")
		assert made["password"] and len(dav.passwords()) == 2
		dav.drop_password(next(one.name for one in dav.passwords() if one.label == "Home desktop"))
		_asked(path=f"{dav.MOUNT}/My Files/", method="PROPFIND", headers={"Depth": "1"})
		answer = dav.serve()
		assert answer.status_code == 207 and demo.NOTES.encode() in b"".join(answer.response)
	_unasked()
	with as_user("yousef@one.test"):
		assert demo.ELEVATIONS in {one["name"] for one in api.listing(root)["items"]}
		try:
			api.rename(drawing, "Mine now.pdf")
			raise AssertionError("a reader renamed a library's file")
		except frappe.PermissionError:
			pass
		try:
			api.color([root], "pink")
			raise AssertionError("a reader coloured a library's folder")
		except frappe.PermissionError:
			pass


@check
def onecloud_files_go_out_and_come_in():
	"""The villa's elevations through the link Samir made, a folder link
	with a password a customer sends photos into, and an invitation opened
	with the code mailed to Khalid. Al Noor answers Karim's request for its
	papers, and Karim reminds and closes it. Samir uploads straight to the
	store and through the workspace, opens a stored file, and connects a
	server folder. The store and the server are stood in for here."""
	from io import BytesIO
	from unittest import mock
	from urllib.parse import unquote

	from onedesk.one_demo import storage as demo
	from onedesk.one_cloud import api, file_requests, links, mounts, store, upload
	from onedesk.one_cloud import namespace as ns

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	drawing = frappe.db.get_value("File", {"folder": root, "file_name": demo.ELEVATIONS})
	with as_user(demo.PM):
		made = links.links(drawing)
		assert len(made) == 1 and made[0]["audience"] == links.ANYONE
		photos = api.make_folder(root, "Photos from Khalid")["id"]
		inbox = links.make(photos, allow_upload=1, password="villa-2026")
		invited = links.make(drawing, audience=links.INVITED, invitees=["khalid@mansour.example"])
	token = made[0]["url"].rsplit("/", 1)[-1]
	inbox_token = inbox["url"].rsplit("/", 1)[-1]
	invited_token = invited["url"].rsplit("/", 1)[-1]

	frappe.set_user("Guest")
	_asked(path="/", method="GET")
	sent = links.get(token)
	if sent is not None:
		assert sent.status_code == 302 and demo.ELEVATIONS in unquote(sent.location), "a stored file is sent from the store"
	else:
		assert frappe.local.response.filename == demo.ELEVATIONS and frappe.local.response.filecontent.startswith(b"%PDF")
	_asked()
	assert "said=wrong" in links.unlock(inbox_token, "guess").location
	_asked()
	links.unlock(inbox_token, "villa-2026")
	from PIL import Image

	photo = BytesIO()
	Image.new("RGB", (8, 8), "white").save(photo, "JPEG")
	photo.seek(0)
	_asked(data={"file": (photo, "west.jpg")}, cookies=_cookies())
	assert "said=sent_1" in links.put(inbox_token).location
	assert frappe.db.get_value("File", {"folder": photos, "file_name": "west.jpg"}, "owner") == demo.PM
	_asked()
	links.ask_code(invited_token, "khalid@mansour.example")
	link = frappe.db.get_value("Cloud Link", {"file": drawing, "audience": links.INVITED})
	code = frappe.cache.get_value(f"onecloud:code:{link}:khalid@mansour.example")
	_asked(cookies=_cookies())
	links.enter_code(invited_token, code)
	assert frappe.db.get_value("Cloud Link Invitee", {"parent": link}, "opened_on")
	frappe.set_user(demo.PM)
	links.drop(link)
	assert not links.live(invited_token)

	asked = frappe.db.get_value("Cloud File Request", {"title": "Al Noor papers for this year"})
	with as_user("karim@one.test"):
		said = file_requests.progress(asked)
		person = said["people"][0]
		assert person["email"] == demo.SUPPLIER and person["state"] != "Complete"
		assert file_requests.fields("Supplier") is not None
		again = file_requests.make(f"{ns.RECORDS}/Supplier/{frappe.db.get_value('Supplier', {})}", {"title": "Bank letter", "items": [{"label": "Bank letter", "required": 1}], "recipients": demo.SUPPLIER})
		assert again["links"] and again["name"]
	item = frappe.db.get_value("Cloud File Request Item", {"parent": asked, "label": "Trade licence"})
	frappe.set_user("Guest")
	_asked(data={"file": (BytesIO(demo._pdf("Trade licence 2026")), "licence.pdf")})
	assert "said=sent" in file_requests.send(person["url"].rsplit("/", 1)[-1], item).location
	with as_user("karim@one.test"):
		assert file_requests.progress(asked)["people"][0]["sent"]["Trade licence"]
		assert file_requests.remind(asked) == 1
		file_requests.close(asked)
		assert frappe.db.get_value("Cloud File Request", asked, "status") == "Closed"
	staff = frappe.db.get_value("Employee", {"user_id": ["is", "set"]}, ["name", "user_id"], as_dict=True)
	with as_user("Administrator"):
		assert file_requests.asked_at("Employee", staff.name) == staff.user_id
	with as_user("karim@one.test"):
		mine = file_requests.make(ns.MY, {"title": "Signed contract", "items": [{"label": "Signed contract", "required": 1}], "recipients": "yousef@one.test"})
	wanted = frappe.db.get_value("Cloud File Request Item", {"parent": mine["name"]})
	with as_user("yousef@one.test"):
		picked = frappe.get_doc({"doctype": "File", "file_name": "contract.pdf", "content": demo._pdf("Signed contract"), "is_private": 1}).insert()
		assert file_requests.guess(wanted, request=mine["name"], file_url=picked.file_url) == {}
		file_requests.send_mine(mine["name"], wanted, picked.file_url)
		assert not frappe.db.exists("File", picked.name)
	with as_user("karim@one.test"):
		assert file_requests.progress(mine["name"])["people"][0]["sent"]["Signed contract"]

	where = "https://r2.example.com/put"
	with as_user(demo.PM), mock.patch("onedesk.one_cloud.store.enabled", return_value=True), mock.patch(
		"onedesk.one.account.put_url", return_value={"url": where}
	), mock.patch("onedesk.one_cloud.store.signed", return_value="https://r2.example.com/get"), mock.patch(
		"onedesk.one_cloud.upload.requests.get", return_value=mock.Mock(status_code=206)
	):
		tickets = upload.begin(root, [{"name": demo.ELEVATIONS, "size": 900}, {"name": "Door schedule.pdf", "size": 400}])
		assert tickets["direct"] and tickets["existing"] == [demo.ELEVATIONS]
		placed = upload.done(tickets["tickets"][1]["token"])
		for token, who in ((tickets["tickets"][1]["token"], demo.PM), (tickets["tickets"][0]["token"], "rania@one.test")):
			with as_user(who):
				try:
					upload.done(token)
				except frappe.ValidationError as e:
					assert "expired" in str(e), e
				else:
					raise AssertionError(f"{who} filed an upload with a ticket that was not theirs to use")
		stored = frappe.db.get_value("File", placed["id"], "file_url")
		assert store.is_stored(stored)
		assert store.fetch(store.key_of(stored)).status_code == 302
	with as_user(demo.PM):
		_asked(data={"file": (BytesIO(b"Window W03 sill packed."), "W03 note.txt")})
		placed = upload.here(ns.home())
		assert frappe.db.get_value("File", placed["id"], "file_name") == "W03 note.txt"

		held = {"drawings": None, "drawings/old.dwg": b"DWG"}
		with mock.patch("onedesk.one_cloud.mounts.connect", return_value=_Server(held)):
			server = mounts.save({"title": "Office NAS", "protocol": "WebDAV", "url": "https://nas.example.com/dav", "username": "samir", "password": "nas-pass"})["id"]
			assert mounts.settings(server)["values"]["title"] == "Office NAS"
			assert "drawings" in {one["name"] for one in api.listing(server)["items"]}
			response = mounts.get(f"{server}/drawings/old.dwg")
			assert response.get_data() == b"DWG"
			mounts.disconnect(server)
	_unasked()


@check
def onecloud_each_file_answers_to_its_people():
	"""What OneCloud lets each person do with what is not theirs. A stored
	file opens for whoever may read it and for anybody else is not there at
	all. What Samir shared with Rania she may copy out but not take, nor
	share on; a file of a record is shared with the record, and only with the
	team. A library keeps an owner, and only its owners say who is in it. A
	server is its maker's until an administrator shares it, and its password
	never leaves the workspace. Nobody finds by searching what they may not
	open, and nobody fills in a request after it is closed."""
	from unittest import mock

	from werkzeug.exceptions import NotFound

	from onedesk.one_demo import storage as demo
	from onedesk.one_cloud import api, file_requests, library, mounts, share, store
	from onedesk.one_cloud import namespace as ns

	notes = frappe.db.get_value("File", {"owner": demo.PM, "file_name": demo.NOTES})
	key = "demo/kept/site-visit.pdf"
	kept = frappe.get_doc({"doctype": "File", "file_name": "Site visit.pdf", "file_url": store.url_for(key), "is_private": 1, "folder": ns.home(demo.PM)})
	kept.owner = demo.PM
	kept.db_insert()
	with mock.patch("onedesk.one_cloud.store.signed", return_value="https://r2.example.com/get"):
		with as_user(demo.PM):
			assert store.fetch(key).status_code == 302
		with as_user("omar@one.test"):
			try:
				store.fetch(key)
			except NotFound:
				pass
			else:
				raise AssertionError("a stranger opened a private file, or was told it was there")

	with as_user("rania@one.test"):
		try:
			share.share([notes], ["tariq@one.test"])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania shared on what she may only read")
	with as_user(demo.PM):
		share.set_edit(notes, "rania@one.test", 1)
	with as_user("rania@one.test"):
		try:
			api.move([notes], ns.home())
		except frappe.ValidationError as e:
			assert "Copy it instead" in str(e), e
		else:
			raise AssertionError("Rania took Samir's notes into her own files")
		copied = api.copy([notes], ns.home())
		assert frappe.db.get_value("File", copied[0], "file_url") == frappe.db.get_value("File", notes, "file_url"), "a copy names the same bytes"
	cover = frappe.db.get_value("File", {"attached_to_doctype": "Project", "attached_to_name": VILLA, "is_folder": 0})
	with as_user(demo.PM):
		for nodes, users, said in (([notes], ["probe@example.com"], "Only people on the team"), ([cover], ["rania@one.test"], "Share the record instead")):
			try:
				share.share(nodes, users)
			except frappe.ValidationError as e:
				assert said in str(e), e
			else:
				raise AssertionError(said)

	root = frappe.db.get_value("File", {"one_library": 1, "file_name": demo.LIBRARY})
	with as_user("yousef@one.test"):
		try:
			library.add(root, ["nadia@one.test"])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a reader added somebody to a library")
	with as_user(demo.PM):
		try:
			library.remove(root, demo.PM)
		except frappe.ValidationError as e:
			assert "last owner" in str(e), e
		else:
			raise AssertionError("a library was left without an owner")

	with as_user(demo.PM), mock.patch("onedesk.one_cloud.mounts.connect", return_value=_Server({})):
		server = mounts.save({"title": "Office NAS", "protocol": "WebDAV", "url": "https://nas.example.com/dav", "username": "samir", "password": "nas-pass"})["id"]
		assert "password" not in mounts.settings(server)["values"]
		try:
			mounts.save({"shared": 1}, name=mounts.split(server)[0])
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("a server was shared with everyone by somebody who is not an administrator")
	with as_user("rania@one.test"):
		assert server not in {one["id"] for one in mounts.visible()}
	with as_user(OWNER), mock.patch("onedesk.one_cloud.mounts.connect", return_value=_Server({})):
		mounts.save({"shared": 1}, name=mounts.split(server)[0])
	with as_user("rania@one.test"):
		assert server in {one["id"] for one in mounts.visible()}

	with as_user("yousef@one.test"):
		found = {one["id"] for one in api.listing(ns.ROOT, search="visit", everywhere=1)["items"]}
		assert notes not in found and kept.name not in found, found

	asked = frappe.db.get_value("Cloud File Request", {"title": "Al Noor papers for this year"})
	with as_user("karim@one.test"):
		person = file_requests.progress(asked)["people"][0]
		file_requests.close(asked)
	item = frappe.db.get_value("Cloud File Request Item", {"parent": asked, "label": "Trade licence"})
	frappe.set_user("Guest")
	from io import BytesIO

	_asked(data={"file": (BytesIO(demo._pdf("Trade licence 2026")), "licence.pdf")})
	assert "said=closed" in file_requests.send(person["url"].rsplit("/", 1)[-1], item).location
