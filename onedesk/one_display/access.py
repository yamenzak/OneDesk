"""What OneDisplay lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on
Display Settings, declared in permission_type/ beside this file. A
workspace administrator may do it without."""

from frappe import _lt

from onedesk.one import registry

APP = registry.name("one_display")

DOCTYPE = "Display Settings"

TITLE = None

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "alert",
		"group": WORKSPACE,
		"label": _lt("Send an Emergency Alert"),
		"kind": "switch",
		"all": "display_alert",
		"about": _lt("Put a message over everything on every screen, and end it."),
	},
]

# The role every OneDisplay user holds: whoever works a counter.
USER = "OneDisplay User"

# Nothing of OneDisplay's is given on one record.
SHARED = ()

# OneDisplay's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}). A User works a
# counter; a Manager runs the screens and what they show.
DEFAULTS = {
	"OneDisplay User": {},
	"OneDisplay Manager": {"alert": 1},
}
