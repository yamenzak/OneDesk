"""What OneProject lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on
Project, declared in permission_type/ beside this file. A workspace
administrator may do it without."""

from frappe import _lt

APP = "OneProject"

# Everybody may be on a project: its User role is given to every person
# (rights.everyone).
EVERYONE = "OneProject User"

DOCTYPE = "Project"

TITLE = "project_name"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "every",
		"group": WORKSPACE,
		"label": _lt("See Every Project"),
		"kind": "switch",
		"all": "project_every",
		"about": _lt("Open every project in the workspace, not only those you are on."),
	},
]

# Nothing of OneProject's is given on one record.
SHARED = ()

# OneProject's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneProject User": {},
	"OneProject Manager": {"every": 1},
}
