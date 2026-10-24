"""How far OneAI may read a mailbox: the OneAI tab of a mailbox in OneMail's
settings. One switch reaches everything that reads mail, so a mailbox turned
off is off for OneIntake's reading, for search by meaning and for the OneAI
panel's tools alike. A mailbox that is read can be held to sorting, to
reading and filing, or allowed to act; its attachments can be left to the
free reading; and its credits can be capped by the month, after which only
the free reading goes on until the month turns."""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

LEVELS = ("Sort Only", "Read and File", "Read, File and Act")
SORT, FILE, ACT = LEVELS
FIELDS = [
	"name",
	"email_id",
	"one_ai_off",
	"one_intake",
	"one_intake_for",
	"one_ai_level",
	"one_ai_attachments",
	"one_ai_limit",
	"one_ai_spent",
	"one_ai_month",
	"one_ai_skips",
]

#: What OneIntake does with a mailbox's mail, each its own switch on the
#: mailbox's OneAI tab, by the level it starts at. All are on until switched
#: off (`one_ai_skips`); `job_of` says which one an Intake Action is.
JOBS = {
	SORT: ("junk", "newsletters"),
	FILE: ("link", "attach", "tidy"),
	ACT: ("parties", "contacts", "enrich", "tasks", "events", "money", "hr", "projects", "agent"),
}

HEADS = {
	"junk": "junk",
	"newsletters": "newsletters",
	"advertising": "newsletters",
	"link": "link",
	"back": "link",
	"attach": "attach",
	"name": "tidy",
	"tags": "tidy",
	"file away": "tidy",
	"cut": "tidy",
	"party": "parties",
	"contact": "contacts",
	"enrich": "enrich",
	"employee": "hr",
	"document": "hr",
	"education": "hr",
	"leave": "hr",
	"resignation": "hr",
	"expense": "hr",
	"task": "tasks",
	"promise": "tasks",
	"event": "events",
	"books": "money",
	"project": "projects",
}

TWO = {"task|renew": "hr", "task|unordered": "money", "task|contract": "money", "task|never-received": "money"}


def job_of(key: str) -> str | None:
	"""The job an Intake Action's key says it is (JOBS), or None for one
	no switch covers. A key may start with its reading's or its matter's
	key. Pure."""
	parts = (key or "").split("|")
	if "agent" in parts:
		return "agent"
	for at in range(min(2, len(parts))):
		said = TWO.get("|".join(parts[at : at + 2])) or HEADS.get(parts[at])
		if said:
			return said
	return None


def skips(account: str | None) -> set[str]:
	"""The jobs switched off for a mailbox."""
	held = of(account)
	return set(frappe.parse_json(held.one_ai_skips) or []) if held and held.one_ai_skips else set()


def does(account: str | None, job: str | None) -> bool:
	"""Whether OneIntake may do this job with this mailbox's mail: always for
	a job no switch covers, and for anything not from a mailbox."""
	return not job or not account or job not in skips(account)


def month() -> str:
	return nowdate()[:7]


def of(account: str | None) -> dict | None:
	if not account:
		return None
	return frappe.db.get_value("Email Account", account, FIELDS, as_dict=True)


def may_read(account: str | None) -> bool:
	"""Whether OneAI may read this mailbox at all, asked or on its own."""
	held = of(account)
	return bool(held) and not held.one_ai_off


def reads(account: str | None) -> bool:
	"""Whether a mailbox's new mail is read at all, so its Ask OneAI rules
	can run (flow.needs_ai): OneAI may read it, New Mail is not Not Read,
	and OneIntake is on for the workspace."""
	from onedesk.one import apps

	held = of(account)
	return bool(held) and not held.one_ai_off and bool(held.one_intake) and apps.intake_on()


def used(held: dict) -> float:
	"""This month's credits, nothing when the count is from a month before."""
	return flt(held.one_ai_spent) if held.one_ai_month == month() else 0.0


def over(held: dict) -> bool:
	return bool(held.one_ai_limit) and used(held) >= flt(held.one_ai_limit)


def level(account: str | None) -> str | None:
	"""How far new mail here is read on its own: None when it is not, or when
	this month's credits are spent."""
	held = of(account)
	if not held or held.one_ai_off or not held.one_intake or over(held):
		return None
	return held.one_ai_level if held.one_ai_level in LEVELS else ACT


def halted(reading: str) -> bool:
	"""A reading of mail whose mailbox has since been turned off, switched
	off or run out of credits: no more model calls for it."""
	account = account_of("Reading", reading)
	return bool(account) and not level(account)


def reads_attachments(account: str | None) -> bool:
	held = of(account)
	return bool(held) and bool(held.one_ai_attachments)


def turned_off() -> list[str]:
	"""Mailboxes OneAI may not read, once per request."""
	cached = getattr(frappe.local, "one_ai_off", None)
	if cached is None:
		cached = frappe.local.one_ai_off = frappe.get_all("Email Account", filters={"one_ai_off": 1}, pluck="name")
	return cached


def not_indexed() -> list[str]:
	"""Mailboxes whose mail is not embedded for search by meaning: those OneAI
	may not read, and those it is not reading on its own."""
	cached = getattr(frappe.local, "one_ai_unindexed", None)
	if cached is None:
		cached = frappe.local.one_ai_unindexed = frappe.get_all(
			"Email Account", or_filters={"one_ai_off": 1, "one_intake": 0}, pluck="name"
		)
	return cached


def account_of(doctype: str, name: str) -> str | None:
	"""The mailbox a message, a file on a message or a reading of either
	came from."""
	if doctype == "Communication":
		return frappe.db.get_value("Communication", name, "email_account")
	if doctype == "File":
		held = frappe.db.get_value("File", name, ["attached_to_doctype", "attached_to_name"], as_dict=True)
		if held and held.attached_to_doctype == "Communication":
			return account_of("Communication", held.attached_to_name)
		return None
	if doctype == "Reading":
		held = frappe.db.get_value("Reading", name, ["source_doctype", "source_name", "part_of"], as_dict=True)
		if not held:
			return None
		if held.source_doctype in ("Communication", "File") and held.source_name:
			return account_of(held.source_doctype, held.source_name)
		if held.part_of and held.part_of != name:
			return account_of("Reading", held.part_of)
	return None


def readable(doctype: str, name: str) -> bool:
	"""Whether OneAI may read this message, file or reading: anything not from
	a mailbox, or from one it may read."""
	account = account_of(doctype, name)
	return not account or account not in turned_off()


def refuse(account: str | None) -> None:
	if account and account in turned_off():
		frappe.throw(
			_("OneAI is turned off for {0}.").format(frappe.db.get_value("Email Account", account, "email_id") or account),
			frappe.PermissionError,
		)


def spent(reference: str | None, credits) -> None:
	"""A model call made for a reading of mail, or for a message (a rule's
	reply), adds to its mailbox's month, and
	the mailbox's holders hear once when the limit is reached."""
	if not reference or not flt(credits):
		return
	kind = next((one for one in ("Reading", "Communication") if frappe.db.exists(one, reference)), None)
	if not kind:
		return
	account = account_of(kind, reference)
	held = of(account)
	if not held:
		return
	before = used(held)
	after = before + flt(credits)
	frappe.db.set_value(
		"Email Account", account, {"one_ai_spent": after, "one_ai_month": month()}, update_modified=False
	)
	if held.one_ai_limit and before < flt(held.one_ai_limit) <= after:
		from onedesk.one_mail import tell

		tell.oneai_limit_reached(held)


def forget(account: str) -> None:
	"""A mailbox no longer read: what search by meaning held of its mail goes."""
	frappe.db.sql(
		"""delete from `tabAI Chunk` where
			(source_doctype = 'Communication' and source_name in
				(select name from `tabCommunication` where email_account = %(account)s))
			or (source_doctype = 'Reading' and source_name in
				(select r.name from `tabReading` r join `tabCommunication` m
					on r.source_doctype = 'Communication' and r.source_name = m.name
				where m.email_account = %(account)s))
			or (source_doctype = 'Reading' and source_name in
				(select r.name from `tabReading` r join `tabFile` f
					on r.source_doctype = 'File' and r.source_name = f.name
				join `tabCommunication` m on f.attached_to_doctype = 'Communication' and f.attached_to_name = m.name
				where m.email_account = %(account)s))""",
		{"account": account},
	)


@frappe.whitelist()
def settings_of(account: str) -> dict:
	"""A mailbox's OneAI tab: whether OneAI may read it, whether and how far it
	reads new mail on its own, attachments, and the month's credits."""
	from onedesk.one import apps
	from onedesk.one_mail import holders

	holders.sees(account)
	held = of(account)
	return {
		"ai": apps.ai_on(),
		"on": not held.one_ai_off,
		"reads": bool(held.one_intake),
		"for": frappe.utils.get_fullname(held.one_intake_for) if held.one_intake_for else None,
		"level": held.one_ai_level if held.one_ai_level in LEVELS else ACT,
		"attachments": bool(held.one_ai_attachments),
		"limit": held.one_ai_limit or 0,
		"used": round(used(held), 2),
		"skips": sorted(skips(account)),
		"asks": asks_of(account),
		"may_manage": holders.may(account, "ai"),
	}


def asks_of(account: str) -> list[str]:
	"""The titles of a mailbox's rules that ask OneAI, which only run while
	its new mail is read."""
	from onedesk.one_mail import rules

	return [one.title or one.name for one in rules.rules_of(account, True)]


@frappe.whitelist(methods=["POST"])
def set_settings(
	account: str,
	on: int | None = None,
	reads: int | None = None,
	level: str | None = None,
	attachments: int | None = None,
	limit: int | None = None,
	skips: list | str | None = None,
) -> dict:
	"""Change a mailbox's OneAI tab. Its manager may (holders.may_manage); new
	mail is then read on behalf of whoever turned reading on."""
	from onedesk.one_intake import switches
	from onedesk.one_mail import holders

	holders.must(account, "ai")
	values = {}
	if on is not None:
		values["one_ai_off"] = 0 if int(on) else 1
	if reads is not None:
		if int(reads):
			switches._reading()
		values.update(
			{"one_intake": int(reads), "one_intake_for": frappe.session.user if int(reads) else None}
		)
		if int(reads):
			values["create_contact"] = 0
	if level is not None:
		if level not in LEVELS:
			frappe.throw(_("Choose one of {0}.").format(", ".join(_(one) for one in LEVELS)))
		values["one_ai_level"] = level
	if attachments is not None:
		values["one_ai_attachments"] = int(attachments)
	if limit is not None:
		values["one_ai_limit"] = max(0, int(limit or 0))
	if skips is not None:
		known = {job for jobs in JOBS.values() for job in jobs}
		said = frappe.parse_json(skips) if isinstance(skips, str) else skips
		values["one_ai_skips"] = frappe.as_json(sorted(set(said or []) & known), indent=None)
	if values:
		frappe.db.set_value("Email Account", account, values, update_modified=False)
		frappe.local.one_ai_off = frappe.local.one_ai_unindexed = None
	if values.get("one_ai_off") or values.get("one_intake") == 0:
		forget(account)
	return settings_of(account)
