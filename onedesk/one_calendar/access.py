"""What OneCalendar lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on
Event, declared in permission_type/ beside this file. A workspace
administrator may do it without."""

from frappe import _lt

from onedesk.one import registry

APP = registry.name("one_calendar")

# Everybody keeps a calendar: its User role is given to every person
# (rights.everyone).
EVERYONE = "OneCalendar User"

DOCTYPE = "Event"

TITLE = "subject"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "publish",
		"group": WORKSPACE,
		"label": _lt("Put Events on Everyone's Calendar"),
		"kind": "switch",
		"all": "calendar_publish",
		"about": _lt("Make an event everybody in the workspace sees, such as a closure or a training day."),
	},
]

# Nothing of OneCalendar's is given on one record.
SHARED = ()

# OneCalendar's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneCalendar User": {},
	"OneCalendar Manager": {"publish": 1},
}
