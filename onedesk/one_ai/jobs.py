"""Every job OneAI does, and what it is told for it (docs/AICENTER.md, The
voice). A job's words are `words/<key>.md`, after the parts of `voice.py`
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
	spend and `takes` the input tokens it may send; `speaks` when it answers
	a person in prose rather than in a shape a program reads."""

	label: str
	module: str
	kind: str
	tools: bool = False
	speaks: bool = False
	most: int = 0
	takes: int = 0


JOBS = {
	"chat": Job(_lt("Chat"), "OneAI", "talk", tools=True, speaks=True, most=800),
	"chat_title": Job(_lt("Title a Conversation"), "OneAI", "talk", most=30),
	"brief": Job(_lt("Summarise a Record"), "OneAI", "talk", speaks=True, most=400),
	"print_design": Job(_lt("Print Design"), "OneAI", "build", tools=True, speaks=True, most=4000),
	"workspace_setup": Job(_lt("Workspace Setup"), "OneAI", "build", tools=True, speaks=True, most=4000),
	"studio": Job(_lt("OneStudio"), "OneAI", "build", tools=True, speaks=True, most=8000),
	"studio_review": Job(_lt("Review an Extension"), "OneAI", "build", most=4000),
	"studio_mend": Job(_lt("Fix an Extension"), "OneAI", "build", most=8000),
	"embed": Job(_lt("Search by Meaning"), "OneAI", "embed", takes=8192),
	"reply": Job(_lt("Draft a Reply"), "OneMail", "talk", most=600),
	"screen": Job(_lt("Screen Applicants"), "OneHR", "talk", most=1500),
	"interview": Job(_lt("Interviews"), "OneHR", "talk", most=2000),
	"transcribe": Job(_lt("Transcribe Interviews"), "OneHR", "hear", most=4000),
	"grievance": Job(_lt("Grievances"), "OneHR", "talk", most=600),
	"read_pages": Job(_lt("Read Scans"), "OneIntake", "see", most=16000),
	"read_sound": Job(_lt("Transcribe Recordings"), "OneIntake", "hear", most=4000),
	"intake_look": Job(_lt("First Look"), "OneIntake", "talk", most=200),
	"intake_read": Job(_lt("Read a Document"), "OneIntake", "talk", most=4000),
	"intake_place": Job(_lt("Place a Document"), "OneIntake", "talk", most=200),
	"intake_explain": Job(_lt("Explain a Document"), "OneIntake", "talk", most=2000),
	"intake_audit": Job(_lt("Audit What OneAI Did"), "OneIntake", "talk", most=1500),
	"intake_fill": Job(_lt("Fill What a Record Still Needs"), "OneIntake", "talk", most=800),
	"intake_act": Job(_lt("Act on What Arrived"), "OneIntake", "talk", tools=True, most=1500),
}


def get(key: str) -> Job | None:
	return JOBS.get(key)


@cache
def words(key: str) -> str:
	"""A job's own words, empty for one that is told nothing (embed)."""
	path = WORDS / f"{key}.md"
	return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def told(key: str) -> str:
	"""Everything a model is told for a job: the voice's parts, then its words."""
	job = JOBS[key]
	return "\n\n".join([*voice.parts(job.speaks, job.tools), *([words(key)] if words(key) else [])])


def label(key: str | None) -> str:
	"""A job as a person reads it, in their language; the key for one gone."""
	import frappe

	job = JOBS.get(key or "")
	return frappe._(job.label) if job else (key or "")
