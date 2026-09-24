"""Turning any file into text: stage 1 of Intake, without a model where one is
not needed.

`read` decides by what the file is, not only by what it is called, and says
what it could not do itself: a scan or a photo `needs` eyes, a recording
`needs` ears, a locked PDF `needs` a password. The pipeline supplies those.
Pure: nothing here touches a site.
"""

import io
import zipfile
from dataclasses import dataclass, field

from onedesk.one_intake import language, split
from onedesk.one_intake.readers import bank, card, einvoice, mail, office, pdf, sheet
from onedesk.one_intake.readers import markup as m

IMAGES = ("jpg", "jpeg", "png", "webp", "heic", "heif", "gif", "tif", "tiff", "bmp")
SOUNDS = ("mp3", "m4a", "wav", "ogg", "oga", "opus", "amr", "aac", "webm", "3gp")
PLAIN = ("txt", "md", "text", "log", "json", "rtf")
MT940 = ("sta", "940", "mt940")

#: What a zip may hold before it is somebody's attempt to stall a worker.
MOST_MEMBERS = 200
MOST_UNPACKED = 256 * 1024 * 1024


@dataclass
class Text:
	text: str = ""
	how: str = ""
	pages: list[str] = field(default_factory=list)
	structured: dict | None = None
	needs: str | None = None
	inner: list[dict] = field(default_factory=list)
	documents: list[list[int]] = field(default_factory=list)
	language: str | None = None


def extension(name: str) -> str:
	return (name or "").rsplit(".", 1)[-1].lower() if "." in (name or "") else ""


def read(name: str, content: bytes, password: str | None = None) -> Text:
	said = _read(name, content or b"", password)
	if said.text and not said.language:
		said.language = language.guess(said.text)
	return said


def _read(name: str, content: bytes, password: str | None) -> Text:
	ext = extension(name)
	if content.startswith(b"%PDF") or ext == "pdf":
		return _pdf(content, password)
	if ext in IMAGES:
		return Text(how="Image", needs="eyes")
	if ext in SOUNDS:
		return Text(how="Sound", needs="ears")
	if ext == "eml":
		return _mail(content)
	if ext in ("vcf", "vcard", "ics", "ical"):
		return _card(content)
	if ext in ("xls",):
		return _said(sheet.xls(content), "Sheet")
	if ext in ("csv", "tsv"):
		return _said(sheet.delimited(content), "Sheet")
	if ext in MT940:
		return _statement(bank.mt940(sheet.decoded(content)), sheet.decoded(content))
	if content.startswith(b"PK"):
		return _zipped(ext, content)
	if ext == "xml" or content.lstrip()[:5] == b"<?xml":
		return _xml(content)
	if ext in ("html", "htm"):
		return _said(mail.plain(sheet.decoded(content)), "Text")
	if ext in PLAIN:
		text = sheet.decoded(content)
		statement = bank.mt940(text)
		return _statement(statement, text) if statement else _said(text, "Text")
	if ext == "msg":
		return Text(how="Outlook message", needs="nothing")
	return Text(how="Unknown", needs="nothing")


def _said(text: str | None, how: str) -> Text:
	if text is None:
		return Text(how=how, needs="nothing")
	return Text(text=text.strip(), how=how)


def _pdf(content: bytes, password: str | None) -> Text:
	try:
		texts = pdf.pages(content, password)
		xml = pdf.embedded(content, password)
	except pdf.Locked:
		return Text(how="PDF", needs="password")
	except Exception:
		return Text(how="PDF", needs="nothing")
	invoice = einvoice.parse(xml) if xml else None
	if invoice:
		return Text(
			text=einvoice.described(invoice) + "\n\n" + "\n".join(texts),
			how="E-invoice",
			pages=texts,
			structured={"invoice": invoice},
		)
	if not pdf.has_text(texts):
		return Text(how="Scan", pages=texts, needs="eyes")
	return Text(text="\n\n".join(texts).strip(), how="PDF", pages=texts, documents=split.documents(texts))


def _xml(content: bytes) -> Text:
	invoice = einvoice.parse(content)
	if invoice:
		return Text(text=einvoice.described(invoice), how="E-invoice", structured={"invoice": invoice})
	statement = bank.camt(content)
	if statement:
		return _statement(statement, "")
	root = m.root(content)
	if root is None:
		return Text(how="XML", needs="nothing")
	return Text(text=" ".join(" ".join(root.itertext()).split()), how="XML")


def _statement(statement: dict | None, text: str) -> Text:
	if not statement:
		return _said(text, "Text")
	return Text(text=bank.described(statement), how="Bank statement", structured={"statement": statement})


def _card(content: bytes) -> Text:
	text = sheet.decoded(content)
	cards, events = card.vcards(text), card.events(text)
	if not cards and not events:
		return Text(how="Card", needs="nothing")
	return Text(
		text=card.described(cards, events),
		how="Contact card" if cards else "Invitation",
		structured={key: value for key, value in (("cards", cards), ("events", events)) if value},
	)


def _mail(content: bytes) -> Text:
	said = mail.message(content)
	return Text(
		text=f"{said['subject']}\n\n{said['text']}".strip(),
		how="Mail",
		structured={"mail": {key: value for key, value in said.items() if key not in ("text", "attachments")}},
		inner=[{"name": one["name"], "content": one["content"]} for one in said["attachments"]],
	)


def _zipped(ext: str, content: bytes) -> Text:
	if ext in ("docx", "docm", "dotx"):
		return _said(office.word(content), "Word")
	if ext in ("pptx", "ppsx"):
		return _said(office.slides(content), "Slides")
	if ext in ("odt", "ods", "odp"):
		return _said(office.opendocument(content), "OpenDocument")
	if ext in ("xlsx", "xlsm"):
		return _said(sheet.xlsx(content), "Sheet")
	found = office.members(content) or {}
	if "word/document.xml" in found:
		return _said(office.word(content), "Word")
	if "xl/workbook.xml" in found:
		return _said(sheet.xlsx(content), "Sheet")
	if "content.xml" in found and "mimetype" in _names(content):
		return _said(office.opendocument(content), "OpenDocument")
	return _archive(content)


def _names(content: bytes) -> list[str]:
	try:
		with zipfile.ZipFile(io.BytesIO(content)) as held:
			return held.namelist()
	except (zipfile.BadZipFile, OSError):
		return []


def _archive(content: bytes) -> Text:
	"""A zip's files, each to be read as a document of its own."""
	try:
		with zipfile.ZipFile(io.BytesIO(content)) as held:
			infos = [info for info in held.infolist() if not info.is_dir() and not info.filename.startswith("__MACOSX/")]
			if len(infos) > MOST_MEMBERS or sum(info.file_size for info in infos) > MOST_UNPACKED:
				return Text(how="Archive", needs="nothing")
			inner = [{"name": info.filename.rsplit("/", 1)[-1], "content": held.read(info)} for info in infos]
	except (zipfile.BadZipFile, OSError, RuntimeError):
		return Text(how="Archive", needs="nothing")
	return Text(text="\n".join(one["name"] for one in inner), how="Archive", inner=inner)
