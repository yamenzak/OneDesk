"""Which modules are ready for live, and where each one's files are
(docs/READY.md). Pure, so the guards read it without a site.

A module's files are its folder, its static files under
`public/js/<folder>/`, `public/css/<folder>/` and `public/images/<folder>/`, and its screens under
`frontend/src/<screens>/`.
"""

import hashlib
import re
from pathlib import Path

from onedesk.one import registry, standard

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent

# One is declared ready for production once every module is. Until then the
# agreements change freely (docs/READY.md, Before production).
PRODUCTION = False



def _entry(app) -> dict:
	"""What this file held for a module before the registry: its readiness,
	its files outside its folder and its interface, read from its manifest."""
	entry = {"folder": app.id, "names": app.names}
	if app.screens:
		entry["screens"] = app.screens
	if app.help:
		entry["help"] = app.help
	entry.update(app.ready)
	for key, value in (
		("interface", app.interface),
		("companies", app.companies),
		("windowless", app.windowless),
		("engine", app.no_roles),
		("app", app.frontend),
		("operators", app.operators),
	):
		if value:
			entry[key] = value
	return entry


MODULES = {app.name: _entry(app) for app in registry.apps() if app.kind != "engine" or app.help}
"""Every app and centre, and every engine with Help of its own: an engine
nobody reads about, such as the demo, is not a module."""

POINTS = {point.key: {"number": point.number, "title": point.title} for point in standard.POINTS.values() if point.live}
"""The points of the standard a module is held to before it is marked ready
(docs/STANDARD.md), in its order."""

HAND = {point.key: point.look for point in standard.POINTS.values() if point.look}
"""The points no rule settles, and what a person looks at: before a module
is marked ready, and again after a version that adds to it."""

# Files named for a module, or in its places, that are not its own, and why.
# A path ending in / is a whole folder. A module's files leave them out, so
# its version moves only with what is its own.
_ENGINE = "an engine every module uses, kept in One's folder"
_RAN = "OnePortal's, a patch that has run, kept at the path frappe recorded it under"
_DESK = "the desk's, shared by every module"
SHARED = {
	"brand/onemail.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/oneadmin.svg": "every product's mark is drawn in brand/, into one sprite",
	"frontend/src/islands/oneadmin.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_billing.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_releases.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_server_part.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_servers.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_sessions.js": "the islands build takes its entries from one folder",
	"frontend/src/islands/oneadmin_status.js": "the islands build takes its entries from one folder",
	"brand/oneinventory.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onefactory.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onequality.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onecrm.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onehr.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_crm/business-card.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/business-card.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-ar.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-ar.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-de.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-de.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/order-from-lead.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/order-from-lead.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/cv.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/cv.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/sick-note.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/sick-note.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/signed-contract.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/signed-contract.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt-doubted.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt-doubted.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt.json": "reading's samples sit with every module's, under tests/samples",
	"brand/onebook.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_inventory/coating-bill.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/coating-bill.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/delivery-note.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/delivery-note.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/supplier-quote.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/supplier-quote.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/bank-statement-2026-10-06.xml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/bank-statement.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/new-supplier-invoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/new-supplier-invoice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/payment-advice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/payment-advice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/supplier-einvoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/supplier-einvoice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/transport-contract.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/transport-contract.json": "reading's samples sit with every module's, under tests/samples",
	"brand/oneportal.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onecalendar.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onedisplay.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onedeck.svg": "every product's mark is drawn in brand/, into one sprite",
	"docs/ONEDECK.md": "the plan that made OneDeck and moved OneDisplay's slides into it, across both modules",
	"brand/onedoc.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onesheet.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onecloud.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_calendar/site-meeting.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_calendar/site-meeting.json": "reading's samples sit with every module's, under tests/samples",
	"brand/onetask.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_task/drawings-request.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_task/drawings-request.json": "reading's samples sit with every module's, under tests/samples",
	"brand/oneproject.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_project/extra-work-request.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/extra-work-request.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/scaffolding-bill.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/scaffolding-bill.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/site-log.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/site-log.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/subcontractor-timesheet.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/subcontractor-timesheet.json": "reading's samples sit with every module's, under tests/samples",
	"onedesk/templates/emails/one_mail.html": "the frame every mail One sends is laid in, OneMail's or not",
	"brand/oneai.svg": "every product's mark is drawn in brand/, into one sprite",
	"onedesk/public/images/oneai.svg": "the mark as an image, for the places that can't use the sprite",
	"onedesk/one_mail/docs/asking-oneai.md": "OneMail's own Help page on what OneAI does in mail",
	"onedesk/one_mail/docs/asking-oneai/reading.png": "the picture on OneMail's page on OneAI",
	"tests/samples/intake/one_ai/ignore-instructions.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/ignore-instructions.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/locked-invoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/locked-invoice.json": "reading's samples sit with every module's, under tests/samples",
	# The engines every module uses (docs/ONE.md, What One keeps).
	"onedesk/one/rights.py": _ENGINE + ": what a role may do in each module (docs/ROLES.md)",
	"onedesk/one/roles.py": _ENGINE + ": who administers the workspace",
	"onedesk/one/notify.py": _ENGINE + ": every notification goes through it",
	"onedesk/one/push.py": _ENGINE + ": every notification's push",
	"onedesk/one/doctype/push_device/": _ENGINE + ": the devices a push goes to",
	"onedesk/one/tell.py": _ENGINE + ": what every module tells people about the workspace goes through it",
	"onedesk/one/account.py": _ENGINE + ": every module asks the account through it",
	"onedesk/one/apps.py": _ENGINE + ": which apps the workspace has turned off, which every module asks",
	"onedesk/one/people.py": _ENGINE + ": the apps every person is given, which every module asks",
	"onedesk/one/head.py": _ENGINE + ": the record head every module's records wear",
	"onedesk/one/stages.py": _ENGINE + ": the record head's stages",
	"onedesk/one/figures.py": _ENGINE + ": the record head's figures",
	"onedesk/one/linked.py": _ENGINE + ": another record's fields edited on this one",
	"onedesk/one/tabs.py": _ENGINE + ": a record's tabs after its fields",
	"onedesk/one/homes.py": _ENGINE + ": where every module's record leads back to",
	"onedesk/one/doctype/record_head/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_band/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_chart/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_indicator/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_linked/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_sentence/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_verb/": _ENGINE + ": the record head",
	"onedesk/one/layer.py": _ENGINE + ": what a workspace may change about any module's forms",
	"onedesk/one/babel.py": _ENGINE + ": every module's standard records in the reader's language",
	"onedesk/one/doctype/workspace_customization/": _ENGINE + ": the workspace layer",
	"onedesk/one/boards.py": _ENGINE + ": the board every module's boards open in",
	"onedesk/one/sections.py": _ENGINE + ": what every centre's section is drawn from and saved to",
	"onedesk/one/print_format_field_template/": _ENGINE + ": the blocks every module's print formats are made of",
	"onedesk/one/ready.py": _ENGINE + ": the READY mechanisms (docs/READY.md)",
	"onedesk/one/versions.py": _ENGINE + ": the READY mechanisms, What's New",
	"onedesk/one/tours.py": _ENGINE + ": the READY mechanisms, tours",
	"onedesk/one/setup_steps.py": _ENGINE + ": the READY mechanisms, setup steps",
	"onedesk/one/setup_wizard.py": _ENGINE + ": the first run, which sets every module up",
	# What is in One's folder on its way to the module it belongs to.
	"onedesk/one/patches/portal_account_forms.py": _RAN,
	"onedesk/one/patches/portal_address_button.py": _RAN,
	"onedesk/one/patches/portal_own_by_record.py": _RAN,
	"onedesk/one/patches/portal_settle.py": _RAN,
	"onedesk/one/privacy.py": "TrustCenter's Your Data, to move into trust_center",
	"onedesk/one/privacy_copy.py": "TrustCenter's Your Data, to move into trust_center",
	"onedesk/one/privacy_public.py": "TrustCenter's Your Data, to move into trust_center",
	"onedesk/one/custom/personal_data_deletion_request.json": "TrustCenter's Your Data, to move into trust_center",
	"onedesk/one/custom/personal_data_download_request.json": "TrustCenter's Your Data, to move into trust_center",
	"onedesk/one/webhooks.py": "OneStudio's Webhooks, to move into one_studio",
	"brand/onestudio.svg": "every product's mark is drawn in brand/, into one sprite",
	"onedesk/one/patches/holiday_names.py": "OneHR's holidays, a patch that has run",
	"onedesk/public/js/apps.js": _DESK + ": the apps a workspace turned off, which every rail, search and link asks",
	"onedesk/public/js/band.js": _DESK + ": the band every record head draws its numbers and charts in",
	"onedesk/public/js/brand.js": _DESK + ": every product's name drawn as its mark",
	"onedesk/public/js/center_section.js": _DESK + ": a centre's section, which every centre draws",
	"onedesk/public/css/center_section.css": _DESK + ": a centre's section, which every centre draws",
	"onedesk/public/js/chart_colors.js": _DESK + ": every chart's colours",
	"onedesk/public/js/check.js": _DESK + ": the check page OneBook's and OneInventory's checks both draw",
	"onedesk/public/js/crumb_switch.js": _DESK + ": every crumb's switcher",
	"onedesk/public/js/desk.js": _DESK + ": the desk itself",
	"onedesk/public/css/desk.css": _DESK + ": the desk itself",
	"onedesk/public/js/doctype_settings.js": _DESK + ": numbering, printing, approvals and automations on every record type",
	"onedesk/public/js/head.js": _DESK + ": the record head every module's records wear",
	"onedesk/public/js/island_page.js": _DESK + ": the page every module's screens are mounted in",
	"onedesk/public/js/list_names.js": _DESK + ": every list's titles",
	"onedesk/public/css/lost.css": _DESK + ": the page for what is not there, on the desk and the web",
	"onedesk/public/js/module_docs.js": _DESK + ": every module's Help and What's New",
	"onedesk/public/css/module_docs.css": _DESK + ": every module's Help and What's New",
	"onedesk/public/js/module_settings.js": _DESK + ": every module's settings",
	"onedesk/public/css/module_settings.css": _DESK + ": every module's settings",
	"onedesk/public/js/outside.js": _DESK + ": what every module leaves out of frappe's, erpnext's and hrms's pages",
	"onedesk/public/js/panel_menu.js": _DESK + ": the menu every place's crumb lists",
	"onedesk/public/js/phone_head.js": _DESK + ": every page's head on a phone",
	"onedesk/public/js/record.js": _DESK + ": the record frame every module's records open in",
	"onedesk/public/js/record_calendar.js": _DESK + ": the Calendar button on a lead, a deal, an employee or a project",
	"onedesk/public/js/record_tabs.js": _DESK + ": the tabs after every record's fields",
	"onedesk/public/js/reports.js": _DESK + ": every report",
	"onedesk/public/js/setup_wizard.js": _DESK + ": the first run, which every module adds its steps to",
	"onedesk/public/js/shell.js": _DESK + ": the shell every page is drawn in",
	"onedesk/public/css/shell.css": _DESK + ": the shell every page is drawn in",
	"onedesk/public/js/size.js": _DESK + ": a file's size in words, on the desk and OneCloud's guest pages",
	"onedesk/public/js/theme.js": _DESK + ": the theme, and every script's address",
	"onedesk/public/css/theme.css": _DESK + ": the theme",
}


def shared(path: str) -> bool:
	"""Whether a path, from the repository's root, is in SHARED."""
	return path in SHARED or any(key.endswith("/") and path.startswith(key) for key in SHARED)




def files(module: str) -> list[Path]:
	"""Every file of a module: its folder, its static files and its screens."""
	found = []
	for root in places(module):
		if root.exists():
			found += [path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
	found = [path for path in found if not shared(str(path.relative_to(ROOT)))]
	return sorted(found)


def places(module: str) -> list[Path]:
	"""Where a module's files may be: its folder, its static folders and its
	screens."""
	spec = MODULES[module]
	return [
		APP / spec["folder"],
		APP / "public" / "js" / spec["folder"],
		APP / "public" / "css" / spec["folder"],
		APP / "public" / "images" / spec["folder"],
	] + ([ROOT / "frontend" / "src" / spec["screens"]] if spec.get("screens") else []) + ([ROOT / "frontend" / spec["app"]] if spec.get("app") else [])


# What a version is taken over: what the module ships and its help pages,
# not what only we read or run (its notes, versions, tests, checks, demo, and
# the passover's stamps, which only a dev site shows).
UNSHIPPED = ("AGENTS.md", "SCRATCHPAD.md", "checks.py", "demo.py", "stamps.py")
KINDS = ("major", "minor", "fix", "internal")
SHOWN = ("major", "minor", "fix")
"""An internal version is numbered as a fix and holds the fingerprint, but is
for us: What's New and the version chip never show it."""
HEAD = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def shipped(module: str) -> list[Path]:
	"""The files a module's version is taken over."""
	return [
		path
		for path in files(module)
		if path.name not in UNSHIPPED
		and "tests" not in path.parts
		and "changelog" not in path.parts
		and path.suffix not in (".pyc",)
	]


def fingerprint(module: str) -> str:
	"""Twelve hex characters over every shipped file's path and bytes, so it
	moves with any change to the module and nothing else."""
	digest = hashlib.sha256()
	for path in shipped(module):
		digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes() + b"\0")
	return digest.hexdigest()[:12]


def changelog(module: str) -> Path:
	return APP / MODULES[module]["folder"] / "docs" / "changelog"


def number(version: str) -> tuple[int, int, int]:
	major, minor, fix = (int(one) for one in version.split("."))
	return major, minor, fix


def versions(module: str) -> list[dict]:
	"""Every version of a module, newest first: its front matter (version,
	date, kind, title, fingerprint) and its words, read from
	docs/changelog/<version>.md."""
	found = []
	for path in changelog(module).glob("*.md"):
		text = path.read_text(encoding="utf-8")
		head = HEAD.match(text)
		if not head:
			raise ValueError(f"{path} has no front matter")
		said = dict(line.split(": ", 1) for line in head.group(1).splitlines())
		said["docs"] = [one.strip() for one in said.get("docs", "").split(",") if one.strip()]
		found.append({**said, "version": path.stem, "body": text[head.end() :].strip(), "path": path})
	return sorted(found, key=lambda one: number(one["version"]), reverse=True)


def legal(module: str) -> str:
	"""What a module agrees on, as a version of it records it
	(trust_center/assemble.py `stamp`)."""
	from onedesk.trust_center import assemble

	return assemble.stamp(module)


def shown(module: str) -> list[dict]:
	"""The versions people read in What's New: every one but internal ones."""
	return [one for one in versions(module) if one["kind"] in SHOWN]


def current(module: str) -> str | None:
	"""A module's version as people see it: its newest shown entry's."""
	found = shown(module)
	return found[0]["version"] if found else None


def help_pages(module: str) -> list[dict]:
	"""A module's help pages in reading order: id, icon, title (its first
	heading), the rest of its words, and where it is, which its pictures sit
	beside."""
	folder = APP / MODULES[module]["folder"] / "docs"
	found = []
	for page, icon in MODULES[module].get("help", ()):
		text = (folder / f"{page}.md").read_text(encoding="utf-8")
		title, _, body = text.partition("\n")
		found.append(
			{"id": page, "icon": icon, "title": title.lstrip("# ").strip(), "body": body.strip(), "path": folder / f"{page}.md"}
		)
	return found


GROWN = ("major", "minor")
"""A version that makes a module's hand looks stale: people work it
differently, so a person looks again."""


def looks(module: str) -> dict[str, dict]:
	"""The hand looks that hold now: each version's `looked:` and `looked_by:`,
	from the newest back to the newest major or minor, which a look must not
	be older than."""
	found = {}
	for one in versions(module):
		for key in (key.strip() for key in one.get("looked", "").split(",") if key.strip()):
			found.setdefault(key, {"version": one["version"], "by": one.get("looked_by", "")})
		if one["kind"] in GROWN:
			break
	return found


def registry(module: str) -> list[dict]:
	"""Where a module stands on each point it is held to before live: for a
	point a person must look at, the version they last looked at it in."""
	checked = looks(module)
	return [
		{
			"point": key,
			"number": point["number"],
			"title": point["title"],
			"look": HAND.get(key),
			"checked": checked.get(key),
		}
		for key, point in POINTS.items()
	]


INTERFACE_KEYS = {"tabs", "fields", "cards", "track", "states", "links", "views"}


def _states(said: dict | None) -> dict:
	"""The list's strip: the field it counts, its values in the order the
	strip shows them (the rest after, by count) and those it leaves out.
	Undeclared, the strip counts `status`, by count. A record type whose
	kinds are no one field's values names them as `kinds` instead, each a
	label and its filters ([field, operator, value]), counted in that order."""
	said = said or {}
	strange = set(said) - {"field", "order", "hide", "kinds"}
	if strange:
		raise ValueError(f"a strip declares {sorted(strange)}")
	kinds = []
	for one in said.get("kinds") or ():
		if set(one) != {"label", "filters"} or not one["filters"]:
			raise ValueError(f"a strip's kind says a label and its filters: {one}")
		kinds.append({"label": str(one["label"]), "filters": [list(rule) for rule in one["filters"]]})
	return {"field": said.get("field", "status"), "order": list(said.get("order") or ()), "hide": list(said.get("hide") or ()), "kinds": kinds}


VIEW_KEYS = {"name", "label", "icon", "island"}


def _view(said: dict) -> dict:
	"""A way of looking at a list beside frappe's own (List, Report, Kanban…):
	its name in the route (`/view/<name>`), its label and icon in the view
	switcher, and the island it draws. The record type's `default_view` may
	name it."""
	if set(said) != VIEW_KEYS or not re.fullmatch(r"[A-Z][a-z]+", said["name"]):
		raise ValueError(f"a view says a one-word name, a label, an icon and its island: {said}")
	return {**said, "label": str(said["label"])}


LINK_KEYS = {"label", "icon", "new", "list", "open", "with", "when"}


def _link(said: dict) -> dict:
	"""A record's shortcut: a new record of `new`, the list of `list`, or
	the record this one's `open` field names, with `with` (the other type's
	field: this record's field) carried over, shown while every `when`
	([field, "=" | "!=" | "in", value]) holds."""
	strange = set(said) - LINK_KEYS
	if strange or not said.get("label") or sum(bool(said.get(one)) for one in ("new", "list", "open")) != 1:
		raise ValueError(f"a link must say a label and one of new, list or open: {said}")
	return {
		"label": str(said["label"]),
		"icon": said.get("icon") or "arrow-up-right",
		"new": said.get("new"),
		"list": said.get("list"),
		"open": said.get("open"),
		"with": dict(said.get("with") or {}),
		"when": [list(one) for one in said.get("when") or ()],
	}


def interface() -> dict:
	"""How each record type is drawn, as every module declares it under
	"interface": icons for its tabs and fields, at most four head cards, the
	row whose steps are its track, the states its list's strip counts and
	its list's views of its own. The renderer reads this and nothing
	else; a record type is declared by one module only."""
	found = {}
	for module, one in MODULES.items():
		for doctype, said in (one.get("interface") or {}).items():
			strange = set(said) - INTERFACE_KEYS
			if strange:
				raise ValueError(f"{module} declares {sorted(strange)} for {doctype}")
			if doctype in found:
				raise ValueError(f"{doctype} is declared by {found[doctype]['module']} and {module}")
			if len(said.get("cards") or ()) > 4:
				raise ValueError(f"{module} gives {doctype} more than four head cards")
			found[doctype] = {
				"module": module,
				"tabs": dict(said.get("tabs") or {}),
				"fields": dict(said.get("fields") or {}),
				"cards": [{**card, "title": str(card["title"])} if card.get("title") else dict(card) for card in said.get("cards") or ()],
				"track": said.get("track"),
				"states": _states(said.get("states")),
				"links": [_link(one) for one in said.get("links") or ()],
				"views": [_view(one) for one in said.get("views") or ()],
			}
	return found

