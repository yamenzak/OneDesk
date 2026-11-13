"""One word for one thing, in Arabic and German: onedesk/locale/glossary.csv.

A term is matched in the English as written, Title Case, as a whole word: the
label `Approve`, the heading `Leave Application`, "the Workspace's". A term
scoped `label` (the verbs) is matched only in a string of four words or fewer,
which is a button, a label or a heading; in a sentence the verb is free to take
whatever form the sentence needs.

A translation keeps the term when it contains one of its forms. The forms are
the word's own family (موظف, الموظف, موظفين), never a synonym, so a string that
says وافق where the glossary says اعتماد is caught. Arabic is compared without
its vowel marks and with every alef as one; German without case.

Pure: reads files, imports nothing of frappe's.
"""

import csv
import json
import re
from functools import cache
from pathlib import Path

LOCALE = Path(__file__).resolve().parent.parent / "onedesk" / "locale"
GLOSSARY = LOCALE / "glossary.csv"
DEBT = LOCALE / "glossary_debt.json"
LABEL_WORDS = 4

MARKS = re.compile("[ً-ْٰـ]")
ALEF = str.maketrans("أإآٱ", "اااا")
# Where the English word is not the term: "Leave empty" is the verb, not time
# off; "Draft a reply" is writing, not a draft; "No Show" is an absence; and a
# "Board Item" is a thing on a board, not a stock item; "Act on" is reacting,
# not the agents' level. Cut out before matching.
NOT_THE_TERM = {
	"Leave": re.compile(r"\bLeave (empty|blank|unchecked|it|this|as|out|the|them|a|an|both|all)\b", re.I),
	"Draft": re.compile(r"\bDraft (a|an|the|it|from|with|one|my|your|our)\b"),
	"Share": re.compile(r"\bShare (Transfer|Ledger|Type|Balance|Holder|Allocation|of)\b"),
	"Shift": re.compile(r"\bShift\+"),
	"Report": re.compile(r"\bReport (any|it|a|an|the|this|to)\b"),
	"Show": re.compile(r"\bNo Show\b"),
	"Act": re.compile(r"\bAct (on|After|as|upon)\b"),
	"Item": re.compile(r"(?<!\w)(?!(?:Stock|Sales|Purchase|Service|Variant|Template|New|Each|Every|Any|One|No|All|Your|This|Add|Find|View|Edit) )[A-Z][a-z]+ Items?\b"),
}
NOT_THE_TERM["Items"] = NOT_THE_TERM["Item"]


def plain(text: str, lang: str) -> str:
	if lang == "ar":
		return MARKS.sub("", text).translate(ALEF).replace("ى", "ي")
	return text.lower()


@cache
def terms() -> list[dict]:
	with GLOSSARY.open(encoding="utf-8") as f:
		rows = list(csv.DictReader(f))
	for row in rows:
		row["pattern"] = re.compile(r"(?<![\w-])" + re.escape(row["term"]) + r"(?![\w-])")
		for lang in ("ar", "de"):
			said = row[f"{lang}_forms"] or row[lang]
			forms = [plain(one.strip(), lang).removeprefix("ال") for one in said.split("|") if one.strip()]
			# شركة is شركت before a suffix: شركتك, شركتنا.
			forms += [one[:-1] + "ت" for one in forms if lang == "ar" and one.endswith("ة")]
			row[f"{lang}_match"] = forms
	# The longest first, so "Job Opening" is looked for before a shorter term inside it.
	return sorted(rows, key=lambda row: -len(row["term"]))


def found(msgid: str) -> list[dict]:
	"""The glossary's terms this English string uses."""
	short = len(msgid.split()) <= LABEL_WORDS
	hits = []
	for row in terms():
		if row["term"] not in msgid or (row["scope"] == "label" and not short):
			continue
		skip = NOT_THE_TERM.get(row["term"])
		if row["pattern"].search(skip.sub(" ", msgid) if skip else msgid):
			hits.append(row)
	return hits


def missed(msgid: str, msgstr: str, lang: str) -> list[str]:
	"""The terms msgid uses that msgstr does not say the glossary's way."""
	if not msgstr:
		return []
	said = plain(msgstr, lang)
	return [
		row["term"]
		for row in found(msgid)
		if row[f"{lang}_match"] and not any(one in said for one in row[f"{lang}_match"])
	]


def debt() -> set[tuple[str, str]]:
	"""(lang, msgid) already wrong when the glossary came in, cleared screen by
	screen in the final checks. The file only shrinks."""
	if not DEBT.exists():
		return set()
	return {(lang, msgid) for lang, msgid in json.loads(DEBT.read_text(encoding="utf-8"))}


ENTRY = re.compile(r'^msgid ((?:"[^\n]*"\n)+)msgstr ((?:"[^\n]*"\n?)+)', re.M)
QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')


def catalogue(lang: str) -> dict[str, str]:
	"""Our own msgid -> msgstr for one language, with no babel needed."""
	text = (LOCALE / f"{lang}.po").read_text(encoding="utf-8")
	out = {}
	for match in ENTRY.finditer(text):
		msgid = "".join(QUOTED.findall(match.group(1)))
		if msgid:
			out[unescape(msgid)] = unescape("".join(QUOTED.findall(match.group(2))))
	return out


def unescape(text: str) -> str:
	return text.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


@cache
def wrong() -> frozenset[tuple[str, str]]:
	"""Every (lang, msgid) whose translation misses a glossary term."""
	return frozenset((lang, msgid) for lang in ("ar", "de") for msgid, msgstr in catalogue(lang).items() if missed(msgid, msgstr, lang))
