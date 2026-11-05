"""What OneQuality lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on Non
Conformance, declared in permission_type/ beside this file. A workspace
administrator may do it without."""

from frappe import _lt

APP = "OneQuality"

# Not everybody's: People gives it to whoever uses OneQuality.
USER = "Quality User"

DOCTYPE = "Non Conformance"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "resolve",
		"group": WORKSPACE,
		"label": _lt("Resolve Non Conformances"),
		"kind": "switch",
		"all": "quality_resolve",
		"about": _lt("Set a non conformance to Resolved once its actions are done."),
	},
]

# Nothing of OneQuality's is given on one record.
SHARED = ()

# Its roles and what each starts with, written once on migrate
# (rights.settle): anybody in quality raises a problem, its manager closes it.
DEFAULTS = {
	"Quality User": {},
	"Quality Manager": {"resolve": 1},
}
