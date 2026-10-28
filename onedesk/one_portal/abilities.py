"""What OnePortal lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on
Portal Link, declared in permission_type/ beside this file. A workspace
administrator, and a customer's or supplier's manager for their own
contacts (invite.MANAGERS), may invite without it."""

from frappe import _lt

APP = "OnePortal"

# Everybody sees who is on the portal from a record's Portal dialog: its User
# role is given to every person (rights.everyone).
EVERYONE = "OnePortal User"

DOCTYPE = "Portal Link"

TITLE = "reference_name"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "invite",
		"group": WORKSPACE,
		"label": _lt("Invite to the Portal"),
		"kind": "switch",
		"all": "portal_invite",
		"about": _lt("Invite any customer's or supplier's contact to the portal, and turn their access off."),
	},
]

# Nothing of OnePortal's is given on one record.
SHARED = ()

# OnePortal's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OnePortal User": {},
	"OnePortal Manager": {"invite": 1},
}
