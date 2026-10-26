"""OneInventory's lists, kept in its ControlCenter (one/lists.py)."""

from frappe import _lt

LISTS = (
	("Item Group", _lt("Item Groups"), _lt("Item Group")),
	("Brand", _lt("Brands"), _lt("Brand")),
	("UOM", _lt("Units"), _lt("Unit")),
	("UOM Category", _lt("Unit Categories"), _lt("Unit Category")),
	("Item Attribute", _lt("Attributes"), _lt("Attribute")),
	("Supplier Group", _lt("Supplier Groups"), _lt("Supplier Group")),
)
