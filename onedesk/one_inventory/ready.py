"""What will fail the first time somebody receives stock, counts it, or
registers an asset.
"""

import frappe
from frappe import _

FIXERS = ("Stock Manager", "Accounts Manager", "Workspace Administrator")

READY, TO_DO, SUGGESTED = "Ready", "To Do", "Suggested"

#: The company's accounts perpetual inventory posts through.
STOCK_ACCOUNTS = {
	"default_inventory_account": "Default Inventory Account",
	"stock_adjustment_account": "Stock Adjustment Account",
	"stock_received_but_not_billed": "Stock Received But Not Billed",
}

#: The usual asset categories: the chart's Fixed Assets ledger each is kept
#: in, and its life in months.
USUAL = (
	("Computers", "Electronic Equipment", 36),
	("Software", "Software", 36),
	("Furniture", "Furniture and Fixtures", 60),
	("Office Equipment", "Office Equipment", 60),
	("Machinery", "Plants and Machineries", 120),
)


def company():
	from erpnext import get_default_company

	return frappe.get_cached_doc("Company", get_default_company())


def _row(key, check, state, says, fix=None) -> dict:
	return {"key": key, "check": check, "state": state, "says": says, "fix": fix if state != READY else None}


def checks() -> list[dict]:
	one = company()
	return [
		_warehouse(one),
		_home(one),
		_valued(one),
		_below_zero(),
		_reorder(),
		_serials(),
		_location(),
		_categories(one),
		_depreciation(),
		_registered(),
		_serviced(one),
	]


def _warehouse(one) -> dict:
	check = _("Somewhere to keep stock")
	found = frappe.db.count("Warehouse", {"company": one.name, "is_group": 0, "disabled": 0})
	if found:
		return _row("warehouse", check, READY, _("Stock can be received into {0} warehouses.").format(found))
	return _row("warehouse", check, TO_DO, _("There is no warehouse, so nothing can be received."), "warehouse")


def _home(one) -> dict:
	check = _("Stock has a warehouse to go to")
	home = one.default_warehouse
	if home:
		return _row("home", check, READY, _("A new item is kept in {0} unless it says otherwise.").format(home))
	if not frappe.db.exists("Warehouse", {"company": one.name, "is_group": 0, "disabled": 0}):
		return _row("home", check, TO_DO, _("Add a warehouse first."))
	return _row("home", check, SUGGESTED, _("A new item has no warehouse, so every receipt and count asks for one on each line."), "home")


def home(names: list[str]) -> str | None:
	"""The warehouse stock goes to when nothing says otherwise: the one called
	Stores if there is one, or else the first. Pure over warehouse names."""
	return next((name for name in names if name.split(" - ")[0].strip().lower() == "stores"), names[0] if names else None)


def _below_zero() -> dict:
	check = _("Stock cannot go below zero")
	if frappe.db.get_single_value("Stock Settings", "allow_negative_stock"):
		return _row("below_zero", check, TO_DO, _("Stock can go below zero, and what it is worth goes wrong with it."), "below_zero")
	return _row("below_zero", check, READY, _("Nothing leaves a warehouse that does not have it."))


def _reorder() -> dict:
	check = _("Running low asks for more")
	levels = frappe.db.count("Item Reorder", {"parenttype": "Item", "warehouse_reorder_level": [">", 0]})
	if frappe.db.get_single_value("Stock Settings", "auto_indent"):
		return _row("reorder", check, READY, _("An item at its reorder level gets a material request each night."))
	if not levels:
		return _row("reorder", check, READY, _("No item has a reorder level yet. Set one on an item's Stock view."))
	return _row("reorder", check, SUGGESTED, _("{0} items have a reorder level, but nothing is asked for when they reach it. To Order still lists them.").format(levels), "reorder")


def _valued(one) -> dict:
	check = _("Stock is valued in the books")
	if not one.enable_perpetual_inventory:
		return _row("valued", check, SUGGESTED, _("Receipts and deliveries do not reach the ledger, so the balance sheet has no stock."), "company")
	missing = [_(label) for field, label in STOCK_ACCOUNTS.items() if not one.get(field)]
	if missing:
		return _row("valued", check, TO_DO, _("Set on the company: {0}.").format(", ".join(missing)), "company")
	return _row("valued", check, READY, _("Every receipt and delivery is posted to the stock accounts."))


def _serials() -> dict:
	check = _("Serial and batch numbers can be used")
	if frappe.db.get_single_value("Stock Settings", "enable_serial_and_batch_no_for_item"):
		return _row("serials", check, READY, _("An item can have serial numbers or batches."))
	return _row("serials", check, SUGGESTED, _("Switched off, so no item can have serial numbers or batches."), "serials")


def _location() -> dict:
	check = _("Somewhere for an asset to be")
	if frappe.db.exists("Location", {"is_group": 0}):
		return _row("location", check, READY, _("Every asset is kept at a location."))
	return _row("location", check, TO_DO, _("There is no location, and an asset will not save without one."), "location")


def categories(company_name: str) -> list[str]:
	return frappe.get_all("Asset Category Account", filters={"company_name": company_name}, pluck="parent")


def _categories(one) -> dict:
	check = _("Assets have categories")
	found = categories(one.name)
	if found:
		return _row("categories", check, READY, _("{0} categories, each with its ledger and how it depreciates.").format(len(found)))
	return _row("categories", check, TO_DO, _("There is no asset category, and an item marked Is Fixed Asset needs one."), "categories")


def _depreciation() -> dict:
	check = _("Depreciation posts itself")
	if frappe.db.get_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically"):
		return _row("depreciation", check, READY, _("Each asset's depreciation is posted to the books when it falls due."))
	return _row("depreciation", check, SUGGESTED, _("Depreciation is worked out but never posted unless somebody does it."), "depreciation")


def _registered() -> dict:
	from onedesk.one_inventory import assets

	check = _("Every asset is registered")
	waiting = assets.drafts()
	if waiting:
		return _row("drafts", check, TO_DO, _("{0} assets are drafts, so they are not depreciated or counted. Each says why on its page.").format(len(waiting)), "drafts")
	return _row("drafts", check, READY, _("Assets bought are registered and depreciating by themselves."))


def _serviced(one) -> dict:
	from onedesk.one_inventory import maintenance

	check = _("Equipment that needs servicing has a schedule")
	if not frappe.db.exists("Asset", {"docstatus": 1, "maintenance_required": 1}):
		return _row("serviced", check, READY, _("No asset is marked Maintenance Required."))
	if not frappe.db.exists("Asset Maintenance Team", {"company": one.name}):
		return _row("serviced", check, TO_DO, _("There is no maintenance team, and a schedule needs one."), "team")
	missing = maintenance.unscheduled()
	if missing:
		return _row("serviced", check, SUGGESTED, _("Marked Maintenance Required with no schedule: {0}. Add one under Assets › Maintenance.").format(", ".join(missing)))
	return _row("serviced", check, READY, _("Each asset that needs servicing has a schedule, on its people's calendars."))


@frappe.whitelist(methods=["POST"])
def fix(key: str, **values) -> None:
	frappe.only_for(FIXERS)
	one = company()
	if key == "serials":
		frappe.db.set_single_value("Stock Settings", "enable_serial_and_batch_no_for_item", 1)
	elif key == "home":
		names = frappe.get_all("Warehouse", filters={"company": one.name, "is_group": 0, "disabled": 0}, order_by="lft asc", pluck="name")
		if not names:
			frappe.throw(_("Add a warehouse first."))
		company_ = frappe.get_doc("Company", one.name)
		company_.default_warehouse = home(names)
		company_.flags.ignore_permissions = True
		company_.save()
	elif key == "below_zero":
		_settle(allow_negative_stock=0)
	elif key == "reorder":
		_settle(auto_indent=1)
	elif key == "location":
		add_location((values.get("location_name") or "").strip())
	elif key == "categories":
		add_categories(one)
	elif key == "depreciation":
		frappe.db.set_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically", 1)
	elif key == "drafts":
		from onedesk.one_inventory import assets

		left = [name for name in assets.drafts() if not assets.finish(name)]
		if left:
			frappe.msgprint(_("{0} could not be registered; each says why on its page.").format(", ".join(left)))
	elif key == "team":
		from onedesk.one_inventory import maintenance

		maintenance.add_team(one.name)
	elif key == "warehouse":
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Stores", "company": one.name}).insert()
	else:
		frappe.throw(_("Nothing to fix for {0}.").format(key))


def _settle(**values) -> None:
	"""Stock Settings changed through its own save, so ERPNext's checks hold.
	Whoever may fix was checked by `fix`."""
	settings = frappe.get_single("Stock Settings")
	settings.update(values)
	settings.flags.ignore_permissions = True
	settings.save()


def add_location(name: str) -> str:
	if not name:
		frappe.throw(_("Name the location."))
	return frappe.get_doc({"doctype": "Location", "location_name": name}).insert().name


def plan(ledgers: dict) -> list[tuple]:
	"""The usual categories this chart can keep: (category, ledger, months) for
	each whose ledger is there. Pure over {ledger name: account}."""
	return [(name, ledgers[ledger], months) for name, ledger, months in USUAL if ledger in ledgers]


def add_categories(one) -> list[str]:
	ledgers = {
		account.account_name: account.name
		for account in frappe.get_all(
			"Account",
			filters={"company": one.name, "is_group": 0, "account_type": "Fixed Asset"},
			fields=["name", "account_name"],
		)
	}
	made = []
	for name, ledger, months in plan(ledgers):
		if frappe.db.exists("Asset Category", name):
			continue
		category = frappe.get_doc(
			{
				"doctype": "Asset Category",
				"asset_category_name": name,
				"accounts": [
					{
						"company_name": one.name,
						"fixed_asset_account": ledger,
						"accumulated_depreciation_account": one.accumulated_depreciation_account,
						"depreciation_expense_account": one.depreciation_expense_account,
					}
				],
				"finance_books": [
					{"depreciation_method": "Straight Line", "total_number_of_depreciations": months, "frequency_of_depreciation": 1}
				],
			}
		).insert()
		made.append(category.name)
	if not made and not categories(one.name):
		frappe.throw(_("The chart of accounts has no Fixed Asset ledgers to keep assets in."))
	return made
