"""What an item's and an asset's page say above their fields: the heads, the
measures they place and the verbs they offer. See one/head.py.

An item answers how many there are, how many are free to sell, how many are
on order, what they are worth, whether it is time to order more, and what it
last cost (item.py). An item marked Is Fixed Asset says how many assets it has
become instead. An asset answers what it is worth now, what it cost, how far
through its life it is, the next depreciation and service, where it is and who
has it (assets.py), and offers the two movements a person makes: Give To… and
Take Back (custody.py).
"""

from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import flt, fmt_money, formatdate, getdate, today
from frappe.utils.caching import request_cache

from onedesk.one_inventory import assets, custody, item

FIXED = [["is_fixed_asset", "=", 1]]
STOCK = [["is_stock_item", "=", 1]]
SUBMITTED = [["docstatus", "=", 1]]


@request_cache
def _item(name: str) -> dict:
	return item.said(name)


@request_cache
def _asset(name: str) -> dict:
	return assets.said(name)


def _money(value) -> str:
	return fmt_money(flt(value), currency=frappe.db.get_default("currency"))


def _count(doc, value) -> str:
	return f"{fmt_money(flt(value), precision=0)} {_(doc.stock_uom or '')}".strip()


# ------------------------------------------------------------------ an item


def on_hand(doc):
	said = _item(doc.name)
	return {"value": _count(doc, said["on_hand"]), "tone": None if said["on_hand"] > 0 else "quiet"}


def free(doc):
	return _count(doc, _item(doc.name)["free"])


def on_order(doc):
	ordered = _item(doc.name)["ordered"]
	if not ordered:
		return {"value": _count(doc, 0), "tone": "quiet", "route": None}
	return _count(doc, ordered)


def worth(doc):
	return _money(_item(doc.name)["value"])


def reorder(doc):
	said = _item(doc.name)
	if said["below"]:
		return {"value": _("Low in {0}").format(", ".join(said["below"])), "tone": "alarm"}
	return {"value": _("Above its level") if said["levels"] else _("No level set"), "tone": "quiet"}


def last_bought(doc):
	"""A service that is only ever sold was never bought, and saying so is noise."""
	last = _item(doc.name)["last"]
	if last:
		return _("{0} from {1} · {2}").format(_money(last.rate), last.supplier, formatdate(last.on_date))
	return {"value": _("Never"), "tone": "quiet"} if doc.is_stock_item else None


# ------------------------------------------------------------------ an asset


def worth_now(doc):
	return _money(_asset(doc.name)["worth"])


def cost(doc):
	return _money(_asset(doc.name)["cost"])


def _depreciating(doc) -> bool:
	said = _asset(doc.name)
	return doc.docstatus == 1 and said["depreciates"] and bool(said["months"])


def depreciation(doc):
	"""Before it is registered, or when it never depreciates. Otherwise the
	two below say it."""
	if doc.docstatus == 0:
		return {"value": _("Starts when registered"), "tone": "waiting"}
	return None if _depreciating(doc) else {"value": _("Does not depreciate"), "tone": "quiet"}


def written_off(doc):
	if not _depreciating(doc):
		return None
	said = _asset(doc.name)
	return _("{0} of {1} months").format(
		said["booked"] * said["frequency"], said["months"] * said["frequency"]
	)


def next_depreciation(doc):
	if not _depreciating(doc):
		return None
	upcoming = _asset(doc.name)["next"]
	if not upcoming:
		return {"value": _("None left"), "tone": "quiet"}
	return _("{0} on {1}").format(_money(upcoming.depreciation_amount), formatdate(upcoming.schedule_date))


def where(doc):
	return doc.location or {"value": _("Nowhere yet"), "tone": "waiting"}


def next_service(doc):
	"""Only equipment marked Maintenance Required has a service to be due."""
	service = _asset(doc.name)["service"]
	if not service:
		return {
			"value": _("No schedule"),
			"tone": "waiting",
			"route": f"/desk/asset-maintenance/new?asset_name={quote(doc.name)}",
		}
	return {
		"value": _("{0} · {1}").format(service.task_name, formatdate(service.due_date)),
		"tone": "alarm" if getdate(service.due_date) < getdate(today()) else None,
		"route": f"/desk/asset-maintenance-log/{quote(service.name)}",
	}


def who_has_it(doc):
	if not doc.custodian:
		return {"value": _("Nobody"), "tone": "quiet", "route": None}
	return _asset(doc.name)["custodian_name"] or doc.custodian


MEASURES = {
	"item.on_hand": on_hand,
	"item.free": free,
	"item.on_order": on_order,
	"item.worth": worth,
	"item.reorder": reorder,
	"item.last_bought": last_bought,
	"asset.worth_now": worth_now,
	"asset.cost": cost,
	"asset.depreciation": depreciation,
	"asset.written_off": written_off,
	"asset.next_depreciation": next_depreciation,
	"asset.where": where,
	"asset.next_service": next_service,
	"asset.who_has_it": who_has_it,
}


# ------------------------------------------------------------------ the two movements


def _movable(doc) -> bool:
	"""A sold or scrapped asset is nobody's to give."""
	return (
		doc.docstatus == 1
		and doc.status not in ("Sold", "Scrapped")
		and frappe.has_permission("Asset Movement", "create")
	)


VERBS = {
	"asset.give": {
		"doctypes": ["Asset"],
		"label": lambda doc: _("Hand To…") if doc.custodian else _("Give To…"),
		"title": lambda doc: _("Hand To Somebody Else") if doc.custodian else _("Give To"),
		"action": _lt("Give"),
		"when": _movable,
		"fields": lambda doc: [
			{
				"fieldtype": "Link",
				"fieldname": "employee",
				"label": _("Employee"),
				"options": "Employee",
				"reqd": 1,
				"filters": {"status": "Active"},
			}
		],
		"run": lambda doc, employee: custody.give(doc.name, employee) and _("Given."),
	},
	"asset.take_back": {
		"doctypes": ["Asset"],
		"label": _lt("Take Back"),
		"action": _lt("Take Back"),
		"when": lambda doc: _movable(doc) and bool(doc.custodian),
		"fields": lambda doc: [
			{
				"fieldtype": "Link",
				"fieldname": "location",
				"label": _("Kept At"),
				"options": "Location",
				"reqd": 1,
				"default": doc.location,
			}
		],
		"run": lambda doc, location: custody.take_back(doc.name, location) and _("Taken back."),
	},
}


# ------------------------------------------------------------------ the heads

HEADS = [
	{
		"doctype": "Item",
		"band": [
			{
				"label": _lt("Assets"),
				"source": "Count",
				"of_doctype": "Asset",
				"filters": [["item_code", "=", "{{ doc.name }}"], ["docstatus", "<", 2]],
				"shown_when": FIXED,
				"route": "/desk/asset?item_code={{ doc.name }}",
			},
			{
				"label": _lt("Not Yet Registered"),
				"source": "Count",
				"of_doctype": "Asset",
				"filters": [["item_code", "=", "{{ doc.name }}"], ["docstatus", "=", 0]],
				"shown_when": FIXED,
				"route": "/desk/asset?item_code={{ doc.name }}&docstatus=0",
				"tone": "waiting",
				"hide_empty": 1,
			},
			{
				"label": _lt("On Hand"),
				"source": "Measure",
				"measure": "item.on_hand",
				"shown_when": STOCK,
				"route": "/desk/query-report/Stock Balance?item_code={{ doc.name }}",
			},
			{"label": _lt("Free to Sell"), "source": "Measure", "measure": "item.free", "shown_when": STOCK},
			{
				"label": _lt("On Order"),
				"source": "Measure",
				"measure": "item.on_order",
				"shown_when": STOCK,
				"route": '/desk/purchase-order?item_code={{ doc.name }}&docstatus=1&status=["not in",["Completed","Closed"]]',
			},
			{"label": _lt("Worth"), "source": "Measure", "measure": "item.worth", "shown_when": STOCK},
			{"label": _lt("Reorder"), "source": "Measure", "measure": "item.reorder", "shown_when": STOCK},
			{
				"label": _lt("Last Bought"),
				"source": "Measure",
				"measure": "item.last_bought",
				"shown_when": [["is_fixed_asset", "=", 0]],
			},
		],
	},
	{
		"doctype": "Asset",
		"band": [
			{"label": _lt("Worth Now"), "source": "Measure", "measure": "asset.worth_now"},
			{"label": _lt("Cost"), "source": "Measure", "measure": "asset.cost"},
			{"label": _lt("Depreciation"), "source": "Measure", "measure": "asset.depreciation"},
			{"label": _lt("Written Off"), "source": "Measure", "measure": "asset.written_off"},
			{"label": _lt("Next Depreciation"), "source": "Measure", "measure": "asset.next_depreciation"},
			{"label": _lt("Where"), "source": "Measure", "measure": "asset.where"},
			{
				"label": _lt("Next Service"),
				"source": "Measure",
				"measure": "asset.next_service",
				"shown_when": [["maintenance_required", "=", 1]],
			},
			{
				"label": _lt("Who Has It"),
				"source": "Measure",
				"measure": "asset.who_has_it",
				"shown_when": SUBMITTED,
				"route": "/desk/employee/{{ doc.custodian }}",
			},
		],
		"verbs": [{"verb": "asset.give"}, {"verb": "asset.take_back"}],
	},
]
