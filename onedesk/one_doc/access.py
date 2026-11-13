"""What OneDoc lets a role do beyond its records (one/rights.py,
docs/ROLES.md): a document is a file in OneCloud, so who may open, change,
share or delete one is whoever may do that to its File (namespace.may). Its
one ability is one of frappe's Permission Types on Writer Document,
declared in permission_type/ beside this file. A workspace administrator
may do it without."""

from frappe import _lt

from onedesk.one import registry

APP = registry.name("one_doc")

# Everybody writes documents: its User role is given to every person
# (rights.everyone).
EVERYONE = "OneDoc User"

DOCTYPE = "Writer Document"

TITLE = "title"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "template",
		"group": WORKSPACE,
		"label": _lt("Keep Company Templates"),
		"kind": "switch",
		"all": "doc_template",
		"about": _lt("Save a document as a template everybody in the workspace can start from."),
	},
]

# Nothing of OneDoc's is given on one record.
SHARED = ()

# OneDoc's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneDoc User": {},
	"OneDoc Manager": {"template": 1},
}
