"""The fields Sahara Glass & Aluminium shows (making.py and the steps of the
demo's own year): a contractor that fabricates what it installs in its own
workshop, so contracting and making are both its own; and a field none of
the group's companies is in, which opens on it as the fullest of them."""

from onedesk.one.registry.model import _lt
from onedesk.one_demo.field import Field

COMPANY = "Sahara Glass & Aluminium"

CONTRACTING = Field(
	"contracting",
	_lt("Contracting"),
	_lt("Builds or installs on a customer's site."),
	("one_project", "one_inventory", "one_quality"),
	{"working_day": {"starts": "08:00", "ends": "17:00"}},
	COMPANY,
)

MANUFACTURER = Field(
	"manufacturer",
	_lt("Manufacturer"),
	_lt("Makes what it sells, on a shop floor."),
	("one_inventory", "one_factory", "one_quality"),
	{"working_day": {"starts": "07:00", "ends": "16:00"}},
	COMPANY,
)

OTHER = Field(
	"other",
	_lt("Other"),
	_lt("Something else."),
	demo=COMPANY,
	nearest="no company of the group is in no field, and Sahara Glass shows the most of One",
)

FIELDS = (CONTRACTING, MANUFACTURER, OTHER)
