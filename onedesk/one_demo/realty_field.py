"""The field Palm Key Properties shows (realty.py): properties let and sold
for their owners, and the tenants who rent them."""

from onedesk.one.registry.model import _lt
from onedesk.one_demo.field import Field

COMPANY = "Palm Key Properties"

REAL_ESTATE = Field(
	"real_estate",
	_lt("Real Estate"),
	_lt("Properties, owners and tenants."),
	("one_portal",),
	{"working_day": {"starts": "09:00", "ends": "18:00"}},
	COMPANY,
)

FIELDS = (REAL_ESTATE,)
