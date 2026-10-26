"""What One lets a role do beyond its records (one/rights.py, docs/ROLES.md):
each ability is one of frappe's Permission Types on Deleted Document,
declared in permission_type/ beside this file. Everything else of the
workspace's, its settings, who may do what and its own notifications, stays
a workspace administrator's (roles.require)."""

from frappe import _lt

APP = "One"

# Everybody uses One: its User role is given to every person (rights.everyone).
EVERYONE = "One User"

DOCTYPE = "Deleted Document"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "bin",
		"group": WORKSPACE,
		"label": _lt("Everyone's Deletions"),
		"kind": "switch",
		"all": "all_deletions",
		"about": _lt("See and put back what anybody deleted, of the kinds of record they may read."),
	},
]

# Nothing of One's is given on one record.
SHARED = ()

# One's roles and what each starts with: made and written once on migrate
# (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"One User": {},
	"One Manager": {"bin": 1},
}
