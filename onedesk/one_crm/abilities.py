"""What OneCRM lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability is one of frappe's Permission Types on
CRM Settings, declared in permission_type/ beside this file. A workspace
administrator may do it without."""

from frappe import _lt

APP = "OneCRM"

# Not everybody's: People gives it to whoever uses OneCRM.
USER = "Sales User"

DOCTYPE = "CRM Settings"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "merge",
		"group": WORKSPACE,
		"label": _lt("Merge Duplicate Leads"),
		"kind": "switch",
		"all": "crm_merge",
		"about": _lt("Fold a lead that is somebody already known into the one kept, which deletes it."),
	},
]

# Nothing of OneCRM's is given on one record.
SHARED = ()

# ERPNext's own roles and what each starts with, written once on migrate
# (rights.settle); merging deleted a lead, so it was a Sales Manager's, and still is.
DEFAULTS = {
	"Sales User": {},
	"Sales Manager": {"merge": 1},
}
