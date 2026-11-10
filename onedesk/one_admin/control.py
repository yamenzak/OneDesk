"""OneAdmin's ControlCenter (docs/ONE.md): One Admin Settings, a tab for each
thing OneAdmin runs on, and Operators. Every field is the settings' own and
each tab saves only its own, through the record, so a key still moves to the
config (vault.py) and the other operators still hear what changed. Operators
only, on the admin site only."""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils.background_jobs import is_job_enqueued

from onedesk.one.sections import as_opened, opened as opened_of
from onedesk.one.sections import fields as fields_of
from onedesk.one_admin import site
from onedesk.one_admin.setup import LOCK

SETTINGS = "One Admin Settings"

HOLDS = {
	"cloudflare": (
		"cloudflare_account",
		"environment",
		"cloudflare_master_token",
		"cloudflare_oauth_client_id",
		"cloudflare_oauth_client_secret",
		"cloudflare_oauth_scopes",
		"cloudflare_token",
		"cloudflare_kv",
		"cloudflare_zone",
		"tenant_domain",
		"mail_domain",
		"sender_email",
		"office_url",
		"backup_bucket",
		"keeper_url",
		"config_copy_key",
		"release_at",
	),
	"servers": ("aws_access_key_id", "aws_secret_access_key", "aws_template_url", "github_token"),
	"storage": ("bucket_global", "bucket_eu", "r2_key_id", "r2_secret"),
	"stripe": ("stripe_publishable_key", "stripe_secret_key", "stripe_webhook_secret"),
	"gateway": ("ai_gateway", "ai_gateway_token"),
	"weather": ("openweather_key",),
	"grace": ("grace_days", "held_days", "kept_days"),
}

AREAS = (
	("account", "cloud", ("sign-in", "account", "zone", "kv", "token ")),
	("addresses", "globe", ("worker one-tenant-router", "dns", "route", "certificate", "fallback origin")),
	("mail", "mail", ("worker one-mail", "worker one-testmail", "mail routing", "test mail routing", "catch-all", "mail sending", "sender")),
	("storage", "database", ("bucket", "domain ", "backup lock")),
	("services", "server", ()),
)
WORST = ("failed", "needs attention")


def _area_of(step: str) -> str:
	for key, _icon, starts in AREAS:
		if any(step == one.strip() or step.startswith(one) for one in starts):
			return key
	return AREAS[-1][0]


def areas_of(said: list[dict]) -> list[dict]:
	"""The last setup's steps as a tile per area: its worst state, what it
	found and every step under it. Pure."""
	held = {key: [] for key, *_rest in AREAS}
	for one in said:
		held[_area_of(one.get("step") or "")].append(one)
	tiles = []
	for key, icon, _starts in AREAS:
		steps = held[key]
		if not steps:
			continue
		states = {one.get("state") for one in steps}
		worst = next((state for state in WORST if state in states), "ready")
		found = list(dict.fromkeys(one.get("detail") for one in steps if one.get("detail")))
		tiles.append({"key": key, "icon": icon, "state": worst, "found": found[:2], "steps": steps})
	return tiles


def _only() -> None:
	site.require_admin()
	frappe.only_for(site.OPERATOR)


def _writable(section: str) -> set[str]:
	meta = frappe.get_meta(SETTINGS)
	return {name for name in HOLDS[section] if not meta.get_field(name).read_only}


def _section(section: str) -> dict:
	doc = frappe.get_single(SETTINGS)
	meta = frappe.get_meta(SETTINGS)
	said = {
		"fields": [{**one, "read_only": meta.get_field(one["fieldname"]).read_only} for one in fields_of(SETTINGS, HOLDS[section])],
		"values": {name: doc.get(name) for name in HOLDS[section]},
		"opened": opened_of(doc),
	}
	if section == "cloudflare":
		said["areas"] = areas_of(frappe.parse_json(doc.cloudflare_setup or "[]") or [])
		said["signs_in"] = bool(doc.cloudflare_oauth_client_id)
		said["running"] = is_job_enqueued(LOCK)
	return said


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section."],
	record: Annotated[str | None, "Not used: each section is one page."] = None,
) -> dict:
	_only()
	if section == "operators":
		return {"operators": site.operators()}
	if section not in HOLDS:
		frappe.throw(_("There is no such section."))
	return _section(section)


@frappe.whitelist(methods=["POST"])
def save(
	section: Annotated[str, "Which section."],
	values: Annotated[str | dict, "What was changed."],
	opened: Annotated[str | list | None, "The records as the page loaded them: doctype, name and modified."] = None,
	record: Annotated[str | None, "Not used: each section is one page."] = None,
) -> dict:
	_only()
	if section not in HOLDS:
		frappe.throw(_("There is nothing to save here."))
	frappe.flags.one_opened = {f"{one['doctype']}:{one['name']}": one["modified"] for one in frappe.parse_json(opened) or []}
	wanted = frappe.parse_json(values) or {}
	doc = as_opened(frappe.get_single(SETTINGS))
	doc.update({name: wanted[name] for name in _writable(section) if name in wanted})
	doc.save()
	return _section(section)
