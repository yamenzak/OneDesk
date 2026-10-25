"""OneMail's setup steps (one/setup_steps.py, docs/READY.md mechanism 9):
the company's domains, whether people may connect mailboxes of their own,
and the templates people start from."""

import frappe
from frappe import _lt


def _domain(values: dict) -> None:
	"""The company's domain with the servers it most likely uses, as Setup
	adds it (connect.add_domain)."""
	from onedesk.one_mail import addresses, connect

	domain = addresses.domain_of(values.get("domain"))
	servers = connect.guesses(domain, None if domain in connect.KNOWN else connect.hosted_by(domain))[0]
	connect.add_domain(domain, servers["email_server"], servers["incoming_port"], servers["smtp_server"], servers["smtp_port"])


def _private(values: dict) -> None:
	from onedesk.one_mail import addresses

	frappe.db.set_default(addresses.EXTERNAL, str(int(bool(int(values.get("allowed") or 0)))))


STEPS = [
	{
		"key": "domains",
		"title": _lt("Your Company's Mail"),
		"about": _lt("Add the domain your company's mail is at, so people connect their mailbox there with its password alone."),
		"needs": "policy",
		"tab": "setup",
		"later": True,
		"fields": [
			{
				"fieldname": "domain",
				"fieldtype": "Data",
				"label": _lt("Company Domain"),
				"description": _lt("Such as yourcompany.com, whose mail servers are found for you."),
			}
		],
		"save": _domain,
		"done": lambda: bool(frappe.get_all("Email Domain", limit=1)),
	},
	{
		"key": "private",
		"title": _lt("Private Mailboxes"),
		"about": _lt("Choose whether people may connect a mailbox of their own, such as Gmail, beside the company's."),
		"needs": "policy",
		"tab": "private",
		"later": True,
		"fields": [
			{
				"fieldname": "allowed",
				"fieldtype": "Check",
				"label": _lt("People May Connect Their Own Mailboxes"),
				"default": 1,
			}
		],
		"save": _private,
	},
	{
		"key": "templates",
		"title": _lt("Mail Templates"),
		"about": _lt("Look over the emails people start from, such as a quotation's, and make them sound like your company."),
		"needs": "templates",
		"tab": "templates",
		"later": True,
	},
]
