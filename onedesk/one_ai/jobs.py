"""Every job OneAI does, and what it is told for it (docs/AICENTER.md, The
voice). A job's words are `words/<key>.txt`, after the parts of `voice.py`
it takes; a workspace adds nothing to either. `models.py` says which model
does each kind of work at each tier. Pure, so the guards read it without a
site."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

from onedesk.one_ai import voice

WORDS = Path(__file__).with_name("words")


def _lt(text: str) -> str:
	"""Marks a label for the translation files; `label` translates it."""
	return text


@dataclass(frozen=True)
class Job:
	"""`kind` is a kind in `models.py`; `most` the output tokens a round may
	spend and `takes` the input tokens it may send (all a reading model such
	as Clef holds, since it answers in probabilities rather than words); `speaks` when it answers
	a person in prose rather than in a shape a program reads. `thinks` is
	when the model may reason first ("always", or "full" on that tier only),
	with `room` as its allowance then: a model thinks inside the same tokens
	it answers in, and otherwise spends them all before writing a word."""

	label: str
	module: str
	kind: str
	tools: bool = False
	speaks: bool = False
	most: int = 0
	takes: int = 0
	thinks: str = ""
	room: int = 0


JOBS = {
	"chat": Job(_lt("Chat"), "OneAI", "talk", tools=True, speaks=True, most=800),
	"chat_title": Job(_lt("Title a Conversation"), "OneAI", "talk", most=100),
	"brief": Job(_lt("Summarise a Record"), "OneAI", "talk", speaks=True, most=400),
	"print_design": Job(_lt("Print Design"), "OneAI", "build", tools=True, speaks=True, most=4000, thinks="always"),
	"workspace_setup": Job(_lt("Workspace Setup"), "OneAI", "build", tools=True, speaks=True, most=4000, thinks="always"),
	"studio": Job(_lt("OneStudio"), "OneAI", "build", tools=True, speaks=True, most=8000, thinks="always"),
	"studio_review": Job(_lt("Review an Extension"), "OneAI", "build", most=4000, thinks="always"),
	"studio_mend": Job(_lt("Fix an Extension"), "OneAI", "build", most=8000, thinks="always"),
	"embed": Job(_lt("Search by Meaning"), "OneAI", "embed", takes=8192),
	"reply": Job(_lt("Draft a Reply"), "OneMail", "talk", most=600),
	"bio": Job(_lt("Write a Bio"), "One", "talk", speaks=True, most=300),
	"screen": Job(_lt("Screen Applicants"), "OneHR", "talk", most=1500),
	"interview": Job(_lt("Interviews"), "OneHR", "talk", most=2000),
	"transcribe": Job(_lt("Transcribe Interviews"), "OneHR", "hear", most=4000),
	"grievance": Job(_lt("Grievances"), "OneHR", "talk", most=600),
	"read_pages": Job(_lt("Read Scans"), "OneAI", "see", most=16000),
	"read_sound": Job(_lt("Transcribe Recordings"), "OneAI", "hear", most=4000),
	"intake_decide": Job(_lt("Sort What Arrives"), "OneAI", "decide", takes=4000),
	"intake_look": Job(_lt("First Look"), "OneAI", "talk", most=200),
	"intake_extract": Job(_lt("Read a Bill Twice"), "OneAI", "extract", takes=4000),
	"intake_read": Job(_lt("Read a Document"), "OneAI", "talk", most=4000),
	"intake_place": Job(_lt("Place a Document"), "OneAI", "talk", most=200),
	"intake_explain": Job(_lt("Explain a Document"), "OneAI", "talk", most=2000),
	"intake_audit": Job(_lt("Audit What OneAI Did"), "OneAI", "talk", most=1500),
	"intake_fill": Job(_lt("Fill What a Record Still Needs"), "OneAI", "talk", most=800),
	"intake_act": Job(_lt("Act on What Arrived"), "OneAI", "talk", tools=True, most=1500),
	"guard": Job(_lt("Check What Arrived Before Acting"), "OneAI", "guard", most=10, takes=4000),
}


def get(key: str) -> Job | None:
	return JOBS.get(key)


def thinking(job: Job, tier: str | None) -> bool:
	return job.thinks == "always" or (job.thinks == "full" and tier == "full")


def most(job: Job, tier: str | None) -> int:
	"""The output tokens a round may spend: its room when it thinks."""
	return max(job.most, job.room) if thinking(job, tier) else job.most


@cache
def words(key: str) -> str:
	"""A job's own words, empty for one that is told nothing (embed)."""
	path = WORDS / f"{key}.txt"
	return path.read_text(encoding="utf-8").strip() if path.exists() else ""


# Kinds told nothing: Llama Guard judges the whole conversation in its own
# template, so anything it were told would be judged with the text.
UNTOLD = ("guard",)


def told(key: str) -> str:
	"""Everything a model is told for a job: the voice's parts, then its words."""
	job = JOBS[key]
	if job.kind in UNTOLD:
		return ""
	return "\n\n".join([*voice.parts(job.speaks, job.tools), *([words(key)] if words(key) else [])])


def label(key: str | None) -> str:
	"""A job as a person reads it, in their language; the key for one gone."""
	import frappe

	job = JOBS.get(key or "")
	return frappe._(job.label) if job else (key or "")
