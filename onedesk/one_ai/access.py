"""What OneAI lets a role do beyond its records (one/rights.py,
docs/ROLES.md): each ability is one of frappe's Permission Types on AI
Knowledge, declared in permission_type/ beside this file. Turning OneAI on
or off, its tier and reading are a workspace administrator's."""

from frappe import _lt

APP = "OneAI"

# Everybody asks OneAI: its User role is given to every person
# (rights.everyone), and People offers no None for it.
EVERYONE = "OneAI User"

DOCTYPE = "AI Knowledge"

TITLE = "title"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "usage",
		"group": WORKSPACE,
		"label": _lt("Usage"),
		"kind": "switch",
		"all": "ai_usage",
		"about": _lt("See what OneAI used, job by job, in the last thirty days."),
	},
	{
		"key": "knowledge",
		"group": WORKSPACE,
		"label": _lt("Knowledge"),
		"kind": "switch",
		"all": "ai_knowledge",
		"about": _lt("Write the facts, terms and policies OneAI reads with every answer."),
	},
]

# Nothing of OneAI's is given on one record.
SHARED = ()

# OneAI's roles and what each starts with: made and written once on migrate
# (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneAI User": {},
	"OneAI Manager": {"usage": 1, "knowledge": 1},
}
