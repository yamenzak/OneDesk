"""SetupCenter's setup guide, the agent somebody setting One up asks: in
the signup wizard on OneAdmin before a workspace exists
(one_admin/wizard_ask.py), and in SetupCenter afterwards, through OneChat.
It holds no role, suggests rather than saves, and never pays or makes a
workspace. one_ai/AGENTS.md, The setup guide."""

from typing import Annotated, Literal

import frappe
from frappe import _lt

from onedesk.one import registry

TOOLS = (
	"about_fields",
	"about_apps",
	"about_plans",
	"about_regions",
	"about_questions",
	"about_steps",
	"suggest_answer",
	"fill_step",
)

LEVELS = {
	"about_fields": "Do it",
	"about_apps": "Do it",
	"about_plans": "Do it",
	"about_regions": "Do it",
	"about_questions": "Do it",
	"about_steps": "Do it",
	"suggest_answer": "Do it",
	"fill_step": "Ask First",
}

LABELS = {
	"about_fields": _lt("Read the Fields"),
	"about_apps": _lt("Read the Apps"),
	"about_plans": _lt("Read the Plans"),
	"about_regions": _lt("Read Where Data Is Kept"),
	"about_questions": _lt("Read the Setup Questions"),
	"about_steps": _lt("Read Each App's Steps"),
	"suggest_answer": _lt("Suggest an Answer"),
	"fill_step": _lt("Fill In a Step"),
}

MOST_HELP = 1800

SUGGESTS = ("field", "apps", "plan", "region")
"""The wizard's questions the guide may suggest an answer to: those whose
answers are choices the wizard offers."""

QUESTIONS = {
	"you": "The owner's first and last name. The owner becomes the workspace's first administrator. The email address is the one they sign up with; no password is asked here.",
	"company": "The first company's name and country. The workspace takes its name, and its web address starts with it; a name another signup holds is taken.",
	"language": "The workspace's language, the time zone and each company's currency. The country picks the currency, time zone, number and date formats, holidays and taxes.",
	"field": "What the company does. Each field turns on the apps that suit it and fills some later answers, such as the working day; the next question changes the apps.",
	"companies": f"Each other company the workspace keeps books for, with its own name, country and currency, up to 10. It can be skipped and added later in {registry.name('account_center')}.",
	"apps": "Which apps are on. An app another app needs is turned on with it; an app that holds records the law or other apps need cannot be turned off once it holds them. Any app can be turned on later.",
	"plan": "The plan: its price a month, its trial, its storage, database, people and credits, and what it includes.",
	"region": "Where the workspace's data is kept. The European Union keeps the workspace's files in the EU. It cannot be changed later.",
	"payment": "Payment by card through Stripe's own page. A plan with a trial takes the card now and charges it when the trial ends. The workspace is built once payment is accepted.",
	"week": "The working week: the days off and the working day's start and end, used for attendance, leave and the calendar. It can be skipped.",
	"steps": f"Each app's own questions, such as {registry.name('one_mail')}'s company domain. Any can be skipped and waits in {registry.name('setup_center')}.",
	"people": "The people to invite, each by email address and name. They are invited by email once the workspace is ready, and the plan limits how many.",
}
"""What each of the wizard's questions decides, as the wizard (frontend/
portal/src/pages/Start.vue, one_admin/wizard.py) does it: what the guide
reads to say what a question means."""


def who(guest: bool) -> str:
	"""Who is answering, as the model is told it first."""
	shared = (
		"Answer only about setting up One, from your tools: never a feature, an app, a price, a plan, a date "
		"or a law your tools did not return. When the tools do not say, say you do not know. Keep to two or "
		"three short sentences in the person's language."
	)
	if guest:
		return (
			"You are One's setup guide. You help somebody signing up for One while they answer the setup "
			"questions, before their workspace exists: what a question means, what a field turns on, what a "
			"plan includes, which apps a business like theirs needs and where data is kept. When they ask what "
			"to choose, call suggest_answer: it is shown to them to take or leave, and you never choose, pay "
			f"or make the workspace for them. {shared}"
		)
	return (
		f"You are {registry.name('setup_center')}'s setup guide. You help this workspace's administrators set "
		"up each app: what a step does and why, and where it is done. When they ask you to fill a step in, "
		f"call fill_step: it becomes a card they approve, and nothing is saved before. {shared}"
	)


def reaches(user: str | None = None) -> bool:
	"""Who may talk to the guide in a workspace: whoever may do a step in
	SetupCenter."""
	from onedesk.one import setup_center

	return setup_center.reaches(user)


def tools(guest: bool) -> tuple[tuple, tuple]:
	"""The guide's tools, as (reads, suggestions): One's Help and the
	wizard's offer for a guest, and in a workspace the steps it may fill."""
	from onedesk.one_ai import guide

	reads = (about_fields, about_apps, about_regions, about_questions, about_steps, guide.how_to)
	if guest:
		return (*reads, about_plans), (suggest_answer,)
	return reads, (fill_step,)


def about_fields() -> list[dict]:
	"""Each field the wizard offers for what a company does: the apps it
	turns on, and which later answers it fills in (such as the working day)."""
	from onedesk.one.registry import fields

	return [
		{
			"id": one.id,
			"label": str(frappe._(one.label)),
			"line": str(frappe._(one.line)),
			"apps": [registry.name(app) for app in fields.preset(one.id)],
			"fills": sorted(key for key in fields.suggested(one.id) if key != "steps")
			+ [f"{registry.name(app)} {step}" for app, given in (fields.suggested(one.id).get("steps") or {}).items() for step in given],
		}
		for one in fields.FIELDS
	]


def about_apps(
	app: Annotated[str, "One app's name, such as OneBook, to read its Help as well; leave it out for every app."] | None = None,
) -> dict:
	"""Every app One offers: what it does, what it brings, which apps it
	needs, whether it is always on or kept once it holds records, and in
	which countries it is built or works. Name one app to read its Help."""
	from onedesk.one_admin import wizard_offer

	apps = []
	for one in wizard_offer.apps():
		declared = registry.get(one["id"])
		apps.append(
			{
				"name": one["name"],
				"line": one["line"],
				"pitch": registry.filled(str(frappe._(declared.pitch))) if declared.pitch else "",
				"brings": [str(frappe._(line)) for line in declared.brings],
				"needs": [registry.name(id) for id in one["needs"]],
				"always_on": one["always"],
				"kept": one["kept"],
				"countries": dict(declared.countries),
			}
		)
	if not app:
		return {"apps": apps}
	try:
		chosen = registry.by_name(app)
	except KeyError:
		return {"apps": apps, "next": f"There is no app called {app}. Name one from this list."}
	return {"apps": [one for one in apps if one["name"] == chosen.name], "help": _help(chosen.id)}


def _help(id: str) -> str:
	from onedesk.one_ai import guide

	page = guide.APP / id / "help" / "overview.md"
	return guide.plain(registry.filled(page.read_text(encoding="utf-8")))[:MOST_HELP] if page.is_file() else ""


def about_plans() -> list[dict]:
	"""The plans on offer, cheapest first: price a month, trial, storage,
	database, people, credits a month and what each includes."""
	from onedesk.one_admin import wizard_offer

	return [
		{key: one.get(key) for key in ("name", "label", "description", "price", "trial", "quota", "includes")}
		for one in wizard_offer.plans()
	]


def about_regions(
	country: Annotated[str, "A country's name in English, to read its currency, time zones and how far each app is built there."] | None = None,
) -> dict:
	"""Where a workspace's data may be kept, and for a country its currency,
	its time zones and which apps are built for it, work there or are not
	checked there."""
	from onedesk.one_admin import wizard_offer

	said = {"regions": [one["label"] for one in wizard_offer.regions()], "region": QUESTIONS["region"]}
	if not country:
		return said
	found = next((one for one in wizard_offer.countries() if one["value"].casefold() == country.casefold()), None)
	if not found:
		return {**said, "next": f"There is no country called {country}."}
	states = {one.name: one.countries.get(found["value"], "not checked") for one in registry.apps() if one.kind == "app"}
	return {**said, "country": found["value"], "currency": found["currency"], "time_zones": found["zones"][:5], "apps": states}


def about_questions(
	question: Annotated[str, "One question's key, such as field or region; leave it out for every question."] | None = None,
) -> dict:
	"""What each of the signup's setup questions asks and decides, in the
	order they come: before payment, then while the workspace is built."""
	from onedesk.one_admin import wizard_answers

	keys = [question] if question in QUESTIONS else list(wizard_answers.STEPS)
	return {"questions": [{"key": key, "title": str(frappe._(wizard_answers.LABELS[key])), "decides": QUESTIONS[key]} for key in keys]}


def about_steps() -> list[dict]:
	"""Each app's own setup steps: what each is for, the answers it asks
	and, in a workspace, whether it is done and whether you may fill it."""
	from onedesk.one import setup_steps
	from onedesk.one_admin import site

	guest = site.is_admin()
	out = []
	for module, step in setup_steps.declared():
		if not guest and not setup_steps.may(module, step):
			continue
		out.append(
			{
				"app": module,
				"key": step["key"],
				"title": str(frappe._(step["title"])),
				"about": str(frappe._(step["about"])),
				"fields": [
					{"fieldname": one["fieldname"], "label": str(frappe._(one.get("label") or "")), "fieldtype": one.get("fieldtype") or "Data", "description": str(frappe._(one.get("description") or ""))}
					for one in step.get("fields") or []
				],
				**({} if guest else {"done": setup_steps.done(module, step), "may_fill": bool(step.get("fields") and step.get("save"))}),
			}
		)
	return out


def suggest_answer(
	question: Annotated[Literal["field", "apps", "plan", "region"], "The question the suggestion answers."],
	why: Annotated[str, "One sentence the person reads under it: why this suits them."],
	field: Annotated[str, "For field: a field's id from about_fields."] | None = None,
	apps: Annotated[list[str], "For apps: the names of the apps to have on, such as OneBook."] | None = None,
	plan: Annotated[str, "For plan: a plan's name from about_plans."] | None = None,
	region: Annotated[str, "For region: one of the regions about_regions lists."] | None = None,
) -> dict:
	"""Suggest an answer to one setup question, shown to the person with a
	button to use it. Nothing is chosen until they press it. Suggest only
	what your tools offered."""
	from onedesk.one_admin import wizard_offer

	offered = wizard_offer.offer()
	if question == "field":
		chosen = next((one for one in offered["fields"] if one["id"] == field), None)
		if not chosen:
			return {"error": f"There is no field {field!r}. Use an id from about_fields."}
		answers, shown = {"field": chosen["id"]}, chosen["label"]
	elif question == "apps":
		switchable = {one["name"]: one["id"] for one in offered["apps"] if not one["always"]}
		unknown = [one for one in apps or [] if one not in switchable]
		if unknown or not apps:
			return {"error": f"Name apps One offers, from about_apps; {unknown or 'none'} is not one."}
		answers, shown = {"apps": {id: name in apps for name, id in switchable.items()}}, ", ".join(apps)
	elif question == "plan":
		chosen = next((one for one in offered["plans"] if plan in (one["name"], one["label"])), None)
		if not chosen:
			return {"error": f"There is no plan {plan!r} on offer. Use one from about_plans."}
		answers, shown = {"plan": chosen["name"]}, chosen["label"]
	else:
		chosen = next((one for one in offered["regions"] if region in (one["value"], one["label"])), None)
		if not chosen:
			return {"error": f"Data cannot be kept in {region!r}. Use one about_regions lists."}
		answers, shown = {"region": chosen["value"]}, chosen["label"]
	return {
		"suggestion": {"question": question, "shown": shown, "why": (why or "")[:300], "answers": answers},
		"next": "It is shown under your answer with Use This. Say in one sentence why it suits them; do not say it was chosen.",
	}


def fill_step(
	app: Annotated[str, "The app the step belongs to, by its name from about_steps."],
	key: Annotated[str, "The step's key from about_steps."],
	values: Annotated[dict, "The step's answers, by the fieldnames about_steps lists."],
	why: Annotated[str, "One sentence on why these answers."] | None = None,
) -> dict:
	"""Fill in one app's setup step with its answers, as a card the person
	who asked approves; nothing is saved before. Say that it waits for them."""
	from onedesk.one import setup_steps
	from onedesk.one_ai.agents import door
	from onedesk.one_ai.reading import act

	given = {"_app": app, "_step": key, **{name: value for name, value in (values or {}).items() if name not in setup_steps.WHICH}}
	found = setup_steps.step_of(given)
	if not found:
		return {"error": "That step has no answers to fill. Use one about_steps lists with may_fill."}
	fields = {one["fieldname"] for one in found[1]["fields"]}
	given = {name: value for name, value in given.items() if name in fields or name in setup_steps.WHICH}
	made = door.act_for("setup_center", "fill_step", act.Action("Step", "", values=given, why=why or ""), asked_by=frappe.session.user)
	row = frappe.db.get_value("Reading Action", made, ["level", "why"], as_dict=True) if made else None
	if not row:
		return {"state": "Not done", "why": "The same answers already wait."}
	return {"state": {"Proposed": "Waiting for the person to approve its card", "Refused": "Refused"}.get(row.level, row.level), **({"why": row.why} if row.why else {})}
