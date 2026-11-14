"""The field Jumeirah Family Clinic shows (clinic.py): the doctors'
appointments on the calendar, the stores of what is used on patients, and,
for their privacy, mail kept to the clinic's own mailboxes."""

from onedesk.one.registry.model import _lt
from onedesk.one_demo.field import Field

COMPANY = "Jumeirah Family Clinic"

CLINIC = Field(
	"clinic",
	_lt("Clinic"),
	_lt("Patients, appointments and a waiting room."),
	("one_inventory", "one_display"),
	{"working_day": {"starts": "08:00", "ends": "20:00"}, "steps": {"one_mail": {"private": {"allowed": 0}}}},
	COMPANY,
)

FIELDS = (CLINIC,)
