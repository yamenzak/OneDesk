"""What will fail the first time somebody receives stock, counts it, or
registers an asset.
"""

import frappe
from frappe import _

READY, TO_DO, SUGGESTED = "Ready", "To Do", "Suggested"

STOCK_ACCOUNTS = {
	"default_inventory_account": "Default Inventory Account",
	"stock_adjustment_account": "Stock Adjustment Account",
	"stock_received_but_not_billed": "Stock Received But Not Billed",
}

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
		_rejected(),
		_held(),
		_stock_accounts(one),
		_reposted(),
		_corrected(),
		_scored(),
		_workshop(one),
		_floor(one),
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


def _rejected() -> dict:
	check = _("Rejected goods are not billed")
	if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
		return _row("rejected", check, SUGGESTED, _("A bill made from a receipt charges for what was rejected on arrival too."), "rejected")
	return _row("rejected", check, READY, _("A bill made from a receipt charges only for what was accepted."))


def _held() -> dict:
	check = _("Stock can be held for an order")
	if frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
		return _row("held", check, READY, _("An order can have its stock set aside, so no other order takes it."))
	return _row("held", check, SUGGESTED, _("Stock promised to an order can still go out on another one first."), "held")


def wrong_accounts(company_name: str) -> list[tuple[str, str]]:
	"""Warehouses whose stock is posted to an account that is not a stock
	account, as ERPNext resolves each one's account, so stock and the books
	can never agree however often they are recalculated."""
	from erpnext.stock import get_warehouse_account_map

	found = []
	for name, row in sorted(get_warehouse_account_map(company_name).items()):
		kind = row.get("account") and frappe.get_cached_value("Account", row.account, "account_type")
		if not row.get("is_group") and kind and kind != "Stock":
			found.append((name, row.account))
	return found


def _stock_accounts(one) -> dict:
	check = _("Every warehouse posts to a stock account")
	if not one.enable_perpetual_inventory:
		return _row("stock_accounts", check, READY, _("Stock is not valued in the books, so no account is used."))
	wrong = wrong_accounts(one.name)
	if wrong:
		said = ", ".join(_("{0} to {1}").format(warehouse, account) for warehouse, account in wrong)
		return _row("stock_accounts", check, TO_DO, _("These post to an account that is not a stock account, so stock and the books disagree: {0}. Set a stock account on each warehouse.").format(said))
	return _row("stock_accounts", check, READY, _("What each warehouse holds is posted to a stock account."))


def failed_reposts() -> list[str]:
	"""Recalculations of stock values that stopped with an error, so what a
	back-dated entry changed is not in the books yet."""
	return frappe.get_all("Repost Item Valuation", filters={"docstatus": 1, "status": "Failed"}, pluck="name", order_by="creation asc")


def _reposted() -> dict:
	check = _("Stock values are up to date")
	failed = failed_reposts()
	if failed:
		return _row("reposts", check, TO_DO, _("{0} recalculations after back-dated entries stopped with an error, so what they change is not in the books yet. Fix tries them again.").format(len(failed)), "reposts")
	waiting = frappe.db.count("Repost Item Valuation", {"docstatus": 1, "status": ["in", ["Queued", "In Progress"]]})
	if waiting:
		return _row("reposts", check, READY, _("{0} recalculations after back-dated entries are on their way.").format(waiting))
	return _row("reposts", check, READY, _("Every back-dated entry has been worked through."))



def _corrected() -> dict:
	check = _("Stock and the books are put right each week")
	if frappe.db.get_single_value("Stock Reposting Settings", "repost_incorrect_valuation_entries"):
		return _row("corrected", check, READY, _("Each week, stock valued wrongly or apart from the books this year is recalculated."))
	return _row("corrected", check, SUGGESTED, _("Stock valued wrongly or apart from the books stays that way until somebody recalculates it."), "corrected")

CRITERIA = (
	(
		"Delivered On Time",
		"({cost_of_on_time_shipments} / {tot_cost_shipments} if {tot_cost_shipments} > 0 else 1) * 100",
	),
	(
		"Accepted on Arrival",
		"({total_accepted_items} / {total_received_items} if {total_received_items} > 0 else 1) * 100",
	),
)


def _scored() -> dict:
	check = _("Suppliers can be scored")
	found = frappe.get_all("Supplier Scorecard Criteria", pluck="name")
	if found:
		return _row("scoring", check, READY, _("A supplier's scorecard scores them by {0}.").format(", ".join(_(one) for one in found)))
	return _row("scoring", check, SUGGESTED, _("Nothing to score suppliers by yet. Fix adds Delivered On Time and Accepted on Arrival."), "scoring")


def _absorbed(company_name: str) -> str | None:
	"""The account ERPNext keeps for costs that go into what stock is worth."""
	return frappe.db.get_value(
		"Account", {"company": company_name, "account_type": "Expenses Included In Valuation", "is_group": 0, "disabled": 0}
	)


def _workshop(one) -> dict:
	check = _("Workshop time is costed")
	if one.default_operating_cost_account:
		return _row("workshop", check, READY, _("Time on a job card is added to what was made, against {0}.").format(one.default_operating_cost_account))
	return _row(
		"workshop",
		check,
		TO_DO,
		_("Making goods that take workshop time fails until the company names an account for it. Fix uses {0}.").format(
			_absorbed(one.name) or _("the account for costs included in stock value")
		),
		"workshop",
	)


def _floor(one) -> dict:
	"""Where a new work order takes its materials to and puts what it makes."""
	check = _("Work orders know their warehouses")
	if one.default_wip_warehouse and one.default_fg_warehouse:
		return _row("floor", check, READY, _("Materials go to {0} and what is made goes to {1}.").format(one.default_wip_warehouse, one.default_fg_warehouse))
	return _row("floor", check, SUGGESTED, _("Each new work order asks where to work and where to put what it makes. Fix sets the company's Work In Progress and Finished Goods."), "floor")


def add_criteria() -> list[str]:
	made = []
	for name, formula in CRITERIA:
		if frappe.db.exists("Supplier Scorecard Criteria", name):
			continue
		criteria = frappe.get_doc(
			{"doctype": "Supplier Scorecard Criteria", "criteria_name": name, "max_score": 100, "weight": 50, "formula": formula}
		)
		criteria.flags.ignore_permissions = True
		made.append(criteria.insert().name)
	return made


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
	if not fixes():
		raise frappe.PermissionError
	if key in ("home", "workshop", "floor"):
		frappe.has_permission("Company", "write", throw=True)
	elif key == "depreciation":
		frappe.has_permission("Accounts Settings", "write", throw=True)
	one = company()
	if key == "serials":
		_settle(enable_serial_and_batch_no_for_item=1)
	elif key == "home":
		names = frappe.get_all("Warehouse", filters={"company": one.name, "is_group": 0, "disabled": 0}, order_by="lft asc", pluck="name")
		if not names:
			frappe.throw(_("Add a warehouse first."))
		company_ = frappe.get_doc("Company", one.name)
		company_.default_warehouse = home(names)
		company_.save()
	elif key == "below_zero":
		_settle(allow_negative_stock=0)
	elif key == "reorder":
		_settle(auto_indent=1)
	elif key == "held":
		_settle(enable_stock_reservation=1)
	elif key == "reposts":
		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import bulk_restart_reposting

		failed = failed_reposts()
		if failed:
			bulk_restart_reposting(failed)
	elif key == "corrected":
		_settle("Stock Reposting Settings", repost_incorrect_valuation_entries=1)
	elif key == "scoring":
		add_criteria()
	elif key == "workshop":
		account = _absorbed(one.name)
		if not account:
			frappe.throw(_("Add an account for costs included in stock value first."))
		company_ = frappe.get_doc("Company", one.name)
		company_.default_operating_cost_account = account
		company_.save()
	elif key == "floor":
		made = {name: frappe.db.get_value("Warehouse", {"company": one.name, "warehouse_name": name, "is_group": 0}) for name in ("Work In Progress", "Finished Goods")}
		if not all(made.values()):
			frappe.throw(_("Add the Work In Progress and Finished Goods warehouses first."))
		company_ = frappe.get_doc("Company", one.name)
		company_.default_wip_warehouse, company_.default_fg_warehouse = made["Work In Progress"], made["Finished Goods"]
		company_.save()
	elif key == "rejected":
		_settle(bill_for_rejected_quantity_in_purchase_invoice=0, settings="Buying Settings")
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


def _settle(settings: str = "Stock Settings", **values) -> None:
	"""Stock or Buying Settings changed through its own save, so ERPNext's
	checks hold. Whoever may fix was checked by `fix`."""
	settings = frappe.get_single(settings)
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


def fixes(user: str | None = None) -> bool:
	"""Whether somebody may make what Inventory Check offers: OneInventory's
	Fix What the Check Finds (abilities.py)."""
	from onedesk.one import rights

	return rights.held("Stock Settings", "inventory_fix", user)
