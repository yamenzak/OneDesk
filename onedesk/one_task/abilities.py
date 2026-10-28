"""What OneTask lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on
Task, declared in permission_type/ beside this file. A workspace
administrator may do it without."""

from frappe import _lt

APP = "OneTask"

# Everybody keeps tasks: its User role is given to every person
# (rights.everyone).
EVERYONE = "OneTask User"

DOCTYPE = "Task"

TITLE = "subject"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "every",
		"group": WORKSPACE,
		"label": _lt("See Every Task"),
		"kind": "switch",
		"all": "task_every",
		"about": _lt("Open every task in the workspace, not only your own and your projects'."),
	},
]

# Nothing of OneTask's is given on one record.
SHARED = ()

# OneTask's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneTask User": {},
	"OneTask Manager": {"every": 1},
}
