"""OneHR's lists, kept in its ControlCenter (one/lists.py)."""

from frappe import _lt

LISTS = (
	("Department", _lt("Departments"), _lt("Department")),
	("Designation", _lt("Designations"), _lt("Designation")),
	("Branch", _lt("Branches"), _lt("Branch")),
	("Employment Type", _lt("Employment Types"), _lt("Employment Type")),
	("Skill", _lt("Skills"), _lt("Skill")),
	("KRA", _lt("Key Result Areas"), _lt("Key Result Area")),
	("Grievance Type", _lt("Grievance Types"), _lt("Grievance Type")),
	("Identification Document Type", _lt("ID Document Types"), _lt("ID Document Type")),
)
