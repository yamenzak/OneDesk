"""The assets register finishes itself.
"""

import frappe
from frappe import _

from onedesk.one_inventory.maintenance import next_service

SERIES = "ACC-ASS-.YYYY.-"


def fixed_item(doc, method=None) -> None:
	"""Item validate: a fixed-asset item makes its assets when it is bought."""
	if not doc.is_fixed_asset:
		return
	if not doc.asset_naming_series:
		doc.asset_naming_series = SERIES
	before = doc.get_doc_before_save()
	if not before or not before.is_fixed_asset:
		doc.auto_create_assets = 1


def only_location() -> str | None:
	found = frappe.get_all("Location", filters={"is_group": 0}, pluck="name", limit=2)
	return found[0] if len(found) == 1 else None


def located(doc, method=None) -> None:
	"""Purchase Receipt and Purchase Invoice validate: a fixed-asset row goes
	to the one location there is."""
	rows = [row for row in doc.get("items") if row.get("is_fixed_asset") and not row.get("asset_location")]
	if not rows:
		return
	where = only_location()
	for row in rows:
		row.asset_location = where


def registered(doc, method=None) -> None:
	"""Purchase Receipt, and Purchase Invoice that updates stock, on_submit:
	finish the assets it made."""
	field = "purchase_receipt" if doc.doctype == "Purchase Receipt" else "purchase_invoice"
	for name in frappe.get_all("Asset", filters={field: doc.name, "docstatus": 0}, pluck="name"):
		finish(name)


def drafts() -> list[str]:
	return frappe.get_all("Asset", filters={"docstatus": 0}, pluck="name")


def finish(name: str) -> bool:
	"""A draft asset completed from its category and submitted; False, with
	the reason commented on it, when it will not go."""
	frappe.db.savepoint("one_asset")
	asset = frappe.get_doc("Asset", name)
	try:
		category = frappe.get_cached_doc("Asset Category", asset.asset_category) if asset.asset_category else None
		if not category:
			raise frappe.ValidationError(_("It has no asset category."))
		asset.available_for_use_date = asset.available_for_use_date or asset.purchase_date
		if category.finance_books and not category.non_depreciable_category:
			asset.calculate_depreciation = 1
			asset.set("finance_books", [])
			asset.set_missing_values()
			for row in asset.finance_books:
				row.depreciation_start_date = None
		asset.flags.ignore_permissions = True
		asset.save()
		asset.submit()
		return True
	except frappe.ValidationError as error:
		frappe.db.rollback(save_point="one_asset")
		frappe.clear_messages()
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Asset",
				"reference_name": name,
				"content": _("Not registered by itself: {0}").format(frappe.utils.strip_html(str(error))),
			}
		).insert(ignore_permissions=True)
		return False


@frappe.whitelist()
@frappe.read_only()
def said(asset: str) -> dict:
	"""What an asset's page says first: what it is worth now, what it cost,
	how far through its life it is, and the next depreciation."""
	frappe.has_permission("Asset", "read", asset, throw=True)
	doc = frappe.get_doc("Asset", asset)
	book = doc.finance_books[0] if doc.get("finance_books") else None
	upcoming = None
	if book and doc.docstatus == 1:
		schedule = frappe.db.get_value(
			"Asset Depreciation Schedule", {"asset": asset, "docstatus": 1, "finance_book_id": book.idx}, "name"
		) or frappe.db.get_value("Asset Depreciation Schedule", {"asset": asset, "docstatus": 1}, "name")
		if schedule:
			upcoming = frappe.db.get_value(
				"Depreciation Schedule",
				{"parent": schedule, "journal_entry": ["is", "not set"]},
				["schedule_date", "depreciation_amount"],
				as_dict=True,
				order_by="schedule_date asc",
			)
	return {
		"worth": book.value_after_depreciation if book and doc.docstatus == 1 else doc.net_purchase_amount,
		"cost": doc.net_purchase_amount or doc.total_asset_cost,
		"booked": book.total_number_of_booked_depreciations if book else 0,
		"months": book.total_number_of_depreciations if book else 0,
		"frequency": book.frequency_of_depreciation if book else 0,
		"next": upcoming,
		"depreciates": bool(doc.calculate_depreciation),
		"custodian_name": frappe.db.get_value("Employee", doc.custodian, "employee_name") if doc.custodian else None,
		"service": next_service(asset) if doc.maintenance_required else None,
	}
