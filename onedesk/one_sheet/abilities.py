"""What OneWorkbook lets a role do beyond its records (one/rights.py,
docs/ROLES.md): a workbook is a file in OneCloud, so who may open, change,
share or delete one is whoever may do that to its File (namespace.may). Its
one ability is one of frappe's Permission Types on Workbook, declared in
permission_type/ beside this file. A workspace administrator may do it
without."""

from frappe import _lt

APP = "OneWorkbook"

# Everybody keeps workbooks: its User role is given to every person
# (rights.everyone).
EVERYONE = "OneWorkbook User"

DOCTYPE = "Workbook"

TITLE = "title"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "template",
		"group": WORKSPACE,
		"label": _lt("Keep Company Templates"),
		"kind": "switch",
		"all": "sheet_template",
		"about": _lt("Save a workbook as a template everybody in the workspace can start from."),
	},
]

# Nothing of OneWorkbook's is given on one record.
SHARED = ()

# OneWorkbook's roles and what each starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneWorkbook User": {},
	"OneWorkbook Manager": {"template": 1},
}
