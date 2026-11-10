"""The test mail sink (deploy/testmail): what reached an address on the test
domain, newest first, so a rehearsal can sign up as somebody there and open
the link it was mailed. Nothing is ever sent from it, and Cloudflare deletes
each message after seven days (setup.py, sink)."""

import html
import re
from email import message_from_bytes, policy

import frappe
from frappe import _
from frappe.utils import cint

from onedesk.one_admin import operator, setup, site, storage

NEWEST = 5
MOST = 20
LINK = re.compile(r"https?://[^\s\"'<>]+")


def domain() -> str | None:
	"""The test domain Set Up Cloudflare turned Email Routing on for."""
	return frappe.db.get_default(setup.TEST_MAIL_DOMAIN)


def address(name: str) -> str:
	"""An address on the test domain for a rehearsal to use, such as
	`address("signup+1105")`."""
	held = domain()
	if not held:
		frappe.throw(_("Set Up Cloudflare hasn't made the test mail domain yet."))
	return f"{name.strip().lower()}@{held}"


def bucket() -> str:
	env = (frappe.db.get_single_value("One Admin Settings", "environment") or "").strip().lower() or None
	return setup.for_env(env, setup.TESTMAIL)


def newest(recipient: str, limit: int = NEWEST) -> list[dict]:
	"""The newest messages kept for an address on the test domain, each
	read (`parsed`), newest first. What a script calls."""
	site.require_admin()
	recipient = (recipient or "").strip().lower()
	held = domain()
	if not held or recipient.rpartition("@")[2] != held:
		frappe.throw(_("{0} isn't on the test mail domain.").format(recipient))
	client, name = storage._client("Global"), bucket()
	keys, after = [], None
	while True:
		asked = {"Bucket": name, "Prefix": f"{recipient}/"}
		if after:
			asked["ContinuationToken"] = after
		page = client.list_objects_v2(**asked)
		keys += [one["Key"] for one in page.get("Contents") or []]
		after = page.get("NextContinuationToken")
		if not after:
			break
	return [{"key": key, **parsed(client.get_object(Bucket=name, Key=key)["Body"].read())} for key in sorted(keys, reverse=True)[:limit]]


def parsed(raw: bytes) -> dict:
	"""A kept message as a rehearsal reads it: who, what, when, its text and
	every link in it, in order and once each. Pure."""
	message = message_from_bytes(raw, policy=policy.default)
	text = message.get_body(preferencelist=("plain",))
	page = message.get_body(preferencelist=("html",))
	text = text.get_content() if text else ""
	page = page.get_content() if page else ""
	links = [html.unescape(one).rstrip(".,;)") for one in LINK.findall(page or text)]
	return {
		"from": str(message["From"] or ""),
		"to": str(message["To"] or ""),
		"subject": str(message["Subject"] or ""),
		"date": str(message["Date"] or ""),
		"text": text,
		"html": page,
		"links": list(dict.fromkeys(links)),
	}


@frappe.whitelist()
@frappe.read_only()
def read(address: str, limit: int = NEWEST) -> list[dict]:
	"""For operators: the newest messages kept for an address on the test
	domain."""
	operator._may()
	return newest(address, min(cint(limit) or NEWEST, MOST))
