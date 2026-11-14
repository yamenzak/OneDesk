"""Apps a workspace has turned off, OneAI and its reading among them.

An app turned off leaves the rail, search and the pickers for everybody, and
nothing is deleted or refused. Turning one off is refused while it is kept
(its manifest's `kept`) or an app left on needs it; turning one on turns on
what it needs (`needs`), and says so. OneAI off refuses every model call and turns
reading off with it; OnePortal off closes the portal (one_portal/gate.py). The rest is in One's Help, under Settings (one/help/settings.md).
"""

import json

import frappe
from frappe import _, _lt

from onedesk.one import registry

KEY = "one_hidden_apps"
HOST = "onedesk"
KEPT = tuple(app.sidebar for app in registry.apps() if app.kept and app.kept.always() and app.sidebar)
"""The rail rows never offered as a switch: apps kept whatever they hold."""
AI = registry.name("one_ai")
INTAKE = "Reading"
NEEDS = {INTAKE: AI}
# OneAI is a rail of its own, turned off as any app is; reading is a switch
# with no rail, whose rows leave every rail when it is off.
SECTIONS = (INTAKE,)
ICONS = {INTAKE: "oneintake"}
# One's rail rows for OneAI's centre, which go when OneAI is off.
MEMORY = {"url": "/desk/one?center=ai&at=yours"}
AI_CENTER = {"url": "/desk/one?center=ai"}
# AccessCenter's row, which only an administrator can open.
ACCESS_CENTER = {"url": "/desk/one?center=access"}
SETUP_CENTER = {"url": "/desk/one?center=setup"}
# What reading shows in the rails, which goes when reading is off.
READS = (
	{"link_to": "Ready to Submit"},
	{"link_to": "Deadlines"},
	{"link_to": "Spending"},
	{"url": "/desk/one?center=ai&at=reads"},
)
# What the Apps screen calls the switches that are not apps.
LABELS = {INTAKE: _lt("Reading")}


def hidden() -> list[str]:
	"""The rail rows (Sidebar names) the workspace has turned off, and those
	of the apps its plan doesn't include."""
	try:
		said = json.loads(frappe.db.get_default(KEY) or "[]")
	except ValueError:
		said = []
	off = [one for one in said if isinstance(one, str)]
	off += [one for one, needs in NEEDS.items() if needs in off and one not in off]
	return off + [one for one in unplanned() if one not in off]


def unplanned() -> list[str]:
	"""The rail rows of One's apps and the private apps whose manifest needs
	a plan feature (`plan=`) this workspace's plan lacks: not on the rail,
	not offered as a switch, never refused with an error."""
	from onedesk.account_center import plan, private

	held = plan.held()
	return [] if held is None else short(registry.apps(), held) + private.unplanned(held)


def short(apps, held) -> list[str]:
	"""The sidebars of those apps whose plan features `held` lacks. Pure."""
	from onedesk.one.registry import features

	return [one.sidebar for one in apps if one.sidebar and features.missing(one.plan, held)]


def ai_on() -> bool:
	"""Whether OneAI may be asked anything in this workspace."""
	return AI not in hidden()


def intake_on() -> bool:
	"""Whether OneAI reads: it needs OneAI too."""
	return INTAKE not in hidden()


def refuse_ai() -> None:
	"""Every model call goes through run.py (turn, once, read, make and
	begin), which ask this first. A Refused is what their callers already
	handle."""
	if not ai_on():
		from onedesk.one_admin import faults

		raise faults.Refused(_("{0} is turned off for this workspace.").format(registry.name("one_ai")))


def offered() -> list[dict]:
	"""One's own rail rows a workspace may turn off, OneAI among them, in rail
	order, each with the rows it needs and why it is kept now, if it is
	(`held`); then the private apps it has (always on), then OneAI's
	reading."""
	from frappe.desk.doctype.dock.dock import get_app_dock

	from onedesk.account_center import private
	from onedesk.one.people import APP_SAID

	off = set(hidden())
	theirs = private.rail()
	planless = set(unplanned())
	apps = {one.sidebar: one for one in registry.apps() if one.sidebar}
	rows = _rows()
	rail = [
		{
			"name": row.get("link_to"),
			"title": _(row.get("title") or row.get("link_to")),
			"said": str(APP_SAID.get(row.get("link_to"), "")),
			"icon": row.get("icon"),
			"on": row.get("link_to") not in off,
			"needs": _needed_rows(apps.get(row.get("link_to")), rows),
			"held": _held(apps.get(row.get("link_to"))) if row.get("link_to") not in off else None,
		}
		for row in get_app_dock(HOST)
		if row.get("link_type") == "Sidebar"
		and row.get("link_to") not in KEPT
		and row.get("link_to") not in theirs
		and row.get("link_to") not in planless
	]
	needing = private.needs()
	return rail + [{**one, "needs": [rows[id] for id in needing.get(one["name"], ()) if id in rows]} for one in private.offered()] + [
		{
			"name": name,
			"title": str(LABELS.get(name, name)),
			"said": str(APP_SAID.get(name, "")),
			"icon": ICONS[name],
			"on": name not in off,
			"needs": [NEEDS[name]] if name in NEEDS else [],
			"section": True,
		}
		for name in SECTIONS
	]


def _rows() -> dict[str, str]:
	"""Each of One's apps' rail row (its Sidebar), by its id."""
	return {one.id: one.sidebar for one in registry.apps() if one.sidebar}


def _needed_rows(app, rows: dict) -> list[str]:
	return [rows[id] for id in (app.needs if app else ()) if id in rows]


def _submitted(doctype: str) -> bool:
	"""Whether a record of this type is submitted: what a Kept's `when` asks."""
	return bool(frappe.db.exists("DocType", doctype) and frappe.db.exists(doctype, {"docstatus": 1}))


def _held(app) -> str | None:
	"""Why this app can't be turned off now, in the reader's words, or None."""
	from onedesk.one.registry import switches

	why = switches.held(app, _submitted) if app else None
	return _(why) if why else None


def _named(id: str) -> str:
	from onedesk.account_center import private

	return registry.names().get(id) or private.about(id)["title"]


def settled(off: set, before: set) -> tuple[set, list[str]]:
	"""`off` once what an app left on needs is turned back on, and a line
	saying each; refused, naming the app and why, when it turns off one that
	is kept now or that an app left on needs."""
	from frappe.utils import comma_and

	from onedesk.account_center import private
	from onedesk.one.registry import switches

	rows = _rows()
	ids = {row: id for id, row in rows.items()}
	planless = set(unplanned())
	theirs = private.needs()
	on = {id for id, row in rows.items() if row not in off and row not in planless} | set(theirs)
	turning = {ids[row] for row in off - before if row in ids}
	held_now = {id: switches.held(registry.get(id), _submitted) for id in turning}
	refused = []
	for id, (why, said) in switches.refused(turning, on, held_now, theirs).items():
		if why == "kept":
			refused.append(_("{0} can't be turned off. {1}").format(_named(id), _(said)))
		else:
			refused.append(_("{0} is needed by {1}, so it can't be turned off.").format(_named(id), comma_and([_named(one) for one in said], False)))
	if refused:
		frappe.throw("<br>".join(refused), title=_("Apps Not Saved"))
	brought = {id: by for id, by in switches.with_needs(on, theirs).items() if id not in on and id in rows and rows[id] not in planless}
	lines = [_("{0} was also turned on for {1}.").format(_named(id), comma_and([_named(one) for one in by], False)) for id, by in brought.items()]
	return off - {rows[id] for id in brought}, lines


def unlisted(lists: dict[str, set], off: set) -> set:
	"""The record types only apps that are off list: what leaves search and
	the pickers. A type a visible app lists too stays. Pure."""
	gone = set().union(*(names for app, names in lists.items() if app in off)) if off else set()
	kept = set().union(*(names for app, names in lists.items() if app not in off)) if lists else set()
	return gone - kept


def _lists() -> dict[str, set]:
	"""What each of One's rail rows lists, by record type."""
	from frappe.desk.doctype.dock.dock import get_app_dock

	rail = [row.get("link_to") for row in get_app_dock(HOST) if row.get("link_type") == "Sidebar"]
	found: dict[str, set] = {name: set() for name in rail}
	for row in frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Sidebar", "parent": ["in", rail], "link_type": "DocType"},
		fields=["parent", "link_to"],
		limit=0,
	):
		found[row.parent].add(row.link_to)
	return found


def _where(item: dict) -> tuple:
	said = item.get("route_options") or None
	if isinstance(said, str):
		try:
			said = json.loads(said)
		except ValueError:
			pass
	return item.get("link_to") or item.get("url"), json.dumps(said, sort_keys=True)


def gone(off: set) -> set:
	"""The rows that leave every rail: what reading shows (Documents, its
	reports, What OneAI Reads) when reading is off, and What OneAI
	Remembers when OneAI is. OneAI's own rail goes as any app's does. Pure."""
	rows = [*(READS if INTAKE in off else ()), *((MEMORY, AI_CENTER) if AI in off else ())]
	return {_where(one) for one in rows}


def trim(sidebars: dict) -> None:
	"""`outside.kept`: what reading shows, and OneAI's centre, leave every
	rail when they are off; AccessCenter's row is only an administrator's,
	and SetupCenter's only for whoever may do an app's step."""
	from onedesk.one import roles, setup_center

	leaving = gone(set(hidden())) | (set() if roles.administers() else {_where(ACCESS_CENTER)})
	if not roles.administers() and not setup_center.reaches():
		leaving.add(_where(SETUP_CENTER))
	if not leaving or not isinstance(sidebars, dict):
		return
	for sidebar in sidebars.values():
		if isinstance(sidebar, dict):
			sidebar["items"] = [item for item in sidebar.get("items") or [] if _where(item) not in leaving]


def doctypes() -> list[str]:
	off = set(hidden())
	return sorted(unlisted(_lists(), off)) if off else []


def rehome(said: dict) -> None:
	"""A record type only apps turned off list opens on One's Home, rather
	than in whichever app frappe's ladder falls to (`outside.kept`)."""
	shells = (said.get("canonical_shell") or {}).get("DocType")
	if not isinstance(shells, dict) or "One" not in (said.get("module_sidebars") or {}):
		return
	for name in doctypes():
		shells[name] = "One"


def boot(bootinfo) -> None:
	"""What the desk hides: the apps (the rail does it through the site's
	Dock layer) and their record types (search and the pickers), and whether
	OneAI and its reading are on."""
	bootinfo["one_hidden"] = {"apps": hidden(), "doctypes": doctypes(), "ai": ai_on(), "intake": intake_on()}


@frappe.whitelist()
def read() -> dict:
	from onedesk.account_center import private
	from onedesk.one import roles

	roles.require()
	return {"apps": offered() + private.waiting()}


@frappe.whitelist(methods=["POST"])
def save(off: str | list) -> dict:
	"""Turn these apps off and every other back on, for the whole workspace."""
	from onedesk.one import roles

	roles.require()
	return switch(frappe.parse_json(off) if isinstance(off, str) else off)


def switch(off: list | None) -> dict:
	"""The rail rows turned off, every other on, for whoever may: People's
	Apps screen (save), AICenter and the setup job (one/setup_job.py). One
	kept or needed is refused (`settled`); what one turned on needs comes on
	with it, each said in `said`."""
	from onedesk.one import companions

	off = list(off or [])
	off += [one for one, needs in NEEDS.items() if needs in off and one not in off]
	off = [one for one in off if one not in unplanned()]
	allowed = {one["name"] for one in offered() if not one.get("kept")}
	unknown = [one for one in off or [] if one not in allowed]
	if unknown:
		frappe.throw(_("{0} can't be turned off.").format(", ".join(unknown)))
	off, said = settled(set(off), set(hidden()))
	frappe.db.set_default(KEY, json.dumps(sorted(off)))
	companions.layer()
	frappe.clear_cache()
	frappe.publish_realtime("one_apps", after_commit=True)
	return {"apps": offered(), "said": said}


@frappe.whitelist()
def search_link(
	doctype: str,
	txt: str,
	query: str | None = None,
	filters: str | dict | list | None = None,
	page_length: int = 10,
	searchfield: str | None = None,
	reference_doctype: str | None = None,
	ignore_user_permissions: bool = False,
	*,
	link_fieldname: str | None = None,
):
	"""frappe's search_link, as every Link field's picker calls it, without
	the record types of apps turned off when it's picking a DocType: the type
	of a Dynamic Link, and every other Link to DocType."""
	from frappe.desk.search import search_link as frappes

	gone = doctypes() if doctype == "DocType" and not query else []
	if gone:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		if isinstance(filters, dict):
			filters = {**filters, "name": ["not in", gone]} if "name" not in filters else filters
		else:
			filters = [*(filters or []), ["DocType", "name", "not in", gone]]
	return frappes(
		doctype,
		txt,
		query,
		filters=filters,
		page_length=page_length,
		searchfield=searchfield,
		reference_doctype=reference_doctype,
		ignore_user_permissions=ignore_user_permissions,
		link_fieldname=link_fieldname,
	)
