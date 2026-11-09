"""OneAdmin's ControlCenter (docs/ONE.md): One Admin Settings, a tab for each
thing OneAdmin runs on, and Operators. Every field is the settings' own and
each tab saves only its own, through the record, so a key still moves to the
config (vault.py) and the other operators still hear what changed. Operators
only, on the admin site only."""

from typing import Annotated

import frappe
from frappe import _

from onedesk.one.sections import as_opened, opened as opened_of
from onedesk.one.sections import fields as fields_of
from onedesk.one_admin import site

SETTINGS = "One Admin Settings"

HOLDS = {
	"cloudflare": (
		"cloudflare_account",
		"environment",
		"cloudflare_master_token",
		"cloudflare_token",
		"cloudflare_kv",
		"cloudflare_zone",
		"tenant_domain",
		"mail_domain",
		"sender_email",
		"office_url",
		"backup_bucket",
		"keeper_url",
		"release_at",
	),
	"servers": ("aws_access_key_id", "aws_secret_access_key", "github_token"),
	"storage": ("bucket_global", "bucket_eu", "r2_key_id", "r2_secret"),
	"stripe": ("stripe_publishable_key", "stripe_secret_key", "stripe_webhook_secret"),
	"gateway": ("ai_gateway", "ai_gateway_token"),
	"weather": ("openweather_key",),
	"grace": ("grace_days", "held_days", "kept_days"),
}


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
		said["setup"] = doc.cloudflare_setup
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
