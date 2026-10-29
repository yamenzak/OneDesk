"""What OneHR lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on
HR Settings, declared in permission_type/ beside this file. A workspace
administrator may do it without."""

from frappe import _lt

APP = "OneHR"

# Not everybody's: People gives it to whoever uses OneHR.
USER = "HR User"

DOCTYPE = "HR Settings"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "sound",
		"group": WORKSPACE,
		"label": _lt("Delete an Interview's Sound"),
		"kind": "switch",
		"all": "hr_sound",
		"about": _lt("Delete the sound of a recorded interview before its retention does, keeping what was written from it."),
	},
]

# Nothing of OneHR's is given on one record.
SHARED = ()

# ERPNext's own roles and what each starts with, written once on migrate
# (rights.settle); deleting a recording's sound was an HR Manager's, and still is.
DEFAULTS = {
	"HR User": {},
	"HR Manager": {"sound": 1},
}
