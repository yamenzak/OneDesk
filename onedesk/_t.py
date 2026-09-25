import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_permission, update_permission_property
from frappe.utils.password import update_password

ASSET = "ACC-ASS-2026-00002"
EMP = "HR-EMP-00006"
PROBE = "linked.probe@example.org"

def setup():
	head = frappe.get_doc("Record Head", "Asset")
	head.linked = []
	head.append("linked", {"label": "Who Has It", "link_field": "custodian", "fields": "cell_number\npersonal_email\neducation", "placed_in": "location"})
	head.save(ignore_permissions=True)
	make_property_setter("Employee", "cell_number", "permlevel", 1, "Int", validate_fields_for_doctype=False)
	for role, write in (("HR Manager", 1), ("HR User", 0)):
		add_permission("Employee", role, 1)
		update_permission_property("Employee", role, 1, "read", 1)
		update_permission_property("Employee", role, 1, "write", write)
	from onedesk.one_inventory import custody
	if frappe.db.get_value("Asset", ASSET, "custodian") != EMP:
		custody.give(ASSET, EMP)
	emp = frappe.get_doc("Employee", EMP)
	emp.cell_number = "+971 50 123 4567"
	emp.set("education", [{"school_univ": "American University of Sharjah", "qualification": "BSc Computer Engineering", "level": "Graduate", "year_of_passing": 2015}])
	emp.save(ignore_permissions=True)
	if not frappe.db.exists("User", PROBE):
		frappe.get_doc({"doctype": "User", "email": PROBE, "first_name": "Probe", "send_welcome_email": 0,
			"roles": [{"role": "Accounts User"}, {"role": "HR User"}]}).insert(ignore_permissions=True)
	update_password(PROBE, "Probe-Owl-4417")
	frappe.db.commit()
	frappe.clear_cache()
	print("ok", frappe.db.get_value("Asset", ASSET, "custodian"))

def hidden():
	"""Without read at level 1, Mobile is not sent at all."""
	from onedesk.one import linked
	update_permission_property("Employee", "HR User", 1, "read", 0)
	frappe.clear_cache(doctype="Employee")
	frappe.set_user(PROBE)
	doc = frappe.get_doc("Asset", ASSET)
	got = linked.loaded(doc, frappe.get_cached_doc("Record Head", "Asset"))["custodian"]
	print("hidden:", got["hidden"], "values:", sorted(got["values"]), "locked:", got["locked"])
	frappe.set_user("Administrator")
	update_permission_property("Employee", "HR User", 1, "read", 1)
	frappe.db.commit()
	frappe.clear_cache(doctype="Employee")
