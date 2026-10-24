"""What OneMail lets a role do beyond its records (one/abilities.py,
docs/ROLES.md): each ability is one or two of frappe's Permission Types on
Email Account, declared in permission_type/ beside this file."""

from frappe import _lt

APP = "OneMail"

# Everybody uses OneMail: its User role is given to every person
# (abilities.everyone), and People offers no None for it.
EVERYONE = "OneMail User"

DOCTYPE = "Email Account"

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
		"label": _lt("Mail Rules"),
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
		"label": _lt("Who Uses a Mailbox"),
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

# What OneMail's own roles start with, written once on migrate for a role
# with nothing on Email Account yet (abilities.settle).
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
