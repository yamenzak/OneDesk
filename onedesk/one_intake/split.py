"""Where one document ends and the next begins, in a scan of several.

Companies scan the day's post as one PDF. Before anything reads it as a
letter, it is cut into its letters. The signals are ones a person would use:
a blank page or a separator sheet between them, and page numbering that
starts again. A vision model marks the rest when it reads the pages. Pure.
"""

import re

#: A page with fewer characters than this is blank: an empty back, a scanner's
#: speck read as a letter.
BLANK = 6

SEPARATOR = re.compile(
	r"\b(trennblatt|trennseite|separator sheet|document separator|patch ?(?:t|ii|2)|séparateur|scheidingsblad)\b",
	re.IGNORECASE,
)

#: "Seite 2 von 3", "Page 2 of 3", "Pagina 2 di 3", "2/3" alone on a line.
NUMBERED = re.compile(
	r"(?:seite|page|blatt|pagina|página|sayfa|صفحة)\s*(\d{1,3})\s*(?:/|von|of|de|di|sur|van|من)\s*(\d{1,3})"
	r"|^\s*(\d{1,3})\s*/\s*(\d{1,3})\s*$",
	re.IGNORECASE | re.MULTILINE,
)


def blank(text: str) -> bool:
	return len("".join((text or "").split())) < BLANK


def separator(text: str) -> bool:
	return len(text or "") < 300 and bool(SEPARATOR.search(text or ""))


def numbered(text: str) -> tuple[int, int] | None:
	"""Which page of how many a page says it is, where it says so."""
	edges = (text or "")[:400] + "\n" + (text or "")[-400:]
	for found in NUMBERED.finditer(edges):
		page, of = (int(one) for one in (found.group(1) or found.group(3), found.group(2) or found.group(4)))
		if 1 <= page <= of <= 500:
			return page, of
	return None


def documents(texts: list[str], starts: set[int] | None = None) -> list[list[int]]:
	"""The pages of each document, in order, by index. Blank backs and
	separator sheets are left out. `starts` are pages a model said begin a new
	document."""
	starts = set(starts or ())
	backs = _duplex(texts)
	out: list[list[int]] = []
	current: list[int] = []
	cut = False
	for index, text in enumerate(texts):
		if separator(text) or (blank(text) and not backs):
			cut = True
			continue
		if blank(text):
			continue
		said = numbered(text)
		ended = bool(current) and _ended(texts[current[-1]])
		if current and (cut or index in starts or (said and said[0] == 1) or ended):
			out.append(current)
			current = []
		current.append(index)
		cut = False
	if current:
		out.append(current)
	return out


def _ended(text: str) -> bool:
	said = numbered(text)
	return bool(said) and said[0] == said[1]


def _duplex(texts: list[str]) -> bool:
	"""Whether blank pages are the empty backs of a two-sided scan rather
	than gaps between documents: most second sides blank."""
	backs = texts[1::2]
	if len(backs) < 3:
		return False
	return sum(1 for text in backs if blank(text) and not separator(text)) >= len(backs) * 2 / 3
