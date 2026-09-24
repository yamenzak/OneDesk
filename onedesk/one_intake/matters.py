"""Stage 5 of Intake: which matter a document belongs to, and what it changes.

Most of what arrives is not new business. It is the reminder for last month's
invoice, "sorry, forgot the attachment", the corrected invoice, "paid,
thanks", or the scan of a letter that also came by mail. A **matter** needs no
doctype of its own: it is its first document's Reading, and every later
Reading about it names that one in `matter` (docs/INTAKE.md §5.3).

A document is placed strongest first, stopping at the first that is sure:

1. **its mail**: an attachment belongs where the message carrying it does,
   and the other way round;
2. **the thread**: an answer is about what it answers, unless it names a
   different document of its own;
3. **a reference**: an invoice, order or case number an earlier document of
   the same party carried;
4. **the party and kind**, when that party has exactly one open matter of
   that kind;
5. **OneAI**, given that party's open matters as a shortlist, only where a
   model may be asked at all.

Before any of that, a **copy** (the same kind, number, amount and date from
the same party) is recognised and does nothing new. The subject line is never
a key.

**What it changes** is decided without a model where the facts say it (a
reminder nudges, a different amount updates, an automatic reply is nothing
new, a payment advice closes), and by the same one question to the model
otherwise.

**Quiet time.** Reading and understanding start at once, so search finds a
message in seconds. Acting (filing, and what later stages make) waits until
the matter has been quiet for Intake Settings' Quiet Minutes, then runs once
over the burst. Phishing, and money or deadlines due within a day, do not
wait.
"""

import json
import re
from datetime import timedelta

import frappe
from frappe.utils import add_to_date, cint, flt, getdate, now_datetime, today

#: How long an open matter of a party is a candidate for a new document.
RECENT_DAYS = 180

#: How many open matters the model is shown to choose from.
SHORTLIST = 5

PLACE = "intake_place"
CHANGES = ("New", "Nudge", "Update", "Completion", "Answer", "Closing", "Nothing New")

#: Kinds that follow another document rather than start something.
FOLLOWERS = {
	"Reminder": ("Invoice", "Credit Note", "Tax Assessment", "Letter From an Authority"),
	"Payment Advice": ("Invoice",),
	"Order Confirmation": ("Order",),
	"Delivery Note": ("Order", "Order Confirmation"),
	"Credit Note": ("Invoice",),
}


# ------------------------------------------------------------------ pure


def compact(value) -> str:
	"""A number as it is compared, and as Reading Reference stores it
	(facts.compact): letters and digits only, lower case. Pure."""
	return re.sub(r"[^0-9a-z]", "", str(value or "").lower())


def is_copy(new: dict, earlier: dict) -> bool:
	"""Whether two readings say the same thing: one document arriving twice
	(a scan of a PDF that also came by mail, an invoice in the mail body and
	as a file). Pure."""
	if not new.get("kind") or new.get("kind") != earlier.get("kind"):
		return False
	if not new.get("number") or compact(new["number"]) != compact(earlier.get("number")):
		return False
	# The same number from somebody else, or from somebody not known yet, is
	# not the same document.
	if new.get("party") != earlier.get("party"):
		return False
	for key in ("gross", "issued_on"):
		if new.get(key) and earlier.get(key) and str(new[key]) != str(earlier[key]):
			if key == "gross" and abs(flt(new[key]) - flt(earlier[key])) < 0.005:
				continue
			return False
	return True


def by_reference(new: dict, candidates: list[dict]) -> dict | None:
	"""The earlier reading whose own number, or one of whose references, this
	one names. A number alone is not enough across parties: 4711 is somebody
	else's invoice too. Pure."""
	named = {compact(one) for one in new.get("refs") or [] if compact(one)}
	if not named:
		return None
	for one in candidates:
		if new.get("party") and one.get("party") and new["party"] != one["party"]:
			continue
		# This month's invoice on the same order is a new invoice, not a
		# correction of last month's: a document with its own, different
		# number of the same kind starts its own matter.
		if new.get("kind") == one.get("kind") and compact(new.get("number")) and compact(one.get("number")) and compact(new["number"]) != compact(one["number"]):
			continue
		theirs = {compact(one.get("number"))} | {compact(ref) for ref in one.get("refs") or []}
		if named & {each for each in theirs if len(each) >= 3}:
			return one
	return None


def by_party(new: dict, open_matters: list[dict]) -> dict | None:
	"""The one open matter of this party a follower belongs to. Two open
	invoices from the same supplier and a reminder naming neither: not sure,
	so not placed here. Pure."""
	if not new.get("party"):
		return None
	wanted = FOLLOWERS.get(new.get("kind") or "", ())
	# The same kind follows only when it has no number of its own: a letter
	# after a letter, never this month's invoice after last month's.
	same = not compact(new.get("number"))
	fits = [one for one in open_matters if one.get("party") == new["party"] and (one.get("kind") in wanted or (same and one.get("kind") == new.get("kind")))]
	return fits[0] if len(fits) == 1 else None


def change_of(new: dict, head: dict | None, automatic: bool = False) -> str | None:
	"""What a document changes in its matter, where the facts say it without
	a model; None when only reading it can tell. Pure."""
	if head is None:
		return "New"
	if automatic or new.get("verdict") in ("Notification", "Newsletter"):
		return "Nothing New"
	kind, before = new.get("kind"), head.get("kind")
	if kind == "Reminder":
		return "Nudge"
	if kind == "Payment Advice" or new.get("paid_how") == "Already Paid":
		return "Closing"
	if kind and kind == before and new.get("number") and compact(new.get("number")) == compact(head.get("number")):
		if new.get("gross") and head.get("gross") and abs(flt(new["gross"]) - flt(head["gross"])) >= 0.005:
			return "Update"
		return "Nothing New"
	if kind in FOLLOWERS and before in FOLLOWERS[kind]:
		return "Answer" if kind in ("Order Confirmation", "Delivery Note") else "Update"
	return None


def urgent(dates: list, today_: str, verdict: str | None = None) -> bool:
	"""Whether acting must not wait: phishing, or a due date or deadline
	within a day. Pure."""
	if verdict == "Phishing":
		return True
	limit = getdate(today_) + timedelta(days=1)
	return any(one.get("what") in ("Due", "Deadline") and one.get("date") and getdate(one["date"]) <= limit for one in dates or [])


# ------------------------------------------------------------------ on the site


def facts_of(doc) -> dict:
	"""A Reading as the pure functions compare it."""
	party = (doc.get("party_doctype"), doc.get("party_name")) if doc.get("party_name") else None
	return {
		"name": doc.get("name"),
		"kind": doc.get("kind"),
		"number": doc.get("number"),
		"gross": doc.get("gross"),
		"issued_on": str(doc.get("issued_on") or "") or None,
		"verdict": doc.get("verdict"),
		"paid_how": doc.get("paid_how"),
		"party": party,
		"title": doc.get("title"),
		"summary": doc.get("summary"),
		"refs": [row.get("value") for row in doc.get("refs") or []],
	}


def place(reading) -> None:
	"""Put an understood Reading in its matter, say what it changes, and when
	to act on it. Saves nothing; the caller does."""
	from onedesk.one_intake import filing

	belongs = filing.records([row.as_dict() for row in reading.parties])
	if belongs:
		reading.party_doctype, reading.party_name = belongs[0]
	if reading.verdict in ("Spam", "Phishing", "Advertising"):
		_head(reading)
	else:
		_place(reading)
	quiet = cint(frappe.db.get_single_value("Intake Settings", "quiet_minutes"))
	now = now_datetime()
	dates = [row.as_dict() for row in reading.dates]
	reading.act_after = now if not quiet or urgent(dates, today(), reading.verdict) else add_to_date(now, minutes=quiet)


def _head(reading, placed_by: str | None = None) -> None:
	reading.matter, reading.change, reading.placed_by = reading.name, "New", placed_by
	reading.matter_state = "Open"


def _place(reading) -> None:
	new = facts_of(reading)
	earlier = _earlier(reading)
	for one in earlier:
		if is_copy(new, one):
			reading.copy_of = one["name"]
			_join(reading, one, "Copy", "Nothing New")
			return
	held = _by_mail(reading) or _by_thread(reading)
	if held:
		_join(reading, held[0], held[1])
		return
	found = by_reference(new, earlier)
	if found:
		_join(reading, found, "Reference")
		return
	open_matters = [one for one in earlier if one["name"] == one.get("matter") and one.get("matter_state") != "Closed"]
	found = by_party(new, open_matters)
	if found:
		_join(reading, found, "Party")
		return
	# A document with its own number that follows nothing (an invoice, an
	# order) starts its own matter; asking a model would only cost credits.
	starts = bool(compact(new.get("number"))) and new.get("kind") not in FOLLOWERS
	if reading.on_behalf_of and not cint(reading.history) and new["party"] and not starts:
		shortlist = [one for one in open_matters if one.get("party") == new["party"]][:SHORTLIST]
		if shortlist:
			said = _ask(reading, new, shortlist)
			chosen = next((one for one in shortlist if one["name"] == said.get("matter")), None)
			if chosen:
				_join(reading, chosen, "OneAI", said.get("change") if said.get("change") in CHANGES else None)
				return
	_head(reading)


def _join(reading, one: dict, placed_by: str, change: str | None = None) -> None:
	head = frappe.get_doc("Reading", one.get("matter") or one["name"])
	reading.matter, reading.placed_by, reading.matter_state = head.name, placed_by, None
	automatic = bool(cint(reading.automatic))
	reading.change = change or change_of(facts_of(reading), facts_of(head), automatic) or _asked_change(reading, head) or "Update"
	if reading.change == "Closing" and head.matter_state != "Closed":
		head.db_set("matter_state", "Closed", update_modified=False)
	if not reading.party_name and head.party_name:
		reading.party_doctype, reading.party_name = head.party_doctype, head.party_name


def _earlier(reading) -> list[dict]:
	"""Understood readings from the last months that could be this one's
	matter, newest first: the same party's, and any that share a number."""
	since = add_to_date(now_datetime(), days=-RECENT_DAYS)
	numbers = {compact(reading.number)} | {compact(row.value) for row in reading.refs}
	numbers.discard("")
	names = set()
	if reading.party_name:
		names |= set(frappe.get_all("Reading", filters={"party_doctype": reading.party_doctype, "party_name": reading.party_name, "name": ["!=", reading.name], "creation": [">=", since], "state": "Understood"}, pluck="name", limit=50))
	if numbers:
		values = [one for one in numbers if len(one) >= 3]
		if values:
			names |= set(frappe.get_all("Reading Reference", filters={"compact": ["in", values], "parent": ["!=", reading.name]}, pluck="parent", limit=50))
			# An earlier document's own number, named here as a reference.
			written = {one for one in [reading.number, *(row.value for row in reading.refs)] if one}
			names |= set(frappe.get_all("Reading", filters={"number": ["in", list(written)], "name": ["!=", reading.name]}, pluck="name", limit=20))
	out = []
	held = frappe.get_all("Reading", filters={"name": ["in", list(names)], "state": "Understood", "matter": ["is", "set"]}, pluck="name") if names else []
	for name in held:
		doc = frappe.get_doc("Reading", name)
		out.append({**facts_of(doc), "matter": doc.matter, "matter_state": frappe.db.get_value("Reading", doc.matter, "matter_state"), "creation": doc.creation})
	return sorted(out, key=lambda one: one["creation"], reverse=True)


def _by_mail(reading) -> tuple | None:
	"""A message and the files attached to it are one matter."""
	structured = json.loads(reading.structured or "{}")
	for name in structured.get("attachments") or []:
		held = frappe.db.get_value("Reading", name, ["name", "matter", "kind"], as_dict=True)
		if held and held.matter and held.kind:
			return {"name": held.name, "matter": held.matter}, "Attachment"
	if reading.source_doctype == "File":
		message = frappe.db.get_value("File", reading.source_name, ["attached_to_doctype", "attached_to_name"], as_dict=True)
		if message and message.attached_to_doctype == "Communication":
			key = _mail_key(message.attached_to_name)
			held = frappe.db.get_value("Reading", {"key": key}, ["name", "matter"], as_dict=True)
			if held and held.matter:
				return {"name": held.name, "matter": held.matter}, "Attachment"
	return None


def _by_thread(reading) -> tuple | None:
	"""An answer belongs to what it answers, unless it names a document of
	its own that the thread has not seen: a new request in an old thread is a
	new matter in the same conversation."""
	if reading.source_doctype != "Communication":
		return None
	thread, own = frappe.db.get_value("Communication", reading.source_name, ["one_thread", "message_id"]) or (None, None)
	if not thread:
		return None
	for name in frappe.get_all("Communication", filters={"one_thread": thread, "name": ["!=", reading.source_name]}, pluck="name", order_by="communication_date asc"):
		held = frappe.db.get_value("Reading", {"key": _mail_key(name)}, ["name", "matter", "number", "kind"], as_dict=True)
		if not held or not held.matter:
			continue
		if reading.number and held.number and compact(reading.number) != compact(held.number) and reading.kind == held.kind:
			return None
		return {"name": held.name, "matter": held.matter}, "Thread"
	return None


def _mail_key(communication: str) -> str:
	import hashlib

	message_id = frappe.db.get_value("Communication", communication, "message_id")
	return "mail-" + hashlib.md5((message_id or communication).encode()).hexdigest()


# ------------------------------------------------------------------ asking


def _ask(reading, new: dict, shortlist: list[dict]) -> dict:
	"""The model chooses among a party's open matters, or none."""
	from onedesk.one_intake import understand

	lines = [
		f"- {one['name']}: {one.get('kind') or ''} {one.get('number') or ''}, {one.get('title') or ''}. {one.get('summary') or ''}".strip()
		for one in shortlist
	]
	text = (
		"Open matters with this party:\n" + "\n".join(lines) + "\n\nThe new document:\n"
		f"{new.get('kind') or ''} {new.get('number') or ''}, {new.get('title') or ''}. {new.get('summary') or ''}\n---\n{(reading.text or '')[:3000]}\n---"
	)
	try:
		return understand._ask(PLACE, text, reading.name) or {}
	except Exception:
		frappe.log_error(title=f"Intake could not place {reading.name}")
		return {}


def _asked_change(reading, head) -> str | None:
	"""What changed, when the facts do not say it: asked only where a model
	may be asked."""
	if not reading.on_behalf_of or cint(reading.history):
		return None
	said = _ask(reading, facts_of(reading), [{**facts_of(head), "name": head.name}])
	return said.get("change") if said.get("change") in CHANGES else None


# ------------------------------------------------------------------ acting, once it is quiet


def due() -> None:
	"""Every minute: act on the matters that have been quiet long enough,
	each once, over everything that arrived in the burst."""
	now = now_datetime()
	waiting = frappe.get_all(
		"Reading",
		filters={"state": "Understood", "acted_on": ["is", "not set"], "act_after": ["<=", now]},
		fields=["name", "matter"],
		order_by="creation asc",
		limit=200,
	)
	busy = set(
		frappe.get_all("Reading", filters={"state": "Understood", "acted_on": ["is", "not set"], "act_after": [">", now]}, pluck="matter")
	)
	for one in waiting:
		if one.matter in busy:
			continue
		act_now(one.name)


def act_now(name: str) -> None:
	"""Act on one understood document: make the party it needs, file it, then
	make what it asks for (planning.py)."""
	from onedesk.one_intake import filing

	if frappe.db.get_value("Reading", name, "acted_on"):
		return
	from onedesk.one_intake import planning

	frappe.db.set_value("Reading", name, "acted_on", now_datetime(), update_modified=False)
	frappe.db.commit()
	# The counterpart first, so the invoice is filed with the supplier just
	# made; then everything else, with the parties matched again.
	for step, then in (("parties", lambda: planning.run(name, "parties")), ("filing", lambda: filing.run(name)), ("the rest", lambda: planning.run(name, "rest"))):
		try:
			then()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Intake could not act on {name}: {step}")


def records_of(matter: str) -> list[tuple[str, str]]:
	"""The records a matter's documents were filed with or linked to."""
	readings = frappe.get_all("Reading", filters={"matter": matter}, pluck="name")
	if not readings:
		return []
	rows = frappe.get_all(
		"Intake Action",
		filters={"reading": ["in", readings], "kind": ["in", ("Attach", "Link")], "level": "Done"},
		fields=["target_doctype", "target_name"],
		order_by="creation asc",
	)
	out: list[tuple[str, str]] = []
	for row in rows:
		pair = (row.target_doctype, row.target_name)
		if row.target_doctype not in ("File", "Communication") and pair not in out and frappe.db.exists(*pair):
			out.append(pair)
	return out


def key(reading, what: str) -> str:
	"""An action's key within its matter: "a task to pay this invoice" exists
	once, however many reminders, copies and corrections arrive."""
	return f"{reading.matter or reading.name}|{what}"[:140]
