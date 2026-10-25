"""Declarations plus documents into one rendered page, and the version that
names it: `revision.hash`. A bumped revision makes every workspace agree again,
and the hash moves the moment any clause does.
"""

import hashlib

from .documents import DOCUMENTS, PARTY, SECTIONS
from .registry import clauses_for, subprocessor_rows

MODULES = (
	"one",
	"one_admin",
	"one_ai",
	"one_storage",
	"one_mail",
	"one_intake",
	"one_hr",
	"one_calendar",
	"one_task",
	"one_project",
	"one_inventory",
	"one_crm",
	"one_book",
	"one_studio",
)

_loaded = False


def _load() -> None:
	"""Import every module's `legal.py`, once.

	A module with no `legal.py` is not an error: most of what a module does
	needs nothing said about it, and a mandatory empty file is a file nobody
	reads.
	"""
	global _loaded
	if _loaded:
		return
	_loaded = True

	import importlib

	importlib.import_module("onedesk.one_legal.legal")
	for module in MODULES:
		try:
			importlib.import_module(f"onedesk.{module}.legal")
		except ModuleNotFoundError as missing:
			if missing.name != f"onedesk.{module}.legal":
				raise


def documents() -> list[dict]:
	"""Every document, with its version, in the order they are shown."""
	_load()
	return [
		{"key": key, **{k: v for k, v in one.items()}, "version": version_of(key)}
		for key, one in DOCUMENTS.items()
	]


def text_of(key: str) -> str:
	"""The document as plain text: what the hash is taken over.

	Plain rather than HTML, so that changing a heading level or a `<p>` does not
	invalidate every acceptance in the fleet. What is agreed to is the words.
	"""
	_load()
	if key not in DOCUMENTS:
		raise KeyError(key)

	lines = [DOCUMENTS[key]["title"], ""]
	for section, heading in SECTIONS[key]:
		found = clauses_for(key, section)
		rows = subprocessor_rows() if (key, section) == ("subprocessors", "list") else []
		if not found and not rows:
			continue
		lines += [heading, ""]
		for one in found:
			if one["heading"]:
				lines.append(one["heading"])
			lines += [one["body"], ""]
		for row in rows:
			lines.append(
				f"{row['name']} — {row['safeguard']}"
				+ "".join(f" — {use['purpose']} ({use['data']}) in {use['where']}" for use in row["uses"])
			)
		if rows:
			lines.append("")
	return "\n".join(lines).strip() + "\n"


def version_of(key: str) -> str:
	"""`revision.hash` — see this module's docstring."""
	digest = hashlib.sha256(text_of(key).encode("utf-8")).hexdigest()[:8]
	return f"{DOCUMENTS[key]['revision']}.{digest}"


def render(key: str) -> dict:
	"""One document, ready to show: title, version, and HTML."""
	_load()
	if key not in DOCUMENTS:
		raise KeyError(key)

	one = DOCUMENTS[key]
	parts = [f"<h1>{_esc(one['title'])}</h1>", f'<p class="summary">{_esc(one["summary"])}</p>']

	for section, heading in SECTIONS[key]:
		found = clauses_for(key, section)
		rows = subprocessor_rows() if (key, section) == ("subprocessors", "list") else []
		if not found and not rows:
			continue
		parts.append(f"<h2>{_esc(heading)}</h2>")
		for clause in found:
			if clause["heading"]:
				parts.append(f"<h3>{_esc(clause['heading'])}</h3>")
			parts.append(f"<p>{_esc(clause['body'])}</p>")
		if rows:
			parts.append(_table(rows))

	return {
		"key": key,
		"title": one["title"],
		"summary": one["summary"],
		"audience": one["audience"],
		"version": version_of(key),
		"revision": one["revision"],
		"party": PARTY,
		"html": "\n".join(parts),
	}


def of_module(module: str) -> dict:
	"""What one module adds to the agreements (docs/READY.md, mechanism 6):
	its clauses under the document and section each sits in, and the
	companies it sends data to with what each gets and where. Read from the
	registry the documents are assembled from, so the module's Legal tab and
	the agreements can't disagree."""
	_load()
	companies = [
		{**row, "uses": [use for use in row["uses"] if use["module"] == module]}
		for row in subprocessor_rows()
		if any(use["module"] == module for use in row["uses"])
	]
	found = []
	for key, one in DOCUMENTS.items():
		sections = []
		for section, heading in SECTIONS[key]:
			mine = [clause for clause in clauses_for(key, section) if clause["module"] == module]
			if mine:
				sections.append(
					{
						"section": section,
						"heading": heading,
						"clauses": [{"key": c["key"], "heading": c["heading"], "body": c["body"]} for c in mine],
					}
				)
		lists = key == "subprocessors" and bool(companies)
		if sections or lists:
			found.append(
				{
					"key": key,
					"title": one["title"],
					"revision": one["revision"],
					"version": version_of(key),
					"sections": sections,
					"companies": lists,
				}
			)
	return {"module": module, "documents": found, "companies": companies}


def stamp(module: str) -> str:
	"""Each agreement a module writes into, with a hash of the module's own
	part of it: `privacy 1a2b3c4d, ai …`. Another module's clauses don't move
	it. A version of the module records it, so a change to what the module
	adds to the agreements shows as a new version that has to say so."""
	part = of_module(module)
	out = []
	for one in part["documents"]:
		mine = repr((one["sections"], part["companies"] if one["companies"] else []))
		out.append(f"{one['key']} {hashlib.sha256(mine.encode('utf-8')).hexdigest()[:8]}")
	return ", ".join(out)


def _table(rows: list[dict]) -> str:
	"""The subprocessor list, as a table rather than as prose.

	Five columns because that is what a reader checking one is looking for:
	who, what for, what they get, where it sits, and what makes it lawful.
	"""
	head = (
		"<table><thead><tr><th>Company</th><th>What for</th>"
		"<th>What they receive</th><th>Where</th><th>Safeguard</th>"
		"</tr></thead><tbody>"
	)
	body = []
	for row in rows:
		purposes = "<br>".join(
			f"{_esc(use['purpose'])} <em>({_esc(use['module'])})</em>" for use in row["uses"]
		)
		data = "<br>".join(_esc(use["data"]) for use in row["uses"])
		where = "<br>".join(_esc(use["where"]) for use in row["uses"])
		name = _esc(row["name"])
		if row["url"]:
			name = f'<a href="{_esc(row["url"])}" rel="noopener">{name}</a>'
		body.append(
			f"<tr><td>{name}</td><td>{purposes}</td><td>{data}</td>"
			f"<td>{where}</td><td>{_esc(row['safeguard'])}</td></tr>"
		)
	return head + "".join(body) + "</tbody></table>"


def _esc(text: str) -> str:
	return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
