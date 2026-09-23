"""OneAI on the hiring walk: every applicant read, rated and placed.

The plan and the reasons are `docs/HIRING.md`. The short version: a number goes
in a field so it sorts, an opinion goes in a comment so it has an author, and
nothing here changes an applicant's status or reaches the candidate.

**One call per applicant.** The CV is read against the opening's criteria and
the new applicant is placed among everybody else still in the running in the
same call — the model is handed the pool as a line each, never a CV twice.

**Everything here runs as OneAI.** A job made by a web-form applicant would
otherwise run as Guest, and one made by an HR user would write comments in
their name that they never wrote. `AUTHOR` is a disabled user with the OneAI
mark as its picture: the timeline says who spoke, and nobody can sign in as it.
"""

import base64
import html
import io
import json
import re
import zipfile

import frappe
from frappe.utils import cint, now_datetime, strip_html

#: The user every OneAI comment is written by. `.invalid` is the top-level
#: domain that is guaranteed never to deliver a mail.
AUTHOR = "oneai@one.invalid"

#: The applicants a newcomer is compared with: the best-placed this many still
#: in the running. Forty lines is a few thousand tokens; four hundred is a call
#: that costs more than the CV it is about.
POOL = 40

#: An applicant still in the running. Rejected is out; Accepted is hired.
RUNNING = ("Open", "Replied", "Hold")

#: A standing that moves this far gets a line saying why. Smaller moves are
#: the pool settling, and a comment for each is a timeline nobody reads.
MOVED = 15

#: How much of each thing the model is handed.
MOST_CV = 12000
MOST_LETTER = 2500
MOST_DESCRIPTION = 4000
MOST_BRIEF = 320

#: A PDF with at least this much text in it is sent as its text: cheaper than
#: pages, and readable by a model that cannot see. Under it, it is a scan.
READABLE = 300


# ------------------------------------------------------------------- setup


def ensure() -> None:
	"""The OneAI user every OneAI comment is written by. The hiring switches
	are seeded with the rest of HR Settings' in `one_hr/policy.py`."""
	if frappe.db.exists("User", AUTHOR):
		return
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": AUTHOR,
			"first_name": "OneAI",
			"enabled": 0,
			"send_welcome_email": 0,
			"user_type": "System User",
			"user_image": "/assets/onedesk/images/oneai.svg",
		}
	)
	user.flags.ignore_permissions = True
	user.flags.no_welcome_mail = True
	user.insert()


def on(key: str) -> bool:
	return bool(cint(frappe.db.get_single_value("HR Settings", key)))


# ------------------------------------------------------------ the applicant


def arrived(doc, method=None) -> None:
	"""A new applicant for an opening: read them once this is committed."""
	if doc.job_title and on("one_ai_screen"):
		_later("onedesk.one_hr.hiring.screen", f"screen::{doc.name}", applicant=doc.name)


@frappe.whitelist()
def screen_again(applicant: str) -> None:
	"""Read this applicant's CV again, and place them again."""
	frappe.get_doc("Job Applicant", applicant).check_permission("write")
	_later("onedesk.one_hr.hiring.screen", f"screen::{applicant}", applicant=applicant)


@frappe.whitelist()
def rank_again(opening: str) -> None:
	"""Place everybody applying to this opening again, from what OneAI already wrote."""
	frappe.get_doc("Job Opening", opening).check_permission("write")
	_later("onedesk.one_hr.hiring.rank", f"rank::{opening}", opening=opening)


def screen(applicant: str) -> None:
	"""Read one applicant against their opening, rate them, and place them."""
	frappe.set_user(AUTHOR)
	doc = frappe.get_doc("Job Applicant", applicant)
	if not doc.job_title:
		return
	opening = frappe.get_doc("Job Opening", doc.job_title)
	pool = _pool(opening.name, but=applicant)
	cv, files = _cv(doc)

	asked = SCREEN.format(
		opening=_opening_said(opening),
		applicant=_applicant_said(doc, cv, bool(files)),
		id=NEW,
		pool=_pool_said(pool) or "(nobody yet — this is the first)",
	)
	said = _ask("screen", asked, files, applicant)
	if said is None and files and "cannot read" in (frappe.flags.one_ai_refused or ""):
		# The workspace's model cannot read this kind of file. Screened from
		# what is left, and saying so, rather than not at all.
		said = _ask("screen", asked + UNREAD, None, applicant)
	answer = unaliased(_read("screen", said, applicant), _aliases(pool, doc))
	if not answer:
		return

	rating = _clamped(answer.get("rating"), 0, 5)
	brief = _short(answer.get("brief"), MOST_BRIEF)
	frappe.db.set_value(
		"Job Applicant",
		applicant,
		{
			"one_ai_rating": round(rating / 5, 2) if rating is not None else None,
			"one_ai_brief": brief,
			"one_ai_screened_on": now_datetime(),
		},
	)
	moves = _placed(answer, pool, applicant, opening.name)
	standing = frappe.db.get_value("Job Applicant", applicant, "one_ai_standing")
	_comment(
		"Job Applicant",
		applicant,
		_screened(answer, rating, standing, _where(opening.name, applicant)),
	)
	frappe.db.commit()
	_refresh("Job Applicant", applicant, *moves)


def rank(opening: str) -> None:
	"""Place everybody still in the running again, from their briefs alone."""
	frappe.set_user(AUTHOR)
	held = frappe.get_doc("Job Opening", opening)
	pool = _pool(opening)
	if len(pool) < 2:
		return
	said = _ask("screen", RANK.format(opening=_opening_said(held), pool=_pool_said(pool)), None, opening)
	answer = unaliased(_read("screen", said, opening), _aliases(pool))
	if not answer:
		return
	moves = _placed(answer, pool, None, opening)
	_comment(
		"Job Opening",
		opening,
		"<p>" + html.escape(frappe._("Placed {0} applicants again from what I wrote about each.").format(len(pool))) + "</p>",
	)
	frappe.db.commit()
	_refresh("Job Opening", opening, *moves)


# ------------------------------------------------------------ what is said


SCREEN = """Screen one job applicant, then place them among the others applying.

THE OPENING
{opening}

THE NEW APPLICANT, {id}
{applicant}

THE OTHERS STILL IN THE RUNNING (label · rating out of 5 · standing out of 100 · what you wrote when you read their CV)
{pool}

Answer with one JSON object and nothing else:
{{
  "rating": 1 to 5, how well this CV meets what the opening asks for, on its own,
  "brief": "two sentences for the hiring manager: what they bring and what is not shown, against the criteria. No name, no pronoun.",
  "strengths": ["up to four things the CV shows that the opening asks for"],
  "not_shown": ["up to four criteria the CV does not show"],
  "ask_first": ["up to three things worth confirming before anybody books an interview"],
  "standing": {{"{id}": 0 to 100, and every other label above (A1, A2, …): 0 to 100}},
  "why_moved": {{"label": "one line, for anybody whose standing you changed by 15 or more"}}
}}
Standing is how each person compares with everybody else in this pool for this opening: 100 is the strongest here, not a perfect candidate. Keep the standings you were given unless the new applicant changes the picture."""

RANK = """Place everybody applying to this opening again.

THE OPENING
{opening}

THE APPLICANTS (label · rating out of 5 · current standing out of 100 · what you wrote when you read their CV)
{pool}

Answer with one JSON object and nothing else:
{{
  "standing": {{"every label above (A1, A2, …)": 0 to 100}},
  "why_moved": {{"label": "one line, for anybody whose standing you changed by 15 or more"}}
}}
Standing is how each person compares with everybody else here: 100 is the strongest in this pool."""

UNREAD = "\n\nThe CV was attached as a file that could not be read. Screen from the rest and say in the brief that the CV was not read."


def _opening_said(opening) -> str:
	lines = [f"{opening.job_title} ({opening.name})"]
	for label, value in (
		("Designation", opening.designation),
		("Department", opening.department),
		("Employment type", opening.employment_type),
		("Location", opening.location),
	):
		if value:
			lines.append(f"{label}: {value}")
	criteria = (opening.get("one_criteria") or "").strip()
	lines.append("Screening criteria:\n" + (criteria or "(none written; judge against the description)"))
	description = _plain(opening.description, MOST_DESCRIPTION)
	if description:
		lines.append("Description:\n" + description)
	return "\n".join(lines)


def _applicant_said(doc, cv: str, filed: bool) -> str:
	"""What the model reads about somebody: their letter and their CV.

	Not their country, not their phone, not their email — nothing a person
	could be sorted by that the job does not ask about. The CV carries their
	name and that cannot be helped; the pool never does.
	"""
	lines = []
	letter = _plain(doc.cover_letter, MOST_LETTER)
	if letter:
		lines.append("Cover letter:\n" + letter)
	if cv:
		lines.append("CV:\n" + cv)
	elif filed:
		lines.append("CV: attached.")
	elif doc.resume_link:
		lines.append("CV: given as a link, which was not opened.")
	else:
		lines.append("CV: none was given.")
	return "\n\n".join(lines)


def _pool_said(pool: list[dict]) -> str:
	"""A line each, under a label rather than the applicant's id.

	HRMS names an applicant after their email address, so the id is the
	person's name — which is exactly what the pool is meant not to carry.
	"""
	return "\n".join(
		f"A{at} · {_stars(one.one_ai_rating)} · {_percent(one.one_ai_standing)} · {one.one_ai_brief or '—'}"
		for at, one in enumerate(pool, 1)
	)


#: What the newcomer is called in a call, for the same reason.
NEW = "NEW"


def _aliases(pool: list, newcomer=None) -> dict[str, tuple[str, str]]:
	"""Each label the model was shown, and the applicant and name it stands for."""
	held = {f"A{at}": (one.name, one.applicant_name or one.name) for at, one in enumerate(pool, 1)}
	if newcomer is not None:
		held[NEW] = (newcomer.name, newcomer.applicant_name or newcomer.name)
	return held


def unaliased(answer: dict | None, aliases: dict[str, tuple[str, str]]) -> dict | None:
	"""An answer about labels, turned back into one about applicants.

	Standings and reasons are keyed by the applicant's id again, and a label
	inside a reason ("A3 has the same stack") becomes the name a hiring
	manager reads it as. A label the model made up is dropped.
	"""
	if not answer:
		return answer

	def named(text: str) -> str:
		return re.sub(
			r"\b(NEW|A\d+)\b",
			lambda found: aliases[found.group(1)][1] if found.group(1) in aliases else found.group(1),
			str(text or ""),
		)

	out = dict(answer)
	for key in ("standing", "why_moved"):
		given = answer.get(key) or {}
		if not isinstance(given, dict):
			given = {}
		out[key] = {
			aliases[label][0]: (named(value) if key == "why_moved" else value)
			for label, value in given.items()
			if label in aliases
		}
	for key in ("brief", "strengths", "not_shown", "ask_first"):
		value = answer.get(key)
		out[key] = [named(one) for one in value] if isinstance(value, list) else named(value) if value else value
	return out


def _stars(rating) -> str:
	return f"{round((rating or 0) * 5, 1):g}" if rating else "—"


def _percent(standing) -> str:
	return f"{round(standing):g}" if standing is not None else "—"


def _screened(answer: dict, rating, standing, where: tuple[int, int]) -> str:
	"""The comment on a newly read applicant: the verdict first, reasons after."""
	_ = frappe._
	head = []
	if rating is not None:
		head.append(_("Rated {0} of 5").format(f"{round(rating, 1):g}"))
	if standing is not None and where[1]:
		head.append(_("placed {0} of {1}").format(*where))
	parts = []
	if head:
		parts.append(f"<p><strong>{html.escape(' · '.join(head))}</strong></p>")
	if answer.get("brief"):
		parts.append(f"<p>{html.escape(_short(answer['brief'], MOST_BRIEF))}</p>")
	for key, label in (
		("strengths", _("Shows")),
		("not_shown", _("Not shown")),
		("ask_first", _("Worth knowing before you call")),
	):
		items = [str(one).strip() for one in (answer.get(key) or []) if str(one).strip()][:4]
		if items:
			parts.append(
				f"<p><strong>{html.escape(label)}</strong></p><ul>"
				+ "".join(f"<li>{html.escape(one)}</li>" for one in items)
				+ "</ul>"
			)
	return "".join(parts)


# ------------------------------------------------------------ the interview


def scheduled(doc, method=None) -> None:
	"""A new interview: write what the interviewer should know before it."""
	if doc.job_applicant and on("one_ai_prepare"):
		_later("onedesk.one_hr.hiring.prepare", f"prepare::{doc.name}", interview=doc.name)


@frappe.whitelist()
def prepare_again(interview: str) -> None:
	frappe.get_doc("Interview", interview).check_permission("write")
	_later("onedesk.one_hr.hiring.prepare", f"prepare::{interview}", interview=interview)


def prepare(interview: str) -> None:
	"""What to confirm, and what to ask, for this interview with this person.

	Written into a field rather than a comment: it is what an interviewer reads
	with the candidate in front of them, and a timeline is the wrong place to
	look for that in a hurry.
	"""
	frappe.set_user(AUTHOR)
	doc = frappe.get_doc("Interview", interview)
	applicant = frappe.get_doc("Job Applicant", doc.job_applicant)
	opening_name = doc.job_opening or applicant.job_title
	opening = frappe.get_doc("Job Opening", opening_name) if opening_name else None

	asked = PREPARE.format(
		opening=_opening_said(opening) if opening else "(no opening)",
		round=_round_said(doc),
		screening=_screening_said(applicant),
		before=_earlier_said(doc) or "(this is the first round)",
	)
	answer = _read("interview", _ask("interview", asked, None, interview), interview)
	if not answer:
		return
	frappe.db.set_value("Interview", interview, "one_ai_prep", prepared(answer))
	frappe.db.commit()
	_refresh("Interview", interview)


PREPARE = """Prepare an interviewer for one interview.

THE OPENING
{opening}

THIS ROUND
{round}

WHAT WAS SAID WHEN THE CV WAS READ
{screening}

EARLIER ROUNDS WITH THIS PERSON
{before}

Answer with one JSON object and nothing else:
{{
  "confirm": ["up to four things to confirm in the first minutes: gaps, dates, anything the CV leaves unclear"],
  "questions": [
    {{"ask": "the question, as the interviewer would say it", "tests": "the skill or criterion it tests", "why": "why it is asked of this person, in a few words"}}
  ]
}}
At most eight questions. Put first anything an earlier round left open. Every question is about the work."""


def _round_said(doc) -> str:
	lines = [f"Interview type: {doc.interview_type or '—'}"]
	if doc.interview_type:
		described = frappe.db.get_value("Interview Type", doc.interview_type, "description")
		if described:
			lines.append(_plain(described, 800))
		skills = frappe.get_all(
			"Expected Skill Set",
			filters={"parent": doc.interview_type, "parenttype": "Interview Type"},
			fields=["skill", "description"],
			order_by="idx",
		)
		if skills:
			lines.append("Expected skills:")
			lines += [f"- {one.skill}" + (f": {_plain(one.description, 200)}" if one.description else "") for one in skills]
	return "\n".join(lines)


def _screening_said(applicant) -> str:
	"""OneAI's own screening of this person, as it was written on their record."""
	said = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Job Applicant",
			"reference_name": applicant.name,
			"owner": AUTHOR,
			"content": ["like", "%<ul>%"],
		},
		pluck="content",
		order_by="creation desc",
		limit=1,
	)
	if said:
		return _plain(said[0].replace("</strong></p>", ":</strong></p>").replace("</li>", "; "), 1500)
	return applicant.get("one_ai_brief") or "(not screened)"


def _earlier_said(doc) -> str:
	"""What earlier rounds with this applicant decided, and what they left open."""
	rounds = frappe.get_all(
		"Interview",
		filters={"job_applicant": doc.job_applicant, "name": ["!=", doc.name], "docstatus": ["<", 2]},
		fields=["name", "interview_type", "status", "interview_summary"],
		order_by="scheduled_on asc",
	)
	lines = []
	for one in rounds:
		lines.append(f"{one.interview_type or 'Interview'} — {one.status}" + (f": {_plain(one.interview_summary, 400)}" if one.interview_summary else ""))
		for said in frappe.get_all(
			"Interview Feedback",
			filters={"interview": one.name, "docstatus": 1},
			fields=["result", "feedback"],
		):
			lines.append(f"  Feedback ({said.result or '—'}): {_plain(said.feedback, 400)}")
	return "\n".join(lines)


def prepared(answer: dict) -> str:
	"""The field's HTML: what to confirm, then the questions and what each tests."""
	_ = frappe._
	parts = []
	confirm = [str(one).strip() for one in (answer.get("confirm") or []) if str(one).strip()][:4]
	if confirm:
		parts.append(
			f"<p><strong>{html.escape(_('Confirm first'))}</strong></p><ol>"
			+ "".join(_item("bullet", html.escape(one)) for one in confirm)
			+ "</ol>"
		)
	questions = [one for one in (answer.get("questions") or []) if isinstance(one, dict) and one.get("ask")][:8]
	if questions:
		items = []
		for one in questions:
			note = " — ".join(html.escape(str(one[key]).strip()) for key in ("tests", "why") if one.get(key))
			items.append(_item("ordered", html.escape(str(one["ask"]).strip()) + (f"<br><em>{note}</em>" if note else "")))
		parts.append(f"<p><strong>{html.escape(_('Questions'))}</strong></p><ol>" + "".join(items) + "</ol>")
	return "".join(parts)


def _item(kind: str, inner: str) -> str:
	"""A list item the way the Text Editor writes one.

	Quill 2 draws every list as an `<ol>` and puts the marker in a span it
	styles, keyed by `data-list`; a plain `<ul><li>` in a read-only Text Editor
	shows neither bullets nor numbers.
	"""
	return f'<li data-list="{kind}"><span class="ql-ui" contenteditable="false"></span>{inner}</li>'


# ------------------------------------------------------------ the recording


#: How long one part of a recording is. The recorder restarts on this beat so
#: each part is a whole file: uploaded as soon as it closes, transcribed as
#: soon as it lands, and small enough to send — opus at 24 kbit/s is under a
#: megabyte for five minutes. Said again in public/js/hiring.js.
PART_SECONDS = 300

#: What a part's file is, by what the browser could record it as.
SOUND = {".ogg": "audio/ogg", ".webm": "audio/webm", ".m4a": "audio/mp4", ".mp4": "audio/mp4"}

#: How much transcript the remarks read. An hour is about nine thousand words.
MOST_TRANSCRIPT = 80000


def interview_onload(doc, method=None) -> None:
	"""Whether this workspace records interviews, for the form to offer it."""
	doc.set_onload("one_ai_record", on("one_ai_record"))


@frappe.whitelist()
def start_recording(interview: str, agreed: int) -> str:
	"""A new recording of this interview, once the candidate has agreed."""
	if not cint(agreed):
		frappe.throw(frappe._("An interview is only recorded once the candidate has agreed."))
	if not on("one_ai_record"):
		frappe.throw(frappe._("This workspace does not record interviews. HR Settings says whether it does."))
	frappe.get_doc("Interview", interview).check_permission("read")
	now = now_datetime()
	held = frappe.get_doc(
		{
			"doctype": "Interview Recording",
			"interview": interview,
			"status": "Recording",
			"recorded_by": frappe.session.user,
			"started_on": now,
			"agreed": 1,
			"agreed_by": frappe.session.user,
			"agreed_on": now,
		}
	).insert()
	return held.name


@frappe.whitelist()
def recorded_part(recording: str, file_name: str, data: str, starts_at: int, seconds: int) -> str:
	"""One closed part: file its sound on the recording, add it, and transcribe it.

	Added with `db_insert` rather than a save of the recording, because the
	transcription of the part before is writing to the same recording at the
	same moment, and two saves of one document is one of them refused.
	"""
	from onedesk.one_ai import files

	held = frappe.get_doc("Interview Recording", recording)
	held.check_permission("write")
	if held.status != "Recording":
		frappe.throw(frappe._("This recording has already ended."))
	if not re.fullmatch(r"[\w.-]{1,120}", file_name or "") or not any(file_name.lower().endswith(ext) for ext in SOUND):
		frappe.throw(frappe._("That is not a recording."))
	content = base64.b64decode(data or "")
	if not content or len(content) > files.MOST_BYTES:
		frappe.throw(frappe._("That part of the recording is empty or too large."))
	sound = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": "Interview Recording",
			"attached_to_name": recording,
			"is_private": 1,
			"content": content,
		}
	).insert(ignore_permissions=True)
	file_url = sound.file_url
	row = held.append(
		"parts",
		{"file": file_url, "starts_at": cint(starts_at), "length": cint(seconds), "state": "Waiting"},
	)
	row.idx = len(held.parts)
	row.creation = row.modified = now_datetime()
	row.owner = row.modified_by = frappe.session.user
	row.db_insert()
	if on("one_ai_transcribe"):
		_later("onedesk.one_hr.hiring.transcribe", f"transcribe::{row.name}", part=row.name)
	return row.name


@frappe.whitelist()
def stop_recording(recording: str, seconds: int) -> None:
	"""The interview is over: the length, and the transcript once it is whole."""
	held = frappe.get_doc("Interview Recording", recording)
	held.check_permission("write")
	if held.status != "Recording":
		return
	status = "Transcribing" if on("one_ai_transcribe") and held.parts else "Recorded"
	frappe.db.set_value(
		"Interview Recording",
		recording,
		{"ended_on": now_datetime(), "length": cint(seconds), "status": status},
	)
	if status == "Transcribing":
		_finished(recording)


@frappe.whitelist()
def transcribe_again(recording: str) -> None:
	"""Try the parts that failed once more — after a model was picked, say."""
	held = frappe.get_doc("Interview Recording", recording)
	held.check_permission("write")
	if held.status not in ("Failed", "Recorded", "Transcribed") or held.sound_deleted_on:
		frappe.throw(frappe._("This recording cannot be transcribed again."))
	waiting = [row.name for row in held.parts if row.state != "Transcribed" or held.status == "Recorded"]
	if not waiting:
		frappe.throw(frappe._("Every part is already transcribed."))
	for name in waiting:
		frappe.db.set_value("Interview Recording Part", name, "state", "Waiting", update_modified=False)
		_later("onedesk.one_hr.hiring.transcribe", f"transcribe::{name}", part=name)
	frappe.db.set_value("Interview Recording", recording, "status", "Transcribing")


def transcribe(part: str) -> None:
	"""One part, written down, with its turns timed from the start of the interview."""
	frappe.set_user(AUTHOR)
	row = frappe.db.get_value(
		"Interview Recording Part", part, ["parent", "file", "starts_at"], as_dict=True
	)
	if not row:
		return
	sound = _sound(row.file)
	said = None
	if sound:
		said = _ask(
			"transcribe",
			TRANSCRIBE.format(start=clock(row.starts_at)),
			[sound],
			row.parent,
		)
	frappe.db.set_value(
		"Interview Recording Part",
		part,
		{"transcript": (said or "").strip(), "state": "Transcribed" if (said or "").strip() else "Failed"},
		update_modified=False,
	)
	frappe.db.commit()
	_finished(row.parent)


TRANSCRIBE = """This is one part of a recorded job interview. It starts {start} into the interview: time every turn from the start of the interview, not from the start of this part."""


def _sound(url: str) -> dict | None:
	held = frappe.db.get_value("File", {"file_url": url}, "name")
	if not held:
		return None
	file = frappe.get_doc("File", held)
	kind = next((kind for ext, kind in SOUND.items() if (file.file_name or url).lower().endswith(ext)), None)
	if not kind:
		return None
	content = file.get_content()
	if isinstance(content, str):
		content = content.encode()
	from onedesk.one_ai import files

	if len(content) > files.MOST_BYTES:
		return None
	return {"name": file.file_name, "type": kind, "data": base64.b64encode(content).decode()}


def clock(seconds) -> str:
	"""Seconds as the mm:ss a transcript is timed in, hours when there are any."""
	seconds = max(cint(seconds), 0)
	hours, rest = divmod(seconds, 3600)
	return f"{hours}:{rest // 60:02d}:{rest % 60:02d}" if hours else f"{rest // 60:02d}:{rest % 60:02d}"


def _finished(recording: str) -> None:
	"""Put the transcript together once the interview has ended and every part is in.

	Called after each part and when the recording stops, since either can be
	the last. The row lock is what stops the two of them both finishing it.
	"""
	status = frappe.db.get_value("Interview Recording", recording, "status", for_update=True)
	if status != "Transcribing":
		return
	parts = frappe.get_all(
		"Interview Recording Part",
		filters={"parent": recording, "parenttype": "Interview Recording"},
		fields=["starts_at", "state", "transcript"],
		order_by="starts_at asc",
	)
	if any(one.state == "Waiting" for one in parts):
		return
	written = [one for one in parts if one.state == "Transcribed"]
	text = "\n\n".join(
		one.transcript if one.state == "Transcribed" else f"[{clock(one.starts_at)} — {frappe._('this part could not be transcribed')}]"
		for one in parts
	)
	frappe.db.set_value(
		"Interview Recording",
		recording,
		{"transcript": text, "status": "Transcribed" if written else "Failed"},
	)
	frappe.db.commit()
	_refresh("Interview Recording", recording)
	if written:
		_later("onedesk.one_hr.hiring.remark", f"remark::{recording}", recording=recording)


def remark(recording: str) -> None:
	"""OneAI's remarks on an interview, from its transcript, as a comment on it."""
	frappe.set_user(AUTHOR)
	held = frappe.get_doc("Interview Recording", recording)
	interview = frappe.get_doc("Interview", held.interview)
	applicant = frappe.get_doc("Job Applicant", interview.job_applicant)
	opening_name = interview.job_opening or applicant.job_title
	opening = frappe.get_doc("Job Opening", opening_name) if opening_name else None

	asked = REMARK.format(
		opening=_opening_said(opening) if opening else "(no opening)",
		round=_round_said(interview),
		prepared=_plain(interview.get("one_ai_prep"), 3000) or "(nothing was prepared)",
		transcript=(held.transcript or "")[:MOST_TRANSCRIPT],
	)
	answer = _read("interview", _ask("interview", asked, None, recording), recording)
	if not answer:
		return
	_comment("Interview", interview.name, remarked(answer))
	if answer.get("summary"):
		_comment(
			"Job Applicant",
			applicant.name,
			"<p>"
			+ html.escape(
				(
					frappe._("After the {0} interview: {1}").format(interview.interview_type, _short(answer["summary"], 400))
					if interview.interview_type
					else frappe._("After the interview: {0}").format(_short(answer["summary"], 400))
				)
			)
			+ "</p>",
		)
	frappe.db.commit()


REMARK = """Remark on a job interview from its transcript.

THE OPENING
{opening}

THIS ROUND
{round}

WHAT WAS PREPARED FOR IT
{prepared}

THE TRANSCRIPT
{transcript}

Answer with one JSON object and nothing else:
{{
  "summary": "two sentences: what this interview showed, against the opening",
  "skills": [{{"skill": "each expected skill", "shown": "what was said that shows it or does not, in a few words", "at": "mm:ss where it was said", "rating": 1 to 5}}],
  "not_asked": ["prepared questions or expected skills the interview did not reach"],
  "concerns": ["anything said that a hiring manager should weigh, with the time"],
  "follow_up": ["what to ask next round"]
}}
Judge only what was said. Never judge accent, tone, pauses or how anybody sounded."""


def remarked(answer: dict) -> str:
	"""The comment on an interview: the summary, each skill with its minute, then the rest."""
	_ = frappe._
	parts = []
	if answer.get("summary"):
		parts.append(f"<p>{html.escape(_short(answer['summary'], 600))}</p>")
	skills = [one for one in (answer.get("skills") or []) if isinstance(one, dict) and one.get("skill")]
	if skills:
		items = []
		for one in skills[:10]:
			rating = _clamped(one.get("rating"), 0, 5)
			head = html.escape(str(one["skill"]).strip()) + (f" · {round(rating, 1):g}/5" if rating is not None else "")
			said = html.escape(str(one.get("shown") or "").strip())
			at = html.escape(str(one.get("at") or "").strip())
			items.append(f"<li><strong>{head}</strong>" + (f" — {said}" if said else "") + (f" <em>({at})</em>" if at else "") + "</li>")
		parts.append(f"<p><strong>{html.escape(_('By skill'))}</strong></p><ul>" + "".join(items) + "</ul>")
	for key, label in (
		("not_asked", _("Not reached")),
		("concerns", _("Worth weighing")),
		("follow_up", _("Ask next round")),
	):
		items = [str(one).strip() for one in (answer.get(key) or []) if str(one).strip()][:5]
		if items:
			parts.append(
				f"<p><strong>{html.escape(label)}</strong></p><ul>"
				+ "".join(f"<li>{html.escape(one)}</li>" for one in items)
				+ "</ul>"
			)
	return "".join(parts)


def purge() -> None:
	"""Delete the sound of recordings older than the workspace keeps, and keep the words."""
	days = cint(frappe.db.get_single_value("HR Settings", "one_keep_recordings_days"))
	if days <= 0:
		return
	before = frappe.utils.add_days(frappe.utils.today(), -days)
	for recording in frappe.get_all(
		"Interview Recording",
		filters={"ended_on": ["<", before], "sound_deleted_on": ["is", "not set"]},
		pluck="name",
	):
		frappe.flags.one_purging_sound = True
		try:
			# A part names its file, and a file something still names cannot
			# be deleted. The transcript on the part is what stays.
			frappe.db.set_value(
				"Interview Recording Part", {"parent": recording, "parenttype": "Interview Recording"}, "file", None
			)
			for file in frappe.get_all(
				"File",
				filters={"attached_to_doctype": "Interview Recording", "attached_to_name": recording},
				pluck="name",
			):
				frappe.delete_doc("File", file, ignore_permissions=True)
		finally:
			frappe.flags.one_purging_sound = False
		frappe.db.set_value("Interview Recording", recording, "sound_deleted_on", frappe.utils.today())
		frappe.db.commit()


def keep_sound(doc, method=None) -> None:
	"""A recording's sound is deleted by its retention or by an HR Manager, and by nobody else."""
	if doc.attached_to_doctype != "Interview Recording" or frappe.flags.get("one_purging_sound"):
		return
	if "HR Manager" not in frappe.get_roles():
		frappe.throw(frappe._("Only an HR Manager can delete the sound of a recorded interview."))


# ------------------------------------------------------------ the pool


def _pool(opening: str, but: str | None = None) -> list:
	"""The applicants a newcomer is compared with, best-placed first."""
	filters = {
		"job_title": opening,
		"status": ["in", RUNNING],
		"one_ai_screened_on": ["is", "set"],
	}
	if but:
		filters["name"] = ["!=", but]
	return frappe.get_all(
		"Job Applicant",
		filters=filters,
		fields=["name", "applicant_name", "one_ai_rating", "one_ai_standing", "one_ai_brief"],
		order_by="one_ai_standing desc, creation asc",
		limit=POOL,
	)


def _placed(answer: dict, pool: list, applicant: str | None, opening: str) -> list[str]:
	"""Write the standings the model gave, and say why of anybody moved far.

	Only ids that were in the pool, or the newcomer, are written: a model that
	invents an id or names somebody it was not shown does not reach a record.
	"""
	was = {one.name: one.one_ai_standing for one in pool}
	allowed = set(was) | ({applicant} if applicant else set())
	given = standings(answer, allowed)
	why = answer.get("why_moved") or {}
	moved = []
	for name, value in given.items():
		frappe.db.set_value("Job Applicant", name, "one_ai_standing", value, update_modified=False)
		before = was.get(name)
		if name != applicant and before is not None and abs(value - before) >= MOVED:
			moved.append(name)
			said = _short(str(why.get(name) or ""), 200)
			text = (
				frappe._("Moved up from {0}% to {1}%.") if value > before else frappe._("Moved down from {0}% to {1}%.")
			).format(_percent(before), _percent(value))
			_comment("Job Applicant", name, f"<p>{html.escape(text + (' ' + said if said else ''))}</p>")
	return moved


def standings(answer: dict, allowed: set[str]) -> dict[str, float]:
	"""The standings in an answer, kept to ids that exist and to 0–100."""
	out = {}
	for name, value in (answer.get("standing") or {}).items():
		if name not in allowed:
			continue
		held = _clamped(value, 0, 100)
		if held is not None:
			out[name] = round(held, 1)
	return out


def _where(opening: str, applicant: str) -> tuple[int, int]:
	"""Where this applicant sits among those still in the running: (place, of)."""
	rows = frappe.get_all(
		"Job Applicant",
		filters={"job_title": opening, "status": ["in", RUNNING], "one_ai_screened_on": ["is", "set"]},
		fields=["name", "one_ai_standing"],
		order_by="one_ai_standing desc, creation asc",
	)
	names = [one.name for one in rows]
	return (names.index(applicant) + 1, len(names)) if applicant in names else (0, 0)


# ------------------------------------------------------------ the CV


def _cv(doc) -> tuple[str, list[dict] | None]:
	"""The CV as text where it has text, and as the file where it is a picture.

	A PDF with words in it is sent as its words: a third of the cost of pages
	and readable by any model. A scan or a photo is sent whole, and a model
	that cannot see it is asked again without it by `screen`.
	"""
	url = doc.resume_attachment
	if not url:
		return "", None
	held = frappe.db.get_value("File", {"file_url": url}, "name")
	if not held:
		return "", None
	file = frappe.get_doc("File", held)
	try:
		content = file.get_content()
	except Exception:
		return "", None
	if isinstance(content, str):
		content = content.encode()
	name = (file.file_name or url).lower()

	if name.endswith(".pdf"):
		text = _pdf_text(content)
		if len(text) >= READABLE:
			return text[:MOST_CV], None
		return _whole(file.file_name, "application/pdf", content)
	if name.endswith(".docx"):
		return _docx_text(content)[:MOST_CV], None
	if name.endswith((".txt", ".md")):
		return content.decode("utf-8", "replace")[:MOST_CV], None
	if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
		kind = "image/jpeg" if name.endswith((".jpg", ".jpeg")) else f"image/{name.rsplit('.', 1)[-1]}"
		return _whole(file.file_name, kind, content)
	return "", None


def _whole(name: str, kind: str, content: bytes) -> tuple[str, list[dict] | None]:
	"""A file sent as itself, or a sentence saying it was too big to send."""
	from onedesk.one_ai import files

	if len(content) > files.MOST_BYTES:
		return "(The CV is a scanned file too large to read.)", None
	return "", [{"name": name, "type": kind, "data": base64.b64encode(content).decode()}]


def _pdf_text(content: bytes) -> str:
	try:
		from pypdf import PdfReader

		reader = PdfReader(io.BytesIO(content))
		return "\n".join((page.extract_text() or "") for page in reader.pages[:8]).strip()
	except Exception:
		return ""


def _docx_text(content: bytes) -> str:
	"""A Word file's words: it is a zip, and the words are one XML file in it."""
	try:
		with zipfile.ZipFile(io.BytesIO(content)) as held:
			xml = held.read("word/document.xml").decode("utf-8", "replace")
	except Exception:
		return ""
	xml = re.sub(r"</w:p>", "\n", xml)
	return html.unescape(re.sub(r"<[^>]+>", "", xml)).strip()


# ------------------------------------------------------------ the answer


def read(said: str | None) -> dict | None:
	"""The JSON object in a model's answer, fenced or not, or None."""
	if not said:
		return None
	text = said.strip()
	fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
	if fenced:
		text = fenced.group(1).strip()
	start, end = text.find("{"), text.rfind("}")
	if start < 0 or end <= start:
		return None
	try:
		held = json.loads(text[start : end + 1])
	except ValueError:
		return None
	return held if isinstance(held, dict) else None


def _read(action: str, said: str | None, reference: str) -> dict | None:
	"""`read`, and the answer itself in the error log when it cannot be read.

	A model that answered in prose, or ran out of room half way through the
	object, was charged for it: dropping the answer without a word left an
	administrator nothing to look at and nobody any wiser about which model
	does not follow the format.
	"""
	answer = read(said)
	if said and answer is None:
		frappe.log_error(
			title=f"OneAI's {action} answer for {reference} was not the JSON asked for",
			message=said[:8000],
		)
	return answer


def _clamped(value, least: float, most: float) -> float | None:
	try:
		number = float(value)
	except (TypeError, ValueError):
		return None
	return max(least, min(most, number))


def _short(text, most: int) -> str:
	said = " ".join(str(text or "").split())
	if len(said) <= most:
		return said
	return said[: most - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _plain(text, most: int) -> str:
	return _short(strip_html(text or ""), most) if text else ""


def _ask(action: str, text: str, files: list[dict] | None, reference: str) -> str | None:
	"""One call, or None with the reason in the error log.

	A job has nobody to show an error to. The log is where an administrator
	who wonders why an applicant has no rating will look.
	"""
	from onedesk.one_ai import run

	frappe.flags.one_ai_refused = None
	try:
		return run.once(action, text, files=files, reference=reference)
	except Exception as raised:
		frappe.flags.one_ai_refused = str(raised)
		frappe.log_error(title=f"OneAI could not {action} {reference}")
		return None


# ------------------------------------------------------------ plumbing


def _later(method: str, job: str, **kwargs) -> None:
	frappe.enqueue(
		method,
		queue="long",
		job_id=f"one-ai-{job}",
		deduplicate=True,
		enqueue_after_commit=True,
		**kwargs,
	)


def _comment(doctype: str, name: str, content: str) -> None:
	"""A comment in OneAI's name on a record's timeline."""
	if not content:
		return
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": doctype,
			"reference_name": name,
			"content": content,
			"comment_email": AUTHOR,
			"comment_by": "OneAI",
		}
	).insert(ignore_permissions=True)


def _refresh(doctype: str, name: str, *others: str) -> None:
	"""Tell an open form, and the applicant list, that OneAI wrote to them."""
	frappe.publish_realtime("list_update", {"doctype": "Job Applicant"}, after_commit=True)
	for one in (name, *others):
		kind = doctype if one == name else "Job Applicant"
		frappe.publish_realtime(
			"doc_update",
			{"doctype": kind, "name": one, "modified": str(frappe.db.get_value(kind, one, "modified"))},
			doctype=kind,
			docname=one,
			after_commit=True,
		)
