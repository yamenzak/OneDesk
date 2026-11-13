"""The setup wizard on OneAdmin, before payment and while the workspace is
built: the guest calls of frontend/portal/src/pages/Start.vue at
/portal/start. What it offers is wizard_offer.py, the steps and how answers
are kept wizard_answers.py; one_admin/AGENTS.md, The signup page, says the
rest."""

import frappe
from frappe import _, _lt
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime

from onedesk.one import registry, setup_answers
from onedesk.one.registry import switches
from onedesk.one_admin import signup, site, wizard_answers, wizard_offer

A_MINUTE = 60
STARTS_A_MINUTE = 5
SAVES_A_MINUTE = 60
OPEN = ("New", "Paying", "Paid", "Provisioning")
PAID = ("Paid", "Provisioning", "Done")
MOST_EVENTS = 300
SAID = {
	"owner.first_name": _lt("Your first name is needed."),
	"owner.email": _lt("Enter a valid email address."),
	"companies": _lt("Check each company's name and country."),
	"time_zone": _lt("Choose a time zone."),
	"working_day": _lt("Check the working day's start and end."),
	"people": _lt("Check each person's email address and name."),
}


def boot() -> dict:
	"""What /portal/start starts with: the reader's language and its
	translations (www/portal.py)."""
	from frappe.boot import load_translations
	from frappe.utils.jinja_globals import is_rtl

	said = frappe._dict(lang=frappe.local.lang, rtl=is_rtl(), guest=True, me={}, tabs=[], account=[])
	load_translations(said)
	return said


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=SAVES_A_MINUTE, seconds=A_MINUTE)
def offer() -> dict:
	"""What the wizard asks from."""
	site.require_admin()
	return wizard_offer.offer()


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=STARTS_A_MINUTE, seconds=A_MINUTE)
def start(answers: str | dict, email: str | None = None, time_zone: str | None = None, events: str | list | None = None) -> dict:
	"""The signup made, once the owner and the first company are named: its
	answers so far, its lead, and the key that opens it again."""
	site.require_admin()
	if frappe.session.user != "Guest":
		email = frappe.db.get_value("User", frappe.session.user, "email") or frappe.session.user
	email = (email or "").strip().lower()
	said = frappe.parse_json(answers) or {}
	kept = _merged({"owner": {"email": email}}, "you", {"owner": said.get("owner") or {}})
	kept = _merged(kept, "company", {"companies": said.get("companies") or []})
	zone = signup.zone(time_zone)
	kept["time_zone"] = zone
	_checked(kept)
	first = (kept.get("companies") or [{}])[0]
	if not first.get("name") or not first.get("country"):
		frappe.throw(str(SAID["companies"]))
	asked = frappe.get_doc(
		{
			"doctype": "Account Request",
			"email": email,
			"workspace_name": first["name"],
			"slug": first["name"],
			"jurisdiction": "Global",
			"country": first["country"],
			"time_zone": zone,
			"status": "New",
			"step": "company",
			"answers": frappe.as_json(kept),
		}
	)
	for one in _events(events):
		_note(asked, *one)
	asked.insert(ignore_permissions=True)
	from onedesk.one_admin import sales

	sales.signed_up(asked.name)
	return {"request": asked.name, "key": asked.access_key, **_state(asked)}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=SAVES_A_MINUTE, seconds=A_MINUTE)
def resume(request: str, key: str) -> dict:
	"""Where a signup is, to carry on from it."""
	return _state(_open(request, key))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=SAVES_A_MINUTE, seconds=A_MINUTE)
def save(request: str, key: str, step: str, answers: str | dict | None = None, plan: str | None = None, region: str | None = None, events: str | list | None = None) -> dict:
	"""A step's answers kept, with its events: the plan and the region on
	the request itself, the rest in its answers."""
	asked = _open(request, key)
	paid = asked.status in PAID
	held = frappe.parse_json(asked.answers or "{}") or {}
	said = frappe.parse_json(answers) or {}
	at = _kind(step)
	if at == "apps" or "apps" in said:
		said["apps"] = switches.answer([id for id, yes in (said.get("apps") or {}).items() if yes])
	if at == "plan":
		_plan(asked, plan, paid)
	elif at == "region":
		_region(asked, region, paid)
	else:
		kept = _merged(held, step, said, paid)
		if at == "people":
			_seats(asked, kept)
		_checked(kept)
		asked.answers = frappe.as_json(kept)
		if step in ("company", "language"):
			_named(asked, kept)
	asked.step = step
	for one in _events(events):
		_note(asked, *one)
	asked.save(ignore_permissions=True, ignore_version=True)
	if at == "plan":
		from onedesk.one_admin import sales

		sales.signed_up(asked.name)
	return _state(asked)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=SAVES_A_MINUTE, seconds=A_MINUTE)
def note(request: str, key: str, step: str, event: str) -> dict:
	"""One event of a step, such as the page closed on it (sent as the
	page goes, with navigator.sendBeacon)."""
	asked = _open(request, key, finished_too=True)
	if not _note(asked, step, event):
		return {"ok": True}
	asked.save(ignore_permissions=True, ignore_version=True)
	if event == "Left":
		from onedesk.one_admin import sales

		sales.noted(asked, _("Left the setup at {0}.").format(_label(step)))
	return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=STARTS_A_MINUTE, seconds=A_MINUTE)
def pay(request: str, key: str) -> dict:
	"""The checkout for a signup whose answers are whole: Stripe's own page,
	drawn in the wizard (stripe.checkout)."""
	asked = _open(request, key)
	if asked.status not in ("New", "Paying") or asked.tenant:
		frappe.throw(_("This signup can no longer be paid for. Start again."))
	if not asked.offering or not frappe.db.get_value("Offering", asked.offering, "enabled"):
		frappe.throw(_("Choose a plan first."))
	held = frappe.parse_json(asked.answers or "{}") or {}
	try:
		setup_answers.check(held)
	except setup_answers.Invalid as wrong:
		frappe.throw(_said(wrong))
	from onedesk.one_admin import stripe

	return {"checkout": stripe.checkout(asked.name)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=STARTS_A_MINUTE, seconds=A_MINUTE)
def finish(request: str, key: str, events: str | list | None = None) -> dict:
	"""Every step answered or skipped: the build may set the workspace up
	(answers.answering), whether or not Stripe's word of the payment has
	come yet."""
	asked = _open(request, key)
	for one in _events(events):
		_note(asked, *one)
	asked.answered_on = now_datetime()
	asked.step = "done"
	asked.save(ignore_permissions=True, ignore_version=True)
	from onedesk.one_admin import sales

	sales.noted(asked, _("Finished the setup."))
	return _state(asked)


def _open(request: str, key: str, finished_too: bool = False):
	site.require_admin()
	asked = signup.owned(request, key)
	if not asked or asked.status not in OPEN or (asked.answered_on and not finished_too):
		frappe.throw(_("This signup can no longer be changed. Start again."), frappe.PermissionError)
	return asked


def _state(asked) -> dict:
	held = frappe.parse_json(asked.answers or "{}") or {}
	on = wizard_offer.on(held)
	return {
		"needed_by": {id: [registry.name(one) for one in switches.needed_by(id, on)] for id in on if switches.needed_by(id, on)},
		"status": asked.status,
		"paid": asked.status in PAID,
		"step": asked.step,
		"answers": held,
		"plan": asked.offering,
		"region": asked.jurisdiction,
		"slug": asked.slug,
		"email": asked.email,
		"steps": wizard_offer.steps(held),
		"seats": wizard_offer.seats(asked.offering),
		"apps_on": on,
	}


def _merged(held: dict, step: str, said: dict, paid: bool = False) -> dict:
	try:
		return wizard_answers.merge(held, step, said, paid)
	except wizard_answers.Refused as refused:
		frappe.throw(str(refused))
	except setup_answers.Invalid as wrong:
		frappe.throw(_said(wrong))


def _checked(kept: dict) -> None:
	email = (kept.get("owner") or {}).get("email")
	if email and not frappe.utils.validate_email_address(email):
		frappe.throw(str(SAID["owner.email"]))
	for one in kept.get("people") or []:
		if not frappe.utils.validate_email_address(one.get("email") or ""):
			frappe.throw(str(SAID["people"]))


def _said(wrong: setup_answers.Invalid) -> str:
	"""The first problem in the person's words, where there are some for it."""
	for line in wrong.wrong:
		at = line.split(" ", 1)[0]
		for path, said in SAID.items():
			if at == path or at.startswith(f"{path}[") or at.startswith(f"{path}."):
				return str(said)
	return _("Check the answers and try again.")


def _named(asked, kept: dict) -> None:
	"""The request takes the first company's name, country and time zone;
	a new name is checked as a new signup's is."""
	first = (kept.get("companies") or [{}])[0]
	asked.country = first.get("country") or asked.country
	asked.time_zone = kept.get("time_zone") or asked.time_zone
	if first.get("name") and first["name"] != asked.workspace_name:
		slug = signup.tidy_slug(first["name"])
		if slug != asked.slug:
			if frappe.db.exists("Tenant", slug) or frappe.db.exists("Account Request", {"slug": slug, "status": ["in", signup.HOLDING], "name": ["!=", asked.name]}):
				frappe.throw(_("{0} is taken.").format(slug), frappe.DuplicateEntryError)
		asked.workspace_name, asked.slug = first["name"], slug


def _plan(asked, plan: str | None, paid: bool) -> None:
	if paid:
		frappe.throw(_("The plan was chosen before payment."))
	if not plan or not frappe.db.get_value("Offering", {"name": plan, "kind": "Plan", "enabled": 1}):
		frappe.throw(_("That isn't on offer."))
	asked.offering = plan


def _region(asked, region: str | None, paid: bool) -> None:
	if paid:
		frappe.throw(_("Where data is kept was chosen before payment."))
	if region not in [one["value"] for one in wizard_offer.regions()]:
		frappe.throw(_("That isn't on offer."))
	asked.jurisdiction = region


def _seats(asked, kept: dict) -> None:
	most = wizard_offer.seats(asked.offering)
	if most and len(kept.get("people") or []) > most - 1:
		frappe.throw(_("The plan has room for {0} people, you among them.").format(most))


def _events(said) -> list[tuple[str, str]]:
	rows = frappe.parse_json(said) if isinstance(said, str) else said
	return [(one.get("step"), one.get("event")) for one in (rows or [])[:50] if isinstance(one, dict)]


def _note(asked, step: str, event: str) -> bool:
	rows = [{"step": one.step, "event": one.event} for one in asked.get("steps") or []]
	if len(rows) >= MOST_EVENTS:
		return False
	try:
		if not wizard_answers.noted(rows, step, event):
			return False
	except wizard_answers.Refused as refused:
		frappe.throw(str(refused))
	asked.append("steps", {"step": step, "event": event, "at": now_datetime()})
	return True


def _kind(step: str) -> str:
	try:
		return wizard_answers.kind(step)
	except wizard_answers.Refused as refused:
		frappe.throw(str(refused))


def _label(step: str) -> str:
	return _(wizard_answers.LABELS[_kind(step)])
