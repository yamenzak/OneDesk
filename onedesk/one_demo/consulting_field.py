"""The field Bayan Consulting shows (consulting.py): consultants' time on
projects, billed by the hour from their timesheets."""

from onedesk.one.registry.model import _lt
from onedesk.one_demo.field import Field

COMPANY = "Bayan Consulting"

SERVICES = Field(
	"services",
	_lt("Services"),
	_lt("Sells time and expertise."),
	("one_project", "one_portal"),
	{"working_day": {"starts": "09:00", "ends": "18:00"}},
	COMPANY,
)

FIELDS = (SERVICES,)
