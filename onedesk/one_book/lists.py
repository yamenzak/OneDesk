"""OneBook's lists, kept in its ControlCenter (one/lists.py)."""

from frappe import _lt

LISTS = (
	("Tax Category", _lt("Tax Categories"), _lt("Tax Category")),
	("Finance Book", _lt("Finance Books"), _lt("Finance Book")),
)
