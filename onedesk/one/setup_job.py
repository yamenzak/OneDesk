"""A workspace set up from its answers (one/setup_answers.py) in one job:
System Settings, frappe's own setup wizard, the owner, the other companies,
the apps on and off, each app's steps, and the people invited. A new
workspace's build runs it (one_admin/steps.py, set_up) and so does the demo
(one_demo/setup.py); each step is safe twice, and a run after a failure
goes on from the step that failed (one/AGENTS.md, The setup job)."""

import json

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import getdate, nowdate

from onedesk.one import setup_answers

ORDER = ("settings", "wizard", "owner", "companies", "apps", "steps", "people")

KEY = "one_setup_job"

JOB = "one_setup_job"


def walk(answers: dict, steps: dict, held: dict, keep) -> dict:
	"""Each step of ORDER not yet done, in order, each written down done as
	it finishes; a step that fails is written down with its reason and
	raised, and the next walk starts there. `keep` writes what is held.
	Pure but for what `steps` and `keep` do."""
	held = {"done": [one for one in held.get("done") or [] if one in ORDER], "failed": None}
	for name in ORDER:
		if name in held["done"]:
			continue
		try:
			steps[name](answers)
		except Exception as raised:
			held["failed"] = f"{name}: {raised}"[:500]
			keep(held, failed=True)
			raise
		held["done"].append(name)
		keep(held, failed=False)
	return held


def held() -> dict:
	try:
		return json.loads(frappe.db.get_default(KEY) or "{}")
	except ValueError:
		return {}


def _keep(said: dict, failed: bool) -> None:
	if failed:
		frappe.db.rollback()
	frappe.db.set_default(KEY, json.dumps(said))
	frappe.db.commit()


def run(answers: dict) -> dict:
	"""Set the workspace up from its answers, as Administrator, and say
	which steps are done. Refuses answers it can't set up from before doing
	anything, saying why where wake reads it."""
	try:
		setup_answers.check(answers)
		_check_here(answers)
	except setup_answers.Invalid as refused:
		_keep({**held(), "failed": f"answers: {refused}"[:500]}, failed=True)
		raise
	frappe.set_user("Administrator")
	return walk(answers, STEPS, held(), _keep)


def _check_here(answers: dict) -> None:
	"""What only the site knows: the language, each country, the owner's
	and each person's address, and each app's steps by their keys."""
	wrong = []
	if not frappe.db.exists("Language", answers["language"]):
		wrong.append(f"language {answers['language']!r} is not one this site has")
	wrong += [f"country {one['country']!r} is not one this site has" for one in answers["companies"] if not frappe.db.exists("Country", one["country"])]
	for email in [answers["owner"]["email"], *(one["email"] for one in answers.get("people") or [])]:
		if not frappe.utils.validate_email_address(email):
			wrong.append(f"{email!r} is not an email address")
	declared = _declared()
	for id, given in (answers.get("steps") or {}).items():
		for key, values in given.items():
			step = declared.get((id, key))
			if not step or not step.get("fields"):
				wrong.append(f"steps.{id}.{key} is not a step with fields")
				continue
			names = {field["fieldname"] for field in step["fields"]}
			wrong += [f"steps.{id}.{key} has an unknown field {name!r}" for name in values if name not in names]
	if wrong:
		raise setup_answers.Invalid("; ".join(wrong))


def _declared() -> dict:
	from onedesk.one import ready, setup_steps

	return {(ready.MODULES[module]["folder"], step["key"]): {**step, "module": module} for module, step in setup_steps.declared()}


def _country(name: str) -> dict:
	from frappe.geo.country_info import get_country_info

	return get_country_info(name) or {}


def _currency(company: dict) -> str:
	return company.get("currency") or _country(company["country"]).get("currency")


def settings(answers: dict) -> None:
	"""The language, the time zone, the country and its currency, and how
	the country writes a date, a time and a number, first: frappe's wizard
	takes these back from System Settings when its own part was done on an
	earlier try. Set one by one, since before the wizard System Settings
	can't be saved whole."""
	first = answers["companies"][0]
	country = frappe.db.get_value("Country", first["country"], ["date_format", "time_format"], as_dict=True) or {}
	for field, value in {
		"language": answers["language"],
		"time_zone": answers["time_zone"],
		"country": first["country"],
		"currency": _currency(first),
		"date_format": country.get("date_format"),
		"time_format": country.get("time_format"),
		"number_format": setup_answers.number_format(_country(first["country"]).get("number_format")),
	}.items():
		if value:
			frappe.db.set_single_value("System Settings", field, value)
	if answers.get("field"):
		frappe.db.set_default("one_field", answers["field"])
	frappe.clear_cache()


def wizard(answers: dict) -> None:
	"""frappe's own setup_complete, which runs erpnext's, hrms's and One's
	stages as the wizard does: the first company and its chart, the
	financial year, the defaults, the working day. Once."""
	from onedesk.one import roles

	roles.ensure()
	if frappe.is_setup_complete():
		return
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	language = frappe.db.get_value("Language", answers["language"], "language_name") or "English"
	first = answers["companies"][0]
	said = setup_complete(setup_answers.wizard(answers, _currency(first), language, getdate(nowdate())))
	if (said or {}).get("status") != "ok":
		raise RuntimeError(f"frappe's setup wizard did not finish: {said}")


def owner(answers: dict) -> None:
	"""The owner, named, an administrator of the workspace, and invited
	unless a password is given or `invite` is false."""
	from onedesk.account_center import owner as owners

	said = answers["owner"]
	email = said["email"].strip().lower()
	invite = said.get("invite", True) and not said.get("password")
	owners.make(email, said["first_name"], said.get("last_name"), inviting=invite)
	if said.get("password"):
		from frappe.utils.password import update_password

		update_password(email, said["password"])
	if answers.get("theme"):
		frappe.db.set_value("User", email, "desk_theme", answers["theme"])


def companies(answers: dict) -> None:
	"""Every company after the first, made as the wizard makes the first,
	then each joined to the group its answer names as its parent."""
	from onedesk.one.companies import join

	day = answers.get("working_day") or {}
	for one in answers["companies"][1:]:
		company(one, day.get("days_off"))
	for name, parent in setup_answers.joined(answers["companies"]):
		join(name, parent)


def company(said: dict, days_off: list | None = None) -> str:
	"""A company with its name, country, currency and chart (erpnext builds
	the chart and hrms its payroll accounts on insert), then what it needs
	to pay payroll and send invoices (one/companies.py, ready): its
	financial year, holiday list, leave and payroll periods, salary
	accounts and letter head. AccountCenter's Companies makes one through
	this too. Once: a company that exists is left as it is."""
	if frappe.db.exists("Company", said["name"]):
		return said["name"]
	taken = set(frappe.get_all("Company", pluck="abbr"))
	doc = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": said["name"],
			"abbr": said.get("abbr") or setup_answers.abbreviation(said["name"], taken),
			"country": said["country"],
			"default_currency": _currency(said),
			"create_chart_of_accounts_based_on": "Standard Template",
			"enable_perpetual_inventory": 1,
		}
	)
	if said.get("chart") and said["chart"] != setup_answers.CHARTS[0]:
		doc.chart_of_accounts = said["chart"]
	doc.insert(ignore_permissions=True)
	frappe.db.set_value("Currency", doc.default_currency, "enabled", 1)
	from onedesk.one.companies import ready

	ready(doc.name, said, days_off)
	return doc.name


def apps(answers: dict) -> None:
	"""The apps turned on and off, through the Apps screen's own switch."""
	from onedesk.one import apps as switch

	off = setup_answers.switched(answers, switch.hidden())
	if off is not None:
		switch.switch(off)


def steps(answers: dict) -> None:
	"""Each app's steps answered, through the step's own save
	(one/setup_steps.py); one done already is left, and one that fails is
	logged and waits in its app's Getting Started."""
	from onedesk.one import setup_steps

	declared = _declared()
	for id, given in (answers.get("steps") or {}).items():
		for key, values in given.items():
			step = declared[(id, key)]
			if not setup_steps.done(step["module"], step):
				setup_steps.save(step["module"], step, values)


def people(answers: dict) -> None:
	"""Everybody else invited by the owner, each with their levels, and an
	administrator where the answers say. Somebody already there has their
	levels set again; somebody refused, as when the plan's seats are used,
	is logged and left for People."""
	from onedesk.account_center.center import invite
	from onedesk.one.people import set_access

	inviter = answers["owner"]["email"].strip().lower()
	for one in answers.get("people") or []:
		email = one["email"].strip().lower()
		access = setup_answers.levels(one.get("levels"))
		frappe.db.savepoint("one_setup_person")
		try:
			if not frappe.db.exists("User", email):
				frappe.set_user(inviter)
				try:
					invite(email, one["first_name"], one.get("last_name"), access)
				finally:
					frappe.set_user("Administrator")
			set_access(frappe.get_doc("User", email), access, int(bool(one.get("admin"))), told=False)
		except frappe.ValidationError:
			frappe.db.rollback(save_point="one_setup_person")
			frappe.log_error(f"setup: inviting {email}")


STEPS = {
	"settings": settings,
	"wizard": wizard,
	"owner": owner,
	"companies": companies,
	"apps": apps,
	"steps": steps,
	"people": people,
}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60)
def wake(start: int = 0) -> dict:
	"""Where this workspace's setup is: done, running, or failed and why.
	OneAdmin's build calls it (steps.set_up); `start` begins the job, or
	begins it again after a failure. It takes no answers and trusts nobody:
	the job asks OneAdmin for them with this site's own token, and once the
	setup is done it never runs again."""
	from frappe.utils.background_jobs import get_job_status

	from onedesk.one import account

	if not account.configured():
		return {"setup": "waiting"}
	said = held()
	if set(ORDER) <= set(said.get("done") or []):
		return {"setup": "done"}
	if get_job_status(JOB) in ("queued", "started"):
		return {"setup": "running"}
	if said.get("failed") and not int(start or 0):
		return {"setup": "failed", "why": said["failed"]}
	frappe.enqueue("onedesk.one.setup_job.from_admin", queue="long", timeout=1800, job_id=JOB, deduplicate=True)
	return {"setup": "running"}


def from_admin() -> None:
	"""The job a build starts: who this workspace is asked first (so its
	name and seats are known to the invitations), then its answers, and the
	setup run from them."""
	from onedesk.one import account

	frappe.set_user("Administrator")
	account.refresh()
	frappe.db.commit()
	run(account.ask("onedesk.one_admin.proxy.setup_answers") or {})
