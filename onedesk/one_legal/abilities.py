"""What OneLegal lets a role do beyond its records (one/rights.py,
docs/ROLES.md): each ability is one of frappe's Permission Types on Legal
Acceptance, declared in permission_type/ beside this file. Agreeing for the
workspace and turning an optional service on stay a workspace
administrator's (gate._may_bind)."""

from frappe import _lt

APP = "OneLegal"

# Everybody reads the agreements: its User role is given to every person
# (rights.everyone).
EVERYONE = "OneLegal User"

DOCTYPE = "Legal Acceptance"

TITLE = "document"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "acceptances",
		"group": WORKSPACE,
		"label": _lt("Who Agreed"),
		"kind": "switch",
		"all": "legal_acceptances",
		"about": _lt("See who in the workspace agreed to each agreement, and when."),
	},
]

# Nothing of OneLegal's is given on one record.
SHARED = ()

# OneLegal's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneLegal User": {},
	"OneLegal Manager": {"acceptances": 1},
}
