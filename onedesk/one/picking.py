"""Whether this request is somebody choosing a record in a Link field, or
OneAI's find_records, which is the same search. Somebody may pick a record
they may not open (a buyer any project, a storekeeper any employee), so a
rule that narrows reading steps aside here; opening stays narrowed."""

import frappe

SEARCHES = {"frappe.desk.search.search_link", "frappe.desk.search.search_widget"}


def picking() -> bool:
	return bool(frappe.flags.one_picking) or (frappe.form_dict or {}).get("cmd") in SEARCHES
