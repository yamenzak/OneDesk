"""One word for one thing in Arabic and German (onedesk/locale/glossary.csv,
scripts/glossary.py).

A new translation that says a glossary term another way fails here. What was
already wrong when the glossary came in is listed in glossary_debt.json and
cleared screen by screen in the final checks; that list may only shrink, so a
string fixed is a line taken out of it in the same commit.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import glossary


def wordless(rows) -> list[str]:
	"""The terms with a scope other than label or any, or no Arabic. Pure."""
	return [row["term"] for row in rows if row["scope"] not in ("label", "any") or not row["ar"]]


def test_every_term_has_its_words():
	assert not wordless(glossary.terms())


def test_a_new_translation_keeps_the_glossary():
	new = sorted(glossary.wrong() - glossary.debt())
	cat = {lang: glossary.catalogue(lang) for lang in ("ar", "de")}
	lines = [
		f"  {lang}: {msgid!r} → {cat[lang][msgid]!r} (says {', '.join(glossary.missed(msgid, cat[lang][msgid], lang))} another way)"
		for lang, msgid in new
	]
	assert not lines, "Use the glossary's word (onedesk/locale/glossary.csv):\n" + "\n".join(lines)


def test_the_debt_only_shrinks():
	cleared = sorted(glossary.debt() - glossary.wrong())
	assert not cleared, (
		"Fixed or gone, so take these out of onedesk/locale/glossary_debt.json:\n"
		+ "\n".join(f"  {lang}: {msgid!r}" for lang, msgid in cleared)
	)


def test_the_glossary_rules_catch_their_examples():
	assert wordless([{"term": "Save", "scope": "verb", "ar": "حفظ"}, {"term": "Add", "scope": "label", "ar": ""}]) == ["Save", "Add"]
	assert not wordless([{"term": "Add", "scope": "label", "ar": "إضافة"}])
	assert glossary.missed("Employee", "عامل", "ar") == ["Employee"]
	assert not glossary.missed("Employee", "الموظف", "ar")
	wrong, debt = {("ar", "Employee"), ("de", "Save")}, {("de", "Save"), ("de", "Fixed")}
	assert wrong - debt == {("ar", "Employee")} and debt - wrong == {("de", "Fixed")}
