"""The fields Creek Trading shows (trading.py): goods bought in and sold from
its stores; and a shop's, which no company of the group keeps, nearest to
it."""

from onedesk.one.registry.model import _lt
from onedesk.one_demo.field import Field

COMPANY = "Creek Trading"

TRADING = Field(
	"trading",
	_lt("Trading"),
	_lt("Buys and sells goods."),
	("one_inventory", "one_portal"),
	{"working_day": {"starts": "09:00", "ends": "18:00"}},
	COMPANY,
)

RETAIL = Field(
	"retail",
	_lt("Retail"),
	_lt("Sells to customers in a shop."),
	("one_inventory", "one_display"),
	{"working_day": {"starts": "10:00", "ends": "22:00"}},
	COMPANY,
	"no company of the group keeps a shop, and Creek Trading sells goods from its stores as a shop does",
)

FIELDS = (TRADING, RETAIL)
