"""Who may do what in OneQuality: its one ability, a Permission Type on Non
Conformance (one/rights.py, docs/ROLES.md), and the grants ERPNext leaves
out: it gives quality management to a Quality Manager alone and lets every
desk user read it; its Quality User records and works them. A role that
reads one already keeps what it has (one/roles.py `give`).
"""

from frappe import _lt

from onedesk.one import roles

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


MANAGER = "Quality Manager"

QUALITY = (
	"Quality Goal",
	"Quality Procedure",
	"Quality Review",
	"Quality Action",
	"Non Conformance",
	"Quality Meeting",
	"Quality Feedback",
)

GIVEN = {doctype: {USER: roles.WORK, MANAGER: roles.MANAGE} for doctype in QUALITY} | {
	"Quality Feedback Template": {USER: roles.USE},
}

RAISED = {"Quality Feedback Template": {MANAGER: roles.MANAGE}}
"""ERPNext lets its Quality Manager read feedback templates and nothing
more, so `give` would leave it there and nobody could make one."""


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
	roles.open_report("Review", USER, MANAGER)
