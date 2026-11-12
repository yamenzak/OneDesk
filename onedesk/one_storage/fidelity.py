"""What OneWorkbook or OneWriter would drop from an office file it saves over,
read from the file's parts when it is opened. The editors keep values,
formulas, number formats and merges (a workbook), and text, headings, lists,
tables and pictures (a document); everything listed here is not kept. While
a file has something on its list, the editor does not save over it by itself
(one_sheet/api.py and one_doc/word.py write_back)."""

import io
import re
import zipfile

from frappe import _

MACROS = ("xlsm", "xltm", "xlam", "docm", "dotm")
OLDER = ("xls",)


def _parts(content: bytes) -> dict | None:
	try:
		with zipfile.ZipFile(io.BytesIO(content)) as held:
			return {name: held.read(name) for name in held.namelist() if name.endswith((".xml", ".bin")) or "/media/" in name or "/embeddings/" in name}
	except (zipfile.BadZipFile, OSError, ValueError):
		return None


def _any(parts: dict, prefix: str) -> bool:
	return any(name.startswith(prefix) for name in parts)


def _within(parts: dict, prefix: str, pattern: bytes) -> bool:
	found = re.compile(pattern)
	return any(name.startswith(prefix) and found.search(body) for name, body in parts.items())


def _counted(styles: bytes, tag: bytes) -> int:
	found = re.search(rb"<(?:\w+:)?" + tag + rb"\b[^>]*\bcount=\"(\d+)\"", styles or b"")
	return int(found.group(1)) if found else 0


def workbook(content: bytes, formatting: bool = True) -> list[str]:
	"""What OneWorkbook drops from an Excel file: each by its code, in the
	order labels() lists them. `formatting` counts fonts, colours and borders,
	which a workbook of One's own keeps from its own copy. Pure."""
	parts = _parts(content)
	if parts is None:
		return []
	out = []
	if "xl/vbaProject.bin" in parts:
		out.append("macros")
	if _any(parts, "xl/comments") or _any(parts, "xl/threadedComments/"):
		out.append("comments")
	if _any(parts, "xl/charts/"):
		out.append("charts")
	if _any(parts, "xl/pivotTables/") or _any(parts, "xl/slicers/"):
		out.append("pivot_tables")
	if _any(parts, "xl/media/"):
		out.append("pictures")
	if _any(parts, "xl/tables/"):
		out.append("tables")
	if _within(parts, "xl/worksheets/", rb"<(?:\w+:)?dataValidation\b"):
		out.append("data_validation")
	if _within(parts, "xl/worksheets/", rb"<(?:\w+:)?conditionalFormatting\b"):
		out.append("conditional_formatting")
	if _any(parts, "xl/externalLinks/"):
		out.append("external_links")
	styles = parts.get("xl/styles.xml") or b""
	if formatting and (_counted(styles, b"fonts") > 1 or _counted(styles, b"fills") > 2 or _counted(styles, b"borders") > 1):
		out.append("formatting")
	return out


def document(content: bytes, messages: list | None = None, built: tuple = (), formatting: bool = True) -> list[str]:
	"""What OneWriter drops from a Word file: each by its code, from its parts
	and from what the reader said while reading it (`messages`, mammoth's,
	of which only styles it did not know matter, less those in `built`, the
	styles One writes itself). `formatting` counts fonts, sizes and colours,
	left out for a document of One's own, which never had them. Pure."""
	parts = _parts(content)
	if parts is None:
		return []
	body = parts.get("word/document.xml") or b""
	out = []
	if "word/vbaProject.bin" in parts:
		out.append("macros")
	if re.search(rb"<w:comment\b", parts.get("word/comments.xml") or b""):
		out.append("comments")
	if re.search(rb"<w:(ins|del|moveFrom|moveTo)\b", body):
		out.append("tracked_changes")
	if _within(parts, "word/header", rb"<w:t[ >]|<w:drawing\b|<w:pict\b") or _within(parts, "word/footer", rb"<w:t[ >]|<w:drawing\b|<w:pict\b"):
		out.append("headers_and_footers")
	if re.search(rb"<w:(footnote|endnote)\b(?![^>]*w:type=)", (parts.get("word/footnotes.xml") or b"") + (parts.get("word/endnotes.xml") or b"")):
		out.append("footnotes")
	if _any(parts, "word/charts/"):
		out.append("charts")
	if re.search(rb"<w:txbxContent\b|<wps:wsp\b|<v:shape\b", body):
		out.append("text_boxes")
	if re.search(rb"<m:oMath\b", body):
		out.append("equations")
	if _any(parts, "word/embeddings/"):
		out.append("embedded_files")
	if re.search(rb"<w:hyperlink\b", body):
		out.append("links")
	if re.search(rb"<w:fldSimple\b|<w:instrText\b|<w:sdt\b", body):
		out.append("fields")
	if formatting and re.search(rb'<w:rFonts\b|<w:sz\b|<w:color w:val="(?!auto)|<w:highlight\b|<w:shd\b[^>]*w:fill="(?!auto|FFFFFF)', body):
		out.append("text_formatting")
	if any(_style_lost(one, built) for one in messages or []):
		out.append("styles")
	return out


def _style_lost(message, built: tuple) -> bool:
	said = getattr(message, "message", None) or str(message)
	found = re.match(r"Unrecognised (?:paragraph|run) style: (.*?) \(Style ID", said)
	return bool(found) and found.group(1) not in built and not found.group(1).startswith(("None", "Comment"))


def read_only(file_name: str, found: list[str]) -> str | None:
	"""Why an editor opens a file read-only: `macros` it would lose, or an
	`older` format it cannot save. None when it may save. Pure."""
	extension = (file_name or "").rsplit(".", 1)[-1].lower() if "." in (file_name or "") else ""
	if extension in MACROS or "macros" in (found or []):
		return "macros"
	if extension in OLDER:
		return "older"
	return None


def why_read_only(file_name: str, why: str) -> str:
	if why == "macros":
		return _("{0} has macros, so it opens read-only here. Open it in OneOS to edit it.").format(file_name)
	return _("{0} is in an older Excel format, so it opens read-only here. Open it in OneOS to edit it.").format(file_name)


def labels() -> dict:
	return {
		"macros": _("macros"),
		"comments": _("comments"),
		"tracked_changes": _("tracked changes"),
		"headers_and_footers": _("headers and footers"),
		"footnotes": _("footnotes"),
		"charts": _("charts"),
		"pivot_tables": _("pivot tables"),
		"pictures": _("pictures"),
		"tables": _("tables"),
		"data_validation": _("data validation"),
		"conditional_formatting": _("conditional formatting"),
		"external_links": _("links to other workbooks"),
		"formatting": _("fonts, colours and borders"),
		"text_formatting": _("fonts, sizes and colours"),
		"text_boxes": _("text boxes and shapes"),
		"equations": _("equations"),
		"embedded_files": _("embedded files"),
		"links": _("links"),
		"fields": _("fields such as a table of contents"),
		"styles": _("styles"),
	}


def named(found: list[str]) -> str:
	"""The list as a reader reads it: "comments, charts and pictures"."""
	from frappe.utils import comma_and

	said = labels()
	return comma_and([said.get(one, one) for one in found or []], add_quotes=False)


def dropping(file_name: str, found: list[str]) -> str:
	"""The line over an editor while saving over the file waits."""
	return _("Your changes are saved here. Saving them over {0} would drop its {1}.").format(file_name, named(found))
