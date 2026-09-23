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

#: The switches in HR Settings, and what each is when nobody has touched it.
SWITCHES = {
	"one_ai_screen": 1,
	"one_ai_prepare": 1,
	"one_ai_record": 1,
	"one_ai_transcribe": 1,
	"one_keep_recordings_days": 365,
}

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
	"""The OneAI user, and the hiring switches at their defaults.

	A Single keeps no value for a field added after it was first saved, and a
	Check read back from nothing is 0 — so a switch meant to start on would
	start off. Written once here, and a workspace's own choice after that is
	never touched.
	"""
	if not frappe.db.exists("User", AUTHOR):
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

	held = set(frappe.db.sql_list("select field from `tabSingles` where doctype = 'HR Settings'"))
	for key, value in SWITCHES.items():
		if key not in held:
			frappe.db.set_single_value("HR Settings", key, value)


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
	answer = unaliased(read(said), _aliases(pool, doc))
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
	answer = unaliased(read(said), _aliases(pool))
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
	lines.append("What a strong applicant has:\n" + (criteria or "(not written — judge against the description)"))
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
