"""What OneAccount lets a role do beyond its records (one/abilities.py,
docs/ROLES.md): each ability is one of frappe's Permission Types on Workspace
Account, declared in permission_type/ beside this file. Everything else of
the workspace's in AccountCenter stays a workspace administrator's
(roles.require): people, devices, domains, and changing the plan."""

from frappe import _lt

APP = "OneAccount"

# Everybody keeps their own account: its User role is given to every person
# (abilities.everyone).
EVERYONE = "OneAccount User"

DOCTYPE = "Workspace Account"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "plan",
		"group": WORKSPACE,
		"label": _lt("Plan and Credits"),
		"kind": "switch",
		"all": "account_plan",
		"about": _lt("See the plan, its seats and storage, OneAI credits and invoices."),
	},
]

# Nothing of OneAccount's is given on one record.
SHARED = ()

# OneAccount's roles and what each starts with: made and written once on
# migrate (abilities.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneAccount User": {},
	"OneAccount Manager": {"plan": 1},
}
