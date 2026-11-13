"""What OneDeck lets a role do beyond its records (one/rights.py,
docs/ROLES.md): a presentation is a file in OneCloud, so who may open,
change, share or delete one is whoever may do that to its File
(namespace.may). Its one ability is one of frappe's Permission Types on
Presentation, declared in permission_type/ beside this file. A workspace
administrator may do it without."""

from frappe import _lt

APP = "OneDeck"

# Everybody makes presentations: its User role is given to every person
# (rights.everyone).
EVERYONE = "OneDeck User"

DOCTYPE = "Presentation"

TITLE = "title"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "template",
		"group": WORKSPACE,
		"label": _lt("Keep Company Templates"),
		"kind": "switch",
		"all": "slide_template",
		"about": _lt("Save a presentation as a template everybody in the workspace can start from."),
	},
]

# Nothing of OneDeck's is given on one record.
SHARED = ()

# OneDeck's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneDeck User": {},
	"OneDeck Manager": {"template": 1},
}
