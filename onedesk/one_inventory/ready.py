"""What will fail the first time somebody receives stock, counts it, or
registers an asset.

The **Inventory Check** (report/inventory_check) is the Books Check's twin:
a row per check with what it means and the fix beside it.

- **Somewhere to keep stock.** A warehouse that is not a group. ERPNext's
  setup makes four; the check catches a site where they were deleted.
- **Stock is valued in the books.** Perpetual inventory posts every receipt
  and delivery to the ledger, through the company's stock accounts; an empty
  one stops the first receipt.
- **Serial and batch numbers.** Switched off by default: the item has no
  *Has Serial No* or *Has Batch No*, and a bundle is refused — while the rail
  offers Serial Numbers and Batches. Whether a business tracks them is its
  decision, so it is a suggestion.
- **Somewhere for an asset to be.** An asset will not save without a
  location, and a new company has none. The fix asks what to call the first.
- **Asset categories.** An item marked *Is Fixed Asset* needs a category, and
  a category needs the ledger its assets are kept in and how they
  depreciate. A new company has none, and its fixed-asset account is empty.
  The fix makes the usual ones from the chart's Fixed Assets ledgers, each
  depreciating straight-line monthly over its usual life.
- **Depreciation posts itself.** ERPNext books it daily when Accounts
  Settings says to; the check catches a site where it does not.
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
	return [_warehouse(one), _valued(one), _serials(), _location(), _categories(one), _depreciation()]


def _warehouse(one) -> dict:
	check = _("Somewhere to keep stock")
	found = frappe.db.count("Warehouse", {"company": one.name, "is_group": 0, "disabled": 0})
	if found:
		return _row("warehouse", check, READY, _("Stock can be received into {0} warehouses.").format(found))
	return _row("warehouse", check, TO_DO, _("There is no warehouse, so nothing can be received."), "warehouse")


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


@frappe.whitelist(methods=["POST"])
def fix(key: str, **values) -> None:
	frappe.only_for(FIXERS)
	one = company()
	if key == "serials":
		frappe.db.set_single_value("Stock Settings", "enable_serial_and_batch_no_for_item", 1)
	elif key == "location":
		add_location((values.get("location_name") or "").strip())
	elif key == "categories":
		add_categories(one)
	elif key == "depreciation":
		frappe.db.set_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically", 1)
	elif key == "warehouse":
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Stores", "company": one.name}).insert()
	else:
		frappe.throw(_("Nothing to fix for {0}.").format(key))


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
