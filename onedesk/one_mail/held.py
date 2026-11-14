"""Risky mail, warned and held. Every message that arrives is scored
(risk.py) as it is filed (inbound.Arrival.as_dict). From WARN up its
warning is drawn above it; from HOLD up a new message is held: listed only
under Held, and handed to no rule, no out-of-office reply, no link to a
record and no agent until a person who holds the mailbox releases it,
which runs all of that then, or deletes it. A Mail Manager sets both
levels in OneMail's settings (`set_levels`); OneAI's own reading of a
message as spam or phishing adds to its score (`judged`)."""

import json
from email import message_from_string
from types import SimpleNamespace

import frappe
from frappe import _
from frappe.utils import cint

from onedesk.one_mail import risk

LEVELS = {"warn": 25, "hold": 50}
DEFAULTS = {key: f"one_mail_{key}_from" for key in LEVELS}
FOLDER = "@held"
VERDICTS = {"Phishing": "phishing", "Spam": "spam"}
KEPT_HEADERS = (
	"Auto-Submitted",
	"Precedence",
	"List-Id",
	"List-Unsubscribe",
	"X-Autoreply",
	"X-Autorespond",
	"In-Reply-To",
	"References",
)


def levels() -> dict[str, int]:
	"""The score a message is warned from, and held from: as a Mail Manager
	set them, else LEVELS."""
	said = {key: cint(frappe.db.get_default(DEFAULTS[key]) or value) for key, value in LEVELS.items()}
	return {"warn": said["warn"], "hold": max(said["hold"], said["warn"])}


def verdict_of(found: list[dict], at: dict, fresh: bool = True, released: bool = False) -> dict:
	"""What a message's signals make of it: its score, whether it is
	warned and whether it is held. Only a new message is held, and never
	one a person released. Pure."""
	score = risk.score(found)
	return {"score": score, "warned": score >= at["warn"], "held": bool(fresh and not released and score >= at["hold"])}


def headers_kept(mail) -> str:
	"""The headers a rule and an away reply read, kept with a held message
	so they read the same once it is released. Pure."""
	return "".join(f"{name}: {mail.get(name)}\n" for name in KEPT_HEADERS if mail.get(name))


def fields_of(arrival) -> dict:
	"""What a message arriving is filed with: its score, its signals, and
	whether it is held. Mail the mailbox sent is not scored."""
	if arrival.sent:
		return {}
	try:
		found = risk.of(arrival)
	except Exception:
		frappe.log_error(title="OneMail could not score a message")
		return {}
	said = verdict_of(found, levels(), fresh=getattr(arrival, "fresh", True))
	kept = {"found": found}
	if said["held"]:
		kept["headers"] = headers_kept(arrival.mail)
	return {"one_risk": said["score"], "one_held": int(said["held"]), "one_risks": json.dumps(kept) if found else None}


def kept_of(name: str) -> dict:
	return frappe.parse_json(frappe.db.get_value("Communication", name, "one_risks") or "{}") or {}


def is_held(name: str) -> bool:
	return bool(cint(frappe.db.get_value("Communication", name, "one_held")))


def judged(name: str, verdict: str) -> bool:
	"""OneAI's reading of a message as spam or phishing, added to its score.
	Held then if it reaches the level, unless a person released it, so
	nothing more is done with it. Whether it is held."""
	why = VERDICTS.get(verdict)
	if not why or not frappe.db.exists("Communication", name):
		return False
	kept = kept_of(name)
	found = [one for one in kept.get("found") or [] if one.get("why") != why] + [{"why": why}]
	said = verdict_of(found, levels(), released=bool(kept.get("released")))
	kept["found"] = sorted(found, key=lambda one: -risk.WEIGHTS.get(one["why"], 0))
	values = {"one_risk": said["score"], "one_risks": json.dumps(kept)}
	if said["held"]:
		values["one_held"] = 1
	frappe.db.set_value("Communication", name, values, update_modified=False)
	if said["held"]:
		_recount(name)
	return said["held"] or is_held(name)


def said_of(row) -> dict | None:
	"""A message's warning, as the conversation draws it: whether it is
	held, and why, in plain words. None when there is nothing to warn of."""
	at = levels()
	held = bool(cint(row.get("one_held")))
	if not held and cint(row.get("one_risk")) < at["warn"]:
		return None
	found = (frappe.parse_json(row.get("one_risks") or "{}") or {}).get("found") or []
	copied = next((one.get("of") for one in found if one.get("why") == "lookalike"), None)
	return {
		"held": int(held),
		"score": cint(row.get("one_risk")),
		"imitates": copied,
		"reasons": [said for said in (risk.words(one) for one in found) if said],
	}


def count(accounts: list[str]) -> dict[str, int]:
	"""How many messages each mailbox holds back."""
	if not accounts:
		return {}
	from frappe.query_builder.functions import Count

	C = frappe.qb.DocType("Communication")
	rows = (
		frappe.qb.from_(C)
		.select(C.email_account, Count("*").as_("held"))
		.where(C.email_account.isin(accounts) & (C.one_held == 1) & (C.communication_medium == "Email"))
		.groupby(C.email_account)
		.run(as_dict=True)
	)
	return {row.email_account: cint(row.held) for row in rows}


def folder(account: str, held: int) -> dict:
	"""Held, as the page lists it beside a mailbox's folders."""
	return {
		"name": FOLDER,
		"account": account,
		"path": FOLDER,
		"label": _("Held"),
		"kind": "Held",
		"unread": held,
		"total": held,
		"delimiter": None,
	}


def _rows(names) -> list:
	from onedesk.one_mail import actions

	rows = actions._rows(names)
	return [row for row in rows if is_held(row.name)]


def _recount(name: str) -> None:
	from onedesk.one_mail import actions

	row = frappe.db.get_value("Communication", name, ["email_account", "one_folder"], as_dict=True)
	if row and row.email_account:
		actions.recount(row.email_account, row.one_folder)


@frappe.whitelist(methods=["POST"])
def release(names) -> int:
	"""Held messages let into their folders, by somebody who holds their
	mailbox. Then what was held back runs, as if each had just arrived: its
	links to records, the mailbox's rules, an away reply and OneAI's
	reading. One held only once OneAI had read it already ran all of that,
	so nothing runs again."""
	from onedesk.one_ai.reading import pipeline
	from onedesk.one_mail import linking, rules

	rows = _rows(names)
	for row in rows:
		kept = kept_of(row.name)
		waiting = "headers" in kept
		mail = message_from_string(kept.pop("headers", "") or "")
		kept["released"] = frappe.session.user
		frappe.db.set_value("Communication", row.name, {"one_held": 0, "one_risks": json.dumps(kept)}, update_modified=False)
		if waiting:
			doc = frappe.get_doc("Communication", row.name)
			arrival = SimpleNamespace(mail=mail, fresh=True)
			linking.arrived(doc)
			rules.after(doc, arrival)
			pipeline.mail_arrived(doc, arrival)
		_recount(row.name)
	return len(rows)


@frappe.whitelist(methods=["POST"])
def discard(names) -> int:
	"""Held messages deleted, by somebody who holds their mailbox: into
	Trash, still warned, and never run through the rules."""
	from onedesk.one_mail import actions

	rows = _rows(names)
	for row in rows:
		frappe.db.set_value("Communication", row.name, "one_held", 0, update_modified=False)
	if rows:
		actions.delete([row.name for row in rows])
	return len(rows)


@frappe.whitelist()
def settings() -> dict:
	"""The levels, for OneMail's settings: what they are and what they
	start at."""
	from onedesk.one_mail.holders import _admin

	_admin("policy")
	return {**levels(), "defaults": LEVELS, "most": risk.MOST}


@frappe.whitelist(methods=["POST"])
def set_levels(warn: int, hold: int) -> dict:
	"""The score a message is warned from and held from, each 1 to 100, the
	second no lower than the first. Mail already filed keeps its score; a
	message held stays held until somebody releases it."""
	from onedesk.one_mail.holders import _admin

	_admin("policy")
	warn, hold = cint(warn), cint(hold)
	if not (1 <= warn <= risk.MOST and 1 <= hold <= risk.MOST):
		frappe.throw(_("Choose a score from 1 to {0}.").format(risk.MOST))
	if hold < warn:
		frappe.throw(_("Hold From can't be lower than Warn From."))
	frappe.db.set_default(DEFAULTS["warn"], str(warn))
	frappe.db.set_default(DEFAULTS["hold"], str(hold))
	return levels()
