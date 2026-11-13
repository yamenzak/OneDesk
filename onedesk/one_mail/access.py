"""Who may open a message, and what OneMail lets a role do beyond its
records: each ability is one or two Permission Types on Email Account
(one/rights.py, docs/ROLES.md). A message in a mailbox opens for the people
who hold the mailbox and nobody else, though Frappe lets anybody with Inbox
User open any Communication by its name.
"""

import frappe
from frappe import _lt

from onedesk.one import registry, rights, roles
from onedesk.one.registry import agents
from onedesk.one_mail import linking

APP = registry.name("one_mail")

# Everybody uses OneMail: its User role is given to every person
# (rights.everyone), and People offers no None for it.
EVERYONE = "OneMail User"

DOCTYPE = "Email Account"

# What a mailbox is called where AccessCenter lists it (one/access_center.py).
TITLE = "email_id"

MAILBOXES = _lt("Mailboxes")
WORKSPACE = _lt("Workspace")

# What a scope is called in OneMail: "own" is the address the workspace
# issued the person, "all" every mailbox.
SCOPE_LABELS = {"none": _lt("No"), "own": _lt("Their Own Address"), "all": _lt("Every Mailbox")}

ABILITIES = [
	{
		"key": "signature",
		"group": MAILBOXES,
		"label": _lt("Signature and Sender Name"),
		"kind": "scope",
		"all": "mail_signature",
		"own": "mail_signature_own",
	},
	{
		"key": "away",
		"group": MAILBOXES,
		"label": _lt("Out of Office"),
		"kind": "scope",
		"all": "mail_away",
		"own": "mail_away_own",
	},
	{
		"key": "rules",
		"group": MAILBOXES,
		"label": _lt("Automation"),
		"kind": "scope",
		"all": "mail_rules",
		"own": "mail_rules_own",
		"none": _lt("Ask for Approval"),
	},
	{
		"key": "ai",
		"group": MAILBOXES,
		"label": _lt("OneAI Settings"),
		"kind": "scope",
		"all": "mail_ai",
		"own": "mail_ai_own",
	},
	{
		"key": "holders",
		"group": MAILBOXES,
		"label": _lt("Users"),
		"kind": "switch",
		"all": "mail_holders",
		"about": _lt("Give and take away a shared mailbox, and what each person may do in it."),
	},
	{
		"key": "connection",
		"group": MAILBOXES,
		"label": _lt("Connection"),
		"kind": "switch",
		"all": "mail_connection",
		"about": _lt("Give a connected mailbox its password again, or disconnect it."),
	},
	{
		"key": "connect_shared",
		"group": WORKSPACE,
		"label": _lt("Connect Shared Mailboxes"),
		"kind": "switch",
		"all": "mail_connect_shared",
	},
	{
		"key": "policy",
		"group": WORKSPACE,
		"label": _lt("Workspace and External Addresses"),
		"kind": "switch",
		"all": "mail_policy",
		"about": _lt("Give people their workspace address, and choose which mailboxes they may connect."),
	},
	{
		"key": "templates",
		"group": WORKSPACE,
		"label": _lt("Mail Templates"),
		"kind": "switch",
		"all": "mail_templates",
	},
]

# The abilities a mailbox's share can carry: what someone may do in that one
# mailbox (the Users tab of a shared mailbox).
SHARED = ("signature", "away", "rules", "ai", "holders", "connection")

# OneMail's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneMail User": {"away": "own"},
	"Mail Manager": {
		"signature": "all",
		"away": "all",
		"rules": "all",
		"ai": "all",
		"holders": 1,
		"connection": 1,
		"connect_shared": 1,
		"policy": 1,
		"templates": 1,
	},
}


RECEPTIONIST = "OneMail Receptionist"

GIVEN = {doctype: {RECEPTIONIST: ("read",)} for doctype in ("Communication", *linking.LINKED)}
"""The receptionist reads mail, and the records mail is linked to, which
frappe asks of a linked mail before it opens it."""


def settle() -> None:
	"""The receptionist's own role (manifest.py, agent_roles), made before
	OneAI's agents are given their roles, and what it reads."""
	rights.made(RECEPTIONIST, desk=False)
	roles.give(GIVEN)


def allowed(doc, ptype=None, user=None, debug=False) -> bool:
	"""The has_permission hook for Communication. It can only refuse. OneMail's
	receptionist reads Communication by its own role (GIVEN) and opens only
	the mail of a mailbox OneAI reads, which is what the mailbox's switch
	allows (gate.reads)."""
	from onedesk.one_mail import gate

	user = user or frappe.session.user
	email = doc.communication_medium == "Email" and doc.email_account
	if user == agents.email("one_mail"):
		return bool(email) and gate.reads(doc.email_account)
	if user == "Administrator" or not email:
		return True
	return bool(frappe.db.exists("User Email", {"parent": user, "email_account": doc.email_account}))
