"""OneMarketplace: every app a workspace may have, each with its page read
from its manifest (what it is for a buyer, its pictures and clips, what it
brings, the plan it needs, the credits it uses, what it needs and whether
it is kept), and Install or Turn Off for its administrators through
`apps.switch`. Installing an app with setup steps lands in SetupCenter on
them. The private apps the workspace has are shown apart, under its
company's name. It replaces Turn Apps On or Off (one/AGENTS.md, Under the
hood)."""

import json
from urllib.parse import quote

import frappe
from frappe import _

from onedesk.one import registry
from onedesk.one.registry import credits, fields, switches

def shown(one) -> bool:
	"""Whether an app has a page: an app people use, on the rail, and not
	OneAdmin's or a private app's, which are shown apart."""
	return one.kind == "app" and bool(one.sidebar) and not one.private and not one.operators


def least_plan(needs, plans) -> str | None:
	"""The label of the first plan in `plans` ((label, features), cheapest
	first) that has every feature in `needs`; None when none does. Pure."""
	return next((label for label, has in plans if all(one in has for one in needs)), None)


def pages(apps, *, off, held, kept_now, steps, plans, say=str, names=None, media=None, private=None) -> list[dict]:
	"""Each app's page, in the rail's order. `off` are the ids turned off,
	`held` the plan's features (None when nothing holds the workspace to
	any), `kept_now` why each app kept now can't be turned off, by id,
	`steps` the ids with setup steps the reader may do, `plans` the plans
	sold as (label, features), cheapest first, `say` what translates a
	word, `names` every app's name by id, `media` what gives an app's
	pictures and clips, and `private` what each private app the workspace
	has needs, by its id: they are always on. Pure but for the registry."""
	names = names or {one.id: one.name for one in apps}
	private = private or {}
	on = [one.id for one in apps if one.id not in off] + list(private)
	presets = {field.id: set(fields.preset(field.id)) for field in fields.FIELDS}
	found = []
	for one in apps:
		missing = [feature for feature in one.plan if held is not None and feature not in held]
		needed_by = [names.get(other, other) for other in switches.needed_by(one.id, on, private)] if one.id in on else []
		why = kept_now.get(one.id) or ""
		always = bool(one.kept and one.kept.always())
		found.append(
			{
				"id": one.id,
				"name": one.name,
				"line": say(one.line) if one.line else "",
				"pitch": registry.filled(say(one.pitch)) if one.pitch else "",
				"brings": [registry.filled(say(line)) for line in one.brings],
				"mark": one.mark or "app-window",
				"media": media(one) if media else [],
				"on": one.id not in off,
				"plan": {"included": not missing, "needs": None if not missing else least_plan(one.plan, plans)},
				"credits": [registry.filled(say(credits.get(kind).said)) for kind in one.credits],
				"needs": [names.get(other, other) for other in one.needs],
				"needed_by": needed_by,
				"kept": say(why) if why else "",
				"always": always,
				"fields": [field for field, apps in presets.items() if one.id in apps],
				"steps": one.id in steps,
				"may_install": one.id in off and not missing,
				"may_turn_off": one.id not in off and not why and not needed_by and not always,
			}
		)
	return found


def _media(one) -> list[dict]:
	"""An app's pictures and clips at their R2 address, each with the one
	this site serves until R2 has it."""
	from onedesk.one import media

	found = []
	for named in one.media:
		path = registry.FOLDERS / one.id / "media" / named
		here = f"/api/method/onedesk.one.media.picture?module={quote(one.name)}&path={quote('media/' + named)}"
		found.append({"src": f"{media.base()}/{media.key(path)}", "here": here, "video": path.suffix.lower() == ".mp4"})
	return found


def _plans() -> tuple[tuple[str, tuple[str, ...]], ...]:
	from onedesk.one_admin import price_list

	return tuple((one.label, one.features) for one in price_list.PLANS if one.sold)


def _off() -> set[str]:
	from onedesk.one import apps

	hidden = set(apps.hidden())
	return {one.id for one in registry.apps() if one.sidebar and one.sidebar in hidden}


def _kept_now() -> dict[str, str]:
	from onedesk.one import apps

	found = {}
	for one in registry.apps():
		why = switches.held(one, apps._submitted)
		if why:
			found[one.id] = why
	return found


def _steps() -> set[str]:
	from onedesk.one import setup_steps

	said = setup_steps.for_boot()
	return {one.id for one in registry.apps() if said.get(one.name)}


def _private() -> dict:
	"""The private apps the workspace has or has claimed, under its
	company's name."""
	from onedesk.account_center import private

	company = frappe.defaults.get_global_default("company") or ""
	apps = []
	for one in [*private.offered(), *private.waiting()]:
		apps.append(
			{
				"id": one["name"],
				"name": one["title"],
				"line": one.get("said") or "",
				"pitch": one.get("pitch") or "",
				"brings": one.get("brings") or [],
				"mark": one.get("icon") or "package",
				"state": one.get("state") or ("Installed" if one.get("on") else ""),
				"needs": [registry.names().get(id, id) for id in one.get("needs") or ()],
			}
		)
	return {"company": company, "apps": apps}


@frappe.whitelist()
def read() -> dict:
	"""Every app's page, the fields to filter them by, and the private apps."""
	from onedesk.account_center import plan, private
	from onedesk.one import roles

	roles.require()
	return {
		"apps": pages(
			[one for one in registry.apps() if shown(one)],
			off=_off(),
			held=plan.held(),
			kept_now=_kept_now(),
			steps=_steps(),
			plans=_plans(),
			say=lambda text: str(_(text)),
			names={**registry.names(), **{id: private.about(id)["title"] for id in private.needs()}},
			media=_media,
			private=private.needs(),
		),
		"fields": [{"id": one.id, "label": str(_(one.label))} for one in fields.FIELDS if one.apps],
		"private": _private(),
	}


@frappe.whitelist(methods=["POST"])
def turn(app: str, on: int | str) -> dict:
	"""Turn one app on, with what it needs, or off, for the whole workspace,
	through `apps.switch`, which refuses one kept or needed and says why.
	What was off only because this app was comes back with it. Answers what
	else was turned on and where to go next: SetupCenter on the app's steps
	when it was turned on and has some."""
	from onedesk.one import apps, roles

	roles.require()
	one = registry.get(app)
	if not shown(one):
		frappe.throw(_("{0} can't be turned on or off.").format(one.name))
	held = json.loads(frappe.db.get_default(apps.KEY) or "[]")
	off = [row for row in held if row != one.sidebar and apps.NEEDS.get(row) != one.sidebar]
	if not frappe.utils.cint(on):
		off.append(one.sidebar)
	said = apps.switch(off)["said"]
	landing = f"/desk/one?center=setup&at={quote(one.name)}" if frappe.utils.cint(on) and app in _steps() else None
	return {"said": [str(line) for line in said], "landing": landing}
