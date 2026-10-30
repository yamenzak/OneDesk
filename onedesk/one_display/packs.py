"""Voice packs: a call said from pieces. A pack is one language, voice and
tone; it keeps each letter, number, word and counter name once, as files on
the pack (OneCloud shows them under it), and a screen plays a ticket's
pieces end to end. A piece a pack lacks is asked for in the background the
first time a call needs it (one_display/AGENTS.md, Voice packs)."""

import re
from typing import Annotated

import frappe
from frappe import _

from onedesk.one import apps

DOCTYPE = "Voice Pack"
CLIP = "Voice Pack Clip"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
NUMBERS = 1000
SEPARATORS = {"-": "dash", "/": "slash", ".": "point"}
# where "1828" said whole is "1 thousand 828"; elsewhere the thousands
# change the words around them, so the whole sentence is recorded instead
THOUSANDS = frozenset({"en"})
READINGS = ("Auto", "Digit by Digit", "Whole Number")
DIGITS_FROM = 4


def words(lang: str) -> dict:
	"""The words of a call, in its language."""
	return {
		"ticket": _("Ticket number", lang=lang),
		"go_to": _("go to", lang=lang),
		"thousand": _("thousand", lang=lang),
		"dash": _("dash", lang=lang),
		"slash": _("slash", lang=lang),
		"point": _("point", lang=lang),
	}


def _number(run: str, reading: str, lang: str) -> list[str] | None:
	"""A run of digits as pieces, or None where a pack cannot say it. Pure."""
	run = run.lstrip("0") or "0"
	if reading == "Digit by Digit" or (reading != "Whole Number" and len(run) >= DIGITS_FROM):
		return [f"n:{digit}" for digit in run]
	value = int(run)
	if value < NUMBERS:
		return [f"n:{value}"]
	if value < NUMBERS * NUMBERS and lang.split("-")[0] in THOUSANDS:
		rest = value % NUMBERS
		return [f"n:{value // NUMBERS}", "w:thousand", *([f"n:{rest}"] if rest else [])]
	return None


def pieces(ticket: str, reading: str = "Auto", lang: str = "en") -> list[str] | None:
	"""A ticket as a voice says it, piece by piece: A1828 is A, 1, 8, 2, 8;
	1828-3 whole is 1 thousand 828, dash, 3. Pure."""
	out = []
	for part in re.findall(r"\d+|[^\W\d_]|[-/.]", ticket or ""):
		if part.isdigit():
			said = _number(part, reading, lang)
			if said is None:
				return None
			out += said
		elif part in SEPARATORS:
			out.append(f"w:{SEPARATORS[part]}")
		else:
			out.append(f"l:{part.upper()}")
	return out or None


def call(ticket: str, counter: str, reading: str = "Auto", lang: str = "en") -> list[str] | None:
	"""The whole call as pieces: the word for ticket, the ticket, where to go."""
	said = pieces(ticket, reading, lang)
	if said is None:
		return None
	return ["w:ticket", *said, "w:go_to", *([f"c:{counter}"] if counter else [])]


def text(piece: str, lang: str) -> tuple[str, str]:
	"""What a piece says and its kind."""
	kind, _sep, value = piece.partition(":")
	if kind == "l":
		return value, "Letter"
	if kind == "n":
		return value, "Number"
	if kind == "c":
		return _("counter {0}", lang=lang).format(value), "Counter"
	return words(lang).get(value, value), "Word"


def name_of(lang: str, voice: str, tone: str) -> str:
	language = frappe.db.get_value("Language", lang, "language_name") or lang
	return f"{language} · {voice} · {tone}"


def pack(lang: str, voice: str, tone: str = "Announcement", make: bool = True) -> str | None:
	"""The pack of a language, voice and tone, made empty the first time."""
	found = frappe.db.get_value(DOCTYPE, {"language": lang, "voice": voice, "tone": tone})
	if found or not make:
		return found
	return frappe.get_doc({"doctype": DOCTYPE, "language": lang, "voice": voice, "tone": tone}).insert(ignore_permissions=True).name


def clips(name: str, wanted: list[str] | None = None) -> dict:
	"""A pack's recordings by piece."""
	filters = {"parent": name, "parenttype": DOCTYPE}
	if wanted is not None:
		filters["piece"] = ["in", wanted or [""]]
	return dict(frappe.get_all(CLIP, filters=filters, fields=["piece", "audio"], as_list=True))


def voiced(ticket: str, counter: str, lang: str, voice: str | None, reading: str = "Auto", tone: str = "Announcement") -> list[str] | None:
	"""The recordings a call is played from, in order. An empty list when the
	pack still lacks a piece, which is asked for now; None when a pack
	cannot say this ticket at all, so the whole sentence is recorded."""
	if not voice or not apps.ai_on():
		return []
	said = call(ticket, counter, reading or "Auto", lang)
	if said is None:
		return None
	name = pack(lang, voice, tone)
	have = clips(name, list(set(said)))
	missing = [one for one in dict.fromkeys(said) if not have.get(one)]
	if missing:
		ask(name, missing)
		return []
	return [have[one] for one in said]


def ask(name: str, wanted: list[str]) -> None:
	"""Have the pieces recorded in the background, once each, by one job a pack."""
	asked = f"one_display_pack_wanted:{name}"
	for one in wanted:
		frappe.cache.sadd(asked, one)
	frappe.enqueue(
		"onedesk.one_display.packs.fill",
		queue="long",
		job_id=f"one_display_pack:{name}",
		deduplicate=True,
		name=name,
	)


def fill(name: str) -> None:
	"""Record what was asked of a pack until nothing is left."""
	asked = f"one_display_pack_wanted:{name}"
	while True:
		wanted = [one.decode() if isinstance(one, bytes) else one for one in frappe.cache.smembers(asked) or []]
		if not wanted:
			return
		frappe.cache.srem(asked, *wanted)
		have = clips(name, wanted)
		for piece in wanted:
			if not have.get(piece):
				record(name, piece)


def record(name: str, piece: str) -> str | None:
	"""Say one piece in the pack's voice and keep it; again, in place."""
	from onedesk.one_display import voices

	doc = frappe.db.get_value(DOCTYPE, name, ["language", "voice", "tone"], as_dict=True)
	said, kind = text(piece, doc.language)
	try:
		sound = voices.say(said, doc.language, doc.voice, doc.tone, f"OneDisplay voice pack {name}")
	except Exception:
		frappe.log_error(title="OneDisplay voice pack")
		return None
	if not sound:
		return None
	label = piece.partition(":")[2] if kind == "Counter" else said
	file_name = re.sub(r'[\\/:*?"<>|]', " ", f"{_(kind, lang=doc.language)} {label}.wav")
	saved = voices.attach(DOCTYPE, name, file_name, sound, quiet=True)
	row = frappe.db.get_value(CLIP, {"parent": name, "parenttype": DOCTYPE, "piece": piece}, ["name", "audio"], as_dict=True)
	if row:
		frappe.db.set_value(CLIP, row.name, "audio", saved.file_url, update_modified=False)
		voices.replace(row.audio, DOCTYPE, name, saved.name)
	else:
		count = frappe.db.count(CLIP, {"parent": name, "parenttype": DOCTYPE})
		frappe.get_doc(
			{"doctype": CLIP, "parent": name, "parenttype": DOCTYPE, "parentfield": "clips", "idx": count + 1, "piece": piece, "kind": kind, "said": said, "audio": saved.file_url}
		).db_insert()
		frappe.db.set_value(DOCTYPE, name, "made", count + 1, update_modified=False)
	frappe.db.commit()
	return saved.file_url


def everything(name: str) -> list[str]:
	"""Every piece a pack may need: each letter and every ticket prefix, the
	numbers below a thousand, the words, and each counter's name."""
	lang = frappe.db.get_value(DOCTYPE, name, "language")
	prefixes = {letter for prefix in frappe.get_all("Queue Service", pluck="prefix") for letter in re.findall(r"[^\W\d_]", prefix or "")}
	counters = sorted(set(frappe.get_all("Queue Counter", pluck="counter")) - {None, ""})
	said = ["w:ticket", "w:go_to", *(f"w:{one}" for one in SEPARATORS.values())]
	if lang.split("-")[0] in THOUSANDS:
		said.append("w:thousand")
	said += [f"l:{one}" for one in sorted(set(LETTERS) | {one.upper() for one in prefixes})]
	said += [f"n:{one}" for one in range(NUMBERS)]
	return said + [f"c:{one}" for one in counters]


def covers(name: str) -> dict:
	"""How much of each kind a pack has said, out of what it may need."""
	have = clips(name)
	out = {}
	for piece in everything(name):
		kind = text(piece, "en")[1]
		made, of = out.get(kind, (0, 0))
		out[kind] = (made + (1 if have.get(piece) else 0), of + 1)
	return {kind: {"made": made, "of": of} for kind, (made, of) in out.items()}


def _may(name: str) -> None:
	frappe.get_doc(DOCTYPE, name).check_permission("write")
	apps.refuse_ai()


@frappe.whitelist(methods=["POST"])
def make(name: Annotated[str, "The voice pack."]) -> int:
	"""Record every piece the pack still lacks, in the background."""
	_may(name)
	have = clips(name)
	missing = [one for one in everything(name) if not have.get(one)]
	if missing:
		ask(name, missing)
	return len(missing)


@frappe.whitelist(methods=["POST"])
def again(name: Annotated[str, "The voice pack."]) -> int:
	"""Record every piece the pack has once more, each in its place."""
	_may(name)
	kept = list(clips(name))
	frappe.enqueue("onedesk.one_display.packs.redo", queue="long", job_id=f"one_display_pack_again:{name}", deduplicate=True, name=name, kept=kept)
	return len(kept)


def redo(name: str, kept: list[str]) -> None:
	for piece in kept:
		record(name, piece)


@frappe.whitelist(methods=["POST"])
def of_zone(zone: Annotated[str, "The sound zone."]) -> str:
	"""The pack a zone's calls are said from, made empty the first time."""
	doc = frappe.get_doc("Sound Zone", zone)
	doc.check_permission("read")
	if not doc.voice:
		frappe.throw(_("Choose the zone's voice first."))
	return pack(doc.voice_language or frappe.db.get_default("lang") or "en", doc.voice)
