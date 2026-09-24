"""Word, PowerPoint and OpenDocument files, read as the zips of XML they are.

Only the XML is read. Nothing in the file is run, so a macro in a document
stays a macro nobody executed. Pure.
"""

import io
import re
import zipfile

from onedesk.one_intake.readers import markup as m

#: Uncompressed, a document larger than this is somebody's attempt at a zip bomb.
LARGEST = 64 * 1024 * 1024

#: Where the words are, in reading order, for each kind.
WORD = ("word/header", "word/document.xml", "word/footnotes.xml", "word/footer")
SLIDES = re.compile(r"ppt/slides/slide(\d+)\.xml$")


def members(content: bytes) -> dict[str, bytes] | None:
	try:
		with zipfile.ZipFile(io.BytesIO(content)) as held:
			if sum(info.file_size for info in held.infolist()) > LARGEST:
				return None
			return {info.filename: held.read(info) for info in held.infolist() if info.filename.endswith(".xml")}
	except (zipfile.BadZipFile, OSError, RuntimeError):
		return None


def word(content: bytes) -> str | None:
	files = members(content)
	if not files or "word/document.xml" not in files:
		return None
	order = [name for prefix in WORD for name in sorted(files) if name.startswith(prefix)]
	return "\n".join(_paragraphs(files[name], "p", "t") for name in order).strip()


def slides(content: bytes) -> str | None:
	files = members(content)
	if not files:
		return None
	numbered = sorted(
		(int(found.group(1)), name) for name in files if (found := SLIDES.search(name))
	)
	if not numbered:
		return None
	return "\n\n".join(
		f"[Slide {number}]\n{_paragraphs(files[name], 'p', 't')}" for number, name in numbered
	).strip()


def opendocument(content: bytes) -> str | None:
	files = members(content)
	if not files or "content.xml" not in files:
		return None
	root = m.root(files["content.xml"])
	if root is None:
		return None
	lines = []
	for element in root.iter():
		name = m.local(element.tag)
		if name in ("p", "h"):
			lines.append("".join(element.itertext()).strip())
		elif name == "table-row":
			lines.append("\t".join("".join(cell.itertext()).strip() for cell in element if m.local(cell.tag) == "table-cell"))
	return "\n".join(line for line in lines if line).strip()


def _paragraphs(xml: bytes, paragraph: str, run: str) -> str:
	root = m.root(xml)
	if root is None:
		return ""
	out = []
	for element in root.iter():
		if m.local(element.tag) != paragraph:
			continue
		words = []
		for inner in element.iter():
			name = m.local(inner.tag)
			if name == run and inner.text:
				words.append(inner.text)
			elif name == "tab":
				words.append("\t")
			elif name in ("br", "cr"):
				words.append("\n")
		out.append("".join(words))
	return "\n".join(line for line in out if line.strip())
