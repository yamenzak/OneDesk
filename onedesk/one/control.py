"""One's ControlCenter (docs/ONE.md): the workspace's own settings, a tab
each for the company, its branding, region and formats, sign-in and sharing,
then Pictures. Every field of the first five is System Settings', Company's
or Global Defaults' own, and each tab loads and saves only its own; Pictures
is the style each record type's drawn pictures are in (one/avatars.py).
Workspace administrators only."""

from typing import Annotated

import frappe
from frappe import _, _lt

from onedesk.one import avatars, roles, tell
from onedesk.one.sections import as_opened
from onedesk.one.sections import fields as fields_of
from onedesk.one.sections import opened as opened_of

SECTIONS = [
	("company", _lt("Company"), "building-2"),
	("branding", _lt("Branding"), "palette"),
	("formats", _lt("Region and Formats"), "globe"),
	("signin", _lt("Sign-in"), "key-round"),
	("sharing", _lt("Sharing"), "share-2"),
	("pictures", _lt("Pictures"), "image"),
]


# What each tab holds. "general" is all of them, as one page, for whoever
# still asks for it by that name (the demo's build and checks).
HOLDS = {
	"company": ("phone_no", "email", "website", "tax_id", "address_line1", "address_line2", "city", "state", "pincode", "email_footer_address"),
	"branding": ("company_logo", "one_brand_icon", "one_brand_colour", "one_frame_colour"),
	"formats": (
		"language",
		"time_zone",
		"date_format",
		"time_format",
		"number_format",
		"first_day_of_the_week",
		"one_currency_symbol",
		"one_rounded_total",
		"one_in_words",
	),
	"signin": (
		"one_two_factor",
		"two_factor_method",
		"one_password",
		"force_user_to_reset_password",
		"one_login_with_passkey",
		"login_with_email_link",
		"session_expiry",
		"deny_multiple_sessions",
		"allow_consecutive_login_attempts",
		"allow_login_after_fail",
	),
	"sharing": ("one_calendar_links", "one_record_sharing"),
}


@frappe.whitelist()
@frappe.read_only()
def sections_of() -> dict:
	"""The sections of One's ControlCenter."""
	roles.require()
	return {"sections": [{"key": key, "label": str(label), "icon": icon} for key, label, icon in SECTIONS]}


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section."],
	record: Annotated[str | None, "Not used: General is one page."] = None,
) -> dict:
	roles.require()
	if section == "pictures":
		return _pictures()
	if section != "general" and section not in HOLDS:
		frappe.throw(_("There is no such section."))
	return _general(section)


@frappe.whitelist(methods=["POST"])
def save(
	section: Annotated[str, "Which section."],
	values: Annotated[str | dict, "What was changed."],
	opened: Annotated[str | list | None, "The records as the page loaded them: doctype, name and modified."] = None,
	record: Annotated[str | None, "Not used: General is one page."] = None,
) -> dict:
	roles.require()
	if section != "general" and section not in HOLDS:
		frappe.throw(_("There is nothing to save here."))
	_hearing(opened)
	values = frappe.parse_json(values) or {}
	if section in HOLDS:
		values = {name: value for name, value in values.items() if name in HOLDS[section]}
	_save_general(values)
	frappe.db.commit()
	return _general(section)


def _pictures() -> dict:
	"""The optional services pictures come from (Gravatar, Google's logos),
	switched as TrustCenter switches them, then the style drawn for each
	record type with none of its own (avatars.py)."""
	from onedesk.trust_center import gate, services

	chosen = avatars.chosen()
	named = {one["key"]: one for one in avatars.styles()}
	return {
		"services": [one for one in services.standing() if one["key"] in PICTURE_SERVICES],
		"may_bind": gate._may_bind(),
		"kinds": [
			{"doctype": kind, "label": _(kind), "style": chosen.get(kind), "title": named.get(chosen.get(kind), {}).get("title")}
			for kind in avatars.KINDS
			if frappe.db.exists("DocType", kind)
		],
		"styles": avatars.styles(),
		"opened": [],
	}


PICTURE_SERVICES = ("gravatar", "logos")


def _hearing(opened) -> None:
	"""The records as the page loaded them, for `sections.as_opened`."""
	frappe.flags.one_opened = {f"{one['doctype']}:{one['name']}": one["modified"] for one in frappe.parse_json(opened) or []}


SYSTEM = ("date_format", "time_format", "number_format", "first_day_of_the_week", "one_calendar_links")


def _company():
	name = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	return frappe.get_doc("Company", name) if name else None


def _general(section: str = "general") -> dict:
	from onedesk.one_calendar import feed

	company = _company()
	system = frappe.get_single("System Settings")
	account = frappe.get_single("Workspace Account")
	defaults = frappe.get_single("Global Defaults")
	address = _company_address(company)
	fields = (
		fields_of("Company", ("company_logo", *ON_DOCUMENTS, *ON_SCREEN))
		+ fields_of("Address", ADDRESS)
		+ _zones(_switches(fields_of("System Settings", ("language", "time_zone", *SYSTEM, *SIGNING_IN, *FOOTER))))
		+ _switches(fields_of("Global Defaults", AMOUNTS))
	)
	said = {
		"name": account.workspace_name,
		"company": company.company_name if company else None,
		"country": company.country if company else system.country,
		"currency": company.default_currency if company else None,
		"fields": [{**one, **_said_on_general(one["fieldname"], system)} for one in fields]
		+ _signing_in_fields()
		+ _sharing_fields()
		+ _amount_fields(),
		"values": {
			"company_logo": company.company_logo if company else None,
			**{name: company.get(name) if company else None for name in (*ON_DOCUMENTS, *ON_SCREEN)},
			**{name: address.get(name) if address else None for name in ADDRESS},
			"language": system.language,
			"time_zone": system.time_zone,
			**{name: system.get(name) for name in (*SYSTEM, *SIGNING_IN, *FOOTER)},
			**{name: defaults.get(name) for name in AMOUNTS},
			"one_rounded_total": 0 if defaults.disable_rounded_total else 1,
			"one_in_words": 0 if defaults.disable_in_words else 1,
			"one_currency_symbol": 0 if frappe.utils.cint(defaults.hide_currency_symbol) else 1,
			"allow_login_after_fail": str(system.allow_login_after_fail or 60),
			"one_record_sharing": 0 if system.disable_document_sharing else 1,
			"one_calendar_links": 1 if feed.allowed() else 0,
			"one_two_factor": _two_factor(system),
			"one_password": str(system.minimum_password_score or "") if system.enable_password_policy else "",
		},
		"opened": opened_of(company, system, address, defaults),
	}
	if not said["values"].get("email_footer_address"):
		said["values"]["email_footer_address"] = _mail_address(company, address)
	if section in HOLDS:
		held = HOLDS[section]
		said["fields"] = [one for one in said["fields"] if one["fieldname"] in held]
		said["values"] = {name: value for name, value in said["values"].items() if name in held}
	said["logo"] = company.company_logo if company else None
	said["brand"] = company.get("one_brand_colour") if company else None
	said["frame"] = company.get("one_frame_colour") if company else None
	return said


def _mail_address(company, address) -> str:
	"""The address at the foot of the workspace's mails, as the company's own
	address says it, until somebody writes something else."""
	if not company or not address:
		return ""
	return "\n".join(
		one
		for one in (
			company.company_name,
			address.address_line1,
			address.address_line2,
			" ".join(filter(None, (address.city, address.state, address.pincode))),
			_(company.country) if company.country else "",
		)
		if one
	)


def _amount_fields() -> list:
	"""Global Defaults' three switches that say what is hidden, said the
	right way round: on shows it."""
	return [
		{
			"fieldname": "one_currency_symbol",
			"fieldtype": "Switch",
			"label": _("Currency Symbol"),
			"description": _("Amounts show their currency's symbol."),
		},
		{
			"fieldname": "one_rounded_total",
			"fieldtype": "Switch",
			"label": _("Rounded Totals"),
			"description": _("Sales and purchases are rounded to a whole amount."),
		},
		{
			"fieldname": "one_in_words",
			"fieldtype": "Switch",
			"label": _("Totals in Words"),
			"description": _("Sales and purchases say their total in words."),
		},
	]


AMOUNTS = ("hide_currency_symbol", "disable_rounded_total", "disable_in_words")


ON_DOCUMENTS = ("one_brand_colour", "phone_no", "email", "website", "tax_id")


ON_SCREEN = ("one_frame_colour",)


ADDRESS = ("address_line1", "address_line2", "city", "state", "pincode")


def _company_address(company):
	"""The company's own primary address, as ERPNext finds it for a document."""
	if not company:
		return None
	name = frappe.db.get_value(
		"Address",
		{"is_your_company_address": 1, "name": ["in", _linked_addresses(company.name)]},
		"name",
		order_by="is_primary_address desc, modified desc",
	)
	return frappe.get_doc("Address", name) if name else None


def _linked_addresses(company: str) -> list[str]:
	return frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Company", "link_name": company},
		pluck="parent",
	) or [""]


def _save_company_address(company, values: dict) -> None:
	wanted = {name: (values.get(name) or "").strip() for name in ADDRESS if name in values}
	if not wanted:
		return
	address = _company_address(company)
	if not address:
		if not wanted.get("address_line1"):
			return
		address = frappe.new_doc("Address")
		address.update(
			{
				"address_title": company.company_name,
				"address_type": "Billing",
				"country": company.country,
				"is_your_company_address": 1,
				"is_primary_address": 1,
				"links": [{"link_doctype": "Company", "link_name": company.name}],
			}
		)
	else:
		as_opened(address)
	if all(address.get(name) == value for name, value in wanted.items()) and not address.is_new():
		return
	address.update(wanted)
	address.save(ignore_permissions=True)


SIGNING_IN = (
	"two_factor_method",
	"session_expiry",
	"one_login_with_passkey",
	"login_with_email_link",
	"deny_multiple_sessions",
	"allow_consecutive_login_attempts",
	"allow_login_after_fail",
	"force_user_to_reset_password",
)


FOOTER = ("email_footer_address",)


LOCKOUT = (("60", _lt("1 minute")), ("300", _lt("5 minutes")), ("900", _lt("15 minutes")), ("3600", _lt("1 hour")))


EXPIRY = (
	("08:00", _lt("8 hours")),
	("24:00", _lt("1 day")),
	("168:00", _lt("1 week")),
	("240:00", _lt("10 days")),
	("720:00", _lt("30 days")),
)


GENERAL_SAID = {
	"company_logo": _lt("On printed and sent invoices, quotes and orders."),
	"one_brand_colour": _lt("Used for the company name, lines and banner in letter heads."),
	"one_frame_colour": _lt("The rail and the bars around every screen, for everyone. Leave it empty for One's own."),
	"language": _lt("For everyone who hasn't chosen their own in Profile."),
	"time_zone": _lt("For everyone who hasn't chosen their own in Profile."),
	"one_login_with_passkey": _lt("People sign in with the passkey on their own device, without a password."),
	"session_expiry": _lt("How long someone stays signed in while inactive."),
	"two_factor_method": _lt("An authenticator app on their phone, or a code by email."),
	"email_footer_address": _lt("At the foot of every mail the workspace sends. Leave it empty for none."),
	"login_with_email_link": _lt("People can sign in with a link sent to their email instead of a password."),
	"deny_multiple_sessions": _lt("Signing in somewhere new signs a person out everywhere else."),
	"allow_consecutive_login_attempts": _lt("After this many wrong passwords in a row, signing in is refused for a while."),
	"allow_login_after_fail": _lt("How long signing in is refused after too many wrong passwords."),
	"force_user_to_reset_password": _lt("Then a new one is asked for at sign-in. 0 means they never expire."),
	"hide_currency_symbol": _lt("Amounts are shown without their currency symbol."),
	"disable_rounded_total": _lt("Sales and purchases are not rounded to a whole amount."),
	"disable_in_words": _lt("Sales and purchases don't say their total in words."),
}


GENERAL_LABELS = {
	"one_login_with_passkey": _lt("Passkey Sign-in"),
	"email_footer_address": _lt("Address in Mails"),
	"login_with_email_link": _lt("Email Link Sign-in"),
	"deny_multiple_sessions": _lt("One Device at a Time"),
	"allow_consecutive_login_attempts": _lt("Wrong Passwords Before a Lockout"),
	"allow_login_after_fail": _lt("Locked Out For"),
	"force_user_to_reset_password": _lt("Passwords Expire After (Days)"),
}


def _said_on_general(fieldname: str, system) -> dict:
	said = {"description": str(GENERAL_SAID[fieldname])} if fieldname in GENERAL_SAID else {}
	if fieldname in GENERAL_LABELS:
		said["label"] = str(GENERAL_LABELS[fieldname])
	if fieldname == "allow_login_after_fail":
		options = [{"value": value, "label": str(label)} for value, label in LOCKOUT]
		now = str(system.allow_login_after_fail or 60)
		if now not in dict(LOCKOUT):
			options.append({"value": now, "label": _("{0} seconds").format(now)})
		said.update({"fieldtype": "Select", "options": options})
	if fieldname == "session_expiry":
		options = [{"value": value, "label": str(label)} for value, label in EXPIRY]
		if system.session_expiry and system.session_expiry not in dict(EXPIRY):
			options.append({"value": system.session_expiry, "label": _("{0} hours").format(system.session_expiry.split(":")[0])})
		said.update({"fieldtype": "Select", "options": options, "label": _("Signed Out After")})
	if fieldname == "two_factor_method":
		said.update(
			{
				"options": [{"value": "OTP App", "label": _("Authenticator App")}, {"value": "Email", "label": _("Email")}],
				"label": _("The Code Comes From"),
				"depends_on": "eval:doc.one_two_factor && doc.one_two_factor != 'off'",
			}
		)
	return said


def _signing_in_fields() -> list:
	"""Two of System Settings' rules as one choice each: two-factor is a switch
	plus a flag on every role, and the password rule a switch plus a score."""
	return [
		{
			"fieldname": "one_two_factor",
			"fieldtype": "Select",
			"label": _("Two-Factor Sign-in"),
			"options": [
				{"value": "off", "label": _("Off")},
				{"value": "admins", "label": _("Administrators")},
				{"value": "everybody", "label": _("Everyone")},
			],
			"description": _("A code after the password. Each person sets it up the next time they sign in."),
		},
		{
			"fieldname": "one_password",
			"fieldtype": "Select",
			"label": _("Passwords"),
			"options": [
				{"value": "", "label": _("Any password")},
				{"value": "2", "label": _("Hard to guess")},
				{"value": "3", "label": _("Very hard to guess")},
				{"value": "4", "label": _("Strongest")},
			],
			"description": _("Checked when someone sets or changes their password."),
		},
	]


def _sharing_fields() -> list:
	"""Frappe's switch says sharing is off; the page's says it is on."""
	return [
		{
			"fieldname": "one_record_sharing",
			"fieldtype": "Switch",
			"label": _("Record Sharing"),
			"description": _("Lets people share a record with someone who can't otherwise open it."),
		}
	]


EVERYBODY = "All"


def _two_factor(system) -> str:
	if not system.enable_two_factor_auth:
		return "off"
	if frappe.db.get_value("Role", EVERYBODY, "two_factor_auth"):
		return "everybody"
	return "admins"


def _zones(fields: list) -> list:
	"""System Settings' form fills its Time Zone list in the browser, so the
	field arrives with none: shown blank, and saved blank, which frappe refuses."""
	from frappe.utils.momentjs import get_all_timezones

	return [{**one, "options": "\n".join(get_all_timezones())} if one["fieldname"] == "time_zone" else one for one in fields]


def _switches(fields: list) -> list:
	"""A Check on a settings page is drawn as frappe's Switch, as the rest of
	Settings draws them. The value is the same 0 or 1."""
	return [{**one, "fieldtype": "Switch"} if one["fieldtype"] == "Check" else one for one in fields]


def _save_general(values: dict) -> None:
	company = _company()
	if company:
		changed = {
			name: values[name] or None
			for name in ("company_logo", *ON_DOCUMENTS, *ON_SCREEN)
			if name in values and (values[name] or None) != (company.get(name) or None)
		}
		if changed:
			as_opened(company).update(changed)
			company.save(ignore_permissions=True)
		if "one_frame_colour" in changed:
			from onedesk.one import company as workspace_company

			frappe.publish_realtime(
				"one_frame",
				{"colour": company.one_frame_colour or "", "ink": workspace_company.frame_ink(company.one_frame_colour)},
				after_commit=True,
			)
		was = _mail_address(company, _company_address(company))
		_save_company_address(company, values)
		# The footer follows the address while it still says what the
		# address said.
		footer = values.get("email_footer_address", frappe.db.get_single_value("System Settings", "email_footer_address"))
		if any(name in values for name in ADDRESS) and (footer or "").strip() in ("", was):
			values["email_footer_address"] = _mail_address(company, _company_address(company))
	_save_amounts(values)
	system = as_opened(frappe.get_single("System Settings"))
	guarded = (*SIGNING_IN, "enable_two_factor_auth", "enable_password_policy", "minimum_password_score", "disable_document_sharing")
	was = {name: system.get(name) for name in guarded}
	system.update({name: values[name] for name in ("language", "time_zone", *SYSTEM, *SIGNING_IN, *FOOTER) if name in values})
	if "one_record_sharing" in values:
		system.disable_document_sharing = 0 if frappe.utils.cint(values["one_record_sharing"]) else 1
	if "one_password" in values:
		system.enable_password_policy = 1 if values["one_password"] else 0
		system.minimum_password_score = values["one_password"] or system.minimum_password_score
	wanted = values.get("one_two_factor") or "off"
	if "one_two_factor" in values:
		system.enable_two_factor_auth = 0 if wanted == "off" else 1
	if system.enable_two_factor_auth and system.otp_issuer_name in (None, "", "Frappe Framework", "One"):
		# The name an authenticator app lists the code under: the workspace's,
		# as the top bar names it.
		system.otp_issuer_name = (
			frappe.db.get_single_value("Workspace Account", "workspace_name") or frappe.defaults.get_global_default("company") or "One"
		)
	system.save(ignore_permissions=True)
	changed = [name for name in guarded if str(was[name] or "") != str(system.get(name) or "")]
	if changed:
		meta = frappe.get_meta("System Settings")
		tell.sign_in_rules_changed([_(meta.get_label(name)) for name in changed])
	if "one_two_factor" in values and wanted != "off":
		frappe.db.set_value("Role", roles.ADMINISTRATOR, "two_factor_auth", 1)
		frappe.db.set_value("Role", EVERYBODY, "two_factor_auth", 1 if wanted == "everybody" else 0)


def _save_amounts(values: dict) -> None:
	"""Global Defaults' on_update hides or shows the rounded total and the
	amount in words on every sale and purchase form. The page says them the
	right way round (Rounded Totals, Totals in Words)."""
	if "one_rounded_total" in values:
		values["disable_rounded_total"] = 0 if frappe.utils.cint(values["one_rounded_total"]) else 1
	if "one_in_words" in values:
		values["disable_in_words"] = 0 if frappe.utils.cint(values["one_in_words"]) else 1
	if "one_currency_symbol" in values:
		values["hide_currency_symbol"] = 0 if frappe.utils.cint(values["one_currency_symbol"]) else 1
	defaults = frappe.get_single("Global Defaults")
	wanted = {name: frappe.utils.cint(values[name]) for name in AMOUNTS if name in values}
	if any(frappe.utils.cint(defaults.get(name)) != value for name, value in wanted.items()):
		as_opened(defaults).update(wanted)
		frappe.flags.one_amounts = True
		try:
			defaults.save(ignore_permissions=True)
		finally:
			frappe.flags.one_amounts = False
