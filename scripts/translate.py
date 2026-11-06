"""Translate in context: every new string with where it is shown, what is said
around it, and the glossary's words for the terms it uses.

Run with the bench's Python, after `bench generate-pot-file --app onedesk`:

    ../../env/bin/python scripts/translate.py todo > /tmp/todo.json
    (fill each entry's "ar" and "de")
    ../../env/bin/python scripts/translate.py apply /tmp/todo.json
    bench compile-po-to-mo --app onedesk

`todo` lists only what nobody translates yet: a string frappe, erpnext or hrms
already translate is left to theirs. `apply` writes what is filled in and
refuses, per language, a translation whose placeholders differ from the
English or that says a glossary term another way.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from babel.messages.pofile import read_po, write_po

sys.path.insert(0, str(Path(__file__).resolve().parent))

import glossary  # noqa: E402

LOCALE = glossary.LOCALE
APPS = LOCALE.parents[2]
UPSTREAM = ("frappe", "erpnext", "hrms")
LANGS = ("ar", "de")
NEAR = 3
PLACEHOLDER = re.compile(r"\{[^{}]*\}|%\(?\w*\)?[sd]")


def load(path: Path):
	with path.open("rb") as f:
		return read_po(f)


def upstream(lang: str) -> set[str]:
	said = set()
	for app in UPSTREAM:
		path = APPS / app / app / "locale" / f"{lang}.po"
		if path.exists():
			said |= {m.id for m in load(path) if m.id and m.string}
	return said


def kind(message) -> str:
	"""What the string is, as the POT says it ("Label of a Data field…"), or
	the file it is in when the POT says nothing."""
	if message.auto_comments:
		return " ".join(message.auto_comments)
	where = message.locations[0][0] if message.locations else ""
	return {".py": "Python message", ".js": "desk script", ".vue": "island screen", ".html": "page"}.get(Path(where).suffix, where)


def neighbours(pot) -> dict[str, list[str]]:
	"""For each string, the strings next to it in the same file."""
	by_file = defaultdict(list)
	for m in pot:
		if m.id:
			for path, line in m.locations:
				by_file[path].append((line or 0, m.id))
	near = defaultdict(list)
	for said in by_file.values():
		said.sort()
		ids = [one for _, one in said]
		for i, one in enumerate(ids):
			for other in ids[max(0, i - NEAR) : i] + ids[i + 1 : i + 1 + NEAR]:
				if other != one and other not in near[one]:
					near[one].append(other)
	return near


def todo() -> None:
	pot = load(LOCALE / "main.pot")
	ours = {lang: {(m.id, m.context): m.string for m in load(LOCALE / f"{lang}.po") if m.id} for lang in LANGS}
	theirs = {lang: upstream(lang) for lang in LANGS}
	near = neighbours(pot)
	out = []
	for m in pot:
		if not m.id or not isinstance(m.id, str):
			continue
		needed = [lang for lang in LANGS if not ours[lang].get((m.id, m.context)) and (m.context or m.id not in theirs[lang])]
		if not needed:
			continue
		out.append({
			"msgid": m.id,
			**({"context": m.context} if m.context else {}),
			"kind": kind(m),
			"where": [path for path, _ in m.locations][:3],
			"near": [{"en": one, "ar": ours["ar"].get((one, None), "")} for one in near[m.id][: NEAR * 2]],
			"glossary": {row["term"]: {"ar": row["ar"], "de": row["de"], "note": row["note"]} for row in glossary.found(m.id)},
			**{lang: "" for lang in needed},
		})
	json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
	print(f"\n{len(out)} to translate", file=sys.stderr)


def apply(path: str) -> None:
	entries = json.loads(Path(path).read_text(encoding="utf-8"))
	pot = load(LOCALE / "main.pot")
	refused = []
	for lang in LANGS:
		po_path = LOCALE / f"{lang}.po"
		po = load(po_path)
		for entry in entries:
			msgid, context, said = entry["msgid"], entry.get("context"), (entry.get(lang) or "").strip()
			if not said:
				continue
			source = pot.get(msgid, context=context)
			if source is None:
				refused.append(f"{lang}: not in the POT: {msgid[:70]}")
				continue
			if sorted(PLACEHOLDER.findall(msgid)) != sorted(PLACEHOLDER.findall(said)):
				refused.append(f"{lang}: placeholders differ: {msgid[:70]}")
				continue
			missed = glossary.missed(msgid, said, lang)
			if missed:
				refused.append(f"{lang}: says {', '.join(missed)} another way: {msgid[:70]} → {said[:70]}")
				continue
			there = po.get(msgid, context=context)
			if there is not None:
				there.string = said
			else:
				po.add(msgid, said, locations=source.locations, auto_comments=source.auto_comments, context=context)
		for m in list(po):
			if m.id and pot.get(m.id, context=m.context) is None:
				po.delete(m.id, context=m.context)
		with po_path.open("wb") as f:
			write_po(f, po, sort_output=True, ignore_obsolete=True, width=None)
	print("\n".join(refused) or "all written")
	if refused:
		sys.exit(1)


if __name__ == "__main__":
	if sys.argv[1:2] == ["todo"]:
		todo()
	elif sys.argv[1:2] == ["apply"] and len(sys.argv) == 3:
		apply(sys.argv[2])
	else:
		sys.exit(__doc__)
