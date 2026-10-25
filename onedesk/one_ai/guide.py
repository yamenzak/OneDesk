"""How One works, answered from each module's own README.

`how_to` hands the model the sections that match, read only down to
`## Under the hood`, and tells it to answer from those alone.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from onedesk.one_ai import memory

APP = Path(__file__).resolve().parent.parent

BACKSTAGE = "## Under the hood"

ASKING = frozenset(
	"how what who whom why when where which the can could was were are does did get "
	"out over see happen about will would should there their this that with from into".split()
)

MOST = 3
LONGEST = 1800


def how_to(
	question: Annotated[
		str,
		"The question in English, in the words the documentation would use — "
		"translate it first if the person asked in another language.",
	],
) -> dict:
	"""How One works and how to do something in it — where a screen is, what a
	setting does, what happens after a button is pressed, why something was
	refused — from One's own documentation of each module. Use it for any
	"how do I", "where is", "what does" or "why can't I" question about the
	product rather than about this workspace's records. Answer from what it
	returns alone, and name the section each part of the answer comes from."""
	words = [word for word in memory._words(question) if word not in ASKING]
	found = ranked(_sections(_readmes()), words)[:MOST]
	if not found:
		return {
			"sections": [],
			"next": "One's documentation does not cover this. Say so, and suggest asking the workspace's administrator.",
		}
	return {
		"sections": [{"source": one["path"], "text": plain(one["text"])[:LONGEST]} for one in found],
		"next": "Answer from these sections alone, in the person's language. After the answer, name the "
		"section it came from, such as (OneHR › Clocking in). If they do not answer the question, say so.",
	}


def _readmes() -> tuple:
	"""What people read about each module, as (path, time it last changed),
	for the cache key: its README, or, for a module with an AGENTS.md, the
	pages of its docs/ (docs/READY.md, A module's folder)."""
	return tuple((str(one), one.stat().st_mtime) for one in manuals())


def manuals() -> list[Path]:
	found = []
	for readme in sorted(APP.glob("*/README.md")):
		found.append(readme)
	for agents in sorted(APP.glob("*/AGENTS.md")):
		found += sorted(path for path in (agents.parent / "docs").glob("*.md"))
	return found


@lru_cache(maxsize=4)
def _sections(readmes: tuple) -> tuple:
	found = []
	for path, _changed in readmes:
		found += split(page(Path(path)))
	return tuple(found)


def page(path: Path) -> str:
	"""A module's README as it is, or one page of its docs/ under the module's
	name: "# Out of Office" read as OneMail › Out of Office."""
	text = path.read_text(encoding="utf-8")
	if path.parent.name != "docs":
		return text
	module = (path.parent.parent / "AGENTS.md").read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip()
	if "{roles}" in text:
		from onedesk.one import abilities

		text = text.replace("{roles}", abilities.defaults_table(module))
	if "{notifications}" in text:
		import importlib

		from onedesk.notifications import layout

		sent = importlib.import_module(f"onedesk.{path.parent.parent.name}.notifications").TYPES
		text = text.replace("{notifications}", layout.table(sent))
	text = re.sub(r"^(#{1,2}) ", lambda found: "#" * (len(found.group(1)) + 1) + " ", text, flags=re.M)
	return f"# {module}\n\n{text}"


CODE = re.compile(r"\s*\((?:[^()`]{0,20}`[^`]+`[^()]*?)\)")


def plain(text: str) -> str:
	"""A section as its reader needs it: the names of the code that does it,
	put in brackets for whoever maintains it ("(`retention.taxed`)"), left
	out, since a model hands them on as if they were something to press."""
	return CODE.sub("", text)


def split(text: str) -> list[dict]:
	"""A README's sections for its readers, each with the headings above it. Pure.

	The first line of a README is its title and names the module; every `##`
	and `###` starts a section; `## Under the hood` ends the reading.
	"""
	text = text.split(BACKSTAGE, 1)[0]
	title, path, body, out = "", [], [], []

	def close():
		said = "\n".join(body).strip()
		where = " › ".join([title, *path]) if path else title
		for part in parts(said):
			out.append({"path": where, "text": part})
		body.clear()

	for line in text.splitlines():
		heading = re.match(r"^(#{1,3})\s+(.*)", line)
		if not heading:
			body.append(line)
			continue
		close()
		depth, name = len(heading.group(1)), heading.group(2).strip()
		if depth == 1:
			title, path = name, []
		elif depth == 2:
			path = [name]
		else:
			path = path[:1] + [name]
	close()
	return out


def parts(said: str) -> list[str]:
	"""A section as pieces no longer than a model is handed, cut between
	paragraphs, so the end of a long section is found and read rather than
	cut off. Pure."""
	out, now = [], ""
	for paragraph in [one for one in said.split("\n\n") if one.strip()]:
		if now and len(now) + len(paragraph) + 2 > LONGEST:
			out.append(now)
			now = ""
		now = f"{now}\n\n{paragraph}" if now else paragraph
	return [*out, now] if now else out


def ranked(sections, words: list[str]) -> list[dict]:
	"""The sections that answer the words asked about, best first. Pure.

	Ranked by how many of the different words a section holds, then by its heading,
	then by mentions. A section holding fewer than half the words is no answer.
	"""
	asked = sorted({word for word in words if word})
	if not asked:
		return []
	needed = (len(asked) + 1) // 2
	scored = []
	for one in sections:
		heading, body = one["path"].lower(), one["text"].lower()
		held = [word for word in asked if word in heading or word in body]
		if len(held) < needed:
			continue
		titled = sum(1 for word in asked if word in heading)
		mentions = sum(min(body.count(word), 5) for word in asked)
		scored.append(((len(held), titled, mentions), one))
	scored.sort(key=lambda pair: pair[0], reverse=True)
	return [one for _score, one in scored]
